"""LLM report generation driven by llm_config.yml."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from config import llm_config
from database import DailyFeatures, Report

logger = logging.getLogger(__name__)

PLACEHOLDER_REPORT = (
    "今日运动数据已记录。步态整体平稳，建议继续保持户外步行。"
    "今天表现很棒，继续加油！（占位报告：请在 llm_config.yml 或 DEEPSEEK_API_KEY 中配置 API 密钥）"
)


def render_prompt(features: DailyFeatures) -> str:
    return llm_config.user_prompt_template.format(**features.as_dict())


def generate_report_text(features: DailyFeatures) -> str:
    if not llm_config.api_key:
        logger.warning("DEEPSEEK_API_KEY empty — returning placeholder report")
        return PLACEHOLDER_REPORT

    client = OpenAI(
        api_key=llm_config.api_key,
        base_url=llm_config.api_base,
    )

    messages: list[dict[str, str]] = []
    if llm_config.system_prompt.strip():
        messages.append({"role": "system", "content": llm_config.system_prompt})
    messages.append({"role": "user", "content": render_prompt(features)})

    extra_body: dict[str, Any] = {}
    if llm_config.thinking.enabled:
        thinking_cfg: dict[str, Any] = {"type": "enabled"}
        if llm_config.thinking.budget_tokens > 0:
            thinking_cfg["budget_tokens"] = llm_config.thinking.budget_tokens
        extra_body["thinking"] = thinking_cfg

    try:
        response = client.chat.completions.create(
            model=llm_config.model,
            messages=messages,
            max_tokens=llm_config.max_tokens,
            temperature=llm_config.temperature,
            extra_body=extra_body if extra_body else None,
        )
        content = response.choices[0].message.content
        return content.strip() if content else PLACEHOLDER_REPORT
    except Exception:
        logger.exception("LLM API call failed")
        return PLACEHOLDER_REPORT


def save_report(
    date_str: str,
    report_text: str,
    summary: DailyFeatures,
    db: Session,
) -> Report:
    summary_json = json.dumps(summary.as_dict(), ensure_ascii=False)
    existing = db.query(Report).filter(Report.date == date_str).first()
    if existing:
        existing.report_text = report_text
        existing.summary_json = summary_json
        row = existing
    else:
        row = Report(
            date=date_str,
            report_text=report_text,
            summary_json=summary_json,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def generate_and_save_report(date_str: str, db: Session) -> Report:
    from services.feature import compute_daily_features

    features = compute_daily_features(date_str, db)
    report_text = generate_report_text(features)
    return save_report(date_str, report_text, features, db)


def report_generated_at(date_str: str) -> int:
    day = datetime.fromisoformat(date_str)
    return int(datetime.combine(day, datetime.min.time()).timestamp())

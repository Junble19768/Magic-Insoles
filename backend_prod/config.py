"""Application settings: .env + llm_config.yml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent
_LLM_CONFIG_PATH = _BASE_DIR / "llm_config.yml"


@dataclass(frozen=True)
class ThinkingConfig:
    enabled: bool
    budget_tokens: int


@dataclass(frozen=True)
class LLMConfig:
    model: str
    api_base: str
    api_key: str
    max_tokens: int
    temperature: float
    thinking: ThinkingConfig
    system_prompt: str
    user_prompt_template: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = "dev-magic-insoles-key"
    deepseek_api_key: str = ""
    db_path: str = "./data/magic_insoles.db"
    cors_origins: str = "http://localhost:5173"
    device_tcp_host: str = "0.0.0.0"
    device_tcp_port: int = 9000
    device_max_frame_bytes: int = 8192

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def db_path_resolved(self) -> Path:
        path = Path(self.db_path)
        if not path.is_absolute():
            path = _BASE_DIR / path
        return path


def _load_llm_yaml() -> dict[str, Any]:
    if not _LLM_CONFIG_PATH.exists():
        return {}
    with _LLM_CONFIG_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def load_llm_config(settings: Settings) -> LLMConfig:
    raw = _load_llm_yaml()
    thinking_raw = raw.get("thinking", {}) or {}
    api_key = settings.deepseek_api_key or str(raw.get("api_key", "") or "")
    return LLMConfig(
        model=str(raw.get("model", "deepseek-v4-pro")),
        api_base=str(raw.get("api_base", "https://api.deepseek.com")),
        api_key=api_key,
        max_tokens=int(raw.get("max_tokens", 512)),
        temperature=float(raw.get("temperature", 0.7)),
        thinking=ThinkingConfig(
            enabled=bool(thinking_raw.get("enabled", False)),
            budget_tokens=int(thinking_raw.get("budget_tokens", 0)),
        ),
        system_prompt=str(raw.get("system_prompt", "") or ""),
        user_prompt_template=str(
            raw.get(
                "user_prompt_template",
                "今日步数：{step_count}，运动时长：{walk_min} 分钟。",
            )
        ),
    )


settings = Settings()
llm_config = load_llm_config(settings)

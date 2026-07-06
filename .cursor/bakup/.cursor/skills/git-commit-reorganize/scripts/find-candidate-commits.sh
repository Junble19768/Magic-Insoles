#!/usr/bin/env bash
# List recent commits that are non-standard or look temporary.
# Usage: find-candidate-commits.sh [count]
set -euo pipefail

COUNT="${1:-30}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

VALID_TYPE='feat|fix|docs|style|refactor|test|chore'
STANDARD_RE="^(${VALID_TYPE})(\\([^)]*\\))?: .+"

PLACEHOLDER_RE='^(first|second|init)$'
TEMP_PREFIX_RE='^(com[0-9]+|tmp|wip|fixup|squash!)'
TEMP_INLINE_RE='(^com[0-9]+ | com[0-9]+ |^com[0-9]+$)'

suggest_hint() {
  local subject="$1"
  local lower
  lower="$(echo "$subject" | tr '[:upper:]' '[:lower:]')"

  if [[ "$lower" =~ ^refact: ]]; then
    echo "refactor(?): fix type spelling"
    return
  fi
  if [[ "$lower" == "doc" ]] || [[ "$lower" =~ ^doc$ ]]; then
    echo "docs(?): add subject verb"
    return
  fi
  if [[ "$lower" =~ $PLACEHOLDER_RE ]]; then
    echo "squash into themed commit"
    return
  fi
  if [[ "$lower" =~ $TEMP_PREFIX_RE ]] || [[ "$lower" =~ $TEMP_INLINE_RE ]]; then
    echo "squash into themed commit"
    return
  fi
  if [[ ! "$subject" =~ $STANDARD_RE ]]; then
    echo "type(scope): subject"
    return
  fi
  echo ""
}

echo "Scanning last ${COUNT} commits..."
echo "Standard format: type(scope): subject"
echo "Allowed types: feat, fix, docs, style, refactor, test, chore"
echo

git log --format='%H %h %s' -n "$COUNT" | while read -r full short subject; do
  reason=""
  lower_subject="$(echo "$subject" | tr '[:upper:]' '[:lower:]')"

  if [[ ! "$subject" =~ $STANDARD_RE ]]; then
    reason="non-standard format"
  fi

  if [[ "$lower_subject" =~ ^refact: ]]; then
    reason="${reason:+$reason; }type typo (refact)"
  fi

  if [[ "$lower_subject" == "doc" ]]; then
    reason="${reason:+$reason; }single-word subject"
  fi

  if [[ "$lower_subject" =~ $PLACEHOLDER_RE ]]; then
    reason="${reason:+$reason; }placeholder subject"
  fi

  if echo "$lower_subject" | grep -qE "$TEMP_PREFIX_RE"; then
    reason="${reason:+$reason; }temporary marker"
  fi

  if echo "$lower_subject" | grep -qE "$TEMP_INLINE_RE"; then
    reason="${reason:+$reason; }comN pattern"
  fi

  if [[ -n "$reason" ]]; then
    hint="$(suggest_hint "$subject")"
    if [[ -n "$hint" ]]; then
      printf '%s %s  [%s]\n  %s\n  hint: %s\n\n' "$short" "$full" "$reason" "$subject" "$hint"
    else
      printf '%s %s  [%s]\n  %s\n\n' "$short" "$full" "$reason" "$subject"
    fi
  fi
done

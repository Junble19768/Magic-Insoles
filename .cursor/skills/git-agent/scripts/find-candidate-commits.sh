#!/usr/bin/env bash
# List recent commits that are non-standard or look temporary.
# Usage: find-candidate-commits.sh [count]
set -euo pipefail

COUNT="${1:-30}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

valid_type='feat|fix|docs|style|refactor|test|chore'
standard_re="^(${valid_type})(\\([^)]*\\))?: .+"
temp_re='^(com[0-9]+|tmp|wip|fixup|squash!|first|second|init)\b'
inline_temp_re='(^com[0-9]+ | com[0-9]+ |^com[0-9]+$)'

echo "Scanning last ${COUNT} commits..."
echo "Standard format: type(scope): subject"
echo

git log --format='%H %h %s' -n "$COUNT" | while read -r full short subject; do
  lower_subject="$(printf '%s' "$subject" | tr '[:upper:]' '[:lower:]')"
  reasons=()

  [[ ! "$subject" =~ $standard_re ]] && reasons+=("non-standard format")
  [[ "$lower_subject" =~ ^refact: ]] && reasons+=("type typo (refact)")
  [[ "$lower_subject" =~ $temp_re || "$lower_subject" =~ $inline_temp_re ]] && reasons+=("temporary marker")

  if [[ ${#reasons[@]} -gt 0 ]]; then
    printf '%s %s  [%s]\n  %s\n\n' "$short" "$full" "$(IFS='; '; echo "${reasons[*]}")" "$subject"
  fi
done

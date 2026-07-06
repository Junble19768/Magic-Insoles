#!/usr/bin/env bash
# Summarize uncommitted changes grouped by module scope.
# Usage: summarize-working-tree.sh [path1 path2 ...]
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

infer_scope() {
  local file="$1"
  case "$file" in
    backend/*) echo "backend" ;;
    frontend/*) echo "frontend" ;;
    3rdparty/*) echo "3rdparty" ;;
    docs/*) echo "docs" ;;
    .cursor/*) echo "cursor" ;;
    config.yml) echo "config" ;;
    .github/*|*.yml|*.yaml|.gitignore) echo "chore" ;;
    *) echo "chore" ;;
  esac
}

declare -A groups=()

while IFS= read -r line; do
  [[ -z "$line" ]] && continue

  index_status="${line:0:1}"
  worktree_status="${line:1:1}"
  file="${line:3}"
  file="${file%\"}"
  file="${file#\"}"

  if [[ $# -gt 0 ]]; then
    matched=false
    for prefix in "$@"; do
      [[ "$file" == "$prefix"* ]] && matched=true && break
    done
    [[ "$matched" == false ]] && continue
  fi

  stage=()
  [[ "$index_status" != " " && "$index_status" != "?" ]] && stage+=("staged")
  [[ "$worktree_status" != " " ]] && stage+=("unstaged")
  [[ "$index_status" == "?" && "$worktree_status" == "?" ]] && stage=("untracked")

  scope="$(infer_scope "$file")"
  entry="  [$(IFS=' + '; echo "${stage[*]}")] $file"
  groups[$scope]="${groups[$scope]:-}${groups[$scope]:+$'\n'}$entry"
done < <(git status --porcelain)

if [[ ${#groups[@]} -eq 0 ]]; then
  echo "No uncommitted changes found."
  exit 0
fi

echo "Working tree summary (grouped by scope):"
echo
for scope in backend frontend 3rdparty docs cursor config chore; do
  if [[ -n "${groups[$scope]:-}" ]]; then
    echo "[$scope]"
    echo "${groups[$scope]}"
    echo
    unset "groups[$scope]"
  fi
done

for scope in "${!groups[@]}"; do
  echo "[$scope]"
  echo "${groups[$scope]}"
  echo
done

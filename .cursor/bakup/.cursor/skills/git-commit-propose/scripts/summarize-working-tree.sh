#!/usr/bin/env bash
# Summarize uncommitted changes grouped by module scope.
# Usage: summarize-working-tree.sh [path1 path2 ...]
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

PATH_ARGS=()
if [[ $# -gt 0 ]]; then
  PATH_ARGS=("$@")
fi

infer_scope() {
  local file="$1"

  case "$file" in
    backend/*) echo "backend" ;;
    frontend/*) echo "frontend" ;;
    3rdparty/*) echo "3rdparty" ;;
    docs/*) echo "docs" ;;
    config.yml) echo "config" ;;
    .github/*|.cursor/*|*.yml|*.yaml|environment.yml|.gitignore)
      echo "chore"
      ;;
    *)
      echo "chore"
      ;;
  esac
}

describe_stage() {
  local index_status="$1"
  local worktree_status="$2"

  local parts=()
  if [[ "$index_status" != " " && "$index_status" != "?" ]]; then
    parts+=("staged")
  fi
  if [[ "$worktree_status" != " " ]]; then
    parts+=("unstaged")
  fi
  if [[ "$index_status" == "?" && "$worktree_status" == "?" ]]; then
    parts=("untracked")
  fi

  local IFS=' + '
  echo "${parts[*]}"
}

declare -A GROUPS=()
declare -A ENTRIES=()

while IFS= read -r line; do
  if [[ -z "$line" ]]; then
    continue
  fi

  index_status="${line:0:1}"
  worktree_status="${line:1:1}"
  rest="${line:3}"

  # Handle quoted paths from git status --porcelain
  if [[ "$rest" == \"*\" ]]; then
    file="${rest:1:${#rest}-2}"
  else
    file="$rest"
  fi

  if [[ ${#PATH_ARGS[@]} -gt 0 ]]; then
    matched=false
    for prefix in "${PATH_ARGS[@]}"; do
      if [[ "$file" == "$prefix"* ]]; then
        matched=true
        break
      fi
    done
    if [[ "$matched" == false ]]; then
      continue
    fi
  fi

  scope="$(infer_scope "$file")"
  stage="$(describe_stage "$index_status" "$worktree_status")"
  entry="  [$stage] $file"

  if [[ -n "${GROUPS[$scope]:-}" ]]; then
    GROUPS[$scope]="${GROUPS[$scope]}"$'\n'"$entry"
  else
    GROUPS[$scope]="$entry"
  fi
done < <(git status --porcelain)

if [[ ${#GROUPS[@]} -eq 0 ]]; then
  echo "No uncommitted changes found."
  exit 0
fi

ORDER=(backend frontend 3rdparty docs config chore)
echo "Working tree summary (grouped by scope):"
echo

for scope in "${ORDER[@]}"; do
  if [[ -n "${GROUPS[$scope]:-}" ]]; then
    echo "[$scope]"
    echo "${GROUPS[$scope]}"
    echo
    unset "GROUPS[$scope]"
  fi
done

for scope in "${!GROUPS[@]}"; do
  echo "[$scope]"
  echo "${GROUPS[$scope]}"
  echo
done

echo "Scope mapping:"
echo "  backend/     -> backend"
echo "  frontend/    -> frontend"
echo "  3rdparty/    -> 3rdparty"
echo "  docs/        -> docs"
echo "  config.yml   -> config"
echo "  other        -> chore"

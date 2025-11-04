#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but was not found on PATH." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SH="$SCRIPT_DIR/../common.sh"
if [[ -f "$COMMON_SH" ]]; then
  # shellcheck source=/dev/null
  source "$COMMON_SH"

  if [[ -z "${SPEC_KITTY_AUTORETRY:-}" ]]; then
    repo_root=$(get_repo_root)
    current_branch=$(get_current_branch)
    if [[ ! "$current_branch" =~ ^[0-9]{3}- ]]; then
      if latest_worktree=$(find_latest_feature_worktree "$repo_root" 2>/dev/null); then
        if [[ -d "$latest_worktree" ]]; then
          >&2 echo "[spec-kitty] Auto-running tasks-move-to-lane inside $latest_worktree (current branch: $current_branch)"
          (
            cd "$latest_worktree" && \
            SPEC_KITTY_AUTORETRY=1 "$0" "$@"
          )
          exit $?
        fi
      fi
    fi
  fi
fi

PY_HELPER="$SCRIPT_DIR/../tasks/tasks_cli.py"

if [[ ! -f "$PY_HELPER" ]]; then
  echo "Error: tasks_cli helper not found at $PY_HELPER" >&2
  exit 1
fi

python3 "$PY_HELPER" move "$@"

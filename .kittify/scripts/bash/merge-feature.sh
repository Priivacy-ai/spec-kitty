#!/usr/bin/env bash
set -euo pipefail

# Script: merge-feature.sh
# Purpose: Merge feature back to main branch
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation), #3 (context auto-detection)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Issue #3: Auto-detect context - switch to latest worktree if on main
if [[ -z "${SPEC_KITTY_AUTORETRY:-}" ]]; then
    repo_root=$(get_repo_root)
    current_branch=$(get_current_branch)
    if [[ ! "$current_branch" =~ ^[0-9]{3}- ]]; then
        if latest_worktree=$(find_latest_feature_worktree "$repo_root" 2>/dev/null); then
            if [[ -d "$latest_worktree" ]]; then
                if ! is_quiet; then
                    show_log "Auto-switching to feature worktree: $latest_worktree"
                fi
                (
                    cd "$latest_worktree" && \
                    SPEC_KITTY_AUTORETRY=1 "$0" "$@"
                )
                exit $?
            fi
        fi
    fi
fi

# Validate python3
if ! command -v python3 >/dev/null 2>&1; then
  show_log "❌ ERROR: python3 is required but was not found on PATH"
  exit $EXIT_PRECONDITION_ERROR
fi

PY_HELPER="$SCRIPT_DIR/../tasks/tasks_cli.py"

# Validate helper
if [[ ! -f "$PY_HELPER" ]]; then
  show_log "❌ ERROR: tasks_cli helper not found at $PY_HELPER"
  exit $EXIT_PRECONDITION_ERROR
fi

# Handle common flags
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Merge feature branch back to main"
    exit $EXIT_SUCCESS
fi

python3 "$PY_HELPER" merge "$@"

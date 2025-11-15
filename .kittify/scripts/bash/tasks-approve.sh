#!/usr/bin/env bash
set -euo pipefail

# Script: tasks-approve.sh
# Purpose: Approve a task from for_review lane with proper reviewer attribution
# Usage: tasks-approve.sh <feature> <work_package_id> [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Auto-detect context - switch to latest worktree if on main
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
        "Approve a task from for_review lane with proper reviewer attribution"
    echo ""
    echo "Usage: $0 <feature> <work_package_id> [options]"
    echo ""
    echo "Options:"
    echo "  --review-status <status>       Review decision (default: approved)"
    echo "  --reviewer-agent <agent_id>    Reviewer agent ID (default: \$AGENT_ID or 'reviewer')"
    echo "  --reviewer-shell-pid <pid>     Reviewer shell PID (default: parent PID)"
    echo "  --target-lane <lane>           Target lane (default: done)"
    echo "  --note <note>                  Additional note for activity log"
    echo "  --dry-run                      Show what would happen without modifying files"
    echo ""
    echo "Example:"
    echo "  $0 001-my-feature WP01 --review-status 'approved without changes' --reviewer-agent claude-reviewer"
    echo ""
    exit $EXIT_SUCCESS
fi

python3 "$PY_HELPER" approve "$@"

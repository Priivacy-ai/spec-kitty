#!/usr/bin/env bash
set -euo pipefail

# Script: move-task-to-doing.sh
# Purpose: Move task to doing lane and record metadata
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Handle common flags
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Move task to doing lane" \
        "WORK_PACKAGE_ID" "Task identifier" \
        "FEATURE_DIR" "Feature directory path" \
        "AGENT" "AI agent name (optional, defaults to 'unknown')"
    exit $EXIT_SUCCESS
fi

# Validate required arguments
if [[ $# -lt 2 ]]; then
  show_log "❌ ERROR: Missing required arguments"
  show_log "Usage: $0 WORK_PACKAGE_ID FEATURE_DIR [AGENT]"
  exit $EXIT_USAGE_ERROR
fi

TASK_ID="$1"
FEATURE_DIR="$2"
FEATURE_DIR="${FEATURE_DIR%/}"
AGENT="${3:-unknown}"

# Validate arguments
if ! validate_arg_provided "$TASK_ID" "WORK_PACKAGE_ID"; then
  exit $EXIT_VALIDATION_ERROR
fi

if [[ ! -d "$FEATURE_DIR" ]]; then
  show_log "❌ ERROR: Feature directory not found: $FEATURE_DIR"
  exit $EXIT_VALIDATION_ERROR
fi

FEATURE_SLUG=$(basename "$FEATURE_DIR")
LANE_HELPER="$SCRIPT_DIR/tasks-move-to-lane.sh"

if [[ ! -x "$LANE_HELPER" ]]; then
  show_log "❌ ERROR: Lane helper script not available at $LANE_HELPER"
  exit $EXIT_PRECONDITION_ERROR
fi

SHELL_PID=$$
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

"$LANE_HELPER" "$FEATURE_SLUG" "$TASK_ID" doing \
  --agent "$AGENT" \
  --shell-pid "$SHELL_PID" \
  --note "Started implementation" \
  --timestamp "$TIMESTAMP"

if ! is_quiet; then
    show_log "✓ Moved work package $TASK_ID to doing lane"
    show_log "  Feature: $FEATURE_SLUG"
    show_log "  Shell PID: $SHELL_PID"
    show_log "  Agent: $AGENT"
    show_log "  Timestamp: $TIMESTAMP"
    show_log ""
    show_log "Next: Implement the task following the prompt guidance"
fi

exit $EXIT_SUCCESS

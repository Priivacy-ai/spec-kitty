#!/usr/bin/env bash
set -euo pipefail

# Script: validate-task-workflow.sh
# Purpose: Validate task workflow state before implementation
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Handle common flags
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Validate task workflow state" \
        "WORK_PACKAGE_ID" "Task identifier" \
        "FEATURE_DIR" "Feature directory path"
    exit $EXIT_SUCCESS
fi

# Validate required arguments
if [[ $# -lt 2 ]]; then
  show_log "❌ ERROR: Missing required arguments"
  show_log "Usage: $0 WORK_PACKAGE_ID FEATURE_DIR"
  exit $EXIT_USAGE_ERROR
fi

TASK_ID="$1"
FEATURE_DIR="$2"
FEATURE_DIR="${FEATURE_DIR%/}"
PROMPT_PATH=""

# Validate arguments
if ! validate_arg_provided "$TASK_ID" "WORK_PACKAGE_ID"; then
  exit $EXIT_VALIDATION_ERROR
fi

if [[ ! -d "$FEATURE_DIR" ]]; then
  show_log "❌ ERROR: Feature directory not found: $FEATURE_DIR"
  exit $EXIT_VALIDATION_ERROR
fi

if [[ -d "$FEATURE_DIR/tasks/doing" ]]; then
  PROMPT_PATH=$(find "$FEATURE_DIR/tasks/doing" -maxdepth 3 -name "${TASK_ID}-*.md" -print -quit)
fi

if [[ -z "$PROMPT_PATH" ]]; then
  show_log "❌ ERROR: Work package $TASK_ID not found in tasks/doing/"
  show_log "   Move the prompt from tasks/planned/ to tasks/doing/ using tasks-move-to-lane.sh before implementing."
  exit $EXIT_VALIDATION_ERROR
fi

# Validate workflow state
lane_ok=$(grep -E '^[[:space:]]*lane:[[:space:]]*"doing"' "$PROMPT_PATH" || true)
if [[ -z "$lane_ok" ]]; then
  show_log "❌ ERROR: $PROMPT_PATH does not declare lane: \"doing\" in frontmatter."
  exit $EXIT_VALIDATION_ERROR
fi

# Check for optional metadata
if ! grep -Eq '^[[:space:]]*shell_pid:' "$PROMPT_PATH"; then
  if ! is_quiet; then
      show_log "⚠️  WARNING: $PROMPT_PATH is missing shell_pid in frontmatter."
  fi
fi

if ! grep -Eq '^[[:space:]]*agent:' "$PROMPT_PATH"; then
  if ! is_quiet; then
      show_log "⚠️  WARNING: $PROMPT_PATH is missing agent in frontmatter."
  fi
fi

if ! is_quiet; then
    show_log "✓ Work package $TASK_ID workflow validated"
    show_log "  Prompt location: $PROMPT_PATH"
fi

exit $EXIT_SUCCESS

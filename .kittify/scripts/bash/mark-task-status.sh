#!/usr/bin/env bash
set -euo pipefail

# Script: mark-task-status.sh
# Purpose: Mark task completion status (done/pending)
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

TASK_ID=""
STATUS=""
TASKS_FILE=""

# Handle common flags
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Mark task completion status in tasks.md" \
        "--task-id" "Task identifier (required)" \
        "--status" "Status: done or pending (required)" \
        "--tasks-file" "Path to tasks.md (optional, uses feature default)"
    exit $EXIT_SUCCESS
fi

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --task-id)
            TASK_ID="$2"
            shift 2
            ;;
        --status)
            STATUS="$2"
            shift 2
            ;;
        --tasks-file)
            TASKS_FILE="$2"
            shift 2
            ;;
        *)
            show_log "❌ ERROR: Unknown argument: $1"
            exit $EXIT_USAGE_ERROR
            ;;
    esac
done

# Validate required arguments (Issue #5)
if [[ -z "$TASK_ID" ]]; then
    show_log "❌ ERROR: --task-id is required"
    exit $EXIT_VALIDATION_ERROR
fi

if [[ -z "$STATUS" ]]; then
    show_log "❌ ERROR: --status is required"
    exit $EXIT_VALIDATION_ERROR
fi

if [[ "$STATUS" != "done" && "$STATUS" != "pending" ]]; then
    show_log "❌ ERROR: --status must be 'done' or 'pending' (got: $STATUS)"
    exit $EXIT_VALIDATION_ERROR
fi

# Get feature paths
eval $(get_feature_paths)

if [[ -z "$TASKS_FILE" ]]; then
    TASKS_FILE="$TASKS"
fi

# Validate tasks file exists
if [[ ! -f "$TASKS_FILE" ]]; then
    show_log "❌ ERROR: tasks file not found: $TASKS_FILE"
    show_log "Have you run '/spec-kitty.tasks' yet?"
    exit $EXIT_VALIDATION_ERROR
fi

python3 - "$TASK_ID" "$STATUS" "$TASKS_FILE" <<'PY'
import re
import sys
from pathlib import Path

task_id, status, path = sys.argv[1:]
path = Path(path)
text = path.read_text()
pattern = re.compile(rf"^(\s*-\s*)\[[ xX]\]\s+({re.escape(task_id)})(\b.*)$", re.MULTILINE)
box = "[X]" if status == "done" else "[ ]"

def repl(match):
    return f"{match.group(1)}{box} {match.group(2)}{match.group(3)}"

new_text, count = pattern.subn(repl, text, count=1)
if count == 0:
    sys.stderr.write(f"Task ID {task_id} not found in {path}\n")
    sys.exit(1)

path.write_text(new_text)
PY

if ! is_quiet; then
    show_log "✓ Updated $TASK_ID to status: $STATUS"
fi

exit $EXIT_SUCCESS

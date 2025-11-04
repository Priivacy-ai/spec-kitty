#!/usr/bin/env bash
set -euo pipefail

print_usage() {
    cat <<'USAGE'
Usage: mark-task-status.sh --task-id TXXX --status <done|pending> [--tasks-file path]

Marks a task entry in tasks.md with the desired checkbox state.
- If --tasks-file is omitted, the current feature's tasks.md is used via common.sh helpers.
- Updates the first matching task ID only; aborts if no entry is found.
USAGE
}

TASK_ID=""
STATUS=""
TASKS_FILE=""

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
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            print_usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "$TASK_ID" ]]; then
    echo "--task-id is required" >&2
    exit 1
fi

if [[ -z "$STATUS" ]]; then
    echo "--status is required" >&2
    exit 1
fi

case "$STATUS" in
    done|pending)
        ;;
    *)
        echo "--status must be 'done' or 'pending'" >&2
        exit 1
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

eval $(get_feature_paths)

if [[ -z "$TASKS_FILE" ]]; then
    TASKS_FILE="$TASKS"
fi

if [[ ! -f "$TASKS_FILE" ]]; then
    echo "tasks file not found: $TASKS_FILE" >&2
    exit 1
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

echo "Updated $TASK_ID to $STATUS in $TASKS_FILE"

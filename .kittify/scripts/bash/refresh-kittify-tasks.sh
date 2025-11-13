#!/usr/bin/env bash
set -euo pipefail

# Script: refresh-kittify-tasks.sh
# Purpose: Update task helper modules in existing projects
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Handle common flags
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Update task helper modules in existing Spec Kitty projects" \
        "[project-root]" "Target project root (optional, auto-detects if not provided)"
    exit $EXIT_SUCCESS
fi

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_TASK_DIR="$REPO_ROOT/scripts/tasks"

if [[ ! -d "$SOURCE_TASK_DIR" ]]; then
  show_log "❌ ERROR: Expected task helpers at $SOURCE_TASK_DIR"
  exit $EXIT_PRECONDITION_ERROR
fi

if [[ $# -gt 1 ]]; then
  show_log "❌ ERROR: Too many arguments provided"
  exit $EXIT_USAGE_ERROR
fi

if [[ $# -eq 1 ]]; then
  if [[ ! -d $1 ]]; then
    show_log "❌ ERROR: project path '$1' does not exist or is not a directory"
    exit $EXIT_VALIDATION_ERROR
  fi
  START_PATH="$(cd "$1" && pwd)"
else
  START_PATH="$(pwd)"
fi

locate_project_root() {
  local current="$1"
  while true; do
    if [[ -d "$current/.kittify/scripts" ]]; then
      echo "$current"
      return 0
    fi
    if [[ "$current" == "/" ]]; then
      break
    fi
    current="$(dirname "$current")"
  done
  return 1
}

PROJECT_ROOT="$(locate_project_root "$START_PATH" || true)"
if [[ -z "$PROJECT_ROOT" ]]; then
  show_log "❌ ERROR: Unable to locate .kittify/scripts starting from $START_PATH"
  exit $EXIT_VALIDATION_ERROR
fi

TARGET_SCRIPT_ROOT="$PROJECT_ROOT/.kittify/scripts"
TARGET_TASK_DIR="$TARGET_SCRIPT_ROOT/tasks"

# Preserve legacy task CLI for reference if a standalone file exists.
LEGACY_BACKUP="$TARGET_SCRIPT_ROOT/tasks_cli.py.legacy"
if [[ -f "$TARGET_TASK_DIR/tasks_cli.py" ]]; then
  cp "$TARGET_TASK_DIR/tasks_cli.py" "$LEGACY_BACKUP"
elif [[ -f "$TARGET_SCRIPT_ROOT/tasks_cli.py" ]]; then
  cp "$TARGET_SCRIPT_ROOT/tasks_cli.py" "$LEGACY_BACKUP"
fi

python3 - "$SOURCE_TASK_DIR" "$TARGET_TASK_DIR" <<'PY'
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

if not src.is_dir():
    raise SystemExit(f"Source directory missing: {src}")

if dst.exists():
    shutil.rmtree(dst)

def ignore_cb(_path, names):
    return {"__pycache__"} if "__pycache__" in names else set()

shutil.copytree(src, dst, ignore=ignore_cb)
PY

if ! is_quiet; then
    show_log "✓ Updated .kittify scripts successfully"
    show_log "  Source : $SOURCE_TASK_DIR"
    show_log "  Target : $TARGET_TASK_DIR"
    if [[ -f "$LEGACY_BACKUP" ]]; then
      show_log "  Legacy backup saved at $LEGACY_BACKUP"
    fi
fi

exit $EXIT_SUCCESS

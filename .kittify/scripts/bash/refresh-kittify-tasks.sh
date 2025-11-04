#!/usr/bin/env bash
set -euo pipefail

# refresh-kittify-tasks.sh
# Copy the latest task helper modules into an existing Spec Kitty project.
# Usage:
#   scripts/bash/refresh-kittify-tasks.sh [<project-root>]
# If no project root is provided the script walks upward from the current
# directory until it finds a .kittify/scripts directory.

usage() {
  cat <<'EOF'
Usage: refresh-kittify-tasks.sh [<project-root>]

Copies the current repo's scripts/tasks helpers into the target project's
.kittify/scripts/tasks directory. Provide the project root explicitly or run
from anywhere inside the project tree.
EOF
}

if [[ ${1:-} == "--help" ]] || [[ ${1:-} == "-h" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_TASK_DIR="$REPO_ROOT/scripts/tasks"

if [[ ! -d "$SOURCE_TASK_DIR" ]]; then
  echo "Error: expected task helpers at $SOURCE_TASK_DIR" >&2
  exit 1
fi

if [[ $# -gt 1 ]]; then
  echo "Error: too many arguments" >&2
  usage >&2
  exit 1
fi

if [[ $# -eq 1 ]]; then
  if [[ ! -d $1 ]]; then
    echo "Error: project path '$1' does not exist or is not a directory" >&2
    exit 1
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
  echo "Error: unable to locate .kittify/scripts starting from $START_PATH" >&2
  exit 1
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

echo "✅ Updated .kittify scripts:"
echo "   Source : $SOURCE_TASK_DIR"
echo "   Target : $TARGET_TASK_DIR"
if [[ -f "$LEGACY_BACKUP" ]]; then
  echo "   Legacy backup saved at $LEGACY_BACKUP"
fi

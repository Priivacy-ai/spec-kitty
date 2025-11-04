#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 WORK_PACKAGE_ID FEATURE_DIR" >&2
  exit 1
fi

TASK_ID="$1"
FEATURE_DIR="$2"
FEATURE_DIR="${FEATURE_DIR%/}"
PROMPT_PATH=""

if [[ ! -d "$FEATURE_DIR" ]]; then
  echo "❌ ERROR: Feature directory not found: $FEATURE_DIR" >&2
  exit 1
fi

if [[ -d "$FEATURE_DIR/tasks/doing" ]]; then
  PROMPT_PATH=$(find "$FEATURE_DIR/tasks/doing" -maxdepth 3 -name "${TASK_ID}-*.md" -print -quit)
fi

if [[ -z "$PROMPT_PATH" ]]; then
  echo "❌ ERROR: Work package $TASK_ID not found in tasks/doing/." >&2
  echo "   Move the prompt from tasks/planned/ to tasks/doing/ using tasks-move-to-lane.sh before implementing." >&2
  exit 1
fi

lane_ok=$(grep -E '^[[:space:]]*lane:[[:space:]]*"doing"' "$PROMPT_PATH" || true)
if [[ -z "$lane_ok" ]]; then
  echo "❌ ERROR: $PROMPT_PATH does not declare lane: \"doing\" in frontmatter." >&2
  exit 1
fi

if ! grep -Eq '^[[:space:]]*shell_pid:' "$PROMPT_PATH"; then
  echo "⚠️  WARNING: $PROMPT_PATH is missing shell_pid in frontmatter." >&2
fi

if ! grep -Eq '^[[:space:]]*agent:' "$PROMPT_PATH"; then
  echo "⚠️  WARNING: $PROMPT_PATH is missing agent in frontmatter." >&2
fi

echo "✅ Work package $TASK_ID workflow validated"
echo "   Prompt location: $PROMPT_PATH"
exit 0

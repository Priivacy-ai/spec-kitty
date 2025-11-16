#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 WORK_PACKAGE_ID FEATURE_DIR [AGENT]" >&2
  exit 1
fi

TASK_ID="$1"
FEATURE_DIR="$2"
FEATURE_DIR="${FEATURE_DIR%/}"
AGENT="${3:-unknown}"

if [[ ! -d "$FEATURE_DIR" ]]; then
  echo "❌ ERROR: Feature directory not found: $FEATURE_DIR" >&2
  exit 1
fi

FEATURE_SLUG=$(basename "$FEATURE_DIR")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LANE_HELPER="$SCRIPT_DIR/tasks-move-to-lane.sh"

if [[ ! -x "$LANE_HELPER" ]]; then
  echo "❌ ERROR: Lane helper script not available at $LANE_HELPER" >&2
  exit 1
fi

SHELL_PID=$$
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

"$LANE_HELPER" "$FEATURE_SLUG" "$TASK_ID" doing \
  --agent "$AGENT" \
  --shell-pid "$SHELL_PID" \
  --note "Started implementation" \
  --timestamp "$TIMESTAMP"

echo "✅ Moved work package $TASK_ID to doing lane via tasks-move-to-lane.sh"
echo "   Feature: $FEATURE_SLUG"
echo "   Shell PID: $SHELL_PID"
echo "   Agent: $AGENT"
echo "   Timestamp: $TIMESTAMP"
echo ""
echo "Next: Implement the task following the prompt guidance"

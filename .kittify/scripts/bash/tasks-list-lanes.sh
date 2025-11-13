#!/usr/bin/env bash
set -euo pipefail

# Script: tasks-list-lanes.sh
# Purpose: List all tasks in workflow lanes
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

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
        "List all tasks in workflow lanes"
    exit $EXIT_SUCCESS
fi

python3 "$PY_HELPER" list "$@"

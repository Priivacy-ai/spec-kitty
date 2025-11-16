#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but was not found on PATH." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_HELPER="$SCRIPT_DIR/../tasks/tasks_cli.py"

if [[ ! -f "$PY_HELPER" ]]; then
  echo "Error: tasks_cli helper not found at $PY_HELPER" >&2
  exit 1
fi

python3 "$PY_HELPER" accept "$@"

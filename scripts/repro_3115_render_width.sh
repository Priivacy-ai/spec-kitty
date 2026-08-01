#!/bin/bash
# Reproducer for #3115: an 80-column dumb-terminal render width folds a
# 36-character project uuid across two lines in `sync status` / `sync doctor`,
# and a substring assertion in the test suite stops seeing it.
#
# The cause (measured, not guessed): `rich.console.Console.size` returns
# `ConsoleDimensions(80, 25)` from its `if self.is_dumb_terminal:` branch,
# which sits ABOVE the `COLUMNS` read -- so `COLUMNS` is set by the victim
# tests' own isolation fixture and never consulted. `is_terminal` is true
# whenever `FORCE_COLOR` is set to a non-empty value. The `Project` column is
# `overflow="fold"` (src/specify_cli/cli/commands/sync.py:1440, deliberate),
# so at width 80 the uuid folds and stops being a contiguous substring of the
# rendered output.
#
# Usage (one line):
#   TERM=dumb FORCE_COLOR=1 ./scripts/repro_3115_render_width.sh [status|doctor|both]
#
# Control -- must PASS, distinguishing "the width is the cause" from "this
# file is just broken" -- add TTY_COMPATIBLE=0:
#   TERM=dumb FORCE_COLOR=1 TTY_COMPATIBLE=0 ./scripts/repro_3115_render_width.sh [status|doctor|both]
#
# Deliberately one victim file per pytest invocation, one process, no xdist
# (C-004): a reproducer that depends on `--dist loadfile`'s dynamic,
# work-stealing worker assignment is not reproducible by construction.
#
# Sets PYTHONPATH to this checkout's own src/ (sibling of this script's
# directory) so the reproducer is correct even when the ambient venv's
# editable install points at a different checkout's src -- as it silently
# does for a venv shared with a git worktree.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

STATUS_FILE="tests/cli/commands/test_sync_status_per_project_3030.py"
DOCTOR_FILE="tests/cli/commands/test_sync_doctor_per_project_3030.py"

TARGET="${1:-status}"

PYTEST_BIN=("${PYTHON_BIN:-python3}" -m pytest)

run_one() {
  local file="$1"
  local label="$2"
  echo "=== ${label}: ${file} (one file, one process, no xdist) ==="
  # -p no:cacheprovider only -- no -n/--dist flag is ever passed here.
  "${PYTEST_BIN[@]}" "$REPO_ROOT/$file" -p no:cacheprovider
}

cd "$REPO_ROOT"

case "$TARGET" in
  status)
    run_one "$STATUS_FILE" "status"
    ;;
  doctor)
    run_one "$DOCTOR_FILE" "doctor"
    ;;
  both)
    run_one "$STATUS_FILE" "status"
    run_one "$DOCTOR_FILE" "doctor"
    ;;
  *)
    echo "usage: $0 [status|doctor|both]" >&2
    exit 2
    ;;
esac

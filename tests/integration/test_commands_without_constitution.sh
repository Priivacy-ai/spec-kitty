#!/usr/bin/env bash
set -euo pipefail

TEST_DIR=${1:-/tmp/test-no-constitution}
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

git init
git config user.name "Test User"
git config user.email "test@example.com"

spec-kitty init --here --ai codex --script sh --ignore-agent-tools --force

if [ -f .kittify/memory/constitution.md ]; then
  rm .kittify/memory/constitution.md
fi

CREATE_JSON=$(spec-kitty agent feature create-feature "test-feature" --json)

WORKTREE=$(CREATE_JSON="$CREATE_JSON" python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ.get("CREATE_JSON", "{}"))
path = payload.get("worktree_path")
if not path:
    sys.exit(1)
print(path)
PY
)

if [ ! -d "$WORKTREE" ]; then
  echo "ERROR: worktree not created"
  exit 1
fi

cd "$WORKTREE"

spec-kitty agent feature setup-plan --json >/dev/null

echo "PASS: Commands ran without constitution"

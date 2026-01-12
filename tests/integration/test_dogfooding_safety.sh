#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO_ROOT"

if ! python3 -m build --help >/dev/null 2>&1; then
  echo "SKIP: python -m build not available; install build to run dogfooding test."
  exit 0
fi

MARKER="Dogfooding Safety Marker"
MEMORY_DIR="$REPO_ROOT/.kittify/memory"
MEMORY_FILE="$MEMORY_DIR/constitution.md"
BACKUP_FILE="${MEMORY_FILE}.bak"

cleanup() {
  if [ -f "$BACKUP_FILE" ]; then
    mv "$BACKUP_FILE" "$MEMORY_FILE"
  else
    rm -f "$MEMORY_FILE"
  fi
}

trap cleanup EXIT

mkdir -p "$MEMORY_DIR"
if [ -f "$MEMORY_FILE" ]; then
  cp "$MEMORY_FILE" "$BACKUP_FILE"
fi

echo "# $MARKER" > "$MEMORY_FILE"
echo "This should never be packaged." >> "$MEMORY_FILE"

python3 -m build

WHEEL=$(ls dist/spec_kitty_cli-*.whl | tail -1)
if unzip -l "$WHEEL" | grep -E "(\.kittify/|memory/constitution\.md)"; then
  echo "ERROR: wheel contains runtime constitution or .kittify paths"
  exit 1
fi

tmp_venv=/tmp/test-dogfooding-venv
tmp_project=/tmp/test-dogfooding-user-project
rm -rf "$tmp_venv" "$tmp_project"

python3 -m venv "$tmp_venv"
"$tmp_venv/bin/pip" install "$WHEEL"

mkdir -p "$tmp_project"
cd "$tmp_project"
"$tmp_venv/bin/spec-kitty" init --here --ai codex --script sh --no-git --ignore-agent-tools

if grep -q "$MARKER" .kittify/memory/constitution.md; then
  echo "ERROR: user received spec-kitty internal constitution"
  exit 1
fi

echo "PASS: dogfooding safety test completed"

cd "$REPO_ROOT"
rm -rf "$tmp_venv" "$tmp_project"

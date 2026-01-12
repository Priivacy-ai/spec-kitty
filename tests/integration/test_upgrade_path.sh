#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)

if ! command -v docker >/dev/null 2>&1; then
  echo "SKIP: docker not found; upgrade path test requires Docker."
  exit 0
fi

if ! ls "$REPO_ROOT"/dist/spec_kitty_cli-*.whl >/dev/null 2>&1; then
  echo "ERROR: wheel not found in dist/. Build the package first."
  exit 1
fi

echo "==================================="
echo "Upgrade Path Integration Test"
echo "0.6.4 -> 0.10.12"
echo "==================================="

TTY_FLAG=""
if [ -t 0 ]; then
  TTY_FLAG="-t"
fi

docker run --rm -i $TTY_FLAG \
  -v "$REPO_ROOT":/workspace \
  -w /tmp/test-upgrade \
  python:3.11-slim bash -c '
set -e

apt-get update -y >/dev/null
apt-get install -y git >/dev/null

pip install --no-cache-dir spec-kitty-cli==0.6.4

git config --global user.name "Test User"
git config --global user.email "test@example.com"

spec-kitty init test-project --ai codex --script sh --mission software-dev

cd test-project

test -d .kittify/memory
test -d .kittify/scripts

echo "# Test Constitution" > .kittify/memory/constitution.md
echo "## Principle 1" >> .kittify/memory/constitution.md

pip install --no-cache-dir --upgrade /workspace/dist/spec_kitty_cli-*.whl

spec-kitty upgrade --force

grep -q "Principle 1" .kittify/memory/constitution.md

if [ -d .kittify/missions/software-dev/constitution ]; then
  echo "WARN: mission constitution still present"
else
  echo "OK: mission constitutions removed"
fi

spec-kitty agent feature setup-plan --help >/dev/null

spec-kitty upgrade --force

echo "PASS: upgrade path test completed"
'

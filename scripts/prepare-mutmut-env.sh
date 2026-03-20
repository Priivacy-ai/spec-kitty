#!/bin/bash
# Helper script to prepare mutmut environment for mutation testing.
#
# The actual copy logic lives in tests.mutmut_env so pytest startup and this
# manual repair path use the same implementation.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Preparing mutmut environment ==="

if ! command -v mutmut >/dev/null 2>&1; then
    echo "ERROR: mutmut command not found"
    exit 1
fi

# Step 1: Run mutmut to create mutants directory (will fail during stats collection)
echo "Step 1: Creating mutants directory..."
mutmut run --max-children 1 2>&1 || true

# Step 2: Check if mutants directory was created
if [ ! -d "mutants/src/specify_cli" ]; then
    echo "ERROR: mutants/src/specify_cli directory not found"
    exit 1
fi

echo "Step 2: Copying missing source files..."
python3 -m tests.mutmut_env \
    --repo-root "$REPO_ROOT" \
    --mutants-root "$REPO_ROOT/mutants" \
    --require "src/specify_cli/frontmatter.py" \
    --require "src/doctrine"

echo "✅ Environment prepared successfully!"
echo ""
echo "Now you can run mutmut with full capacity:"
echo "  mutmut run --max-children 4"
echo ""
echo "Or continue the interrupted run:"
echo "  cd mutants && mutmut run --max-children 4"

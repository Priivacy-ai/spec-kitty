#!/bin/bash
# Helper script to prepare mutmut environment for mutation testing
# This script works around the stats collection issue by manually copying
# all required modules before mutmut tries to run pytest.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Preparing mutmut environment ==="

# Step 1: Run mutmut to create mutants directory (will fail during stats collection)
echo "Step 1: Creating mutants directory..."
mutmut run --max-children 1 2>&1 || true

# Step 2: Check if mutants directory was created
if [ ! -d "mutants/src/specify_cli" ]; then
    echo "ERROR: mutants/src/specify_cli directory not found"
    exit 1
fi

echo "Step 2: Copying non-mutated modules..."

# Copy all top-level .py files from specify_cli
for f in src/specify_cli/*.py; do
    if [ -f "$f" ]; then
        cp "$f" "mutants/src/specify_cli/" 2>/dev/null || true
    fi
done

# Copy all non-mutated subdirectories.
# Exclude directories listed in [tool.mutmut] paths_to_mutate (pyproject.toml)
# so we don't clobber generated mutant content with the original source.
# Mutated modules: status, glossary, merge, core
for d in src/specify_cli/*/; do
    dirname=$(basename "$d")
    if [ "$dirname" != "status" ] && \
       [ "$dirname" != "glossary" ] && \
       [ "$dirname" != "merge" ] && \
       [ "$dirname" != "core" ] && \
       [ "$dirname" != "__pycache__" ]; then
        cp -r "$d" "mutants/src/specify_cli/" 2>/dev/null || true
    fi
done

echo "Step 3: Verifying environment..."

# Verify frontmatter.py was copied
if [ ! -f "mutants/src/specify_cli/frontmatter.py" ]; then
    echo "ERROR: frontmatter.py was not copied"
    exit 1
fi

# Verify doctrine was copied
if [ ! -d "mutants/src/doctrine" ]; then
    echo "ERROR: doctrine directory was not copied"
    exit 1
fi

echo "✅ Environment prepared successfully!"
echo ""
echo "Now you can run mutmut with full capacity:"
echo "  mutmut run --max-children 4"
echo ""
echo "Or continue the interrupted run:"
echo "  cd mutants && mutmut run --max-children 4"

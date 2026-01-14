#!/bin/bash
# Convert existing worktrees from symlink to sparse-checkout

set -e

# Find repo root from current working directory (not script location)
# This allows the script to be run on ANY project, not just the spec-kitty repo
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "${REPO_ROOT}" ]; then
    echo "Error: Not inside a git repository"
    echo "Run this script from within your project directory"
    exit 1
fi
WORKTREES_DIR="${REPO_ROOT}/.worktrees"

if [ ! -d "${WORKTREES_DIR}" ]; then
    echo "No .worktrees directory found"
    exit 0
fi

echo "Converting worktrees to sparse-checkout (excludes kitty-specs/)..."
echo

for worktree in "${WORKTREES_DIR}"/*; do
    if [ ! -d "${worktree}" ]; then
        continue
    fi

    worktree_name=$(basename "${worktree}")
    kitty_specs_path="${worktree}/kitty-specs"

    echo "Processing: ${worktree_name}"

    # Remove symlink if present (will be replaced by sparse-checkout exclusion)
    if [ -L "${kitty_specs_path}" ]; then
        echo "  → Removing symlink"
        rm "${kitty_specs_path}"
    elif [ -d "${kitty_specs_path}" ]; then
        if [ -n "$(ls -A "${kitty_specs_path}")" ]; then
            echo "  → kitty-specs/ has contents (will be removed by sparse-checkout)"
        else
            echo "  → Removing empty directory"
            rmdir "${kitty_specs_path}"
        fi
    fi

    # Keep .gitignore entry for kitty-specs/ (prevents manual git add)
    # Sparse-checkout only controls checkout, not staging - .gitignore is needed too
    gitignore_file="${worktree}/.gitignore"
    if [ -f "${gitignore_file}" ]; then
        if ! grep -q "^kitty-specs/$" "${gitignore_file}"; then
            echo "  → Adding kitty-specs/ to .gitignore"
            echo "" >> "${gitignore_file}"
            echo "# Prevent worktree-local kitty-specs/ (status managed in main repo)" >> "${gitignore_file}"
            echo "kitty-specs/" >> "${gitignore_file}"
        fi
    else
        echo "  → Creating .gitignore with kitty-specs/ entry"
        echo "# Prevent worktree-local kitty-specs/ (status managed in main repo)" > "${gitignore_file}"
        echo "kitty-specs/" >> "${gitignore_file}"
    fi

    # Configure sparse-checkout (non-cone mode for exclusion patterns)
    cd "${worktree}"
    
    # Get sparse-checkout file path
    sparse_checkout_file="$(git -C "${worktree}" rev-parse --git-path info/sparse-checkout 2>/dev/null)"
    if [ -z "${sparse_checkout_file}" ]; then
        echo "  ⚠️  Unable to locate sparse-checkout file; skipping"
        echo
        continue
    fi

    echo "  → Configuring sparse-checkout"
    
    # Init sparse-checkout (non-cone mode for exclusion patterns)
    git config core.sparseCheckout true
    git config core.sparseCheckoutCone false

    # Write patterns: include everything except kitty-specs/
    mkdir -p "$(dirname "${sparse_checkout_file}")"
    cat > "${sparse_checkout_file}" <<EOF
/*
!/kitty-specs/
!/kitty-specs/**
EOF

    # Apply sparse-checkout
    if ! git read-tree -mu HEAD >/dev/null 2>&1; then
        echo "  ⚠️  Failed to apply sparse-checkout patterns"
    fi

    if [ ! -e "${kitty_specs_path}" ]; then
        echo "  ✓ kitty-specs/ excluded (agents read from main)"
    else
        echo "  ⚠️  kitty-specs/ still exists"
    fi

    echo
done

echo "✓ All worktrees converted to sparse-checkout"
echo
echo "RESULT: Native git solution, clean merges, jujutsu-aligned"

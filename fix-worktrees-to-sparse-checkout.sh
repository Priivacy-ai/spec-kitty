#!/bin/bash
# Convert existing worktrees from symlink to sparse-checkout

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null)"
if [ -z "${REPO_ROOT}" ]; then
    echo "Error: Not inside a git repository"
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

    # Remove symlink/directory if present
    if [ -L "${kitty_specs_path}" ]; then
        echo "  → Removing symlink"
        rm "${kitty_specs_path}"
    elif [ -d "${kitty_specs_path}" ]; then
        if [ -n "$(ls -A "${kitty_specs_path}")" ]; then
            echo "  ⚠️  kitty-specs/ is a real directory with contents; skipping to avoid data loss"
            echo
            continue
        fi
        echo "  → Removing empty directory"
        rmdir "${kitty_specs_path}"
    fi

    # Clean .gitignore
    gitignore_file="${worktree}/.gitignore"
    if [ -f "${gitignore_file}" ] && grep -q "kitty-specs" "${gitignore_file}"; then
        echo "  → Cleaning .gitignore"
        grep -v "kitty-specs" "${gitignore_file}" | \
        grep -v "Ignore kitty-specs" | \
        grep -v "status managed in main" > "${gitignore_file}.tmp"
        mv "${gitignore_file}.tmp" "${gitignore_file}"
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

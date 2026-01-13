#!/bin/bash
# Convert existing worktrees from symlink to sparse-checkout

set -e

REPO_ROOT="/Users/robert/Code/spec-kitty"
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
        echo "  → Removing directory"
        rm -rf "${kitty_specs_path}"
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
    
    # Get git dir path
    gitdir=$(cat .git | cut -d' ' -f2)
    sparse_checkout_file="${gitdir}/info/sparse-checkout"

    echo "  → Configuring sparse-checkout"
    
    # Init sparse-checkout (non-cone mode)
    git config core.sparseCheckout true

    # Write patterns: include everything except kitty-specs/
    mkdir -p "$(dirname "${sparse_checkout_file}")"
    cat > "${sparse_checkout_file}" <<EOF
/*
!/kitty-specs/
EOF

    # Apply sparse-checkout
    git read-tree -mu HEAD >/dev/null 2>&1

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

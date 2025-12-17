#!/usr/bin/env bash

set -e

JSON_MODE=false
FEATURE_NAME=""
MISSION=""
ARGS=()

while [ "$#" -gt 0 ]; do
    case "$1" in
        --json)
            JSON_MODE=true
            ;;
        --feature-name=*)
            FEATURE_NAME="${1#*=}"
            ;;
        --feature-name)
            shift
            if [ -z "${1:-}" ]; then
                echo "Error: --feature-name requires a value" >&2
                exit 1
            fi
            FEATURE_NAME="$1"
            ;;
        --mission=*)
            MISSION="${1#*=}"
            ;;
        --mission)
            shift
            if [ -z "${1:-}" ]; then
                echo "Error: --mission requires a value" >&2
                exit 1
            fi
            MISSION="$1"
            ;;
        --help|-h)
            echo "Usage: $0 [--json] [--feature-name \"Friendly Title\"] [--mission <key>] <feature_description>"
            echo ""
            echo "Options:"
            echo "  --json              Output JSON format for script consumption"
            echo "  --feature-name      Friendly title for the feature"
            echo "  --mission           Mission key (e.g., software-dev, research)"
            echo "                      If not specified, no mission is set in meta.json"
            exit 0
            ;;
        *)
            ARGS+=("$1")
            ;;
    esac
    shift
done

FEATURE_DESCRIPTION="${ARGS[*]}"
if [ -z "$FEATURE_DESCRIPTION" ]; then
    cat >&2 <<'EOF'
[spec-kitty] Error: Feature description missing.
This script must only run after the discovery interview produces a confirmed intent summary.
Return WAITING_FOR_DISCOVERY_INPUT, gather the answers, then invoke the script with the finalized description.
EOF
    exit 1
fi

# Function to find the repository root by searching for existing project markers
find_repo_root() {
    local dir="$1"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.git" ] || [ -d "$dir/.kittify" ]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# Resolve repository root. Prefer git information when available, but fall back
# to searching for repository markers so the workflow still functions in repositories that
# were initialised with --no-git.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if git rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_ROOT=$(git rev-parse --show-toplevel)
    HAS_GIT=true
else
    REPO_ROOT="$(find_repo_root "$SCRIPT_DIR")"
    if [ -z "$REPO_ROOT" ]; then
        echo "Error: Could not determine repository root. Please run this script from within the repository." >&2
        exit 1
    fi
    HAS_GIT=false
fi

# Validate mission if provided
if [ -n "$MISSION" ]; then
    MISSION_DIR="$REPO_ROOT/.kittify/missions/$MISSION"
    if [ ! -f "$MISSION_DIR/mission.yaml" ]; then
        echo "Error: Mission '$MISSION' not found" >&2
        echo "Available missions:" >&2
        for m in "$REPO_ROOT/.kittify/missions"/*/mission.yaml; do
            [ -f "$m" ] && echo "  - $(basename "$(dirname "$m")")" >&2
        done
        exit 1
    fi
fi

trim() {
    local trimmed="$1"
    trimmed="${trimmed#"${trimmed%%[![:space:]]*}"}"
    trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
    echo "$trimmed"
}

slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//'
}

# Find highest feature number from BOTH kitty-specs/ AND .worktrees/
# This ensures we don't reuse numbers when features exist in worktrees
SPECS_DIR_BASE="$REPO_ROOT/kitty-specs"
WORKTREES_DIR="$REPO_ROOT/.worktrees"
HIGHEST=0

# Scan kitty-specs/ for feature numbers
if [ -d "$SPECS_DIR_BASE" ]; then
    for dir in "$SPECS_DIR_BASE"/*; do
        [ -d "$dir" ] || continue
        dirname=$(basename "$dir")
        number=$(echo "$dirname" | grep -o '^[0-9]\+' || echo "0")
        number=$((10#$number))
        if [ "$number" -gt "$HIGHEST" ]; then HIGHEST=$number; fi
    done
fi

# Also scan .worktrees/ for feature numbers (worktree names = branch names = feature numbers)
if [ -d "$WORKTREES_DIR" ]; then
    for dir in "$WORKTREES_DIR"/*; do
        [ -d "$dir" ] || continue
        dirname=$(basename "$dir")
        number=$(echo "$dirname" | grep -o '^[0-9]\+' || echo "0")
        number=$((10#$number))
        if [ "$number" -gt "$HIGHEST" ]; then HIGHEST=$number; fi
    done
fi

NEXT=$((HIGHEST + 1))
FEATURE_NUM=$(printf "%03d" "$NEXT")

FRIENDLY_NAME="$(trim "${FEATURE_NAME:-}")"
if [ -z "$FRIENDLY_NAME" ]; then
    FRIENDLY_NAME="$(trim "$FEATURE_DESCRIPTION")"
fi

SLUG_SOURCE=$(slugify "$FRIENDLY_NAME")
if [ -z "$SLUG_SOURCE" ]; then
    SLUG_SOURCE=$(slugify "$FEATURE_DESCRIPTION")
fi

WORDS=$(echo "$SLUG_SOURCE" | tr '-' '\n' | grep -v '^$' | head -3 | tr '\n' '-' | sed 's/-$//')
if [ -z "$WORDS" ]; then
    WORDS="feature"
fi

BRANCH_NAME="${FEATURE_NUM}-${WORDS}"

WORKTREE_NOTE=""
TARGET_ROOT="$REPO_ROOT"
WORKTREE_CREATED=false
GIT_ENABLED=true
FEATURE_EXISTS=false

if [ "$HAS_GIT" = true ]; then
    case "$REPO_ROOT" in
        */.worktrees/*) SKIP_WORKTREE_CREATION=true ;;
        *) SKIP_WORKTREE_CREATION=false ;;
    esac

    if [ "$SKIP_WORKTREE_CREATION" != "true" ]; then
        if git worktree list >/dev/null 2>&1; then
            GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || true)
            if [ -n "$GIT_COMMON_DIR" ]; then
                PRIMARY_REPO_ROOT="$(cd "$GIT_COMMON_DIR/.." && pwd)"
            else
                PRIMARY_REPO_ROOT="$REPO_ROOT"
            fi
            WORKTREE_ROOT="$PRIMARY_REPO_ROOT/.worktrees"
            WORKTREE_PATH="$WORKTREE_ROOT/$BRANCH_NAME"
            mkdir -p "$WORKTREE_ROOT"
            if [ -d "$WORKTREE_PATH" ]; then
                if git -C "$WORKTREE_PATH" rev-parse --show-toplevel >/dev/null 2>&1; then
                    CURRENT_WORKTREE_BRANCH=$(git -C "$WORKTREE_PATH" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
                    if [ "$CURRENT_WORKTREE_BRANCH" = "$BRANCH_NAME" ] || [ "$CURRENT_WORKTREE_BRANCH" = "HEAD" ]; then
                        TARGET_ROOT="$WORKTREE_PATH"
                        WORKTREE_CREATED=true
                        WORKTREE_NOTE="$WORKTREE_PATH"
                        >&2 echo "[spec-kitty] Warning: Reusing existing worktree at $WORKTREE_PATH for $BRANCH_NAME."
                    else
                        >&2 echo "[spec-kitty] Warning: Existing worktree at $WORKTREE_PATH is checked out to $CURRENT_WORKTREE_BRANCH; skipping worktree creation."
                    fi
                else
                    >&2 echo "[spec-kitty] Warning: Worktree path $WORKTREE_PATH exists but is not a git worktree; skipping worktree creation."
                fi
            else
                if git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" >/dev/null 2>&1; then
                    TARGET_ROOT="$WORKTREE_PATH"
                    WORKTREE_CREATED=true
                    WORKTREE_NOTE="$WORKTREE_PATH"
                else
                    >&2 echo "[spec-kitty] Warning: Unable to create git worktree for $BRANCH_NAME; falling back to in-place checkout."
                fi
            fi
        else
            >&2 echo "[spec-kitty] Warning: Git worktree command unavailable; falling back to in-place checkout."
        fi
    fi

    if [ "$WORKTREE_CREATED" != "true" ]; then
        if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
            # Feature branch already exists
            FEATURE_EXISTS=true
            >&2 echo "[spec-kitty] ⚠️  Warning: Branch '$BRANCH_NAME' already exists"
            >&2 echo "[spec-kitty]    This may indicate you're recreating an existing feature."
            >&2 echo "[spec-kitty]    Existing feature specs may be overwritten."

            if ! git checkout "$BRANCH_NAME"; then
                >&2 echo "[spec-kitty] Error: Failed to check out existing branch $BRANCH_NAME"
                exit 1
            fi
        else
            if ! git checkout -b "$BRANCH_NAME"; then
                >&2 echo "[spec-kitty] Error: Failed to create branch $BRANCH_NAME"
                exit 1
            fi
        fi
    fi
else
    >&2 echo "[spec-kitty] ⚠️  Warning: Git repository not detected"
    >&2 echo "[spec-kitty]    Feature branch '$BRANCH_NAME' will NOT be created"
    >&2 echo "[spec-kitty]    Version control disabled for this feature"
    GIT_ENABLED=false
fi

# SHARED CONSTITUTION VIA SYMLINK
# Worktrees use relative symlinks to share the main repo's constitution.
# This ensures all feature branches follow the same project principles.
#
# Structure:
#   Main repo: /path/to/repo/.kittify/memory/constitution.md
#   Worktree:  /path/to/repo/.worktrees/001-feature/.kittify/memory -> ../../../.kittify/memory
#
# Benefits:
#   - Single source of truth for constitution
#   - Changes immediately visible in all worktrees
#   - Works even if repository is moved (relative path)
if [ "$WORKTREE_CREATED" = "true" ]; then
    WORKTREE_KITTIFY_DIR="$WORKTREE_PATH/.kittify"
    WORKTREE_MEMORY_DIR="$WORKTREE_KITTIFY_DIR/memory"

    # Calculate relative path from worktree to main repo
    # Worktree: .worktrees/001-feature/.kittify/memory
    # Main:     .kittify/memory
    # Relative: ../../../.kittify/memory
    RELATIVE_MEMORY_PATH="../../../.kittify/memory"

    # Remove copied memory directory if it exists
    if [ -d "$WORKTREE_MEMORY_DIR" ]; then
        rm -rf "$WORKTREE_MEMORY_DIR"
    fi

    # Ensure parent directory exists
    mkdir -p "$WORKTREE_KITTIFY_DIR"

    # Try to create relative symlink (works even if repo is moved)
    cd "$WORKTREE_KITTIFY_DIR"

    # Try symlink, fall back to copy on Windows if it fails
    if ln -s "$RELATIVE_MEMORY_PATH" memory 2>/dev/null; then
        >&2 echo "[spec-kitty] ✓ Shared constitution symlink created"
    else
        >&2 echo "[spec-kitty] Warning: Symlink failed (Windows?), using directory copy"
        if [ -d "$PRIMARY_REPO_ROOT/.kittify/memory" ]; then
            cp -r "$PRIMARY_REPO_ROOT/.kittify/memory" "$WORKTREE_MEMORY_DIR"
        fi
    fi

    # Also symlink AGENTS.md so command templates can find it
    # Relative: ../../../.kittify/AGENTS.md
    RELATIVE_AGENTS_PATH="../../../.kittify/AGENTS.md"
    if [ -f "$PRIMARY_REPO_ROOT/.kittify/AGENTS.md" ]; then
        # Remove existing AGENTS.md if present
        rm -f "$WORKTREE_KITTIFY_DIR/AGENTS.md" 2>/dev/null
        if ln -s "$RELATIVE_AGENTS_PATH" AGENTS.md 2>/dev/null; then
            >&2 echo "[spec-kitty] ✓ Shared AGENTS.md symlink created"
        else
            >&2 echo "[spec-kitty] Warning: AGENTS.md symlink failed, using file copy"
            cp "$PRIMARY_REPO_ROOT/.kittify/AGENTS.md" "$WORKTREE_KITTIFY_DIR/AGENTS.md"
        fi
    fi

    cd - >/dev/null
fi

REPO_ROOT="$TARGET_ROOT"
cd "$REPO_ROOT"

SPECS_DIR="$REPO_ROOT/kitty-specs"
mkdir -p "$SPECS_DIR"

FEATURE_DIR="$SPECS_DIR/$BRANCH_NAME"

# Check if feature already exists (specs directory already present)
if [ -d "$FEATURE_DIR" ]; then
    if [ ! "$FEATURE_EXISTS" = "true" ]; then
        FEATURE_EXISTS=true
        >&2 echo "[spec-kitty] ⚠️  Warning: Feature directory already exists at $FEATURE_DIR"
        >&2 echo "[spec-kitty]    Existing feature specs may be overwritten."
    fi
fi

mkdir -p "$FEATURE_DIR"

# Scaffold tasks directory structure (flat structure with frontmatter lanes)
# This guides agents to use the correct structure when /spec-kitty.tasks runs
TASKS_DIR="$FEATURE_DIR/tasks"
mkdir -p "$TASKS_DIR"
touch "$TASKS_DIR/.gitkeep"

# Create README with frontmatter format reference
cat > "$TASKS_DIR/README.md" <<'TASKS_README'
# Tasks Directory

This directory contains work package (WP) prompt files with lane status in frontmatter.

## Directory Structure (v0.9.0+)

```
tasks/
├── WP01-setup-infrastructure.md
├── WP02-user-authentication.md
├── WP03-api-endpoints.md
└── README.md
```

All WP files are stored **FLAT** in `tasks/`. The lane (planned, doing, for_review, done) is stored in the YAML frontmatter `lane:` field.

⚠️  **CRITICAL: NO SUBDIRECTORIES ALLOWED**

**DO NOT** create subdirectories in tasks/ for organization:
- ❌ `tasks/phase-1/WP01.md` - WRONG
- ❌ `tasks/backend/WP02.md` - WRONG
- ❌ `tasks/planned/WP03.md` - WRONG (old format)
- ✅ `tasks/WP01.md` - CORRECT

Even if your plan has "Phase 1", "Phase 2", etc., all WP files go directly in `tasks/`.
Use the `phase:` frontmatter field to track phases, not directories.

## Work Package File Format

Each WP file **MUST** use YAML frontmatter:

```yaml
---
work_package_id: "WP01"
title: "Work Package Title"
lane: "planned"
subtasks:
  - "T001"
  - "T002"
phase: "Phase 1 - Setup"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-01-01T00:00:00Z"
    lane: "planned"
    agent: "system"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Work Package Title

[Content follows...]
```

## Valid Lane Values

- `planned` - Ready for implementation
- `doing` - Currently being worked on
- `for_review` - Awaiting review
- `done` - Completed

## Moving Between Lanes

Use the CLI (updates frontmatter only, no file movement):
```bash
spec-kitty tasks update <WPID> --lane <lane>
```

Or use the helper script:
```bash
.kittify/scripts/bash/tasks-move-to-lane.sh <FEATURE> <WPID> <lane>
```

## File Naming

- Format: `WP01-kebab-case-slug.md`
- Examples: `WP01-setup-infrastructure.md`, `WP02-user-auth.md`
TASKS_README

>&2 echo "[spec-kitty] ✓ Tasks directory created (flat structure with frontmatter lanes)"

SPEC_FILE="$FEATURE_DIR/spec.md"
SPEC_TEMPLATE_CANDIDATES=(
    "${MISSION_SPEC_TEMPLATE:-}"
    "$REPO_ROOT/.kittify/templates/spec-template.md"
    "$REPO_ROOT/templates/spec-template.md"
)

TEMPLATE=""
for candidate in "${SPEC_TEMPLATE_CANDIDATES[@]}"; do
    if [ -n "$candidate" ] && [ -f "$candidate" ]; then
        TEMPLATE="$candidate"
        break
    fi
done

if [ -n "$TEMPLATE" ]; then
    cp "$TEMPLATE" "$SPEC_FILE"
    echo "[spec-kitty] Copied spec template from $TEMPLATE"
else
    echo "[spec-kitty] Warning: Spec template not found for active mission; creating empty spec.md"
    touch "$SPEC_FILE"
fi

# Set the SPECIFY_FEATURE environment variable for the current session
export SPECIFY_FEATURE="$BRANCH_NAME"
export SPECIFY_FEATURE_NAME="$FRIENDLY_NAME"

META_FILE="$FEATURE_DIR/meta.json"
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

json_escape() {
    local str="$1"
    str=${str//\\/\\\\}
    str=${str//\"/\\\"}
    str=${str//$'\n'/\\n}
    str=${str//$'\r'/\\r}
    echo "$str"
}

FRIENDLY_JSON=$(json_escape "$FRIENDLY_NAME")
DESCRIPTION_JSON=$(json_escape "$FEATURE_DESCRIPTION")

# Build meta.json with optional mission field
if [ -n "$MISSION" ]; then
    cat > "$META_FILE" <<EOF
{
  "feature_number": "$FEATURE_NUM",
  "slug": "$BRANCH_NAME",
  "friendly_name": "$FRIENDLY_JSON",
  "source_description": "$DESCRIPTION_JSON",
  "created_at": "$timestamp",
  "mission": "$MISSION"
}
EOF
else
    cat > "$META_FILE" <<EOF
{
  "feature_number": "$FEATURE_NUM",
  "slug": "$BRANCH_NAME",
  "friendly_name": "$FRIENDLY_JSON",
  "source_description": "$DESCRIPTION_JSON",
  "created_at": "$timestamp"
}
EOF
fi

WORKTREE_JSON=$(json_escape "$WORKTREE_NOTE")

if $JSON_MODE; then
    # Build JSON with warning fields for both issues
    if [ "$FEATURE_EXISTS" = "true" ] || [ "$GIT_ENABLED" = "false" ]; then
        # Include warnings in JSON output
        WARNINGS=()
        [ "$FEATURE_EXISTS" = "true" ] && WARNINGS+=("FEATURE_ALREADY_EXISTS")
        [ "$GIT_ENABLED" = "false" ] && WARNINGS+=("GIT_DISABLED")

        printf '{"BRANCH_NAME":"%s","SPEC_FILE":"%s","FEATURE_NUM":"%s","FRIENDLY_NAME":"%s","WORKTREE_PATH":"%s","GIT_ENABLED":%s,"FEATURE_EXISTS":%s,"WARNINGS":[' \
            "$BRANCH_NAME" "$SPEC_FILE" "$FEATURE_NUM" "$FRIENDLY_JSON" "$WORKTREE_JSON" \
            "$([ "$GIT_ENABLED" = "true" ] && echo "true" || echo "false")" \
            "$([ "$FEATURE_EXISTS" = "true" ] && echo "true" || echo "false")"

        for i in "${!WARNINGS[@]}"; do
            [ "$i" -gt 0 ] && printf ","
            printf '"%s"' "${WARNINGS[$i]}"
        done
        printf ']}\n'
    else
        # Clean output when no issues
        printf '{"BRANCH_NAME":"%s","SPEC_FILE":"%s","FEATURE_NUM":"%s","FRIENDLY_NAME":"%s","WORKTREE_PATH":"%s","GIT_ENABLED":true,"FEATURE_EXISTS":false,"WARNINGS":[]}\n' \
            "$BRANCH_NAME" "$SPEC_FILE" "$FEATURE_NUM" "$FRIENDLY_JSON" "$WORKTREE_JSON"
    fi
else
    echo "BRANCH_NAME: $BRANCH_NAME"
    echo "SPEC_FILE: $SPEC_FILE"
    echo "FEATURE_NUM: $FEATURE_NUM"
    echo "FRIENDLY_NAME: $FRIENDLY_NAME"
    echo "SPECIFY_FEATURE environment variable set to: $BRANCH_NAME"
    echo "SPECIFY_FEATURE_NAME environment variable set to: $FRIENDLY_NAME"

    # Show warnings prominently in human-readable output
    if [ "$FEATURE_EXISTS" = "true" ] || [ "$GIT_ENABLED" = "false" ]; then
        echo ""
        echo "⚠️  WARNINGS:"
        [ "$FEATURE_EXISTS" = "true" ] && echo "  • Feature branch already exists - you may be overwriting previous work"
        [ "$GIT_ENABLED" = "false" ] && echo "  • Git is disabled - branch not created, version control unavailable"
        echo ""
    fi

    if [ -n "$WORKTREE_NOTE" ]; then
        echo ""
        echo "✓ Git worktree created at: $WORKTREE_NOTE"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "NEXT STEP (REQUIRED):"
        echo "  cd \"$WORKTREE_NOTE\""
        echo ""
        echo "Then continue with:"
        echo "  /spec-kitty.plan"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "When finished, remove the worktree with:"
        echo "  git worktree remove \"$WORKTREE_NOTE\""
    fi
fi

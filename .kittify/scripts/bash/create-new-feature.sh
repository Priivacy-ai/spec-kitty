#!/usr/bin/env bash

set -e

JSON_MODE=false
FEATURE_NAME=""
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
        --help|-h)
            echo "Usage: $0 [--json] [--feature-name \"Friendly Title\"] <feature_description>"
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

trim() {
    local trimmed="$1"
    trimmed="${trimmed#"${trimmed%%[![:space:]]*}"}"
    trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
    echo "$trimmed"
}

slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//'
}

SPECS_DIR_BASE="$REPO_ROOT/kitty-specs"
HIGHEST=0
if [ -d "$SPECS_DIR_BASE" ]; then
    for dir in "$SPECS_DIR_BASE"/*; do
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
    >&2 echo "[spec-kitty] Warning: Git repository not detected; skipped branch creation for $BRANCH_NAME"
fi

REPO_ROOT="$TARGET_ROOT"
cd "$REPO_ROOT"

SPECS_DIR="$REPO_ROOT/kitty-specs"
mkdir -p "$SPECS_DIR"

FEATURE_DIR="$SPECS_DIR/$BRANCH_NAME"
mkdir -p "$FEATURE_DIR"

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

cat > "$META_FILE" <<EOF
{
  "feature_number": "$FEATURE_NUM",
  "slug": "$BRANCH_NAME",
  "friendly_name": "$FRIENDLY_JSON",
  "source_description": "$DESCRIPTION_JSON",
  "created_at": "$timestamp"
}
EOF

WORKTREE_JSON=$(json_escape "$WORKTREE_NOTE")

if $JSON_MODE; then
    printf '{"BRANCH_NAME":"%s","SPEC_FILE":"%s","FEATURE_NUM":"%s","FRIENDLY_NAME":"%s","WORKTREE_PATH":"%s"}\n' "$BRANCH_NAME" "$SPEC_FILE" "$FEATURE_NUM" "$FRIENDLY_JSON" "$WORKTREE_JSON"
else
    echo "BRANCH_NAME: $BRANCH_NAME"
    echo "SPEC_FILE: $SPEC_FILE"
    echo "FEATURE_NUM: $FEATURE_NUM"
    echo "FRIENDLY_NAME: $FRIENDLY_NAME"
    echo "SPECIFY_FEATURE environment variable set to: $BRANCH_NAME"
    echo "SPECIFY_FEATURE_NAME environment variable set to: $FRIENDLY_NAME"
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

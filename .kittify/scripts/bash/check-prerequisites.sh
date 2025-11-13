#!/usr/bin/env bash

# Consolidated prerequisite checking script
#
# This script provides unified prerequisite checking for Spec-Driven Development workflow.
# It replaces the functionality previously spread across multiple scripts.
#
# Usage: ./check-prerequisites.sh [OPTIONS]
#
# OPTIONS:
#   --json              Output in JSON format
#   --require-tasks     Require tasks.md to exist (for implementation phase)
#   --include-tasks     Include tasks.md in AVAILABLE_DOCS list
#   --paths-only        Only output path variables (no validation)
#   --help, -h          Show help message
#
# OUTPUTS:
#   JSON mode: {"FEATURE_DIR":"...", "AVAILABLE_DOCS":["..."]}
#   Text mode: FEATURE_DIR:... \n AVAILABLE_DOCS: \n ✓/✗ file.md
#   Paths only: REPO_ROOT: ... \n BRANCH: ... \n FEATURE_DIR: ... etc.

set -e

# Script: check-prerequisites.sh
# Purpose: Validate feature structure and prerequisites for spec workflow
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation)

# Source common functions first
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Initialize variables
REQUIRE_TASKS=false
INCLUDE_TASKS=false
PATHS_ONLY=false

# Handle common flags (--help, --json, --quiet, --dry-run)
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

# Parse custom arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --require-tasks)
            REQUIRE_TASKS=true
            shift
            ;;
        --include-tasks)
            INCLUDE_TASKS=true
            shift
            ;;
        --paths-only)
            PATHS_ONLY=true
            shift
            ;;
        *)
            show_log "❌ ERROR: Unknown option '$1'"
            show_script_help "$(basename "$0")" \
                "Consolidated prerequisite checking for Spec-Driven Development workflow" \
                "--require-tasks" "Require tasks.md to exist (for implementation phase)" \
                "--include-tasks" "Include tasks.md in AVAILABLE_DOCS list" \
                "--paths-only" "Only output path variables (no prerequisite validation)"
            exit $EXIT_USAGE_ERROR
            ;;
    esac
done

if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Consolidated prerequisite checking for Spec-Driven Development workflow" \
        "--require-tasks" "Require tasks.md to exist (for implementation phase)" \
        "--include-tasks" "Include tasks.md in AVAILABLE_DOCS list" \
        "--paths-only" "Only output path variables (no prerequisite validation)"
    exit $EXIT_SUCCESS
fi

# Auto-switch to the most recent feature worktree when invoked from main or an
# ambiguous location. This keeps downstream commands from thrashing while they
# try to discover the right context.
if [[ -z "${SPEC_KITTY_AUTORETRY:-}" ]]; then
    repo_root=$(get_repo_root)
    current_branch=$(get_current_branch)
    if [[ ! "$current_branch" =~ ^[0-9]{3}- ]]; then
        if latest_worktree=$(find_latest_feature_worktree "$repo_root" 2>/dev/null); then
            if [[ -d "$latest_worktree" ]]; then
                >&2 echo "[spec-kitty] Auto-running prerequisites inside $latest_worktree (current branch: $current_branch)"
                (
                    cd "$latest_worktree" && \
                    SPEC_KITTY_AUTORETRY=1 "$SCRIPT_DIR/check-prerequisites.sh" "$@"
                )
                exit $?
            fi
        fi
    fi
fi

# Get feature paths and validate branch
eval $(get_feature_paths)
check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1

# If paths-only mode, output paths and exit (support JSON + paths-only combined)
if $PATHS_ONLY; then
    if $JSON_MODE; then
        # Minimal JSON paths payload (no validation performed)
        printf '{"REPO_ROOT":"%s","BRANCH":"%s","FEATURE_DIR":"%s","FEATURE_SPEC":"%s","IMPL_PLAN":"%s","TASKS":"%s"}\n' \
            "$REPO_ROOT" "$CURRENT_BRANCH" "$FEATURE_DIR" "$FEATURE_SPEC" "$IMPL_PLAN" "$TASKS"
    else
        echo "REPO_ROOT: $REPO_ROOT"
        echo "BRANCH: $CURRENT_BRANCH"
        echo "FEATURE_DIR: $FEATURE_DIR"
        echo "FEATURE_SPEC: $FEATURE_SPEC"
        echo "IMPL_PLAN: $IMPL_PLAN"
        echo "TASKS: $TASKS"
    fi
    exit 0
fi

# Validate required directories and files
if [[ ! -d "$FEATURE_DIR" ]]; then
    show_log "❌ ERROR: Feature directory not found: $FEATURE_DIR"
    show_log "Run /spec-kitty.specify first to create the feature structure."
    exit $EXIT_VALIDATION_ERROR
fi

if [[ ! -f "$IMPL_PLAN" ]]; then
    show_log "❌ ERROR: plan.md not found in $FEATURE_DIR"
    show_log "Run /spec-kitty.plan first to create the implementation plan."
    exit $EXIT_VALIDATION_ERROR
fi

# Validate that plan.md has been filled out (not just template)
# Check for common template markers that should be replaced
template_markers=(
    '\[FEATURE\]'
    '\[###-feature-name\]'
    '\[DATE\]'
    'ACTION REQUIRED: Replace the content'
    '\[e.g., Python 3.11'
    'or NEEDS CLARIFICATION'
    '# \[REMOVE IF UNUSED\]'
    '\[Gates determined based on constitution file\]'
)

marker_count=0
for marker in "${template_markers[@]}"; do
    if grep -qE "$marker" "$IMPL_PLAN" 2>/dev/null; then
        ((marker_count++)) || true
    fi
done

# If 5 or more template markers are still present, plan is unfilled
if [[ $marker_count -ge 5 ]]; then
    show_log "❌ ERROR: plan.md appears to be unfilled (still in template form)"
    show_log "Found $marker_count template markers that need to be replaced."
    show_log ""
    show_log "Please complete the /spec-kitty.plan workflow:"
    show_log "  1. Fill in [FEATURE], [DATE], and technical context placeholders"
    show_log "  2. Replace 'NEEDS CLARIFICATION' with actual values"
    show_log "  3. Remove [REMOVE IF UNUSED] sections and choose your project structure"
    show_log "  4. Replace [Gates determined...] with actual constitution checks"
    show_log ""
    show_log "Then run this command again."
    exit $EXIT_VALIDATION_ERROR
fi

# Check for tasks.md if required
if $REQUIRE_TASKS && [[ ! -f "$TASKS" ]]; then
    show_log "❌ ERROR: tasks.md not found in $FEATURE_DIR"
    show_log "Run /spec-kitty.tasks first to create the task list."
    exit $EXIT_VALIDATION_ERROR
fi

# Build list of available documents
docs=()

# Always check these optional docs
[[ -f "$RESEARCH" ]] && docs+=("research.md")
[[ -f "$DATA_MODEL" ]] && docs+=("data-model.md")

# Check contracts directory (only if it exists and has files)
if [[ -d "$CONTRACTS_DIR" ]] && [[ -n "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]]; then
    docs+=("contracts/")
fi

[[ -f "$QUICKSTART" ]] && docs+=("quickstart.md")

# Include tasks.md if requested and it exists
if $INCLUDE_TASKS && [[ -f "$TASKS" ]]; then
    docs+=("tasks.md")
fi

# Output results (Issue #1: JSON to stdout, logs to stderr)
if [[ "$JSON_OUTPUT" == true ]]; then
    # Build JSON array of documents
    if [[ ${#docs[@]} -eq 0 ]]; then
        json_docs="[]"
    else
        json_docs=$(printf '"%s",' "${docs[@]}")
        json_docs="[${json_docs%,}]"
    fi

    printf '{"FEATURE_DIR":"%s","AVAILABLE_DOCS":%s}\n' "$FEATURE_DIR" "$json_docs"
else
    # Text output
    if ! is_quiet; then
        show_log "✓ Prerequisites validated"
        show_log "FEATURE_DIR: $FEATURE_DIR"
        show_log "AVAILABLE_DOCS:"

        # Show status of each potential document
        check_file "$RESEARCH" "  research.md"
        check_file "$DATA_MODEL" "  data-model.md"
        check_dir "$CONTRACTS_DIR" "  contracts/"
        check_file "$QUICKSTART" "  quickstart.md"

        if $INCLUDE_TASKS; then
            check_file "$TASKS" "  tasks.md"
        fi
    fi
fi

exit $EXIT_SUCCESS

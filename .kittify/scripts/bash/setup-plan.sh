#!/usr/bin/env bash

# Script: setup-plan.sh
# Purpose: Setup plan phase for feature development
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation)

set -e

# Get script directory and load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

# Handle common flags (--help, --json, --quiet, --dry-run)
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Setup implementation plan for feature development"
    exit $EXIT_SUCCESS
fi

# Get all paths and variables from common functions
eval $(get_feature_paths)

# Check if we're on a proper feature branch (only for git repos)
check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1

# Ensure the feature directory exists
mkdir -p "$FEATURE_DIR"

# Copy plan template if it exists
TEMPLATE_CANDIDATES=(
    "${MISSION_PLAN_TEMPLATE:-}"
    "$REPO_ROOT/.kittify/templates/plan-template.md"
    "$REPO_ROOT/templates/plan-template.md"
)

TEMPLATE=""
for candidate in "${TEMPLATE_CANDIDATES[@]}"; do
    if [[ -n "$candidate" && -f "$candidate" ]]; then
        TEMPLATE="$candidate"
        break
    fi
done

if [[ -n "$TEMPLATE" ]]; then
    cp "$TEMPLATE" "$IMPL_PLAN"
    if ! is_quiet; then
        show_log "✓ Copied plan template (source: $TEMPLATE)"
    fi
else
    show_log "⚠️  Warning: Plan template not found; using empty plan"
    touch "$IMPL_PLAN"
fi

# Output results (Issue #1: JSON to stdout, logs to stderr)
if [[ "$JSON_OUTPUT" == true ]]; then
    output_json \
        "FEATURE_SPEC" "$FEATURE_SPEC" \
        "IMPL_PLAN" "$IMPL_PLAN" \
        "SPECS_DIR" "$FEATURE_DIR" \
        "BRANCH" "$CURRENT_BRANCH" \
        "HAS_GIT" "$HAS_GIT"
else
    if ! is_quiet; then
        show_log "Plan setup complete"
        show_log "  FEATURE_SPEC: $FEATURE_SPEC"
        show_log "  IMPL_PLAN: $IMPL_PLAN"
        show_log "  SPECS_DIR: $FEATURE_DIR"
        show_log "  BRANCH: $CURRENT_BRANCH"
    fi
fi

exit $EXIT_SUCCESS

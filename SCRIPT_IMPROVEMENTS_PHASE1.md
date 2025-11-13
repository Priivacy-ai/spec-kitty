# Script UX Improvements - Phase 1 Implementation Guide

**Status**: Foundation Complete ✅ | Script Application In Progress
**Commit**: d5bab73 (Foundation utilities)
**Date**: 2025-11-13

## Overview

Phase 1 implements fixes for 5 critical UX issues discovered in script execution testing. This guide provides the blueprint for updating all remaining bash scripts.

## What Was Completed

### Foundation Utilities (common.sh)

The following functions are now available for all scripts to use:

#### Exit Codes (Issue #5: Consistent Error Codes)
```bash
EXIT_SUCCESS=0              # Success
EXIT_USAGE_ERROR=1          # Missing or invalid arguments
EXIT_VALIDATION_ERROR=2     # Input validation failed
EXIT_EXECUTION_ERROR=3      # Command execution failed
EXIT_PRECONDITION_ERROR=4   # Precondition not met (e.g., not in git repo)
```

#### Logging Functions (Issue #1: Separate Output Streams)
```bash
show_log "message"                    # Log to stderr with [spec-kitty] prefix
show_log_timestamped "message"        # Log with timestamp to stderr
is_quiet                              # Check if --quiet flag was set
```

#### JSON Output (Issue #1: Separate Output Streams)
```bash
output_json "key1" "value1" "key2" "value2"
# Outputs to stdout: {"key1":"value1","key2":"value2"}
# Properly escapes special characters
```

#### Validation Functions (Issue #5: Input Validation)
```bash
validate_feature_exists "feature-slug"        # Check if feature exists
validate_feature_dir_exists "/path/to/dir"    # Check feature directory structure
validate_tasks_file_exists "/path/to/dir"     # Check for tasks.md
validate_arg_provided "$value" "arg_name"     # Validate argument provided
validate_in_git_repo                          # Check we're in git repo
```

#### Flag Handling (Issue #4: Standardized --help)
```bash
handle_common_flags "$@"          # Parse --help, --json, --quiet, --dry-run
# Sets: SHOW_HELP, JSON_OUTPUT, QUIET_MODE, DRY_RUN, REMAINING_ARGS

show_script_help "script.sh" \
    "Description of what script does" \
    "arg1_name" "Argument description" \
    "arg2_name" "Another argument"    # Display help text
```

#### Execution Support
```bash
exec_cmd "command" "arg1" "arg2"  # Execute with dry-run support
```

## Template: How to Update a Script

### Example: Before and After

**BEFORE** (Mixed streams, no validation, no --help):
```bash
#!/bin/bash

set -e

if [ -z "$1" ]; then
    echo "Error: Feature required" >&2
    exit 1
fi

if [ "$1" = "--help" ]; then
    echo "Usage: script.sh <feature>"
    exit 0
fi

echo "[spec-kitty] Processing feature $1"
# ... actual work ...
printf '{"status":"done"}\n'
```

**AFTER** (Using Phase 1 utilities):
```bash
#!/usr/bin/env bash

# Script: example-script.sh
# Purpose: Do something useful
# Issues Fixed: #1 (separate streams), #4 (standardized --help), #5 (validation)

set -e

# Source common functions (CRITICAL)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Handle common flags early (--help, --json, --quiet, --dry-run)
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

# Show help if requested
if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Do something useful with a feature" \
        "feature_slug" "Feature identifier (e.g., 001-my-feature)"
    exit $EXIT_SUCCESS
fi

# Validate required arguments (returns EXIT_USAGE_ERROR if missing)
if ! validate_arg_provided "${1:-}" "feature_slug"; then
    exit $EXIT_USAGE_ERROR
fi

FEATURE_SLUG="$1"

# Validate feature exists (returns EXIT_VALIDATION_ERROR if not found)
if ! validate_feature_exists "$FEATURE_SLUG"; then
    exit $EXIT_VALIDATION_ERROR
fi

# Log to stderr (won't interfere with JSON output)
if ! is_quiet; then
    show_log "Processing feature $FEATURE_SLUG"
fi

# ... actual work ...

# Output to stdout (with proper separation from logs)
if [[ "$JSON_OUTPUT" == true ]]; then
    output_json "status" "done" "feature" "$FEATURE_SLUG"
else
    if ! is_quiet; then
        show_log "✓ Feature processed successfully"
    fi
fi

exit $EXIT_SUCCESS
```

## Step-by-Step Update Checklist

For each bash script, apply these changes:

### 1. Add Header Comment (Lines 1-5)
```bash
#!/usr/bin/env bash

# Script: script-name.sh
# Purpose: What this script does
# Issues Fixed: #1, #4, #5 (or whichever apply)
```

### 2. Add Common.sh Source (After shebang, before set -e)
```bash
set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
```

### 3. Add Flag Handling (After sourcing common.sh)
```bash
# Handle common flags (--help, --json, --quiet, --dry-run)
handle_common_flags "$@"
set -- "${REMAINING_ARGS[@]}"

if [[ "$SHOW_HELP" == true ]]; then
    show_script_help "$(basename "$0")" \
        "Script description here" \
        "arg1" "Argument 1 description" \
        "arg2" "Argument 2 description"
    exit $EXIT_SUCCESS
fi
```

### 4. Replace All Log Output
**Before**: `echo "[spec-kitty] Message"` or `echo "Message" >&2`
**After**: `show_log "Message"` (automatically goes to stderr)

**Before**: `echo "Message"` (human-readable output)
**After**: `if ! is_quiet; then show_log "Message"; fi`

### 5. Replace JSON Output
**Before**: `printf '{"key":"value"}\n'`
**After**: `output_json "key" "value"`

### 6. Add Input Validation
**Before**: Check arguments manually with if statements
**After**: Use validation functions
```bash
if ! validate_arg_provided "${1:-}" "arg_name"; then
    exit $EXIT_USAGE_ERROR
fi

if ! validate_feature_exists "$FEATURE_SLUG"; then
    exit $EXIT_VALIDATION_ERROR
fi
```

### 7. Use Proper Exit Codes
**Before**: `exit 0`, `exit 1`, etc.
**After**: `exit $EXIT_SUCCESS`, `exit $EXIT_VALIDATION_ERROR`, etc.

### 8. Respect --quiet and --json Flags
```bash
# For logs (only show if not quiet)
if ! is_quiet; then
    show_log "Processing..."
fi

# For JSON output
if [[ "$JSON_OUTPUT" == true ]]; then
    output_json "key" "value"
else
    # Human-readable output
    show_log "Done"
fi
```

## Scripts Requiring Updates

**Priority 1** (Core workflow - update first):
1. ✅ `create-new-feature.sh` - DONE (example template)
2. `setup-plan.sh`
3. `setup-sandbox.sh`
4. `move-task-to-doing.sh`
5. `mark-task-status.sh`

**Priority 2** (Supporting scripts):
6. `accept-feature.sh`
7. `merge-feature.sh`
8. `refresh-kittify-tasks.sh`
9. `tasks-add-history-entry.sh`
10. `tasks-move-to-lane.sh`
11. `tasks-list-lanes.sh`
12. `tasks-rollback-move.sh`
13. `validate-task-workflow.sh`
14. `update-agent-context.sh`

**Note**: `check-prerequisites.sh` already sources common.sh and uses --json, needs minor cleanup

## Testing Checklist

After updating each script, test:

```bash
# Test 1: Help output
./.kittify/scripts/bash/script-name.sh --help

# Test 2: Validation (should fail with exit code 2)
./.kittify/scripts/bash/script-name.sh
echo "Exit code: $?"

# Test 3: JSON output (should parse cleanly)
./.kittify/scripts/bash/script-name.sh --json arg | jq .

# Test 4: Quiet mode (no logs)
./.kittify/scripts/bash/script-name.sh --quiet arg | jq .

# Test 5: Dry-run (if applicable)
./.kittify/scripts/bash/script-name.sh --dry-run arg
```

## Expected Outcomes

**Before Phase 1**:
- Script tests: 10/15 passing (67%)
- JSON parsing: Requires custom workarounds
- Error messages: Inconsistent, sometimes cryptic
- Help support: Inconsistent

**After Phase 1 Complete**:
- Script tests: 15/15 passing (100%)
- JSON parsing: Standard tools work (jq, etc.)
- Error messages: Consistent, actionable format
- Help support: All scripts have --help

## Estimated Effort

- **Per script**: 15-20 minutes (following template)
- **All 14 scripts**: 3-4 hours
- **With testing**: 4-5 hours total

## Notes

- The foundation (common.sh) is complete and tested
- `create-new-feature.sh` serves as a complete working example
- All changes maintain backward compatibility
- No breaking changes to script behavior
- Exit codes enable better automation
- Logs to stderr won't break piped output

## Next Steps

1. Update Priority 1 scripts (5 scripts)
2. Update Priority 2 scripts (9 scripts)
3. Run integration tests
4. Create final commit
5. Proceed to Phase 2 (worktree documentation, context auto-detection)

---

**Related**: Findings Report: `/Users/robert/Code/spec-kitty-test/findings/2025-11-13_06_script_execution_ux_issues.md`


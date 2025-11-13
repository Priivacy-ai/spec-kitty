# Plan Validation Guardrail

## Overview

The Plan Validation Guardrail prevents AI agents (and humans) from accidentally skipping the critical planning phase by detecting when `plan.md` is still in template form and blocking progression to research or task generation.

## Problem Solved

**Scenario:** An AI agent runs `/spec-kitty.specify`, which creates a feature branch with `plan.md` scaffolded from the template. The agent then immediately jumps to `/spec-kitty.research` or `/spec-kitty.tasks` without filling in the technical architecture, dependencies, and design decisions in `plan.md`.

**Result:** The implementation proceeds without clear technical guidance, leading to:
- Inconsistent technology choices
- Missing architectural decisions
- Incomplete dependency specifications
- Poor code organization
- Rework and confusion

## Solution

Automated validation that detects unfilled `plan.md` files by checking for template markers that should have been replaced with real content.

## How It Works

### Template Markers Detected

The validation looks for these common template placeholders:

- `[FEATURE]` - Feature name placeholder
- `[###-feature-name]` - Branch name placeholder
- `[DATE]` - Date placeholder
- `[Extract from feature spec:` - Summary placeholder
- `ACTION REQUIRED: Replace the content` - Explicit action marker
- `[e.g., Python 3.11` - Example technology choices
- `or NEEDS CLARIFICATION` - Unresolved decisions
- `# [REMOVE IF UNUSED]` - Project structure options
- `[Gates determined based on constitution file]` - Constitution checks
- `[Document the selected structure` - Documentation placeholder

### Validation Threshold

If **5 or more** template markers are still present, the plan is considered unfilled.

### Where Validation Occurs

1. **`/spec-kitty.research` command** (Python)
   - Location: `src/specify_cli/cli/commands/research.py`
   - Validates before scaffolding research artifacts
   - Provides clear error message with next steps

2. **`/spec-kitty.tasks` command** (Bash)
   - Location: `.kittify/scripts/bash/check-prerequisites.sh`
   - Called by the tasks slash command during setup
   - Fails early before task generation begins

## User Experience

### When Plan is Unfilled

**Research Command:**
```
❌ Error: plan.md for feature '001-user-auth' appears to be unfilled (template form).
Found 8 template markers:
  - [FEATURE]
  - [DATE]
  - [e.g., Python 3.11
  - or NEEDS CLARIFICATION
  - # [REMOVE IF UNUSED]
  ... and 3 more

Please complete the /spec-kitty.plan workflow before proceeding to research or tasks.
The plan.md file must have technical details filled in, not just template placeholders.

Next steps:
  1. Run /spec-kitty.plan to fill in the technical architecture
  2. Complete all [FEATURE], [DATE], and technical context placeholders
  3. Remove [REMOVE IF UNUSED] sections and choose your project structure
  4. Then run /spec-kitty.research again
```

**Tasks Command:**
```
❌ ERROR: plan.md appears to be unfilled (still in template form)
Found 7 template markers that need to be replaced.

Please complete the /spec-kitty.plan workflow:
  1. Fill in [FEATURE], [DATE], and technical context placeholders
  2. Replace 'NEEDS CLARIFICATION' with actual values
  3. Remove [REMOVE IF UNUSED] sections and choose your project structure
  4. Replace [Gates determined...] with actual constitution checks

Then run this command again.
```

### When Plan is Properly Filled

Validation passes silently and the command proceeds normally.

## Implementation Files

### Python Module
**File:** `src/specify_cli/plan_validation.py`

**Functions:**
- `detect_unfilled_plan(plan_path)` - Returns (is_unfilled, list_of_markers)
- `validate_plan_filled(plan_path, feature_slug, strict)` - Raises `PlanValidationError` if unfilled

### Bash Script
**File:** `.kittify/scripts/bash/check-prerequisites.sh`

**Integration:** Lines 131-164 perform template marker detection

### Tests
**File:** `tests/test_plan_validation.py`

**Coverage:**
- Detects unfilled plans with many markers
- Passes filled plans with complete content
- Handles non-existent files gracefully
- Supports strict and lenient modes
- Validates partial marker scenarios

## Configuration

### Threshold Adjustment

To change the sensitivity, modify `MIN_MARKERS_TO_REMOVE` in:

**Python:**
```python
# src/specify_cli/plan_validation.py
MIN_MARKERS_TO_REMOVE = 5  # Increase for stricter, decrease for lenient
```

**Bash:**
```bash
# .kittify/scripts/bash/check-prerequisites.sh
if [[ $marker_count -ge 5 ]]; then  # Change threshold here
```

### Adding New Markers

**Python:**
```python
# src/specify_cli/plan_validation.py
TEMPLATE_MARKERS = [
    "[FEATURE]",
    "[DATE]",
    # Add new markers here
    "[YOUR_NEW_MARKER]",
]
```

**Bash:**
```bash
# .kittify/scripts/bash/check-prerequisites.sh
template_markers=(
    '\[FEATURE\]'
    '\[DATE\]'
    # Add new markers here (escaped for grep -E)
    '\[YOUR_NEW_MARKER\]'
)
```

## Benefits

1. **Prevents Downstream Confusion** - Forces clear technical decisions before implementation
2. **Improves Code Quality** - Ensures consistent technology choices and architecture
3. **Saves Time** - Avoids rework from missing architectural decisions
4. **Agent-Friendly** - Clear error messages guide AI agents to the correct workflow
5. **Human-Friendly** - Helps human developers remember to complete planning

## Testing

Run the validation tests:

```bash
python3.11 -m pytest tests/test_plan_validation.py -v
```

All 7 tests should pass:
- ✓ Detects unfilled plans with template markers
- ✓ Passes properly filled plans
- ✓ Handles non-existent files
- ✓ Strict mode raises errors
- ✓ Lenient mode warns
- ✓ Complete plans pass validation
- ✓ Partial markers handled correctly

## Future Enhancements

Potential improvements:
1. Add `--force` flag to bypass validation when intentional
2. Provide suggestions for filling specific missing sections
3. Integrate with IDE plugins for real-time validation
4. Add metrics tracking for plan quality
5. Generate plan quality score based on completeness

## Related Documentation

- [Spec Kitty Workflow](../README.md)
- [Planning Phase Guide](../docs/quickstart.md)
- [Context Switching for Agents](../docs/CONTEXT_SWITCHING_GUIDE.md)

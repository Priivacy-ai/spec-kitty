---
description: Perform structured code review and kanban transitions for completed task prompt files
---

## Pre-Review Validation (Issue #72)

**BEFORE reviewing, verify subtasks are complete**:
```bash
# Check tasks.md for this WP's section
grep -A 20 "## WP01" kitty-specs/###-feature/tasks.md | grep "- \[ \]"
# If any unchecked subtasks appear, DO NOT proceed with review
# Ask implementing agent to mark them complete first
```

**The system should have blocked moving to for_review with unchecked subtasks**, but if this check was bypassed with `--force`, reject the review immediately and request all subtasks be marked complete.
Only mark a subtask done after you have verified the implementation. Do not mark subtasks done just to unblock a lane move.
If the implementation is incomplete, request changes instead of marking subtasks.

Run this command to get the work package prompt and review instructions, then immediately proceed with the review steps in the workspace output (do not pause for confirmation):

```bash
spec-kitty agent workflow review $ARGUMENTS
```

During review, the workflow command will warn if dependent WPs are in progress
and may need a rebase if changes are requested.

If no WP ID is provided, it will automatically find the first work package with `lane: "for_review"` and move it to "doing" for you.

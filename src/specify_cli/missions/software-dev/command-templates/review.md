---
description: Perform structured code review and kanban transitions for completed task prompt files
---

**IMPORTANT**: After running the command below, you'll see a LONG work package prompt (~1000+ lines).

**You MUST scroll to the BOTTOM** to see the completion commands!

Run this command to get the work package prompt and review instructions:

```bash
spec-kitty agent workflow review $ARGUMENTS --agent <your-name>
```

**CRITICAL**: You MUST provide `--agent <your-name>` to track who is reviewing!

If no WP ID is provided, it will automatically find the first work package with `lane: "for_review"` and move it to "doing" for you.

**After reviewing, scroll to the bottom and run ONE of these commands**:
- ✅ Approve: `spec-kitty agent tasks move-task WP## --to done --note "Review passed: <summary>"`
- ❌ Reject: `spec-kitty agent tasks move-task WP## --to planned --review-feedback-file feedback.md`

**The Python script handles all file updates automatically - no manual editing required!**
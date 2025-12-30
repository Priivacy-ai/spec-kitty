---
description: Perform structured code review and kanban transitions for completed task prompt files
---

Run this command to get the work package prompt and review instructions:

```bash
spec-kitty agent workflow review $ARGUMENTS
```

If no WP ID is provided, it will automatically find the first work package with `lane: "for_review"` and move it to "doing" for you.

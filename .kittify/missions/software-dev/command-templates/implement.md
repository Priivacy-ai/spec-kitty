---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
---

Run this command to get your work package prompt and instructions:

```bash
spec-kitty agent workflow implement $ARGUMENTS
```

If no WP ID is provided, it will automatically find the first work package with `lane: "planned"` and move it to "doing" for you.

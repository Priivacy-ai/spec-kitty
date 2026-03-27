---
description: Perform structured code review and kanban transitions for completed task prompt files
---

## Constitution Context Bootstrap (required)

Before running workflow review, load constitution context for this action:

```bash
spec-kitty constitution context --action review --json
```

Use JSON `text` as governance context. On first load (`mode=bootstrap`), follow referenced docs as needed.

**IMPORTANT**: After running the command below, you'll see a LONG work package prompt (~1000+ lines).

**You MUST scroll to the BOTTOM** to see the completion commands!

Resolve canonical action context first.

Explicit slash-command argument from the caller (may be empty; only explicit WP IDs are supported here):

{ARGS}

If the explicit caller argument above is non-empty:

- Treat it as the required work package id for this review run.
- Forward it to `spec-kitty agent context resolve` as `--wp-id <value>`.
- Do not run the default resolver command below unchanged when an explicit WP is present.
- Do not interpret it as a prompt path in resolver-first review prompts.
- Do not rely on raw argument text appended elsewhere in the prompt for correctness.
- Example with explicit WP: `spec-kitty agent context resolve --action review --agent <your-name> --wp-id WP02 --json`
- Example without explicit WP: `spec-kitty agent context resolve --action review --agent <your-name> --json`

Default resolver command:

```bash
spec-kitty agent context resolve --action review --agent <your-name> --json
```

Then run the returned `workflow` command to get the work package prompt and
review instructions.

**CRITICAL**: You MUST provide `--agent <your-name>` to track who is reviewing!

The resolver returns the canonical WP to review. Do not rediscover context
from branch names or directory guesses inside the prompt.

## Dependency checks (required)

- dependency_check: If the WP frontmatter lists `dependencies`, confirm each dependency WP is merged to the target branch before you review this WP.
- dependent_check: Identify any WPs that list this WP as a dependency and note their current lanes.
- rebase_warning: If you request changes AND any dependents exist, warn those agents to rebase and provide a concrete command (example: `cd .worktrees/FEATURE-WP02 && git rebase FEATURE-WP01`).
- verify_instruction: Confirm dependency declarations match actual code coupling (imports, shared modules, API contracts).

**After reviewing, scroll to the bottom and run ONE of these commands**:
- ✅ Approve: `spec-kitty agent tasks move-task WP## --to approved --note "Review passed: <summary>"`
- ❌ Reject: Write feedback to the temp file path shown in the prompt, then run `spec-kitty agent tasks move-task WP## --to planned --review-feedback-file <temp-file-path>`

`approved` means review passed and merge-complete `done` will be recorded separately
once the WP branch is actually integrated into the target branch.

**The prompt will provide a unique temp file path for feedback - use that exact path to avoid conflicts with other agents!**
`move-task` will persist the feedback artifact in shared git common-dir and write a `review_feedback: "feedback://..."` pointer into the WP frontmatter.

**The Python script handles all file updates automatically - no manual editing required!**

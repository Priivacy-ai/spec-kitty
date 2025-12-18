---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
---

## User Input

```text
$ARGUMENTS
```

---

## Automatic Setup (Command Handles This)

Before showing you any instructions, this command automatically:

1. **Determines which WP to implement**:
   - If `$ARGUMENTS` is empty → Find first WP with `lane: "planned"`
   - If `$ARGUMENTS` is provided → Normalize and find matching WP
     - Accepts: `wp01`, `WP01`, `WP01-foo-bar` → All resolve to same file
     - Finds: `tasks/WP01*.md`

2. **Moves WP to doing lane**:
   ```bash
   spec-kitty agent tasks move-task <WPID> doing --note "Started implementation" --agent "<your-agent>"
   ```
   This automatically:
   - Updates `lane: "doing"` in frontmatter
   - Captures and records shell PID
   - Adds activity log entry
   - Commits the change with message: "Start <WPID>: Move to doing lane"

3. **Gets the prompt file path**:
   - Full absolute path to `tasks/WPxx-slug.md`
   - Verifies lane is now "doing"

4. **Tells you what to do** (see below)

---

## Your Job (What You Actually Do)

✅ **Work Package <WPID> is now in "doing" lane**

**Prompt file**: `<ABSOLUTE_PATH_TO_PROMPT>`

**Your workflow**:

1. **READ THE PROMPT FILE** (link above) - This is your implementation guide
2. **Check for review feedback**:
   - Look at `review_status` field in frontmatter
   - If `has_feedback` or `acknowledged` → Read `## Review Feedback` section first
   - Treat action items as your TODO list
3. **Read supporting docs**:
   - `tasks.md` - Full task breakdown
   - `plan.md` - Architecture and tech stack
   - `spec.md` - User requirements
   - `data-model.md`, `contracts/`, `research.md`, `quickstart.md` (if they exist)
4. **Implement the work** following the prompt's guidance
5. **When complete**, move to for_review:
   ```bash
   spec-kitty agent tasks move-task <WPID> for_review --note "Ready for review"
   ```
   Then commit your implementation changes.

---

## Implementation Guidelines

**Execution rules**:
- Follow the prompt's subtask order
- Respect dependencies (sequential vs parallel markers `[P]`)
- Run tests if the prompt requires them
- Update activity log in prompt file as you complete major milestones

**Error handling**:
- Report clear errors if you can't proceed
- Don't skip required steps
- If blocked, explain why and suggest next steps

**When done**:
- Move to for_review (command above)
- Commit your implementation
- Report what you completed

---

## Notes

- Shell PID, frontmatter updates, and workflow mechanics are handled automatically
- Focus on implementation, not busywork
- The prompt file is your authoritative guide
- All `$ARGUMENTS` processing happened before you saw this

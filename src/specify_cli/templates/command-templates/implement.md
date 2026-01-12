---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
---

## Work Package Selection

**User specified**: `$ARGUMENTS`

**Your task**: Determine which WP to implement:
- If `$ARGUMENTS` is empty → Find first WP file with `lane: "planned"` in `tasks/` directory
- If `$ARGUMENTS` provided → Normalize it:
  - `wp01` → `WP01`
  - `WP01` → `WP01`
  - `WP01-foo-bar` → `WP01`
  - Then find: `tasks/WP01*.md`

**Once you know which WP**, proceed to setup.

---

## Setup (Do This First)

**1. Move WP to doing lane:**
```bash
spec-kitty agent tasks move-task <WPID> --to doing --note "Started implementation" --agent "codex"
```
This updates frontmatter, captures shell PID, adds activity log, and creates a commit.

**2. Get the prompt file path:**
The WP file is at: `kitty-specs/<feature>/tasks/<WPID>-<slug>.md`
Find the full absolute path.

**3. Verify the move worked:**
```bash
git log -1  # Should show "Start <WPID>: Move to doing lane"
```

---

## Implementation (Do This Second)

**1. READ THE PROMPT FILE** (`tasks/<WPID>-slug.md`)
   - This is your complete implementation guide
   - Check `review_status` in frontmatter:
     - If `has_feedback` → Read `## Review Feedback` section first
     - Treat action items as your TODO list

**2. Read supporting docs:**
   - `tasks.md` - Full task breakdown
   - `plan.md` - Tech stack and architecture
   - `spec.md` - Requirements
   - `data-model.md`, `contracts/`, `research.md`, `quickstart.md` (if exist)

**3. Implement following the prompt's guidance:**
   - Follow subtask order
   - Respect dependencies (sequential vs parallel `[P]`)
   - Run tests if required
   - Commit as you complete major milestones

**4. When complete:**
```bash
spec-kitty agent tasks move-task <WPID> --to for_review --note "Ready for review"
git add <your-changes>
git commit -m "Complete <WPID>: <description>"
```

---

## That's It

**Simple workflow:**
1. Find which WP (from `$ARGUMENTS` or first planned)
2. Move it to doing
3. Read the prompt file
4. Do the work
5. Move to for_review

**No busywork, no shell PID tracking, just implement.**

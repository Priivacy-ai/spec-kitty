---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

**UTF-8 Encoding Rule:** When writing any markdown or code files during implementation, use only UTF-8 compatible characters. Avoid Windows-1252 smart quotes (" " ' '), em dashes, or copy-pasted content from Microsoft Office. Use standard ASCII quotes (" ') and simple symbols. See [templates/common/utf8-file-writing-guidelines.md](templates/common/utf8-file-writing-guidelines.md) for details.

*Path: [templates/commands/implement.md](templates/commands/implement.md)*


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Quick Implementation Workflow

Get to work fast. Assume you have no context and build it efficiently.

### 1. Location Check (Fast)

**Check current branch:**
```bash
git branch --show-current
```

**If on main branch**, navigate to worktree:
```bash
# Find worktree
ls .worktrees/

# Navigate to it
cd .worktrees/<feature-name>

# Verify
git branch --show-current
```

**If already on feature branch**, you're good - continue.

### 2. Get Paths & Available Docs (One Command)

```bash
{SCRIPT}
```

Parse JSON for:
- `FEATURE_DIR` - Your specs directory
- `AVAILABLE_DOCS` - Which docs exist (plan, data-model, contracts, research, quickstart)

### 3. Find Next Task

```bash
ls $FEATURE_DIR/tasks/planned/WP*.md | sort | head -1
```

This is your next task. Read it.

**IMPORTANT**: If task has reviewer notes or came back from for_review, those notes are your TODO list - address every point.

### 4. Build Context (Read Only What You Need)

**Always read**:
- The task prompt file you're working on
- `plan.md` (for tech stack, architecture, file structure)

**Read only if needed for your task**:
- `data-model.md` - Entity definitions
- `contracts/<relevant-file>` - API specs referenced in task
- `research.md` - Technical decisions (if task references them)
- `quickstart.md` - Integration examples

**Don't read**:
- All 742 lines of tasks.md (you already have your specific task)
- Checklists (those are for /accept, not implementation)
- Other task prompts (focus on yours)

### 5. Implement

Do the work described in the task prompt. Write code, tests, docs - whatever the task requires.

Follow the tech stack and patterns from plan.md.

### 6. Move Task to Review

When implementation is complete:

```bash
# Move the task file
mv $FEATURE_DIR/tasks/planned/WPXX-name.md $FEATURE_DIR/tasks/for_review/

# Commit
git add tasks/
git commit -m "Complete WPXX: brief description of what was done"
```

**That's it.** No shell PIDs, no activity logs, no frontmatter updates, no verification checklists.

### 7. Next Task

```bash
ls $FEATURE_DIR/tasks/planned/WP*.md | sort | head -1
```

If there's another task, repeat from Step 3.

If `ls` returns nothing, all planned tasks are done. Run `/spec-kitty.review` to review completed work.

## Implementation Guidelines

**Test-Driven Development**:
- If task involves contracts, write tests that validate the contract first
- Then implement to make tests pass

**Code Quality**:
- Follow patterns established in plan.md
- Maintain consistency with existing codebase
- Add comments for complex logic

**Security**:
- Avoid command injection, XSS, SQL injection
- Validate all inputs
- Use parameterized queries
- Escape user-provided content

**Error Handling**:
- If you get stuck or blocked, stop and report the issue clearly
- Don't skip parts of the task - ask for clarification instead
- If tests fail, fix them before moving to for_review

## Task Dependencies

Tasks are numbered for a reason (WP01, WP02, WP03...). Generally:
- Do them in order
- If task says [P] for parallel, it can be done anytime
- If task explicitly lists dependencies, respect them

## Progress Tracking

As you complete each task:
1. Move it to for_review (as shown in Step 6)
2. Commit the change
3. Report what you completed
4. Move to next task

The dashboard will show your progress in real-time.

## Advanced: Batch Implementation

If you're implementing multiple small tasks:

```bash
# Get all planned tasks
ls tasks/planned/WP*.md

# Work through them sequentially
# After each one, move to for_review and commit
```

You can implement several tasks before running /spec-kitty.review.

## When You're Done

After all planned tasks are moved to for_review:
1. Run `/spec-kitty.review` to review completed work
2. Review will move approved tasks to done
3. Any tasks needing changes go back to planned with reviewer notes
4. Repeat until all tasks are in done/
5. Run `/spec-kitty.accept` to validate feature readiness
6. Run `/spec-kitty.merge` to merge to main

## Troubleshooting

**"No planned tasks found"**: All tasks are either done or in review. Run `/spec-kitty.review`.

**"Can't find FEATURE_DIR"**: You're not in a feature worktree. Navigate to `.worktrees/<feature>/` first.

**"Don't know what to implement"**: Read the task prompt in `tasks/planned/`. That's your spec.

**"Task prompt is empty or unclear"**: That's a bug in task generation. Ask the user or run `/spec-kitty.tasks` again.

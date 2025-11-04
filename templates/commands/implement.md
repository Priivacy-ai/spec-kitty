---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---
**⚠️ CRITICAL: Read [.kittify/AGENTS.md](.kittify/AGENTS.md) for universal rules (paths, UTF-8 encoding, context management, quality expectations).**

*Path: [templates/commands/implement.md](templates/commands/implement.md)*


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Workflow

### 1. Get Your Bearings

Run the prerequisites script to get paths and see what documentation exists:

```bash
{SCRIPT}
```

This gives you `FEATURE_DIR` and lists available docs (plan, data-model, contracts, research, quickstart).

**Location note**: If you're on `main` branch and there's a worktree at `.worktrees/<feature>/`, navigate there first.

### 2. Find Next Task

```bash
ls $FEATURE_DIR/tasks/planned/WP*.md | sort | head -1
```

Read that task prompt. That's your assignment.

**If task has reviewer feedback** (came back from for_review), those notes are your TODO list - address all of them.

### 3. Build Context

You have no context at session start. Read what you need:

**Essential**:
- The task prompt (your spec)
- `plan.md` (tech stack, architecture, file structure)

**As needed** (use your judgment):
- `tasks.md` - See all tasks, dependencies, execution order
- `data-model.md` - Entity definitions
- `contracts/<file>` - API specs the task references
- `research.md` - Technical decisions
- `quickstart.md` - Integration examples

**Don't skip relevant information. Read what you need to do the job right.**

### 4. Implement

Do the work. Write code, tests, documentation - whatever the task requires.

Follow the patterns from plan.md. If you reference contracts, validate against them. If tests fail, fix them.

### 5. Mark Complete

```bash
mv $FEATURE_DIR/tasks/planned/WPXX-name.md $FEATURE_DIR/tasks/for_review/
git add tasks/
git commit -m "Complete WPXX: what you did"
```

### 6. Next Task

Find the next planned task and repeat. When planned/ is empty, run `/spec-kitty.review`.

## Notes

- **Tasks are numbered** for a reason. Generally do them in order unless marked [P] for parallel.
- **Quality matters**: Follow plan.md patterns, write secure code, make tests pass before moving to review.
- **Get help when stuck**: Don't skip task requirements or write placeholders. Ask for clarification.
- **Mid-session**: If you already have context (plan.md, tasks.md in your history), don't re-read them. Use your judgment.

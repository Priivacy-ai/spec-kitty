---
description: Generate individual WP prompt files (tasks/WP*.md) from the task outline in tasks.md.
---

# /spec-kitty.tasks-packages - Generate Work Package Files

**Version**: 0.12.0+

## Purpose

Generate individual `tasks/WP*.md` prompt files from the outline in `tasks.md`.
This step assumes `tasks.md` already exists with complete WP definitions.

---

## 📍 WORKING DIRECTORY: Stay in planning repository

**IMPORTANT**: This step works in the planning repository. NO worktrees created.

## User Input

```text
$ARGUMENTS
```

## Steps

### 1. Setup

Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks` from the repository root and capture `FEATURE_DIR`. All paths must be absolute.

### 2. Load tasks.md

Read `FEATURE_DIR/tasks.md` — this must already exist from the previous step.
Parse the work package definitions, subtask lists, and dependencies.

### 3. Generate Prompt Files

For each work package defined in `tasks.md`:

**CRITICAL PATH RULE**: All WP files MUST be created in a FLAT `FEATURE_DIR/tasks/` directory, NOT in subdirectories!

- Correct: `FEATURE_DIR/tasks/WPxx-slug.md` (flat, no subdirectories)
- WRONG: `FEATURE_DIR/tasks/planned/`, `FEATURE_DIR/tasks/doing/`, or ANY lane subdirectories

**For each WP**:
1. Derive a kebab-case slug from the title
2. Filename: `WPxx-slug.md` (e.g., `WP01-create-html-page.md`)
3. Full path: `FEATURE_DIR/tasks/WP01-create-html-page.md`
4. Use the bundled task prompt template (`.kittify/missions/software-dev/templates/task-prompt-template.md`)
5. Include frontmatter with:
   - `work_package_id`, `subtasks` array, `lane: "planned"`, `dependencies`, history entry
6. Include in body:
   - Objective, context, detailed guidance per subtask
   - Test strategy (only if requested)
   - Definition of Done, risks, reviewer guidance
7. Update `tasks.md` to reference the prompt filename

**TARGET PROMPT SIZE**: 200-500 lines per WP (3-7 subtasks)
**MAXIMUM PROMPT SIZE**: 700 lines per WP (10 subtasks max)
**If prompts are >700 lines**: Split the WP — it's too large

**IMPORTANT**: All WP files live in flat `tasks/` directory. Lane status is tracked ONLY in the `lane:` frontmatter field, NOT by directory location.

### 4. Include Dependencies in Frontmatter

Each WP prompt file MUST include a `dependencies` field:
```yaml
---
work_package_id: "WP02"
title: "Build API"
lane: "planned"
dependencies: ["WP01"]  # From tasks.md
subtasks: ["T001", "T002"]
---
```

Include the correct implementation command:
- No dependencies: `spec-kitty implement WP01`
- With dependencies: `spec-kitty implement WP02 --base WP01`

### 5. Self-Check

After generating each prompt:
- Subtask count: 3-7? ✓ | 8-10? ⚠️ | 11+? ❌ SPLIT
- Estimated lines: 200-500? ✓ | 500-700? ⚠️ | 700+? ❌ SPLIT
- Can implement in one session? ✓ | Multiple sessions needed? ❌ SPLIT

## Output

After completing this step:
- `FEATURE_DIR/tasks/WP*.md` prompt files exist for all work packages
- Each has proper frontmatter with `work_package_id`, `lane`, `dependencies`
- `tasks.md` references all prompt filenames

**Next step**: `spec-kitty next --agent <name>` will advance to finalization.

## Prompt Quality Guidelines

**Good prompt** (~60 lines per subtask):
```markdown
### Subtask T001: Implement User Login Endpoint

**Purpose**: Create POST /api/auth/login endpoint that validates credentials and returns JWT token.

**Steps**:
1. Create endpoint handler in `src/api/auth.py`:
   - Route: POST /api/auth/login
   - Request body: `{email: string, password: string}`
   - Response: `{token: string, user: UserProfile}` on success
   - Error codes: 400, 401, 429

2. Implement credential validation:
   - Hash password with bcrypt
   - Use constant-time comparison

**Files**: `src/api/auth.py` (new, ~80 lines)
**Validation**: Valid credentials return 200 with token
```

**Bad prompt** (~20 lines per subtask):
```markdown
### T001: Add auth
Steps: Create endpoint. Add validation. Test it.
```

Context for work-package planning: {ARGS}

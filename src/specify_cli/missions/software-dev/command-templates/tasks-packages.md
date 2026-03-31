# /spec-kitty.tasks-packages - Generate Work Package Files

**Version**: 0.12.0+

## Purpose

Generate individual `tasks/WP*.md` prompt files from the outline in `tasks.md`.
This step assumes `tasks.md` already exists with complete WP definitions.

---

## 📍 WORKING DIRECTORY: Stay in the project root checkout

**IMPORTANT**: This step works in the project root checkout. NO worktrees created.

**In repos with multiple features, always pass `--feature <slug>` to every spec-kitty command.**

## User Input

```text
$ARGUMENTS
```

## Steps

### 1. Setup

Run:

```bash
spec-kitty agent context resolve --action tasks_packages --json
```

Then execute the returned `check_prerequisites` command and capture
`feature_dir`. All paths must be absolute.

### 2. Load tasks.md

Read `feature_dir/tasks.md` — this must already exist from the previous step.
Parse the work package definitions, subtask lists, and dependencies.

### 3. Generate Prompt Files

For each work package defined in `tasks.md`:

**CRITICAL PATH RULE**: All WP files MUST be created in a FLAT `feature_dir/tasks/` directory, NOT in subdirectories!

- Correct: `feature_dir/tasks/WPxx-slug.md` (flat, no subdirectories)
- WRONG: `feature_dir/tasks/planned/`, `feature_dir/tasks/doing/`, or ANY status subdirectories

**For each WP**:
1. Derive a kebab-case slug from the title
2. Filename: `WPxx-slug.md` (e.g., `WP01-create-html-page.md`)
3. Full path: `feature_dir/tasks/WP01-create-html-page.md`
4. Follow the WP prompt template structure below (**do NOT write instructions to read a template file from `.kittify/`**)
5. Include frontmatter with:
   - `work_package_id`, `subtasks` array, `dependencies`, history entry
   - `requirement_refs` array from the WP's `Requirement Refs` line in `tasks.md`
   - `owned_files`, `authoritative_surface`, `execution_mode` (required ownership fields)
6. Include in body:
   - Objective, context, detailed guidance per subtask
   - Test strategy (only if requested)
   - Definition of Done, risks, reviewer guidance
7. Update `tasks.md` to reference the prompt filename

**TARGET PROMPT SIZE**: 200-500 lines per WP (3-7 subtasks)
**MAXIMUM PROMPT SIZE**: 700 lines per WP (10 subtasks max)
**If prompts are >700 lines**: Split the WP — it's too large

**IMPORTANT**: All WP files live in flat `tasks/` directory. Status is managed via `status.events.jsonl`, not by directory location or frontmatter fields.

### 4. Include Dependencies in Frontmatter

Each WP prompt file MUST include a `dependencies` field:
```yaml
---
work_package_id: "WP02"
title: "Build API"
dependencies: ["WP01"]  # From tasks.md
requirement_refs: ["FR-001", "NFR-001"]  # From tasks.md Requirement Refs
subtasks: ["T001", "T002"]
owned_files: ["src/api/**"]
authoritative_surface: "src/api/"
execution_mode: "code_change"
---
```

Include the correct implementation command:
- No dependencies: `spec-kitty implement WP01`
- With dependencies: `spec-kitty implement WP02 --base WP01`

**Ownership rules**:
- `owned_files`: List of glob patterns for files this WP touches — no two WPs may overlap.
- `authoritative_surface`: Path prefix that must be a prefix of at least one `owned_files` entry.
- `execution_mode`: `"code_change"` for source code changes, `"planning_artifact"` for kitty-specs docs.
- Agents working on a WP must not modify files outside their `owned_files` list.

### 5. Self-Check

After generating each prompt:
- Subtask count: 3-7? ✓ | 8-10? ⚠️ | 11+? ❌ SPLIT
- Estimated lines: 200-500? ✓ | 500-700? ⚠️ | 700+? ❌ SPLIT
- Can implement in one session? ✓ | Multiple sessions needed? ❌ SPLIT

## Output

After completing this step:
- `feature_dir/tasks/WP*.md` prompt files exist for all work packages
- Each has proper frontmatter with `work_package_id`, `dependencies`, `owned_files`, `authoritative_surface`, `execution_mode`
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

Context for work-package planning: $ARGUMENTS

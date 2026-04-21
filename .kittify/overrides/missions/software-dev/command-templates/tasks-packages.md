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

Run `spec-kitty agent mission check-prerequisites --json --paths-only --include-tasks` from the repository root and capture `mission_dir`. All paths must be absolute.

### 2. Load tasks.md

Read `mission_dir/tasks.md` — this must already exist from the previous step.
Parse the work package definitions, subtask lists, and dependencies.

### 3. Generate Prompt Files in Parallel

Parse all WP definitions from `tasks.md`. Each WP prompt file is independent —
dispatch one sub-agent per WP in a **single message** so they run concurrently
rather than generating all WP content in one serial response.

**CRITICAL PATH RULE**: All WP files MUST be created in a FLAT `mission_dir/tasks/`
directory, NOT in subdirectories!

- Correct: `mission_dir/tasks/WPxx-slug.md` (flat, no subdirectories)
- WRONG: `mission_dir/tasks/planned/`, `mission_dir/tasks/doing/`, or ANY lane subdirectories

**Batching for large missions**: If there are more than 6 WPs, dispatch in groups
of 4. Send all agents in a group in one message, wait for all to complete, then
start the next group.

**Sub-agent prompt** (send one per WP, all dispatched simultaneously in one message):

---

You are writing a single Work Package prompt file for the spec-kitty planning
pipeline. Write exactly one file, then update `tasks.md` to reference it, and
return the filename and final line count.

**Mission directory**: `{mission_dir}` (absolute path)
**Write to**: `{mission_dir}/tasks/{wp_id}-{slug}.md`

**Work Package** (from tasks.md):
- id: `{wp_id}`
- title: `{title}`
- dependencies: `{dependencies}` (from tasks.md "Depends on" line)
- requirement_refs: `{requirement_refs}` (from tasks.md "Requirement Refs" line)
- subtasks: `{subtask_list}` (T-ids listed under this WP)

**Read for context** (all from `mission_dir`):
- `tasks.md` (required — full WP definition, subtask list, dependencies)
- `plan.md` (required — tech architecture, stack)
- `spec.md` (required — user stories, acceptance criteria)
- `data-model.md`, `research.md` (read if present)

**Write the WP prompt file with this structure:**

Frontmatter:
```yaml
---
work_package_id: "{wp_id}"
title: "{title}"
lane: "planned"
dependencies: {dependencies}
requirement_refs: {requirement_refs}
subtasks: {subtask_list}
---
```

Body sections (in order):
1. `## Objective` — 1–3 sentence goal
2. `## Context` — why this WP exists, what depends on it, key design decisions from plan.md
3. `### Subtask {T-id}: {name}` — one section per subtask, ~60 lines each:
   - **Purpose**: what this subtask accomplishes
   - **Steps**: numbered, with specific file paths and implementation details
   - **Files**: what to create/modify, approximate size
   - **Validation**: how to verify it works
4. `## Definition of Done` — verifiable checklist covering all subtasks
5. `## Risks` — known risks and mitigations
6. `## Reviewer Guidance` — what reviewers should focus on

Include the implementation command (pick one):
- No dependencies: `spec-kitty implement {wp_id}`
- With dependencies: `spec-kitty implement {wp_id} --base {first_dep}`

After writing the file, update `tasks.md` to reference the prompt filename on the
WP's line (e.g., append `→ tasks/{wp_id}-{slug}.md`).

Sizing: target 200–500 lines (3–7 subtasks), maximum 700 lines (10 subtasks).
If >700 lines would be needed: write the file anyway but add a `> NOTE: This WP
should be split` callout at the top.

---

**After all sub-agents confirm completion**, proceed to Step 4.

**Fallback — if your host does not support sub-agents**: Generate all WP files
sequentially and issue all Write tool calls in a single batched response.

Do NOT update `tasks.md` during sub-agent dispatch — each sub-agent updates its
own reference, or collect all and update once after all complete.

### 4. Include Dependencies in Frontmatter

Each WP prompt file MUST include a `dependencies` field:

```yaml
---
work_package_id: "WP02"
title: "Build API"
lane: "planned"
dependencies: ["WP01"]  # From tasks.md
requirement_refs: ["FR-001", "NFR-001"]  # From tasks.md Requirement Refs
subtasks: ["T001", "T002"]
---
```

Include the correct implementation command:

- No dependencies: `spec-kitty implement WP01`
- With dependencies: `spec-kitty implement WP02 --base WP01`

### 5. Self-Check

After all sub-agents complete, verify each generated prompt:

- Subtask count: 3-7? ✓ | 8-10? ⚠️ | 11+? ❌ needs splitting
- Estimated lines: 200-500? ✓ | 500-700? ⚠️ | 700+? ❌ needs splitting
- Can implement in one session? ✓ | Multiple sessions needed? ❌ needs splitting

## Output

After completing this step:

- `mission_dir/tasks/WP*.md` prompt files exist for all work packages
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

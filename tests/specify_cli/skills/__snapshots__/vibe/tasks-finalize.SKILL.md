---
name: spec-kitty.tasks-finalize
description: "Validate dependencies, finalize WP metadata, and commit all task artifacts."
user-invocable: true
---

# /spec-kitty.tasks-finalize - Finalize Tasks

**Version**: 3.2.0

## Purpose

Run the finalization command to parse dependencies from `tasks.md`, validate
them, update WP frontmatter, and commit all task artifacts to the target branch.

---

## 📍 WORKING DIRECTORY: Stay in planning repository

**IMPORTANT**: This step works in the planning repository. NO worktrees created.

## User Input

The content of the user's message that invoked this skill (everything after the skill invocation token, e.g. after `/spec-kitty.<command>` or `$spec-kitty.<command>`) is the User Input referenced elsewhere in these instructions.

You **MUST** consider this user input before proceeding (if not empty).
## Steps

### 1. Run Validate-Only Preflight

**CRITICAL**: Run this preflight command from repo root before any mutating
finalization:

```bash
spec-kitty agent mission finalize-tasks --validate-only --mission <mission-slug> --json
```

This command will:

- Parse dependencies from tasks.md
- Parse `Requirement Refs` from tasks.md
- Preview WP frontmatter updates without writing files
- Validate dependencies (check for cycles, invalid references)
- Validate requirement mapping:
  - Every WP has at least one requirement reference
  - Referenced requirement IDs exist in spec.md
  - Every FR-### in spec.md is mapped to at least one WP

If the JSON output contains `"error": "Requirement mapping validation failed"`,
do **not** run finalization. Report the blocking fields
(`missing_requirement_refs_wps`, `unknown_requirement_refs`, and
`unmapped_functional_requirements`), then fix mappings with
`spec-kitty agent tasks map-requirements --mission <mission-slug> --json` or by
updating WP `requirement_refs`.

### 2. Run Finalization Command

Only after validate-only exits successfully, run the mutating finalization
command from repo root:

```bash
spec-kitty agent mission finalize-tasks --mission <mission-slug> --json
```

This command will update WP frontmatter, compute lanes, and commit all tasks to
the target branch.

### 3. Check Output

The JSON output includes:

- `"commit_created": true/false` — whether a commit was made
- `"commit_hash"` — the commit hash if created
- `"wp_count"` — number of WP files processed
- `"dependencies_parsed"` — dependency relationships found
- `"requirement_refs_parsed"` — requirement reference mapping found
- Validation details when checks fail (`missing_requirement_refs_wps`, `unknown_requirement_refs`, `unmapped_functional_requirements`)

### 4. Verify

**IMPORTANT — DO NOT COMMIT AGAIN AFTER THIS COMMAND**:

- `finalize-tasks` commits the files automatically
- If `commit_created=true`, files are ALREADY committed — do not run `git commit` again
- Other dirty files shown by `git status` (templates, config) are UNRELATED
- Verify using the `commit_hash` from JSON output, not by running `git add/commit` again

### 5. Report

Provide a concise outcome summary:

- Path to `tasks.md`
- Work package count and per-package subtask tallies
- Parallelization highlights
- MVP scope recommendation
- Finalization status (dependencies parsed, X WP files updated, committed to target branch)
- Next suggested command (e.g., `/spec-kitty.analyze` or `/spec-kitty.implement`)

## Output

After completing this step:

- All WP files have `dependencies` field in frontmatter
- All WP files have `requirement_refs` field in frontmatter
- Dependencies are validated (no cycles, no invalid references)
- Requirement references are validated against spec.md
- Task artifacts are committed to the target branch

**Next step**: `spec-kitty next --agent <name>` will advance to implementation.

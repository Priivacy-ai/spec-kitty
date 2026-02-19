---
description: Validate dependencies, finalize WP metadata, and commit all task artifacts.
---

# /spec-kitty.tasks-finalize - Finalize Tasks

**Version**: 0.12.0+

## Purpose

Run the finalization command to parse dependencies from `tasks.md`, validate
them, update WP frontmatter, and commit all task artifacts to the target branch.

---

## 📍 WORKING DIRECTORY: Stay in planning repository

**IMPORTANT**: This step works in the planning repository. NO worktrees created.

## User Input

```text
$ARGUMENTS
```

## Steps

### 1. Run Finalization Command

**CRITICAL**: Run this command from repo root:

```bash
spec-kitty agent feature finalize-tasks --json
```

This command will:
- Parse dependencies from tasks.md
- Update WP frontmatter with `dependencies` field
- Validate dependencies (check for cycles, invalid references)
- Commit all tasks to target branch

### 2. Check Output

The JSON output includes:
- `"commit_created": true/false` — whether a commit was made
- `"commit_hash"` — the commit hash if created
- `"wp_count"` — number of WP files processed
- `"dependencies_parsed"` — dependency relationships found

### 3. Verify

**IMPORTANT — DO NOT COMMIT AGAIN AFTER THIS COMMAND**:
- `finalize-tasks` commits the files automatically
- If `commit_created=true`, files are ALREADY committed — do not run `git commit` again
- Other dirty files shown by `git status` (templates, config) are UNRELATED
- Verify using the `commit_hash` from JSON output, not by running `git add/commit` again

### 4. Report

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
- Dependencies are validated (no cycles, no invalid references)
- Task artifacts are committed to the target branch

**Next step**: `spec-kitty next --agent <name>` will advance to implementation.

Context for work-package planning: {ARGS}

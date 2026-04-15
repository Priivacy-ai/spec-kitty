---
description: Review a work package implementation
---
# /spec-kitty.review - Review Work Package Implementation

**Version**: 0.12.0+

## Purpose

Review the implementation of a work package against its prompt file, acceptance
criteria, and owned-file boundaries. Verify correctness, test coverage, and
compliance with any applicable guardrails (e.g., bulk edit occurrence maps).

---

## Working Directory

**IMPORTANT**: This step works inside the execution workspace (worktree)
allocated by `spec-kitty agent action review WPxx --agent <name>`. Do NOT modify files outside
your `owned_files` boundaries.

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`. The resolver disambiguates by `mission_id` and returns a structured `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Review Steps

### 1. Setup

Run:

```bash
spec-kitty agent context resolve --action review --mission <handle> --json
```

Then execute the returned `check_prerequisites` command and capture
`feature_dir`. All paths must be absolute.

The output of `spec-kitty agent action review ...` is the authoritative work
package prompt and review context. Do **not** separately call
`spec-kitty charter context` or go hunting for alternate prompt files unless
the command output tells you to.

### 2. Load Work Package Prompt

Read the WP prompt file from `feature_dir/tasks/WPxx-slug.md`.
Parse frontmatter for:
- `owned_files` -- only these globs should have been modified
- `authoritative_surface` -- primary directory for this WP
- `execution_mode` -- `code_change` or `planning_artifact`
- `subtasks` -- ordered list of subtask IDs
- `dependencies` -- WPs that must be done first

### 3. Verify Implementation

For each subtask:
1. Confirm the subtask has been implemented as specified
2. Check that tests exist and pass (for code_change subtasks)
3. Verify no files outside `owned_files` were modified

### 4. Check Quality

- All tests pass
- Code follows project conventions (run linter if configured)
- No unintended side effects or regressions
- Changes are well-documented where appropriate

---

## Bulk Edit Compliance (if applicable)

If this mission has `change_mode: bulk_edit` in `meta.json`:

1. **Verify occurrence map exists**: `occurrence_map.yaml` must be present in the feature directory
2. **Reference during review**: The occurrence map is the governing artifact for this bulk edit
3. **Check category compliance**:
   - Verify changes respect `do_not_change` categories — reject if these were modified
   - Verify `manual_review` categories have documented justification
   - Flag any changed files that fall outside classified categories
4. **Check exceptions**: Verify exception files/patterns were not modified
5. **If occurrence map is missing**: Reject the review — bulk edit missions require classification

The system enforces map existence automatically, but as a reviewer you should verify
that the *substance* of the changes aligns with the classification, not just that the
file exists.

---

## Output

After completing review:
- Approve or reject each subtask with clear reasoning
- If rejecting, provide specific feedback on what needs to change
- Commit any review notes or annotations

**Next step**: `spec-kitty next --agent <name>` will advance to the next phase.

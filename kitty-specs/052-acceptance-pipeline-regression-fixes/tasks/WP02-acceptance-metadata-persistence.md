---
work_package_id: WP02
title: Acceptance Metadata Persistence
lane: "for_review"
dependencies: [WP01]
base_branch: 052-acceptance-pipeline-regression-fixes-WP01
base_commit: ac8a27c115c62ad99a4496d5e9de6d6395b27686
created_at: '2026-03-19T17:11:27.090604+00:00'
subtasks:
- T005
- T006
- T007
phase: Phase 1 - Core Bug Fixes
assignee: ''
agent: coordinator
shell_pid: '10668'
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-19T16:39:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-002
- FR-005
---

# Work Package Prompt: WP02 – Acceptance Metadata Persistence

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Objectives & Success Criteria

- After `perform_acceptance()` creates a git commit, the resulting SHA is written back to `meta.json` in both:
  - Top-level `accept_commit` field
  - `acceptance_history[-1]["accept_commit"]`
- The fix does NOT create a duplicate history entry (no second `record_acceptance()` call).
- Both `src/specify_cli/acceptance.py` and `src/specify_cli/scripts/tasks/acceptance_support.py` receive the same fix.
- Legacy copies synced.

**Success gate**: After `perform_acceptance()` returns, reading `meta.json` shows a real SHA (not `null`) in `accept_commit`.

## Context & Constraints

- **Spec**: `kitty-specs/052-acceptance-pipeline-regression-fixes/spec.md` — User Story 2
- **Plan**: `kitty-specs/052-acceptance-pipeline-regression-fixes/plan.md` — Bug Analysis P1 (commit SHA)
- **Constraint C-001**: Both copies must receive identical fixes

**Root cause**: `perform_acceptance()` calls `record_acceptance(..., accept_commit=None)` at line 545 (acceptance.py) / 628 (acceptance_support.py) BEFORE creating the git commit. After the commit, the SHA is captured into the local variable but never written back to `meta.json`.

**Why not call `record_acceptance()` again?**: It would append a duplicate entry to `acceptance_history`. The fix uses a targeted `load_meta()` + `write_meta()` to update the existing entry.

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T005 – Add post-commit SHA write-back in `acceptance.py`

- **Purpose**: After the acceptance commit is created and its SHA is captured, write it back to `meta.json`.
- **File**: `src/specify_cli/acceptance.py`
- **Steps**:
  1. In `perform_acceptance()` (starts at line 516), locate the block after the commit is created and the SHA is captured (around lines 567-573):
     ```python
     commit_created = True
     try:
         accept_commit = (
             run_git(["rev-parse", "HEAD"], cwd=summary.repo_root, check=True)
             .stdout.strip()
         )
     except TaskCliError:
         accept_commit = None
     ```
  2. Immediately after this block (after the `except TaskCliError` clause), add the SHA write-back:
     ```python
     # Persist commit SHA to meta.json
     if accept_commit:
         _meta = load_meta(summary.feature_dir)
         if _meta is not None:
             _meta["accept_commit"] = accept_commit
             _history = _meta.get("acceptance_history", [])
             if _history:
                 _history[-1]["accept_commit"] = accept_commit
             write_meta(summary.feature_dir, _meta)
     ```
  3. Add imports at the top of the file (alongside existing `record_acceptance` import at line 27):
     ```python
     from specify_cli.feature_metadata import load_meta, record_acceptance, write_meta
     ```
     (Replace the existing `from specify_cli.feature_metadata import record_acceptance` with this expanded import.)
  4. Use underscore-prefixed local names (`_meta`, `_history`) to avoid shadowing any outer-scope variables.
- **Parallel?**: No
- **Notes**: The `meta.json` file has already been committed at this point (the acceptance commit includes it). The SHA update is written AFTER the commit, so `meta.json` will have an uncommitted change containing the SHA. This is acceptable and expected — the SHA is reference data.

### Subtask T006 – Mirror T005 in `src/specify_cli/scripts/tasks/acceptance_support.py`

- **Purpose**: Apply the same fix to the standalone copy.
- **File**: `src/specify_cli/scripts/tasks/acceptance_support.py`
- **Steps**:
  1. In `perform_acceptance()` (starts around line 599), locate the equivalent post-commit SHA capture block (around lines 649-656).
  2. Add the same SHA write-back code as T005.
  3. The standalone copy already imports `record_acceptance` from `specify_cli.feature_metadata` (line 27). Expand this to include `load_meta` and `write_meta`:
     ```python
     from specify_cli.feature_metadata import load_meta, record_acceptance, write_meta
     ```
  4. Verify the fix is structurally identical to T005.
- **Parallel?**: No

### Subtask T007 – Sync to `scripts/tasks/` and `.kittify/scripts/tasks/`

- **Purpose**: Keep legacy and generated copies in sync.
- **Files**:
  - `scripts/tasks/acceptance_support.py`
  - `.kittify/scripts/tasks/acceptance_support.py`
- **Steps**:
  1. Copy `src/specify_cli/scripts/tasks/acceptance_support.py` to both locations.
  2. Verify byte-identical with `diff`.
- **Parallel?**: No
- **Notes**: Same sync as WP01 T004, but now includes the WP02 fix too.

## Risks & Mitigations

- **Risk**: Post-commit meta.json write leaves an uncommitted file. **Mitigation**: This is by design — the SHA references the commit itself, so it can't be inside the commit. The next `git add/commit` cycle picks it up naturally.
- **Risk**: Race condition if multiple acceptance attempts run concurrently. **Mitigation**: Acceptance is always single-threaded per feature.

## Review Guidance

- Verify `record_acceptance()` is called exactly ONCE (not twice).
- Verify the SHA write-back uses `load_meta()` + `write_meta()`, not a second `record_acceptance()`.
- Verify both `accept_commit` (top-level) and `acceptance_history[-1]["accept_commit"]` are set.
- Verify no duplicate history entries are created.
- Check that the import is expanded (not a new import line duplicating the module).

## Activity Log

- 2026-03-19T16:39:32Z – system – lane=planned – Prompt created.
- 2026-03-19T17:11:27Z – coordinator – shell_pid=10668 – lane=doing – Assigned agent via workflow command
- 2026-03-19T17:14:09Z – coordinator – shell_pid=10668 – lane=for_review – Ready for review: SHA write-back added to all 3 acceptance_support copies, 50 tests pass

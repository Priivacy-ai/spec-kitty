---
work_package_id: WP03
title: '#845 — dossier snapshot does not self-block transitions'
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-e2e-827-followups-01KQAJA0
base_commit: b63e107acf869b30ccca53a3664d336738c2f988
created_at: '2026-04-28T20:36:30.199882+00:00'
subtasks:
- T010
- T011
- T012
- T013
agent: "claude:sonnet:python-pedro:reviewer"
shell_pid: "78452"
history:
- at: '2026-04-28T19:59:16Z'
  actor: planner
  note: Initial work package created from /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
execution_mode: code_change
mission_id: 01KQAJA02YZ2Q7SH5WND713HKA
mission_slug: charter-e2e-827-followups-01KQAJA0
model: claude-sonnet-4-6
owned_files:
- .gitignore
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/status/preflight.py
- tests/integration/test_dossier_snapshot_no_self_block.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile so your behavior matches what this work package expects:

```
/ad-hoc-profile-load python-pedro
```

This sets `role=implementer`, scopes your editing surface to the `owned_files` declared above, and applies Python-specialist standards.

## Objective

Adopt the **EXCLUDE** ownership policy for `<feature_dir>/.kittify/dossiers/<mission_slug>/snapshot-latest.json`: gitignore it AND filter it from the dirty-state preflight used by `agent tasks move-task` and related transitions. Real unrelated dirty state still blocks.

Per Constraint **C-006** in the spec, this WP picks **exactly one** ownership policy (EXCLUDE — see [`research.md`](../research.md) R5 for rejected alternatives) and MUST NOT introduce a runtime branch where two policies conditionally apply.

## Context

- The snapshot writer at `src/specify_cli/dossier/snapshot.py:142–147` writes `feature_dir/.kittify/dossiers/<mission_slug>/snapshot-latest.json` with a plain file write. No staging, no commit, no special-case logic.
- `src/specify_cli/state_contract.py:211` declares the on-disk path pattern: `.kittify/dossiers/<feature>/snapshot-latest.json`.
- The mission setup-plan command at `src/specify_cli/cli/commands/agent/mission.py:84` references the same path.
- The dirty-state preflight that backs `agent tasks move-task` is in `src/specify_cli/cli/commands/agent/tasks.py` (and may have helpers in `src/specify_cli/status/`). When the snapshot is written by a status-aware command, the preflight then sees the snapshot as dirty and self-blocks the next transition.
- Contract for this fix: [`contracts/dossier-snapshot-ownership.md`](../contracts/dossier-snapshot-ownership.md) (D1, D2, D3) and [`data-model.md`](../data-model.md) (INV-845-1, INV-845-2, INV-845-3).

## Detailed guidance per subtask

### Subtask T010 [P] — Add gitignore entry

**Purpose**: Cover the common case (`git status`, default `git status --porcelain`) where `.gitignore` is respected.

**Steps**:

1. Open the root `.gitignore`.
2. Add a section (with a clarifying header comment) for dossier snapshots:
   ```
   # Dossier snapshots are mutable derived artifacts; recomputable from dossier source.
   # See kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/dossier-snapshot-ownership.md
   .kittify/dossiers/*/snapshot-latest.json
   kitty-specs/*/.kittify/dossiers/*/snapshot-latest.json
   ```
3. The two patterns cover both possible parent locations (project root `.kittify/` and per-mission `kitty-specs/<mission>/.kittify/`) — match whichever the existing writers actually use; include both for safety.
4. Verify:
   ```bash
   touch .kittify/dossiers/test-mission/snapshot-latest.json
   git check-ignore -v .kittify/dossiers/test-mission/snapshot-latest.json   # should print the gitignore rule
   rm .kittify/dossiers/test-mission/snapshot-latest.json
   ```
   (Use whichever path the writer actually uses for the verification.)

**Files**: `.gitignore` (modified, ~5 added lines).

**Validation**:
- [ ] `git check-ignore -v <path>` matches a real snapshot path against the new rule.
- [ ] `git status` does not list a fresh snapshot file as untracked.
- [ ] No unrelated changes to `.gitignore`.

### Subtask T011 — Explicit path filter in dirty-state preflight

**Purpose**: Belt-and-suspenders alongside `.gitignore` (per research R6). Some preflight code paths may compute dirty state in ways that bypass `.gitignore`.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/tasks.py`.
2. Locate the `move-task` (or equivalent name) command handler. Find the dirty-state preflight call.
3. Add a small helper near the preflight (or in a shared location like `src/specify_cli/status/preflight.py` if it exists or makes sense to add) named `_is_dossier_snapshot(path: Path) -> bool`:
   ```python
   import fnmatch
   from pathlib import Path

   _DOSSIER_SNAPSHOT_PATTERNS = (
       "**/.kittify/dossiers/*/snapshot-latest.json",
       "kitty-specs/*/.kittify/dossiers/*/snapshot-latest.json",
   )

   def _is_dossier_snapshot(path: Path) -> bool:
       posix = path.as_posix()
       return any(fnmatch.fnmatch(posix, pat) for pat in _DOSSIER_SNAPSHOT_PATTERNS)
   ```
4. After computing the dirty-files list, filter it:
   ```python
   dirty_files = compute_dirty_files(repo_root)  # whatever the existing call looks like
   filtered = [p for p in dirty_files if not _is_dossier_snapshot(p)]
   if filtered:
       raise DirtyWorktreeError(filtered)  # whatever the existing exception is
   ```
5. If `src/specify_cli/status/` has helpers that ALSO compute preflight dirty state (e.g., from `validate.py`, `doctor.py`, or a future `preflight.py`), apply the same filter consistently. If a new `src/specify_cli/status/preflight.py` is the natural home for the helper, place it there and import from `tasks.py`.
6. Verify behavior with a one-off manual repro:
   ```bash
   # Touch the snapshot path
   touch .kittify/dossiers/<some-slug>/snapshot-latest.json
   # The preflight should NOT report it as dirty.
   ```

**Files**: `src/specify_cli/cli/commands/agent/tasks.py` (modified, ~20–40 lines added). Optionally `src/specify_cli/status/preflight.py` (new file, ~30 lines) if that's the cleaner placement.

**Validation**:
- [ ] `_is_dossier_snapshot()` returns True for the documented snapshot paths.
- [ ] `_is_dossier_snapshot()` returns False for unrelated paths.
- [ ] The preflight no longer reports the snapshot as dirty.
- [ ] Real unrelated dirty files (e.g. an edit to `README.md`) still trigger the preflight failure (regression target for T012).

### Subtask T012 — Author the regression test

**Purpose**: Lock in the fix at the exact pre-flight path that previously blocked, per FR-011.

**Steps**:

1. Create `tests/integration/test_dossier_snapshot_no_self_block.py`.
2. Test 1: green path
   ```
   GIVEN a clean worktree on a mission with no other dirty state
   WHEN the dossier snapshot writer runs and creates snapshot-latest.json
   AND the very next call is `spec-kitty agent tasks move-task <wp> --to <lane>`
   THEN the move-task call succeeds (no DirtyWorktreeError)
   AND the snapshot file is left in place (not deleted, not auto-committed)
   ```
3. Test 2: control path (real dirty state still blocks)
   ```
   GIVEN a worktree where snapshot-latest.json was just written
   AND an unrelated file (say tests/integration/_fixture_dirty.txt) has uncommitted edits
   WHEN `agent tasks move-task` runs
   THEN it fails with a dirty-state error
   AND the error message names the unrelated file
   AND the error message does NOT name the snapshot
   ```
4. Use existing pytest fixtures and CLI helpers (e.g. `subprocess.run` against the spec-kitty CLI, or test-internal helpers). Mirror the patterns used in nearby integration tests.
5. Skip with a clear reason if the test environment cannot create a transient mission/worktree (the test should run in CI; do not write a flaky test).

**Files**: `tests/integration/test_dossier_snapshot_no_self_block.py` (new, ~120–160 lines).

**Validation**:
- [ ] Test 1 passes against the post-T010/T011 codebase.
- [ ] Test 2 passes against the post-T010/T011 codebase (i.e. real dirty state still blocks).
- [ ] If you temporarily revert T011's filter, Test 1 fails (proves the test is meaningful).

### Subtask T013 — Verify integration suite

**Purpose**: Confirm no collateral regressions in adjacent tests.

**Steps**:

1. Run:
   ```bash
   uv run pytest tests/integration -k 'dossier or move_task or dirty or transition' -q
   ```
2. All tests in the filtered set must pass.
3. If any unrelated test fails because it relied on the snapshot showing as dirty, fix the test's expectations (the new behavior is correct).

**Validation**:
- [ ] Filtered integration suite is green.

## Branch strategy

- **Planning/base branch**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: lane C per the tasks.md plan; assigned by `finalize-tasks`.

## Definition of Done

- [ ] `.gitignore` entry covers both possible snapshot path patterns.
- [ ] `_is_dossier_snapshot(path)` helper exists and is used in the dirty-state preflight in `agent tasks move-task` (and any peer status helper that computes the same gate).
- [ ] `tests/integration/test_dossier_snapshot_no_self_block.py` covers both the green path and the control case.
- [ ] `uv run pytest tests/integration -k 'dossier or move_task or dirty or transition' -q` passes.
- [ ] No changes to `src/specify_cli/dossier/snapshot.py` (the writer is unchanged — see contract D and research R5).
- [ ] `mypy --strict` clean.
- [ ] Only files in this WP's `owned_files` list were modified.

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent claude --mission charter-e2e-827-followups-01KQAJA0
```

## Reviewer guidance

- The fix MUST be belt-and-suspenders (gitignore + explicit filter). Reviewing only one is incomplete.
- The control case in T012 (real dirty state still blocks AND names the offending file) is essential — without it, the fix could mask a regression where dirty state silently passes.
- No changes to the snapshot writer (`src/specify_cli/dossier/snapshot.py`) are expected — the writer's behavior is intentionally unchanged.
- If the implementer puts the helper in `src/specify_cli/status/preflight.py` (new file), verify that file is registered in `__init__.py` exports if needed.

## Requirement references

- **FR-009** (single ownership policy applied).
- **FR-010** (move-task no longer self-blocks on snapshot writes).
- **FR-011** (regression coverage on the exact previously-blocking path).
- **C-006** (single ownership policy; no conditional dual-policy runtime branch).
- Contributes to **NFR-003** (verification matrix).

## Activity Log

- 2026-04-28T20:44:50Z – claude – shell_pid=73767 – WP03 ready for review: gitignore + explicit dirty-state filter + regression test
- 2026-04-28T20:45:32Z – claude:sonnet:python-pedro:reviewer – shell_pid=78452 – Started review via action command

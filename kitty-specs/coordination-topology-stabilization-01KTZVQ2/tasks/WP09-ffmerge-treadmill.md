---
work_package_id: WP09
title: ff-merge Treadmill Elimination
dependencies:
- WP01
- WP06
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "68084"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
execution_mode: code_change
owned_files:
- src/specify_cli/merge/executor.py
- tests/specify_cli/test_no_manual_ffmerge.py
priority: P3-Medium
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Roll out `advance_branch_ref` as the standard post-write primary-ref sync, so operators never need to run `git merge --ff-only` manually after a coordination-topology write. Retire the `_ensure_branch_checked_out` shim. Add a coord-owned-residue exclusion to prevent `advance_branch_ref` from aborting on valid residue.

**This WP depends on WP01 and WP06**: The coord-owned-residue exclusion must share the same exclusion list established by WP06's accept gate fix.

---

## Context

### The Bug (Issue #1878, ff-merge treadmill aspect)

After spec-kitty writes artifacts to the coordination branch, the primary checkout (`main`) is behind the coordination branch. Operators must manually run `git merge --ff-only kitty/mission-<slug>-<mid8>` to bring `main` forward. This is the "treadmill" — every write operation on the coordination branch requires a manual sync.

### `advance_branch_ref`

`advance_branch_ref` in `executor.py` already exists and handles this sync. But it's not called consistently after every coordination-branch write, and it currently refuses to run when coord-owned residue (e.g., `status.events.jsonl`, `status.json`, `tasks/.gitkeep`) is present in the working tree. The exclusion from WP06 solves the residue problem; rollout is then safe.

### `_ensure_branch_checked_out` Shim

`mission.py:2512–2515` contains `_ensure_branch_checked_out` — a workaround that switches to the right branch before writes. This is the shim that `advance_branch_ref` was meant to replace. Retiring it removes a complexity layer and is only safe after `advance_branch_ref` is stable and tested.

---

## Subtasks

### T041 — Add coord-owned-residue exclusion to `advance_branch_ref`

1. Read `src/specify_cli/merge/executor.py` for `advance_branch_ref`.
2. Import or replicate the `ACCEPT_OWNED_PATHS` exclusion set from WP06 (share the same constant — do not duplicate it).
3. In `advance_branch_ref`, before checking if the working tree is clean, filter out `ACCEPT_OWNED_PATHS` from the dirty-file check.
4. This ensures `advance_branch_ref` does not abort when `status.events.jsonl` or `status.json` is present as a known coord-owned path.

### T042 — Roll out `advance_branch_ref` as standard post-write primary-ref sync

1. Identify all coordination-branch write call sites in `executor.py` and `mission.py`.
2. After each write that commits to the coordination branch, add a call to `advance_branch_ref`.
3. If `advance_branch_ref` fails (e.g., primary checkout has diverged), log a warning but do NOT abort the write — the primary sync is a best-effort convenience, not a hard requirement.
4. Confirm the calls are idempotent (calling twice in the same state is a no-op).

### T043 — Retire `_ensure_branch_checked_out` shim

1. Read `src/specify_cli/missions/software_dev/mission.py` lines 2505–2520.
2. Confirm all callers of `_ensure_branch_checked_out` have been replaced by `advance_branch_ref` rollout (T042).
3. Remove `_ensure_branch_checked_out` function.
4. If any caller still needs it (e.g., a write that doesn't go through `executor.py`), update that caller to use `advance_branch_ref` before removing the shim.

### T044 — End-to-end test: zero manual ff-merges through full lifecycle

File: `tests/specify_cli/test_no_manual_ffmerge.py` (new)

Write a pytest test that:
1. Sets up a mission with coordination topology (coord branch + worktree).
2. Simulates a coordination-branch write (commit an artifact to the coord branch).
3. Asserts that after the write, `git log --oneline main..kitty/mission-<slug>` returns empty (primary is up to date — no manual ff-merge needed).
4. No manual `git merge --ff-only` call is made anywhere in the test setup.

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
# Only after WP01 and WP06 are approved/done:
spec-kitty agent action implement WP09 --agent <name>
```

---

## Definition of Done

- [ ] `advance_branch_ref` excludes `ACCEPT_OWNED_PATHS` from dirty-file check
- [ ] `advance_branch_ref` called after every coordination-branch write
- [ ] `_ensure_branch_checked_out` shim removed
- [ ] `test_no_manual_ffmerge.py` passes
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues

## Risks

- **`advance_branch_ref` failure tolerance**: If the primary checkout has local uncommitted changes, `advance_branch_ref` may fail. Use a graceful fallback (log warning, continue) rather than aborting the parent operation.
- **Shim removal ordering**: Do not remove `_ensure_branch_checked_out` until ALL callers are migrated and confirmed working. Run the full test suite after removal before committing.
- **Shared `ACCEPT_OWNED_PATHS` constant**: Define this in a shared location (`specify_cli/merge/constants.py` or `specify_cli/common.py`) so both WP06 and WP09 import the same constant without duplication.

## Activity Log

- 2026-06-13T08:26:22Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55911 – Assigned agent via action command
- 2026-06-13T08:35:56Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55911 – Ready for review: advance_branch_ref wired, ff-merge treadmill eliminated
- 2026-06-13T08:39:02Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=68084 – Started review via action command
- 2026-06-13T08:41:11Z – user – shell_pid=68084 – Review passed: all 4 tests pass, mypy clean (0 issues), ruff clean (0 issues), advance_branch_ref excludes COORD_OWNED_STATUS_FILES from dirty-file check, _try_advance_primary_ref wired after every COORDINATION-kind write, _ensure_branch_checked_out shim fully removed, noqa:BLE001 is narrowly scoped with inline rationale.

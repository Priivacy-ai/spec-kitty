---
work_package_id: WP06
title: Accept Gate Transactional Ownership
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "45161"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
execution_mode: code_change
owned_files:
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/acceptance/matrix.py
- src/specify_cli/cli/commands/accept.py
- tests/specify_cli/test_accept_gate_convergence.py
- tests/specify_cli/test_accept_no_commit_readonly.py
priority: P1-Critical
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Make `spec-kitty accept` idempotent and `--no-commit` truly read-only:

1. Fix `mutate_matrix` gate so `--no-commit` / diagnose mode does NOT write to `acceptance-matrix.json`.
2. Implement a write-aware dirty baseline: snapshot before any accept-owned write; exclude accept-owned derived paths from the git-status dirty check.
3. Call `_commit_residual_acceptance_artifacts` on ALL writing exit paths (not only the success path).
4. Fix the write-target split in `_check_lane_gates` so it uses the coord-resolved `feature_dir`.

**This WP depends on WP01**: The coord-aware `feature_dir` resolution in T028 requires the `placement`-aware `is_committed()` from WP01 to be in place.

---

## Context

### The Bug (Issue #1883)

Running `spec-kitty accept` twice in the same mission state produces different pass/fail results. Cause: `collect_feature_summary` takes a whole-tree `git status --porcelain` snapshot AFTER accept has already written `acceptance-matrix.json` and other residue. The second run sees those artifacts as dirty-tree changes, causing a false "dirty tree" failure.

Additionally, `accept.py:284` sets `mutate_matrix=not diagnose`, meaning even `--no-commit` mode writes to `acceptance-matrix.json`. After the run, `git status` is dirty.

### Key Code Locations

- `accept.py:284`: `mutate_matrix=not diagnose` → must gate on `commit_required` too
- `acceptance/__init__.py:934`: `collect_feature_summary` git-status snapshot
- `acceptance/__init__.py:752-754`: matrix write inside `mutate_matrix` guard
- `accept.py:74-108`: `_commit_residual_acceptance_artifacts` — only called on success path
- `accept.py:369-376`: success-path commit call

### Accept-Owned Derived Paths (exclusion list)

These paths are written by accept and must be excluded from the dirty-tree gate:
- `acceptance-matrix.json`
- `status.json` (daemon-materialized view)
- `kitty-specs/<slug>/` residue committed on success path
- Any path matching the `#1814 pattern` exclusion list (check existing exclusions)

---

## Subtasks

### T025 — Fix `mutate_matrix` in `--no-commit` mode

1. Read `src/specify_cli/cli/commands/accept.py` lines 275–295.
2. Find the `mutate_matrix=not diagnose` assignment.
3. Change to: `mutate_matrix=(not diagnose and not no_commit)` (or `commit_required`).
   - `no_commit=True` → `mutate_matrix=False` (no matrix writes in read-only mode)
   - `diagnose=True` → `mutate_matrix=False` (existing behavior, preserved)
4. Confirm the `--no-commit` flag is named `no_commit` in the CLI parameter; adjust if different.
5. `mypy --strict` on `accept.py`.

### T026 — Implement write-aware dirty baseline

1. Read `src/specify_cli/acceptance/__init__.py` lines 920–960 (`collect_feature_summary`).
2. Move the `git status --porcelain` snapshot to BEFORE any matrix write or artifact mutation.
   - Add a `baseline_dirty_paths: set[str]` taken at entry to `accept` run.
3. In the dirty-tree gate check, exclude paths in `ACCEPT_OWNED_PATHS`:
   ```python
   ACCEPT_OWNED_PATHS = frozenset({
       "acceptance-matrix.json",
       "status.json",
   })

   dirty_paths = {
       p for p in current_dirty_paths
       if not any(p.endswith(owned) for owned in ACCEPT_OWNED_PATHS)
       and p not in baseline_dirty_paths  # exclude pre-existing dirty
   }
   ```
4. The gate should only fail if `dirty_paths` is non-empty AFTER excluding accept-owned paths.

### T027 — Call `_commit_residual_acceptance_artifacts` on ALL writing exit paths

1. Read `accept.py` lines 70–120 and 360–380.
2. Identify all writing exit paths:
   - Success path (already calls it at :369-376)
   - Failure/partial-success exit paths (e.g., `sys.exit(1)` after failed checks)
   - Exception paths (add a `try/finally` or `contextlib.ExitStack` guard)
3. Wrap the main accept body in a `try/finally`:
   ```python
   try:
       # existing accept logic
   finally:
       if commit_required:
           _commit_residual_acceptance_artifacts(...)
   ```
4. Ensure `_commit_residual_acceptance_artifacts` is idempotent: calling it on a clean state (nothing to commit) must not error.

### T028 — Fix write-target split in `_check_lane_gates`

1. Read `acceptance/__init__.py` for `_check_lane_gates` (or similar name).
2. Find where `feature_dir` is resolved for write targets.
3. Pass the coord-resolved `feature_dir` (using the placement resolver from WP01) instead of the primary checkout path.
4. This ensures the accept gate writes to the correct location when coordination topology is active.

**Prerequisite**: WP01 must be in `approved` or `done` lane before this subtask can be implemented correctly.

### T029 — Convergence regression test

File: `tests/specify_cli/test_accept_gate_convergence.py` (new)

Write a pytest test that:
1. Sets up a mission with a known acceptance state.
2. Runs `spec-kitty accept` (or the core accept function) in a temp repo.
3. Runs it a SECOND time in the same state.
4. Asserts both runs produce the same `pass`/`fail` result.
5. Asserts `git status --porcelain` shows no unexpected dirty files after the second run.

### T030 — `--no-commit` read-only regression test

File: `tests/specify_cli/test_accept_no_commit_readonly.py` (new)

Write a pytest test that:
1. Captures `git status --porcelain` output before running accept in `--no-commit` mode.
2. Runs `spec-kitty accept --no-commit`.
3. Captures `git status --porcelain` output after.
4. Asserts the two outputs are byte-for-byte identical (no new dirty files).

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
# Only after WP01 is approved/done:
spec-kitty agent action implement WP06 --agent <name>
```

---

## Definition of Done

- [ ] `mutate_matrix` is False in `--no-commit` and `diagnose` modes
- [ ] Baseline git-status snapshot taken before any accept write
- [ ] Accept-owned derived paths excluded from dirty-tree gate
- [ ] `_commit_residual_acceptance_artifacts` called on ALL writing exit paths
- [ ] Write-target uses coord-resolved `feature_dir`
- [ ] `test_accept_gate_convergence.py` passes (two-run convergence)
- [ ] `test_accept_no_commit_readonly.py` passes (no dirty files after `--no-commit`)
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues

## Risks

- **`try/finally` in accept**: If `_commit_residual_acceptance_artifacts` itself fails, the `finally` block must not swallow the original exception. Log the residue-commit failure; re-raise the original.
- **Daemon materialization race**: `status.json` may be re-written by a concurrent daemon after the baseline snapshot. The exclusion list handles this, but confirm `status.json` is in `ACCEPT_OWNED_PATHS`.
- **Encoding-normalization retry path** (`scripts/tasks/tasks_cli.py:157-191`): May cause a same-run self-defeat that this fix doesn't address. Explicitly defer to a follow-up if it's not in scope.

## Activity Log

- 2026-06-13T08:15:34Z – claude:sonnet-4-6:implementer:implementer – shell_pid=17617 – Assigned agent via action command
- 2026-06-13T08:22:49Z – claude:sonnet-4-6:implementer:implementer – shell_pid=17617 – Ready for review: accept gate made transactional and convergent
- 2026-06-13T08:23:19Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=45161 – Started review via action command
- 2026-06-13T08:25:56Z – user – shell_pid=45161 – Review passed: accept gate convergent, no-commit read-only, residual commit in finally, coord-resolved feature_dir

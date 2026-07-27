---
work_package_id: WP04
title: Idempotent mission-number assignment
dependencies: []
requirement_refs:
- FR-010
- FR-011
- FR-012
planning_base_branch: fix/3.2.x-review-merge-gate-hardening
merge_target_branch: fix/3.2.x-review-merge-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.x-review-merge-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.x-review-merge-gate-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-review-merge-gate-hardening-3-2-x-01KRC57C
base_commit: fb6a45d54c20041636a147d70c43b3f6d94544b9
created_at: '2026-05-12T13:13:30.119599+00:00'
subtasks:
- T024
- T025
- T026
- T027
agent: "claude:opus:reviewer:reviewer"
shell_pid: "479487"
history:
- at: '2026-05-12'
  actor: planner
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/merge/
execution_mode: code_change
mission_id: 01KRC57CNW5JCVBRV8RAQ2ARXZ
mission_slug: review-merge-gate-hardening-3-2-x-01KRC57C
owned_files:
- src/specify_cli/merge/state.py
- src/specify_cli/merge/executor.py
- tests/merge/test_mission_number_idempotency.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load implementer-ivan
```

The profile establishes your identity (Implementer Ivan), primary focus (writing and verifying production-grade code), and avoidance boundary (no architectural redesign; no scope expansion beyond what this WP authorizes). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

`spec-kitty merge` resume after a partial-merge that committed `mission_number` must succeed without producing an empty mission-number commit. Add `mission_number_baked` flag to `MergeState`; short-circuit the assignment step when `meta.json.mission_number` already equals the computed value.

This WP fixes [#983](https://github.com/Priivacy-ai/spec-kitty/issues/983) and satisfies FR-010, FR-011, FR-012 in [`../spec.md`](../spec.md).

Reference contract: [`../contracts/merge-state-idempotency.md`](../contracts/merge-state-idempotency.md).

## Context

The mission-number-assignment step in `_run_lane_based_merge` (in `src/specify_cli/merge/executor.py`) runs inside the merge-state lock and writes `meta.json.mission_number = max(existing) + 1`. If the merge fails after this write but before final integration, `spec-kitty merge --resume` walks through the same step again. The current code attempts to re-write the same value, producing an "empty commit" that the merge state machine treats as a hard error.

Fix: idempotency check. If `meta.json.mission_number == expected_value` at the start of the step, skip the assignment and persist `MergeState.mission_number_baked = True`. On `--resume`, read the flag and short-circuit before reading `meta.json`.

The mission-identity work from #557 / mission 083 makes `mission_number` display-only (the canonical id is `mission_id`/ULID). That work already landed; this WP just adds the resume-after-partial behavior on top.

## Branch Strategy

- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Final merge target**: `main` (after PR review)
- **Execution worktree**: assigned by `spec-kitty implement WP04`. WP04 is independent; can run in parallel with WP02/WP05/WP06/WP07.

## Subtasks

### T024 — Add `mission_number_baked` to MergeState

**Purpose**: extend the existing `MergeState` dataclass so the assignment-completion flag survives across `spec-kitty merge` invocations.

**Steps**:

1. In `src/specify_cli/merge/state.py`, add the field with a default:
   ```python
   @dataclass
   class MergeState:
       # ... existing fields ...
       mission_number_baked: bool = False  # WP04 — set True once mission_number is committed
   ```
2. Verify `save_state` / `load_state` already serialize via `dataclasses.asdict` / `from_dict` (or whatever serializer the module uses). Add explicit (de)serialization if the existing pattern requires it.
3. Bump no schema version; the addition is backward-compatible (older state files load with `mission_number_baked=False`, which is the safe default).

**Files**: `src/specify_cli/merge/state.py`

**Validation**:
- [ ] Round-trip: `save_state(state); load_state(repo_root) == state` for a state where the flag is True.
- [ ] Older state files (without the flag) load with `mission_number_baked=False`.

### T025 — Implement idempotency check in the merge executor

**Purpose**: inside `_run_lane_based_merge`, the assignment step reads `meta.json.mission_number` before writing; skips the write + commit if already equal to expected.

**Steps**:

1. Locate the assignment step in `src/specify_cli/merge/executor.py`. Grep for `mission_number` writes:
   ```bash
   rg -n 'mission_number' src/specify_cli/merge/
   ```
2. Wrap the write in an idempotency check:
   ```python
   # Inside the merge-state lock:
   meta = json.loads((feature_dir / "meta.json").read_text())
   if meta.get("mission_number") == expected_number:
       # Already assigned; mark as baked and continue.
       state.mission_number_baked = True
       save_state(state)
       return
   # Otherwise, write meta.json.mission_number = expected_number; commit.
   ```
3. After successful write + commit, set `state.mission_number_baked = True` and persist.
4. **Keep the read+decide inside the existing merge-state lock**. Do not move it outside; the `max(existing) + 1` computation requires lock semantics.

**Files**: `src/specify_cli/merge/executor.py`

**Validation**:
- [ ] Fresh merge: assignment runs as before; flag set to True after success.
- [ ] Partial-merge resume: read shows `mission_number == expected`; no write; flag set to True; no empty commit.

### T026 — Update `--resume` flow to short-circuit when flag is True

**Purpose**: on `merge --resume`, before even entering the assignment step's read, check the persisted flag.

**Steps**:

1. In the executor's `_run_lane_based_merge` (or wherever the resume entry point is), at the place where the assignment step would begin, check:
   ```python
   if state.mission_number_baked:
       # Already baked on a previous run; skip the entire step.
       return
   ```
2. Place this check **before** the lock acquisition for the assignment step. The flag is persisted and survives across invocations; reading it doesn't need a lock.
3. Document the resume contract inline:
   ```python
   # NOTE: mission_number_baked is set after a successful idempotency check
   # OR a successful write. On resume, we trust the flag: if it says baked,
   # the persisted meta.json is correct, and we don't need to re-read it.
   ```

**Files**: `src/specify_cli/merge/executor.py`

**Validation**:
- [ ] Resume with `mission_number_baked=True` does not read `meta.json` for the assignment step.
- [ ] Resume with `mission_number_baked=False` runs the idempotency check from T025.

### T027 — Regression test for partial-merge resume

**Purpose**: prove the #983 scenario is fixed: partial-merge after mission-number commit, resume, no empty commit.

**Steps**:

1. Create `tests/merge/test_mission_number_idempotency.py`.
2. Test fixture: a temporary mission directory with `meta.json` and a synthetic merge-state. Simulate "first attempt wrote mission_number=115 then crashed":
   ```python
   def test_resume_after_partial_mission_number_commit_is_idempotent(tmp_repo):
       feature_dir = tmp_repo / "kitty-specs" / "test-mission-01ABCDEF"
       feature_dir.mkdir(parents=True)
       (feature_dir / "meta.json").write_text(json.dumps({
           "mission_id": "01ABCDEFGHIJKLMNOPQRSTUVWX",
           "mission_number": 115,
           "mission_slug": "test-mission-01ABCDEF",
       }))

       state = MergeState(
           feature_slug="test-mission-01ABCDEF",
           target_branch="main",
           wp_order=["WP01"],
           completed_wps=[],
           current_wp=None,
           has_pending_conflicts=False,
           strategy="merge",
           started_at="2026-05-12T00:00:00Z",
           updated_at="2026-05-12T00:00:00Z",
           mission_number_baked=False,
       )
       save_state(tmp_repo, state)

       # Simulate the assignment step running on resume.
       result = _run_assignment_step(tmp_repo, feature_dir, expected_number=115, state=state)

       # Assertions:
       assert result.skipped_due_to_idempotency is True
       assert state.mission_number_baked is True
       loaded = load_state(tmp_repo)
       assert loaded.mission_number_baked is True
       # No commit was made:
       assert git_log_count(tmp_repo) == git_log_count_before
   ```
3. Add a second test for the resume short-circuit: with `mission_number_baked=True`, the assignment step doesn't even read `meta.json`.
4. Add a third test for the fresh-merge happy path: with no prior assignment, the step writes + commits + sets the flag.

**Files**: `tests/merge/test_mission_number_idempotency.py` (new)

**Validation**:
- [ ] All three tests pass.
- [ ] Failure path (flag bypass disabled) reproduces the #983 bug — proves the test actually exercises the fix.

## Definition of Done

- [ ] T024–T027 acceptance checks pass.
- [ ] FR-010, FR-011, FR-012 cited in commits.
- [ ] No glossary entries required (no new canonical terms introduced).

## Risks and Reviewer Guidance

**Risk**: the idempotency check leaks outside the lock and races with a concurrent merge. **The check MUST be inside the merge-state lock.** Reviewer should verify the lock acquisition is around both the check and the write.

**Risk**: a stale `mission_number_baked=True` flag from a state where the meta.json was manually edited. Mitigation: T026's docstring documents the trust assumption; operators who manually edit `meta.json` are responsible for clearing the flag.

**Reviewer focus**:
- T025: lock placement.
- T027: does the regression test actually reproduce #983 without the fix?

## Suggested implement command

```bash
spec-kitty agent action implement WP04 --agent claude --mission review-merge-gate-hardening-3-2-x-01KRC57C
```

## Activity Log

- 2026-05-12T13:13:31Z – claude:sonnet:implementer-ivan:implementer – shell_pid=463415 – Assigned agent via action command
- 2026-05-12T13:20:05Z – claude:sonnet:implementer-ivan:implementer – shell_pid=463415 – WP04 ready: idempotency check inside lock + resume short-circuit + regression test
- 2026-05-12T13:20:30Z – claude:opus:reviewer:reviewer – shell_pid=479487 – Started review via action command
- 2026-05-12T13:22:15Z – claude:opus:reviewer:reviewer – shell_pid=479487 – Review passed: FR-010 idempotency check verified INSIDE __global_merge__ lock (merge.py:514-528 called from _run_lane_based_merge_locked); FR-011 flag persisted after write at merge.py:589; FR-012 resume short-circuit at merge.py:380 fires before any I/O; T024 backward-compat from_dict filters unknown keys; T027 5/5 tests pass, partial-merge test honestly reproduces #983 if check is reverted (commit-count assertion); full tests/merge/ suite green (163 passed); scope clean (3 owned files).

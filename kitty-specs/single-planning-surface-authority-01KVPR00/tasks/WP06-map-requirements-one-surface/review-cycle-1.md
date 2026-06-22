---
verdict: approved
reviewer: reviewer-renata
cycle: 1
---

# WP06 Review — Cycle 1 (reviewer-renata)

**Verdict: APPROVED.** FR-008 (#2064) read-surface consolidation + FR-005 (#2069)
predicate routing land cleanly in the one owned file (`tasks.py`) plus a
non-fakeable regression test. The #2064 red proof was reproduced independently
(not trusted from pasted output).

## Per-criterion findings

### 1. Read-surface consolidation (FR-008) — PASS
- `map_requirements` now resolves the WP `tasks/` dir via the new
  `_map_requirements_feature_dir` helper → `resolve_feature_dir_for_mission`
  (the `resolve_action_context(action="tasks")` seam that `finalize_tasks` and the
  rest of `tasks.py` already use). **One** read surface for both commands.
- `resolve_feature_dir_for_slug` has **zero** call sites in `tasks.py` (verified by
  grep: only 2 docstring/comment mentions remain). The divergent :3633 call is GONE.
- `compute_coverage` untouched (0 hits in the WP06 diff) — scope guard honored.

### 2. THE non-fakeability check (T033 / DIR-041) — PASS (red reproduced)
- I **independently restored** the divergent `resolve_feature_dir_for_slug` path in
  `_map_requirements_feature_dir` and re-ran the suite. Result:
  `test_map_and_finalize_agree_on_coord_topology` went **RED** at line 151:
  `map=.../kitty-specs/single-planning-surface-authority` (PRIMARY, no mid8) vs
  `finalize=.../.worktrees/single-planning-surface-authority-01KVPR00-coord/...`
  (COORD). This is exactly the #2064 desync. Edit reverted; working tree clean.
- The test also carries the structural divergence assertion (option a):
  `test_pre_fix_resolvers_diverge_on_coord_topology` asserts the two PRE-fix
  resolvers return DIFFERENT Paths on the coord fixture (slug→PRIMARY,
  for_mission→COORD), AND the agreement test asserts SAME Path post-fix.
- Production-shaped identity: full 26-char ULID `mission_id`, real `<slug>-<mid8>`
  coord worktree form, operator handle is the bare slug (the exact form that makes
  `mid8_from_slug` empty and the divergent resolver miss the coord worktree).
- 5/5 new tests pass on the fixed tree; existing `test_requirement_mapping.py`
  (23 tests) green — no regression.

### 3. FR-005 routing (T032) — PASS
- The `placement.kind is CommitTargetKind.COORDINATION` read at
  `_review_currency_check_branch` (now :364) is replaced by
  `routes_through_coordination(placement)`. The predicate is literally
  `return target.kind is CommitTargetKind.COORDINATION` — provably behavior-identical.
- `CommitTargetKind` type NOT deleted; `CommitTarget(..., kind=CommitTargetKind.PRIMARY)`
  constructions at :2439/:3077/:3645 preserved. T034 unit tests directly exercise the
  branch (COORDINATION → placement.ref; PRIMARY/FLATTENED → target_branch).

### 4. Error-message preservation (Risk #1) — PASS
- On `ActionContextError` the helper returns `candidate_feature_dir_for_mission(...)`
  (a non-existent candidate path), so the existing `if not feature_dir.exists():`
  guard fires the unchanged `"Mission directory not found: {feature_dir}"` message.
  The typed seam exception does not leak. Error-class contract preserved.

### 5. Gates — PASS
- `ruff check` clean on both `tasks.py` and the new test file.
- `mypy` clean: "Success: no issues found".
- Complexity ≤15 (C901 passes on `tasks.py`).
- No new S1192 (the `"Mission directory not found"` literal is pre-existing, not
  duplicated by WP06).
- No suppressions added (no `noqa` / `type: ignore` / sonar in the WP06 diff).
- `spec.md` PRIMARY-input read unchanged (still via `primary_dir`).
- Scope = `tasks.py` + new test only. `mission.py` NOT touched — and the
  consolidation did **not** require an out-of-scope `mission.py` edit, so there is
  no coverage gap.

## Notes
- WP06 commit (`c158ec769`) touches exactly 2 files: `tasks.py` (+41) and the new
  `tests/specify_cli/test_requirement_mapping_coord_surface.py` (+217). The lane
  stacks WP00–WP05 underneath (stale pre-#2081 base); review scoped to the WP06
  commit only, per orchestrator note that `tasks.py` is byte-identical at base.
- `routes_through_coordination` resolves from the worktree's `mission_runtime`
  (WP01 export, present in this lane); the editable-install pointing at the primary
  src is a stacked-lane artifact, not a WP06 defect.
- Pre-existing `test_mission_runtime_surface.py::test_public_surface_matches_contract`
  (WP01 symbol gap) is NOT a WP06 defect — orchestrator handles at pre-merge.

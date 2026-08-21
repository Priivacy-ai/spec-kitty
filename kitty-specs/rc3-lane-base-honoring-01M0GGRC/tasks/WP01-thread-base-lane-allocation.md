---
work_package_id: WP01
title: Thread --base into lane allocation; fail loud; honor base at the for_review gate
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: rc3-lane-base-honoring-01M0GGRC
merge_target_branch: rc3-lane-base-honoring-01M0GGRC
branch_strategy: Planning artifacts for this mission were generated on rc3-lane-base-honoring-01M0GGRC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-lane-base-honoring-01M0GGRC unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-lane-base-honoring-01M0GGRC
base_commit: 60e0a2ad31b54255cc981f4f4340d94b89110a9f
created_at: '2026-08-21T12:48:04.401313+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
history:
- at: '2026-08-21T12:29:22Z'
  actor: spec-kitty tasks
  note: WP created — atomic P0 --base honoring fix
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent:
- tests/specify_cli/lanes/test_lane_base_honoring.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/lanes/worktree_allocator.py
- src/specify_cli/lanes/implement_support.py
- src/specify_cli/lanes/for_review_gate.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/lanes/test_worktree_allocator_coord.py
- tests/specify_cli/lanes/test_lane_base_honoring.py
- tests/cli/commands/test_implement_base_flag.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Then load action-scoped governance:

```bash
spec-kitty charter context --action implement --json
```

Apply the resolved initialization, boundaries, directives, and tactics. State which you applied.
You are an **implementer**: red-green-refactor, run the full local gate (ruff + mypy --strict +
targeted pytest) before handoff, no `# noqa`/`# type: ignore`.

## Objective

Fix #3571 (P0): `spec-kitty implement --base <ref>` is silently ignored on coord-topology missions
(the default). The override is smuggled through `lanes_manifest.mission_branch`, which the coord
allocation path never reads. Thread an explicit `base` parameter into the topology-aware
`allocate_lane_worktree` (via `create_lane_workspace`), hard-error where the base cannot be honored,
and make the `for_review` gate measure against the lane's actual honored base. **Preserve the legacy
route (#1684) exactly on the `base=None` path.**

Read `spec.md` (FR-001..011, D1/D2/D3, AC-1..4), `plan.md` (design + FR→site map + Test plan), and
`research.md` (decisions) in this mission dir. The live repro is at
`evidence/repro_3571_live_main.py`; the post-spec/post-plan squad findings are in
`evidence/post-spec-squad-findings.md`.

## Branch Strategy

- **Planning base**: `main`. **Merge target**: `main`.
- The execution worktree for this WP is allocated per computed lane from `lanes.json` by
  `spec-kitty implement WP01`. Do NOT reconstruct the worktree path.
- Run: `spec-kitty agent action implement WP01 --agent claude`.

## Context: the two-route root cause (code-verified against upstream/main)

- `implement.py:_resolve_active_lanes_manifest` (~1391) validates `--base`, prints
  `→ Using explicit base ref` (~1411, BEFORE allocation — the fabricated success line), and patches
  `mission_branch=base` (~1412). It is **topology-blind** (branches only on `is_planning_lane`).
- `allocate_lane_worktree` (`worktree_allocator.py:136`) is **topology-aware**
  (`_read_coordination_branch`). Coord fresh-create parents on `coordination_branch` (:260-264);
  the legacy `else` reads `mission_branch` (:272-276). Reuse early-return at :191; crash-recovery
  re-attach at :235.
- `create_lane_workspace` (`implement_support.py:48`, only caller `implement.py:~1886`) records base
  provenance from `lanes_manifest.mission_branch` (:112 reuse-detect, :117 `base_branch`, :130
  `base_commit`, :138 frontmatter, :156 `WorkspaceContext`, :174 result).
- Second production caller: `orchestrator_api/commands.py:903` (passes no base — inert).
- `for_review_gate.resolve_lane_base_ref` (~55) resolves the base as the coordination branch.

---

### Subtask T001 — Red-first AC-1 seam-level test (RED on upstream/main)

**Purpose**: Prove #3571 through the REAL `implement --base` wiring (C-003), not the allocator in
isolation. This test is written FIRST and must be symptom-RED on `upstream/main`.

**Steps**:
1. Create `tests/specify_cli/lanes/test_lane_base_honoring.py` with `pytestmark = [pytest.mark.unit,
   pytest.mark.git_repo]` (matches `test_worktree_allocator_coord.py`; both markers are CI-routed).
2. Build a coord-topology fixture (mirror `test_worktree_allocator_coord.py`'s `new_topology_repo`):
   `meta.json` carries `coordination_branch`; the coord branch descends from an unrelated commit `U`;
   a divergent `explicit-base` branch `B` does NOT contain `U`.
3. **MANDATORY red-first entry (post-tasks reviewer HIGH):** drive base through the **in-process
   `implement(...)` CLI entry** (as the existing `test_implement_base_flag.py` does — invoke the Typer
   command function with `base="explicit-base"`, `wp_id`, mission). `--base` is then a stable EXTERNAL
   input on both trees. **PROHIBITED as the C-003 proof:** the manual `_resolve_active_lanes_manifest(...)
   → create_lane_workspace(...)` chain — on `upstream/main` `create_lane_workspace` has no `base` param
   (TypeError = false-red), and post-fix a base-less `create_lane_workspace` call would stay RED forever,
   tempting an implementer to *retain the smuggle* and leave #3571 unfixed under a green test.
4. Assert `git merge-base --is-ancestor B <lane>` **succeeds** and `--is-ancestor U <lane>` **fails**.
5. **Fixture-fidelity gate** (post-plan reviewer): assert the fixture genuinely carries coordination
   topology (so `_read_coordination_branch` returns non-None) and that the RED is *wrong-ancestry*,
   not *no-coordination-branch* (a degraded-to-legacy fixture would honor `mission_branch=B` on main
   and go falsely GREEN).
6. **NFR-003 positive composition (post-tasks reviewer MED):** in a separate no-dep test with a base `B'`
   that SHARES an ancestor with the recorded planning commit, assert that BOTH `B'` AND the merged
   planning commit are ancestors of the lane (the "planning commit composes on top of base" guarantee,
   distinct from FR-010's detached-fail case).

**Validation**: on `upstream/main` (PYTHONPATH to the worktree src), the in-process `implement(--base)`
test FAILS on ancestry (symptom-red), NOT with a `TypeError`. Capture that output for the swap-back proof.

**Covers**: AC-1, FR-001, FR-002, NFR-003, C-003.

### Subtask T002 — Thread the explicit `base`; drop the smuggle; record the true honored parent

**Purpose**: Bind `--base` to the field the dominant path reads; keep provenance accurate.

**Steps**:
1. `allocate_lane_worktree(...)` and `create_lane_workspace(...)` gain `base: str | None = None`
   (defaulted — NFR-005, keeps ~30 existing call sites green). Thread `base=base` from
   `create_lane_workspace` (`implement_support.py:92`) into the allocator.
2. In `_resolve_active_lanes_manifest` (`implement.py`): STOP patching `mission_branch=base`. Instead
   pass `base` down to `create_lane_workspace(..., base=base)` from the call site (~1886). Keep the
   `_validate_base_ref` validation and the repo-root planning-lane "ignored" warning branch (FR-007).
3. Coord fresh-create (`worktree_allocator.py:260-264`), **no-dependency** lane: parent on `base` when
   supplied, else `coordination_branch` (D1 — base ALONE, coord not layered on).
4. **Record the ACTUAL honored parent** into `base_branch` provenance (`implement_support.py`): `base`
   when supplied, else the topology parent the allocator used (`coordination_branch` for coord,
   `mission_branch` for legacy). Keep this distinct from the `mission_branch` field that
   `_report_workspace_created` prints as "Mission branch:" (do NOT feed base into `mission_branch` —
   post-plan architect LOW, else the honored-base run mislabels base as the mission branch). Update the
   reuse-detection base (`_has_commits_beyond_base`, :112) to use the honored base too.

**Validation**: AC-1 seam test goes GREEN; provenance `base_branch` == honored parent.

**Covers**: FR-001, FR-002, FR-003.

### Subtask T003 — `UnhonorableBaseError(StructuredError)` + four pre-side-effect fail-loud sites

**Purpose**: Hard-error (never warn-continue, never a success line) where the base cannot be honored.

**Steps**:
1. Add `class UnhonorableBaseError(StructuredError)` to `worktree_allocator.py` (import from
   `specify_cli.core.errors`; it is a `RuntimeError` subclass — matches siblings
   `DependencyLaneMergeConflictError`/`PlanningCommitMergeConflictError`). `error_code="UNHONORABLE_BASE"`.
   **Build the message and payload INSIDE the exception** (post-tasks implementer, S1192): `__init__(self,
   *, route, wp_id, base)` stores the three, composes `str(self)`, and `to_dict()` returns
   `{error_code, route, wp_id, base}`. Every raise site then reads `raise UnhonorableBaseError(route=...,
   wp_id=wp_id, base=base)` — no inlined f-strings duplicated across the 4 sites. Give it a public-API
   docstring (DIR-007).
2. **Extract two helpers (post-tasks implementer, Sonar S3776 cognitive-nesting — the 4 guards sit inside
   already-nested arms, projecting into the 13–16 band):**
   - `_guard_base_honorable(base, route, wp_id, *, lane=None, planning_sha=None, repo_root=None)` — the
     one place that raises `UnhonorableBaseError`; called at each site so the branch bodies stay flat.
   - `_resolve_lane_parent(base, coordination_branch, mission_branch)` — the ternary parent selection.
   Both keep ruff C901 (~9) and Sonar comfortable AND become directly unit-testable (Sonar new-code cover).
3. Raise (via `_guard_base_honorable`), **before each block's side effects**, when `base is not None` at:
   - **FL1 reuse** (`:191`, `worktree_path.exists()`): raise before `_validate_worktree_clean`/merges.
   - **FL2 crash-recovery** (`:235`, `_branch_exists`): raise before `git worktree prune`/re-attach.
   - **FL3 dependency lane** (coord fresh-create, `lane.depends_on_lanes` non-empty): raise before
     `_create_lane_worktree` (FR-009/D2 — re-parenting coord-descended dep tips onto base is M8's seam).
   - **FL4 detached base** (FR-010): a **PRE-CREATE** guard — `git merge-base <base> <planning_commit_sha>`
     returns empty (no common ancestor) ⇒ raise BEFORE `_create_lane_worktree`, so nothing is created.
     (Do NOT place this inside `_merge_recorded_planning_commit` post-create — that leaves a half-created
     worktree and wedges a retry on FL1. Post-plan architect HIGH.)
4. **`__all__` (post-tasks reviewer):** `worktree_allocator.py` has **no `__all__` today** and 16 modules
   import from it by name. Do NOT add a single-entry `__all__=["UnhonorableBaseError"]` (it would hide
   `allocate_lane_worktree` + siblings from `import *` and trip the C-007 gate). Either omit the export
   step (follow the module's no-`__all__` convention) OR add a COMPLETE `__all__` enumerating the existing
   public surface plus the new error.
5. **Machine-readable envelope (post-tasks implementer HIGH):** `_fail` (`orchestrator_api/commands.py`)
   hard-codes the top-level `error_code` to its positional `"LANE_ALLOCATION_FAILED"` and does NOT read
   `exc.error_code`/`to_dict()`. So merge `getattr(exc, "to_dict", lambda: {})()` (or at least
   `exc.error_code` + route/wp_id/base) into the `_fail` **data** payload at the allocation catch site
   (`commands.py` is owned). The T007 envelope test asserts on `data["error_code"] == "UNHONORABLE_BASE"`,
   NOT the top-level code (which stays `LANE_ALLOCATION_FAILED`). Without this, `to_dict()` is dead new
   code. Also list `UnhonorableBaseError` in the except-tuple (documentary — the `RuntimeError` arm already
   catches it; the listing is not independently testable, verify by review not by the synthetic test).

**Validation**: AC-3 / FR-010 tests (T006/T007) prove each raise; no residual worktree after FL4; a focused
unit test asserts `UnhonorableBaseError(route=..., wp_id=..., base=...).to_dict()` carries all three keys.

**Covers**: FR-004, FR-009, FR-010, NFR-002, NFR-004.

### Subtask T004 — Legacy substitution; relocate+guard the success print; docstring

**Purpose**: Keep #1684 working; print the success line only on a genuinely honored path.

**Steps**:
1. Legacy `else` (`worktree_allocator.py:272-276`): feed the parent as `base if base is not None else
   lanes_manifest.mission_branch` into `_ensure_mission_branch` + `_create_lane_worktree`
   (behavior-preserving; `base=None` is byte-identical to today — C-005/FR-006).
2. Relocate `→ Using explicit base ref: <ref>` out of `_resolve_active_lanes_manifest` to AFTER the
   successful `create_lane_workspace` return in `implement.py` — insert at **~line 1897–1898** (after
   `workspace_path`/`branch_name` are bound, before `_start_wp_implementation_status`), inside the `try`.
   Guard: `if base is not None and not is_planning_lane(...)` (equivalently `result.execution_mode !=
   ExecutionMode.PLANNING_ARTIFACT`). It must NOT fire on `base=None`, planning lanes, the orchestrator
   path (silent), or before a fail-loud raise.
3. Fix the stale docstring at `worktree_allocator.py:450-453` to describe `base` arriving via the
   threaded param on both routes (no `mission_branch` smuggling reference) — FR-008.

**Validation**: AC-2 (legacy through the seam descends from the ref; `test_issue_1684_cross_lane_base.py`
green); AC-4 print present/absent.

**Covers**: FR-005, FR-006, FR-008, C-005.

### Subtask T005 — FR-011: for_review gate reads the recorded honored base

**Purpose**: Make the gate measure against the lane's actual parent (operator ruling; coord is the
default value, not a special case).

**Steps**:
1. **Read the recorded base in `evaluate_for_review_gate`** (post-tasks squad: it HAS `wp_id`;
   `resolve_lane_base_ref(main_repo_root, mission_slug, manifest)` does NOT — do not mis-place the read
   into the wp_id-less resolver). Load the WP's recorded honored base via `load_context(...)`
   (`WorkspaceContext.base_branch`, persisted in T002) keyed by the worktree dir name, and prefer it when
   present; else fall back through the existing `resolve_lane_base_ref` chain
   (`resolve_placement_only(STATUS_STATE).ref` coord → `mission_branch` → repo default). Never returns empty.
2. **No-regression pin**: for a default no-`--base` coord lane, the recorded base equals
   `coordination_branch` (T002 records the true parent), so the gate still measures against coord exactly
   as today.

**Validation**: T007 FR-011 tests — a `--base B` lane is gated with `rev-list B..HEAD`; a default coord
lane is still gated against `coordination_branch`.

**Covers**: FR-011, C-004.

### Subtask T006 — Tests: AC-2 legacy, AC-3 fail-loud, AC-4 both-directions

**Steps** (in `test_lane_base_honoring.py`, real state, NO mocking the allocator):
1. **AC-2**: legacy `--base` through the seam → lane descends from the supplied ref; assert existing
   `test_legacy_topology_skips_sparse_checkout` + `test_issue_1684_cross_lane_base.py` still pass.
2. **AC-3(a) reuse**: allocate a lane, then re-allocate the same lane with `base` → `UnhonorableBaseError`.
3. **AC-3(b) crash-recovery**: allocate, `rm -rf` the worktree dir, re-allocate with `base` →
   `UnhonorableBaseError`.
4. **AC-3(c) dep-lane**: a lane with non-empty `depends_on_lanes` + `base` → `UnhonorableBaseError`.
5. **AC-4**: success line PRESENT on the honored no-dep path; ABSENT on an error path; ABSENT on
   `base=None`; ABSENT on a planning-lane-with-base run (guard predicate). **Capture mechanism (post-tasks
   reviewer MED):** the line is emitted via `impl_mod.console.print` (a rich `Console`), NOT plain stdout —
   `capsys` would MISS it and make every ABSENT assertion vacuously pass. Patch `impl_mod.console.print`
   (as the existing invalid-ref test does) for BOTH directions, and add a **positive control** (assert
   some other expected line IS captured) so an empty capture cannot green the ABSENT case.

**Covers**: AC-2, AC-3, AC-4, FR-004, FR-005, FR-006, FR-009.

### Subtask T007 — Tests: FR-010 atomicity, FR-011 gate, NFR-004 envelope, FR-007 warning

**Steps**:
1. **FR-010**: detached-base fixture (base with no common ancestor to the planning commit) →
   `UnhonorableBaseError` AND no residual worktree/branch; an immediate retry does NOT hit FL1.
2. **FR-011**: `--base B` coord lane gated with `rev-list B..HEAD`; default no-base coord lane still
   gated against `coordination_branch` (no-regression).
3. **NFR-004**: orchestrator-api path — assert the envelope's **`data["error_code"] == "UNHONORABLE_BASE"`**
   (the top-level code stays `LANE_ALLOCATION_FAILED`; see T003 step 5) plus the route/wp_id/base data
   keys. Mock-inject the raise (orchestrator passes `base=None`; label the test as the defensive/synthetic
   catch it is).
4. **FR-007**: a planning lane with `--base` emits the yellow "ignored" warning and has NO allocation
   effect (no existing test covers this branch adjacent to the edit).

**Covers**: FR-007, FR-010, FR-011, NFR-004.

### Subtask T008 — Rewrite the pre-existing CLI test; gates; swap-back proof

**Steps**:
1. **Rewrite** `tests/cli/commands/test_implement_base_flag.py::test_implement_base_flag_creates_workspace_from_ref`:
   it currently asserts `used_manifest.mission_branch == "main"` (pins the RETIRED smuggle) and mocks
   `create_lane_workspace`. Convert it to assert base-THREADING (the `base` arg reaches
   `create_lane_workspace`/allocator) and STOP mocking `create_lane_workspace` for the honored-path
   claim. Also extend the allocator-unit companion in `test_worktree_allocator_coord.py`.
2. Run the gate: `ruff check .` (touched files), `mypy --strict` (touched files),
   `PWHEADLESS=1 .venv/bin/python -m pytest tests/specify_cli/lanes/ tests/lanes/
   tests/cli/commands/test_implement_base_flag.py -q`. Zero new issues, 0 regressions (NFR-001/002).
3. **Swap-back proof (C-003)**: with the fix applied + AC-1 green, `git stash` the product diff
   (`worktree_allocator.py` + `implement.py` + `implement_support.py` + `for_review_gate.py`) keeping the
   new test; run AC-1 → capture symptom-red; restore; run AC-1 → capture green. Post both on the PR.

**Covers**: NFR-001, NFR-002, NFR-005, C-003.

## Definition of Done

- All of FR-001..011, NFR-001..005 satisfied; AC-1..4 green.
- AC-1 proven RED on `upstream/main` and GREEN after (swap-back outputs captured).
- `ruff` + `mypy --strict` clean on touched files; `tests/specify_cli/lanes/` + `tests/lanes/` +
  `tests/cli/commands/test_implement_base_flag.py` green.
- Legacy route (#1684) unchanged on `base=None`; no residual worktree after any fail-loud.
- New test file declares `pytestmark = [pytest.mark.unit, pytest.mark.git_repo]` (both CI-routed markers;
  the marker-job-completeness gate is derived live from collection — no static baseline file to edit).
- FR-008 (docstring) is a code edit verified by review, not a test; the except-tuple listing is documentary
  (untestable — the `RuntimeError` arm already catches). Every OTHER FR/NFR/AC has a named subtask test.

## Reviewer guidance (opus)

- Verify the fail-loud sites raise BEFORE side effects (esp. FR-010 pre-create — no half-created worktree).
- Verify the success print cannot fire on `base=None`/planning/orchestrator/error paths.
- Verify legacy `base=None` is byte-identical (diff `_ensure_mission_branch`/`_create_lane_worktree` args).
- Verify the for_review no-regression: default coord lane still measured against `coordination_branch`.
- Verify no AC is satisfied by mocking the allocator (AC-3/AC-4 must use real state); confirm AC-4 captures
  via `impl_mod.console.print` (not `capsys`) with a positive control.
- Confirm the typed error is machine-readable in the orchestrator envelope via `data["error_code"] ==
  "UNHONORABLE_BASE"` (the `_fail` data payload merges `exc.to_dict()`), not merely a message substring.
- Confirm `allocate_lane_worktree` stayed under the Sonar cognitive-complexity ceiling (helpers extracted),
  and the red-first AC-1 test enters via the in-process `implement(--base)` CLI, not the manual
  `_resolve → create_lane_workspace` chain.

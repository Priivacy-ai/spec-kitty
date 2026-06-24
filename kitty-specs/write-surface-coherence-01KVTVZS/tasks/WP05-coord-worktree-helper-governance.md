---
work_package_id: WP05
title: Shared coord-worktree helper governance
dependencies:
- WP03
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: feat/write-surface-coherence
merge_target_branch: feat/write-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/write-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
phase: Phase 3 - Helper governance
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2971044"
history:
- at: '2026-06-23T19:28:09Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/cli/commands/agent/mission.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Shared coord-worktree helper governance

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/coordination/`.

---

## Objective

Once planning no longer transits the coordination worktree (WP02/WP03), the shared
coord-worktree helpers must be **correct for status-only coord writes**:
`_materialise_coord_worktree` staging, the `_try_advance_ref` ff-advance (#1878), and
the `is_coordination_artifact_residue_path` dirty-filter now apply only to COORD-partition
writes. Remove any **dead ff-advance on the planning path** and any **orphaned
`target_branch`** plumbing that only existed to carry planning commits through coord.

## Context & Constraints

Ground truth: [spec.md](../spec.md) FR-005, C-004; [plan.md](../plan.md) IC-03;
[research.md](../research.md) D-4 (the ff-advance previously fast-forwarded primary to a
coord HEAD mixing planning+status — that mix no longer happens).

Verified surfaces:
- `commit_router.py:139-150` — the `use_coord` branch (materialise) vs direct branch.
- `commit_router.py:198-200` — `if use_coord and target_branch: _try_advance_ref(...)`.
  After WP02, `use_coord` is False for primary kinds, so this ff-advance is **status-only**.
- `commit_router.py:214-263` — `_materialise_coord_worktree` (staging copy).
- `commit_router.py:358-392` — `_try_advance_ref`.
- `mission.py:752-806` — `_planning_commit_worktree`: after WP03 returns `(repo_root, paths)`
  for primary kinds; verify no dead coord-staging path remains reachable for planning.
- `mission.py:838-896` — `_enforce_analysis_report_write_preflight`: drops coord-owned
  residue via `is_coordination_artifact_residue_path` (`:870`).
- `artifacts.py:141-161` — `is_coordination_artifact_residue_path` / `kind_is_coordination_residue`.

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `feat/write-surface-coherence`
- **Merge target branch**: `feat/write-surface-coherence`

> Overlaps `commit_router.py`/`mission.py` with WP02/WP03; serialized by WP03→WP05.

## Subtasks & Detailed Guidance

### Subtask T020 – Govern staging + ff-advance for status-only coord writes

- **Files**: `commit_router.py`.
- **Steps**:
  1. Confirm `_materialise_coord_worktree` (214-263) and `_stage_artifacts_in_coord_worktree`
     (284-346) are now reached ONLY for COORD-partition kinds (after WP02 made `use_coord`
     kind-aware). **Add a RUNTIME guard (DECISION 8), not a comment**: at the
     `_materialise_coord_worktree` / staging entry, assert the artifact kind is NOT a
     primary-partition kind — `assert kind not in _PRIMARY_ARTIFACT_KINDS` (or a typed
     `RuntimeError`/guard raise if an `assert` would be stripped under `-O`; prefer a
     raised typed error so the invariant holds in production). The guard must thread/receive
     the kind into the staging path so it can check it. This makes "planning artifacts
     never reach coord staging" an enforced invariant, not a wish.
  2. The `_try_advance_ref` call (199) now fast-forwards the primary `target_branch` to a
     coord HEAD that carries ONLY status/bookkeeping — confirm the ff-advance's
     `coord_owned_filenames=COORD_OWNED_STATUS_FILES` exclusion (387) still matches what a
     status-only coord write produces.
- **Notes**: The semantics narrow from "advance primary to a planning+status coord HEAD"
  to "advance primary to a status-only coord HEAD". No behavior should change for status
  writes; the planning case is simply gone. The runtime guard in step 1 is covered by a
  test in T023 (a primary kind reaching staging raises).

### Subtask T021 – Remove dead ff-advance on the planning path; no orphaned param

- **Files**: `commit_router.py`, `mission.py`.
- **Steps**:
  1. Verify `_planning_commit_worktree` (mission.py:752-806) no longer has a reachable
     coord-staging branch for primary kinds (WP03 short-circuited it). If the
     `_stage_finalize_artifacts_in_coord_worktree` call (800-805) is now dead for the
     planning callers, remove the dead arm or narrow it to COORD callers only — do NOT
     leave dead code (Sonar / D-4).
  2. Audit the `target_branch` parameter threaded into `commit_for_mission` (91) and
     `spec_commit_cmd`'s `--target-branch` (117-124): it exists for the post-commit
     ff-advance. For primary-kind commits the ff-advance does not fire — confirm the param
     is still meaningful (it is, for the COORD callers and the status ff-advance) and is
     NOT orphaned. If a planning caller passes `target_branch` only for a now-dead advance,
     drop it.
- **Notes**: "No orphaned `target_branch` param" (D-4) — the param stays where the
  ff-advance is live (status/coord), and is removed where it only served the retired
  planning-on-coord advance.

### Subtask T022 – Confirm the residue dirty-filter stays correct

- **Files**: `artifacts.py` (read-only verification), `mission.py:838-896`.
- **Steps**:
  1. After WP01 moved SPEC/DATA_MODEL/RESEARCH/CHECKLIST to `_PRIMARY_ARTIFACT_KINDS`,
     `kind_is_coordination_residue` (artifacts.py:57-75) returns False for them — so
     `is_coordination_artifact_residue_path` no longer treats a stale primary `spec.md`/
     `data-model.md` as coord residue. **This is correct**: those files now LIVE on primary,
     so a primary copy is not residue — it is the real artifact. Confirm
     `_enforce_analysis_report_write_preflight` (mission.py:862-871) still drops only
     COORD-partition residue (status/issue-matrix/acceptance/analysis) from the dirty set.
  2. Verify `_COORD_RESIDUE_FILENAMES`/`_COORD_RESIDUE_DIRS` (artifacts.py:95-112) — those
     map filenames to kinds for the path-based residue check. SPEC/DATA_MODEL/RESEARCH/
     CHECKLIST entries there now map to PRIMARY kinds, so `kind_is_coordination_residue`
     returns False for them. Confirm this does not break the record-analysis preflight
     (which gates on genuine uncommitted edits — a now-primary spec edit SHOULD block the
     preflight as a real dirty file, which is the corrected behavior).
- **Notes**: This is the subtle correctness win the spec flags. Add a regression test
  (T023) proving a stale primary `spec.md` is NOT silently dropped as residue anymore.

### Subtask T023 – Red-first helper-governance test (DIRECTIVE_034)

- **Files**: `tests/specify_cli/` (commit_router / mission preflight test module).
- **Steps (red-first)**:
  1. Write the failing test FIRST through the pre-existing entry point:
     - A STATUS coord write (`commit_for_mission(..., kind=STATUS_STATE)`) on a coord
       fixture still materialises coord AND ff-advances `target_branch`.
     - A PLANNING commit (`kind=SPEC`) does NOT enter `_materialise_coord_worktree` and
       does NOT ff-advance (assert the coord worktree is not touched).
     - **Runtime-guard test (DECISION 8)**: if a primary-partition kind is forced into the
       staging entry, the runtime guard from T020 raises (assert the typed error / guard
       fires). This pins the "planning never reaches coord staging" invariant as enforced.
     - `is_coordination_artifact_residue_path("kitty-specs/<slug>/spec.md", mission_slug=...)`
       returns **False** post-fix (it returned True pre-fix when SPEC was a placement kind).
  2. Prove red where the behavior changes (the residue assertion flips True→False; assert
     the pre-WP01 value to demonstrate red).
  3. Realistic fixtures: real ULID/mid8, real coord worktree path.

## Test Strategy

- `pytest tests/specify_cli/ -k "commit_router or coord_worktree or residue or ff_advance or preflight" -q`.
- `ruff check` + `mypy` on owned files — zero issues, no dead code, no suppressions.

## Risks & Mitigations

- **Dead code left behind**: a now-unreachable coord-staging arm on the planning path.
  Mitigation: T021 audits and removes/narrows it.
- **Residue filter over-drop**: if the filter still treated a primary `spec.md` as residue
  it would silently pass a dirty tree. Mitigation: T022 + T023 confirm the corrected
  False return.
- **Status ff-advance regression**: narrowing must not break the #1878 status advance.
  Mitigation: T023 asserts the status path still ff-advances.

## Review Guidance

- Verify the coord-staging/ff-advance helpers fire ONLY for COORD-partition writes.
- Verify no dead planning-on-coord arm and no orphaned `target_branch` param remain.
- Verify the residue filter now returns False for primary planning artifacts, with a test.

## Activity Log

- 2026-06-23T19:28:09Z – system – Prompt created.
- 2026-06-23T23:16:33Z – claude:opus:python-pedro:implementer – shell_pid=2952793 – Started implementation via action command
- 2026-06-23T23:29:36Z – claude:opus:python-pedro:implementer – shell_pid=2952793 – Runtime DECISION-8 guard added to _materialise_coord_worktree (raises PrimaryKindReachedCoordStagingError on primary kind), kind threaded through; ff-advance confirmed coord/status-only (no dead planning ff-advance); residue-ripple pinned (real predicate). Red-first proven for both new tests. 24 touched-area + 18 arch tests green. 8 selector failures PRE-EXISTING WP01-03 ripple (stash-confirmed). diff-scoped ruff exit 0; mypy clean. --force used for inherited-kitty-specs dirty tasks.md (mark-status checkbox update).
- 2026-06-23T23:31:16Z – claude:opus:reviewer-renata:reviewer – shell_pid=2971044 – Started review via action command
- 2026-06-23T23:45:35Z – user – shell_pid=2971044 – Review passed (reviewer-renata). Diff scoped to commit_router.py + 2 test modules; artifacts.py untouched (WP01-owned docstring deferral OK). TESTS RE-RUN GREEN: 18/18 in test_commit_router.py + test_wp05_mission_coordination_routing.py; tests/architectural/ 454 passed (4 pre-existing fails ref merge.py/tasks.py/mission_state.py NOT WP05 surface, persist with commit_router reverted to parent). GUARD VERIFIED: DECISION-8 real typed raise PrimaryKindReachedCoordStagingError (holds under -O), kind threaded into _materialise_coord_worktree; red-first proven (neutralize guard -> DID NOT RAISE). RESIDUE RIPPLE: real predicate no stub, spec.md=False status.events.jsonl=True; tests assert behavior not structure. T021: single _try_advance_ref gated use_coord+target_branch; planning short-circuits _planning_commit_worktree:793 so coord-staging arm narrowed not dead; no orphaned param. ruff+mypy clean. 8-PRE-EXISTING CONFIRMED via revert: reverting WP05 commit_router to parent yields identical 8 failures (wp06_sc2/test_acceptance/charter_preflight/merge_residue_gate_wp13[plan.md]) WP01-03 residue fallout re-pinned at WP07/merge; WP05 introduces 0 new failures. --force used for inherited flat-mission kitty-specs-on-lane guard.

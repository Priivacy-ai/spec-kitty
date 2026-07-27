# Tasks: Write-Surface Coherence

**Mission**: write-surface-coherence-01KVTVZS
**Branch**: `feat/write-surface-coherence`
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [data-model.md](./data-model.md) · [contracts/placement-bifurcation.md](./contracts/placement-bifurcation.md) · [research.md](./research.md)

Make the **write side** of the planning lifecycle kind-aware (the read side already
is via `MissionArtifactKind` / `artifact_home_for`), and **re-partition** the
planning + identity kinds onto the primary `target_branch` for every topology shape.
Status/bookkeeping kinds stay on the coordination branch for coord topology. The
frozenset partition (`_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` in
`src/mission_runtime/artifacts.py`) is the single swappable locus (NFR-004).
Forward-only (C-003); behavior-neutral for flattened missions (NFR-001).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `_PRIMARY_ARTIFACT_KINDS` frozenset; move planning+identity kinds out of `_PLACEMENT_ARTIFACT_KINDS` | WP01 | — |
| T002 | Make `artifact_home_for` route primary kinds → primary write/commit | WP01 | — |
| T003 | Make `resolve_placement_only` kind-aware (accept `MissionArtifactKind`, internal seam) | WP01 | — |
| T004 | Confirm partition membership of `LANE_STATE`/`ACCEPTANCE_MATRIX`/`ANALYSIS_REPORT` | WP01 | — |
| T005 | Red-first partition unit tests (SPEC→target_branch, STATUS_STATE→coord; flat unchanged) | WP01 | — |
| T006 | Thread REQUIRED `kind` through `commit_for_mission` (no default — DECISION 1) | WP02 | — |
| T007 | `spec_commit_cmd` + `_commit_artifact_to_branch` callers pass kind | WP02 | — |
| T008 | mission.py inline commit tails (~2345/2392/3825) + record-analysis (~1919) pass kind | WP02 | — |
| T009 | tasks.py `map-requirements` caller passes kind; acceptance meta commit passes `PRIMARY_METADATA` | WP02 | — |
| T010 | Remove the planning→coord route in the router `use_coord` arm | WP02 | — |
| T011 | Red-first caller-convergence test (planning caller → primary on coord fixture) | WP02 | — |
| T031 | Thread explicit `kind` at all 7 `resolve_placement_only` sites (status/base reads stay coord) | WP02 | — |
| T032 | Converge direct-`safe_commit` planning writers (`tasks.py:2438/3076`) + retire `_skip_target_commit` 2nd router | WP02 | — |
| T012 | `_resolve_mission_aware_target` (safe-commit) consults the kind authority | WP03 | — |
| T013 | `append-history` (`commands.py:1283/1340`) consults the kind authority | WP03 | — |
| T014 | Converge `_planning_commit_worktree` (`mission.py:775`) onto the partition | WP03 | — |
| T015 | FR-008: refuse a primary-kind commit to a protected `target_branch` | WP03 | — |
| T016 | Red-first bypass-writer + protected-primary tests | WP03 | — |
| T017 | Stop the read path consulting the coord husk for primary-partition kinds | WP04 | ∥ WP02/03 |
| T018 | Preserve C-005 KEEP transients (#1718 create-window, #1848 coord-deleted) | WP04 | ∥ WP02/03 |
| T019 | Red-first stale-coord-shadow test (#2062 class) for a planning artifact | WP04 | ∥ WP02/03 |
| T020 | Govern `_materialise_coord_worktree` staging + `_try_advance_ref` for status-only coord writes | WP05 | — |
| T021 | Remove dead ff-advance on the planning path; no orphaned `target_branch` param | WP05 | — |
| T022 | Confirm residue dirty-filter (`is_coordination_artifact_residue_path`) stays correct | WP05 | — |
| T023 | Red-first helper-governance test (status coord write still ff-advances; planning does not transit) | WP05 | — |
| T024 | Route the ~3 inline `json.loads(meta…read_text())` reads in mission.py through canonical `load_meta` | WP06 | — |
| T025 | Name/reconcile the duplicate `load_meta` at `task_utils/support.py:363` | WP06 | — |
| T026 | SC-004 contract-pinned test (canonical `load_meta` is the import; zero inline reads in touched modules) | WP06 | — |
| T027 | Behavioral two-ref guard across `commit_for_mission` + a bypass writer + `_planning_commit_worktree` | WP07 | — |
| T028 | Flattened-regression proof (NFR-001) | WP07 | — |
| T029 | FR-007 end-to-end coord-topology mission maps 100% requirements | WP07 | — |
| T030 | FR-008 protected-primary refusal end-to-end | WP07 | — |

---

## WP01 — Kind-aware placement authority + re-partition

**Prompt**: [tasks/WP01-kind-aware-placement-authority.md](tasks/WP01-kind-aware-placement-authority.md)

**Summary**
- **Goal**: Make the write-side placement consult the existing `MissionArtifactKind` model and re-partition the planning + identity kinds onto primary by introducing `_PRIMARY_ARTIFACT_KINDS`. The frozenset partition is the single swappable locus (NFR-004).
- **Priority**: P0 — foundation; every other WP depends on it.
- **Independent test**: Unit test on `artifact_home_for` / `resolve_placement_only` over a coord-topology fixture: `SPEC` → `target_branch`, `STATUS_STATE` → coordination, flat unchanged.

**Tracking**
- [x] T001 Add `_PRIMARY_ARTIFACT_KINDS` frozenset; move planning+identity kinds out of `_PLACEMENT_ARTIFACT_KINDS` (WP01)
- [x] T002 Make `artifact_home_for` route primary kinds → primary write/commit (WP01)
- [x] T003 Make `resolve_placement_only` kind-aware (accept `MissionArtifactKind`, internal seam) (WP01)
- [x] T004 Confirm partition membership of `LANE_STATE`/`ACCEPTANCE_MATRIX`/`ANALYSIS_REPORT` (WP01)
- [x] T005 Red-first partition unit tests (SPEC→target_branch, STATUS_STATE→coord; flat unchanged) (WP01)

**Implementation sketch**
- `src/mission_runtime/artifacts.py`: add `_PRIMARY_ARTIFACT_KINDS = frozenset({SPEC, DATA_MODEL, RESEARCH, CHECKLIST, FINALIZED_EXECUTION_PLAN, TASKS_INDEX, WORK_PACKAGE_TASK, LANE_STATE, PRIMARY_METADATA})`; remove those members from `_PLACEMENT_ARTIFACT_KINDS` (lines 78-93); `artifact_home_for` (115-138) returns a primary home (`write_surface="primary"`, `commit_target=None`/target ref) for primary kinds before the placement branch.
- `src/mission_runtime/resolution.py`: `resolve_placement_only` (1013-1106) gains a **REQUIRED** keyword `kind: MissionArtifactKind` (DECISION 1 — NO default; a default would silently flip un-threaded callers coord→primary); consults the partition to decide primary vs placement. Internal seam only (NFR-003). A no-kind call raises `TypeError` (pinned by T005).
- Negative scope: NO migration logic (FR-010 / C-003).

**Dependencies**: none.
**Estimated prompt size**: ~260 lines.

---

## WP02 — Converge commit_for_mission write path

**Prompt**: [tasks/WP02-converge-commit-for-mission.md](tasks/WP02-converge-commit-for-mission.md)

**Summary**
- **Goal**: Thread the kind through `commit_for_mission` and all its planning callers; remove the planning→coordination route in the router arm so planning artifacts commit to the primary `target_branch`.
- **Priority**: P0.
- **Independent test**: A planning caller (e.g. `spec-commit`) on a coord-topology fixture lands its commit on `target_branch`, not the coordination branch.

**Tracking**
- [x] T006 Thread REQUIRED `kind` through `commit_for_mission` (no default — DECISION 1) (WP02)
- [x] T007 `spec_commit_cmd` + `_commit_artifact_to_branch` callers pass kind (WP02)
- [x] T008 mission.py inline commit tails (~2345/2392/3825) + record-analysis (~1919) pass kind (WP02)
- [x] T009 tasks.py `map-requirements` caller passes kind; acceptance meta commit passes `PRIMARY_METADATA` (WP02)
- [x] T010 Remove the planning→coord route in the router `use_coord` arm (WP02)
- [x] T011 Red-first caller-convergence test (planning caller → primary on coord fixture) (WP02)
- [x] T031 Thread explicit `kind` at all 7 `resolve_placement_only` sites (status/base reads stay coord) (WP02)
- [x] T032 Converge direct-`safe_commit` planning writers (`tasks.py:2438/3076`) + retire `_skip_target_commit` 2nd router (WP02)

**Implementation sketch**
- `commit_router.py:82-206`: `commit_for_mission` accepts a **REQUIRED** `kind` (DECISION 1 — no default), forwards to `resolve_placement_only(repo_root, mission_slug, kind=kind)`; the `use_coord` arm (124) becomes kind-aware (primary kinds never route through coordination). The protected-ref refusal message is left wired (WP03 T015 rewrites its text).
- `spec_commit_cmd.py:155` and mission.py `_commit_artifact_to_branch` (~1092), tails (2345/2392/3825), record-analysis (1919): pass the artifact kind (no silent `SPEC` fallback).
- `tasks.py:3870` map-requirements: pass kind. `acceptance/__init__.py` `_commit_acceptance_meta_via_router` (~1398): pass `PRIMARY_METADATA`.
- **T031 (DECISION 2)**: all 7 `resolve_placement_only` sites thread `kind`. Status/base reads stay coord: `status_transition.py:332` (`STATUS_STATE`), `tasks.py:359` (review-currency base), `commands.py:796` (lane-base gate). `_resolve_write_target` coord test added.
- **T032 (DECISION 3)**: the hardcoded `safe_commit(target=CommitTarget(ref=target_branch))` planning writes at `tasks.py:2438` (move-task: `WORK_PACKAGE_TASK`) and `tasks.py:3076` (`tasks.md`: `TASKS_INDEX`) route through the kind authority; `_skip_target_commit` (`tasks.py:2425`) is retired/narrowed so it is not a 2nd routing authority (G-1).

**Owned files note**: WP02 adds `src/specify_cli/coordination/status_transition.py` (the `_resolve_write_target` status caller, T031). It also touches the direct-`safe_commit` planning writers in `agent/tasks.py` (already owned).

**Dependencies**: WP01.
**Estimated prompt size**: ~302 lines (was ~300; +T031/T032 added, under the <700 ceiling).

---

## WP03 — Converge bypass writers + 2nd routing authority + FR-008

**Prompt**: [tasks/WP03-converge-bypass-writers-fr008.md](tasks/WP03-converge-bypass-writers-fr008.md)

**Summary**
- **Goal**: Converge the writers that bypass `commit_for_mission` (`safe-commit`, `append-history`) and the second routing authority (`_planning_commit_worktree`) onto the partition; enforce FR-008 protected-primary refusal.
- **Priority**: P0.
- **Independent test**: `safe-commit` of a `spec.md` on a coord-topology fixture lands on `target_branch`; a primary-kind commit to a protected `target_branch` is refused.

**Tracking**
- [x] T012 `_resolve_mission_aware_target` (safe-commit) consults the kind authority (WP03)
- [x] T013 `append-history` (`commands.py:1283/1340`) consults the kind authority (WP03)
- [x] T014 Converge `_planning_commit_worktree` (`mission.py:775`) onto the partition (WP03)
- [x] T015 FR-008: refuse a primary-kind commit to a protected `target_branch` (WP03)
- [x] T016 Red-first bypass-writer + protected-primary tests (WP03)

**Implementation sketch**
- `safe_commit_cmd.py:192-209` `_resolve_mission_aware_target`: resolve with the planning kind; the result is primary for planning artifacts under coord topology.
- `orchestrator_api/commands.py:1260-1303` `_resolve_history_commit_args`: WP prompt files are `WORK_PACKAGE_TASK` (a primary kind) → primary placement; retire the `routes_through_coordination` arm for that kind.
- `mission.py:775` `_planning_commit_worktree`: consult the partition (retire the independent `routes_through_coordination` decision for primary kinds → return `(repo_root, paths)`).
- FR-008 guard: a primary-kind commit whose resolved `target_branch` is protected is refused (the `safe_commit` step-6 `ProtectedBranchRefused` path), with feature-branch guidance.
- **T015 (DECISION 5 — MANDATORY message rewrite)**: REPLACE the coord-transit guidance in BOTH `commit_router.py:126-137` (router refusal) AND `commit_helpers.py:285` (`ProtectedBranchRefused`) with `mission create --start-branch <feature-branch>` guidance. Test asserts each message contains "feature branch" and NOT "coordination worktree".

**Owned files note**: WP03 adds `src/specify_cli/coordination/commit_router.py` and `src/specify_cli/git/commit_helpers.py` (the two FR-008 message sites, T015). `commit_router.py` is shared with WP02/WP05 (serialized).

**Dependencies**: WP02.
**Estimated prompt size**: ~224 lines.

---

## WP04 — Planning read-path residue

**Prompt**: [tasks/WP04-planning-read-path-residue.md](tasks/WP04-planning-read-path-residue.md)

**Summary**
- **Goal**: Stop the planning read path consulting the coordination husk for primary-partition kinds once writes are primary-always; preserve the C-005 KEEP transients.
- **Priority**: P1 — runs in PARALLEL with WP02/WP03 (depends only on WP01).
- **Independent test**: Red-first stale-coord-shadow test (#2062 class) — a stale `-coord` planning copy must not shadow primary truth.

**Tracking**
- [x] T017 Stop the read path consulting the coord husk for primary-partition kinds (WP04)
- [x] T018 Preserve C-005 KEEP transients (#1718 create-window, #1848 coord-deleted) (WP04)
- [x] T019 Red-first stale-coord-shadow test (#2062 class) for a planning artifact (WP04)

**Implementation sketch**
- **REAL per-kind read split (DECISION 4 — not a no-op)**: planning-artifact reads route to the PRIMARY feature dir (`primary_feature_dir_for_mission`, the sanctioned pattern at `mission.py:830/1226/1273/1903`); status reads keep the topology-aware seam (`resolve_handle_to_read_path:843`). Identify the planning-read callers going through the topology seam and route them to primary; clean the husk residue (`_read_path_resolver.py:961-963` `consults_coord_husk`, the `topology is None` arms; `surface_resolver.py:473/503-528`).
- Preserve C-005 KEEP transients (#1718 create-window, #1848 coord-deleted) — only PLANNING-kind reads change.
- **DoD**: a line-cited deliverable naming the exact resolver line(s) changed (or, per-caller, the line proving already-primary). NO whole-WP green-pin / "no change needed"; the coord-topology stale-husk T019 variant is red-first.

**Dependencies**: WP01 (parallel with WP02/WP03).
**Estimated prompt size**: ~205 lines.

---

## WP05 — Shared coord-worktree helper governance

**Prompt**: [tasks/WP05-coord-worktree-helper-governance.md](tasks/WP05-coord-worktree-helper-governance.md)

**Summary**
- **Goal**: Make the coord-worktree helpers correct once planning no longer transits coord — staging, `_try_advance_ref` ff-advance (#1878), residue filter apply to status-only coord writes; remove dead ff-advance on the planning path.
- **Priority**: P1.
- **Independent test**: A status-only coord write still ff-advances; a planning commit goes direct to `target_branch` with no coord transit and no orphaned `target_branch` param.

**Tracking**
- [x] T020 Govern `_materialise_coord_worktree` staging + `_try_advance_ref` for status-only coord writes (WP05)
- [x] T021 Remove dead ff-advance on the planning path; no orphaned `target_branch` param (WP05)
- [x] T022 Confirm residue dirty-filter (`is_coordination_artifact_residue_path`) stays correct (WP05)
- [x] T023 Red-first helper-governance test (status coord write ff-advances; planning does not transit) (WP05)

**Implementation sketch**
- `commit_router.py`: `_materialise_coord_worktree` (214-263) and `_try_advance_ref` (358-392) now only fire for COORD-partition writes; the `use_coord and target_branch` ff-advance gate (199) must no longer be reachable on a planning commit. **T020 (DECISION 8)**: add a RUNTIME guard (`assert kind not in _PRIMARY_ARTIFACT_KINDS` or a typed raise) at the staging entry — not a comment — covered by a T023 test.
- `mission.py:775` `_planning_commit_worktree`: after WP03 it returns `(repo_root, paths)` for primary kinds — verify no dead coord staging path or unused `target_branch` plumbing remains.
- `is_coordination_artifact_residue_path` (`artifacts.py:141`): SPEC/DATA_MODEL/RESEARCH are now primary kinds — confirm the residue filter still classifies only COORD-partition files as residue (the partition moved, so these are no longer coord residue).

**Dependencies**: WP03.
**Estimated prompt size**: ~250 lines.

---

## WP06 — Meta-reader sweep (in-mission)

**Prompt**: [tasks/WP06-meta-reader-sweep.md](tasks/WP06-meta-reader-sweep.md)

**Summary**
- **Goal**: Route the ~3 inline `json.loads(meta…read_text())` reads in mission.py through canonical `load_meta`; name/reconcile the duplicate `load_meta` at `task_utils/support.py:363`.
- **Priority**: P2.
- **Independent test**: SC-004 contract-pinned test — the canonical `load_meta` is the import in the touched modules; zero inline `meta.json` reads remain there.

**Tracking**
- [x] T024 Route the ~3 inline `json.loads(meta…read_text())` reads in mission.py through canonical `load_meta` (WP06)
- [x] T025 Name/reconcile the duplicate `load_meta` at `task_utils/support.py:363` (WP06)
- [x] T026 SC-004 contract-pinned test (canonical `load_meta` is the import; zero inline reads in touched modules) (WP06)

**Implementation sketch**
- `mission.py:442`, `:1647`, `:3487`: replace `json.loads(meta_*.read_text(...))` with `load_meta(...)` from `specify_cli.mission_metadata` (the canonical authority).
- `task_utils/support.py:363` already delegates to `_load_meta_canonical` (`mission_metadata.load_meta`) but exposes a path-taking shim — name `mission_metadata.load_meta` as canonical; do NOT fork. Document the shim's distinct signature (path vs dir).
- Keep to in-mission sites; the ~53-site #2100 backlog stays deferred.
- **T026 (DECISION 7)**: BEHAVIORAL test only — feed a malformed `meta.json` through each of the 3 converted sites via their pre-existing entry points; assert `load_meta`-contract degradation (not raw `JSONDecodeError`). DROP the source-grep / module-count option.

**Dependencies**: WP05.
**Estimated prompt size**: ~190 lines.

---

## WP07 — Behavioral verification

**Prompt**: [tasks/WP07-behavioral-verification.md](tasks/WP07-behavioral-verification.md)

**Summary**
- **Goal**: Prove the bifurcation behaviorally (two-ref guard) across every converged write site, guard the flattened regression, and verify FR-007 end-to-end + FR-008 refusal.
- **Priority**: P0 (final gate).
- **Independent test**: Behavioral two-ref guard passes — planning-kind → `target_branch` AND status-kind → coordination — exercised across `commit_for_mission`, a bypass writer, and `_planning_commit_worktree`.

**Tracking**
- [x] T027 Behavioral two-ref guard across `commit_for_mission` + a bypass writer + `_planning_commit_worktree` (WP07)
- [x] T028 Flattened-regression proof (NFR-001) (WP07)
- [x] T029 FR-007 end-to-end coord-topology mission maps 100% requirements (WP07)
- [x] T030 FR-008 protected-primary refusal end-to-end (WP07)

**Implementation sketch**
- `tests/architectural/test_write_surface_placement_guard.py`: the behavioral two-ref guard (NFR-002) — for a coord fixture assert primary-kind→`target_branch` AND status-kind→coordination, exercised across the three write paths, **driving the REAL resolver (no `resolve_topology`/`resolve_placement_only` stubs — DECISION 7)**. T027 includes a **MANDATORY** anti-mutant negative test that forces the pre-fix partition (SPEC back in `_PLACEMENT_ARTIFACT_KINDS`) and asserts the planning-ref assertion goes red.
- `tests/missions/test_write_surface_coherence.py`: FR-007 fresh coord-topology mission specify→plan→tasks→finalize maps 100% requirements with zero manual coord steps; NFR-001 flattened regression green; FR-008 protected-primary refusal. **T030 (DECISION 6)** asserts BOTH refusal shapes: the router returns `CommitRouterResult(status="no_op_wrong_surface")`; `safe_commit` RAISES `ProtectedBranchRefused` — each against the path that produces it.
- Realistic data: real-length ULID/mid8, never short fake slugs.

**Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06.
**Estimated prompt size**: ~270 lines.

# Feature Specification: Write-Surface Coherence

**Mission**: write-surface-coherence-01KVTVZS
**Mission ID**: 01KVTVZS6ZT02NTR0YBJ9WWKMJ
**Created**: 2026-06-23
**Status**: Draft (revised post-spec squad)
**Target branch**: feat/write-surface-coherence

## Summary

The write-side companion to the merged read-path single-authority work (mission
`single-authority-topology-cleanup`, PR #2099 / 01KVRJ6P). That mission made
every *read* path resolve a mission's surface from one authority. This mission
does the same for the *write/authoring* path of the planning lifecycle.

**The real seam (post-plan squad, confirmed by live trace).** The canonical
artifact-placement model **already exists** on the *read* side
(`src/mission_runtime/artifacts.py`, from merged 01KVRJ6P): `MissionArtifactKind`
+ `artifact_home_for` + `_PLACEMENT_ARTIFACT_KINDS` already classify every artifact
(`PRIMARY_METADATA`→primary; everything else→placement). The bug is an
**asymmetry**: the *write* side (`resolve_placement_only` /
`commit_for_mission`, plus the bypass writers `safe-commit` / `append-history` and
the second routing authority in `_planning_commit_worktree`) is **kind-blind** — it
routes purely by topology, so planning artifacts are *written* to coordination even
though the read model has a richer view.

**The decision (operator, 2026-06-23).** Make the write side **kind-aware** by
consulting the existing `MissionArtifactKind` model, and **re-partition**: the
planning + identity kinds (`SPEC`, `DATA_MODEL`, `RESEARCH`, `CHECKLIST`,
`FINALIZED_EXECUTION_PLAN`, `TASKS_INDEX`, `WORK_PACKAGE_TASK`, `PRIMARY_METADATA`)
author+read+commit on the **primary `target_branch` for every shape**; the
status/bookkeeping/verification kinds (`STATUS_STATE`, `ISSUE_MATRIX`,
`ACCEPTANCE_MATRIX`, `ANALYSIS_REPORT`) stay on the **coordination branch** for
coord topology. `meta.json` moves to primary on **both** read and write (full
symmetry — it already reads primary but is written to coord today). The single
swappable locus is the frozenset partition. Unification, not parity: the
planning-artifact→coordination *write* route is removed, not preserved.

## User Scenarios & Testing

### Primary scenario (happy path)

1. An operator runs `/spec-kitty.specify` → `/spec-kitty.plan` →
   `/spec-kitty.tasks` for a coordination-topology mission on its feature branch.
2. Every planning-artifact commit (via the shared `commit_for_mission` seam)
   lands on the primary `target_branch`; the working-tree authoring/read surface
   is the primary checkout throughout.
3. `finalize-tasks --validate-only` reads those files from the same primary
   surface and reports **100% of requirements mapped**.
4. The operator proceeds to `implement` with **zero** manual coordination-worktree
   steps.

### Status still lands on coordination

- For the same coord-topology mission, a status transition still commits
  `status.events.jsonl` (and `decisions/index.json`, `issue-matrix.md`) to the
  coordination branch — proving the bifurcation, not a blanket move to primary.

### Exception path (protected primary)

- A coord-topology mission whose `target_branch` is a protected branch
  (`main`/`master`) is **refused** at the planning-commit boundary with guidance
  to start a feature branch (FR-008) — the feature-branch invariant avoids the
  deadlock; no coordination-worktree transit for planning commits.

### Edge case (already-split existing mission) — out of scope

- A mission already split (planning on coordination, reads on primary) is **not**
  reconciled (forward-only, C-003); the flatten / manual-recovery flow remains
  the documented remedy.

## Domain Language

| Canonical term | Meaning | Avoid |
|----------------|---------|-------|
| **placement bifurcation** | `resolve_placement_only` returns a primary `target_branch` ref for planning-class commits and a coordination ref for status/bookkeeping commits. | "converge the resolvers" (there is already one) |
| **planning artifacts** | `spec.md`, `plan.md`, `tasks.md`, `tasks/WP*.md`. | conflating with bookkeeping |
| **status/bookkeeping** | The append-only `status.events.jsonl`, plus `decisions/index.json` and `issue-matrix.md`, plus WP transition commits — coordination-branch surface for coord topology. | "planning lives on coord" (retired) |

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Make the write-side placement **kind-aware** by consulting the existing `MissionArtifactKind` model (`artifact_home_for` / the kind partition in `mission_runtime/artifacts.py`) instead of routing purely by topology. The PRIMARY-vs-COORD decision is the existing frozenset partition — one place. | Proposed |
| FR-002 | **Re-partition** the planning + identity kinds (`SPEC`, `DATA_MODEL`, `RESEARCH`, `CHECKLIST`, `FINALIZED_EXECUTION_PLAN`, `TASKS_INDEX`, `WORK_PACKAGE_TASK`, `PRIMARY_METADATA`) onto the **primary `target_branch` for all shapes** — read and write agree (INV-5 full symmetry; `meta.json` moves to primary on the write side to match the read model). The coordination worktree is never the authoring/read/commit surface for these kinds. | Proposed |
| FR-003 | Converge **all** planning-placement write sites onto the kind-aware authority — not just `commit_for_mission`'s callers (`spec-commit`, `setup-plan`, `map-requirements`, finalize tail, record-analysis, analyze/tasks/accept) but also the **bypass writers** `_resolve_mission_aware_target` (`safe_commit_cmd.py`, the `safe-commit` command) and `append-history` (`orchestrator_api/commands.py:1343`), **and** the **second routing authority** `_planning_commit_worktree` (`mission.py:752/775`, its own `routes_through_coordination`). A green guard must prove the split closed across all of them (no "fixed N of M"). The planning→coordination write route is removed (C-005). | Proposed |
| FR-004 | The status/bookkeeping/verification kinds (`STATUS_STATE`, `ISSUE_MATRIX`, `ACCEPTANCE_MATRIX`, `ANALYSIS_REPORT`) and `decisions/index.json` continue to resolve to the **coordination branch** for coord topology, unchanged. (Membership of `LANE_STATE` (→primary default), `ACCEPTANCE_MATRIX`/`ANALYSIS_REPORT` (→coord default) is confirmed in tasks.) | Proposed |
| FR-005 | Govern the shared coord-worktree helpers post-bifurcation: `_planning_commit_worktree` / `_materialise_coord_worktree` staging, the `_try_advance_ref` ff-advance (#1878), and the `is_coordination_artifact_residue_path` dirty-filter must be correct when planning artifacts no longer transit coord (planning commits go direct to `target_branch`; the ff-advance and residue logic apply to status-only coord writes). | Proposed |
| FR-006 | The planning **read** path must not fall back to the coordination husk for planning artifacts once writes are primary-always (prevent a stale pre-mission coord copy shadowing primary truth — the #2062 class). Only status reads may consult coord. (Builds on the merged read-side resolver; if any residue remains, name it or defer explicitly.) | Proposed |
| FR-007 | A fresh coordination-topology mission run through specify → plan → tasks has all planning artifacts on the primary surface, so `finalize-tasks` reads them with full requirement mapping and **no** manual coordination-worktree creation. | Proposed |
| FR-008 | Planning commits target the primary `target_branch`, which **MUST be a non-protected feature branch**. A coord-topology mission whose `target_branch` is a protected branch (`main`/`master`) is refused at the planning-commit boundary with guidance to start a feature branch (consistent with the existing `mission create --start-branch` recommendation). The protected-primary deadlock is avoided by this feature-branch **invariant** — not by a coordination-worktree landing transit. (operator decision 2026-06-23) | Proposed |
| FR-009 | Route the inline `json.loads(meta_path.read_text(...))` reads in the modules this mission actually touches (≈3 sites in `cli/commands/agent/mission.py`) through the canonical `load_meta`/`load_meta_strict`/`load_meta_or_empty` authority (`mission_metadata.py`). Acknowledge the duplicate `load_meta` at `task_utils/support.py:363` (name which is canonical; do not silently fork). The remaining ~53-site #2100 backlog stays deferred to its own sweep. | Proposed |
| FR-010 | The mission is **forward-only**: no migration logic to reconcile already-split existing missions. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Behavior-neutral for flattened / single-branch missions (already primary). | 100% of existing flattened-mission planning tests stay green; zero new failures attributable to the change. | Proposed |
| NFR-002 | Verified by a **behavioral two-ref guard**, not a structural count: for a coord-topology fixture, a PRIMARY-partition commit (e.g. `SPEC`) resolves to the primary `target_branch` AND a COORD-partition commit (e.g. `STATUS_STATE`) resolves to the coordination branch — across **every** converged write site (FR-003), including a `_planning_commit_worktree` and a bypass-writer path. | One guard asserting both refs from the same coord fixture per write path; fails if either side regresses. | Proposed |
| NFR-003 | No new public **CLI** command/flag surface. (Internal Python seams — `resolve_placement_only`/`commit_for_mission` etc. — may gain a `MissionArtifactKind` parameter to thread the kind; that is an internal seam change, not a public CLI surface.) | No new CLI command/flag; the kind is threaded as an internal parameter. | Proposed |
| NFR-004 | The PRIMARY-vs-COORD destination is decided by the **single frozenset partition** (`_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` in `artifacts.py`). Flipping where a kind lands is **moving it between the two sets (one line)**; the returned `MissionArtifactHome`/`CommitTarget` shape and the `artifact_home_for`/placement signatures are unchanged, and callers are blind to the membership. | A test that moves a kind between the sets changes only that kind's destination, touching no caller, no returned-object field, no signature. | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | KEEP status/bookkeeping (event log + `decisions/index.json` + `issue-matrix.md` + WP transition commits) on the coordination branch for coord topology — do not move status to primary (preserves the atomic-event-log model from mission `01KSPTVW`). | Active |
| C-002 | KEEP protected-primary deadlock avoidance — enforced by the FR-008 invariant (planning commits require a non-protected feature `target_branch`), not by transiting coord. | Active |
| C-003 | Forward-only (operator decision 2026-06-23) — no reconciliation of already-split missions. | Active |
| C-004 | The coordination worktree remains the internal materialization for status/sync; this mission stops routing planning artifacts to it but does not remove the mechanism. | Active |
| C-005 | Unification not parity — remove the planning-artifact→coordination route; do not preserve it as a compatibility fallback. | Active |
| C-006 | Build on the merged read-path surfaces (`primary_feature_dir_for_mission`, `resolve_handle_to_read_path`, `candidate_feature_dir_for_mission` in `missions/_read_path_resolver.py`; `resolve_topology` / `routes_through_coordination` / `resolve_placement_only` in `mission_runtime`). No parallel **read** resolver — but the placement **destination** legitimately **bifurcates by artifact class** (planning vs status); that bifurcation is this mission's core change, not a parallel resolver. | Active |

## Key Entities

- **Placement authority** (`resolve_placement_only` via `commit_for_mission`) — the
  single seam that must bifurcate by artifact class.
- **Planning artifacts** — `spec.md`, `plan.md`, `tasks.md`, `tasks/WP*.md`.
- **Status/bookkeeping** — event log + `decisions/index.json` + `issue-matrix.md`
  + WP transitions (coordination surface).
- **Mission topology** — after this mission, determines only the status-commit
  destination, not the planning-commit destination.

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A fresh coordination-topology mission completes specify → plan → tasks → `finalize-tasks --validate-only` with **100% of requirements mapped** and **zero** manual coordination-worktree steps. |
| SC-002 | For a coord-topology fixture, a planning-artifact commit lands on the primary `target_branch` AND a status-event commit lands on the coordination branch (the NFR-002 behavioral two-ref guard passes). |
| SC-003 | Flattened / single-branch missions exhibit **no** behavior change (existing planning tests remain green). |
| SC-004 | **Zero** inline `meta.json` reads remain in the modules this mission touches (≈3 in `agent/mission.py`); the canonical `load_meta` authority is unambiguous (the `task_utils/support.py` duplicate named/reconciled). |

## Resolved Decisions

- **FR-008 protected-primary mechanism (operator, 2026-06-23):** **require a
  non-protected feature branch** for planning commits. A coord-topology mission
  on a protected `target_branch` is refused with guidance to start a feature
  branch — no coordination-worktree landing transit. Cleaner invariant, no
  special case.

## Assumptions

- PR-bound missions start on a feature branch, so `target_branch` is the
  (non-protected) feature branch — planning commits are direct; protected-primary
  is the FR-008 edge.
- PR #2089's `_primary_anchored_feature_dir` (read) + `resolve_placement_only`
  (write) are the precedent seams; the read side already converged in PR #2099.
- Mission `01KSPTVW` FR-005 originally required planning-artifact commits on the
  coordination branch; this mission deliberately **revises** that to
  planning-on-primary / status-on-coordination — the operator-confirmed
  unification (called out so it is not read as a regression).

## Out of Scope

- Reconciling already-split existing missions (forward-only, C-003).
- Removing the coordination-worktree mechanism (C-004).
- The remaining ~53-site #2100 meta-reader backlog outside this mission's touched
  modules.
- `agent action implement --json` (#1891) and the acceptance-matrix C-010 gate
  (#2085) — separate deferred slices, not folded here.

# Implementation Plan: Write-Surface Coherence

**Branch**: `feat/write-surface-coherence` | **Date**: 2026-06-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/write-surface-coherence-01KVTVZS/spec.md`

## Summary

Bifurcate the single placement authority (`resolve_placement_only`, consumed via
`commit_for_mission`) **by artifact class**: planning artifacts
(`spec.md`/`plan.md`/`tasks.md`/`tasks/WP*.md`) resolve to the primary
`target_branch`; status/bookkeeping (`status.events.jsonl`,
`decisions/index.json`, `issue-matrix.md`, WP transitions) resolve to the
coordination ref. The decision is made in one seam (the `use_coord` arm in
`commit_router.py`), so it closes the split for **all ≥7 planning-class
callers** at once. This is the write-side twin of the merged read-path
single-authority work (mission `single-authority-topology-cleanup` / 01KVRJ6P,
PR #2099); it builds on that mission's surfaces (C-006), does not re-implement
them. Forward-only; behavior-neutral for flattened/single-branch missions.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `mission_runtime` (`resolve_placement_only`, `resolve_topology`, `routes_through_coordination`, `CommitTarget`); `specify_cli.coordination.commit_router` (`commit_for_mission`); `specify_cli.git.commit_helpers` (`safe_commit`, `ProtectedBranchRefused`); `specify_cli.missions._read_path_resolver`; `specify_cli.mission_metadata` (`load_meta` family)
**Storage**: Git branches/worktrees + `meta.json` mission identity (no DB)
**Testing**: pytest — `tests/architectural/` (behavioral two-ref guard, NFR-002), `tests/missions/` + `tests/specify_cli/` (caller behavior, flattened regression), red-first repro per DIRECTIVE_034
**Target Platform**: Linux/macOS developer CLI
**Project Type**: single (Python CLI / library)
**Performance Goals**: N/A (planning-lifecycle CLI operations; no hot path)
**Constraints**: behavior-neutral for flattened/single-branch missions (NFR-001); no new public command/flag (NFR-003); build on merged 01KVRJ6P read-side surfaces, no parallel read resolver (C-006); unification not parity — remove the planning→coord route, no fallback (C-005)
**Scale/Scope**: one placement seam + ≥7 planning-class callers + 4 shared coord-worktree helpers + read-path residue + ~3 in-mission inline meta reads + the behavioral guard

## Charter Check

*GATE: charter context is `compact` (no project charter file).* No charter gates
to evaluate; standard doctrine applies (DIRECTIVE_034 red-first, DIRECTIVE_041
behavioral-not-structural guards, unification-not-parity). Section satisfied.

## Project Structure

### Documentation (this mission)

```
kitty-specs/write-surface-coherence-01KVTVZS/
├── plan.md              # This file
├── research.md          # Phase 0 output (squad-grounded design decisions)
├── data-model.md        # Phase 1 output (artifact-class placement model)
├── quickstart.md        # Phase 1 output (verify the bifurcation)
├── contracts/           # Phase 1 output (placement-bifurcation contract)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── mission_runtime/
│   └── resolution.py            # resolve_placement_only — the bifurcation seam (IC-01)
├── specify_cli/
│   ├── coordination/
│   │   └── commit_router.py     # commit_for_mission use_coord arm (IC-01/IC-02);
│   │                            #   _materialise_coord_worktree, _try_advance_ref (IC-03)
│   ├── cli/commands/
│   │   ├── spec_commit_cmd.py   # planning-class caller (IC-02)
│   │   └── agent/
│   │       ├── mission.py       # setup-plan, finalize tail, record-analysis,
│   │       │                    #   _planning_commit_worktree (IC-02/IC-03); ~3 meta reads (IC-05)
│   │       └── tasks.py         # map-requirements caller (IC-02)
│   ├── missions/_read_path_resolver.py   # planning read residue (IC-04)
│   ├── coordination/surface_resolver.py  # _coord_mid8 read residue (IC-04)
│   ├── acceptance/__init__.py            # accept artifact-commit caller (IC-02)
│   ├── mission_metadata.py               # canonical load_meta (IC-05)
│   └── task_utils/support.py             # duplicate load_meta — name/reconcile (IC-05)

tests/
├── architectural/       # NFR-002 behavioral two-ref guard
├── missions/            # caller behavior, flattened regression (NFR-001)
└── specify_cli/         # command-level behavior + red-first repros
```

**Structure Decision**: Single Python CLI/library. The change is concentrated at
the `mission_runtime` placement seam and its `specify_cli.coordination` consumer,
with caller convergence across the planning-lifecycle command modules and a
read-path residue cleanup in `missions/_read_path_resolver.py`.

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Kind-aware write authority + re-partition

- **Purpose**: Make the write-side placement consult the existing
  `MissionArtifactKind` model (`artifact_home_for` / the frozenset partition in
  `mission_runtime/artifacts.py`) instead of routing by topology, and **move the
  planning + identity kinds onto primary** by re-partitioning
  `_PLACEMENT_ARTIFACT_KINDS` → a `_PRIMARY_ARTIFACT_KINDS` set. The partition is
  the single swappable locus (NFR-004): flipping a kind's destination is moving it
  between the two sets. Read and write become symmetric (INV-5), incl. `meta.json`.
- **Relevant requirements**: FR-001, FR-002, FR-004, NFR-004. *Negative scope:
  FR-010 / C-003 — add NO migration logic for already-split missions.*
- **Affected surfaces**: `src/mission_runtime/artifacts.py` (the partition +
  `artifact_home_for`); `resolution.py` (`resolve_placement_only` consults the kind
  via `artifact_home_for` / a `MissionArtifactKind` input — internal seam, NFR-003).
- **Sequencing/depends-on**: none (foundation).
- **Risks**: `resolve_placement_only` is shared with the STATUS caller
  (`status_transition.py:332`) and ~5 others — thread the kind without changing
  status routing (C-001); the kind input is internal (NFR-003), not a CLI surface.
  Partition membership of `LANE_STATE`/`ACCEPTANCE_MATRIX`/`ANALYSIS_REPORT`
  confirmed here. Highest-leverage change.

### IC-02 — Converge ALL planning-placement write sites

- **Purpose**: Route every planning-placement write through the kind-aware
  authority and delete the planning→coordination path; enforce the FR-008
  feature-branch invariant. Covers the `commit_for_mission` callers **and** the
  sites that bypass it.
- **Relevant requirements**: FR-003, FR-008, C-005. *NFR-003 boundary: no new CLI
  flag; the kind is an internal parameter.*
- **Affected surfaces**:
  - `commit_for_mission` callers — `spec_commit_cmd.py:155`,
    `agent/mission.py:1092/1919/2345/2392/3825`, `agent/tasks.py:3870`,
    `acceptance/__init__.py:1418/1446`.
  - **Bypass writers (squad-found, NOT via `commit_for_mission`)** —
    `_resolve_mission_aware_target` (`safe_commit_cmd.py:198-209`, the `safe-commit`
    command) and `append-history` (`orchestrator_api/commands.py:1283/1343`).
  - **Second routing authority** — `_planning_commit_worktree`
    (`agent/mission.py:752/775`), its own `routes_through_coordination`, used by
    `map-requirements` (`tasks.py:3880`) and the history write — converge it onto
    the partition (do NOT leave it as an independent decision).
  - Enumerate all **9 `resolve_placement_only` callers** with per-site kind (status
    callers pass STATUS and stay coord — C-001).
- **Sequencing/depends-on**: IC-01.
- **Risks**: the "fixed N of M" trap is **live in the original IC map** — the guard
  (IC-06) must exercise a bypass-writer path and `_planning_commit_worktree`, not
  only `commit_for_mission`.

### IC-03 — Shared coord-worktree helper governance

- **Purpose**: Make the helpers correct once planning no longer transits coord —
  `_planning_commit_worktree` / `_materialise_coord_worktree` staging,
  `_try_advance_ref` ff-advance (#1878), and the
  `is_coordination_artifact_residue_path` dirty-filter now apply to status-only
  coord writes.
- **Relevant requirements**: FR-005, C-004.
- **Affected surfaces**: `commit_router.py` (`_materialise_coord_worktree`,
  `_try_advance_ref`), `agent/mission.py` (`_planning_commit_worktree`).
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: the ff-advance previously fast-forwarded primary to a coord HEAD
  mixing planning+status; once planning is direct-to-primary the advance semantics
  and residue-filter meaning change — must not orphan the `target_branch` param or
  leave dead ff-advance on the planning path.

### IC-04 — Planning read-path residue

- **Purpose**: Stop the planning **read** path consulting the coordination husk for
  planning artifacts (a stale pre-mission coord copy must not shadow primary truth
  — the #2062 class).
- **Relevant requirements**: FR-006.
- **Affected surfaces**: `missions/_read_path_resolver.py` (the
  `consults_coord_husk` arms), `coordination/surface_resolver.py` (`_coord_mid8`).
- **Sequencing/depends-on**: IC-01.
- **Risks**: must preserve the C-005 KEEP transients from 01KVRJ6P (create-window
  #1718, coord-deleted #1848) — only planning-artifact reads stop consulting coord,
  not the status/transient probes.

### IC-05 — Meta-reader sweep (in-mission) + duplicate `load_meta`

- **Purpose**: Route the ~3 inline `json.loads(meta…read_text())` reads in the
  touched modules through the canonical `load_meta`; name/reconcile the duplicate
  authority so "canonical `load_meta`" is unambiguous.
- **Relevant requirements**: FR-009.
- **Affected surfaces**: `agent/mission.py` (~3 inline reads), `mission_metadata.py`
  (canonical), `task_utils/support.py:363` (duplicate).
- **Sequencing/depends-on**: IC-02, IC-03 (they define the touched-module set).
- **Risks**: scope creep — keep to in-mission sites; the remaining ~53-site #2100
  backlog stays deferred (Out of Scope).

### IC-06 — Behavioral verification

- **Purpose**: Prove the bifurcation behaviorally and guard the flattened
  regression and the FR-008 refusal.
- **Relevant requirements**: NFR-001, NFR-002, FR-007, FR-008, SC-001..SC-004.
- **Affected surfaces**: `tests/architectural/` (two-ref guard), `tests/missions/`
  + `tests/specify_cli/` (coord-topology end-to-end mapping, flattened regression,
  protected-primary refusal).
- **Sequencing/depends-on**: all.
- **Risks**: the guard must be behavioral (planning-commit ref == primary AND
  status-commit ref == coord), NOT a structural "one function" count (which passes
  vacuously); red-first repro of the split per DIRECTIVE_034.

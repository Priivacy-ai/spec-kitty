# Implementation Plan: Execution-Context Unification

**Branch**: `fixups/code-engine-stabilization` (single-branch / flattened topology — landing = coordination)
**Date**: 2026-06-09 | **Spec**: `kitty-specs/execution-context-unification-01KTPKST/spec.md`
**Input**: Feature specification + `research.md` (three-agent squad findings)

## Summary

Structurally drain the **coord-vs-primary split-brain class** by routing every command surface through one
resolved `MissionExecutionContext` — composed as a **doc-09 fragment / op-composite** on the existing
`mission_runtime.ExecutionContext` substrate — with status owned by the existing Mission-Management OHS
facade (`status/aggregate.py:MissionStatus`). The work is mostly **strangle + subtraction**: ~7 parallel
resolvers (Clusters A–E) collapse, ~500–650 LOC of duplication is removed, and 5 dead `status_service`
symbols are deleted. **Sequencing decision (operator):** *facade-first* — adopt the status facade first so
every downstream consumer has one stable status authority, then read-path, then artifact-placement (which
unblocks the paused-mission dogfood failures #1814/#1816), then the highest-risk runtime writers last.
**#1815 decision (operator):** *extend the occurrence-map* schema to model multi-path structural moves.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml; internal: `mission_runtime` (ExecutionContext substrate), `specify_cli.status` (MissionStatus/OHS facade, event log), `specify_cli.coordination` (surface/workspace resolution); `spec_kitty_events` / `spec_kitty_tracker` consumed via public imports only (shared-package boundary)
**Storage**: append-only `status.events.jsonl` event log (sole authority for WP lane state); git worktrees + branches for execution topology; `meta.json` for mission identity
**Testing**: `pytest`; **extend** `tests/architectural/test_execution_context_parity.py` (existing 1,323 LOC parity ratchet — ATDD-first per C-011); `ruff` + `mypy` zero-issue gate on changed paths; `tests/architectural/` (terminology, shared-package-boundary) must stay green
**Target Platform**: Linux/macOS developer CLI
**Project Type**: single (Python package `src/`)
**Performance Goals**: N/A — correctness/structural mission; parity ratchet must be deterministic across repeated runs and both CWDs (NFR-003)
**Constraints**: strangler discipline — never break the lifecycle mid-conversion (C-004); no parallel mechanisms — extend the existing resolver, never fork (C-005/NFR-001); net LOC trends **down** (NFR-005); honour doc-09 fragment model + ADRs 2026-06-03-1/2/3 + 2026-06-07-1 (NFR-004)
**Scale/Scope**: ~7 resolvers across Clusters A–E; ~500–650 LOC duplication collapse + 5 dead symbols; 13 FR / 5 NFR / 4 C

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-First (C-011, binding):** PASS by design — IC-08 authors the extended parity assertions (red) first; ICs converge them to green. The regression guard precedes the conversions.
- **Burn-down policy (C-004, binding):** PASS — every deletion (IC-04 parsers, IC-09 dead symbols) is strangler-ordered: convert consumer → prove parity green → delete the now-unreferenced surface. Never delete-then-rewire.
- **No parallel mechanisms (C-005):** PASS — extends `mission_runtime.ExecutionContext` + the existing parity test; static/review check confirms one resolution path (SC-4). Forking a second context resolver or a second parity test is explicitly prohibited.
- **`__all__` convention (C-007):** new fragment modules MUST declare `__all__`.
- **Shared-package boundary:** PASS — no new vendored copies; `spec_kitty_events`/`spec_kitty_tracker` via public imports; runtime stays within the canonical runtime boundary.
- **Terminology Canon:** new code uses Mission terms; do NOT introduce new `feature*` aliases. Pre-existing `feature_dir`/`feature_slug` public names are out of scope for renaming this mission (would explode the diff) — note, don't churn.
- **Git workflow:** lands on `fixups/code-engine-stabilization` via `spec-kitty merge` to local branch; PR to origin (no direct push to origin/main).

No charter violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/execution-context-unification-01KTPKST/
├── plan.md              # This file
├── spec.md              # FR-001..FR-015, NFR-001..005, C-001..004
├── research.md          # Squad findings (Clusters A-E, dup/dead-code, design conformance)
├── data-model.md        # Phase 1: the context fragments + CommitTarget value object
├── quickstart.md        # Phase 1: parity-ratchet + dogfood validation scenarios
├── contracts/           # Phase 1: context-composite + facade-adoption contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── mission_runtime/
│   ├── context.py            # ExecutionContext substrate → grow into doc-09 composite (IC-02)
│   └── resolution.py         # resolve_action_context → assemble fragments (IC-02)
├── specify_cli/
│   ├── status/
│   │   ├── aggregate.py      # MissionStatus / OHS facade (EXISTS — adopt, IC-01)
│   │   └── views.py          # materialize_if_stale → git-op guard + stale-key (IC-06)
│   ├── coordination/
│   │   ├── surface_resolver.py    # resolve_status_surface (IC-01)
│   │   ├── status_transition.py   # _identity_for_request #1737 (IC-01)
│   │   ├── workspace.py           # CoordinationWorkspace.resolve lock #1357 (IC-01)
│   │   └── status_service.py      # 5 DEAD symbols → delete (IC-09)
│   ├── missions/
│   │   ├── _read_path_resolver.py     # canonical read primitive (IC-03)
│   │   └── feature_dir_resolver.py    # duplicate → fold into above (IC-03)
│   ├── core/paths.py              # keep as single worktree-pointer parser (IC-04)
│   ├── workspace/root_resolver.py # duplicate parser → delete (IC-04)
│   └── cli/commands/implement.py  # _ensure_planning_artifacts_committed_git #1816 (IC-05)
└── doctrine/ (+ bulk-edit skill)  # occurrence-map structural-move extension (IC-10)

tests/architectural/
└── test_execution_context_parity.py   # EXTEND (1,323 LOC) — dual-CWD + flattened fixture (IC-08)
```

**Structure Decision**: Single Python package. The unification core lives in `src/mission_runtime/`;
consumers being strangled live across `src/specify_cli/{status,coordination,missions,core,workspace,cli}`.
No new top-level packages — the point is to *remove* parallel surfaces, not add one.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.
> Sequencing below reflects the operator's **facade-first** decision. Reviewer profiles are
> *recommendations* (R-07 pattern) — `finalize-tasks` assigns owners; do not pre-assign.

### IC-01 — Status-surface facade adoption (Cluster B) — *facade-first, runs first*

- **Purpose**: Establish the single status authority before anything else consumes it: route the remaining raw primary/coord status readers through the existing `MissionStatus`/OHS facade, fix the parallel coord-path derivation, and lock-serialize coord resolution.
- **Relevant requirements**: FR-003, FR-008 (#1737, #1357, #1572)
- **Affected surfaces**: `status/aggregate.py`, `coordination/surface_resolver.py`, `coordination/status_transition.py` (`_identity_for_request`), `coordination/workspace.py` (`CoordinationWorkspace.resolve`)
- **Sequencing/depends-on**: none (first)
- **Risks**: highest-traffic surface; touching status read/write risks lifecycle breakage. Strangle one reader at a time; parity assertions (IC-08) gate each. Recommended deep-review: architect-alphonso.

### IC-02 — MissionExecutionContext composite (doc-09 fragments)

- **Purpose**: Grow `mission_runtime.ExecutionContext` into the doc-09 fragment / op-composite (identity, branch/ref incl. `destination_ref`=CommitTarget, workspace, status-surface, artifact-placement, prompt-source). Derive `mid8` and `target_branch` from a single source. This is the ExecutionContext-owner of ADR-2026-06-03-2.
- **Relevant requirements**: FR-001, FR-012 (mid8/target_branch single-derivation), NFR-004
- **Affected surfaces**: `mission_runtime/context.py`, `mission_runtime/resolution.py`
- **Sequencing/depends-on**: IC-01 (status-surface fragment consumes the resolved facade surface)
- **Risks**: fragment-boundary granularity is the key design call (deferred from research) — decide the exact cut by which ops co-consume fragments. Recommended sign-off: architect-alphonso.

### IC-03 — Read-path consolidation (Cluster A)

- **Purpose**: Route all surfaces through the context's read-path; collapse `candidate_feature_dir_for_mission` into `_read_path_resolver`; replace the `_find_feature_directory` silent fallback with a structured error (no silent fallback, per the C-009 selector rule); route `prompt_source_dir` through the context.
- **Relevant requirements**: FR-002, FR-012 (`_find_feature_directory`, `prompt_source_dir`)
- **Affected surfaces**: `missions/_read_path_resolver.py`, `missions/feature_dir_resolver.py`, prompt-source resolution sites
- **Sequencing/depends-on**: IC-02
- **Risks**: the silent-fallback removal will surface latent misconfigurations as errors (intended). Note: the `decision open` mid8-resolution bug observed during planning is an instance of this class — fold into the read-path repro set.

### IC-04 — Worktree-pointer parser collapse (Cluster C)

- **Purpose**: Delete the duplicate worktree-pointer parser in `workspace/root_resolver.py`; keep `core/paths.py` as the single parser feeding the context (~200 LOC removed).
- **Relevant requirements**: FR-002, NFR-005 (net subtraction)
- **Affected surfaces**: `core/paths.py`, `workspace/root_resolver.py`
- **Sequencing/depends-on**: IC-02 (parallelizable with IC-03)
- **Risks**: callers of the deleted parser must be re-pointed first (strangler order).

### IC-05 — Artifact-placement invariant adoption (Cluster D) — *unblocks the paused mission*

- **Purpose**: Resolve planning-artifact + analysis placement via the context's artifact-placement fragment at the two failing sites, eliminating the primary↔coord split that deadlocked the dogfood.
- **Relevant requirements**: FR-004 (#1816 implement-claim, #1814 record-analysis), FR-009 (#1764 analysis-report staleness keying context-aware)
- **Affected surfaces**: `cli/commands/implement.py` (`_ensure_planning_artifacts_committed_git`), `record-analysis` path, analysis-report freshness keying
- **Sequencing/depends-on**: IC-03
- **Risks**: directly governs whether paused mission 01KTNWFC can resume — SC-2 repro must pass. Verify against the recorded 01KTNWFC blockers.

### IC-06 — Runtime writers git-op guard (Cluster E) — *highest-risk, runs last among conversions*

- **Purpose**: `materialize_if_stale` must never re-materialize tracked status during a git op (rebase/reset), and its staleness key must be context-aware (no false-stale across CWDs).
- **Relevant requirements**: FR-005 (#1789, #1062), FR-012 (`materialize_if_stale` stale-key)
- **Affected surfaces**: `status/views.py`
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: highest blast radius (daemons/dashboard write here). SC-5 long-rebase scenario must pass with no clobber.

### IC-07 — retrospect + merge coord-topology reconciliation

- **Purpose**: Reconcile retrospect read/write to the canonical surface (no primary-checkout reads, no gitignored writes); reconcile merge coord-topology seams (PATH/env, baking step, mixed JSONL) to consume the context.
- **Relevant requirements**: FR-006 (#1735, #1771), FR-007 (#1736, #1770)
- **Affected surfaces**: retrospect read/write path, `merge/` executor PATH/env + baking + JSONL handling
- **Sequencing/depends-on**: IC-02
- **Risks**: merge is lifecycle-terminal; conversion must not regress the resumable merge-state machine.

### IC-08 — Parity ratchet extension (ATDD-first regression guard)

- **Purpose**: EXTEND `tests/architectural/test_execution_context_parity.py` with dual-CWD assertions (primary vs lane/coord) across the full lifecycle and a **flattened-topology synthetic fixture** so C-001 is proven, not just configured. Authored first (red), converges green as ICs land.
- **Relevant requirements**: FR-011, NFR-003, SC-1, C-001 proof
- **Affected surfaces**: `tests/architectural/test_execution_context_parity.py` (extend only — never fork)
- **Sequencing/depends-on**: scaffold authored first (ATDD-first, C-011); green-ness depends on IC-01..IC-07
- **Risks**: must stay deterministic; synthetic flattened fixture must not leak `test-feature-*` artifacts (memory: E2E test-feature leak).

### IC-09 — Dead-symbol deletion (strangler-ordered)

- **Purpose**: Delete the 5 dead `coordination/status_service.py` symbols (`EventLogWriteTarget`, `StatusContractError`, `StatusReadSource`, `append_event_log_batch`, `read_wp_lane_actor`) after consumers are on the facade.
- **Relevant requirements**: FR-013 (#1622, #391), NFR-005
- **Affected surfaces**: `coordination/status_service.py`
- **Sequencing/depends-on**: IC-01 (delete only once nothing references them)
- **Risks**: confirm zero live callers at deletion time (grep), not at plan time.

### IC-10 — Occurrence-map structural-move extension (adjacent, #1815)

- **Purpose**: Per operator decision, **extend** the occurrence-map schema and the bulk-edit-classification skill to model multi-path structural moves (from→to path mappings) in addition to the 8 term-rename categories — one artifact, broader schema.
- **Relevant requirements**: FR-010 (#1815)
- **Affected surfaces**: bulk-edit doctrine + `spec-kitty-bulk-edit-classification` skill, occurrence-map schema/loader + implement-gate validation
- **Sequencing/depends-on**: none (independent adjacent track; can run in parallel from the start)
- **Risks**: schema change must remain backward-compatible with existing single-term occurrence-maps; gate must not false-reject legacy maps. Recommended sign-off: architect-alphonso + doctrine.

### IC-12 — Dashboard read-only status (no tracked write on read) — *folded-in #1789 dashboard half* (squad-validated)

- **Purpose**: The **dashboard** is the only background tracked-status writer: its handlers call the *writing* `materialize()` on every kanban request, clobbering `status.json` during git ops. Switch to the read-only `materialize_snapshot` so reads never write tracked status; share WP07's git-op detection.
- **Relevant requirements**: FR-014(a) (complements FR-005 git-op guard)
- **Affected surfaces**: `src/specify_cli/dashboard/handlers/features.py` + `dashboard/scanner.py`
- **Sequencing/depends-on**: IC-06 (WP07 git-op guard — consumes/shares it). NOT the facade/context — the dashboard only reads.
- **Risks**: confirm `materialize_snapshot` returns the same payload shape the dashboard renders.

### IC-13 — Sync-daemon singleton + reaper consolidation — *folded-in #1789 daemon half / #1071 + FR-015 collapse*

- **Purpose**: The **sync daemon** (machine-global, missionless — writes NO status) leaks across interpreters. Two coupled jobs on one surface: **(b/FR-014)** enforce **one daemon per host/auth-scope** keyed on `DaemonOwnerRecord`, wiring the reaper into the `ensure_sync_daemon_running` spawn path; **(FR-015)** collapse the three duplicate orphan-reapers (`owner.is_orphan`/`list_orphan_records`, `orphan_sweep.sweep_orphans`, `daemon.scan_sync_daemons`/`cleanup_orphan_sync_daemons`, ~390 LOC) into the ONE canonical reaper, and dedup `_is_process_alive`/health-probe shared with `dashboard/lifecycle.py`. The collapsed single reaper is what gets wired into the spawn path — singleton + collapse are the same edit.
- **Relevant requirements**: FR-014(b), FR-015 (C-005/NFR-005 net subtraction)
- **Affected surfaces**: `src/specify_cli/sync/{owner.py,orphan_sweep.py,daemon.py}` (NOT `runtime.py`); `src/specify_cli/dashboard/lifecycle.py` (shared `_is_process_alive`/health-probe dedup)
- **Sequencing/depends-on**: none (daemon lifecycle is independent of context/facade; can run from the start). Coordinate with IC-12 only on the shared git-op detection.
- **Risks**: reaper blast radius — `_iter_sync_daemon_processes` matches any `run_sync_daemon` cmdline host-wide; must scope by executable/auth-identity or it regresses legitimate multi-user/container daemons. The collapse must preserve every real behavior of the three reapers (port-scan, cmdline-scan, record-based) — characterize before deleting.

### IC-11 — Deep review / sign-off (revision concern, R-07 pattern)

- **Purpose**: A dedicated revision/sign-off pass on the structural core: architect-alphonso deep-review of the context composite (IC-02), facade adoption (IC-01 + IC-12), and parity proof (IC-08); reviewer-renata for standard per-WP review across all WPs.
- **Relevant requirements**: NFR-001 (one resolution path / SC-4), NFR-004 (ADR + doc-09 conformance)
- **Affected surfaces**: cross-cutting (review only)
- **Sequencing/depends-on**: IC-02, IC-08 (and informed by all conversion ICs)
- **Risks**: this is the C-005 enforcement gate — confirm no second resolver/parity-test slipped in.

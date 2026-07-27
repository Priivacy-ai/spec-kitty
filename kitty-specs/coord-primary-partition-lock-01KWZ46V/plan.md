# Implementation Plan: Coord/Primary Partition Regression Lock

**Branch**: `design/coord-primary-partition-lock` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/coord-primary-partition-lock-01KWZ46V/spec.md`

## Summary

Complete and lock the coord/primary artifact-placement SSOT. A single topology-aware
placement authority already exists (`resolve_action_context` → `artifact_home_for` /
`MissionArtifactHome` + the two frozensets in `mission_runtime/artifacts.py`) and the
read side is ~90% routed through it. This mission formalizes that authority as the
public **seam** (kind-aware `write_target(kind)` / `read_dir(kind)`), routes the
remaining write bypasses through it — starting with the unowned create-time root
`core/mission_creation.py:176`, then the sibling-owned `implement.py`/`workflow.py`/
`tasks.py` sites (authoritative, per C-005) — extends the existing architectural ratchet
with the `CommitTarget(ref=<checkout>)` grammar that currently lets those bypasses pass,
hardens the two identity/topology bugs (#2091 composition guard, #2250 verify), and locks
the whole with an end-to-end characterization test. No new placement path is created; the
existing one is completed and made unbypassable.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (stdlib `ast` for the ratchet scanner); no new runtime deps
**Storage**: git (branch/worktree refs), `meta.json` mission metadata, `status.events.jsonl` (append-only) — files, no DB
**Testing**: pytest (unit + integration + `tests/architectural/` AST ratchets); `PWHEADLESS=1`; parallel `-n auto --dist loadfile`; red-first for new guards/routing (C-006)
**Target Platform**: Linux/macOS developer + CI (GitHub Actions)
**Project Type**: single (CLI library — `src/specify_cli/` + `src/mission_runtime/`)
**Performance Goals**: placement resolution bounded to `meta.json` + config reads (no worktree-tree scan, no husk probe — NFR-003); characterization test < 30 s (NFR-002)
**Constraints**: `ruff` + `mypy` zero-issue; per-function complexity ≤ 15; C-001 seam is sole placement access point; no new shadow path (SC-005)
**Scale/Scope**: the ~5 named checkout-derived write bypass sites (the kind-blind `resolve_feature_dir_for_mission` ~71-site / 18-write read sweep is deferred to #2453); 4 duplicate `_planning_read_dir` copies (DRY-only); 1 ratchet grammar extension; 2 bug loci; 1 characterization test; doc/roadmap truth-up

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (compact mode, `software-dev-default`). Relevant standing orders and how this plan satisfies them:

- **Canonical sources / unification (Directive-044)** — ✅ the plan *extends* the existing SSOT and ratchet; it explicitly forbids forking a parallel authority (C-001). This is the mission's thesis, not a risk.
- **Architectural gate discipline** — ✅ the ratchet (`test_no_write_side_rederivation.py`) is extended, not bypassed; new grammar closes a real blind spot (FR-011).
- **Red-first / test-remediation** — ✅ C-006 mandates a failing reproduction before each new guard/route; #2250 is verify-only (already shipped).
- **Terminology canon** — ✅ Mission terminology; the doc truth-up (FR-010) runs the terminology guard pre-push.
- **DDD tiered rigour** — the placement seam is core-domain (`mission_runtime/`) → higher rigour, characterization-first.

No unjustified violations. Complexity Tracking not required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coord-primary-partition-lock-01KWZ46V/
├── plan.md              # This file
├── research.md          # Phase 0 — squad evidence + decisions D1–D10
├── data-model.md        # Phase 1 — placement entities/value objects
├── quickstart.md        # Phase 1 — how to verify the strangle
├── contracts/           # Phase 1 — seam API + ratchet contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── mission_runtime/
│   ├── artifacts.py          # kind→partition SSOT (frozensets, artifact_home_for, MissionArtifactHome)  [FR-002]
│   ├── context.py            # MissionTopology 2×2 + routes_through_coordination                          [FR-003, FR-012]
│   └── resolution.py         # resolve_action_context root; resolve_placement_only → CommitTarget         [FR-001]
├── specify_cli/
│   ├── core/mission_creation.py          # _commit_feature_file (create-time write root)                 [FR-004 · IC-02]
│   ├── coordination/
│   │   ├── workspace.py                   # CoordinationWorkspace composition (empty-mid8 guard)          [FR-007 · IC-05]
│   │   ├── surface_resolver.py            # resolve_status_surface (coord read) + husk guard              [FR-005, FR-012]
│   │   └── commit_router.py              # _resolve_planning_placement (write projection)                 [FR-001/004]
│   ├── missions/_read_path_resolver.py    # read seam; resolve_feature_dir_for_mission (kind-blind)       [FR-005]
│   ├── cli/commands/
│   │   ├── implement.py                   # write sites :885,:1462                                        [FR-004 · IC-03]
│   │   └── agent/workflow.py              # write sites :487/503/549/1694                                 [FR-004 · IC-03]
│   │   └── agent/tasks*.py                # move-task/mark-status write cluster (coord w/ #2438)           [FR-004 · IC-03]
│   └── (4× _planning_read_dir wrapper copies → consolidate to one shared helper)                          [FR-001]
tests/
├── architectural/
│   ├── test_no_write_side_rederivation.py   # extend: CommitTarget(ref=<checkout>) grammar + allow-list  [FR-011 · IC-04]
│   └── resolution_gate_allowlist.yaml       # shrink coord_authority_baseline                             [NFR-001]
├── integration/  or  tests/e2e/             # FR-009 golden-path characterization test                    [FR-009 · IC-06]
└── (focused unit tests per strangled site + bug loci)
docs/
├── release-goals/3.2.x.md                   # whole #1878 → 3.2.x                                         [FR-010 · IC-07]
└── (AGENTS.md / CLAUDE.md "planning happens in main" retirement)                                          [FR-010 · IC-07]
```

**Structure Decision**: Single-project CLI library. The placement authority lives in the
core-domain package `src/mission_runtime/`; consumers live in `src/specify_cli/`. The
mission touches existing files only — it adds no new package. The seam is the public face
of `resolve_action_context`; leaf resolvers remain as delegating implementation details.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are architectural areas, not work packages. `/spec-kitty.tasks` translates them
> into executable WPs (one concern may split into several WPs, or several merge into one).

### IC-01 — Placement seam formalization (the authority)

- **Purpose**: Expose the existing `resolve_action_context` root as the single kind-aware placement seam (`write_target(kind)` / `read_dir(kind)`, classified by `MissionArtifactHome`), and consolidate the 4 duplicate `_planning_read_dir` wrappers into one shared helper.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-006, FR-012, C-001, C-002.
- **Affected surfaces**: `mission_runtime/resolution.py`, `mission_runtime/artifacts.py`, `mission_runtime/context.py`, `missions/_read_path_resolver.py`, the 4 `_planning_read_dir` copies (`mission_feature_resolution.py`, `orchestrator_api/commands.py`, `acceptance/__init__.py`, `agent/mission.py`).
- **Sequencing/depends-on**: none — foundation for IC-02/IC-03.
- **Risks**: Must be a *thin* authority (bounds FR-001 size); write and read have different outputs (CommitTarget vs dir/surface) → one authority, two methods. Do not fork.

### IC-02 — Create-time write-site strangle (unowned bullseye)

- **Purpose**: Route `mission_creation.py:176` (`_commit_feature_file`) through the seam so the spec commit's destination comes from `write_target(SPEC)`, not `CommitTarget(ref=current_branch)`.
- **Relevant requirements**: FR-004, C-001, C-006.
- **Affected surfaces**: `src/specify_cli/core/mission_creation.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: Create-time is load-bearing (every mission); red-first reproduction of the split-brain required.

### IC-03 — Sibling-owned write-site strangle (authoritative)

- **Purpose**: Route `implement.py:885/1462`, `workflow.py:487/503/549/1694`, the `tasks.py` move-task/mark-status cluster, **and `mission_record_analysis.py:80` (`_resolve_record_analysis_placement_ref`, ANALYSIS_REPORT — the second CommitTarget producer the squad missed; SC-001 requires it)** through the seam; authoritative over sibling missions.
- **Relevant requirements**: FR-004, FR-011, C-001, C-005, C-006. **See D11** (forbidden-fallback resolution).
- **Affected surfaces**: `cli/commands/implement.py` (incl. `_resolve_placement_ref:672` + legacy fallback `:1467`), `cli/commands/agent/workflow.py`, `cli/commands/agent/tasks*.py`, `cli/commands/agent/mission_record_analysis.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: C-005 authority — siblings rebase onto this; operator sequences merges. **#2438 just landed on `tasks.py`/`tasks_move_task.py`** — reconcile with the new move-task gate code. Inline `coord_branch if … else …` decisions → `routes_through_coordination`. **Extraction budget (stay ≤15 complexity):** `_mt_commit_wp_file` (`tasks_move_task.py:1252`, at 13) and `_stage_artifacts_in_coord_worktree` (`commit_router.py:376`, at 13) must extract a placement helper *before* adding routing; `commit_for_mission` (`commit_router.py:98`, at 11) watch headroom; for `workflow.py` (2830 LOC) add ONE `_resolve_workflow_placement` helper, not 4× inline.
- **D11 — forbidden-fallback resolution (binding)**: two live `if …is None: CommitTarget(ref=<checkout>)` legacy fallbacks (`implement.py:672→:1467`, `mission_record_analysis.py:80`) violate the no-legacy-resolver-paths standing order. Resolve **fail-closed / require-canonical**: replace the None→legacy-checkout fallback with a structured error; support any genuinely-legacy mission via migration/backfill, not a silent runtime fallback. The inline "C-004 never break the lifecycle" justification does not license a silent shadow path — these are exactly the `CommitTarget(ref=<checkout>)` sites the IC-04 grammar must catch.

### IC-04 — Ratchet extension + baseline lock

- **Purpose**: Add the `CommitTarget(ref=<checkout>)` grammar to the write-side ratchet, pin/shrink the write-side allow-list (seed=1 @ `status_transition.py:347`), expand the adopted-module set as sites are strangled, and allow-list the tracked-VISIBLE residuals (retrospective authority + `#2453` fallbacks). **`coord_authority_baseline` stays at 7** — its read-side drain is deferred to #2453 (post-squad).
- **Relevant requirements**: FR-011, NFR-001, SC-005.
- **Affected surfaces**: `tests/architectural/test_no_write_side_rederivation.py`, `tests/architectural/resolution_gate_allowlist.yaml`, `test_resolution_authority_gates.py`.
- **Sequencing/depends-on**: co-evolves with IC-02/IC-03 (adopt a module only once it is strangled — else the ratchet goes red before the route lands).
- **Risks**: Shared substrate with the sibling gate-hardening mission (C-005). The grammar must not false-positive on the sanctioned coord primitives (`branch_naming.py` `coord_*`) or the legacy allow-list.

### IC-05 — Identity/topology hardening (#2091, #2250, husk)

- **Purpose**: Add the empty-`mid8` guard at `CoordinationWorkspace` composition (#2091, red-first); verify + regression-lock the #2250 never-created path and distinguish it from `DELETED`/`UNMATERIALIZED`; enforce stored-topology-not-husk (FR-012).
- **Relevant requirements**: FR-007, FR-008, FR-012, C-006.
- **Affected surfaces**: `coordination/workspace.py`, `missions/_read_path_resolver.py` (husk guard region), `coordination/surface_resolver.py`.
- **Sequencing/depends-on**: none (parallelizable with IC-01..IC-04); FR-012 aligns with IC-01.
- **Risks**: #2091 is defense-in-depth over an existing upstream guard — the red test must target the composition locus specifically.

### IC-06 — Regression lock (characterization test)

- **Purpose**: End-to-end golden-path test (`create → spec → setup-plan → tasks status → decision verify`) + ≥1 lifecycle mutation, CWD-independent, across coord and non-coord topologies.
- **Relevant requirements**: FR-009, NFR-002, C-007.
- **Affected surfaces**: `tests/integration/` or `tests/e2e/`.
- **Sequencing/depends-on**: IC-01..IC-03 (tests the routed behavior); **soft-gated on PR #2429** landing (C-007) — sequence this WP last / after #2429.
- **Risks**: Timing on #2429; must characterize post-#2429 `resolve_planning_read_dir` to avoid an immediate re-pin.

### IC-07 — Docs & roadmap truth-up

- **Purpose**: Retire "planning happens in main" (AGENTS.md/CLAUDE.md), correct #1716's stale decision (issue body), rewrite roadmap to move whole #1878 → 3.2.x, correct inventory references.
- **Relevant requirements**: FR-010, SC-004.
- **Affected surfaces**: `AGENTS.md`, `CLAUDE.md`, `docs/release-goals/3.2.x.md`, GitHub issue #1716.
- **Sequencing/depends-on**: none.
- **Risks**: Terminology guard (`test_no_legacy_terminology.py`) + docs-freshness gate must pass; roadmap edit follows operator decision (whole strangler → 3.2.x), not the squad's narrower reading.

## Post-plan brownfield addenda (fold into /tasks)

Refinements from the post-plan brownfield check — apply during WP decomposition:

- **IC-01 scope-down**: the four `_planning_read_dir` copies **already delegate** to `resolve_planning_read_dir` — so "consolidate to one helper" is **DRY-only, low-risk**, not authority de-duplication. Do not over-scope it. Also census (don't assume 3rd authority): `status.py:113/:201` `_resolve_status_surface*` are thin consumers of `MissionStatus.load` — confirm, don't re-route.
- **IC-01/IC-04 campsite**: `_planning_commit_worktree` (`commit_router.py:475`) has a **stale name** post-D2 (planning never transits coord) — rename/simplify; its PRIMARY-kind guard **raises** (not `assert` — survives `python -O`) — a real invariant, do **not** delete.
- **IC-04 reuse**: EXTEND the already-shipped partition-stability gate `tests/architectural/test_write_surface_placement_guard.py` (#2198, CLOSED) — do not re-implement it. IC-04 adds the `CommitTarget(ref=<checkout>)` grammar on top.
- **IC-06 fold (#2404, lite)**: add an `ACCEPTANCE_MATRIX` read-partition assertion to the characterization test (accept must not read the acceptance-matrix from a stale `-coord` worktree); cross-link #2404. Full #2404 fix may remain a fast-follow, but the regression belongs here.
- **OUT → tracked (do not fold)**: #2334 (cross-worktree kitty-specs copy drift — root addressed here, copy-elimination separate), #2139 (`core/paths.py` target_branch silent-`main` fallback — same anti-pattern class, different surface; the IC-04 grammar should eventually cover it), #2138 (#2400 identity surface), dashboard `scanner.py:436/563` placement (dashboard-adjacent). Cross-link, don't poach.
- **Sibling boundary (C-005)**: #2160 residuals #2197/#2199/#2214 are sibling-owned gate-hardening — do not fold; coordinate per C-005.

# Implementation Plan: Coord-Read Residuals — Merge/Lanes Planning Reads + Identity-Read Routing

**Branch**: `mission/coord-read-residuals-2185-2186` | **Date**: 2026-06-26 | **Spec**: `kitty-specs/coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V/spec.md`
**Input**: Feature specification (#2185 Lane A + #2186 Lane B; children of epic #2160, siblings of #2115).

## Summary

Route the PRIMARY-partition reads that still resolve through coord-aware resolvers (landing on the empty `-coord` status husk after #2106) onto the existing read-path seam. **Lane A (#2185)**: ~10 sites in `merge/`, `lanes/`, `core/worktree_topology` reading `lanes.json`/`tasks/`/`meta.json` → `resolve_planning_read_dir(kind=...)`, with per-leg splits where one resolved dir feeds both a PRIMARY and a STATUS leg. **Lane B (#2186)**: command-layer identity/type reads (`next_cmd.py`, owned `workflow.py` legs, `implement.py:1394`) → `primary_feature_dir_for_mission` + `_canonicalize_primary_read_handle`. Both lanes are backed by a **single net-new call-shape scan arm** covering the two shapes the ratchet's literal vocabulary cannot see: `lanes.json` reads (scope `merge/`+`lanes/`+`core/worktree_topology.py`) and `meta.json` function-call identity reads (scope `cli/commands/`). The technical approach is **consume-not-author**: the resolver seam already exists and is in production use; this mission only re-points call sites and extends the gate. Lands after the implement-loop sibling (inherits its whole-`src` scanner **scope** widening — but **no #2185 pin hand-off** exists, since the literal vocabulary is blind to `lanes.json`/`meta.json` reads and the merge/lanes/core cluster has zero pins; re-resolves Lane B line citations against merged `main`). The #2185 regression backstop is the FR-009 divergent-fixture revert-fails test, not a pin drain.

## Technical Context

**Language/Version**: Python 3.11+ (CLI; `ruff` + `mypy` clean, McCabe complexity ≤ 15)
**Primary Dependencies**: the read-path resolver seam — `specify_cli.missions._read_path_resolver` (`resolve_planning_read_dir`, `primary_feature_dir_for_mission`, `_canonicalize_primary_read_handle`); `mission_runtime` partition authority (`MissionArtifactKind`, `is_primary_artifact_kind`); `typer`, `rich` (existing CLI stack). No new runtime dependency.
**Storage**: filesystem planning artifacts (`kitty-specs/<mission>/`: `meta.json`, `lanes.json`, `tasks/`, `status.events.jsonl`) across PRIMARY checkout vs. `-coord` git-worktree husk. No database.
**Testing**: `pytest`; architectural ratchet gates (`tests/architectural/test_gate_read_literal_ban.py`, `test_resolution_authority_gates.py`); the merged sibling's already-divergent real `git worktree` coord fixture (`tests/integration/coord_topology_fixture.py`), extended with the FR-009 sentinel-husk-meta variant (NOT `write_side/topology_fixtures.py::build_coord`). Integration-over-stubs (NFR-004).
**Target Platform**: Linux / macOS / Windows CLI (loopback/local only; no network).
**Project Type**: single (library + CLI; `src/specify_cli/`).
**Performance Goals**: behavioral parity — read-routing only; no measurable runtime change. PRIMARY routing is a no-op on flat topology (NFR-003).
**Constraints**: STATUS-partition reads stay coord-aware (C-001); no silent fallback on ambiguous/coord-deleted handles (C-002, #1848); consume the resolver, never edit its internals (C-002); surface exclusivity vs. the implement-loop ROUTE surface (C-009-mirror); `scripts/tasks/` legacy reader untouched (C-EXCL-2167); does not remove the `implement.py:1018` fallback (C-EXCL-FALLBACK); lands after the implement-loop sibling (C-SEQ).
**Scale/Scope**: Lane A ≈ 10 sites (3 mixed PRIMARY+STATUS needing per-leg split) + 1 coord-topology integration test; Lane B ≈ 6 command-layer identity sites + 1 net-new gate arm (with synthetic-AST non-vacuity self-test) + floor recompute. Estimated 5–7 WPs.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Integration-over-stubs (NFR-004)**: the #2185 acceptance proof drives real code against a real `git worktree` coord fixture with a **divergent** husk — PASS by design (FR-009). Unit stubs handing in a primary dir are explicitly disallowed.
- **Gate-can't-self-validate**: the net-new identity arm (Lane B) and its remediation co-land in this mission, validated by a pre-merge full-gate dry run + a committed synthetic-AST non-vacuity self-test — PASS (US3/FR-007/FR-008).
- **Terminology canon**: prose uses "Mission"; no `feature*` aliases on active domain objects — PASS.
- **Sonar/complexity**: read-routing edits keep touched functions ≤ 15; per-leg split extractions get focused tests — PASS by constraint.
- **Realistic test data**: the coord fixture seeds production-shaped `lanes.json`/`tasks/`/`meta.json` (real ULIDs, real WP ids) — PASS (FR-009).
- **Canonical sources**: consumes the documented resolver seam; no improvised path reconstruction — PASS (C-002).

No charter violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V/
├── spec.md              # committed (revised post-squad)
├── issue-matrix.md      # committed (#2185/#2186 in-mission)
├── plan.md              # this file
├── research.md          # Phase 0 (3-agent code-state research, summarized below)
├── data-model.md        # Phase 1 — the artifact-kind partition + per-site route table
├── contracts/           # Phase 1 — resolver-consumption contract + identity-arm contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── merge/                  # Lane A: forecast.py, executor.py (mixed), resolve.py, done_bookkeeping.py (mixed)
├── lanes/                  # Lane A: merge.py, recovery.py (mixed:356), worktree_allocator.py
├── core/worktree_topology.py   # Lane A: single swap co-resolves 3 PRIMARY legs
├── cli/commands/
│   ├── merge.py            # Lane A: :269 meta.json
│   ├── next_cmd.py         # Lane B: :187/:253/:619 identity/type (re-resolved on merged main)
│   ├── implement.py        # Lane B: :1394 (was :1389) shared-variable, own anchor
│   └── agent/workflow.py   # Lane B: owned identity legs ONLY (re-resolve vs merged main)
└── missions/_read_path_resolver.py   # CONSUMED ONLY — not edited (C-002)

tests/
├── architectural/test_gate_read_literal_ban.py        # FR-007 new call-shape arm (lanes.json + identity); FR-011 #2187 pin; FR-006 honest-scope note
├── architectural/test_resolution_authority_gates.py   # FR-010 floor recompute (honest census)
└── integration/coord_topology_fixture.py             # FR-009: reuse merged divergent fixture + add sentinel-husk-meta variant (NOT build_coord); new coord-topology merge test
```

**Structure Decision**: single project. Edits are confined to the owned surfaces above; the resolver seam and the implement-loop ROUTE surface (`tasks.py`, `workflow.py` route legs, `tasks_dependency_graph.py`, `workspace/context.py`, …) are out of scope (C-009-mirror).

## Phase 0 — Research (summary; full findings in research.md)

Three independent code-state agents verified against `main`:
- **Kind corrections confirmed**: 6 of 10 #2185 issue labels are wrong (3 sites read `meta.json` not LANE_STATE; 1 reads `lanes.json` not `tasks/`); `executor`/`done_bookkeeping`/`recovery:356` are mixed PRIMARY+STATUS (debugger fully traced `executor.py` `feature_dir`→`run.feature_dir`→`status_feature_dir` at `:503`/`:560`). Route by real partition.
- **Husk failure mode real**: `meta.json`/`lanes.json`/`tasks/` are PRIMARY-only; `next_cmd.py:187/253` swallow `FileNotFoundError` (silent drop); `:619` (was `:631`) falls back to default `software-dev` type (wrong-routing).
- **Gate blindness confirmed**: the scanner's literal vocabulary is `tasks`/`.md` dir-join literals only — it is **blind to `lanes.json` (LANE_STATE) AND to `meta.json` function-call reads**. So the merge/lanes/core #2185 cluster has **zero pins** (none can be added), and identity reads escape too → a single net-new **call-shape arm covering both shapes** is needed (FR-007).
- **#2115 sequencing**: `implement.py:1394` (was `:1389`) is correct only via the `:1018` fallback; guards must precede fallback removal (C-EXCL-FALLBACK).

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Foundational gate: call-shape arm (lanes.json + identity) + floor + fixture

- **Purpose**: Build the net-new **call-shape scan arm** covering BOTH the `lanes.json` shape (`merge/`+`lanes/`+`core/worktree_topology.py`) and the identity shape (`cli/commands/`), each with a synthetic-AST non-vacuity self-test; recompute `ROUTED_CANONICALIZER_FLOOR` (honestly — if seam-routing did not move the census, say so). This is the detector that makes BOTH residual classes observable, since the ratchet's literal vocabulary is structurally blind to `lanes.json` and to `meta.json` function-call reads. WP01 also **owns the divergent-fixture extension** (the FR-009 sentinel-husk-meta variant) so every consumer (its own identity tests + the Lane A per-site tests + WP04) shares one divergence definition. The sentinel variant is a **distinct fixture/parametrization that *writes* a husk `meta.json`** (sentinel id `6KERGF2ZNFBPR91YEZMARG99KS`), explicitly **OVERRIDING the base `coord_topology_fixture.py` invariant `assert not (coord_mission_dir / "meta.json").exists()`**; its precondition binds to the fixture's actual resolved primary id (`01KW2E7AFC0000000000000001`, the reused sibling's), asserting the sentinel `!= ctx.mission_id`.
- **Relevant requirements**: FR-007, FR-009 (fixture extension), FR-010, C-003. (FR-006 honest-scope note + FR-011 narrowed #2187 preflight live with the Lane A merge-cluster concern IC-02 / its pin-presence preflight subtask — not here.)
- **Affected surfaces**: `tests/architectural/test_gate_read_literal_ban.py`, `test_resolution_authority_gates.py`, `tests/integration/coord_topology_fixture.py` (sentinel-husk-meta variant).
- **Sequencing/depends-on**: none (foundational). Mirrors the sibling's dedicated gate WP to avoid a shared-ratchet-file merge race; the only drainable pin in scope is #2187 (the #2187 drain subtask).
- **Risks**: identity-arm scope creep beyond `cli/commands/` + `agent_utils/status.py` (or lanes.json-arm creep beyond `merge/`+`lanes/`+`core/`) would red-CI on out-of-scope strangers (sync/acceptance/policy) — bound each shape. Gate-can't-self-validate → pair with a pre-merge full-gate dry run.

### IC-02 — Lane A: merge cluster routing

- **Purpose**: Route the `merge/` PRIMARY reads by real kind, splitting the mixed sites per-leg (STATUS stays coord-aware). **No merge-cluster #2185 pin exists to drain** (vocabulary-blind); regression coverage is the FR-007 lanes.json arm + the FR-009 divergent fixture.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-006 (honest-scope note in the pin-presence preflight subtask), FR-008 (merge cluster = arm + fixture coverage, not a pin drain), FR-011 (narrowed #2187 pin-presence preflight subtask).
- **Affected surfaces**: `merge/forecast.py` (`:153`+`:159`), `merge/executor.py` (mixed split), `merge/resolve.py` (`:98` PRIMARY_METADATA), `merge/done_bookkeeping.py` (`:237` WP-path leg + comment removal, keep status-transactional legs on primary), `cli/commands/merge.py` (`:269`).
- **Sequencing/depends-on**: IC-01 (the call-shape arm + divergent fixture present to test against); rebase onto post-implement-loop `main` first.
- **Risks**: over-routing a STATUS leg (NFR-001); `done_bookkeeping` status legs must stay on the meta-bearing primary dir, not be coord-ified.
- **Brownfield refinement**: in `executor.py`, **route the `:976` legs DIRECTLY, per-leg** — `:981`/`:1003` `resolve_mission_identity` → META and `:997` `require_lanes_json` → LANE_STATE seam — keeping the `run.feature_dir` STATUS leg coord-aware. These legs live in `_run_lane_based_merge` (def `:947`), a **different function** from the `:887` PRIMARY anchor in `_run_lane_based_merge_locked` (def `:866`); do **not** thread `:887` through (the prior plan's threading direction was wrong — verified on merged `main`). In `merge/resolve.py` route only `:98` (meta read); leave `:63` (handle→dir-name canonicalization at the no-silent-fallback boundary) on `candidate_`. Do not reintroduce the silent `main` target-branch fallback (#2139 neighborhood).

### IC-03 — Lane A: lanes/core cluster routing

- **Purpose**: Route the `lanes/` + `core/worktree_topology` + `agent_utils/status.py` (`show_kanban_status`, #2187) PRIMARY reads; `recovery.py:356` per-leg split. The lanes/core sites have **no #2185 pins** (vocabulary-blind); the **only drainable pin in this cluster is #2187** (`show_kanban_status`, a `tasks/` literal) — drained by the #2187 drain subtask.
- **Relevant requirements**: FR-001, FR-002, FR-008 (the single genuine pin-drain is #2187).
- **Affected surfaces**: `lanes/merge.py` (`:68`/`:198`), `lanes/recovery.py` (`:356` mixed, `:611` LANE_STATE; **KEEP `:664` coord-aware** — STATUS-write leg feeding `emit_status_transition_transactional` @ `:686`), `lanes/worktree_allocator.py` (`:360` meta.json), `core/worktree_topology.py` (`:138` single swap co-resolves three PRIMARY legs), `agent_utils/status.py` (`show_kanban_status` `:126` `tasks/` glob → resolver, keep `:151` `read_events` coord-aware; #2187 pin drain. The adjacent `:132` `resolve_mission_identity` leg is the #2186 identity class — route to `kind=PRIMARY_METADATA`, gated by the FR-007 identity arm whose scope now includes `agent_utils/status.py`).
- **Sequencing/depends-on**: IC-01 (+ IC-02 gate-file chain).
- **Risks**: `worktree_allocator` chicken-and-egg (reads meta to discover coord) — `kind=PRIMARY_METADATA` is topology-blind and correct. Never route the `:664` STATUS-write leg (C-001/#2155 analog).
- **Brownfield refinement (sizing)**: `lanes/recovery.py::scan_recovery_state` already carries `# noqa: C901` (over the complexity ceiling). The per-leg split must **extract the PRIMARY-planning read and the status-events read into named helpers + drop the `# noqa` + add focused tests** — not add another branch. **Guardrail:** `candidate_feature_dir_for_mission` is the C-005 STATUS primitive — re-point PRIMARY reads off it, never remove or "converge away" the coord-aware primitive (would break C-001).

### IC-04 — Lane A: coord-topology integration proof

- **Purpose**: Reuse the merged sibling's **already-divergent** fixture (`tests/integration/coord_topology_fixture.py`: STATUS-only husk — no `tasks/`/`lanes.json`/`meta.json`) — extended by WP01 with the **sentinel-husk-meta variant** (husk `meta.json` present-but-wrong, `mission_id = 6KERGF2ZNFBPR91YEZMARG99KS` ≠ PRIMARY; `lanes.json`+`tasks/` PRIMARY-only). Add a real merge/recovery/topology integration test that fails — on a **returned domain value** — if any routed read reverts to coord-aware. **Do NOT** retrofit `write_side/topology_fixtures.py::build_coord` (non-divergent husk, ~26 consumers).
- **Relevant requirements**: FR-009, NFR-003, NFR-004, SC-001.
- **Affected surfaces**: `tests/integration/coord_topology_fixture.py` (fixture extension owned by WP01), `tests/integration/` (new coord-topology merge test).
- **Sequencing/depends-on**: WP01 (fixture extension) + IC-02/IC-03 (the routed code under test).
- **Risks**: a non-divergent husk silently passes a broken routing (the squad's CRITICAL finding) — the HARD-precondition divergence assertion (`assert not (husk/"lanes.json").exists()`; husk meta `mission_id == 6KERGF2ZNFBPR91YEZMARG99KS`) is the guard.

### IC-05 — Lane B: identity routing + ownership table

- **Purpose**: Emit a definitive per-site ROUTE/KEEP/owned-by-implement-loop table (cross-checked vs the sibling's ROUTE+KEEP list, re-resolved against merged `main`), then primary-anchor the genuinely-owned identity sites — including the shared-variable mixed sites with their own anchor.
- **Relevant requirements**: FR-004, FR-005, FR-007 (consumes IC-01 identity arm), FR-008 (Lane B co-land), C-003 (identity routing matches the implement-loop seam model — primary-anchor + caller-side canonicalization, no silent fallback).
- **Affected surfaces** *(citations re-resolved on merged `main`)*: `cli/commands/next_cmd.py` (`:187`/`:253`/`:619`), `cli/commands/implement.py` (`:1394` own anchor), `cli/commands/agent/workflow.py` (owned identity legs `:1282`/`:2739` clean; `:1644` shared-variable own anchor) — only legs NOT inside the implement-loop ROUTE scope.
- **Sequencing/depends-on**: IC-01 (the arm must exist before its sites can be ratchet-validated); rebase onto merged `main` to re-resolve citations.
- **Risks**: a site falling into the gap between the two missions (neither routes it) — the ownership table must account for every Lane B site, no "verify later".

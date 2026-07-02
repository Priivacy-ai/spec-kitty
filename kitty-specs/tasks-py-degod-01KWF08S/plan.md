# Implementation Plan: Degod tasks.py — thin CLI over pure cores (Wave 1)

**Branch**: `design/degod-tasks-2116` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/tasks-py-degod-01KWF08S/spec.md`

## Summary

Decompose the `agent tasks` god-command (`src/specify_cli/cli/commands/agent/tasks.py`,
~3,617 LOC, 9 subcommands) into a **thin CLI shell over pure decision/aggregation cores behind
injected ports** — a behavior-preserving (pure-parity) refactor closing #2116 under #2173.
Approach (settled by two pre-plan squads + a 4-lens post-tasks squad): freeze the full CLI contract
with a golden characterization harness *first* (freezing **every** `move_task` decision branch, not
just the skip/refuse arms), co-design a **stratified** port set (2 program-reference ports — `FsReader`
+ a **two-capability** `CoordCommitRouter` [`commit_status` + `commit_artifact`, disjoint seams] — + 2
mission-local seams), extract three pure cores (each wired by **deleting** its inline block + a sentinel
test), thin the fat bodies to orchestrators, fold the pre-3.0 read-authority split-brain (pinned kinds
+ a dir-equivalence proof), and honestly drain the resolution-authority census (shrink-only, enumerated
cross-base artifact) on top of #2072's already-landed composite-key re-key. **9 strictly-linear WPs.**

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (existing; no new runtime deps)
**Storage**: files (kitty-specs planning artifacts, `status.events.jsonl`, git worktrees) — N/A change
**Testing**: pytest — a **golden CLI-characterization harness** (extends `test_tasks_cli_contract.py`, adds a coord-topology + protected-branch fixture) as the parity guard + **per-core unit tests** (the failing-first/red-on-base artifact for these pure-parity WPs, satisfying charter C-011); selected in CI via the Wave-0 marker binding (#2294, merged)
**Target Platform**: Linux/macOS CLI (the `spec-kitty` toolkit)
**Project Type**: single (CLI tool)
**Performance Goals**: N/A (behavior-preserving refactor — no runtime-perf target)
**Constraints**: **pure parity** (100% golden cases byte-identical pre/post each WP); each command body ≤150 LOC and each extracted helper ≤150 LOC, CC ≤15; ruff + mypy clean, 0 new suppressions; net-zero new arch-ratchet entries (shrink-only floors)
**Scale/Scope**: `agent tasks` surface only (9 subcommands / 53 params); ~3,617 LOC → ≤1400 LOC thin surface + cores; 9 strictly-linear work packages

## Charter Check

*GATE: Must pass before Phase 0. Re-checked after Phase 1.* Charter `.kittify/charter/charter.md` (v1.2.0), governed under the #2299 compiled doctrine.

| Charter/doctrine principle | Status | Note |
|---|---|---|
| Branch/PR strategy (no direct push to main) | ✅ | plan on `design/degod-tasks-2116`; PR to main after #2299 |
| Terminology Canon (no `feature*`) | ✅ | new symbols `resolve_planning_read_dir`, `TasksPorts`, `CoordCommitRouter` — no feature-surface |
| Code Quality (CC≤15, ruff/mypy, no suppressions) — DIRECTIVE_030 | ✅ | NFR-003 |
| **C-011 ATDD-first (failing-first per WP)** | ✅ *(reconciled)* | pure-parity WPs deliver no new observable behavior → the red-first artifact is the **per-core unit test** (RED against the not-yet-extracted core); the golden harness is the green parity guard (NFR-002) |
| DIRECTIVE_040 (structural intervention over point-fix) | ✅ | the "why-now": #1 change-magnet, recurring defect class |
| DIRECTIVE_041 (tests as scaffold; observable contracts; anti-vacuity) | ✅ | golden freezes observable contract; NFR-002 enumerates branches from the harness |
| DIRECTIVE_043 (shrink-only ratchet, non-vacuous gate) | ✅ | FR-011/NFR-005; C-002 preserves canonicalizer-gate non-vacuity |
| DIRECTIVE_044 (canonical-source unification) | ✅ | FR-009 (CoordRead≠CoordWrite), FR-010 (pre30 read unification) |
| `post-merge-arch-gate-adjudication` procedure | ✅ | WP08 + mission-merge full `tests/architectural/` cross-base sweep |

**No charter violations.** No entries in Complexity Tracking.

## Project Structure

### Documentation (this mission)
```
kitty-specs/tasks-py-degod-01KWF08S/
├── plan.md              # this file
├── research.md          # Phase 0 — the settled design decisions (squad-derived)
├── data-model.md        # Phase 1 — port protocols + decision-core value objects
├── contracts/           # Phase 1 — port interfaces + decision-core I/O contracts
├── quickstart.md        # Phase 1 — validation scenarios (golden + per-core)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)
```
src/specify_cli/cli/commands/agent/
├── tasks.py                    # → thin surface (target: ≤1400 LOC, 0 inline json.dumps; owned by WP09)
├── tasks_ports.py              # NEW — TasksPorts protocols + Real/Fake adapters (program: FsReader, CoordCommitRouter[commit_status + commit_artifact]; local: GitOps, Render)
├── tasks_transition_core.py    # NEW — pure move_task transition decision
├── tasks_mapping_core.py       # NEW — pure requirement-mapping decision
├── tasks_status_view.py        # NEW — pure status aggregation
├── tasks_outline.py            # existing seam (from #2058/#2114)
├── tasks_materialization.py    # existing seam
├── tasks_parsing_validation.py # existing seam
├── tasks_finalize_validation.py# existing seam (mark_status/finalize thin via this)
└── tasks_dependency_graph.py   # existing seam

tests/specify_cli/cli/commands/agent/
├── test_tasks_cli_contract.py          # golden harness (EXTENDED: coord-topology fixture + ALL move_task branches + branch-cov gate)
├── test_tasks_ports.py                 # NEW — port stratification + FR-010 dir-equivalence proof (WP02)
├── test_tasks_transition_core.py       # NEW — per-branch unit tests (--cov-branch gated)
├── test_tasks_mapping_core.py          # NEW
├── test_tasks_status_view.py           # NEW
├── test_move_task_orchestration.py     # NEW — WP06 sentinel + orchestration
├── test_tasks_orchestration.py         # NEW — WP07/WP08 orchestration + non-import AST gate
└── test_tasks_shim.py                  # NEW — WP09 AST 0-json.dumps + LOC ceiling

tests/architectural/
├── resolution_gate_allowlist.yaml      # census entries DRAIN (shrink) as bodies thin (FR-011); baseline 13→12
├── test_resolution_authority_gates.py  # floors lowered shrink-only + margin gate (WP09; reviewer-signed cross-base artifact)
└── (NEW tasks.py LOC gate: 5 bodies ≤150, helpers ≤150, total ≤1400)
```

**Structure Decision**: single-project CLI. New sibling modules alongside `tasks.py` (matching the #2056 `mission_*` sibling-extraction template); the command file becomes a registration shim. No new packages.

## Implementation Concern Map

> Concerns are architectural areas, not work packages. `/spec-kitty.tasks` translates them into executable WPs (the post-squad **9-WP** shape is the target — WP07 is split into a core-backed slice (WP07) and a coreless slice (WP08); render+shim+census is WP09); one concern may span multiple WPs.

### IC-01 — Behavior characterization (the parity anchor)
- **Purpose**: Freeze the exact observable `agent tasks` contract *before* any extraction, so the refactor is provably behavior-preserving.
- **Relevant requirements**: FR-001, C-004, NFR-001.
- **Affected surfaces**: `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py` (extend); a **new coord-topology + protected-branch fixture class** constructing real on-disk coord-worktree state.
- **Sequencing/depends-on**: none — must be first.
- **Risks**: the crown-jewel **coord skip-exit-0 arm** and the exit-1 refuse arms are NOT covered by the existing harness (its docstring punts them); **and neither are move_task's OTHER decision branches** (arbiter-override, rejected-verdict, planning-artifact, review-currency, force) — the golden must freeze **all** of them (a from-harness branch-coverage measurement of the mutating commands is the DoD, not "skip+refuse pinned"), or WP03 extracts unguarded branches. The skip-arm assertion must be *distinguishing* (primary HEAD unchanged + coord event), not exit-0 + key-presence (a non-skip success also exits 0).

### IC-02 — Port seam & dependency injection (stratified)
- **Purpose**: Define the capability boundary the cores/orchestrators depend on, shaped so Wave 2 *reuses* it rather than re-cutting it.
- **Relevant requirements**: FR-003, FR-009, C-002, C-005.
- **Affected surfaces**: new `tasks_ports.py`; call sites in `tasks.py`.
- **Sequencing/depends-on**: IC-01 (freeze first); **predecessor #2072 has landed** (allowlist composite-keyed) → not blocked. Also delivers the **FR-010 dir-equivalence proof artifact** (per-kind coord-fixture equivalence) here, before any read fold.
- **Risks**: (1) the coord WRITE port is **two capabilities over two disjoint seams** — `commit_status` (over the transactional emitter, `GuardCapability`) + `commit_artifact` (over `commit_for_mission`, `MissionArtifactKind`, event-less) — NOT a fused `commit()`; the Wave-2 consumers use disjoint halves (`implement`=status-only, `acceptance`=artifact-only writer, `move_task`=both), so a fused method is re-cut in Wave 2 (the C-006 failure). `GitOps`+`Render` are mission-local (#2173 DROPs). (2) inject at the `_do_<cmd>(*, ports=None)` **orchestrator boundary**, never the Typer `@app.command` (Protocol-param collision). (3) keep the `_canonicalize_primary_read_handle` fold **co-located** with the primitive in the adapter (intra-function gate). (4) rename result types off `CommitResult` (collides with `git/commit_helpers.py:424`).

### IC-03 — Pure decision & aggregation cores
- **Purpose**: Extract the logic that drives the change-ripple into pure, independently-testable functions.
- **Relevant requirements**: FR-002, FR-004, FR-005, FR-006.
- **Affected surfaces**: new `tasks_transition_core.py` (move_task decision), `tasks_mapping_core.py`, `tasks_status_view.py`.
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: `move_task`'s decision is a nested state machine (arbiter-override, FR-008a planning arm, force paths, review-currency, the coord skip arm) — extract it **reproducing exact behavior**, NOT unifying with the other commands (that's #2300, deferred). Each core's branch set is enumerated from the IC-01 golden harness, gated by `--cov-branch` on the core module (NFR-002). **Anti-shadow-code**: wiring a core into its command **deletes** the old inline decision block (does not add a discarded call) and ships a fake-core sentinel test proving the return value drives observable behavior — "grep-for-callers" is insufficient.

### IC-04 — Command-body thinning
- **Purpose**: Reduce the fat bodies to thin orchestrators over cores + ports. Split across **WP06** (move_task), **WP07** (core-backed: map_requirements + status), **WP08** (coreless: mark_status + finalize_tasks) — the squad flagged a single 4-body WP as overloaded.
- **Relevant requirements**: FR-007, NFR-004.
- **Affected surfaces**: the fat command bodies in `tasks.py` (owned authoritatively by WP09; WP06-WP08 edit under documented leeway).
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: `mark_status` and `finalize_tasks` carry **no new core** — they thin via ports + the existing `tasks_finalize_validation`/parsing seams. Borrowing move_task's core would be the deferred unification (#2300) — guarded **structurally** by a WP08 non-import AST gate (`tasks_transition_core` NOT reachable from those bodies), not behavior alone. Each body ≤150 LOC; glue helpers ≤150 LOC/CC≤15, enforced by a dedicated LOC gate (ruff CC≤15 does not bound LOC).

### IC-05 — Coord read-authority unification (fold)
- **Purpose**: Fix the latent pre-3.0-layout read split-brain (DIRECTIVE_044).
- **Relevant requirements**: FR-010, C-001.
- **Affected surfaces**: resolver calls at `move_task:1138` (WP06), `finalize_tasks:2373` + `list_dependents:3568` (WP08) — migrate kind-blind `resolve_feature_dir_for_mission` reads → kind-aware `resolve_planning_read_dir` with a **pinned `MissionArtifactKind` per site**.
- **Sequencing/depends-on**: the **dir-equivalence proof artifact is a WP02 deliverable** (IC-02); the rewire sites ride with IC-04.
- **Risks**: the two resolvers **differ by construction** on coord topology (`-coord` husk vs primary read dir) — a wrong `kind` breaks byte-identity on the WP01 coord fixture. This is the single most likely parity break; the WP02 proof (not a WP06 runtime "stop if it shifts") is the guard.

### IC-06 — Render seam, shim finalization & census honesty (WP09)
- **Purpose**: Isolate output, reduce the file toward a thin surface (≤1400 LOC), and honestly manage the arch-ratchet census.
- **Relevant requirements**: FR-008, FR-011, NFR-004, NFR-005.
- **Affected surfaces**: the `Render` dual-arm seam (human + **13** `json.dumps`, AST-gated to 0); `tasks.py` → thin surface (owns it); `tests/architectural/resolution_gate_allowlist.yaml` + `test_resolution_authority_gates.py` floors + the new LOC gate.
- **Sequencing/depends-on**: IC-04 (bodies must be thin first — that's what reclassifies WRITE→READ).
- **Risks**: the census is **at floor** (write census 12/floor 12); body-thinning reclassifies WRITE→READ → sites **drain** and floors **lower shrink-only**. Because the floor gate is a lower-bound owned by this same WP, over-lowering is self-attestable — so ship **(a)** a 1:1 enumerated cross-base drain artifact, **(b)** reviewer (not author) sign-off, **(c)** a **margin gate**. Also fix stale `coord_authority_baseline: 13`→12. WP09 + the mission-merge run the full `tests/architectural/` cross-base sweep (`post-merge-arch-gate-adjudication`).

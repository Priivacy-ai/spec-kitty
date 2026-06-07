# Implementation Plan: WP Lane State Machine Canonicalization

**Branch**: `mission/wp-lane-state-machine-fsm` | **Date**: 2026-06-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/wp-lane-state-machine-fsm-01KTGZAZ/spec.md`

## Summary

Fully encapsulate WP lane behavior as a State-pattern Finite State Machine
(`status/wp_state.py`) that is the *single* authority for lane reads, transition
edges, **guards, and force-override**. The baseline (branch
`fix/status-genesis-lane-bootstrap`, merged here) already added `Lane.GENESIS` (a
non-display pre-finalize lane), derived `ALLOWED_TRANSITIONS` from the state
objects, added the `current_lane`/`may_transition_to`/`transition_to` interface,
and fixed the finalize event-log clobber (#1589). This mission **completes the
wiring** and **resolves every adversarial-review finding** (research/):

- Move the guard matrix + force-override INTO the `WPState` objects;
  `validate_transition` becomes a thin delegator (Decision DM-01KTH03G).
- Make read/write layers agree on genesis (readers default to `GENESIS`); fail an
  unseeded `implement` fast with an actionable message before any workspace alloc.
- Enforce the genesis non-display invariant everywhere (summary, discovery,
  `by_lane`, frontmatter validation).
- Represent the genesis seed faithfully on the SaaS boundary by **adding `genesis`
  to `spec_kitty_events.Lane`** via the owning-package workflow (Decision DM-01KTH03H).
- Leanness/hygiene: one shared seed fixture, lock in the FSM API with real callers,
  `validate` accepts genesis as `from_lane`-only, fix stale docstrings.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (CLI); pytest, pytestarch, mypy, ruff (quality); `spec_kitty_events` (external PyPI contract — to be bumped to add `genesis` to its `Lane` enum), `spec_kitty_tracker` (consumed via public imports only)
**Storage**: Filesystem only — `status.events.jsonl` (append-only event log, sole authority) + materialized `status.json`; coordination-branch worktree topology; no database
**Testing**: pytest (unit / integration / architectural); per-charter targeted suites (`tests/status/`, `tests/specify_cli/status/`, `tests/specify_cli/coordination/`, `tests/sync/`, `tests/lanes/`, `tests/integration/`); the existing transition + guard suites are the **behavior-preservation envelope**; full suite reserved for cross-cutting/RC validation
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: single (Python CLI library under `src/`)
**Performance Goals**: no runtime regression; `ALLOWED_TRANSITIONS` stays a module-load-time derived constant; `mypy`/`ruff` clean
**Constraints**: behavior-preserving for the 9 pre-existing lanes (NFR-001); `genesis` stays non-display (C-002); FSM is the single transition+guard+force source (NFR-002); `spec_kitty_events` change goes through the owning-package workflow with no committed path/editable overrides (C-004, Shared Package Boundary charter); `ruff` + `mypy` clean, no disabled checks (NFR-004)
**Scale/Scope**: ~15 `status/` modules; the guard/force migration (`transitions.py` → `wp_state.py`); ~25 `.lane` read sites + readers in `coordination/`, `runtime/next/`, `agent_utils/`; `sync/emitter.py` + the external `spec_kitty_events` package; ~30 test files; 5 adversarial-review artefacts driving FR-007..FR-020

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (charter context: compact mode)

- **Shared Package Boundary (binding)** — `spec_kitty_events` is a true external dependency. Adding `genesis` to its `Lane` MUST follow the owning-package workflow: change the package repo first, publish a versioned artifact with compatibility notes, update CLI dependency constraints/lockfile, run consumer/compatibility tests. No committed path/editable/branch overrides. **PASS (planned)** via C-004 / IC-04.
- **ATDD-First (binding, C-011)** — the existing transition/guard suites pin the behavior envelope before the guard/force migration; new tests pin the delegation, read/write parity, the non-display invariant, and the SaaS genesis payload, authored failing-first. **PASS (planned)**.
- **Test & Typecheck Quality Gate** — `ruff` + `mypy` clean on touched modules; no disabled checks (justified narrow suppressions only, with rationale). **PASS (planned)** NFR-004.
- **Burn-down Policy (C-004 charter)** — the change *removes* the dual-source transition matrix and the half-wired API; no net new untested debt. **PASS (planned)**.
- **Terminology Canon** — `genesis` is a new canonical (non-display) lane term; Mission vocabulary preserved. **PASS (planned)**.
- **`__all__` Convention** — `status/`/`kernel/` modules unaffected beyond existing declarations. **PASS**.

No Charter Check violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/wp-lane-state-machine-fsm-01KTGZAZ/
├── plan.md              # This file
├── research.md          # Phase 0 output (decisions + review consolidation)
├── data-model.md        # Phase 1 output (FSM state model + invariants)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (FSM delegation + genesis invariant contracts)
├── research/            # Adversarial review artefacts (review-*.md + synthesis) — FR source
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/status/
├── wp_state.py            # THE FSM authority: 10 StateObjects own edges + guards + force;
│                          #   current_lane / may_transition_to / transition_to is the runtime path
├── transitions.py         # validate_transition → thin delegator to wp_state; ALLOWED_TRANSITIONS derived
├── transition_context.py  # GuardContext/TransitionContext consumed by the states
├── emit.py                # _derive_from_lane (genesis); pipeline routes through the FSM
├── validate.py            # genesis accepted as from_lane only
├── reducer.py / views.py  # summary excludes genesis (non-display)
├── progress.py            # genesis weight 0
└── bootstrap.py           # explicit genesis→planned seed (drop redundant force)

src/specify_cli/coordination/status_service.py      # wp_lane_actor_from_events → GENESIS default
src/specify_cli/coordination/status_transition.py   # read fallback → GENESIS
src/runtime/next/discovery.py, decision.py          # discovery defaults → GENESIS (hide unseeded)
src/specify_cli/agent_utils/status.py               # reader default → GENESIS
src/specify_cli/status/work_package_lifecycle.py    # genesis branch → actionable rejection
src/specify_cli/cli/commands/agent/implement.py     # reject before workspace allocation
src/specify_cli/cli/commands/agent/tasks.py         # by_lane excludes genesis
src/specify_cli/sync/emitter.py                     # _PAYLOAD_RULES single-sourced (incl genesis)
<external> spec_kitty_events.Lane                    # add `genesis` (owning-package workflow)

tests/
├── status/conftest.py                  # ONE shared seed_to_planned fixture (replaces 12 copies)
├── status/, specify_cli/status/        # FSM delegation, parity, non-display, validate
├── specify_cli/coordination/, sync/    # reader parity, SaaS genesis payload
└── specify_cli/cli/commands/agent/     # e2e finalize clobber regression
```

**Structure Decision**: Single Python project. The change is concentrated in
`src/specify_cli/status/` (the FSM becomes the authority and `transitions.py`
delegates), the lane readers (`coordination/`, `runtime/next/`, `agent_utils/`),
`sync/emitter.py`, and the external `spec_kitty_events` package. No new top-level
package; this is an encapsulation/wiring refactor of an existing surface.

## Complexity Tracking

*No Charter Check violations.* The State-pattern FSM is the explicitly-mandated
design (operator directive + refactoring.guru/state); it reduces complexity by
collapsing the dual-source transition matrix and the half-wired API into one
owner, in exchange for moving the guard/force logic into the state objects.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Full FSM wiring: guards + force into the State objects

- **Purpose**: Make the `WPState` FSM the single authority for edges, guards, and force-override; `validate_transition` becomes a thin delegator to `wp_state_for(from).transition_to(to, ctx)`. Every lane is a full StateObject like `GenesisState`.
- **Relevant requirements**: FR-001, FR-002, FR-002b, FR-003, FR-012; NFR-001, NFR-002.
- **Affected surfaces**: `status/wp_state.py` (own guards+force per state), `status/transitions.py` (delegate; keep `_GUARDED_TRANSITIONS`→state moves), `status/transition_context.py`, `status/emit.py` (transition path).
- **Sequencing/depends-on**: none (foundational).
- **Risks**: the guard matrix (actor / subtasks-complete / review-result / done-evidence / force) is intricate; behavior MUST be preserved — the existing transition+guard suites are the envelope; migrate guard-by-guard keeping green; force-exit of terminal states must reach parity with the old `validate_transition` force path.

### IC-02 — Read/write parity for genesis + actionable unseeded-implement rejection

- **Purpose**: Every lane reader reports an unseeded WP as `GENESIS` (matching the writer); implementing an unfinalized WP fails fast with a "run finalize-tasks" message **before** workspace allocation (no dangling worktree).
- **Relevant requirements**: FR-008, FR-009; US4 (review F2).
- **Affected surfaces**: `coordination/status_service.py`, `coordination/status_transition.py`, `runtime/next/discovery.py`, `runtime/next/decision.py`, `agent_utils/status.py`, `status/work_package_lifecycle.py`, `cli/commands/agent/implement.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: reject before allocation (ordering); do not regress the happy path where finalize seeds first.

### IC-03 — Genesis non-display invariant, enforced everywhere

- **Purpose**: `genesis` never surfaces as a column/summary key/discovery candidate/authorable lane; a genesis WP is never silently dropped from a table.
- **Relevant requirements**: FR-007, FR-013, FR-014; US2/US7 (review F4 + paula-2/3 + debbie inert leaks).
- **Affected surfaces**: `status/reducer.py` (summary excludes genesis), `status/views.py`, `cli/commands/agent/tasks.py` (`by_lane`), `task_metadata_validation.py`, snapshot fixtures.
- **Sequencing/depends-on**: IC-01.
- **Risks**: fixture churn — assert reducer real output, not a hand-built fixture.

### IC-04 — SaaS genesis fidelity via `spec_kitty_events` enum bump

- **Purpose**: The `genesis → planned` seed fans out to SaaS as a real transition (not dropped); add `genesis` to `spec_kitty_events.Lane`; single-source the local `_PAYLOAD_RULES` lane set.
- **Relevant requirements**: FR-010, FR-011; C-004; NFR-005; US5 (review F1 / alphonso-3).
- **Affected surfaces**: **external** `spec_kitty_events` package (`Lane` enum, owning-package workflow), CLI dependency constraints/lockfile, `sync/emitter.py` (`_PAYLOAD_RULES` derived), `status/emit.py` (`_saas_fan_out`).
- **Sequencing/depends-on**: IC-01 (local genesis lane exists).
- **Risks**: external release coordination per the Shared Package Boundary charter (change package → publish → update constraints → consumer tests); no committed path/editable overrides; until released, guard with compatibility fixtures / a feature gate.

### IC-05 — Finalize clobber hardening + end-to-end regression

- **Purpose**: Lock in the finalize clobber fix (baseline) with an end-to-end test that a coord-topology `finalize-tasks` preserves the seeded coordination event log.
- **Relevant requirements**: FR-006, FR-019; US3.
- **Affected surfaces**: `cli/commands/agent/mission.py` (done), `tests/specify_cli/cli/commands/agent/`.
- **Sequencing/depends-on**: none.
- **Risks**: e2e realism — exercise a real coord worktree, not a mock.

### IC-06 — Leanness & hygiene

- **Purpose**: Remove avoidable complexity surfaced by the leanness lens — one shared seed fixture, lock in the FSM API with real callers, `validate` genesis `from_lane`-only, fix stale docstrings, drop redundant bootstrap `force`.
- **Relevant requirements**: FR-015, FR-016, FR-017, FR-018, FR-020; NFR-003; US8 (review randy + paula-4/5).
- **Affected surfaces**: `tests/status/conftest.py` (+ `tests/conftest.py`), the ~12 `_seed_planned` sites, `status/validate.py`, `status/emit.py` + module docstrings, `status/bootstrap.py`, `tests/utils.py`, the tautological equivalence/count test annotation.
- **Sequencing/depends-on**: IC-01..IC-03 (caller migration locks in the FSM API).
- **Risks**: low.

## Phases

- **Phase 0 — Research** (`research.md`): consolidate the two resolved decisions (DM-01KTH03G full guard/force ownership; DM-01KTH03H `spec_kitty_events` enum bump) and the adversarial-review findings (already captured in `research/`); pin the guard/force migration order and the external-release approach.
- **Phase 1 — Design** (`data-model.md`, `contracts/`, `quickstart.md`): the 10-state FSM model (edges + guards + force per state), the genesis non-display invariant table, the `validate_transition` delegation contract, the `spec_kitty_events.Lane` contract delta, and a quickstart for exercising the FSM.
- **Phase 2 — Tasks** (`/spec-kitty.tasks`): translate IC-01..IC-06 into work packages with Randy-Reducer / Paula-Patterns ICs. **Not produced by this command.**

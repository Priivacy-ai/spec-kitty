---
description: "Work package task list — WP Lane State Machine Canonicalization"
---

# Work Packages: WP Lane State Machine Canonicalization

**Inputs**: `spec.md`, `plan.md`, `data-model.md`, `contracts/fsm-and-genesis-contracts.md`, `research.md`, and the five adversarial-review artefacts in `research/`.
**Baseline**: the FSM + genesis + clobber fix is already merged here (branch `fix/status-genesis-lane-bootstrap`); these WPs **complete the wiring** and **resolve every review finding**.

**Tests**: explicit and load-bearing — the existing transition/guard suites are the **behavior-preservation envelope** (NFR-001); new tests pin delegation, parity, the non-display invariant, and the SaaS payload.

**Persona ICs**: every shaping WP carries **Randy-Reducer** (leanness, no derived-constant tech debt) and **Paula-Patterns** (single ownership) contracts (C-005).

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** = parallel-safe (different files/components).

## Path Conventions

- Single Python project: `src/specify_cli/status/` is the FSM home; readers in `coordination/`, `runtime/next/`, `agent_utils/`; SaaS in `sync/`; external `spec_kitty_events` (owning-package workflow).

---

## Work Package WP01: Full FSM ownership — edges + guards + force in WPState; no derived authority (Priority: P1) 🎯 FOUNDATION

**Goal**: Make the `WPState` objects the single owner of the edge graph AND the act of transitioning (guards + force). `validate_transition` becomes a thin delegator; `ALLOWED_TRANSITIONS` is no longer a consumed authority. Behavior-preserving for the 9 lanes.
**Independent Test**: Full historical transition+guard+force matrix passes through `wp_state_for(from).transition_to(to, ctx)`; an architectural test proves no production edge-gate consults `ALLOWED_TRANSITIONS`.
**Prompt**: `/tasks/WP01-full-fsm-ownership.md`
**Requirement Refs**: FR-001, FR-021, FR-002, FR-022, FR-003, FR-012, FR-015, NFR-001, NFR-002, NFR-004

### Included Subtasks

> **ATDD (C-011):** author/extend the behavior-preservation parity suite (T007) **RED-first** against the pre-refactor behavior, then migrate keeping it green.

- [x] T001 Move each lane's guard conditions into its `WPState.can_transition_to` (actor, workspace_context, subtasks_complete_or_force, reviewer_approval, ReviewResult-required, done-evidence) (WP01)
- [x] T002 Move force-override into `WPState.transition_to` — terminal `done`/`canceled` force-exit reaches parity with the old `validate_transition` force branch (WP01)
- [x] T003 Rewrite `validate_transition(from,to,ctx)` as a thin delegator returning `(ok, error_message)` from the State object (WP01)
- [x] T004 Eliminate `ALLOWED_TRANSITIONS` as an authority: migrate `validate.py::validate_canonical_event` (`(from,to) in ALLOWED_TRANSITIONS`) to query the FSM; remove or relegate the constant + `__init__` export to a non-authoritative derived projection (WP01)
- [x] T005 `validate.py`: accept `genesis` as a `from_lane` only — flag `to_lane=genesis` as non-canonical (FR-015) (WP01)
- [x] T006 Architectural test: no production module consults `ALLOWED_TRANSITIONS`/a derived edge set as a gate; the FSM is the sole edge+transition authority (WP01)
- [x] T007 Behavior-preservation parity suite over the full historical transition+guard+force matrix; refresh `wp_state.py`/`transitions.py` docstrings (WP01)

### Dependencies
- None (foundational — gates WP02, WP03, WP04, WP06).

### Risks & Mitigations
- The guard matrix is intricate; migrate guard-by-guard keeping the envelope green. An overlooked `(from,to) in ALLOWED_TRANSITIONS` re-introduces the split-brain — the audit must be exhaustive (`grep -rn ALLOWED_TRANSITIONS src/`).

---

## Work Package WP02: Read/write parity for genesis + actionable unseeded-implement rejection (Priority: P1)

**Goal**: Every lane reader reports an unseeded WP as `GENESIS`; implementing an unfinalized WP fails fast with a "run finalize-tasks" message **before** any workspace is allocated.
**Independent Test**: each reader returns `GENESIS` for an unseeded WP; `implement` on an unseeded WP exits with the actionable message and leaves no `.worktrees/` entry.
**Prompt**: `/tasks/WP02-readwrite-parity-genesis.md`
**Requirement Refs**: FR-008, FR-009

### Included Subtasks

- [ ] T008 `coordination/status_service.py::wp_lane_actor_from_events` → default unseeded WP to `Lane.GENESIS` (WP02)
- [ ] T009 `coordination/status_transition.py::read_current_wp_state_transactional` fallback → `Lane.GENESIS` (WP02)
- [ ] T010 [P] Runtime discovery defaults → `Lane.GENESIS`: `runtime/next/discovery.py`, `runtime/next/decision.py`, `agent_utils/status.py` (so unseeded WPs are filtered from claimable lists) (WP02)
- [ ] T011 `status/work_package_lifecycle.py::start_implementation_status` → explicit `genesis` branch raising `WorkPackageStartRejected("WP … not finalized; run finalize-tasks")` (WP02)
- [ ] T012 `cli/commands/agent/implement.py` → perform the genesis rejection BEFORE workspace/worktree allocation (no dangling worktree) (WP02)
- [ ] T013 Tests: reader parity for unseeded WPs; unseeded-implement actionable error + no leftover worktree (WP02)

### Dependencies
- Depends on WP01 (genesis as a first-class FSM state).

### Risks & Mitigations
- Ordering: reject before allocation. Do not regress the happy path (finalize seeds first → WP is `planned`).

---

## Work Package WP03: Genesis non-display invariant, enforced everywhere (Priority: P2)

**Goal**: `genesis` never surfaces as a column/summary key/discovery candidate/authorable lane; a genesis WP is never silently dropped.
**Independent Test**: reducer real output (not a fixture) has no genesis key; no display/summary/discovery surface includes genesis.
**Prompt**: `/tasks/WP03-genesis-non-display.md`
**Requirement Refs**: FR-007, FR-013, FR-014, NFR-002

### Included Subtasks

- [ ] T014 `status/reducer.py` summary → exclude `genesis` (`{l.value: 0 for l in Lane if l is not Lane.GENESIS}`); update `views.py` (WP03)
- [ ] T015 `cli/commands/agent/tasks.py` `by_lane` → exclude the genesis bucket; never drop a genesis WP from the table (WP03)
- [ ] T016 `task_metadata_validation.py` → do not offer `genesis` as an authorable frontmatter lane (WP03)
- [ ] T017 [P] Fix the stale "7 lanes"/"9-lane" comments in `reducer.py`/`views.py`/`progress.py` (WP03)
- [ ] T018 Tests: assert the reducer's REAL summary output excludes genesis; assert no genesis WP is dropped from the board table (WP03)

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- Fixture churn — assert reducer output, not a hand-built fixture (the test_summary_has_all_lane_keys trap).

---

## Work Package WP04: SaaS genesis fidelity via spec_kitty_events enum bump (Priority: P2)

**Goal**: The `genesis → planned` seed fans out to SaaS as a real transition (not dropped). Add `genesis` to `spec_kitty_events.Lane` via the owning-package workflow; single-source the local `_PAYLOAD_RULES` lane set.
**Independent Test**: a genesis seed yields a contract-valid SaaS payload; a compatibility fixture covers old and new `spec_kitty_events`.
**Prompt**: `/tasks/WP04-saas-genesis-fidelity.md`
**Requirement Refs**: FR-010, FR-011, NFR-005

### Included Subtasks

- [ ] T019 (External) Add `genesis` to `spec_kitty_events.Lane` via the owning-package workflow (change package repo → publish versioned artifact → compatibility notes) (WP04)
- [ ] T020 Update CLI dependency constraints/lockfile to the genesis-aware `spec_kitty_events`; no committed path/editable overrides (WP04)
- [ ] T021 `sync/emitter.py` `_PAYLOAD_RULES["WPStatusChanged"]` lane set → derive from the canonical source (incl. genesis), not a hardcoded 9-lane list (WP04)
- [ ] T022 `status/emit.py::_saas_fan_out` → emit the genesis seed faithfully (no swallowed `ValidationError`); add a compatibility gate for the pre-release window; fix the emit pipeline "(or 'planned')" docstring (WP04)
- [ ] T023 Tests: genesis seed → contract-valid SaaS payload; consumer/compatibility fixture for old vs new `spec_kitty_events` (WP04)

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- External release coordination (Shared Package Boundary charter). Until the genesis-aware `spec_kitty_events` is released, the CLI side must degrade gracefully (capability/version gate). No path/editable overrides.

---

## Work Package WP05: Finalize clobber hardening + end-to-end regression (Priority: P2)

**Goal**: Lock in the finalize clobber fix (baseline) with an end-to-end test proving a coord-topology `finalize-tasks` preserves the seeded coordination event log.
**Independent Test**: after a coord `finalize-tasks`, the committed coord event log retains the bootstrap lane events; non-coord missions still commit their status files.
**Prompt**: `/tasks/WP05-finalize-clobber-e2e.md`
**Requirement Refs**: FR-006, FR-019

### Included Subtasks

- [ ] T024 End-to-end test: real coord-topology `finalize-tasks` retains the bootstrap lane events on the coordination branch (WP05)
- [ ] T025 [P] Negative test: non-coordination mission still commits its primary-checkout `status.events.jsonl`/`status.json` (no regression) (WP05)
- [ ] T026 Edge test: coord re-finalize where only status files changed does not error with an empty-changeset commit (WP05)

### Dependencies
- None (baseline clobber fix already merged; this is the regression net).

### Risks & Mitigations
- E2E realism — exercise a real coord worktree, not a mock.

---

## Work Package WP06: Leanness & hygiene — shared seed fixture, lock-in FSM API, no debt (Priority: P3)

**Goal**: Remove avoidable complexity surfaced by the leanness lens — one shared seed fixture (not 12 copies), the FSM API locked in by real callers, drop the redundant bootstrap `force`, fix remaining stale docstrings, annotate the tautological count test.
**Independent Test**: ≤2 shared `seed_to_planned` fixtures; `current_lane`/`may_transition_to`/`transition_to` each have ≥1 real caller; bootstrap seed records no redundant `force`.
**Prompt**: `/tasks/WP06-leanness-hygiene.md`
**Requirement Refs**: FR-016, FR-017, FR-018, FR-020, NFR-003

### Included Subtasks

- [ ] T027 Consolidate the 12 `_seed_planned` helpers into ≤2 shared fixtures (`tests/status/conftest.py` + `tests/conftest.py`); remove the copies (WP06)
- [ ] T028 Fix `tests/utils.py::_seed_canonical_wp_state` stale `PLANNED` default (WP06)
- [ ] T029 Lock in the FSM API (FR-017): migrate select real callers to `current_lane`/`may_transition_to`/`transition_to` so the operator-mandated interface is load-bearing, not dead (WP06)
- [ ] T030 `status/bootstrap.py`: drop the redundant `force=True` on the guard-free `genesis→planned` seed (or document why) (WP06)
- [ ] T031 Annotate the now-tautological equivalence/`test_transition_count` test (WP06)

### Dependencies
- Depends on WP01, WP02, WP03, WP04 (lock-in + hygiene after the API is wired and callers migrated).

### Risks & Mitigations
- Cross-cutting test edits (`scope: codebase-wide`) — coordinate; run after the others.

---

## Dependency & Execution Summary

- **Sequence**: WP01 (foundation) → WP02 / WP03 / WP04 (parallel, all depend on WP01) ; WP05 independent (run anytime) ; WP06 last (depends on WP01–WP04).
- **MVP / gate scope**: WP01 establishes the single-owner FSM; WP02 makes the loop usable (read/write parity). WP01+WP02 are the critical path.
- **Parallelization**: after WP01, WP02/WP03/WP04 run in parallel; WP05 anytime.

## Requirements Coverage Summary

| Requirement | Work Package(s) |
|-------------|-----------------|
| FR-001, FR-021, FR-002, FR-022, FR-003, FR-012, FR-015 | WP01 |
| FR-008, FR-009 | WP02 |
| FR-007, FR-013, FR-014 | WP03 |
| FR-010, FR-011 | WP04 |
| FR-006, FR-019 | WP05 |
| FR-016, FR-017, FR-018, FR-020 | WP06 |
| NFR-001, NFR-002, NFR-004 | WP01 |
| NFR-003 | WP06 |
| NFR-005 | WP04 |
| C-001, C-002, C-003 | WP01, WP03 |
| C-004 | WP04 |
| C-005 | WP01, WP02, WP03, WP04, WP06 |

## Subtask Index (Reference)

| Subtask | Summary | WP | Parallel? |
|---------|---------|-----|-----------|
| T001–T007 | Full FSM ownership (guards+force in states; delegator; no derived authority) | WP01 | Partial |
| T008–T013 | Read/write genesis parity + actionable unseeded-implement rejection | WP02 | Partial |
| T014–T018 | Genesis non-display invariant everywhere | WP03 | Partial |
| T019–T023 | SaaS genesis fidelity (spec_kitty_events enum bump) | WP04 | No |
| T024–T026 | Finalize clobber end-to-end regression | WP05 | Partial |
| T027–T031 | Leanness & hygiene (shared fixture, lock-in API, no debt) | WP06 | Partial |

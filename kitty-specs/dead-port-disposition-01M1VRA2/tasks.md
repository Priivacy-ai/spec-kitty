# Work Packages: Dead-Port Disposition: RuntimeEventEmitter Seam Consolidation

**Inputs**: Design documents from `kitty-specs/dead-port-disposition-01M1VRA2/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/emitter-seam.md, contracts/decision-log-flush.md, quickstart.md
**Governing decision**: ADR 2026-09-06-2 (Accepted, Option 1)

**Tests**: Required. NFR-001 mandates red-first regression tests for both flush-target fixes; NFR-002 requires the existing bridge suites to stay green at every WP boundary.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package leaves the full test suite green when it lands.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`. This file is the high-level checklist; implementation detail lives in the prompts.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Subtasks are **reference rows**, not checkboxes: record completion with `spec-kitty agent tasks mark-status <Txxx> --status done`. The reduced event-log snapshot is the sole subtask-completion authority.

## Path Conventions

- Single project: `src/runtime/next/`, `src/specify_cli/events/`, `tests/`.
- All paths below are repository-root relative.

---

## Work Package WP01: Seam foundation — factory, registry, `NullEmitter.for_mission` (Priority: P0)

**Goal**: Give the canonical Protocol/`NullEmitter` module the two capabilities the bridge needs (mission-aware construction and snapshot seeding) plus a named factory with a registration hook, so the concrete duplicate class becomes deletable.
**Independent Test**: `pytest tests/next/test_internal_runtime_coverage.py` green, including new factory/registry/`for_mission` cases (contract rules S1–S6); `ruff check` and `mypy` clean on `events.py`; no other module changed.
**Prompt**: `tasks/WP01-seam-foundation.md`
**Requirement Refs**: FR-002, FR-003, FR-004, FR-009, NFR-005, NFR-006, C-005
**Estimated prompt size**: ~380 lines

### Included Subtasks

T001 Extend `NullEmitter` with mission fields and the `for_mission` classmethod in `src/runtime/next/_internal_runtime/events.py` (WP01)
T002 Add `NullEmitter.seed_from_snapshot` no-op (WP01)
T003 Add `runtime_emitter_for_mission` factory with call-time `SPEC_KITTY_SYNC_MINIMAL_IMPORT` gate, plus `register_runtime_emitter_factory` / `reset_runtime_emitter_factory` (WP01)
T004 [P] Extend `__all__` in `events.py` and the `_internal_runtime/emitter.py` re-export shim; update `test_emitter_module_re_exports` (WP01)
T005 Add factory/registry/`for_mission` unit tests to `tests/next/test_internal_runtime_coverage.py` (WP01)
T006 [P] Write the seam docstring naming `status/adapters.py` as the existing zeitgeist seam and the registry as the E3 registration point (WP01)

### Implementation Notes

- Keep the Protocol at the eight `emit_*` methods (research.md R-2). `for_mission` and `seed_from_snapshot` live on `NullEmitter` only.
- `resolve_mission_identity` comes from `specify_cli.mission_metadata`, already imported by `_internal_runtime/planner.py:46`; no new layer edge.
- The env gate is read at call time so tests can toggle it with `monkeypatch.setenv`.

### Parallel Opportunities

- T004 and T006 are independent of T001–T003 once the names are agreed; T005 depends on T001–T003.

### Dependencies

- None (starting package). Runs in parallel with WP02.

### Risks & Mitigations

- `test_emitter_module_re_exports` asserts the exact `__all__` set → update it in the same change (T004).
- A bare `NullEmitter()` is constructed in many tests → the new fields must default (`""`, `""`, `None`) so the existing constructor signature is unchanged.

---

## Work Package WP02: Flush-target fixes, red-first (Priority: P1) 🎯 MVP

**Goal**: Make decision requests raised on a strict-retrospective-policy `decision_required` advance and on composition dispatch reach the coordination-branch decision log, with regression tests that are demonstrably red before the fix and green after.
**Independent Test**: `pytest tests/runtime/test_bridge_decision_log_flush.py` — tests F1/F2 fail on the pre-fix tree and pass after; F3/F4 pass; `pytest tests/specify_cli/events/` green; `pytest tests/runtime/test_bridge_retrospective.py tests/runtime/test_bridge_engine.py` unchanged and green.
**Prompt**: `tasks/WP02-flush-target-fixes.md`
**Requirement Refs**: FR-005, FR-006, FR-007, FR-008, NFR-001, NFR-004, C-004
**Estimated prompt size**: ~520 lines

### Included Subtasks

T007 Build the test fixtures: strict retrospective policy stub, temp mission with coord `meta.json`, real `DecisionGitLog` over `NullEmitter`, and a `DecideNextContext` builder in `tests/runtime/test_bridge_decision_log_flush.py` (WP02)
T008 Write F1 `test_strict_policy_decision_required_reaches_decision_log`; run it and record the red result (WP02)
T009 Write F2 `test_composition_dispatch_decision_required_reaches_decision_log`; run it and record the red result (WP02)
T010 Fix one: `runtime_bridge.py:2187` flushes into `ctx.emitter_for_engine`; update the adjacent comment (WP02)
T011 Fix two: `runtime_bridge.py:1976` passes `ctx.emitter_for_engine`; add `DecisionGitLog.seed_from_snapshot` pass-through in `src/specify_cli/events/decision_log.py` with a unit test in `tests/specify_cli/events/test_decision_log.py` (WP02)
T012 Write F3 `test_strict_policy_refused_terminal_gate_writes_nothing` and F4 `test_gated_flush_does_not_duplicate`; confirm F1–F4 green (WP02)
T013 Record red→green evidence (commands + counts) in the WP Activity Log (WP02)

### Implementation Notes

- The red-first fixture is a `decision_required` advance, never a terminal one (research.md R-3): the decision log persists only `DecisionInputRequested`/`Answered`.
- Strict policy: `enabled=True, timing="before_completion", failure_policy="block"`; monkeypatch `_resolve_retrospective_policy_for_runtime` on the bridge module.
- Drive `_dn_decision_materialize(ctx)` for F1/F3/F4 and `_dn_composition_dispatch(ctx)` for F2; stub `runtime_next_step` / the composition helpers so the engine emits through whatever emitter it is handed.

### Parallel Opportunities

- Independent of WP01; runs in its own lane. T008/T009 can be written together; T010/T011 are separate one-line bridge edits.

### Dependencies

- None.

### Risks & Mitigations

- `_advance_run_state_after_composition` seeds the emitter it receives (`runtime_bridge_engine.py:344`) → `DecisionGitLog` must gain `seed_from_snapshot` in the same WP (T011) or F2 raises `AttributeError`.
- Double-emit fear → F4 counts exactly one entry; the buffer is one-shot and the engine wrote only into the buffer on the gated path.

---

## Work Package WP03: Bridge rewiring and test-site migration (Priority: P1)

**Goal**: Bind the bridge to the factory instead of the concrete class, retype the engine adapter against the Protocol, and migrate all fifteen test patch sites so the suite stays green.
**Independent Test**: `grep -n "event_emitter" src/runtime/next/runtime_bridge.py src/runtime/next/runtime_bridge_engine.py` → no hits; `pytest tests/runtime/ tests/next/ tests/specify_cli/next/` green.
**Prompt**: `tasks/WP03-bridge-rewiring-and-test-migration.md`
**Requirement Refs**: FR-002, FR-003, NFR-002, NFR-006
**Estimated prompt size**: ~470 lines

### Included Subtasks

T014 Swap the bridge import and the two construction sites (`runtime_bridge.py:195`, `:1552`, `:2739`) to `runtime_emitter_for_mission` — declared out-of-map edit, three lines, rationale in the prompt (WP03)
T015 Retype `runtime_bridge_engine.py:80` `TYPE_CHECKING` import against `_internal_runtime.events.RuntimeEventEmitter` (WP03)
T016 Migrate `tests/runtime/_bridge_oracle.py:471-481` spy to wrap the factory name (WP03)
T017 [P] Migrate the five sites in `tests/runtime/test_bridge_decide_next.py` (`:242`, `:282`, `:328`, `:369`, `:416`) (WP03)
T018 [P] Migrate the four `patch.object(rb, "RuntimeEventEmitter")` sites in `tests/next/test_runtime_bridge_blocked_paths.py` (`:205`, `:260`, `:311`, `:362`) (WP03)
T019 [P] Migrate the four sites in `tests/next/test_runtime_bridge_unit.py` (`:245`, `:610`, `:858`, `:2159`) and the one in `tests/specify_cli/next/test_runtime_bridge_composition.py:63` (WP03)
T020 Run the full bridge blast radius and confirm zero `feature*` identifiers in added lines (WP03)

### Implementation Notes

- Every migration has the same shape: `monkeypatch.setattr(rb, "runtime_emitter_for_mission", lambda **_: fake)` replaces both the class-attribute patch and the `for_feature` staticmethod patch.
- WP03 does not delete `event_emitter.py`; WP04 does, after the last importer is moved.

### Parallel Opportunities

- T017, T018, T019 touch different files and can be split across agents once T014 lands.

### Dependencies

- Depends on WP01 (factory exists) and WP02 (bridge edits serialize on the same file).

### Risks & Mitigations

- A missed patch site fails at collection or at call → the blast-radius run in T020 catches it; the WP04 guard prevents recurrence.
- The oracle's `_RecordingProxy` wraps whatever the factory returns; keep the proxy, change only the wrapped callable.

---

## Work Package WP04: Deletion, single-class guard, docs, disclosure (Priority: P2)

**Goal**: Delete the concrete class, close the defect class by construction with an architectural guard, correct the two conformance-test reservation comments, and disclose the behavior change in the CHANGELOG.
**Independent Test**: `grep -rn "^class RuntimeEventEmitter" src/runtime/next/` → exactly one hit; `pytest tests/architectural/test_runtime_emitter_seam.py tests/architectural/test_layer_rules.py tests/architectural/test_no_legacy_terminology.py tests/status/test_producer_conformance.py tests/contract/test_identity_contract_matrix.py tests/specify_cli/events/` green; `make test-fast` green.
**Prompt**: `tasks/WP04-deletion-guard-and-disclosure.md`
**Requirement Refs**: FR-001, FR-009, FR-010, FR-011, NFR-003, NFR-005, C-001, C-002, C-003, C-006, C-007
**Estimated prompt size**: ~400 lines

### Included Subtasks

T021 Move the last live importer: `tests/specify_cli/events/test_decision_log_coord.py:17` → import the Protocol from `_internal_runtime.events` (WP04)
T022 `git rm src/runtime/next/event_emitter.py`; confirm no importer remains under `src/` or `tests/` (WP04)
T023 Add `tests/architectural/test_runtime_emitter_seam.py`: exactly one `class RuntimeEventEmitter` under `src/runtime/next/`; no `runtime.next.event_emitter` import anywhere; bridge source contains neither `flush(ctx.sync_emitter)` nor `sync_emitter=ctx.sync_emitter` (WP04)
T024 [P] Correct the reservation comments in `tests/status/test_producer_conformance.py:10-14` and `tests/contract/test_identity_contract_matrix.py:33-37` (WP04)
T025 [P] Add one `### Fixed` entry under `## [Unreleased] - 3.2.7rc1` in `CHANGELOG.md` (WP04)
T026 Run the full blast radius (plan.md §Test Plan) and the retired-surface scan; record counts (WP04)

### Implementation Notes

- The guard test is the by-construction closure for `043-close-defect-class-by-construction`; write it so a reintroduced plain-seam reference fails with a message naming the ADR.
- No version bump: `src/specify_cli/__init__.py` is untouched.

### Parallel Opportunities

- T024 and T025 are independent of T021–T023.

### Dependencies

- Depends on WP03.

### Risks & Mitigations

- Deleting the module before every importer is moved → T021 precedes T022; T022 greps before removing.

---

## Dependency & Execution Summary

- **Sequence**: WP01 ∥ WP02 → WP03 → WP04.
- **Parallelization**: WP01 and WP02 touch disjoint files and run concurrently in two lanes. Inside WP03, T017–T019 can be split across agents.
- **MVP Scope**: WP02 alone delivers the user-visible correctness fix (FR-005–FR-008). WP01+WP03+WP04 deliver the consolidation.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP04 |
| FR-002 | WP01, WP03 |
| FR-003 | WP01, WP03 |
| FR-004 | WP01 |
| FR-005 | WP02 |
| FR-006 | WP02 |
| FR-007 | WP02 |
| FR-008 | WP02 |
| FR-009 | WP01, WP04 |
| FR-010 | WP04 |
| FR-011 | WP04 |
| NFR-001 | WP02 |
| NFR-002 | WP03 |
| NFR-003 | WP04 |
| NFR-004 | WP02 |
| NFR-005 | WP01, WP04 |
| NFR-006 | WP01, WP03 |
| NFR-007 | WP01, WP02, WP03, WP04 |
| C-001 | WP04 |
| C-002 | WP04 |
| C-003 | WP04 |
| C-004 | WP02 |
| C-005 | WP01 |
| C-006 | WP04 |
| C-007 | WP04 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | `NullEmitter` mission fields + `for_mission` | WP01 | P0 | No |
| T002 | `NullEmitter.seed_from_snapshot` | WP01 | P0 | No |
| T003 | Factory + registry + env gate | WP01 | P0 | No |
| T004 | `__all__` + shim + re-export test | WP01 | P0 | Yes |
| T005 | Factory/registry unit tests | WP01 | P0 | No |
| T006 | Seam docstring | WP01 | P0 | Yes |
| T007 | Flush test fixtures | WP02 | P1 | No |
| T008 | F1 red | WP02 | P1 | No |
| T009 | F2 red | WP02 | P1 | No |
| T010 | Fix one (`:2187`) | WP02 | P1 | No |
| T011 | Fix two (`:1976`) + `DecisionGitLog.seed_from_snapshot` | WP02 | P1 | No |
| T012 | F3 + F4 green | WP02 | P1 | No |
| T013 | Red→green evidence | WP02 | P1 | No |
| T014 | Bridge import + 2 construction sites | WP03 | P1 | No |
| T015 | Engine `TYPE_CHECKING` retype | WP03 | P1 | No |
| T016 | Oracle spy migration | WP03 | P1 | No |
| T017 | decide_next sites ×5 | WP03 | P1 | Yes |
| T018 | blocked_paths sites ×4 | WP03 | P1 | Yes |
| T019 | unit ×4 + composition ×1 | WP03 | P1 | Yes |
| T020 | Blast radius + terminology grep | WP03 | P1 | No |
| T021 | Move last importer | WP04 | P2 | No |
| T022 | Delete `event_emitter.py` | WP04 | P2 | No |
| T023 | Architectural guard | WP04 | P2 | No |
| T024 | Conformance comments | WP04 | P2 | Yes |
| T025 | CHANGELOG entry | WP04 | P2 | Yes |
| T026 | Full blast radius + scans | WP04 | P2 | No |

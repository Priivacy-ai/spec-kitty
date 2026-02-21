# Feature Specification: Mission DSL Foundation

**Feature Branch**: `037-mission-dsl-foundation`
**Created**: 2026-02-09
**Status**: Draft
**Mission**: software-dev
**Phase**: 1B of local-first runtime convergence plan
**Depends On**: Phase 1A (036-kittify-runtime-centralization) complete

## User Scenarios & Testing *(mandatory)*

### User Story 1 - State Machine Mission Loading (Priority: P1)

A spec-kitty user creates a new project and selects the "software-dev" mission. The mission is loaded from `~/.kittify/missions/software-dev/mission.yaml` which now contains v1 format with states, transitions, and guards. The system validates the YAML against JSON Schema, constructs a MarkupMachine, and the user can only proceed through phases in the order defined by the state machine. Invalid transitions are rejected with clear error messages.

**Why this priority**: Core foundation — without state machine loading, no other Phase 1B features work.

**Independent Test**: Load a v1 mission YAML, verify states and transitions are enumerable, attempt an invalid transition and confirm rejection.

**Acceptance Scenarios**:

1. **Given** a v1 mission.yaml with states [specify, plan, implement, review, done], **When** loaded via `load_mission()`, **Then** a `StateMachineMission` is returned with a functioning state machine whose initial state matches the `initial` field.
2. **Given** a loaded state machine in state "specify", **When** `trigger("advance")` is called, **Then** the machine transitions to "plan" and `on_enter` callbacks fire.
3. **Given** a loaded state machine in state "specify", **When** an invalid trigger "skip_to_done" is called, **Then** the transition is rejected with a `MachineError` and the state remains "specify".

---

### User Story 2 - Backward-Compatible v0 Mission Loading (Priority: P1)

An existing spec-kitty user with a project using the current v0 phase-list mission format upgrades to the new version. Their existing `mission.yaml` files (which use `workflow.phases` lists) continue to work without modification. The system detects the v0 format and wraps it in a `PhaseMission` that presents a linear state machine interface (phase1 -> phase2 -> ... -> done) with no guards.

**Why this priority**: Breaking existing users would block adoption. Must ship alongside Story 1.

**Independent Test**: Load a current v0 mission.yaml, verify it returns a working mission with linear phase progression.

**Acceptance Scenarios**:

1. **Given** a v0 mission.yaml with `workflow.phases: [research, design, implement, test, review]`, **When** loaded via `load_mission()`, **Then** a `PhaseMission` is returned that supports linear `advance()` through all phases.
2. **Given** a v0 `PhaseMission` in state "research", **When** `advance()` is called, **Then** it transitions to "design" (next phase in list).
3. **Given** a v0 `PhaseMission` in terminal state "review", **When** `advance()` is called, **Then** it transitions to implicit "done" state.

---

### User Story 3 - Guard-Protected Transitions (Priority: P1)

A mission author defines guard conditions on transitions using declarative expressions. When a user attempts a phase transition, the guard expressions are evaluated. If all guards pass, the transition proceeds. If any guard fails, the transition is blocked with a message indicating which guard failed and what evidence is missing.

**Why this priority**: Guards are the primary value proposition — they enforce workflow quality gates.

**Independent Test**: Define a transition with `conditions: [artifact_exists("spec.md")]`, attempt transition without the artifact, confirm rejection. Create the artifact, confirm transition succeeds.

**Acceptance Scenarios**:

1. **Given** a transition from "specify" to "plan" with guard `artifact_exists("spec.md")`, **When** the transition is attempted without spec.md existing, **Then** the transition is blocked and the guard failure reason is reported.
2. **Given** a transition with guard `all_wp_status("done")`, **When** some WPs are not "done", **Then** the transition is blocked.
3. **Given** a transition with guard `gate_passed("review_approved")`, **When** a GatePassed event has been recorded for "review_approved", **Then** the transition proceeds.
4. **Given** a transition with `unless: [artifact_exists("SKIP_REVIEW")]`, **When** SKIP_REVIEW file exists, **Then** the transition is blocked (unless-guards invert logic).

---

### User Story 4 - Mission-Specific Workflows (Priority: P2)

Three distinct mission types are defined with genuinely different state machines:

- **software-dev**: Linear with rollback transitions (e.g., review -> implement for rework)
- **research**: Evidence-gated transitions requiring source documentation
- **plan**: Goal-oriented with rollback for iteration

Each mission has typed inputs and outputs, and different guard expressions appropriate to the domain.

**Why this priority**: Demonstrates the value of the DSL by showing differentiated workflows. Builds on Stories 1-3.

**Independent Test**: Load each mission, verify unique state graphs, trigger domain-specific transitions.

**Acceptance Scenarios**:

1. **Given** the software-dev v1 mission, **When** in "review" state, **Then** a "rework" trigger transitions back to "implement" (rollback).
2. **Given** the research v1 mission, **When** attempting to transition from "gathering" to "synthesis", **Then** guard requires `event_count("source_documented", 3)` — at least 3 sources documented.
3. **Given** the plan v1 mission, **When** in "draft" state, **Then** a "revise" trigger transitions back to "structure" (rollback).

---

### User Story 5 - Provisional Event Emission (Priority: P2)

Mission callbacks and guard evaluations emit events through a provisional `emit_event(type: str, payload: dict)` interface. This interface is a thin boundary for Phase 2 integration. In Phase 1B, events are logged to a local file but the interface contract is stable.

**Why this priority**: Establishes the event boundary contract that Phase 2 builds on. Must not over-engineer.

**Independent Test**: Trigger a state transition, verify `emit_event` is called with correct type and payload structure.

**Acceptance Scenarios**:

1. **Given** a state transition occurs, **When** `on_enter` callback fires, **Then** `emit_event("phase_entered", {"state": "plan", "mission": "software-dev"})` is called.
2. **Given** a guard evaluation fails, **When** the failure is processed, **Then** `emit_event("guard_failed", {"guard": "artifact_exists", "args": ["spec.md"]})` is called.
3. **Given** no Phase 2 event store is configured, **When** `emit_event` is called, **Then** the event is logged to a local JSONL file and does not raise.

---

### User Story 6 - JSON Schema Validation at Load Time (Priority: P2)

When a v1 mission.yaml is loaded, it is validated against a JSON Schema before the state machine is constructed. Invalid schemas produce clear error messages identifying the exact validation failure (missing required field, wrong type, invalid guard expression syntax).

**Why this priority**: Prevents runtime errors from malformed mission definitions.

**Independent Test**: Load a mission.yaml with a missing required field, confirm schema validation error with field path.

**Acceptance Scenarios**:

1. **Given** a v1 mission.yaml missing the `initial` field, **When** loaded, **Then** a `MissionValidationError` is raised citing the missing field.
2. **Given** a v1 mission.yaml with an unknown guard expression `invalid_check("foo")`, **When** loaded, **Then** validation fails with "Unknown guard expression: invalid_check".
3. **Given** a valid v1 mission.yaml, **When** loaded, **Then** schema validation passes silently and the state machine is constructed.

---

### Edge Cases

- What happens when a v1 mission.yaml has both `states`/`transitions` AND legacy `workflow.phases`? The v1 format takes precedence; `workflow.phases` is ignored with a deprecation warning.
- How does the system handle circular transitions in the state machine? The `transitions` library allows cycles (e.g., review -> implement -> review). This is intentional for rollback workflows.
- What happens when a guard expression references a feature directory that doesn't exist yet? `artifact_exists` returns False (guard fails gracefully, no exception).
- What happens when `emit_event` fails (e.g., disk full)? The event emission failure is logged as a warning but does not block the state transition. State transitions are primary; event emission is secondary.
- What if the `transitions` library is not installed? Import error at load time with a clear message: "pip install transitions" (the library is a declared dependency).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load v1 mission.yaml files containing `states`, `transitions`, `initial`, and optional `guards`, `inputs`, `outputs` sections into a functional state machine using the `transitions` library's `MarkupMachine`.
- **FR-002**: System MUST load v0 mission.yaml files containing `workflow.phases` into a `PhaseMission` wrapper that presents a linear state machine interface with no guards.
- **FR-003**: System MUST detect mission format (v0 vs v1) automatically based on the presence of `states` and `transitions` keys.
- **FR-004**: System MUST validate v1 mission.yaml against a JSON Schema at load time, raising `MissionValidationError` with field-path details on failure.
- **FR-005**: System MUST compile declarative guard expressions into callable methods bound to the state machine model. Supported expressions: `artifact_exists(path)`, `gate_passed(gate_name)`, `all_wp_status(status)`, `any_wp_status(status)`, `input_provided(name)`, `event_count(type, min)`.
- **FR-006**: System MUST reject unknown guard expression names at load time (not at runtime).
- **FR-007**: System MUST construct the state machine using `MarkupMachine` with `auto_transitions=False` and `send_event=True`.
- **FR-008**: System MUST support `on_enter` and `on_exit` callbacks on states, and `before`/`after` callbacks on transitions.
- **FR-009**: System MUST define three v1 mission YAML files: software-dev (with rollback transitions), research (with evidence gates), plan (with rollback transitions).
- **FR-010**: System MUST provide a provisional `emit_event(type: str, payload: dict)` interface that logs events to a local JSONL file.
- **FR-011**: System MUST support `conditions` (AND logic) and `unless` (AND-NOT logic) guard lists on transitions.
- **FR-012**: System MUST support typed `inputs` (string, path, url, boolean, integer) and `outputs` (artifact, report, data) in v1 mission schema.
- **FR-013**: Guard failures MUST produce structured error information including which guard failed and what evidence is missing.
- **FR-014**: The `PhaseMission` wrapper MUST be API-compatible with `StateMachineMission` so callers don't need to distinguish between v0 and v1 missions.
- **FR-015**: System MUST integrate with the existing 4-tier resolver from Phase 1A for mission YAML discovery (`~/.kittify/missions/`).

### Key Entities

- **Mission**: Top-level container for a workflow definition. Has a name, version, states, transitions, guards, inputs, and outputs.
- **State**: A named phase in the workflow (e.g., "specify", "implement"). Can have `on_enter`/`on_exit` callbacks.
- **Transition**: A named trigger that moves from source state(s) to destination state. Can have guards (conditions/unless) and callbacks (before/after).
- **Guard**: A declarative expression that must evaluate to True for a transition to proceed. Compiled to a callable at load time.
- **GuardExpression**: One of 6 primitive checks (artifact_exists, gate_passed, all_wp_status, any_wp_status, input_provided, event_count) with typed arguments.
- **PhaseMission**: Adapter wrapping v0 phase-list configs as linear state machines.
- **StateMachineMission**: Full v1 state machine backed by `transitions.MarkupMachine`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 3 v1 missions (software-dev, research, plan) load successfully and their state machines enforce defined transitions.
- **SC-002**: All 6 guard expression types evaluate correctly in both positive and negative cases.
- **SC-003**: All existing v0 mission.yaml files load without modification via `PhaseMission` wrapper.
- **SC-004**: Mission loading completes in under 200ms (including schema validation and machine construction).
- **SC-005**: Test fixtures F-Mission-001, F-Mission-003, F-Mission-004 pass, and gate G1 is satisfied.
- **SC-006**: No regressions in the existing 2032+ test suite beyond known pre-existing failures.
- **SC-007**: `emit_event` interface is called on every state transition with correct type/payload structure.
- **SC-008**: Invalid v1 mission YAML is rejected at load time with actionable error messages.

## Assumptions

- The `transitions` library (pytransitions, pip installable) is stable, MIT-licensed, and suitable for production use.
- Phase 1A (`~/.kittify/` centralization) is complete and merged to 2.x before Phase 1B begins.
- Guard expressions do NOT support user-defined custom guards in Phase 1B — only the 6 built-in primitives.
- The `emit_event` interface in Phase 1B is provisional — it logs to local JSONL only. Phase 2 will replace the backend with a proper event store.
- Hierarchical/nested states (children) are deferred to a future iteration — Phase 1B uses flat state machines only.

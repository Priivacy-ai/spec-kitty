# Feature Specification: Full-Lifecycle Telemetry Events

**Feature Branch**: `048-full-lifecycle-telemetry-events`
**Created**: 2026-02-16
**Status**: Draft
**Input**: Extend 043 telemetry event emission to cover all 5 kitty workflow phases

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phase-Level Event Emission Across All Workflow Phases (Priority: P1)

As a spec-kitty user, I want every phase of the kitty workflow (specify, plan, execute, review, merge) to emit telemetry events so that I have full visibility into model invocations and costs across the entire feature lifecycle.

**Why this priority**: Without coverage of all phases, cost tracking is incomplete. Specification and planning phases can consume significant token budgets but are currently only partially instrumented.

**Independent Test**: Can be verified by running a full lifecycle (specify through merge) on a test feature and confirming that `execution.events.jsonl` contains events for each phase.

**Acceptance Scenarios**:

1. **Given** a user runs `/spec-kitty.specify` for a new feature, **When** the specification phase completes, **Then** an ExecutionEvent with `role: "specifier"` is appended to the feature's `execution.events.jsonl`
2. **Given** a user runs `/spec-kitty.plan` for a feature, **When** the planning phase completes, **Then** an ExecutionEvent with `role: "planner"` is appended to the feature's event log
3. **Given** a user runs `/spec-kitty.implement` for a work package, **When** the implementation completes, **Then** an ExecutionEvent with `role: "implementer"` is appended (already implemented via move-task)
4. **Given** a user runs `/spec-kitty.review` for a work package, **When** the review completes, **Then** an ExecutionEvent with `role: "reviewer"` is appended (already implemented via move-task)
5. **Given** a user runs `/spec-kitty.merge` for a feature, **When** the merge phase completes, **Then** an ExecutionEvent with `role: "merger"` is appended to the feature's event log

---

### User Story 2 - Template-Driven Emission via CLI Command (Priority: P1)

As a spec-kitty user, I want a generic telemetry emit CLI command that slash command templates call at the end of each phase, so that event emission happens automatically as part of the workflow without requiring custom completion hooks per phase.

**Why this priority**: The current design attaches telemetry to scaffold commands (beginning of phase) or requires both `--agent` and `--model` flags to emit at all. A generic emit command called from templates ensures consistent coverage regardless of which phase is running.

**Independent Test**: Call `spec-kitty agent telemetry emit --feature 048-test --role specifier --agent claude` and verify an event appears in the feature's event log.

**Acceptance Scenarios**:

1. **Given** a slash command template includes an emit step at the end, **When** the agent completes the phase and executes the template's final step, **Then** a telemetry event is emitted with the phase role and any available metadata
2. **Given** the emit command is called without `--input-tokens` or `--cost-usd`, **When** the event is persisted, **Then** those fields are null but the event is still recorded (never silently skipped)
3. **Given** the emit command is called with all optional flags, **When** the event is persisted, **Then** all provided values are captured in the event payload

---

### User Story 3 - Minimum Required Event Fields (Priority: P1)

As a spec-kitty user, I want each telemetry event to contain at minimum the tool used, model used, phase, feature slug, and timestamp so that I can attribute costs and invocations to specific tools and phases.

**Why this priority**: Without these fields, events cannot be meaningfully queried or aggregated for cost tracking. This is the core data contract.

**Independent Test**: Emit an event from any phase and validate that the required fields are present and non-empty.

**Acceptance Scenarios**:

1. **Given** any workflow phase emits an event, **When** the event is persisted, **Then** the event payload contains `agent` (tool identifier: copilot, claude, codex, cursor, etc.), `model` (LLM model identifier), and `role` (phase identifier)
2. **Given** any workflow phase emits an event, **When** the event is persisted, **Then** the event envelope contains `aggregate_id` (feature slug), `timestamp` (ISO 8601 date), and `node_id`
3. **Given** a phase is invoked without explicit `--model` or `--agent` flags, **When** the event is emitted, **Then** the fields remain null (not omitted) and the event is still persisted

---

### User Story 4 - Cost Aggregation by Phase (Priority: P2)

As a spec-kitty user, I want to query and aggregate costs grouped by workflow phase so that I can understand which phases consume the most tokens and budget.

**Why this priority**: Phase-level cost breakdown enables informed decisions about workflow optimization (e.g., "planning consumes 60% of budget — should we simplify specs?").

**Independent Test**: Run the cost summary query with `group_by="role"` and confirm that results are bucketed by phase role.

**Acceptance Scenarios**:

1. **Given** a feature has events from multiple phases, **When** I query `cost_summary(events, group_by="role")`, **Then** I receive separate cost summaries for each phase (specifier, planner, implementer, reviewer, merger)
2. **Given** events exist across multiple features, **When** I query project-wide events grouped by role, **Then** I can see aggregate costs per phase across all features

---

### User Story 5 - Lifecycle Transition Events (Priority: P2)

As a spec-kitty user, I want lifecycle transitions between phases to be captured so that I can reconstruct the timeline of a feature's progression.

**Why this priority**: Transition events provide the temporal skeleton for understanding how features flow through the pipeline and where bottlenecks occur.

**Independent Test**: Complete a specify-to-plan transition and verify a transition event is recorded.

**Acceptance Scenarios**:

1. **Given** a feature moves from one phase to the next, **When** the transition occurs, **Then** an event capturing the phase transition is recorded in the feature's event log
2. **Given** a feature's event log contains transition events, **When** I read the events in causal order, **Then** I can reconstruct the complete phase timeline

---

### Edge Cases

- What happens when a phase fails partway through (e.g., specify aborted)? A failure event should still be emitted with `success: false` if the template's final step is reached.
- What happens when a phase is re-run (e.g., re-specify after clarification)? Each invocation emits a separate event; no deduplication by phase.
- What happens when the feature directory doesn't exist yet (first event for specify)? The emission pipeline creates the directory and JSONL file automatically.
- What happens when `--agent` or `--model` flags are not provided? Fields default to null; the event is still valid and persisted. The event is never silently skipped.
- What happens when the agent runtime doesn't report token counts? Token and cost fields remain null. The event still records phase, timestamp, feature, and agent identity.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a generic `spec-kitty agent telemetry emit` CLI command that accepts `--feature`, `--role`, `--agent`, `--model`, `--input-tokens`, `--output-tokens`, `--cost-usd`, `--duration-ms`, and `--success` flags
- **FR-002**: The emit command MUST always persist an event, even when optional fields (tokens, cost, model) are not provided — never silently skip emission
- **FR-003**: Slash command templates for specify, plan, tasks, review, and merge MUST include a final step that calls the emit command upon phase completion
- **FR-004**: System MUST support the following `role` values: `specifier`, `planner`, `implementer`, `reviewer`, `merger`
- **FR-005**: System MUST use the existing `emit_execution_event()` API from the 043 telemetry foundation
- **FR-006**: Every emitted event MUST contain at minimum: `role` (phase), `aggregate_id` (feature slug), `timestamp` — with `agent`, `model`, and token fields nullable
- **FR-007**: The cost summary query MUST support grouping by `role` to enable per-phase cost breakdown
- **FR-008**: Event emission failures MUST NOT block or disrupt the workflow command execution (fire-and-forget)
- **FR-009**: Existing `move-task` telemetry emissions for implement/review MUST be preserved (they serve as natural completion hooks)
- **FR-010**: The `if agent and model` gate on existing emissions MUST be removed — events always emit with available data
- **FR-011**: System MUST emit lifecycle transition events when a feature moves between phases
- **FR-012**: Slash command template updates MUST propagate to all 12 supported agents via migration

### Key Entities

- **ExecutionEvent**: An immutable telemetry record capturing a single phase invocation — includes tool, model, phase role, feature, tokens, cost, duration, and outcome
- **Phase Role**: The workflow phase that generated the event — one of `specifier`, `planner`, `implementer`, `reviewer`, `merger`
- **Feature Event Log**: Per-feature append-only JSONL file (`execution.events.jsonl`) containing all events across all phases
- **Telemetry Emit Command**: Generic CLI command (`spec-kitty agent telemetry emit`) that serves as the universal emission endpoint called by slash command templates

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 5 workflow phases (specify, plan, execute, review, merge) emit telemetry events upon completion
- **SC-002**: 100% of emitted events contain the minimum required fields (role, feature slug, timestamp) with optional fields nullable
- **SC-003**: Users can generate a per-phase cost breakdown for any feature using the existing query and cost summary APIs with `group_by="role"`
- **SC-004**: A full feature lifecycle (specify through merge) produces a complete event trail that can reconstruct the phase timeline
- **SC-005**: Zero workflow disruptions caused by telemetry failures (fire-and-forget guarantee preserved)
- **SC-006**: Template updates are deployed to all 12 supported agents

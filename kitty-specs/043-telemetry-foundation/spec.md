# Feature Specification: Telemetry Foundation and Cost Tracking

**Feature Branch**: `043-telemetry-foundation`
**Created**: 2026-02-15
**Status**: Draft
**Input**: Extend the 2.x status event system with execution event types, a query layer, and LLM cost tracking — consolidating the original 1.x features 040 (EventBridge) and 041 (Telemetry Store).

## Overview

The 2.x branch already has a mature status event system: `StatusEvent` for lane transitions, `status.events.jsonl` for JSONL persistence, `emit_status_transition` for the emission pipeline, and `reduce()`/`materialize()` for state reconstruction. This feature extends that system with:

1. **Execution events** — recording agent invocations with model, token counts, cost, duration, and success/failure
2. **Query layer** — filtered reads over the JSONL event log (by type, WP, agent, timeframe)
3. **Cost tracking** — aggregation of LLM spending by agent/model with a pricing table for estimation
4. **CLI reporting** — `spec-kitty agent telemetry` commands for cost visibility

Execution events are stored in the same per-feature `status.events.jsonl` files, collocated with status events. Cross-feature cost queries iterate over all feature event logs.

**2.x baseline**: `src/specify_cli/status/` — `models.py` (StatusEvent, Lane), `store.py` (append_event, read_events), `emit.py` (emit_status_transition), `reducer.py` (reduce, materialize).

## User Scenarios & Testing

### User Story 1 — Record Agent Execution Events (Priority: P1)

As a Spec Kitty operator, when an AI agent executes a work package (implementation or review), the system records an execution event with the agent identity, model used, token counts, cost, and duration, so I can later audit resource usage.

**Why this priority**: Execution events are the foundation for all cost tracking and telemetry queries. Without them, there's nothing to query.

**Independent Test**: Invoke an agent on a WP, verify that `status.events.jsonl` contains an `ExecutionEvent` with all required fields alongside existing `StatusEvent` entries.

**Acceptance Scenarios**:

1. **Given** a project with a feature in progress, **When** an agent completes a WP implementation, **Then** an `ExecutionEvent` is appended to the feature's `status.events.jsonl` with: event_type, event_id (ULID), timestamp, feature_slug, wp_id, agent, model, input_tokens, output_tokens, cost_usd, duration_ms, success, and error (if failed)
2. **Given** the existing status event system, **When** both `StatusEvent` and `ExecutionEvent` entries exist in the same JSONL file, **Then** `read_events()` can distinguish them by `event_type` field and return typed objects
3. **Given** an agent that does not report token counts, **When** the execution completes, **Then** the event records tokens as null/0 without error

---

### User Story 2 — Query Event History (Priority: P1)

As a Spec Kitty operator, I can query the event log to see a filtered view of events — by type, work package, agent, or timeframe — so I can audit specific activities.

**Why this priority**: Raw JSONL files are not human-friendly. A query layer makes telemetry usable.

**Independent Test**: Create a JSONL log with mixed event types, query by specific filters, verify correct results returned.

**Acceptance Scenarios**:

1. **Given** a feature's event log with mixed StatusEvents and ExecutionEvents, **When** I query by event_type="ExecutionEvent", **Then** only execution events are returned
2. **Given** events spanning multiple WPs, **When** I query by wp_id="WP02", **Then** only WP02's events are returned in chronological order
3. **Given** events from multiple agents, **When** I query by agent="claude", **Then** only Claude's events are returned
4. **Given** an empty or missing JSONL file, **When** I query, **Then** an empty result set is returned (no error)

---

### User Story 3 — View Cost Summary (Priority: P1)

As a team lead, I can see how much each AI agent has cost in tokens and estimated USD across a feature or across all features, so I can manage LLM spending.

**Why this priority**: Cost visibility is the primary business value of telemetry.

**Independent Test**: Create execution events with known token counts and costs, run cost aggregation, verify totals match manual calculation.

**Acceptance Scenarios**:

1. **Given** execution events for agents "claude" and "codex", **When** I query cost summary grouped by agent, **Then** I see total input_tokens, output_tokens, cost_usd, and event_count per agent
2. **Given** execution events, **When** I query cost summary grouped by model, **Then** I see totals per model (e.g., claude-sonnet-4-20250514, gpt-4.1)
3. **Given** execution events across 3 features, **When** I query project-wide cost summary, **Then** all features' events are aggregated
4. **Given** execution events with a timeframe filter, **When** I query, **Then** only events within that timeframe are aggregated

---

### User Story 4 — Estimate Cost from Token Counts (Priority: P2)

As a developer, when an execution event has token counts but no cost_usd, the system estimates the cost using a built-in pricing table, so I get cost visibility even when agents don't report costs.

**Why this priority**: Not all agents report costs. A pricing table fills the gap.

**Independent Test**: Create an ExecutionEvent with tokens but zero cost, configure pricing table, verify estimated cost appears in query results.

**Acceptance Scenarios**:

1. **Given** an ExecutionEvent with input_tokens=1000, output_tokens=500, cost_usd=0.0, model="claude-sonnet-4-20250514", **When** the pricing table has rates for that model, **Then** the cost summary includes an estimated cost
2. **Given** an ExecutionEvent with cost_usd=0.15 (explicitly set), **When** queried, **Then** the reported cost uses the event's value, not the pricing table
3. **Given** a model not in the pricing table, **When** queried, **Then** cost is reported as 0.0 with an "unknown model" flag

---

### User Story 5 — CLI Cost Report (Priority: P2)

As a developer, I can run a CLI command to see a formatted cost report, so I can quickly check spending without parsing JSONL manually.

**Why this priority**: Makes telemetry immediately accessible via the existing CLI.

**Independent Test**: Run the CLI command against a project with events and verify formatted table output.

**Acceptance Scenarios**:

1. **Given** a project with execution events, **When** I run `spec-kitty agent telemetry cost`, **Then** I see a Rich-formatted table with per-agent cost breakdown and project total
2. **Given** a project with no execution events, **When** I run the command, **Then** I see "No execution events found"
3. **Given** a project with events across 5 features, **When** I run the command with `--feature 043-*`, **Then** only that feature's costs are shown

---

### Edge Cases

- What happens when the JSONL file is very large (>100MB)? The query layer MUST stream-parse, not load the entire file into memory.
- What happens when JSONL lines are malformed (partial write from crash)? Skip malformed lines with a warning, return valid results. This aligns with 2.x's existing `read_events()` behavior.
- What happens when the pricing table is missing or malformed? Use zero costs and log a warning.
- What happens when querying across features and some feature directories are missing? Skip missing features, return partial results.
- How do execution events interact with the status reducer? The reducer ignores non-status events — it only processes StatusEvents for state materialization.

## Requirements

### Functional Requirements

#### Event Model Extension

- **FR-001**: System MUST add an `ExecutionEvent` dataclass alongside the existing `StatusEvent` in `src/specify_cli/status/models.py` with fields: event_id (ULID), event_type ("ExecutionEvent"), at (ISO 8601), feature_slug, wp_id, agent, model, input_tokens (int|null), output_tokens (int|null), cost_usd (float|null), duration_ms (int), success (bool), error (str|null)
- **FR-002**: The JSONL store (`append_event`, `read_events`) MUST handle both `StatusEvent` and `ExecutionEvent` entries, distinguishing them by an `event_type` field
- **FR-003**: The existing `reduce()` and `materialize()` functions MUST ignore `ExecutionEvent` entries — they only process `StatusEvent` for state materialization
- **FR-004**: System MUST provide an `emit_execution_event()` function following the same pipeline pattern as `emit_status_transition()` but without validation/transition logic

#### Execution Event Emission

- **FR-005**: The orchestrator MUST emit an `ExecutionEvent` after each agent invocation (implementation or review), capturing the agent's reported output (model, tokens, cost, duration, success)
- **FR-006**: If the agent invoker does not report token/cost data, the event MUST record null values — emission MUST NOT fail due to missing telemetry data
- **FR-007**: Execution event emission MUST NOT block or slow down the orchestrator pipeline — failures are logged and swallowed

#### Query Layer

- **FR-008**: System MUST provide a `query_events()` function that reads JSONL event logs and returns filtered, typed event objects
- **FR-009**: System MUST support filtering by: event_type, wp_id, agent, model, timeframe (start/end datetime), success (bool)
- **FR-010**: System MUST support project-wide queries that iterate over all feature directories' event logs
- **FR-011**: System MUST stream-parse JSONL files to avoid loading entire files into memory
- **FR-012**: System MUST handle malformed JSONL lines gracefully (skip with warning, continue parsing) — consistent with existing `read_events()` behavior

#### Cost Tracking

- **FR-013**: System MUST provide a `cost_summary()` function that aggregates ExecutionEvents by agent and/or model, summing input_tokens, output_tokens, cost_usd, and event_count
- **FR-014**: System MUST support a YAML-based pricing table mapping model identifiers to per-token input/output costs
- **FR-015**: System MUST ship a default pricing table with rates for major providers (Anthropic Claude, OpenAI GPT, Google Gemini). Project-specific overrides are defined in the constitution layer (`.kittify/memory/constitution.md`), which serves as the single source of truth for all project-level configuration including pricing preferences
- **FR-016**: When an ExecutionEvent has token counts but no cost_usd, the system MUST estimate cost from the pricing table
- **FR-017**: When an ExecutionEvent has an explicit cost_usd, the system MUST use it over the pricing table estimate

#### CLI Commands

- **FR-018**: System MUST provide `spec-kitty agent telemetry cost` command that outputs a Rich-formatted cost report
- **FR-019**: The cost command MUST support `--feature` filter and `--since`/`--until` timeframe filters
- **FR-020**: The cost command MUST support `--group-by` (agent|model|feature) for different aggregation views
- **FR-021**: The cost command MUST output JSON when `--json` flag is provided

### Key Entities

- **ExecutionEvent**: Records an agent invocation — agent, model, tokens, cost, duration, success/failure. Stored alongside StatusEvents in per-feature JSONL.
- **TelemetryQuery**: Query parameters — event_type, wp_id, agent, model, timeframe, success filter.
- **CostSummary**: Aggregated cost report — grouping key (agent/model/feature), total_input_tokens, total_output_tokens, total_cost_usd, event_count, estimated flag.
- **PricingTable**: Model-to-cost mapping — model_id → cost_per_1k_input_tokens, cost_per_1k_output_tokens. Ships with defaults; project-specific overrides flow from the constitution layer.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All existing spec-kitty tests pass without modification after this feature is integrated (100% backward compatibility with the status event system)
- **SC-002**: Execution events emitted during agent invocations contain all required fields and can be parsed alongside StatusEvents
- **SC-003**: Queries over a 10,000-line JSONL file complete in under 2 seconds
- **SC-004**: Cost aggregation matches manual calculation within rounding tolerance (0.01 USD)
- **SC-005**: CLI cost report renders correctly for projects with 0, 1, and 100+ execution events
- **SC-006**: New code achieves at least 90% test coverage

## Assumptions

- **ASM-001**: Extends the existing 2.x status event system (`src/specify_cli/status/`) — does not replace it
- **ASM-002**: ExecutionEvents are stored in the same per-feature `status.events.jsonl` files as StatusEvents
- **ASM-003**: The pricing table ships with reasonable defaults for major providers. Project-specific overrides are part of the constitution layer — the single source of truth for all project-level configuration preferences
- **ASM-004**: Log rotation and archival are out of scope — deferred to a future feature
- **ASM-005**: The orchestrator (`src/specify_cli/orchestrator/`) already captures agent invocation results via `InvocationResult` — this feature wraps those into ExecutionEvents
- **ASM-006**: Cross-feature queries iterate over all `kitty-specs/*/status.events.jsonl` files — no centralized index

## Out of Scope

- **Log rotation/archival**: Large JSONL files are handled by stream-parsing, not rotation
- **SQLite materialized views**: Deferred — JSONL query performance is sufficient for typical project sizes
- **Real-time dashboards**: No WebSocket or live-update telemetry views
- **Token counting from prompts**: This feature records what agents report, not independent token counting
- **Cost alerts or budgets**: No automatic warnings when spending exceeds thresholds
- **Historical pricing**: Pricing table is current rates only, no temporal price tracking
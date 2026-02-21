## Context: Events & Telemetry

Terms describing the event emission and telemetry infrastructure.

### EventBridge

|                   |                                                                                                                                                                                                                                                                             |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | An ABC for structured event emission at workflow points. All cross-cutting concerns (telemetry, work logs, cost tracking) register as consumers. `NullEventBridge` discards events (default). `CompositeEventBridge` fans out to registered listeners with error isolation. |
| **Context**       | Events & Telemetry                                                                                                                                                                                                                                                          |
| **Status**        | candidate                                                                                                                                                                                                                                                                   |
| **In code**       | Concept in architecture/specs; no canonical `core/events/bridge.py` implementation path in current tree                                                                                                                                                                     |
| **Related terms** | [Lane Transition Event](#lane-transition-event), [Validation Event](#validation-event), [Execution Event](#execution-event)                                                                                                                                                 |
| **Architecture**  | Unified Event Spine — all lifecycle events flow through a single bridge                                                                                                                                                                                                     |

---

### Lane Transition Event

|                   |                                                                                                                                          |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Historical/conceptual name for lane-move events. In current implementation this concept is represented by [Status Event](#status-event). |
| **Context**       | Events & Telemetry                                                                                                                       |
| **Status**        | superseded                                                                                                                               |
| **In code**       | Superseded by `StatusEvent` in `src/specify_cli/status/models.py`                                                                        |
| **Related terms** | [Lane](#lane), [Status Event](#status-event)                                                                                             |

---

### Validation Event

|                   |                                                                                                      |
|-------------------|------------------------------------------------------------------------------------------------------|
| **Definition**    | Emitted when a governance check runs. Makes governance compliance auditable.                         |
| **Context**       | Events & Telemetry                                                                                   |
| **Status**        | candidate                                                                                            |
| **In code**       | Governance event model is planned under governance features; no canonical model type in current tree |
| **Fields**        | `timestamp`, `validation_type`, `status`, `directive_refs`, `duration_ms`                            |
| **Related terms** | [Validation Result](#validation-result), [EventBridge](#eventbridge)                                 |

---

### Execution Event

|                   |                                                                                                                                  |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Emitted when a tool executes work. Captures token usage, cost, duration, and success/failure.                                    |
| **Context**       | Events & Telemetry                                                                                                               |
| **Status**        | candidate                                                                                                                        |
| **In code**       | Candidate telemetry concept; no canonical `ExecutionEvent` model in current tree                                                 |
| **Fields**        | `timestamp`, `work_package_id`, `agent`, `model`, `input_tokens`, `output_tokens`, `cost_usd`, `duration_ms`, `success`, `error` |
| **Related terms** | [EventBridge](#eventbridge), [Invocation Result](#invocation-result)                                                             |

---

### Status Event

|                   |                                                                                                                                           |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Immutable record of a single work-package lane transition in the canonical status model.                                                  |
| **Context**       | Events & Telemetry                                                                                                                        |
| **Status**        | canonical                                                                                                                                 |
| **In code**       | `StatusEvent` in `src/specify_cli/status/models.py`                                                                                       |
| **Related terms** | [Status Event Log](#status-event-log), [Status Reducer](#status-reducer), [Lane](#lane)                                                   |
| **Fields**        | `event_id`, `feature_slug`, `wp_id`, `from_lane`, `to_lane`, `at`, `actor`, `force`, `execution_mode`, `reason`, `review_ref`, `evidence` |

---

### Mission Event Log

|                   |                                                                                                   |
|-------------------|---------------------------------------------------------------------------------------------------|
| **Definition**    | Provisional per-feature mission workflow log (`mission-events.jsonl`) used by mission v1 runtime. |
| **Context**       | Events & Telemetry                                                                                |
| **Status**        | canonical                                                                                         |
| **In code**       | `emit_event()` / `read_events()` in `src/specify_cli/mission_v1/events.py`                        |
| **Location**      | `kitty-specs/<feature>/mission-events.jsonl`                                                      |
| **Related terms** | [Status Event Log](#status-event-log)                                                             |
| **Distinction**   | Mission events are runtime diagnostics; they are not the authority for lane/status state          |

---

### Status Event Log

|                          |                                                                                                                                                    |
|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**           | The canonical append-only per-feature status history file (`status.events.jsonl`). Each lane transition is persisted as an immutable status event. |
| **Context**              | Events & Telemetry                                                                                                                                 |
| **Status**               | canonical                                                                                                                                          |
| **Location**             | `kitty-specs/<feature>/status.events.jsonl`                                                                                                        |
| **Source-of-truth role** | Canonical authority for WP status history and state derivation                                                                                     |
| **Related terms**        | [Lane Transition Event](#lane-transition-event), [Status Reducer](#status-reducer), [Status Materialization](#status-materialization)              |
| **Distinction**          | Separate from [Mission Event Log](#mission-event-log); both can exist and serve different purposes                                                 |

---

### Status Reducer

|                   |                                                                                                                                           |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The deterministic reducer that folds the canonical [Status Event Log](#status-event-log) into current workflow state.                     |
| **Context**       | Events & Telemetry                                                                                                                        |
| **Status**        | canonical                                                                                                                                 |
| **Related terms** | [Status Event Log](#status-event-log), [Status Materialization](#status-materialization), [Materialization Drift](#materialization-drift) |

---

### Status Materialization

|                   |                                                                                                                               |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The process of regenerating `status.json` from `status.events.jsonl` (for example via `spec-kitty agent status materialize`). |
| **Context**       | Events & Telemetry                                                                                                            |
| **Status**        | canonical                                                                                                                     |
| **Related terms** | [Status Event Log](#status-event-log), [Status Reducer](#status-reducer), [Materialization Drift](#materialization-drift)     |
| **Result**        | `status.json` is a derived snapshot, not the canonical source                                                                 |

---

### Materialization Drift

|                   |                                                                                                                                      |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A mismatch between persisted `status.json` and the reducer output computed from the canonical [Status Event Log](#status-event-log). |
| **Context**       | Events & Telemetry                                                                                                                   |
| **Status**        | canonical                                                                                                                            |
| **Related terms** | [Status Materialization](#status-materialization), [Status Reducer](#status-reducer), [Derived-View Drift](#derived-view-drift)      |

---

### Derived-View Drift

|                   |                                                                                                                                   |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A mismatch between compatibility views (for example WP frontmatter `lane`) and canonical status state derived from the event log. |
| **Context**       | Events & Telemetry                                                                                                                |
| **Status**        | canonical                                                                                                                         |
| **Related terms** | [Materialization Drift](#materialization-drift), [Lane](#lane), [Status Event Log](#status-event-log)                             |

---

### Status Reconciliation

|                   |                                                                                                                                                                                              |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A cross-repository audit and alignment process that compares implementation evidence (branches, commits, merges) with canonical status state, and optionally emits corrective status events. |
| **Context**       | Events & Telemetry                                                                                                                                                                           |
| **Status**        | canonical                                                                                                                                                                                    |
| **Related terms** | [Status Event Log](#status-event-log), [Status Reducer](#status-reducer), [Work Package](#work-package)                                                                                      |

---

### Rollback-Aware Precedence

|                         |                                                                                                                                                       |
|-------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**          | Merge/event conflict rule where explicit reviewer rollback (`for_review` -> `in_progress` with `review_ref`) outranks concurrent forward progression. |
| **Context**             | Events & Telemetry                                                                                                                                    |
| **Status**              | canonical                                                                                                                                             |
| **Authority**           | ADR `2026-02-09-3`                                                                                                                                    |
| **Related terms**       | [Status Event Log](#status-event-log), [Status Reducer](#status-reducer), [Guard Condition](#guard-condition)                                         |
| **Historical contrast** | Replaces naive "most-done-wins" conflict resolution                                                                                                   |

---

### Done Evidence

|                   |                                                                                                                                                                                 |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Structured acceptance evidence required for a transition to `done` (unless a forced transition is explicitly used). Usually contains reviewer identity, verdict, and reference. |
| **Context**       | Events & Telemetry                                                                                                                                                              |
| **Status**        | canonical                                                                                                                                                                       |
| **Related terms** | [Lane](#lane), [Guard Condition](#guard-condition), [Forced Transition](#forced-transition)                                                                                     |

---

### Guard Condition

|                   |                                                                                                                                                                    |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A transition-specific invariant that must be satisfied before a status transition is accepted (for example actor identity, review reference, or evidence payload). |
| **Context**       | Events & Telemetry                                                                                                                                                 |
| **Status**        | canonical                                                                                                                                                          |
| **Related terms** | [Lane](#lane), [Done Evidence](#done-evidence), [Forced Transition](#forced-transition)                                                                            |

---

### Forced Transition

|                   |                                                                                                                                                                                  |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A status transition that bypasses normal [Guard Condition](#guard-condition) checks and is accepted only with explicit actor identity and reason, preserving a full audit trail. |
| **Context**       | Events & Telemetry                                                                                                                                                               |
| **Status**        | canonical                                                                                                                                                                        |
| **Related terms** | [Guard Condition](#guard-condition), [Done Evidence](#done-evidence), [Status Event Log](#status-event-log)                                                                      |

---

### Status Rollout Phases

|                   |                                                                                                                                     |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The staged migration model for status authority: `hardening` (phase 0), `dual-write` (phase 1), and `read-cutover` (phase 2).       |
| **Context**       | Events & Telemetry                                                                                                                  |
| **Status**        | canonical                                                                                                                           |
| **Related terms** | [Status Event Log](#status-event-log), [Status Materialization](#status-materialization), [Derived-View Drift](#derived-view-drift) |

---

### Event Envelope

|                   |                                                                                                                                                |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The fixed schema contract for emitted events, combining core event metadata, identity metadata, and optional git-correlation metadata.         |
| **Context**       | Events & Telemetry                                                                                                                             |
| **Status**        | canonical                                                                                                                                      |
| **Location**      | `docs/reference/event-envelope.md`                                                                                                             |
| **Related terms** | [EventBridge](#eventbridge), [Lamport Clock](#lamport-clock), [Causation ID](#causation-id), [Git Correlation Fields](#git-correlation-fields) |

---

### Lamport Clock

|                   |                                                                                                                               |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The monotonic logical clock value in the [Event Envelope](#event-envelope) used for deterministic ordering of emitted events. |
| **Context**       | Events & Telemetry                                                                                                            |
| **Status**        | canonical                                                                                                                     |
| **Related terms** | [Event Envelope](#event-envelope), [Causation ID](#causation-id)                                                              |

---

### Causation ID

|                   |                                                                                                                          |
|-------------------|--------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Optional parent event identifier in the [Event Envelope](#event-envelope), used to correlate event chains and causality. |
| **Context**       | Events & Telemetry                                                                                                       |
| **Status**        | canonical                                                                                                                |
| **Related terms** | [Event Envelope](#event-envelope), [Lamport Clock](#lamport-clock)                                                       |

---

### Git Correlation Fields

|                   |                                                                                                            |
|-------------------|------------------------------------------------------------------------------------------------------------|
| **Definition**    | Optional event metadata that ties events to git context: `git_branch`, `head_commit_sha`, and `repo_slug`. |
| **Context**       | Events & Telemetry                                                                                         |
| **Status**        | canonical                                                                                                  |
| **Related terms** | [Event Envelope](#event-envelope), [Status Reconciliation](#status-reconciliation)                         |

---

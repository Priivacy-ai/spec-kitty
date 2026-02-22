## Context: Events and Telemetry

Terms describing Spec Kitty's append-only event model and replay behavior.

### Event Envelope

| | |
|---|---|
| **Definition** | Standard wrapper for an emitted event, including identity, ordering, and payload fields. |
| **Context** | Events & Telemetry |
| **Status** | canonical |
| **Common fields** | `event_id`, `event_type`, `aggregate_id`, `lamport_clock`, `payload` |

---

### Glossary Evolution Log

| | |
|---|---|
| **Definition** | Append-only sequence of glossary-related events that records candidate extraction, semantic checks, clarifications, and sense updates. |
| **Context** | Events & Telemetry |
| **Status** | canonical |
| **Related terms** | [Semantic Check](./execution.md#semantic-check), [Clarification Prompt](./execution.md#clarification-prompt) |

---

### Glossary Scope

| | |
|---|---|
| **Definition** | Bounded semantic scope used for term/sense resolution. |
| **Context** | Events & Telemetry |
| **Status** | canonical |
| **Allowed values** | `spec_kitty_core`, `team_domain`, `audience_domain`, `mission_local` |

---

### Semantic Check Evaluation

| | |
|---|---|
| **Definition** | Deterministic pre-generation evaluation of extracted terms against active glossary scopes. |
| **Context** | Events & Telemetry |
| **Status** | canonical |
| **Block rule** | Unresolved high-severity conflicts block generation |

---

### Replay

| | |
|---|---|
| **Definition** | Reconstructing effective glossary state and decisions from canonical append-only events. |
| **Context** | Events & Telemetry |
| **Status** | canonical |
| **Invariant** | No side-channel state may be required for correctness |

---

### Telemetry (Out of Scope for This Slice)

| | |
|---|---|
| **Definition** | Optional usage/cost analytics and operational observability fields layered on top of core event contracts. |
| **Context** | Events & Telemetry |
| **Status** | candidate |
| **Note** | Not required for glossary semantic integrity in this 2.x adoption slice |


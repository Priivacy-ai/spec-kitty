## Context: System Events

Terms describing Spec Kitty's append-only event model, replay behavior, and system-level event types.

### Event Envelope

| | |
|---|---|
| **Definition** | Standard wrapper for an emitted event, including identity, ordering, and payload fields. |
| **Context** | System Events |
| **Status** | canonical |
| **Common fields** | `event_id`, `event_type`, `aggregate_id`, `lamport_clock`, `payload` |

---

### Glossary Evolution Log

| | |
|---|---|
| **Definition** | Append-only sequence of glossary-related events that records candidate extraction, semantic checks, clarifications, and sense updates. |
| **Context** | System Events |
| **Status** | canonical |
| **Related terms** | [Semantic Check](./execution.md#semantic-check), [Clarification Prompt](./execution.md#clarification-prompt) |

---

### Glossary Scope

| | |
|---|---|
| **Definition** | Bounded semantic scope used for term/sense resolution. |
| **Context** | System Events |
| **Status** | canonical |
| **Allowed values** | `spec_kitty_core`, `team_domain`, `audience_domain`, `mission_local` |

---

### Semantic Check Evaluation

| | |
|---|---|
| **Definition** | Deterministic pre-generation evaluation of extracted terms against active glossary scopes. |
| **Context** | System Events |
| **Status** | canonical |
| **Block rule** | Unresolved high-severity conflicts block generation |

---

### Replay

| | |
|---|---|
| **Definition** | Reconstructing effective glossary state and decisions from canonical append-only events. |
| **Context** | System Events |
| **Status** | canonical |
| **Invariant** | No side-channel state may be required for correctness |

---

### Telemetry (Out of Scope for This Slice)

| | |
|---|---|
| **Definition** | Optional usage/cost analytics and operational observability fields layered on top of core event contracts. |
| **Context** | System Events |
| **Status** | candidate |
| **Note** | Not required for glossary semantic integrity in this 2.x adoption slice |

---

### Dossier Event

| | |
|---|---|
| **Definition** | An event emitted during dossier operations. Four types: `ArtifactIndexed` (artifact scanned), `SnapshotComputed` (snapshot created), `ArtifactMissing` (required artifact not found), `ParityDriftDetected` (content changed since baseline). |
| **Context** | System Events |
| **Status** | candidate |
| **Related terms** | [Mission Dossier](./dossier.md#mission-dossier), [Anomaly Event](#anomaly-event), [Event Envelope](#event-envelope) |

---

### Anomaly Event

| | |
|---|---|
| **Definition** | An event that is only emitted when something unexpected happens — such as a required artifact being missing or parity drift being detected. Unlike routine lifecycle events, anomaly events signal conditions that may need the Human-in-Charge's attention. |
| **Context** | System Events |
| **Status** | candidate |
| **Related terms** | [Dossier Event](#dossier-event), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic) |

---

### WPStatusChanged

| | |
|---|---|
| **Definition** | The standard event emitted when a work package moves from one lane to another (e.g., from `planned` to `in_progress`). Part of the status model's event contract. |
| **Context** | System Events |
| **Status** | candidate |
| **Related terms** | [Work Package](./orchestration.md#work-package), [Lane](./orchestration.md#lane), [Event Envelope](#event-envelope) |

---

### Lamport Clock

| | |
|---|---|
| **Definition** | A logical counter included in event envelopes that tracks the order events happened in, without relying on wall-clock time. Each new event increments the counter, ensuring events can be reliably ordered even across different machines. |
| **Context** | System Events |
| **Status** | candidate |
| **Related terms** | [Event Envelope](#event-envelope), [Replay](#replay) |

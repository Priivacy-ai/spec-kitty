# Data Model: Mission Collaboration CLI

**Feature**: 040-mission-collaboration-cli-soft-coordination
**Version**: S1/M1 Step 1
**Date**: 2026-02-15

## Overview

This document defines the data model for mission collaboration, including entities, relationships, state machines, and invariants. The model supports soft coordination (advisory warnings, not hard locks) with local-first event queuing and offline replay.

**Key Principles:**
- **SaaS-authoritative participation**: participant_id minted by SaaS, bound to auth principal
- **Local-first events**: Event queue authoritative for ordering, SaaS eventual consistency replica
- **ULID identifiers**: event_id, causation_id, participant_id use ULID format (26 chars)
- **Soft coordination**: Collision warnings advisory, not blocking

---

## Core Entities

### MissionRun

**Description:** Runtime collaboration/execution container (replaces deprecated "Feature" term in runtime context).

**Storage:** SaaS-managed (not persisted in CLI)

**Attributes:**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `mission_id` | `str` | Primary key, UUID or slug | Required, unique |
| `mission_run_id` | `str` | Session correlation key (ULID) | Required, unique |
| `created_at` | `datetime` | ISO timestamp | Required |
| `status` | `enum` | active, completed, cancelled | Required, default: active |
| `participant_count` | `int` | Number of joined participants | >= 0 |

**Relationships:**
- Contains 1+ WorkPackages
- Has 0+ Participants (joined participants)

**Lifecycle:**
- Created by SaaS when mission starts
- Participants join via CLI `mission join` command
- Completes when all work packages done
- Can be cancelled (not implemented in S1/M1)

---

### Participant

**Description:** Developer, reviewer, observer, or stakeholder actively participating in a mission.

**Storage:**
- SaaS: Authoritative roster (mission_id → list of participants)
- CLI: Cached in `~/.spec-kitty/missions/<mission_id>/session.json` (single participant, self only)

**Attributes:**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `participant_id` | `str` | SaaS-minted ULID (mission-scoped) | Required, unique, 26 chars |
| `mission_id` | `str` | Foreign key to MissionRun | Required |
| `auth_principal` | `str` | User email or OAuth subject | Required (SaaS binding) |
| `role` | `enum` | developer, reviewer, observer, stakeholder | Required, join roles only |
| `participant_type` | `enum` | human, llm_context, service | Required, default: human |
| `drive_intent` | `enum` | active, inactive | Required, default: inactive |
| `focus` | `str | None` | none, wp:<id>, step:<id> | Optional, nullable |
| `last_activity_at` | `datetime` | ISO timestamp | Required, updated on events |
| `joined_at` | `datetime` | ISO timestamp | Required, immutable |

**Derived Attributes (computed from role):**
| Field | Type | Description |
|-------|------|-------------|
| `capabilities` | `dict[str, bool]` | can_focus, can_drive, can_execute, can_ack_warning, can_comment, can_decide |

**Capability Matrix (role → permissions):**
| Role | can_focus | can_drive | can_execute | can_ack_warning | can_comment | can_decide |
|------|-----------|-----------|-------------|-----------------|-------------|------------|
| developer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| reviewer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| observer | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| stakeholder | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

**Relationships:**
- Participates in 1 MissionRun
- May focus on 0-1 WorkPackage or PromptStep

**State Machine (Status):**
```
joining → joined → active → inactive → left
```

**State Transitions:**
- `joining → joined`: SaaS join API success, participant_id minted
- `joined → active`: First event emitted (ParticipantJoined)
- `active → inactive`: Set drive_intent=inactive or timeout (not implemented S1/M1)
- `inactive → active`: Set drive_intent=active
- `active → left`: Explicit leave command (not implemented S1/M1)

**Invariants:**
- participant_id MUST be SaaS-minted (CLI cannot invent IDs)
- participant_id MUST be bound to auth_principal (one-to-one mapping per mission)
- role MUST be one of 4 join roles (llm_actor is NOT a valid role)
- participant_type is metadata only (does NOT affect permissions)
- Execution precondition: role has can_execute=true AND drive_intent=active

---

### WorkPackage

**Description:** Mission-local execution unit (coarser granularity than PromptStep).

**Storage:** SaaS-managed (not persisted in CLI, cached in collaboration/state.py)

**Attributes:**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `wp_id` | `str` | Primary key within mission (e.g., "WP01") | Required, unique in mission |
| `mission_id` | `str` | Foreign key to MissionRun | Required |
| `title` | `str` | Human-readable title | Required |
| `status` | `enum` | pending, in_progress, for_review, done | Required, default: pending |
| `dependencies` | `list[str]` | List of wp_ids (blocking dependencies) | Optional, empty list default |

**Relationships:**
- Belongs to 1 MissionRun
- Contains 1+ PromptSteps
- May have 0+ active Participants (with focus=wp:<id>)

**Lifecycle:**
- Created during mission planning phase
- Status updated via spec-kitty agent commands (not collaboration commands)
- Dependencies defined in task frontmatter

---

### PromptStep

**Description:** Atomic execution step within work package (finest granularity for focus).

**Storage:** SaaS-managed (not persisted in CLI, cached in collaboration/state.py)

**Attributes:**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `step_id` | `str` | Primary key within WP (e.g., "step:42") | Required, unique in WP |
| `parent_wp_id` | `str` | Foreign key to WorkPackage | Required |
| `prompt_text` | `str` | Markdown prompt text | Required |
| `status` | `enum` | pending, running, completed, failed | Required, default: pending |

**Relationships:**
- Belongs to 1 WorkPackage
- May have 0+ active Participants (with focus=step:<id>)

**Lifecycle:**
- Created during mission planning phase
- Status updated via agent execution commands
- Not directly manipulated by collaboration commands

---

### CollaborationEvent

**Description:** Canonical event envelope (14 event types, feature 006 ownership).

**Storage:**
- CLI: Local queue at `~/.spec-kitty/events/<mission_id>.jsonl` (newline-delimited JSON)
- SaaS: Ingested via batch replay endpoint `/api/v1/events/batch/`

**Attributes (Base Event Model):**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `event_id` | `str` | ULID identifier | Required, unique, 26 chars |
| `event_type` | `str` | Event type name (e.g., "DriveIntentSet") | Required, 14 types (see below) |
| `aggregate_id` | `str` | mission_id (primary stream key) | Required |
| `payload` | `dict` | Event-specific data (includes participant_id) | Required, opaque to base model |
| `timestamp` | `datetime` | Wall-clock timestamp | Required, ISO format |
| `node_id` | `str` | CLI instance identifier | Required |
| `lamport_clock` | `int` | Lamport logical clock value | Required, >= 0, monotonic |
| `causation_id` | `str | None` | ULID of triggering event | Optional, 26 chars |

**Additional Metadata (Feature 006 Extension - not in base model):**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `correlation_id` | `str` | mission_run_id (session correlation) | Optional, ULID |
| `project_uuid` | `str` | Project context | Optional, UUID |
| `project_slug` | `str` | Project slug | Optional |
| `schema_version` | `str` | Semver schema version (e.g., "1.0.0") | Optional |
| `data_tier` | `int` | Integer tier 0-4 (not string) | Optional |

**Event Types (14 total, feature 006 ownership):**
1. **ParticipantInvited** - Participant invited to mission (not implemented S1/M1)
2. **ParticipantJoined** - Participant successfully joined mission
3. **ParticipantLeft** - Participant left mission (not implemented S1/M1)
4. **PresenceHeartbeat** - Participant presence signal (not implemented S1/M1)
5. **DriveIntentSet** - Participant set drive intent (active|inactive)
6. **FocusChanged** - Participant changed focus target
7. **PromptStepExecutionStarted** - Agent started executing step
8. **PromptStepExecutionCompleted** - Agent completed step execution
9. **ConcurrentDriverWarning** - High-severity collision detected
10. **PotentialStepCollisionDetected** - Medium-severity collision detected
11. **WarningAcknowledged** - User acknowledged collision warning
12. **CommentPosted** - Participant posted comment
13. **DecisionCaptured** - Participant made decision
14. **SessionLinked** - Session linked to external context (not implemented S1/M1)

**Payload Schemas (Feature 006 Contract - DRAFT):**

**ParticipantJoined:**
```python
{
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",  # ULID
  "role": "developer",
  "participant_type": "human"
}
```

**DriveIntentSet:**
```python
{
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",  # ULID
  "previous_state": "inactive",
  "new_state": "active",
  "focus_context": "wp:WP01"  # Current focus when drive set
}
```

**FocusChanged:**
```python
{
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",  # ULID
  "previous_focus": "wp:WP01",
  "new_focus": "step:42"
}
```

**ConcurrentDriverWarning:**
```python
{
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",  # ULID triggering warning
  "conflicting_participants": [
    {
      "participant_id": "01HQRS8ZMBE6XYZ0000000002",
      "focus": "wp:WP01",
      "drive_intent": "active",
      "last_activity_at": "2026-02-15T10:00:00Z"
    }
  ],
  "severity": "high",
  "collision_type": "concurrent_driver_same_focus"
}
```

**WarningAcknowledged:**
```python
{
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",  # ULID
  "warning_event_id": "01HQRS8ZMBE6XYZABC0123XYZ",  # ULID of warning event
  "action": "continue",  # continue|hold|reassign|defer
  "reason": "Will coordinate manually with Alice"
}
```

**CommentPosted:**
```python
{
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",  # ULID
  "text": "Blocked on API design decision",
  "focus_context": "wp:WP01",  # Mission-level if focus=none
  "comment_id": "01HQRS8ZMBE6XYZABC0123CMT"  # ULID
}
```

**DecisionCaptured:**
```python
{
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",  # ULID
  "decision_text": "Approved: use REST API for now",
  "focus_context": "step:42",
  "decision_id": "01HQRS8ZMBE6XYZABC0123DEC"  # ULID
}
```

**Relationships:**
- Emitted by 1 Participant (via participant_id in payload)
- Scoped to 1 MissionRun (via aggregate_id=mission_id)
- May reference 1 causation Event (via causation_id)

**Ordering:**
- Lamport clock provides total order (logical time)
- Causation chain provides causal order (event_id → causation_id)
- Timestamp provides wall-clock order (human-readable, not used for ordering)

**Invariants:**
- event_id MUST be ULID (26 chars)
- causation_id MUST be ULID (26 chars) if present
- aggregate_id MUST be mission_id
- participant_id in payload MUST be SaaS-minted (validated on SaaS replay)
- Lamport clock MUST monotonically increase per node

---

### SessionState

**Description:** Per-mission CLI session state (local cache of participant identity).

**Storage:** `~/.spec-kitty/missions/<mission_id>/session.json` (filesystem, per mission)

**Attributes:**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `mission_id` | `str` | Mission identifier | Required, unique |
| `participant_id` | `str` | SaaS-minted ULID | Required, 26 chars |
| `role` | `enum` | developer, reviewer, observer, stakeholder | Required |
| `joined_at` | `datetime` | ISO timestamp when joined | Required, immutable |
| `last_activity_at` | `datetime` | ISO timestamp of last command | Required, updated on events |
| `drive_intent` | `enum` | active, inactive | Required, default: inactive |
| `focus` | `str | None` | none, wp:<id>, step:<id> | Optional, nullable |

**Relationships:**
- Represents 1 Participant in 1 MissionRun
- One file per mission (isolated state)

**Lifecycle:**
- Created on successful `mission join` (SaaS returns participant_id)
- Updated on every collaboration command (drive, focus, comment, decide)
- Read by pre-execution checks (collision detection)
- Deleted on mission completion or explicit cleanup (not implemented S1/M1)

**Invariants:**
- participant_id MUST match SaaS-issued value (no client-side generation)
- File MUST exist before any non-join collaboration command
- File permissions: 0600 (owner read/write only, security)

---

### ActiveMissionPointer

**Description:** CLI active mission pointer (fast lookup for commands omitting --mission flag).

**Storage:** `~/.spec-kitty/session.json` (filesystem, single file)

**Attributes:**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `active_mission_id` | `str | None` | Currently active mission_id | Optional, nullable |
| `last_switched_at` | `datetime` | ISO timestamp of last switch | Optional, nullable |

**Relationships:**
- Points to 0-1 MissionRun (active mission)

**Lifecycle:**
- Created/updated on `mission join` (sets active mission)
- Read by all collaboration commands (if --mission flag omitted)
- Cleared on mission leave (not implemented S1/M1)

**Invariants:**
- If active_mission_id is set, corresponding session file MUST exist in `missions/<mission_id>/session.json`
- S1/M1 scope: Only one active mission at a time (single mission focus)

---

## State Machines

### Drive Intent State Machine

**States:** `inactive`, `active`

**Transitions:**
```
     [set drive active]
inactive ───────────────────→ active
   ↑                            │
   │        [set drive inactive]│
   └────────────────────────────┘
```

**Transition Rules:**
- **inactive → active**:
  - Precondition: Participant joined mission (session.json exists)
  - Action: Run pre-execution checks (collision detection)
  - Event: DriveIntentSet (previous: inactive, new: active)
  - If collision detected: Prompt acknowledgement (continue|hold|reassign|defer)
  - If hold selected: Revert to inactive, emit WarningAcknowledged (action: hold)

- **active → inactive**:
  - No precondition (always allowed)
  - Event: DriveIntentSet (previous: active, new: inactive)
  - No collision check (setting inactive is safe)

**Invariants:**
- Cannot transition to same state (idempotent commands skip event emission)
- Execution commands require drive_intent=active (checked before execution)

---

### Focus State Machine

**States:** `none`, `wp:<id>`, `step:<id>`

**Transitions:**
```
          [focus set wp:WP01]
none ────────────────────────→ wp:WP01
   ↑                               │
   │                               │ [focus set step:42]
   │                               └─────────────────→ step:42
   │                                                      │
   │            [focus set none or change to different]  │
   └──────────────────────────────────────────────────────┘
```

**Transition Rules:**
- **none → wp:<id>**:
  - Precondition: wp_id exists in mission
  - Event: FocusChanged (previous: none, new: wp:<id>)

- **wp:<id> → step:<id>**:
  - Precondition: step_id exists in mission, parent_wp_id matches or step is in different WP
  - Event: FocusChanged (previous: wp:<id>, new: step:<id>)

- **wp:<id> → wp:<id2>**:
  - Implicit release of wp:<id>
  - Event: FocusChanged (previous: wp:<id>, new: wp:<id2>)

- **step:<id> → none**:
  - Explicit unfocus
  - Event: FocusChanged (previous: step:<id>, new: none)

**Invariants:**
- Focus change implicitly releases previous focus (no orphaned claims)
- Setting same focus twice is idempotent (no event emission)
- Focus validation: CLI checks wp_id/step_id existence (reject invalid focus)

---

### Participant Status State Machine

**States:** `joining`, `joined`, `active`, `inactive`, `left`

**Transitions:**
```
joining → joined → active ⇄ inactive → left
                     ↓
                  (timeout, not S1/M1)
```

**Transition Rules:**
- **joining → joined**:
  - Action: SaaS join API returns participant_id
  - Event: None (SaaS-side event, not CLI-emitted)

- **joined → active**:
  - Action: First event emission (ParticipantJoined)
  - CLI writes session.json with participant_id

- **active ⇄ inactive**:
  - Action: Set drive_intent (see Drive Intent State Machine)
  - Event: DriveIntentSet

- **active → left**:
  - Action: Explicit leave command (not implemented S1/M1)
  - Event: ParticipantLeft (not emitted in S1/M1)

**Invariants:**
- Cannot skip states (must progress linearly)
- Cannot return to joined after leaving
- Timeout transition (active → inactive) not implemented in S1/M1

---

## Relationships Diagram

```
MissionRun (1) ──────────── (*) Participant
    │                            │
    │ contains                   │ emits
    │                            │
    ▼                            ▼
WorkPackage (*)            CollaborationEvent (*)
    │                            │
    │ contains                   │ scoped to
    │                            │
    ▼                            ▼
PromptStep (*)              MissionRun (1)


Participant (1) ─── focus on ─→ WorkPackage (0-1)
                                     or
                                PromptStep (0-1)


Participant (1) ─── cached in ─→ SessionState (1)
                                     │
                                     │ indexed by
                                     │
                                     ▼
                              ActiveMissionPointer (1)
```

**Cardinality:**
- MissionRun : Participant = 1:N (one mission, many participants)
- MissionRun : WorkPackage = 1:N (one mission, many work packages)
- WorkPackage : PromptStep = 1:N (one WP, many steps)
- Participant : CollaborationEvent = 1:N (one participant, many events emitted)
- Participant : WorkPackage/PromptStep = N:0-1 (many participants can focus on zero or one WP/step)
- Participant : SessionState = 1:1 (per-mission identity cache)
- SessionState : ActiveMissionPointer = N:1 (many mission sessions, one active pointer)

---

## Invariants & Constraints

### Global Invariants

1. **SaaS-Authoritative Participation**:
   - participant_id MUST be minted by SaaS (CLI cannot invent IDs)
   - participant_id MUST be bound to auth_principal (one-to-one per mission)
   - Event payload participant_id MUST be validated against SaaS roster on replay

2. **ULID Identifiers**:
   - event_id, causation_id, participant_id MUST be ULIDs (26 chars)
   - ULID generation MUST use monotonic time (sortable by creation order)

3. **Event Ordering**:
   - Local queue MUST preserve append order (JSONL file, no reordering)
   - Lamport clock MUST monotonically increase per node
   - Causation chain MUST be acyclic (no circular causation)

4. **Soft Coordination**:
   - Collision warnings MUST NOT block execution (advisory only)
   - Acknowledgement action MUST be recorded (continue|hold|reassign|defer)
   - Warnings MUST be emitted before state-changing operations

5. **Session State Integrity**:
   - session.json MUST exist before non-join collaboration commands
   - participant_id in session.json MUST match SaaS-issued value
   - File permissions MUST be 0600 (owner read/write only)

6. **Role-Based Permissions**:
   - Execution commands REQUIRE: can_execute=true AND drive_intent=active
   - llm_actor MUST NOT be accepted as join role (adapter-only identity)
   - participant_type is metadata only (does NOT affect permissions)

### Entity-Specific Constraints

**Participant:**
- role ∈ {developer, reviewer, observer, stakeholder} (exactly 4 join roles)
- participant_type ∈ {human, llm_context, service}
- drive_intent ∈ {active, inactive}
- focus ∈ {none, wp:<valid_id>, step:<valid_id>}
- Capability matrix MUST be derived from role (not stored separately)

**CollaborationEvent:**
- event_id length = 26 (ULID)
- causation_id length = 26 if present (ULID)
- aggregate_id = mission_id (primary stream key)
- lamport_clock >= 0 and monotonic per node
- Event type MUST be one of 14 canonical types (feature 006 contract)

**SessionState:**
- File path: `~/.spec-kitty/missions/<mission_id>/session.json`
- File permissions: 0600
- participant_id length = 26 (ULID)
- joined_at <= last_activity_at (temporal ordering)

**ActiveMissionPointer:**
- File path: `~/.spec-kitty/session.json`
- active_mission_id MUST correspond to existing session file (referential integrity)
- S1/M1: Only one active mission at a time

---

## Data Flow

### Join Mission Flow

```
1. User: spec-kitty mission join mission-abc-123 --role developer
2. CLI: Validate role ∈ {developer, reviewer, observer, stakeholder}
3. CLI: POST /api/v1/missions/{mission_id}/participants (SaaS join API)
4. SaaS: Validate auth_principal, mint participant_id (ULID)
5. SaaS: Return {participant_id, role, session_token}
6. CLI: Write ~/.spec-kitty/missions/mission-abc-123/session.json
7. CLI: Update ~/.spec-kitty/session.json (active_mission_id)
8. CLI: Emit ParticipantJoined event to local queue
9. CLI: Attempt SaaS delivery (if online)
10. CLI: Display success + role capabilities
```

### Set Drive Active Flow (with Collision)

```
1. User: spec-kitty mission drive set --state active
2. CLI: Load session.json (get participant_id, current focus)
3. CLI: Load collaboration/state.py (materialized view of mission roster)
4. CLI: Run collision detection (check for other active drivers on same focus)
5. CLI: Detect collision (Alice has drive=active, focus=wp:WP01)
6. CLI: Emit ConcurrentDriverWarning event
7. CLI: Prompt acknowledgement (continue|hold|reassign|defer)
8. User: Select [h] hold
9. CLI: Emit WarningAcknowledged event (action: hold)
10. CLI: Keep drive_intent=inactive (do NOT change state)
11. CLI: Display advisory message + Alice's last activity timestamp
```

### Offline → Online Replay Flow

```
1. User: (offline) spec-kitty mission focus set wp:WP01
2. CLI: Append FocusChanged event to ~/.spec-kitty/events/mission-abc-123.jsonl
3. CLI: Mark event as pending_replay (SaaS delivery failed)
4. User: (offline) spec-kitty mission drive set --state active
5. CLI: Append DriveIntentSet event, mark pending_replay
6. User: (reconnects to network)
7. User: spec-kitty mission status (or any online command)
8. CLI: Detect pending_replay events (read from JSONL)
9. CLI: POST /api/v1/events/batch/ (batch send 2 events)
10. SaaS: Validate participant_id in roster for each event
11. SaaS: Accept valid events, return accepted event_ids
12. CLI: Mark events as delivered, update JSONL metadata
13. CLI: Display status (merged state from replayed events)
```

---

## Storage Schema

### Event Queue File Format

**Path:** `~/.spec-kitty/events/<mission_id>.jsonl`

**Format:** Newline-delimited JSON (JSONL)

**Example:**
```json
{"event_id":"01HQRS8ZMBE6XYZABC0123001","event_type":"ParticipantJoined","aggregate_id":"mission-abc-123","payload":{"participant_id":"01HQRS8ZMBE6XYZ0000000001","role":"developer","participant_type":"human"},"timestamp":"2026-02-15T10:00:00Z","node_id":"cli-alice-macbook","lamport_clock":1,"causation_id":null,"_replay_status":"delivered"}
{"event_id":"01HQRS8ZMBE6XYZABC0123002","event_type":"FocusChanged","aggregate_id":"mission-abc-123","payload":{"participant_id":"01HQRS8ZMBE6XYZ0000000001","previous_focus":"none","new_focus":"wp:WP01"},"timestamp":"2026-02-15T10:05:00Z","node_id":"cli-alice-macbook","lamport_clock":2,"causation_id":"01HQRS8ZMBE6XYZABC0123001","_replay_status":"pending"}
```

**Metadata Fields (CLI-specific, not in canonical envelope):**
- `_replay_status`: "pending" | "delivered" | "failed"
- `_retry_count`: Number of replay attempts (if failed)
- `_last_retry_at`: ISO timestamp of last retry attempt

**Operations:**
- **Append**: O(1) - Append new event to end of file (no seeking)
- **Read**: O(n) - Scan file line-by-line (JSONL format)
- **Replay**: Filter by `_replay_status="pending"`, batch send to SaaS

---

### Session State File Format

**Path:** `~/.spec-kitty/missions/<mission_id>/session.json`

**Format:** JSON

**Example:**
```json
{
  "mission_id": "mission-abc-123",
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",
  "role": "developer",
  "joined_at": "2026-02-15T10:00:00Z",
  "last_activity_at": "2026-02-15T10:30:00Z",
  "drive_intent": "active",
  "focus": "wp:WP01"
}
```

**Operations:**
- **Create**: On successful join (atomic write)
- **Update**: On every collaboration command (atomic read-modify-write)
- **Read**: On pre-execution checks (collision detection)

---

### Active Mission Pointer File Format

**Path:** `~/.spec-kitty/session.json`

**Format:** JSON

**Example:**
```json
{
  "active_mission_id": "mission-abc-123",
  "last_switched_at": "2026-02-15T10:00:00Z"
}
```

**Operations:**
- **Create/Update**: On mission join (set active)
- **Read**: On every collaboration command (if --mission flag omitted)

---

## Migration Notes

**S1/M1 Scope:**
- This data model is greenfield (2.x branch, no 1.x compatibility)
- No migration from 1.x required (1.x uses YAML activity logs, not collaboration events)

**Future Extensions (post-S1/M1):**
- Multi-mission support: Active mission pointer becomes list
- Presence heartbeat: Periodic background event emission
- Participant invite/leave: Full lifecycle management
- Stale participant detection: Timeout-based inactive transitions

**Schema Evolution:**
- Event schemas owned by feature 006 (semantic versioning)
- CLI must handle schema_version gracefully (future-proof)
- Payload structure may change (feature 006 contract alignment)

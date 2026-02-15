# Mission Collaboration CLI with Soft Coordination

## Overview

This feature adds mission collaboration commands to the spec-kitty CLI, enabling multiple developers to work concurrently on the same mission with advisory collision warnings instead of blocking locks. The system implements a "soft coordination" model where drive intent is organic and fluid, not an exclusive ownership lease.

**Sprint Context:** S1/M1 Step 1 - Observe+Decide behavior with canonical event emission and advisory warnings.

**Key Capabilities:**
- Join missions with role-based capabilities (developer, reviewer, observer, stakeholder)
- Declare focus (work package or prompt step) and drive intent (active/inactive)
- Receive pre-execution collision warnings with acknowledgement flow
- Emit collaboration events to local queue with offline replay support
- Adapter-ready design for Gemini and Cursor agents (baseline plumbing)

## Problem Statement

Current spec-kitty CLI lacks collaboration primitives. Multiple developers working on the same mission face:

1. **Collision blindness**: No visibility into other developers' active work areas
2. **Coordination overhead**: Manual Slack/email coordination required to avoid conflicts
3. **Context loss**: No record of who worked on what, when, and why
4. **Handoff friction**: Explicit lock release required for role transitions
5. **Offline gaps**: Network interruptions cause coordination state loss

Traditional hard-lock models impose rigid ownership that conflicts with organic, fluid development workflows. Developers need advisory coordination that warns without blocking, preserving autonomy while reducing collision risk.

## Goals

1. **Collaboration Commands**: Implement 6 core CLI commands for mission participation, focus/drive management, and decision capture
2. **Canonical Events**: Emit 14 collaboration event types using spec-kitty-events (feature 006) canonical envelope
3. **Advisory Checks**: Pre-execution collision detection (concurrent drivers, stale context, dependency conflicts)
4. **Acknowledgement Flow**: Prompt users with continue|hold|reassign|defer options when collisions detected
5. **Offline-First**: Local durable event queue with replay on reconnect
6. **Adapter Interface**: Protocol-based design for Gemini/Cursor observe+decide integration (stubs shipped in S1/M1)

## Non-Goals

1. **Hard Locks**: No exclusive ownership enforcement as default behavior
2. **Full Policy Matrix**: Role capabilities are fixed for S1/M1 (tenant customization deferred)
3. **Real-time Sync**: SaaS WebSocket delivery is best-effort (local queue is authoritative)
4. **Production Adapter Hardening**: Gemini/Cursor adapters ship as tested stubs (full hardening continues post-S1/M1)

## User Scenarios & Testing

### Scenario 1: Concurrent Development (Happy Path)

**Context:** Alice (developer) and Bob (developer) join mission "mission-abc-123" to work on different work packages.

**Flow:**
1. Alice runs `spec-kitty mission join mission-abc-123 --role developer`
2. Bob runs `spec-kitty mission join mission-abc-123 --role developer`
3. Alice runs `spec-kitty mission focus set wp:WP01 && spec-kitty mission drive set --state active`
4. Bob runs `spec-kitty mission focus set wp:WP02 && spec-kitty mission drive set --state active`
5. Both developers work concurrently without warnings

**Expected Outcome:**
- Both participants appear in `spec-kitty mission status` output
- No collision warnings (different focus targets)
- Events: 2× ParticipantJoined, 2× FocusChanged, 2× DriveIntentSet

**Success Criteria:**
- Mission status displays all active participants with current focus/drive state
- No false-positive warnings when focus targets differ

---

### Scenario 2: Collision Warning with Acknowledgement

**Context:** Alice (developer) is actively working on WP01. Bob (developer) attempts to start work on the same work package.

**Flow:**
1. Alice already has `focus=wp:WP01` and `drive_intent=active`
2. Bob runs `spec-kitty mission focus set wp:WP01`
3. Bob runs `spec-kitty mission drive set --state active`
4. CLI detects collision and displays warning:
   ```
   ⚠️  ConcurrentDriverWarning
   Alice is actively driving wp:WP01 (since 10 minutes ago)

   Choose action:
   [c] Continue (work in parallel, high collision risk)
   [h] Hold (set drive=inactive, observe only)
   [r] Reassign (advisory suggestion to Alice)
   [d] Defer (exit without state change)
   ```
5. Bob selects `[h]` (hold)
6. Bob's drive_intent remains inactive, focus set to WP01 (observer mode)

**Expected Outcome:**
- Collision detected before execution starts
- User prompted with 4 acknowledgement options
- WarningAcknowledged event emitted with selected action
- Bob can still comment and observe, but not execute

**Success Criteria:**
- Collision warnings trigger reliably when 2+ participants have same focus + active drive
- Acknowledgement choice is captured in event stream
- CLI respects selected action (hold prevents execution commands)

---

### Scenario 3: Organic Handoff Without Lock Release

**Context:** Alice (developer) finishes work on WP01 and moves to WP02. Bob (developer) wants to take over WP01.

**Flow:**
1. Alice runs `spec-kitty mission focus set wp:WP02` (implicitly releases WP01)
2. Alice's drive_intent remains active, but focus changed
3. Bob runs `spec-kitty mission focus set wp:WP01 && spec-kitty mission drive set --state active`
4. No collision warning (Alice no longer focused on WP01)
5. Bob becomes active driver for WP01 without explicit lock acquisition

**Expected Outcome:**
- No explicit "release lock" command required
- Focus change implicitly signals availability
- Mission status shows Alice on WP02, Bob on WP01

**Success Criteria:**
- Handoff completes without coordination overhead (no explicit release)
- New driver can claim abandoned focus target immediately
- Event stream preserves handoff sequence (Alice focus change → Bob focus change + drive set)

---

### Scenario 4: Offline Replay Preserves Context

**Context:** Charlie (developer) works offline for 30 minutes, then reconnects. Meanwhile, Alice made progress.

**Flow:**
1. Charlie loses network connection at T0
2. Charlie runs 5 commands offline (join, focus set, drive set, comment × 2)
3. Events queued locally (not delivered to SaaS)
4. Alice runs 3 commands online (focus set, drive set, comment)
5. Charlie reconnects at T0+30min
6. CLI replays Charlie's 5 queued events to SaaS
7. Charlie runs `spec-kitty mission status` and sees merged state (Alice + Charlie events)

**Expected Outcome:**
- Offline commands succeed and append to local queue
- Reconnect triggers batch replay to SaaS
- Mission status reflects merged event stream (Lamport clock ordering)
- No event loss or duplication

**Success Criteria:**
- Local queue persists events across CLI invocations (durable storage)
- Replay preserves event order (causation_id chaining)
- Conflict warnings shown if replayed events reveal retroactive collisions

---

### Scenario 5: Gemini Adapter Emits Identical Events

**Context:** Developer uses Gemini agent via spec-kitty CLI. Events should match Claude/human-driven events.

**Flow:**
1. Gemini agent executes via `spec-kitty --agent gemini mission join mission-abc-123 --role developer`
2. Adapter calls `normalize_actor_identity(gemini_ctx)` → returns ActorIdentity(agent_type='gemini', user_id='dev@example.com')
3. ParticipantJoined event emitted with normalized identity
4. Gemini agent output parsed via `parse_observation(output)` → returns ObservationSignal(signal_type='step_started', step_id='step:42')
5. PromptStepExecutionStarted event emitted (identical schema to Claude/human events)

**Expected Outcome:**
- Gemini-driven events use same canonical envelope (event_type, aggregate_id, correlation_id)
- Mission status shows Gemini actor alongside human participants
- Collision detection works identically (Gemini vs. human on same focus → warning)

**Success Criteria:**
- Contract tests prove Gemini adapter produces identical event structure to Cursor adapter
- No provider-specific logic in mission command handlers
- Swapping `--agent gemini` to `--agent cursor` changes only adapter selection, not event schema

## Functional Requirements

### FR-1: Mission Join Command

**Command:** `spec-kitty mission join <mission_id> --role <role>`

**Behavior:**
- Validates mission_id exists (queries SaaS or local cache)
- Validates role is one of: developer, reviewer, observer, stakeholder
- Emits ParticipantJoined event with participant_id, role, timestamp
- Stores joined mission context in CLI session state (~/.spec-kitty/session.json)
- Returns success message with role capabilities summary

**Acceptance Criteria:**
- Rejects invalid mission_id with clear error message
- Rejects invalid role (must match role taxonomy)
- Supports offline join (event queued for replay)
- Multiple invocations are idempotent (duplicate joins ignored)

---

### FR-2: Focus Set Command

**Command:** `spec-kitty mission focus set <wp_id|step_id>`

**Behavior:**
- Validates wp_id or step_id exists in current mission
- Updates participant focus context
- Emits FocusChanged event with previous_focus, new_focus, timestamp
- Displays current focus in CLI prompt or status output

**Acceptance Criteria:**
- Rejects focus targets not in current mission
- Handles focus=none (explicit unfocus)
- Setting same focus twice is idempotent (no duplicate events)
- Focus change implicitly releases previous focus (no orphaned claims)

---

### FR-3: Drive Set Command

**Command:** `spec-kitty mission drive set --state <active|inactive>`

**Behavior:**
- Updates participant drive_intent state
- Emits DriveIntentSet event with previous_state, new_state, timestamp
- **Pre-execution check**: If setting active, run collision detection
  - Check for other participants with same focus + drive=active
  - Check for stale context (participant's last event timestamp > 30min ago with no PresenceHeartbeat)
  - Check for dependency collisions (driving step B while step A blocked)
- If collision detected, prompt acknowledgement flow (see FR-7)
- If no collision or user acknowledges, proceed with state change

**Acceptance Criteria:**
- Drive state persists across CLI invocations (session state)
- Pre-execution checks run before drive=active (not on drive=inactive)
- Collision warnings include actionable context (who, what, when)
- Offline mode skips pre-execution checks (warnings shown on replay)

---

### FR-4: Mission Status Command

**Command:** `spec-kitty mission status`

**Behavior:**
- Displays current mission participants with role, focus, drive state
- Shows last activity timestamp for each participant
- Highlights collisions (same focus + multiple active drivers)
- Includes mission metadata (mission_id, created_at, participant_count)

**Output Format:**
```
Mission: mission-abc-123
Participants: 3

DEVELOPER
  Alice (active)    wp:WP01    last: 2m ago
  Bob (inactive)    wp:WP02    last: 15m ago

REVIEWER
  Charlie (active)  step:42    last: 5m ago

⚠️  No active collisions
```

**Acceptance Criteria:**
- Displays all participants who have joined (even if drive=inactive)
- Highlights stale participants (last activity > 30min) with warning icon
- Shows collision summary at bottom (count of concurrent drivers per focus)

---

### FR-5: Comment Command

**Command:** `spec-kitty mission comment --text "Blocked on API design decision"`

**Behavior:**
- Emits CommentPosted event with participant_id, text, focus_context, timestamp
- Associates comment with current focus (if set) or mission-level (if focus=none)
- Supports multiline text (via stdin if --text omitted)
- Returns comment_id for reference in future decide commands

**Acceptance Criteria:**
- Comments longer than 500 characters are truncated with warning
- Empty text rejected (must have non-whitespace content)
- Focus context captured automatically (no explicit --focus flag)
- Offline comments queued for replay (not lost)

---

### FR-6: Decide Command

**Command:** `spec-kitty mission decide --text "Approved: use REST API for now"`

**Behavior:**
- Emits DecisionCaptured event with participant_id, decision_text, focus_context, timestamp
- Requires role capability can_decide (developer, reviewer, stakeholder only)
- Associates decision with current focus (work package or step level)
- Returns decision_id for provenance tracking

**Acceptance Criteria:**
- Rejects decision from observer role (lacks can_decide capability)
- Decision text supports markdown formatting (stored as-is, rendered in SaaS UI)
- Decisions linked to focus are retrievable via mission status --verbose

---

### FR-7: Collision Warning & Acknowledgement Flow

**Trigger:** Pre-execution check in drive set --state active (or execution commands like spec-kitty agent execute)

**Behavior:**
1. Detect collision condition:
   - **High severity (ConcurrentDriverWarning)**: Same focus + 2+ active drivers
   - **Medium severity (PotentialStepCollisionDetected)**: Same focus + 1 active driver
   - **Medium severity**: Active drivers on dependency-linked steps
2. Display warning with context:
   - Collision type and severity
   - Conflicting participant(s) with last activity timestamp
   - Current state snapshot (focus, drive, last command)
3. Prompt acknowledgement choice:
   - `[c] Continue` - Proceed with active drive (parallel work, accept risk)
   - `[h] Hold` - Set drive=inactive (observer mode)
   - `[r] Reassign` - Advisory suggestion to conflicting participant (emit reassign comment)
   - `[d] Defer` - Exit without state change
4. Emit WarningAcknowledged event with selected action
5. Execute action (update drive state, emit reassign comment, or exit)

**Acceptance Criteria:**
- Warnings appear before any state-changing operation (preventive, not reactive)
- Acknowledgement prompt blocks CLI until user responds (no default auto-continue)
- Selected action is auditable (appears in event stream with timestamp)
- Reassign action emits CommentPosted with @mention to conflicting participant

---

### FR-8: Canonical Event Emission

**Event Types (14 total):**
- ParticipantInvited, ParticipantJoined, ParticipantLeft, PresenceHeartbeat
- DriveIntentSet, FocusChanged
- PromptStepExecutionStarted, PromptStepExecutionCompleted
- ConcurrentDriverWarning, PotentialStepCollisionDetected, WarningAcknowledged
- CommentPosted, DecisionCaptured, SessionLinked

**Canonical Envelope (spec_kitty_events.models.Event):**
```python
{
  "event_id": "uuid-v4",
  "event_type": "DriveIntentSet",
  "aggregate_id": "mission-abc-123",  # mission_id
  "correlation_id": "run-xyz-789",    # mission_run_id (session correlation)
  "payload": {
    "participant_id": "alice@example.com",
    "previous_state": "inactive",
    "new_state": "active",
    "focus_context": "wp:WP01"
  },
  "timestamp": "2026-02-15T10:30:00Z",
  "node_id": "cli-alice-macbook",
  "lamport_clock": 42,
  "causation_id": "event-uuid-causing-this",
  "project_uuid": "proj-uuid",
  "project_slug": "spec-kitty",
  "schema_version": "2.0",
  "data_tier": "collaboration"
}
```

**Behavior:**
- All commands emit events synchronously to local queue (durable append)
- Events written to ~/.spec-kitty/events/<mission_id>.jsonl (newline-delimited JSON)
- Lamport clock increments per event (logical ordering)
- Causation chain: Each event references triggering event_id (if applicable)

**Acceptance Criteria:**
- All 14 event types conform to canonical envelope schema
- Local queue survives CLI crashes (durable filesystem storage)
- Lamport clock provides total order (even across offline/online transitions)
- SaaS batch replay accepts event batches without schema validation errors

---

### FR-9: Offline Queue & Replay

**Behavior:**
- **Local Queue**: Events append to ~/.spec-kitty/events/<mission_id>.jsonl immediately
- **Online Check**: Each command attempts SaaS delivery (WebSocket or HTTP POST)
- **Offline Detection**: If delivery fails (network error, timeout), mark event as pending_replay
- **Replay Trigger**: On next successful online command, batch-send all pending_replay events
- **Replay Endpoint**: POST to SaaS /api/v2/events/batch with event array
- **Replay Confirmation**: SaaS returns accepted event_ids, CLI marks as delivered

**Edge Cases:**
- **Concurrent Offline Users**: Lamport clocks may conflict on replay (SaaS resolves via timestamp tie-breaker)
- **Partial Replay Failure**: If batch replay partially fails, retry only failed events (idempotent event_id)
- **Stale Context Warning**: If replay reveals retroactive collision (user worked offline while others progressed), emit warning on next command

**Acceptance Criteria:**
- Offline commands succeed instantly (no network wait)
- Replay completes within 5 seconds for batches up to 100 events
- Event order preserved (Lamport clock + causation chain)
- CLI displays replay progress (e.g., "Syncing 12 pending events...")

---

### FR-10: Gemini & Cursor Adapter Interface

**Protocol:** `ObserveDecideAdapter` (Python Protocol in src/specify_cli/adapters/observe_decide.py)

**Required Methods:**
1. `normalize_actor_identity(runtime_ctx: dict) -> ActorIdentity`
   - Extracts agent type (gemini, cursor, claude), user identity
   - Returns ActorIdentity(agent_type: str, user_id: str, session_id: str)

2. `parse_observation(output: str | dict) -> list[ObservationSignal]`
   - Parses agent output (text or JSON) into structured signals
   - Returns list of ObservationSignal(signal_type, entity_id, metadata)
   - Signal types: step_started, step_completed, decision_requested, error_detected

3. `detect_decision_request(observation: ObservationSignal) -> DecisionRequestDraft | None`
   - Checks if observation contains decision request (e.g., "Should I continue with approach A?")
   - Returns DecisionRequestDraft(question, options, context) or None

4. `format_decision_answer(answer: str) -> str`
   - Formats decision answer for agent input (provider-specific formatting)
   - Returns formatted string (e.g., Gemini JSON vs. Cursor markdown)

5. `healthcheck() -> AdapterHealth`
   - Checks adapter prerequisites (API keys, network connectivity)
   - Returns AdapterHealth(status: ok|degraded|unavailable, message: str)

**Adapter Registration:**
```python
from specify_cli.adapters import register_adapter, get_adapter

register_adapter("gemini", GeminiObserveDecideAdapter())
register_adapter("cursor", CursorObserveDecideAdapter())

adapter = get_adapter("gemini")  # Returns GeminiObserveDecideAdapter instance
```

**Command Handler Integration:**
```python
# In mission command handlers
adapter = get_adapter(cli_args.agent)  # e.g., --agent gemini
actor_identity = adapter.normalize_actor_identity(runtime_ctx)
# Emit ParticipantJoined with actor_identity...
```

**Acceptance Criteria:**
- No provider-specific logic in mission command handlers (adapter abstraction enforced)
- Swapping --agent gemini to --agent cursor changes only adapter instance
- Contract tests prove both adapters emit identical canonical events for same input
- Stubs ship with basic implementations (full error handling deferred to post-S1/M1)

## Success Criteria

1. **Concurrent Collaboration**: 3 participants join same mission, set drive=active on different work packages, and work simultaneously without false-positive warnings (measured: 0 warnings when focus differs)

2. **Collision Detection Accuracy**: When 2 participants set drive=active on same focus target, warning triggers 100% of time within 500ms of second participant's command execution (measured: warning latency p99 < 500ms)

3. **Organic Handoff Efficiency**: Participant A changes focus from WP01 to WP02, Participant B claims WP01 within 30 seconds without coordination overhead (measured: 0 explicit lock release commands, handoff latency < 30s)

4. **Offline Resilience**: Participant works offline for 30 minutes (50 commands executed), reconnects, and all events replay successfully within 10 seconds with preserved order (measured: 100% replay success rate, replay latency p95 < 10s)

5. **Adapter Equivalence**: Gemini and Cursor adapters emit events with identical structure for same input scenario (measured: 0 schema differences in contract test suite with 20 recorded scenarios)

6. **Event Integrity**: All 14 event types conform to canonical envelope schema without validation errors (measured: 0 schema validation failures in SaaS ingestion for 1000+ events generated by S1/M1 E2E tests)

7. **Acknowledgement Capture**: When collision warning triggers, user acknowledgement choice is captured in event stream within 1 second of selection (measured: WarningAcknowledged event emission latency p99 < 1s)

## Key Entities

### MissionRun
**Description:** Runtime collaboration/execution container (replaces deprecated "Feature" term)

**Attributes:**
- mission_id (primary key, UUID or slug)
- mission_run_id (session correlation key)
- created_at (ISO timestamp)
- status (active, completed, cancelled)
- participant_count (integer)

**Relationships:**
- Contains 1+ WorkPackages
- Has 1+ Participants

---

### WorkPackage
**Description:** Mission-local execution unit (coarser than PromptStep)

**Attributes:**
- wp_id (primary key within mission, e.g., "WP01")
- title (string)
- status (pending, in_progress, for_review, done)
- dependencies (list of wp_ids)

**Relationships:**
- Belongs to 1 MissionRun
- Contains 1+ PromptSteps
- May have 1+ active Participants (with focus=wp:<id>)

---

### PromptStep
**Description:** Atomic execution step within work package (finest granularity)

**Attributes:**
- step_id (primary key within work package, e.g., "step:42")
- prompt_text (string, markdown)
- status (pending, running, completed, failed)
- parent_wp_id (foreign key to WorkPackage)

**Relationships:**
- Belongs to 1 WorkPackage
- May have 1+ active Participants (with focus=step:<id>)

---

### Participant
**Description:** Developer, reviewer, observer, or stakeholder in a mission

**Attributes:**
- participant_id (user email or agent identifier)
- role (developer, reviewer, observer, stakeholder, llm_actor)
- drive_intent (active, inactive)
- focus (none, wp:<id>, step:<id>)
- last_activity_at (ISO timestamp)
- capabilities (can_focus, can_drive, can_execute, can_ack_warning, can_comment, can_decide)

**Relationships:**
- Participates in 1 MissionRun
- May focus on 1 WorkPackage or 1 PromptStep (or none)

---

### CollaborationEvent
**Description:** Canonical event envelope (14 event types)

**Attributes:**
- event_id (UUID v4, primary key)
- event_type (ParticipantJoined, DriveIntentSet, FocusChanged, etc.)
- aggregate_id (mission_id)
- correlation_id (mission_run_id)
- payload (event-specific data)
- timestamp (ISO timestamp)
- lamport_clock (integer, logical ordering)
- causation_id (event_id of triggering event, nullable)
- node_id (CLI instance identifier)
- project_uuid, project_slug (project context)
- schema_version (e.g., "2.0")
- data_tier (e.g., "collaboration")

**Relationships:**
- Emitted by 1 Participant (via participant_id in payload)
- Scoped to 1 MissionRun (via aggregate_id)
- May reference 1 causation Event (via causation_id)

---

### ActorIdentity
**Description:** Normalized participant identity (human or LLM agent)

**Attributes:**
- agent_type (claude, gemini, cursor, human)
- user_id (email or username)
- session_id (CLI session UUID)

**Relationships:**
- Represents 1 Participant in events

---

### ObservationSignal
**Description:** Structured signal parsed from agent output

**Attributes:**
- signal_type (step_started, step_completed, decision_requested, error_detected)
- entity_id (wp_id or step_id)
- metadata (dict, provider-specific additional data)

**Relationships:**
- Parsed by 1 ObserveDecideAdapter
- Triggers 0-1 canonical CollaborationEvent

## Role and State Semantics

### Role Taxonomy (S1/M1 Default)

- **developer**: Execution-capable participant with full collaboration capabilities
- **reviewer**: Review-first participant, execution-capable for takeover/handoff scenarios
- **observer**: Non-execution participant with read-only visibility
- **stakeholder**: Non-execution participant with decision-input capability
- **llm_actor**: Recorded actor type for provenance/events (not a human CLI join role)

### Capability Model (Role → Permissions)

- **developer**: can_focus, can_drive, can_execute, can_ack_warning, can_comment, can_decide
- **reviewer**: can_focus, can_drive, can_execute, can_ack_warning, can_comment, can_decide
- **observer**: can_focus, can_comment (no execute/drive by default)
- **stakeholder**: can_comment, can_decide (no execute/drive by default)

**Policy Note:** Capabilities are policy-overridable per tenant in future sprints. Soft coordination remains default even with policy overrides.

### Drive vs Focus State Model

- **drive_intent**: Participant intent to actively execute (values: active|inactive)
- **focus**: Participant target context (values: none|wp:<id>|step:<id>)
- **Independence**: These are independent states - focus is "where I am", drive is "I am actively driving execution"

**Execution Precondition:**
Both conditions must be true:
1. Role has can_execute=true
2. Participant has drive_intent=active

### Collision/Warning Semantics

- **ConcurrentDriverWarning (high severity)**: Two participants with same focus and both drive=active
- **PotentialStepCollisionDetected (advisory, lower severity)**: Two participants with same focus, only one drive=active
- **PotentialStepCollisionDetected**: Two active drivers on different but dependency-linked steps

Warnings do not hard-block in default mode; acknowledgement is required to proceed.

### Reassign Behavior

- `reassign` in acknowledgement flow is an advisory coordination action, not a hard ownership transfer
- By default, only roles with can_ack_warning can issue reassign
- `observer` can comment/suggest reassignment, but cannot enforce it unless policy grants capability

## Dependencies

1. **Feature 006 (spec-kitty-events)**: Canonical event schemas, typed payload contracts, reducer semantics
   - **Status**: Event envelope defined, collaboration events planned but not implemented
   - **Risk**: CLI must upgrade to 2.x canonical envelope before emitting new events

2. **SaaS Event Ingestion**: Batch replay endpoint (/api/v2/events/batch) and WebSocket consumer
   - **Status**: Endpoints implemented and deployed to SaaS dev environment
   - **Risk**: Schema validation errors if CLI emits malformed events

3. **Existing CLI Infrastructure**: Session state management (~/.spec-kitty/session.json), agent invokers (gemini.py, cursor.py)
   - **Status**: Partial implementation (session state exists, invokers exist but lack observe+decide hooks)
   - **Risk**: Refactoring required to add adapter hooks without breaking existing commands

4. **Local Event Store**: Durable queue implementation (currently stub)
   - **Status**: store.py exists but lacks full queue/replay logic
   - **Risk**: New implementation required for offline resilience (not yet built)

## Assumptions

1. **Mission Identity**: MissionRun IDs are assigned by SaaS (not CLI-generated) via prior mission start/session service
   - **Implication**: CLI must query SaaS to validate mission_id before join (or cache valid IDs)

2. **Role Capabilities Fixed**: Role → capability mapping is hardcoded for S1/M1 (no tenant customization)
   - **Implication**: Policy engine deferred to future sprint (simplifies initial implementation)

3. **Soft Coordination Default**: No hard lock enforcement in S1/M1 (advisory warnings only)
   - **Implication**: Collision warnings can be ignored by user (system does not block execution)

4. **Gemini/Cursor Stubs Sufficient**: Baseline adapters ship with tested parsing for common scenarios (edge case handling deferred)
   - **Implication**: Production use may reveal gaps requiring post-S1/M1 hardening

5. **Local-First Authority**: CLI local queue is authoritative (SaaS is eventual consistency replica)
   - **Implication**: SaaS backend must handle out-of-order replay (Lamport clock + timestamp ordering)

6. **Feature Term Deprecated**: All new domain models use "Mission" terminology (Feature only for external backlog references)
   - **Implication**: Documentation, code comments, and event naming must avoid "Feature" (except legacy compatibility)

7. **Single Mission Focus**: Participants join one mission at a time (no multi-mission sessions in S1/M1)
   - **Implication**: CLI session.json stores one active mission_id (switching missions requires rejoin)

8. **Network Connectivity**: Offline mode assumes eventual reconnection (no indefinite offline operation)
   - **Implication**: Replay queue has unbounded growth potential (requires periodic cleanup in future)

## Out of Scope

1. **Hard Lock Enforcement**: Exclusive ownership leases, distributed locking, pessimistic concurrency control
2. **Full Policy Matrix**: Tenant-specific role customization, capability overrides, permission hierarchies
3. **Real-Time Presence**: Sub-second heartbeat intervals, live typing indicators, cursor sharing
4. **Multi-Mission Sessions**: Concurrent participation in 2+ missions from single CLI session
5. **Advanced Adapter Features**: Error recovery, retry logic, provider-specific optimizations (deferred to post-S1/M1)
6. **Event Retention Policies**: Automatic cleanup, archival, compression of old events
7. **Conflict Resolution UI**: Interactive merge tools, three-way diff, automated conflict resolution
8. **Audit & Compliance**: Tamper-proof event logs, cryptographic signatures, regulatory compliance features

## Open Questions

_None remaining - all clarifications resolved during discovery._

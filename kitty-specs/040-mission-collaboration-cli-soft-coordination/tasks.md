# Work Packages: Mission Collaboration CLI with Soft Coordination

**Feature**: 040-mission-collaboration-cli-soft-coordination
**Target Branch**: 2.x
**Sprint Context**: S1/M1 Step 1 - Observe+Decide behavior with canonical event emission and advisory warnings

## Overview

This feature implements mission collaboration commands for spec-kitty CLI, enabling multiple developers to work concurrently with advisory collision warnings (soft coordination). The system provides 6 CLI commands (join, focus set, drive set, status, comment, decide) that emit 14 canonical collaboration event types to a local durable queue with offline replay support.

**Total Work Packages**: 10
**Total Subtasks**: 40
**Estimated Lines of Code**: ~3,200

## Work Package Summary

| WP ID | Title | Subtasks | Est. Lines | Dependencies |
|-------|-------|----------|------------|--------------|
| WP01 | Foundation & Dependencies | 5 | ~300 | None |
| WP02 | Event Queue Infrastructure | 5 | ~400 | WP01 |
| WP03 | Session State Management | 4 | ~300 | WP01 |
| WP04 | Collaboration Service Core | 6 | ~450 | WP02, WP03 |
| WP05 | CLI Commands - Join & Focus | 3 | ~300 | WP04 |
| WP06 | CLI Commands - Drive, Status, Comment, Decide | 4 | ~350 | WP04 |
| WP07 | Adapter Implementations | 3 | ~250 | WP01 |
| WP08 | Unit & Domain Tests | 5 | ~400 | WP02, WP03, WP04, WP05, WP06, WP07 |
| WP09 | Integration Tests | 4 | ~350 | WP02, WP03, WP04 |
| WP10 | E2E Test | 1 | ~200 | All |

---

## WP01: Foundation & Dependencies

**Purpose**: Set up project dependencies, module structure, and core data models for collaboration system.

**Estimated Lines**: ~300
**Dependencies**: None (foundation)

### Subtasks

**T001: Add Python Dependencies** (~50 lines)
- Add `httpx` to pyproject.toml (SaaS API client)
- Add `ulid-py` to pyproject.toml (ULID generation)
- Add `spec-kitty-events` as Git dependency pinned to feature 006 prerelease commit
- Update uv.lock with new dependencies
- Verify imports work: `from spec_kitty_events.models import Event`

**T002: Create Module Structure** (~30 lines)
- Create `src/specify_cli/mission/` package with `__init__.py`
- Create `src/specify_cli/collaboration/` package with `__init__.py`
- Create `src/specify_cli/adapters/` package with `__init__.py`
- Create `src/specify_cli/events/` package with `__init__.py` (enhance existing)
- Add module docstrings explaining purpose and ownership

**T003: Define Event Queue Storage Models** (~80 lines)
- Create `src/specify_cli/events/models.py`
- Define `EventQueueEntry` dataclass:
  - `event: Event` (spec-kitty-events base model)
  - `replay_status: Literal["pending", "delivered", "failed"]`
  - `retry_count: int`
  - `last_retry_at: datetime | None`
- Add serialization helpers for queue records (`to_record()`, `from_record()`)
- Add type annotations with mypy --strict compliance

**T004: Define Session State Models** (~80 lines)
- Create `src/specify_cli/collaboration/models.py`
- Define `SessionState` dataclass:
  - `mission_id: str`
  - `mission_run_id: str` (ULID correlation ID from SaaS join response)
  - `participant_id: str` (ULID, SaaS-issued)
  - `role: Literal["developer", "reviewer", "observer", "stakeholder"]`
  - `joined_at: datetime`
  - `last_activity_at: datetime`
  - `drive_intent: Literal["active", "inactive"]`
  - `focus: str | None` (none, wp:<id>, step:<id>)
- Define `ActiveMissionPointer` dataclass:
  - `active_mission_id: str | None`
  - `last_switched_at: datetime | None`
- Add JSON serialization/deserialization methods
- Keep role as SaaS-provided metadata (no local capability gating in S1/M1)

**T005: Create ObserveDecideAdapter Protocol** (~60 lines)
- Create `src/specify_cli/adapters/observe_decide.py`
- Define `ActorIdentity` dataclass:
  - `agent_type: str` (claude, gemini, cursor, human)
  - `auth_principal: str` (email or OAuth subject)
  - `session_id: str` (ULID)
- Define `ObservationSignal` dataclass:
  - `signal_type: str` (step_started, step_completed, decision_requested, error_detected)
  - `entity_id: str` (wp_id or step_id)
  - `metadata: dict` (provider-specific)
- Define `DecisionRequestDraft` dataclass (optional for detection)
- Define `AdapterHealth` dataclass (status, message)
- Define `ObserveDecideAdapter` Protocol with 5 method signatures:
  - `normalize_actor_identity(runtime_ctx: dict) -> ActorIdentity`
  - `parse_observation(output: str | dict) -> list[ObservationSignal]`
  - `detect_decision_request(observation: ObservationSignal) -> DecisionRequestDraft | None`
  - `format_decision_answer(answer: str) -> str`
  - `healthcheck() -> AdapterHealth`

**Files Modified**:
- `pyproject.toml` (T001)
- `src/specify_cli/mission/__init__.py` (T002)
- `src/specify_cli/collaboration/__init__.py` (T002)
- `src/specify_cli/adapters/__init__.py` (T002)
- `src/specify_cli/events/__init__.py` (T002)
- `src/specify_cli/events/models.py` (T003)
- `src/specify_cli/collaboration/models.py` (T004)
- `src/specify_cli/adapters/observe_decide.py` (T005)

**Validation Criteria**:
- ✅ `uv sync` succeeds with new dependencies
- ✅ `from spec_kitty_events.models import Event` works
- ✅ All dataclasses have type annotations (mypy --strict passes)
- ✅ Protocol has 5 method signatures with correct types
- ✅ No import cycles (pytest import test passes)

---

## WP02: Event Queue Infrastructure

**Purpose**: Implement local durable event queue with ULID generation, queue-backed storage, Lamport clock, and SaaS replay transport.

**Estimated Lines**: ~400
**Dependencies**: WP01

### Subtasks

**T006: Implement ULID Generation Utility** (~50 lines)
- Create `src/specify_cli/events/ulid_utils.py`
- Implement `generate_event_id() -> str` using `ulid-py`
- Do not implement local participant ID generation (participant IDs are SaaS-minted at join)
- Add monotonic time validation (ensure sortable by creation order)
- Add unit tests: ULID format (26 chars), uniqueness (generate 1000 IDs, no duplicates)

**T007: Implement Event Queue Append** (~120 lines)
- Enhance `src/specify_cli/events/store.py`
- Implement `append_event(mission_id: str, event: Event, replay_status: str) -> None`:
  - Append mission-scoped rows to local queue storage (`EventStore` backend)
  - Serialize `EventQueueEntry` to queue record payload
  - Atomic write with file locking (fcntl.flock or equivalent)
  - Set file permissions to 0600 (owner read/write only)
- Implement `read_pending_events(mission_id: str) -> list[EventQueueEntry]`:
  - Read queue rows for mission
  - Parse each row to `EventQueueEntry`
  - Filter by `replay_status == "pending"`
- Add error handling: corrupted lines (log warning, skip line)

**T008: Implement Lamport Clock** (~80 lines)
- Create `src/specify_cli/events/lamport.py`
- Implement `LamportClock` class:
  - `__init__(self, node_id: str)`
  - `increment() -> int` (increment and return new value)
  - `update(received_clock: int) -> int` (max(local, received) + 1)
  - `current() -> int` (read without increment)
- Persist clock state to `~/.spec-kitty/events/lamport_clock.json` (per-node)
- Add unit tests: monotonic increment, update logic, persistence across restarts

**T009: Implement Replay Transport** (~100 lines)
- Create `src/specify_cli/events/replay.py`
- Implement `replay_pending_events(mission_id: str) -> dict`:
  - Read pending events from queue (call `store.read_pending_events()`)
  - Batch events (max 100 per request)
  - POST to `/api/v1/events/batch/` with httpx:
    - Payload: `{"events": [event1_dict, event2_dict, ...]}`
    - Headers: `Authorization: Bearer <session_token>`, `Content-Type: application/json`
  - Handle SaaS response: `{"accepted": [event_id1, ...], "rejected": [...]}`
  - Update queue: Mark accepted as "delivered", rejected as "failed"
- Add retry logic: Max 3 retries with exponential backoff (1s, 2s, 4s)
- Add error handling: Network timeout (10s), connection errors

**T010: Add Offline Detection and Queueing** (~50 lines)
- Enhance `src/specify_cli/events/store.py`
- Implement `emit_event(mission_id: str, event: Event) -> None`:
  - Append event to local queue with `replay_status="pending"`
  - Attempt SaaS delivery (call `replay.send_event_immediate()`)
  - If network error: Log warning, keep status="pending" (will replay later)
  - If success: Update status="delivered"
- Add helper: `is_online() -> bool` (quick connectivity check, e.g., ping SaaS health endpoint)

**Files Modified**:
- `src/specify_cli/events/ulid_utils.py` (T006)
- `src/specify_cli/events/store.py` (T007, T010)
- `src/specify_cli/events/lamport.py` (T008)
- `src/specify_cli/events/replay.py` (T009)

**Validation Criteria**:
- ✅ ULID generation produces 26-char strings, sortable by time
- ✅ Queue append is atomic and durable, with mission-scoped filtering
- ✅ Lamport clock increments monotonically, survives CLI restarts
- ✅ Replay batches up to 100 events, retries on network errors
- ✅ Offline mode appends to queue, online mode delivers immediately

---

## WP03: Session State Management

**Purpose**: Implement per-mission session state storage with atomic I/O, active mission pointer, and validation.

**Estimated Lines**: ~300
**Dependencies**: WP01

### Subtasks

**T011: Implement Session File I/O** (~100 lines)
- Create `src/specify_cli/collaboration/session.py`
- Implement `save_session_state(mission_id: str, state: SessionState) -> None`:
  - Write to `~/.spec-kitty/missions/<mission_id>/session.json`
  - Atomic write: Write to temp file, then rename (os.replace)
  - Set file permissions to 0600 (owner read/write only)
  - Create parent directory if missing (mkdir -p)
- Implement `load_session_state(mission_id: str) -> SessionState | None`:
  - Read from `~/.spec-kitty/missions/<mission_id>/session.json`
  - Parse JSON to `SessionState` dataclass
  - Return `None` if file missing or invalid (log warning)
- Add error handling: JSON parse errors, permission errors

**T012: Implement Per-Mission Session Storage** (~80 lines)
- Enhance `src/specify_cli/collaboration/session.py`
- Implement `update_session_state(mission_id: str, **updates) -> None`:
  - Load existing state (or fail if not joined)
  - Apply updates: `last_activity_at`, `drive_intent`, `focus`
  - Save updated state atomically
- Add helper: `ensure_joined(mission_id: str) -> SessionState`:
  - Load session state, raise error if not joined
  - Used by all non-join collaboration commands
- Add helper: `get_mission_dir(mission_id: str) -> Path`:
  - Return `~/.spec-kitty/missions/<mission_id>/`

**T013: Implement Active Mission Pointer** (~70 lines)
- Enhance `src/specify_cli/collaboration/session.py`
- Implement `set_active_mission(mission_id: str) -> None`:
  - Write to `~/.spec-kitty/session.json`
  - Payload: `{"active_mission_id": mission_id, "last_switched_at": now}`
  - Atomic write (temp file + rename)
- Implement `get_active_mission() -> str | None`:
  - Read from `~/.spec-kitty/session.json`
  - Return `active_mission_id` or `None`
- Add helper: `resolve_mission_id(explicit_id: str | None) -> str`:
  - If `explicit_id` provided, return it
  - Else return active mission (or raise error if none)

**T014: Add Session Validation** (~50 lines)
- Enhance `src/specify_cli/collaboration/session.py`
- Implement `validate_participant_id(participant_id: str) -> bool`:
  - Check ULID format (26 chars, alphanumeric)
  - Log warning if invalid format
- Implement `validate_session_integrity(state: SessionState) -> list[str]`:
  - Check `joined_at <= last_activity_at` (temporal ordering)
  - Check `participant_id` is valid ULID
  - Check `role` in allowed join roles
  - Check `focus` format (none, wp:<id>, step:<id>)
  - Return list of validation errors (empty if valid)
- Add pre-command check: Validate session before running collaboration commands

**Files Modified**:
- `src/specify_cli/collaboration/session.py` (T011, T012, T013, T014)

**Validation Criteria**:
- ✅ Session files created with permissions 0600
- ✅ Atomic writes (no partial state on crash)
- ✅ Active mission pointer survives CLI restarts
- ✅ Session validation catches malformed participant_id, temporal violations

---

## WP04: Collaboration Service Core

**Purpose**: Implement domain logic for join, focus, drive, collision detection, warnings, and state materialized view.

**Estimated Lines**: ~450
**Dependencies**: WP02, WP03

### Subtasks

**T015: Implement Join Mission Use-Case** (~90 lines)
- Create `src/specify_cli/collaboration/service.py`
- Implement `join_mission(mission_id: str, role: str, saas_api_url: str, auth_token: str) -> dict`:
  - Do not hardcode role taxonomy in CLI; pass role label to SaaS and rely on SaaS validation
  - POST `/api/v1/missions/{mission_id}/participants` with httpx:
    - Headers: `Authorization: Bearer {auth_token}`
    - Payload: `{"role": role}`
  - SaaS response: `{"participant_id": "01HQRS...", "session_token": "..."}`
  - Save session state: `session.save_session_state(mission_id, SessionState(...))`
  - Set active mission: `session.set_active_mission(mission_id)`
  - Emit `ParticipantJoined` event to local queue
  - Return: `{"participant_id": ..., "role": ...}`
- Add error handling: Network errors, SaaS validation errors (401, 403, 404)

**T016: Implement Set Focus Use-Case** (~70 lines)
- Enhance `src/specify_cli/collaboration/service.py`
- Implement `set_focus(mission_id: str, focus: str) -> None`:
  - Validate focus format: `wp:<id>` or `step:<id>` or `none`
  - Load session state: `state = session.ensure_joined(mission_id)`
  - If focus == current focus: Skip (idempotent)
  - Emit `FocusChanged` event: `previous_focus`, `new_focus`
  - Update session state: `session.update_session_state(mission_id, focus=focus)`
- Add helper: `validate_focus_format(focus: str) -> bool`

**T017: Implement Set Drive Use-Case** (~80 lines)
- Enhance `src/specify_cli/collaboration/service.py`
- Implement `set_drive(mission_id: str, intent: str) -> dict`:
  - Validate `intent` in {active, inactive}
  - Load session state: `state = session.ensure_joined(mission_id)`
  - If `intent` == current state: Skip (idempotent)
  - **Pre-execution check** (if `intent` == active):
    - Call `warnings.detect_collision(mission_id, state.focus)`
    - If collision detected: Return `{"collision": {...}, "action": None}`
    - Caller must handle acknowledgement flow (see T020)
  - Emit `DriveIntentSet` event: `participant_id`, `mission_id`, `intent`
  - Update session state: `session.update_session_state(mission_id, drive_intent=intent)`
  - Return: `{"status": "success", "drive_intent": intent}`

**T018: Implement Collision Detection** (~100 lines)
- Create `src/specify_cli/collaboration/warnings.py`
- Implement `detect_collision(mission_id: str, focus: str | None) -> dict | None`:
  - Load materialized view: `roster = state.get_mission_roster(mission_id)`
  - Filter active drivers: `[p for p in roster if p.drive_intent == "active" and p.focus == focus]`
  - If 2+ active drivers on same focus: Return `{"type": "ConcurrentDriverWarning", "severity": "high", "conflicting_participants": [...]}`
  - If 1 active driver (not self): Return `{"type": "PotentialStepCollisionDetected", "severity": "medium", ...}`
  - Else: Return `None` (no collision)
- Emit warning event: `ConcurrentDriverWarning` or `PotentialStepCollisionDetected`

**T019: Implement State Materialized View** (~80 lines)
- Create `src/specify_cli/collaboration/state.py`
- Implement `get_mission_roster(mission_id: str) -> list[SessionState]`:
  - Read all events from local queue: `store.read_all_events(mission_id)`
  - Build roster by replaying events:
    - `ParticipantJoined`: Add participant to roster
    - `FocusChanged`, `DriveIntentSet`: Update participant state
  - Cache roster in-memory (invalidate on new events)
  - Return list of `SessionState` for all participants
- Add helper: `get_participant_state(mission_id: str, participant_id: str) -> SessionState | None`

**T020: Implement Warning Acknowledgement Flow** (~30 lines)
- Enhance `src/specify_cli/collaboration/service.py`
- Implement `acknowledge_warning(mission_id: str, warning_id: str, acknowledgement: str) -> None`:
  - Validate action in {continue, hold, reassign, defer}
  - Emit `WarningAcknowledged` event: `participant_id`, `mission_id`, `warning_id`, `acknowledgement`
  - If action == "hold": Keep drive_intent=inactive
  - If action == "continue": Proceed with drive=active (caller re-invokes set_drive)
  - If action == "reassign": Emit `CommentPosted` with @mention to conflicting participant
  - If action == "defer": Exit without state change

**Files Modified**:
- `src/specify_cli/collaboration/service.py` (T015, T016, T017, T020)
- `src/specify_cli/collaboration/warnings.py` (T018)
- `src/specify_cli/collaboration/state.py` (T019)

**Validation Criteria**:
- ✅ Join mission calls SaaS API, stores participant_id, emits event
- ✅ Focus set validates format, emits event, updates session
- ✅ Drive set runs collision check before active transition
- ✅ Collision detection identifies 2+ drivers on same focus
- ✅ Materialized view replays events to build roster cache

---

## WP05: CLI Commands - Join & Focus

**Purpose**: Implement mission join and focus set CLI commands with typer integration.

**Estimated Lines**: ~300
**Dependencies**: WP04

### Subtasks

**T021: Implement Mission Join Command** (~120 lines)
- Add `mission join` handler to existing `src/specify_cli/cli/commands/mission.py`
- Implement `join_command(mission_id: str, role: str) -> None`:
  - Validate role argument (typer enum or manual validation)
  - Load SaaS config: API URL, auth token from env or config file
  - Call `service.join_mission(mission_id, role, saas_api_url, auth_token)`
  - Display success message with Rich:
    - "✅ Joined mission {mission_id} as {role}"
    - "Participant ID: {participant_id}"
    - "Role: {role}"
  - Handle errors: Network errors, auth errors, SaaS validation errors
- Add typer command registration:
  ```python
  @app.command(name="join")
  def join(
      mission_id: str,
      role: str = typer.Option(..., help="Participant role label (SaaS-validated)")
  ):
      join_command(mission_id, role)
  ```

**T022: Implement Mission Focus Set Command** (~120 lines)
- Add `mission focus set` handler to existing `src/specify_cli/cli/commands/mission.py`
- Implement `focus_set_command(focus: str, mission_id: str | None = None) -> None`:
  - Resolve mission_id: `mission_id = session.resolve_mission_id(mission_id)`
  - Validate focus format: `wp:<id>`, `step:<id>`, or `none`
  - Call `service.set_focus(mission_id, focus)`
  - Display success message:
    - "✅ Focus set to {focus}"
    - "Previous focus: {previous_focus}"
  - Handle errors: Not joined (clear error), invalid focus format
- Add typer command registration:
  ```python
  @app.command(name="set")
  def set_focus(
      focus: str = typer.Argument(..., help="Focus target: wp:<id>, step:<id>, or none"),
      mission_id: str | None = typer.Option(None, help="Mission ID (default: active mission)")
  ):
      focus_set_command(focus, mission_id)
  ```

**T027: Wire Command Routing in Existing Mission Command Module** (~60 lines)
- Extend `src/specify_cli/cli/commands/mission.py`
- Create typer app: `app = typer.Typer(name="mission", help="Mission collaboration commands")`
- Register collaboration subcommands on the existing `mission` Typer app:
  - `mission join`
  - `mission focus set`
  - `mission drive set`
  - `mission status`
  - `mission comment`
  - `mission decide`
- Keep registration through `src/specify_cli/cli/commands/__init__.py`

**Files Modified**:
- `src/specify_cli/cli/commands/mission.py` (T021, T022, T027)
- `src/specify_cli/cli/commands/__init__.py` (verify command registration unchanged)

**Validation Criteria**:
- ✅ `spec-kitty mission join mission-abc-123 --role developer` succeeds
- ✅ `spec-kitty mission focus set wp:WP01` validates format, emits event
- ✅ Commands display Rich-formatted success messages
- ✅ Error handling: Clear messages for not joined, network errors

---

## WP06: CLI Commands - Drive, Status, Comment, Decide

**Purpose**: Implement drive set, mission status, comment, and decide CLI commands.

**Estimated Lines**: ~350
**Dependencies**: WP04

### Subtasks

**T023: Implement Mission Drive Set Command** (~120 lines)
- Add `mission drive set` handler to existing `src/specify_cli/cli/commands/mission.py`
- Implement `drive_set_command(state: str, mission_id: str | None = None) -> None`:
  - Resolve mission_id: `mission_id = session.resolve_mission_id(mission_id)`
  - Validate state in {active, inactive}
  - Call `service.set_drive(mission_id, state)`
  - If collision detected (response["collision"]):
    - Display warning with Rich panel:
      - Collision type, severity, conflicting participants
      - Last activity timestamps
    - Prompt acknowledgement: `[c] Continue | [h] Hold | [r] Reassign | [d] Defer`
    - Read user input, call `service.acknowledge_warning(...)`
    - If action == "continue": Re-call `service.set_drive(...)` (bypass check)
  - Display success message: "✅ Drive intent set to {state}"
- Add typer command registration

**T024: Implement Mission Status Command** (~100 lines)
- Add `mission status` handler to existing `src/specify_cli/cli/commands/mission.py`
- Implement `status_command(mission_id: str | None = None, verbose: bool = False) -> None`:
  - Resolve mission_id
  - Load mission roster: `roster = state.get_mission_roster(mission_id)`
  - Display with Rich table:
    - Columns: Role, Participant ID (truncated), Focus, Drive, Last Activity
    - Group by role (DEVELOPER, REVIEWER, OBSERVER, STAKEHOLDER)
    - Highlight self (current participant) with green color
    - Highlight stale participants (last_activity > 30min ago) with yellow
  - Display collision summary: "⚠️ {count} active collisions" (same focus + multiple active drivers)
  - If verbose: Show full participant_id, session metadata
- Add typer command registration

**T025: Implement Mission Comment Command** (~70 lines)
- Add `mission comment` handler to existing `src/specify_cli/cli/commands/mission.py`
- Implement `comment_command(text: str | None = None, mission_id: str | None = None) -> None`:
  - Resolve mission_id
  - Load session state: `state = session.ensure_joined(mission_id)`
  - If text is None: Read from stdin (multi-line support)
  - Validate text: Non-empty after stripping whitespace, max 500 chars (warn if truncated)
  - Generate comment_id: ULID
  - Emit `CommentPosted` event: `participant_id`, `mission_id`, `comment_id`, `content`, optional `reply_to`
  - Display success: "✅ Comment posted (ID: {comment_id})"
- Add typer command registration

**T026: Implement Mission Decide Command** (~60 lines)
- Add `mission decide` handler to existing `src/specify_cli/cli/commands/mission.py`
- Implement `decide_command(text: str | None = None, mission_id: str | None = None) -> None`:
  - Resolve mission_id
  - Load session state: `state = session.ensure_joined(mission_id)`
  - Do not enforce local role capability gating; enforce joined-session + valid input only
  - If text is None: Read from stdin
  - Validate text: Non-empty, markdown supported
  - Generate decision_id: ULID
  - Emit `DecisionCaptured` event: `participant_id`, `mission_id`, `decision_id`, `topic`, `chosen_option`, optional `rationale`
  - Display success: "✅ Decision captured (ID: {decision_id})"
- Add typer command registration

**Files Modified**:
- `src/specify_cli/cli/commands/mission.py` (T023, T024, T025, T026)

**Validation Criteria**:
- ✅ Drive set displays collision warnings, prompts acknowledgement
- ✅ Status displays roster table with Rich formatting
- ✅ Comment accepts stdin input, validates length
- ✅ Decide validates input and emits canonical `DecisionCaptured` payload

---

## WP07: Adapter Implementations

**Purpose**: Implement Gemini and Cursor adapter stubs complying with ObserveDecideAdapter protocol.

**Estimated Lines**: ~250
**Dependencies**: WP01

### Subtasks

**T028: Implement GeminiObserveDecideAdapter Stub** (~100 lines)
- Create `src/specify_cli/adapters/gemini.py`
- Implement `GeminiObserveDecideAdapter` class:
  - `normalize_actor_identity(runtime_ctx: dict) -> ActorIdentity`:
    - Extract user email from `runtime_ctx["user_email"]`
    - Generate session_id ULID
    - Return `ActorIdentity(agent_type="gemini", auth_principal=email, session_id=session_id)`
  - `parse_observation(output: str | dict) -> list[ObservationSignal]`:
    - Parse Gemini JSON output (stub implementation):
      - Detect "step_started" if output contains "Starting step" text
      - Detect "step_completed" if output contains "Completed step" text
      - Extract entity_id from output (regex or JSON field)
    - Return list of `ObservationSignal`
  - `detect_decision_request(observation: ObservationSignal) -> DecisionRequestDraft | None`:
    - Stub: Return None (decision detection not implemented S1/M1)
  - `format_decision_answer(answer: str) -> str`:
    - Stub: Return answer wrapped in JSON: `{"decision": answer}`
  - `healthcheck() -> AdapterHealth`:
    - Check GEMINI_API_KEY env var exists
    - Return `AdapterHealth(status="ok", message="Gemini API key found")` or degraded
- Add docstrings explaining stub limitations

**T029: Implement CursorObserveDecideAdapter Stub** (~100 lines)
- Create `src/specify_cli/adapters/cursor.py`
- Implement `CursorObserveDecideAdapter` class (mirror Gemini structure):
  - `normalize_actor_identity`: Extract from Cursor runtime context
  - `parse_observation`: Parse Cursor markdown output (stub implementation)
  - `detect_decision_request`: Stub (return None)
  - `format_decision_answer`: Stub (return markdown formatted)
  - `healthcheck`: Check Cursor CLI availability (`which cursor` command)
- Add docstrings explaining stub limitations

**T030: Add Adapter Registry and Lookup** (~50 lines)
- Enhance `src/specify_cli/adapters/__init__.py`
- Implement `_registry: dict[str, ObserveDecideAdapter] = {}`
- Implement `register_adapter(name: str, adapter: ObserveDecideAdapter) -> None`:
  - Validate adapter implements protocol (runtime check)
  - Store in registry
- Implement `get_adapter(name: str) -> ObserveDecideAdapter`:
  - Lookup in registry, raise KeyError if not found
- Implement `list_adapters() -> list[str]`:
  - Return sorted list of registered adapter names
- Pre-register Gemini and Cursor adapters on module import

**Files Modified**:
- `src/specify_cli/adapters/gemini.py` (T028)
- `src/specify_cli/adapters/cursor.py` (T029)
- `src/specify_cli/adapters/__init__.py` (T030)

**Validation Criteria**:
- ✅ Both adapters implement all 5 protocol methods
- ✅ Healthcheck returns valid status (ok, degraded, unavailable)
- ✅ Parse observation returns well-formed `ObservationSignal` list
- ✅ Adapter registry lookup works, raises KeyError for unknown adapter

---

## WP08: Unit & Domain Tests

**Purpose**: Unit tests for all modules (commands, domain, adapters, events, session).

**Estimated Lines**: ~400
**Dependencies**: WP02, WP03, WP04, WP05, WP06, WP07

### Subtasks

**T031: Unit Tests for Event Queue** (~80 lines)
- Create `tests/specify_cli/events/test_store.py`
- Test `append_event`:
  - Appends to local queue store if missing
  - Appends event with correct format
  - Sets file permissions to 0600
  - Atomic write (no partial lines on simulated crash)
- Test `read_pending_events`:
  - Filters by replay_status="pending"
  - Handles corrupted lines (skips, logs warning)
- Test Lamport clock (in `test_lamport.py`):
  - Increment is monotonic
  - Update logic: max(local, received) + 1
  - Persistence across restarts

**T032: Unit Tests for Session Management** (~80 lines)
- Create `tests/specify_cli/collaboration/test_session.py`
- Test `save_session_state`:
  - Creates parent directory if missing
  - Atomic write (temp file + rename)
  - File permissions 0600
- Test `load_session_state`:
  - Returns None if file missing
  - Parses JSON correctly
  - Handles corrupted JSON (returns None, logs warning)
- Test `set_active_mission`, `get_active_mission`:
  - Survives CLI restarts
  - Atomic writes
- Test `validate_participant_id`, `validate_session_integrity`:
  - Catches malformed ULID (not 26 chars)
  - Catches temporal violations (joined_at > last_activity_at)

**T033: Unit Tests for Collaboration Domain** (~100 lines)
- Create `tests/specify_cli/collaboration/test_service.py`
- Test `join_mission`:
  - Calls SaaS API with correct payload
  - Saves session state with participant_id
  - Sets active mission pointer
  - Emits ParticipantJoined event
- Test `set_focus`:
  - Validates focus format
  - Idempotent (no duplicate events)
  - Updates session state
- Test `set_drive`:
  - Runs collision check on active transition
  - Returns collision dict if detected
  - Updates session state
- Create `tests/specify_cli/collaboration/test_warnings.py`
- Test `detect_collision`:
  - Detects 2+ active drivers on same focus (high severity)
  - Detects 1 active driver (medium severity)
  - Returns None if no collision

**T034: Unit Tests for CLI Commands** (~80 lines)
- Create `tests/specify_cli/cli/commands/test_mission_join.py`
- Test join command:
  - Validates role argument
  - Calls service.join_mission with correct args
  - Displays success message (check Rich output)
- Create `tests/specify_cli/cli/commands/test_mission_focus.py`
- Test focus set command:
  - Resolves mission_id from active pointer
  - Validates focus format
  - Displays success message
- Create `tests/specify_cli/cli/commands/test_mission_drive.py`
- Test drive set command:
  - Prompts acknowledgement if collision detected
  - Calls acknowledge_warning with user input
  - Re-calls set_drive if action=continue

**T035: Unit Tests for Adapters** (~60 lines)
- Create `tests/specify_cli/adapters/test_observe_decide.py`
- Test protocol compliance:
  - Both adapters implement all 5 methods
  - Methods return correct types (ActorIdentity, list[ObservationSignal], etc.)
- Create `tests/specify_cli/adapters/test_gemini.py`
- Test Gemini adapter:
  - normalize_actor_identity extracts email from runtime_ctx
  - parse_observation returns ObservationSignal list
  - healthcheck returns AdapterHealth with status
- Create `tests/specify_cli/adapters/test_cursor.py`
- Test Cursor adapter (mirror Gemini tests)

**Files Created**:
- `tests/specify_cli/events/test_store.py`
- `tests/specify_cli/events/test_lamport.py`
- `tests/specify_cli/collaboration/test_session.py`
- `tests/specify_cli/collaboration/test_service.py`
- `tests/specify_cli/collaboration/test_warnings.py`
- `tests/specify_cli/cli/commands/test_mission_join.py`
- `tests/specify_cli/cli/commands/test_mission_focus.py`
- `tests/specify_cli/cli/commands/test_mission_drive.py`
- `tests/specify_cli/adapters/test_observe_decide.py`
- `tests/specify_cli/adapters/test_gemini.py`
- `tests/specify_cli/adapters/test_cursor.py`

**Validation Criteria**:
- ✅ All unit tests pass: `pytest tests/specify_cli/events/ -v`
- ✅ All unit tests pass: `pytest tests/specify_cli/collaboration/ -v`
- ✅ All unit tests pass: `pytest tests/specify_cli/cli/commands/test_mission_* -v`
- ✅ All unit tests pass: `pytest tests/specify_cli/adapters/ -v`
- ✅ Coverage >= 90% for new code: `pytest --cov=src/specify_cli --cov-report=html`

---

## WP09: Integration Tests

**Purpose**: Integration tests for feature 006 event schemas, SaaS API mocking, and offline queue replay.

**Estimated Lines**: ~350
**Dependencies**: WP02, WP03, WP04

### Subtasks

**T036: Integration Test - 006 Event Schemas** (~80 lines)
- Create `tests/specify_cli/integration/test_006_event_schemas.py`
- Pin to feature 006 prerelease (check pyproject.toml has correct Git dependency)
- Test canonical envelope:
  - Create `Event` from spec_kitty_events.models
  - Validate ULID format (event_id, causation_id): 26 chars
  - Validate required fields: event_type, aggregate_id, payload, timestamp, node_id, lamport_clock
  - Serialize to JSON, deserialize, verify round-trip
- Test collaboration event payloads (canonical feature 006 contracts):
  - ParticipantJoined: participant_id, participant_identity, mission_id, optional auth_principal_id
  - DriveIntentSet: participant_id, mission_id, intent
  - FocusChanged: participant_id, mission_id, focus_target, optional previous_focus_target
  - ConcurrentDriverWarning: warning_id, mission_id, participant_ids, focus_target, severity
  - WarningAcknowledged: participant_id, mission_id, warning_id, acknowledgement
  - CommentPosted: participant_id, mission_id, comment_id, content, optional reply_to
  - DecisionCaptured: participant_id, mission_id, decision_id, topic, chosen_option, optional rationale
- Validate schema version compatibility (if schema_version field exists)

**T037: Integration Test - SaaS Join API** (~90 lines)
- Create `tests/specify_cli/integration/test_saas_join_mock.py`
- Mock httpx client (using pytest-httpx or respx)
- Test join_mission integration:
  - Mock POST `/api/v1/missions/{mission_id}/participants`:
    - Request: `{"role": "developer"}`
    - Response: `{"participant_id": "01HQRS...", "session_token": "..."}`
  - Verify CLI calls API with correct headers, payload
  - Verify CLI saves session state with participant_id
  - Verify CLI emits ParticipantJoined event
- Test error handling:
  - Mock 401 Unauthorized: Verify CLI displays auth error
  - Mock 404 Not Found: Verify CLI displays mission not found error
  - Mock network timeout: Verify CLI displays connection error

**T038: Integration Test - SaaS Replay API** (~100 lines)
- Create `tests/specify_cli/integration/test_saas_replay_mock.py`
- Mock httpx client
- Test replay_pending_events integration:
  - Mock POST `/api/v1/events/batch/`:
    - Request: `{"events": [event1_dict, event2_dict]}`
    - Response: `{"accepted": [event_id1, event_id2], "rejected": []}`
  - Verify CLI batches events (max 100 per request)
  - Verify CLI marks accepted events as "delivered"
- Test partial failure:
  - Mock response: `{"accepted": [event_id1], "rejected": [{"event_id": event_id2, "error": "participant not in mission roster"}]}`
  - Verify CLI marks rejected events as "failed"
  - Verify CLI logs error message
- Test retry logic:
  - Mock network error on first attempt
  - Mock success on second attempt
  - Verify exponential backoff (1s, 2s, 4s)

**T039: Integration Test - Offline Queue Replay** (~80 lines)
- Create `tests/specify_cli/integration/test_offline_queue_replay.py`
- Test offline → online flow:
  - Simulate online join (mock SaaS API, save session state)
  - Simulate offline commands (mock network error):
    - focus set wp:WP01 → Appends event with replay_status="pending"
    - drive set active → Appends event with replay_status="pending"
    - comment --text "test" → Appends event with replay_status="pending"
  - Verify events written to local durable queue
  - Simulate reconnect (mock SaaS API success)
  - Trigger replay (call replay_pending_events)
  - Verify all 3 events sent in batch
  - Verify events marked as "delivered"
- Test Lamport clock ordering:
  - Verify clock increments across offline events
  - Verify causation chain (event2.causation_id == event1.event_id)

**Files Created**:
- `tests/specify_cli/integration/test_006_event_schemas.py`
- `tests/specify_cli/integration/test_saas_join_mock.py`
- `tests/specify_cli/integration/test_saas_replay_mock.py`
- `tests/specify_cli/integration/test_offline_queue_replay.py`

**Validation Criteria**:
- ✅ All integration tests pass: `pytest tests/specify_cli/integration/ -v`
- ✅ Event schemas compatible with feature 006 prerelease
- ✅ SaaS API mocking works (no real network calls)
- ✅ Offline replay flow works end-to-end

---

## WP10: E2E Test

**Purpose**: End-to-end test against real SaaS dev environment with 3-participant concurrent scenario.

**Estimated Lines**: ~200
**Dependencies**: All (final E2E gate)

### Subtasks

**T040: E2E Test - 3-Participant Scenario** (~200 lines)
- Create `tests/e2e/test_collaboration_scenario.py`
- **Prerequisite**: SaaS dev environment with mission API deployed
- **Setup**:
  - Load SaaS dev URL, API key from env vars (SAAS_DEV_URL, SAAS_DEV_API_KEY)
  - Create test mission via SaaS API: POST `/api/v1/missions` → mission_id
- **Scenario (success criterion #1: concurrent development)**:
  - Participant A (developer): Join mission
  - Participant B (developer): Join mission
  - Participant A: focus set wp:WP01, drive set active
  - Participant B: focus set wp:WP02, drive set active
  - Verify: No collision warnings (different focus targets)
  - Verify: mission status shows 2 active participants
- **Scenario (success criterion #2: collision detection)**:
  - Participant A: Already active on wp:WP01
  - Participant B: focus set wp:WP01, drive set active
  - Verify: ConcurrentDriverWarning emitted (p99 latency < 500ms)
  - Participant B: Acknowledge with action="hold"
  - Verify: WarningAcknowledged event emitted
  - Verify: Participant B remains drive=inactive
- **Scenario (success criterion #3: organic handoff)**:
  - Participant A: focus set wp:WP02 (implicitly releases wp:WP01)
  - Participant B: focus set wp:WP01, drive set active
  - Verify: No collision warning (A no longer on WP01)
  - Verify: mission status shows A on WP02, B on WP01
- **Scenario (success criterion #4: offline replay)**:
  - Participant C (developer): Join mission (online)
  - Participant C: Simulate offline (mock network error)
  - Participant C: Run 4 commands offline (focus, drive, comment × 2)
  - Verify: Events queued locally with replay_status="pending"
  - Participant C: Reconnect (restore network)
  - Participant C: mission status (triggers replay)
  - Verify: All 4 events sent to SaaS, marked "delivered"
  - Verify: SaaS accepts events (participant_id in roster)
  - Verify: mission status shows merged state (A + B + C)
- **Teardown**:
  - Delete test mission via SaaS API
- **Assertions**:
  - 0 warnings when focus differs (criterion #1)
  - 100% collision detection rate (criterion #2)
  - < 30s handoff latency (criterion #3)
  - 100% replay success for roster participants (criterion #4)
  - < 10s replay latency for 4 events (criterion #4)

**Files Created**:
- `tests/e2e/test_collaboration_scenario.py`

**Validation Criteria**:
- ✅ E2E test passes against SaaS dev environment
- ✅ All 5 acceptance criteria met (concurrency, collision, handoff, offline, adapter equivalence)
- ✅ Test runs in < 2 minutes (success criterion #2: < 500ms warning latency measured)

---

## Implementation Command Reference

**Dependency-aware implementation commands:**

```bash
# Phase 1: Foundation
spec-kitty implement WP01  # No dependencies

# Phase 2: Infrastructure (parallel after WP01)
spec-kitty implement WP02 --base WP01
spec-kitty implement WP03 --base WP01

# Phase 3: Core Service (after WP02, WP03)
spec-kitty implement WP04 --base WP03
# Then merge WP02: cd .worktrees/040-mission-collaboration-cli-soft-coordination-WP04/ && git merge 040-mission-collaboration-cli-soft-coordination-WP02

# Phase 4: CLI Commands (parallel after WP04)
spec-kitty implement WP05 --base WP04
spec-kitty implement WP06 --base WP04

# Phase 5: Adapters (parallel with Phase 4)
spec-kitty implement WP07 --base WP01

# Phase 6: Tests (after implementation complete)
spec-kitty implement WP08 --base WP07
# Then merge WP05, WP06: cd .worktrees/.../WP08/ && git merge 040-...-WP05 && git merge 040-...-WP06

spec-kitty implement WP09 --base WP04

# Phase 7: E2E Gate (after all)
spec-kitty implement WP10 --base WP09
# Then merge WP08: cd .worktrees/.../WP10/ && git merge 040-...-WP08
```

---

## Validation Checklist

**Constitution Compliance:**
- ✅ Python 3.11+ (existing codebase)
- ✅ All dependencies in pyproject.toml
- ✅ Type checking: mypy --strict passes
- ✅ Test coverage: >= 90% for new code
- ✅ CLI performance: < 2s typical operations

**Functional Requirements:**
- ✅ FR-1: Mission join command (SaaS-authoritative, stores participant_id)
- ✅ FR-2: Focus set command (validates format, emits event)
- ✅ FR-3: Drive set command (pre-execution checks, collision detection)
- ✅ FR-4: Mission status command (roster display, collision summary)
- ✅ FR-5: Comment command (multi-line support, focus context)
- ✅ FR-6: Decide command (capability check, decision capture)
- ✅ FR-7: Collision warning & acknowledgement flow (continue|hold|reassign|defer)
- ✅ FR-8: Canonical event emission (14 event types, ULID identifiers)
- ✅ FR-9: Offline queue & replay (durable local queue, batch send)
- ✅ FR-10: Gemini & Cursor adapter interface (protocol compliance)

**Success Criteria:**
- ✅ #1: 3 participants work concurrently on different WPs without warnings
- ✅ #2: 100% collision detection for 2+ drivers on same focus, < 500ms latency
- ✅ #3: Organic handoff < 30s, 0 explicit lock releases
- ✅ #4: Offline work (50 commands) replays successfully in < 10s after reconnect
- ✅ #5: Gemini and Cursor adapters emit identical event structure (contract tests)
- ✅ #6: All 14 event types pass SaaS schema validation (1000+ events)
- ✅ #7: Acknowledgement capture < 1s latency (p99)

---

## Notes

**Parallel Development with Feature 006:**
- Feature 006 owns event schemas/payloads (spec-kitty-events library)
- Feature 040 owns emission/queue/replay (spec-kitty CLI)
- Pin to 006 prerelease during development, update to main commit after 006 merge
- Integration tests validate compatibility with 006 schemas

**Session State Security:**
- All session files stored with permissions 0600 (owner read/write only)
- participant_id must be SaaS-minted (CLI cannot invent IDs)
- SaaS validates participant_id on event replay (rejects stale/revoked participants not in mission roster)

**Offline Mode:**
- Join must succeed online (SaaS mints participant_id)
- All other commands work offline (queue events for replay)
- Replay triggers on next online command (automatic batch send)

**Testing Strategy:**
- Unit tests: No network, mock all SaaS calls
- Integration tests: Mock SaaS APIs, validate contracts
- E2E test: Real SaaS dev environment, 3-participant scenario (S1/M1 exit gate)

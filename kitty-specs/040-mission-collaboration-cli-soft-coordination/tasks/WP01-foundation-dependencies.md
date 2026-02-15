---
work_package_id: WP01
title: Foundation & Dependencies
lane: "done"
dependencies: []
base_branch: main
base_commit: c2b1699cbfc5000079b144dfdffd3724fd815911
created_at: '2026-02-15T10:51:38.487850+00:00'
subtasks: [T001, T002, T003, T004, T005]
shell_pid: "88801"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
---

# WP01: Foundation & Dependencies

**Purpose**: Set up project dependencies, module structure, and core data models for mission collaboration system.

**Context**: This is the foundation work package for feature 040 (mission collaboration CLI). It establishes the dependency tree, module organization, and core data models that all subsequent work packages will build upon.

**Target Branch**: 2.x

**Estimated Effort**: ~300 lines of code across 8 files

---

## Implementation Command

```bash
spec-kitty implement WP01
```

---

## Subtasks

### T001: Add Python Dependencies (~50 lines)

**Purpose**: Add required third-party libraries and pin spec-kitty-events to feature 006 prerelease.

**Files to Modify**:
- `pyproject.toml`
- `uv.lock` (generated)

**Steps**:

1. **Add httpx dependency** (SaaS API client):
   ```toml
   [project]
   dependencies = [
     "httpx>=0.27.0",
   ]
   ```

2. **Add ulid-py dependency** (ULID generation):
   ```toml
   ulid-py = "^1.1.0"
   ```

3. **Add spec-kitty-events Git dependency** (pin to feature 006 prerelease commit):
   ```toml
   spec-kitty-events = { git = "https://github.com/Priivacy-ai/spec-kitty-events.git", rev = "PLACEHOLDER_COMMIT_HASH" }
   ```

   **Important**: Replace `PLACEHOLDER_COMMIT_HASH` with the actual commit hash from the feature 006 branch. Coordinate with feature 006 team to get latest stable prerelease commit.

4. **Update uv.lock**:
   ```bash
   uv lock
   uv sync
   ```

5. **Verify imports work**:
   ```bash
   python -c "from spec_kitty_events.models import Event; print('✅ Event import successful')"
   python -c "import httpx; print('✅ httpx import successful')"
   python -c "import ulid; print('✅ ulid import successful')"
   ```

**Validation**:
- ✅ `uv sync` succeeds without errors
- ✅ All 3 imports work (Event, httpx, ulid)
- ✅ `uv lock` generates valid lock file

**Risks**:
- Feature 006 may update schemas during parallel development → Update pin as needed
- ULID library compatibility with Python 3.11+ → Verify in CI

---

### T002: Create Module Structure (~30 lines)

**Purpose**: Create package directories and init files for mission, collaboration, adapters, and events modules.

**Files to Create**:
- `src/specify_cli/mission/__init__.py`
- `src/specify_cli/collaboration/__init__.py`
- `src/specify_cli/adapters/__init__.py`
- `src/specify_cli/events/__init__.py` (may already exist, enhance if needed)

**Steps**:

1. **Create mission package**:
   ```python
   # src/specify_cli/mission/__init__.py
   """
   Mission collaboration CLI commands.

   This package provides commands for mission participation, focus management,
   drive intent, status display, commenting, and decision capture.

   Contract Ownership:
   - Feature 006: Event schemas/payloads (spec-kitty-events library)
   - Feature 040: CLI commands, event emission, queue/replay logic
   """

   __all__ = []  # Will be populated by command modules
   ```

2. **Create collaboration package**:
   ```python
   # src/specify_cli/collaboration/__init__.py
   """
   Mission collaboration domain logic.

   This package contains use-cases (service.py), collision detection (warnings.py),
   and materialized view state management (state.py).

   Responsibilities:
   - Use-case orchestration: join_mission, set_focus, set_drive, etc.
   - Advisory collision detection (soft coordination, not hard locks)
   - Local state cache (roster, participant context)
   """

   __all__ = []  # Will be populated by domain modules
   ```

3. **Create adapters package**:
   ```python
   # src/specify_cli/adapters/__init__.py
   """
   Adapter interface for AI agents (Gemini, Cursor, etc.).

   This package provides the ObserveDecideAdapter protocol and implementations
   for normalizing agent output into canonical collaboration events.

   S1/M1 Scope: Baseline stubs (Gemini, Cursor) with tested parsing for common scenarios.
   Full production hardening continues post-S1/M1.
   """

   __all__ = []  # Will be populated by adapter modules
   ```

4. **Enhance events package** (if exists, otherwise create):
   ```python
   # src/specify_cli/events/__init__.py
   """
   Event queue infrastructure.

   This package provides durable local queue storage, Lamport clock management,
   ULID generation, and SaaS replay transport.

   Storage Format:
   - Queue: ~/.spec-kitty/queue.db (mission-scoped rows)
   - Lamport clock: ~/.spec-kitty/events/lamport_clock.json (per-node state)
   """

   __all__ = []  # Will be populated by event modules
   ```

**Validation**:
- ✅ All 4 packages import without errors
- ✅ Package docstrings explain purpose and ownership
- ✅ No import cycles (pytest import test passes)

---

### T003: Define Event Queue Storage Models (~80 lines)

**Purpose**: Define data models for event queue entries with replay metadata.

**Files to Create**:
- `src/specify_cli/events/models.py`

**Steps**:

1. **Define EventQueueEntry dataclass**:
   ```python
   from dataclasses import dataclass
   from datetime import datetime
   from typing import Literal
   import json
   from spec_kitty_events.models import Event


   @dataclass
   class EventQueueEntry:
       """
       Event queue entry with replay metadata.

       The event field contains the canonical Event from spec-kitty-events library.
       Metadata fields (_replay_status, _retry_count, _last_retry_at) are CLI-specific
       and not part of the canonical envelope.
       """
       event: Event
       replay_status: Literal["pending", "delivered", "failed"]
       retry_count: int = 0
       last_retry_at: datetime | None = None

       def to_record(self) -> dict[str, object]:
           """
           Serialize to a queue record payload.

           Includes both canonical event fields and replay metadata.
           """
           # Serialize Event to dict (implementation depends on Event model from 006)
           event_dict = self.event.model_dump() if hasattr(self.event, 'model_dump') else self.event.__dict__

           # Add replay metadata with _ prefix (CLI-specific, not in canonical envelope)
           full_dict = {
               **event_dict,
               "_replay_status": self.replay_status,
               "_retry_count": self.retry_count,
               "_last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
           }

           return full_dict

       @classmethod
       def from_record(cls, data: dict[str, object]) -> "EventQueueEntry":
           """
           Deserialize from queue record payload.

           Raises:
               ValueError: If line is malformed or missing required fields
           """
           # Extract replay metadata
           replay_status = data.pop("_replay_status", "pending")
           retry_count = data.pop("_retry_count", 0)
           last_retry_str = data.pop("_last_retry_at", None)
           last_retry_at = datetime.fromisoformat(last_retry_str) if last_retry_str else None

           # Reconstruct Event (implementation depends on Event model from 006)
           event = Event(**data) if hasattr(Event, '__init__') else Event.model_validate(data)

           return cls(
               event=event,
               replay_status=replay_status,
               retry_count=retry_count,
               last_retry_at=last_retry_at,
           )
   ```

2. **Add type annotations**:
   - Ensure all fields have explicit types
   - Use `Literal` for replay_status (3 valid values)
   - Use `datetime | None` for optional timestamp

3. **Add docstrings**:
   - Explain canonical event vs. replay metadata separation
   - Document serialization format (queue record payload with replay metadata)
   - Document error handling (ValueError for malformed lines)

**Validation**:
- ✅ `mypy --strict src/specify_cli/events/models.py` passes
- ✅ Serialization round-trip: `EventQueueEntry.from_record(entry.to_record()) == entry`
- ✅ Handles missing replay metadata gracefully (defaults to pending, 0, None)

**Integration Points**:
- Feature 006 dependency: `Event` model must support serialization (model_dump or __dict__)
- If Event model changes, update serialization logic accordingly

---

### T004: Define Session State Models (~80 lines)

**Purpose**: Define data models for per-mission session state and active mission pointer.

**Files to Create**:
- `src/specify_cli/collaboration/models.py`

**Steps**:

1. **Define SessionState dataclass**:
   ```python
   from dataclasses import dataclass, field
   from datetime import datetime
   from typing import Literal


   @dataclass
   class SessionState:
       """
       Per-mission CLI session state (local cache of participant identity).

       Stored in: ~/.spec-kitty/missions/<mission_id>/session.json
       File permissions: 0600 (owner read/write only)

       Fields:
       - mission_id: Mission identifier (SaaS-assigned)
       - mission_run_id: Mission run correlation ULID (SaaS-assigned)
       - participant_id: SaaS-minted ULID (26 chars, bound to auth principal)
       - role: Join role label (validated by SaaS)
       - joined_at: ISO timestamp when joined (immutable)
       - last_activity_at: ISO timestamp of last command (updated on events)
       - drive_intent: Active execution intent (active|inactive)
       - focus: Current focus target (none, wp:<id>, step:<id>)
       """
       mission_id: str
       mission_run_id: str
       participant_id: str  # ULID, 26 chars
       role: str
       joined_at: datetime
       last_activity_at: datetime
       drive_intent: Literal["active", "inactive"] = "inactive"
       focus: str | None = None  # none, wp:<id>, step:<id>

       def to_dict(self) -> dict:
           """Serialize to JSON-compatible dict."""
           return {
               "mission_id": self.mission_id,
               "mission_run_id": self.mission_run_id,
               "participant_id": self.participant_id,
               "role": self.role,
               "joined_at": self.joined_at.isoformat(),
               "last_activity_at": self.last_activity_at.isoformat(),
               "drive_intent": self.drive_intent,
               "focus": self.focus,
           }

       @classmethod
       def from_dict(cls, data: dict) -> "SessionState":
           """Deserialize from JSON dict."""
           return cls(
               mission_id=data["mission_id"],
               mission_run_id=data["mission_run_id"],
               participant_id=data["participant_id"],
               role=data["role"],
               joined_at=datetime.fromisoformat(data["joined_at"]),
               last_activity_at=datetime.fromisoformat(data["last_activity_at"]),
               drive_intent=data.get("drive_intent", "inactive"),
               focus=data.get("focus"),
           )
   ```

2. **Define ActiveMissionPointer dataclass**:
   ```python
   @dataclass
   class ActiveMissionPointer:
       """
       CLI active mission pointer (fast lookup for commands omitting --mission flag).

       Stored in: ~/.spec-kitty/session.json

       S1/M1 Scope: Single active mission at a time.
       """
       active_mission_id: str | None = None
       last_switched_at: datetime | None = None

       def to_dict(self) -> dict:
           """Serialize to JSON-compatible dict."""
           return {
               "active_mission_id": self.active_mission_id,
               "last_switched_at": self.last_switched_at.isoformat() if self.last_switched_at else None,
           }

       @classmethod
       def from_dict(cls, data: dict) -> "ActiveMissionPointer":
           """Deserialize from JSON dict."""
           last_switched_str = data.get("last_switched_at")
           return cls(
               active_mission_id=data.get("active_mission_id"),
               last_switched_at=datetime.fromisoformat(last_switched_str) if last_switched_str else None,
           )
   ```

**Validation**:
- ✅ `mypy --strict src/specify_cli/collaboration/models.py` passes
- ✅ Session model stores SaaS-issued role label without local policy gating
- ✅ Serialization round-trip works for both dataclasses
- ✅ Temporal ordering: `joined_at <= last_activity_at` (validated in T014)

---

### T005: Create ObserveDecideAdapter Protocol (~60 lines)

**Purpose**: Define protocol interface for AI agent adapters (Gemini, Cursor, etc.).

**Files to Create**:
- `src/specify_cli/adapters/observe_decide.py`

**Steps**:

1. **Define supporting dataclasses**:
   ```python
   from dataclasses import dataclass
   from typing import Protocol


   @dataclass
   class ActorIdentity:
       """
       Adapter-normalized identity for agent/human actors.

       Used during join flow to normalize agent context. Not directly in events
       (events use SaaS-issued participant_id).
       """
       agent_type: str  # claude, gemini, cursor, human
       auth_principal: str  # User email or OAuth subject
       session_id: str  # CLI session ULID


   @dataclass
   class ObservationSignal:
       """
       Structured signal parsed from agent output.

       Signal types:
       - step_started: Agent began executing a step
       - step_completed: Agent finished executing a step
       - decision_requested: Agent asks for user decision
       - error_detected: Agent encountered error
       """
       signal_type: str  # step_started, step_completed, decision_requested, error_detected
       entity_id: str  # wp_id or step_id
       metadata: dict  # Provider-specific additional data


   @dataclass
   class DecisionRequestDraft:
       """
       Parsed decision request from agent output (optional for S1/M1).
       """
       question: str
       options: list[str]
       context: dict


   @dataclass
   class AdapterHealth:
       """
       Adapter health check result.
       """
       status: str  # ok, degraded, unavailable
       message: str
   ```

2. **Define ObserveDecideAdapter protocol**:
   ```python
   class ObserveDecideAdapter(Protocol):
       """
       Protocol for AI agent adapters (Gemini, Cursor, etc.).

       Adapters normalize agent-specific output into canonical collaboration events.

       S1/M1 Scope: Baseline stubs with tested parsing for common scenarios.
       Full production hardening continues post-S1/M1.

       Contract Ownership:
       - Feature 006: Event schemas/payloads
       - Feature 040: Adapter interface, implementations
       """

       def normalize_actor_identity(self, runtime_ctx: dict) -> ActorIdentity:
           """
           Extract actor identity from agent runtime context.

           Args:
               runtime_ctx: Provider-specific runtime context (e.g., user_email, session_token)

           Returns:
               ActorIdentity with agent_type, auth_principal, session_id
           """
           ...

       def parse_observation(self, output: str | dict) -> list[ObservationSignal]:
           """
           Parse agent output into structured observation signals.

           Args:
               output: Agent output (text or JSON)

           Returns:
               List of ObservationSignal (may be empty if no signals detected)
           """
           ...

       def detect_decision_request(self, observation: ObservationSignal) -> DecisionRequestDraft | None:
           """
           Check if observation contains decision request.

           Args:
               observation: Parsed observation signal

           Returns:
               DecisionRequestDraft if decision requested, else None
           """
           ...

       def format_decision_answer(self, answer: str) -> str:
           """
           Format decision answer for agent input (provider-specific formatting).

           Args:
               answer: Decision answer text

           Returns:
               Formatted string (e.g., Gemini JSON vs. Cursor markdown)
           """
           ...

       def healthcheck(self) -> AdapterHealth:
           """
           Check adapter prerequisites (API keys, network connectivity).

           Returns:
               AdapterHealth with status and message
           """
           ...
   ```

**Validation**:
- ✅ `mypy --strict src/specify_cli/adapters/observe_decide.py` passes
- ✅ Protocol has exactly 5 method signatures
- ✅ All methods have type annotations (args and return types)
- ✅ Docstrings explain purpose and contract ownership

**Integration Points**:
- Adapters implemented in WP07 must satisfy this protocol
- Command handlers use adapters via protocol (no provider-specific logic)

---

## Files Summary

**Created (8 files)**:
- `src/specify_cli/mission/__init__.py` (T002)
- `src/specify_cli/collaboration/__init__.py` (T002)
- `src/specify_cli/adapters/__init__.py` (T002)
- `src/specify_cli/events/__init__.py` (T002, enhance if exists)
- `src/specify_cli/events/models.py` (T003)
- `src/specify_cli/collaboration/models.py` (T004)
- `src/specify_cli/adapters/observe_decide.py` (T005)

**Modified (1 file)**:
- `pyproject.toml` (T001)

**Generated (1 file)**:
- `uv.lock` (T001)

---

## Validation Checklist

Before marking WP01 complete, verify:

- ✅ `uv sync` succeeds with new dependencies
- ✅ `from spec_kitty_events.models import Event` works
- ✅ All 4 packages (`mission`, `collaboration`, `adapters`, `events`) import without errors
- ✅ `mypy --strict src/specify_cli/events/models.py src/specify_cli/collaboration/models.py src/specify_cli/adapters/observe_decide.py` passes
- ✅ EventQueueEntry serialization round-trip works
- ✅ SessionState includes SaaS-issued role and mission context fields
- ✅ ObserveDecideAdapter protocol has 5 method signatures
- ✅ No import cycles (pytest import test passes)

---

## Next Steps

After WP01 completion:
- **WP02** (Event Queue Infrastructure) - Depends on WP01
- **WP03** (Session State Management) - Depends on WP01
- **WP07** (Adapter Implementations) - Depends on WP01

These 3 work packages can be implemented in parallel after WP01.

---

## Notes

**Feature 006 Dependency**:
- Pin to specific commit hash during parallel development
- Update pin as feature 006 schemas evolve
- After 006 merge to main, update to main commit hash

**ULID Format**:
- 26 characters, alphanumeric, sortable by creation time
- Used for event_id, causation_id, participant_id

**Role Handling**:
- SaaS is source of truth for join-role validation and permissions.
- CLI stores role labels for projection/display and auditing; it does not enforce local capability matrices in S1/M1.

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-15

**Issue 1 (blocking): `specify_cli.mission` compatibility shim is incomplete.**

`src/specify_cli/mission/__init__.py` claims backward compatibility but only re-exports a subset of the previous `specify_cli.mission` API.

Repro:
`PYTHONPATH=src python3 -c "import specify_cli.mission as m; print(hasattr(m, 'get_active_mission'), hasattr(m, 'validate_deliverables_path'))"`

Current result: `False False`

Both functions existed in the pre-rename module (`src/specify_cli/mission_system.py`). This is a regression risk for existing callers importing from `specify_cli.mission`.

**How to fix:** Re-export all previously importable public mission symbols from `mission_system` (or provide explicit deprecation aliases with warnings) so legacy imports keep working.

---

**Issue 2 (blocking): Versioning policy violation for `__init__.py` change.**

`src/specify_cli/__init__.py` was modified (`mission` import path switch), but there is no corresponding version bump in `pyproject.toml` and no changelog entry.

Project rule in `AGENTS.md` states:
"Any changes to `__init__.py` for the Spec Kitty CLI require a version rev in `pyproject.toml` and addition of entries to `CHANGELOG.md`."

**How to fix:** Increment `[project].version` in `pyproject.toml` and add a matching `CHANGELOG.md` entry describing the mission import-path compatibility changes.

---

Dependency note: WP02, WP03, WP07, and WP10 depend on WP01. After fixing and merging WP01 updates, dependent worktrees should rebase.


## Activity Log

- 2026-02-15T10:51:38Z – claude-sonnet-4.5 – shell_pid=51268 – lane=doing – Assigned agent via workflow command
- 2026-02-15T11:00:45Z – claude-sonnet-4.5 – shell_pid=51268 – lane=for_review – Ready for review: Foundation complete with all dependencies, module structure, and data models. All validation checks pass.
- 2026-02-15T11:01:25Z – codex – shell_pid=66141 – lane=doing – Started review via workflow command
- 2026-02-15T11:04:11Z – codex – shell_pid=66141 – lane=planned – Moved to planned
- 2026-02-15T11:11:31Z – codex – shell_pid=66141 – lane=for_review – Moved to for_review
- 2026-02-15T11:12:45Z – codex – shell_pid=83301 – lane=doing – Started review via workflow command
- 2026-02-15T11:15:14Z – codex – shell_pid=83301 – lane=planned – Moved to planned
- 2026-02-15T11:22:24Z – codex – shell_pid=83301 – lane=for_review – Moved to for_review
- 2026-02-15T11:22:58Z – codex – shell_pid=88801 – lane=doing – Started review via workflow command
- 2026-02-15T11:25:24Z – codex – shell_pid=88801 – lane=planned – Moved to planned
- 2026-02-15T12:44:50Z – codex – shell_pid=88801 – lane=done – Arbiter approval: Round 3 feedback overly strict. Backwards compat and version rules don't apply to feature branch development. All functional tests pass.

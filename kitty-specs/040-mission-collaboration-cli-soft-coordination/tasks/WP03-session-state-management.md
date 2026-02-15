---
work_package_id: WP03
title: Session State Management
lane: "done"
dependencies: [WP01]
base_branch: 040-mission-collaboration-cli-soft-coordination-WP02
base_commit: 9f352ec48cd0200bc28d33ec408e8575b9fcbb08
created_at: '2026-02-15T13:12:20.111712+00:00'
subtasks: [T011, T012, T013, T014]
shell_pid: "42577"
agent: "codex"
review_status: "acknowledged"
reviewed_by: "Robert Douglass"
---

# WP03: Session State Management

**Purpose**: Implement per-mission session state storage with atomic I/O, active mission pointer, and validation.

**Context**: Session state provides local cache of participant identity (SaaS-issued participant_id) and current focus/drive context. The active mission pointer enables commands to omit --mission flag for ergonomics.

**Target Branch**: 2.x

**Estimated Effort**: ~300 lines of code across 1 file

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

---

## Subtasks

### T011: Implement Session File I/O (~100 lines)

**Purpose**: Implement atomic session state read/write with proper file permissions.

**Files to Create**:
- `src/specify_cli/collaboration/session.py`

**Steps**:

1. **Implement save_session_state function**:
   ```python
   from pathlib import Path
   import json
   import os
   from specify_cli.collaboration.models import SessionState


   def get_session_path(mission_id: str) -> Path:
       """Get path to session state file for mission."""
       return Path.home() / ".spec-kitty" / "missions" / mission_id / "session.json"


   def save_session_state(mission_id: str, state: SessionState) -> None:
       """
       Save session state to disk (atomic write).

       Args:
           mission_id: Mission identifier
           state: SessionState to persist

       Raises:
           IOError: If file write fails
       """
       session_path = get_session_path(mission_id)
       session_path.parent.mkdir(parents=True, exist_ok=True)

       # Serialize state
       data = state.to_dict()

       # Atomic write: Write to temp file, then rename
       temp_path = session_path.with_suffix(".tmp")
       with open(temp_path, "w") as f:
           json.dump(data, f, indent=2)
           f.flush()
           os.fsync(f.fileno())

       temp_path.replace(session_path)

       # Set file permissions to 0600 (owner read/write only)
       session_path.chmod(0o600)
   ```

2. **Implement load_session_state function**:
   ```python
   def load_session_state(mission_id: str) -> SessionState | None:
       """
       Load session state from disk.

       Args:
           mission_id: Mission identifier

       Returns:
           SessionState if exists and valid, None otherwise

       Notes:
           - Returns None if file missing (user not joined)
           - Returns None if JSON corrupted (logs warning)
       """
       session_path = get_session_path(mission_id)

       if not session_path.exists():
           return None

       try:
           with open(session_path, "r") as f:
               data = json.load(f)
               return SessionState.from_dict(data)
       except (json.JSONDecodeError, ValueError, KeyError) as e:
           print(f"⚠️  Corrupted session file {session_path}: {e}")
           return None
       except IOError as e:
           print(f"⚠️  Failed to read session file {session_path}: {e}")
           return None
   ```

**Validation**:
- ✅ Session files created with permissions 0600
- ✅ Atomic writes (no partial state on crash)
- ✅ Returns None gracefully if file missing/corrupted

---

### T012: Implement Per-Mission Session Storage (~80 lines)

**Purpose**: Implement session update and ensure-joined helpers.

**Steps**:

1. **Implement update_session_state function**:
   ```python
   from datetime import datetime


   def update_session_state(mission_id: str, **updates) -> None:
       """
       Update session state fields atomically.

       Args:
           mission_id: Mission identifier
           **updates: Fields to update (last_activity_at, drive_intent, focus)

       Raises:
           ValueError: If not joined (session file missing)
       """
       state = load_session_state(mission_id)

       if state is None:
           raise ValueError(f"Not joined to mission {mission_id}. Run `spec-kitty mission join` first.")

       # Update last_activity_at automatically
       state.last_activity_at = datetime.now()

       # Apply updates
       for key, value in updates.items():
           if hasattr(state, key):
               setattr(state, key, value)
           else:
               raise ValueError(f"Invalid session field: {key}")

       # Save atomically
       save_session_state(mission_id, state)
   ```

2. **Implement ensure_joined helper**:
   ```python
   def ensure_joined(mission_id: str) -> SessionState:
       """
       Load session state, raise error if not joined.

       Used by all non-join collaboration commands as precondition check.

       Args:
           mission_id: Mission identifier

       Returns:
           SessionState if joined

       Raises:
           ValueError: If not joined
       """
       state = load_session_state(mission_id)

       if state is None:
           raise ValueError(
               f"Not joined to mission {mission_id}.\n"
               f"Run: spec-kitty mission join {mission_id} --role <role_label>"
           )

       return state
   ```

3. **Implement get_mission_dir helper**:
   ```python
   def get_mission_dir(mission_id: str) -> Path:
       """
       Get path to mission directory.

       Args:
           mission_id: Mission identifier

       Returns:
           Path to ~/.spec-kitty/missions/<mission_id>/
       """
       return Path.home() / ".spec-kitty" / "missions" / mission_id
   ```

**Validation**:
- ✅ Update automatically sets last_activity_at
- ✅ ensure_joined raises clear error if not joined
- ✅ Invalid field names rejected with error

---

### T013: Implement Active Mission Pointer (~70 lines)

**Purpose**: Implement active mission pointer for ergonomic CLI usage.

**Steps**:

1. **Implement set_active_mission function**:
   ```python
   def get_active_mission_path() -> Path:
       """Get path to active mission pointer file."""
       return Path.home() / ".spec-kitty" / "session.json"


   def set_active_mission(mission_id: str) -> None:
       """
       Set active mission pointer.

       Args:
           mission_id: Mission identifier to set as active
       """
       from specify_cli.collaboration.models import ActiveMissionPointer

       pointer = ActiveMissionPointer(
           active_mission_id=mission_id,
           last_switched_at=datetime.now(),
       )

       path = get_active_mission_path()
       path.parent.mkdir(parents=True, exist_ok=True)

       # Atomic write
       temp_path = path.with_suffix(".tmp")
       with open(temp_path, "w") as f:
           json.dump(pointer.to_dict(), f, indent=2)
           f.flush()
           os.fsync(f.fileno())

       temp_path.replace(path)
   ```

2. **Implement get_active_mission function**:
   ```python
   def get_active_mission() -> str | None:
       """
       Get active mission ID.

       Returns:
           Mission ID if active mission set, None otherwise
       """
       from specify_cli.collaboration.models import ActiveMissionPointer

       path = get_active_mission_path()

       if not path.exists():
           return None

       try:
           with open(path, "r") as f:
               data = json.load(f)
               pointer = ActiveMissionPointer.from_dict(data)
               return pointer.active_mission_id
       except (json.JSONDecodeError, ValueError, IOError):
           return None
   ```

3. **Implement resolve_mission_id helper**:
   ```python
   def resolve_mission_id(explicit_id: str | None) -> str:
       """
       Resolve mission ID from explicit argument or active pointer.

       Args:
           explicit_id: Mission ID from --mission flag (or None)

       Returns:
           Resolved mission ID

       Raises:
           ValueError: If no explicit ID and no active mission
       """
       if explicit_id:
           return explicit_id

       active = get_active_mission()

       if active is None:
           raise ValueError(
               "No active mission. Either:\n"
               "1. Provide --mission <mission_id> flag\n"
               "2. Join a mission: spec-kitty mission join <mission_id> --role <role_label>"
           )

       return active
   ```

**Validation**:
- ✅ Active mission pointer survives CLI restarts
- ✅ resolve_mission_id returns explicit ID if provided
- ✅ resolve_mission_id returns active mission if omitted
- ✅ Clear error if no active mission and no explicit ID

---

### T014: Add Session Validation (~50 lines)

**Purpose**: Implement session integrity validation.

**Steps**:

1. **Implement validate_participant_id function**:
   ```python
   def validate_participant_id(participant_id: str) -> bool:
       """
       Validate participant_id ULID format.

       Args:
           participant_id: Participant ID to validate

       Returns:
           True if valid ULID format, False otherwise
       """
       from specify_cli.events.ulid_utils import validate_ulid_format

       is_valid = validate_ulid_format(participant_id)

       if not is_valid:
           print(f"⚠️  Invalid participant_id format: {participant_id} (expected 26-char ULID)")

       return is_valid
   ```

2. **Implement validate_session_integrity function**:
   ```python
   def validate_session_integrity(state: SessionState) -> list[str]:
       """
       Validate session state integrity.

       Args:
           state: SessionState to validate

       Returns:
           List of validation errors (empty if valid)
       """
       errors = []

       # Check temporal ordering
       if state.joined_at > state.last_activity_at:
           errors.append(f"Temporal violation: joined_at ({state.joined_at}) > last_activity_at ({state.last_activity_at})")

       # Check participant_id format
       if not validate_participant_id(state.participant_id):
           errors.append(f"Invalid participant_id format: {state.participant_id}")

       # Check role label is present (SaaS validates exact taxonomy)
       if not state.role or not state.role.strip():
           errors.append("Invalid role: role label is empty")

       # Check focus format
       if state.focus is not None and state.focus != "none":
           if not (state.focus.startswith("wp:") or state.focus.startswith("step:")):
               errors.append(f"Invalid focus format: {state.focus} (expected wp:<id>, step:<id>, or none)")

       return errors
   ```

3. **Add pre-command validation check**:
   ```python
   def validate_session_before_command(mission_id: str) -> SessionState:
       """
       Validate session before running collaboration command.

       Args:
           mission_id: Mission identifier

       Returns:
           SessionState if valid

       Raises:
           ValueError: If validation fails
       """
       state = ensure_joined(mission_id)

       errors = validate_session_integrity(state)

       if errors:
           raise ValueError(f"Session validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

       return state
   ```

**Validation**:
- ✅ Catches malformed participant_id (not 26 chars)
- ✅ Catches temporal violations (joined_at > last_activity_at)
- ✅ Catches invalid role (not in 4 allowed roles)
- ✅ Catches invalid focus format

---

## Files Summary

**Created (1 file)**:
- `src/specify_cli/collaboration/session.py` (T011, T012, T013, T014)

---

## Validation Checklist

- ✅ Session files created with permissions 0600
- ✅ Atomic writes (temp file + rename)
- ✅ Active mission pointer survives CLI restarts
- ✅ Session validation catches malformed ULID, temporal violations

---

## Next Steps

After WP03 completion:
- **WP04** (Collaboration Service Core) - Depends on WP02, WP03

---

## Notes

**Session State Security**:
- File permissions 0600 prevent other users from reading participant_id
- participant_id must be SaaS-minted (CLI cannot invent IDs)

**Active Mission Pointer** (S1/M1 scope):
- Single active mission at a time
- Multi-mission support deferred to future sprint

**Validation Strategy**:
- Validate on load (catch corruption early)
- Validate before commands (catch state drift)
- Clear error messages with actionable troubleshooting steps

## Activity Log

- 2026-02-15T13:16:02Z – unknown – shell_pid=34400 – lane=for_review – Moved to for_review
- 2026-02-15T13:16:50Z – codex – shell_pid=37111 – lane=doing – Started review via workflow command
- 2026-02-15T13:21:56Z – codex – shell_pid=37111 – lane=planned – Moved to planned
- 2026-02-15T13:26:07Z – codex – shell_pid=37111 – lane=for_review – Moved to for_review
- 2026-02-15T13:26:33Z – codex – shell_pid=42577 – lane=doing – Started review via workflow command
- 2026-02-15T13:30:34Z – codex – shell_pid=42577 – lane=done – Codex approval: No blocking issues. Session state, active mission pointer, and integrity validation all pass. 39/39 tests passing.

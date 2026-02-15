"""Session state management for mission collaboration."""

from pathlib import Path
import json
import os
from datetime import datetime

from specify_cli.collaboration.models import SessionState, ActiveMissionPointer


# ============================================================================
# Constants
# ============================================================================

# Canonical 4-role taxonomy (validated by SaaS)
CANONICAL_ROLES = {"developer", "reviewer", "observer", "stakeholder"}


# ============================================================================
# T011: Session File I/O
# ============================================================================


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


# ============================================================================
# T012: Per-Mission Session Storage
# ============================================================================


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


def get_mission_dir(mission_id: str) -> Path:
    """
    Get path to mission directory.

    Args:
        mission_id: Mission identifier

    Returns:
        Path to ~/.spec-kitty/missions/<mission_id>/
    """
    return Path.home() / ".spec-kitty" / "missions" / mission_id


# ============================================================================
# T013: Active Mission Pointer
# ============================================================================


def get_active_mission_path() -> Path:
    """Get path to active mission pointer file."""
    return Path.home() / ".spec-kitty" / "session.json"


def set_active_mission(mission_id: str) -> None:
    """
    Set active mission pointer.

    Args:
        mission_id: Mission identifier to set as active
    """
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


def get_active_mission() -> str | None:
    """
    Get active mission ID.

    Returns:
        Mission ID if active mission set, None otherwise
    """
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


# ============================================================================
# T014: Session Validation
# ============================================================================


def validate_participant_id(participant_id: str) -> bool:
    """
    Validate participant_id ULID format.

    Args:
        participant_id: Participant ID to validate

    Returns:
        True if valid ULID format, False otherwise

    Note:
        Inlined ULID validation to avoid hard dependency on events package.
        ULID uses Crockford Base32 (0-9, A-Z excluding I, L, O, U).
    """
    # Check length
    if len(participant_id) != 26:
        print(f"⚠️  Invalid participant_id format: {participant_id} (expected 26-char ULID)")
        return False

    # Check character set (Crockford Base32)
    valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    is_valid = all(c in valid_chars for c in participant_id.upper())

    if not is_valid:
        print(f"⚠️  Invalid participant_id format: {participant_id} (expected 26-char ULID)")

    return is_valid


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

    # Check role label against canonical taxonomy
    if not state.role or not state.role.strip():
        errors.append("Invalid role: role label is empty")
    elif state.role not in CANONICAL_ROLES:
        valid_roles = ", ".join(sorted(CANONICAL_ROLES))
        errors.append(f"Invalid role: '{state.role}' not in canonical taxonomy ({valid_roles})")

    # Check focus format
    if state.focus is not None and state.focus != "none":
        if not (state.focus.startswith("wp:") or state.focus.startswith("step:")):
            errors.append(f"Invalid focus format: {state.focus} (expected wp:<id>, step:<id>, or none)")

    return errors


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

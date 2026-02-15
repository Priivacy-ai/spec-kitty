"""Tests for session state management."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from specify_cli.collaboration.session import (
    get_session_path,
    save_session_state,
    load_session_state,
    update_session_state,
    ensure_joined,
    get_mission_dir,
    set_active_mission,
    get_active_mission,
    resolve_mission_id,
    validate_participant_id,
    validate_session_integrity,
    validate_session_before_command,
)
from specify_cli.collaboration.models import SessionState


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """Override home directory for tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def sample_session_state():
    """Create a sample session state for testing."""
    now = datetime.now()
    return SessionState(
        mission_id="test-mission",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ123456",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="developer",
        joined_at=now,
        last_activity_at=now,
        drive_intent="inactive",
        focus=None,
    )


# ============================================================================
# T011: Session File I/O Tests
# ============================================================================


def test_get_session_path(tmp_home):
    """Test session path generation."""
    path = get_session_path("test-mission")
    expected = tmp_home / ".spec-kitty" / "missions" / "test-mission" / "session.json"
    assert path == expected


def test_save_session_state_creates_directory(tmp_home, sample_session_state):
    """Test that save creates directory structure."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    session_path = get_session_path(mission_id)
    assert session_path.exists()
    assert session_path.parent.exists()


def test_save_session_state_sets_permissions(tmp_home, sample_session_state):
    """Test that session file has 0600 permissions."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    session_path = get_session_path(mission_id)
    # Check file permissions (owner read/write only)
    assert oct(session_path.stat().st_mode)[-3:] == "600"


def test_save_session_state_atomic_write(tmp_home, sample_session_state):
    """Test that save uses atomic write (temp file + rename)."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    session_path = get_session_path(mission_id)
    temp_path = session_path.with_suffix(".tmp")

    # Temp file should not exist after successful write
    assert not temp_path.exists()
    assert session_path.exists()


def test_load_session_state_success(tmp_home, sample_session_state):
    """Test loading valid session state."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    loaded = load_session_state(mission_id)
    assert loaded is not None
    assert loaded.mission_id == sample_session_state.mission_id
    assert loaded.participant_id == sample_session_state.participant_id
    assert loaded.role == sample_session_state.role


def test_load_session_state_missing_file(tmp_home):
    """Test loading from non-existent file returns None."""
    loaded = load_session_state("nonexistent-mission")
    assert loaded is None


def test_load_session_state_corrupted_json(tmp_home):
    """Test loading corrupted JSON returns None."""
    mission_id = "test-mission"
    session_path = get_session_path(mission_id)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    # Write invalid JSON
    with open(session_path, "w") as f:
        f.write("{ invalid json }")

    loaded = load_session_state(mission_id)
    assert loaded is None


def test_load_session_state_missing_fields(tmp_home):
    """Test loading JSON with missing required fields returns None."""
    mission_id = "test-mission"
    session_path = get_session_path(mission_id)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    # Write incomplete JSON (missing participant_id)
    with open(session_path, "w") as f:
        json.dump({"mission_id": mission_id}, f)

    loaded = load_session_state(mission_id)
    assert loaded is None


# ============================================================================
# T012: Per-Mission Session Storage Tests
# ============================================================================


def test_update_session_state_updates_fields(tmp_home, sample_session_state):
    """Test updating session state fields."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    # Update focus
    update_session_state(mission_id, focus="wp:WP01")

    loaded = load_session_state(mission_id)
    assert loaded is not None
    assert loaded.focus == "wp:WP01"


def test_update_session_state_auto_updates_last_activity(tmp_home, sample_session_state):
    """Test that update automatically sets last_activity_at."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    original_activity_at = sample_session_state.last_activity_at

    # Small delay to ensure time difference
    import time
    time.sleep(0.01)

    update_session_state(mission_id, drive_intent="active")

    loaded = load_session_state(mission_id)
    assert loaded is not None
    assert loaded.last_activity_at > original_activity_at


def test_update_session_state_not_joined_raises_error(tmp_home):
    """Test updating non-existent session raises error."""
    with pytest.raises(ValueError, match="Not joined to mission"):
        update_session_state("nonexistent-mission", focus="wp:WP01")


def test_update_session_state_invalid_field_raises_error(tmp_home, sample_session_state):
    """Test updating invalid field raises error."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    with pytest.raises(ValueError, match="Invalid session field"):
        update_session_state(mission_id, invalid_field="value")


def test_ensure_joined_success(tmp_home, sample_session_state):
    """Test ensure_joined returns state when joined."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    state = ensure_joined(mission_id)
    assert state.mission_id == mission_id


def test_ensure_joined_not_joined_raises_error(tmp_home):
    """Test ensure_joined raises error when not joined."""
    with pytest.raises(ValueError, match="Not joined to mission"):
        ensure_joined("nonexistent-mission")


def test_get_mission_dir(tmp_home):
    """Test mission directory path generation."""
    mission_id = "test-mission"
    mission_dir = get_mission_dir(mission_id)
    expected = tmp_home / ".spec-kitty" / "missions" / mission_id
    assert mission_dir == expected


# ============================================================================
# T013: Active Mission Pointer Tests
# ============================================================================


def test_set_active_mission(tmp_home):
    """Test setting active mission pointer."""
    mission_id = "test-mission"
    set_active_mission(mission_id)

    active = get_active_mission()
    assert active == mission_id


def test_set_active_mission_creates_directory(tmp_home):
    """Test that set_active_mission creates directory structure."""
    mission_id = "test-mission"
    set_active_mission(mission_id)

    from specify_cli.collaboration.session import get_active_mission_path
    path = get_active_mission_path()
    assert path.exists()
    assert path.parent.exists()


def test_set_active_mission_uses_atomic_write(tmp_home):
    """Test that set_active_mission uses atomic write."""
    mission_id = "test-mission"
    set_active_mission(mission_id)

    from specify_cli.collaboration.session import get_active_mission_path
    path = get_active_mission_path()
    temp_path = path.with_suffix(".tmp")

    # Temp file should not exist after successful write
    assert not temp_path.exists()
    assert path.exists()


def test_get_active_mission_no_file_returns_none(tmp_home):
    """Test get_active_mission returns None when no active mission."""
    active = get_active_mission()
    assert active is None


def test_get_active_mission_corrupted_returns_none(tmp_home):
    """Test get_active_mission returns None for corrupted file."""
    from specify_cli.collaboration.session import get_active_mission_path
    path = get_active_mission_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write invalid JSON
    with open(path, "w") as f:
        f.write("{ invalid json }")

    active = get_active_mission()
    assert active is None


def test_resolve_mission_id_explicit_id_provided(tmp_home):
    """Test resolve_mission_id returns explicit ID when provided."""
    result = resolve_mission_id("explicit-mission")
    assert result == "explicit-mission"


def test_resolve_mission_id_uses_active_mission(tmp_home):
    """Test resolve_mission_id uses active mission when no explicit ID."""
    set_active_mission("test-mission")

    result = resolve_mission_id(None)
    assert result == "test-mission"


def test_resolve_mission_id_no_explicit_no_active_raises_error(tmp_home):
    """Test resolve_mission_id raises error when no explicit ID and no active mission."""
    with pytest.raises(ValueError, match="No active mission"):
        resolve_mission_id(None)


def test_active_mission_pointer_survives_restarts(tmp_home):
    """Test active mission pointer persists across 'restarts'."""
    mission_id = "test-mission"
    set_active_mission(mission_id)

    # Simulate restart by getting fresh value
    active = get_active_mission()
    assert active == mission_id


# ============================================================================
# T014: Session Validation Tests
# ============================================================================


def test_validate_participant_id_valid():
    """Test validating valid ULID participant_id."""
    valid_ulid = "01HXN8K3M9PQRSTVWXYZ123456"
    assert validate_participant_id(valid_ulid) is True


def test_validate_participant_id_wrong_length():
    """Test validating participant_id with wrong length."""
    short_id = "01HXN8K3M9"
    assert validate_participant_id(short_id) is False


def test_validate_participant_id_invalid_chars():
    """Test validating participant_id with invalid characters."""
    invalid_ulid = "01HXN8K3M9PQRSTVWXYZ!@#$%^"
    assert validate_participant_id(invalid_ulid) is False


def test_validate_session_integrity_valid(sample_session_state):
    """Test validating valid session state."""
    errors = validate_session_integrity(sample_session_state)
    assert len(errors) == 0


def test_validate_session_integrity_temporal_violation():
    """Test detecting temporal violation (joined_at > last_activity_at)."""
    now = datetime.now()
    from datetime import timedelta

    state = SessionState(
        mission_id="test-mission",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ123456",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="developer",
        joined_at=now,
        last_activity_at=now - timedelta(seconds=10),  # Earlier than joined_at
        drive_intent="inactive",
        focus=None,
    )

    errors = validate_session_integrity(state)
    assert len(errors) == 1
    assert "Temporal violation" in errors[0]


def test_validate_session_integrity_invalid_participant_id():
    """Test detecting invalid participant_id format."""
    now = datetime.now()

    state = SessionState(
        mission_id="test-mission",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ123456",
        participant_id="invalid-id",  # Wrong length
        role="developer",
        joined_at=now,
        last_activity_at=now,
        drive_intent="inactive",
        focus=None,
    )

    errors = validate_session_integrity(state)
    assert any("Invalid participant_id format" in e for e in errors)


def test_validate_session_integrity_empty_role():
    """Test detecting empty role label."""
    now = datetime.now()

    state = SessionState(
        mission_id="test-mission",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ123456",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="",  # Empty role
        joined_at=now,
        last_activity_at=now,
        drive_intent="inactive",
        focus=None,
    )

    errors = validate_session_integrity(state)
    assert any("Invalid role" in e for e in errors)


def test_validate_session_integrity_invalid_role_taxonomy():
    """Test detecting role not in canonical taxonomy."""
    now = datetime.now()

    state = SessionState(
        mission_id="test-mission",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ123456",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="implementer",  # Not in canonical taxonomy
        joined_at=now,
        last_activity_at=now,
        drive_intent="inactive",
        focus=None,
    )

    errors = validate_session_integrity(state)
    assert any("not in canonical taxonomy" in e for e in errors)
    assert any("developer, observer, reviewer, stakeholder" in e for e in errors)


def test_validate_session_integrity_invalid_focus_format():
    """Test detecting invalid focus format."""
    now = datetime.now()

    state = SessionState(
        mission_id="test-mission",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ123456",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="developer",
        joined_at=now,
        last_activity_at=now,
        drive_intent="inactive",
        focus="invalid-format",  # Should be wp:, step:, or none
    )

    errors = validate_session_integrity(state)
    assert any("Invalid focus format" in e for e in errors)


def test_validate_session_integrity_valid_focus_formats(sample_session_state):
    """Test that valid focus formats pass validation."""
    # Test wp: format
    sample_session_state.focus = "wp:WP01"
    errors = validate_session_integrity(sample_session_state)
    assert len(errors) == 0

    # Test step: format
    sample_session_state.focus = "step:T001"
    errors = validate_session_integrity(sample_session_state)
    assert len(errors) == 0

    # Test none
    sample_session_state.focus = "none"
    errors = validate_session_integrity(sample_session_state)
    assert len(errors) == 0

    # Test None (null)
    sample_session_state.focus = None
    errors = validate_session_integrity(sample_session_state)
    assert len(errors) == 0


def test_validate_session_before_command_success(tmp_home, sample_session_state):
    """Test validate_session_before_command with valid session."""
    mission_id = "test-mission"
    save_session_state(mission_id, sample_session_state)

    state = validate_session_before_command(mission_id)
    assert state.mission_id == mission_id


def test_validate_session_before_command_not_joined(tmp_home):
    """Test validate_session_before_command raises error when not joined."""
    with pytest.raises(ValueError, match="Not joined to mission"):
        validate_session_before_command("nonexistent-mission")


def test_validate_session_before_command_integrity_violation(tmp_home):
    """Test validate_session_before_command raises error on integrity violation."""
    now = datetime.now()
    from datetime import timedelta

    # Create state with temporal violation
    state = SessionState(
        mission_id="test-mission",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ123456",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="developer",
        joined_at=now,
        last_activity_at=now - timedelta(seconds=10),
        drive_intent="inactive",
        focus=None,
    )

    save_session_state("test-mission", state)

    with pytest.raises(ValueError, match="Session validation failed"):
        validate_session_before_command("test-mission")


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_session_lifecycle(tmp_home):
    """Test complete session lifecycle: create, update, validate, destroy."""
    mission_id = "test-mission"
    now = datetime.now()

    # Create session
    state = SessionState(
        mission_id=mission_id,
        mission_run_id="01HXN8K3M9PQRSTVWXYZ123456",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="developer",
        joined_at=now,
        last_activity_at=now,
        drive_intent="inactive",
        focus=None,
    )
    save_session_state(mission_id, state)

    # Set as active mission
    set_active_mission(mission_id)

    # Verify active mission
    assert get_active_mission() == mission_id

    # Update session
    update_session_state(mission_id, focus="wp:WP01", drive_intent="active")

    # Validate
    state = validate_session_before_command(mission_id)
    assert state.focus == "wp:WP01"
    assert state.drive_intent == "active"

    # Verify file permissions
    session_path = get_session_path(mission_id)
    assert oct(session_path.stat().st_mode)[-3:] == "600"


def test_multiple_missions_isolation(tmp_home):
    """Test that multiple missions maintain separate session state."""
    now = datetime.now()

    # Create first mission session
    state1 = SessionState(
        mission_id="mission-1",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ111111",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="developer",
        joined_at=now,
        last_activity_at=now,
        drive_intent="inactive",
        focus="wp:WP01",
    )
    save_session_state("mission-1", state1)

    # Create second mission session
    state2 = SessionState(
        mission_id="mission-2",
        mission_run_id="01HXN8K3M9PQRSTVWXYZ222222",
        participant_id="01HXN8K3M9PQRSTVWXYZ654321",
        role="reviewer",
        joined_at=now,
        last_activity_at=now,
        drive_intent="active",
        focus="wp:WP02",
    )
    save_session_state("mission-2", state2)

    # Verify isolation
    loaded1 = load_session_state("mission-1")
    loaded2 = load_session_state("mission-2")

    assert loaded1 is not None
    assert loaded2 is not None
    assert loaded1.focus == "wp:WP01"
    assert loaded2.focus == "wp:WP02"
    assert loaded1.role == "developer"
    assert loaded2.role == "reviewer"

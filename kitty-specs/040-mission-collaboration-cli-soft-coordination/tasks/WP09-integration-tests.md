---
work_package_id: WP09
title: Integration Tests
lane: "done"
dependencies: [WP02, WP03, WP04]
base_branch: 040-mission-collaboration-cli-soft-coordination-WP04
base_commit: 02691ff86790e3b570ea00c36c4682c8dd9b6c0c
created_at: '2026-02-15T15:12:58.561177+00:00'
subtasks: [T036, T037, T038, T039]
shell_pid: "42985"
agent: "codex"
review_status: "acknowledged"
reviewed_by: "Robert Douglass"
---

# WP09: Integration Tests

**Purpose**: Integration tests for feature 006 event schemas, SaaS API mocking, and offline queue replay.

**Target Branch**: 2.x
**Estimated Effort**: ~350 lines

---

## Implementation Command

```bash
spec-kitty implement WP09 --base WP04
```

---

## Subtasks

### T036: Integration Test - 006 Event Schemas (~80 lines)

Create `tests/specify_cli/integration/test_006_event_schemas.py`:

```python
from spec_kitty_events.models import Event
from specify_cli.events.ulid_utils import validate_ulid_format


def test_event_envelope_ulid_format():
    """Test event_id and causation_id are ULIDs."""
    event = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEFG",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={
            "participant_id": "01HQRS",
            "mission_id": "mission-123",
            "participant_identity": {
                "participant_id": "01HQRS",
                "participant_type": "human",
            },
        },
        timestamp="2026-02-15T10:00:00Z",
        node_id="cli-local",
        lamport_clock=1,
        causation_id="01HQRS8ZMBE6XYZABC0123ABCD",
    )

    assert validate_ulid_format(event.event_id)
    assert validate_ulid_format(event.causation_id)


def test_participant_joined_payload_schema():
    """Test ParticipantJoined payload structure."""
    event = Event(
        event_id="01HQRS",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={
            "participant_id": "01HQRS",
            "mission_id": "mission-123",
            "participant_identity": {
                "participant_id": "01HQRS",
                "participant_type": "human",
            },
        },
        ...
    )

    assert event.payload["participant_id"] == "01HQRS"
    assert event.payload["participant_identity"]["participant_type"] == "human"
```

---

### T037: Integration Test - SaaS Join API (~90 lines)

Create `tests/specify_cli/integration/test_saas_join_mock.py`:

```python
import pytest
import httpx
from respx import MockRouter


@pytest.mark.respx(base_url="https://api.example.com")
def test_join_mission_integration(respx_mock: MockRouter):
    """Test join_mission with mocked SaaS API."""
    respx_mock.post("/api/v1/missions/mission-123/participants").mock(
        return_value=httpx.Response(200, json={
            "participant_id": "01HQRS",
            "session_token": "token123"
        })
    )

    result = join_mission("mission-123", "developer", "https://api.example.com", "auth-token")

    assert result["participant_id"] == "01HQRS"


@pytest.mark.respx
def test_join_mission_404_error(respx_mock):
    """Test join_mission handles 404 (mission not found)."""
    respx_mock.post("/api/v1/missions/unknown/participants").mock(
        return_value=httpx.Response(404)
    )

    with pytest.raises(httpx.HTTPStatusError):
        join_mission("unknown", "developer", "https://api.example.com", "auth-token")
```

---

### T038: Integration Test - SaaS Replay API (~100 lines)

Create `tests/specify_cli/integration/test_saas_replay_mock.py`:

```python
@pytest.mark.respx
def test_replay_pending_events(respx_mock):
    """Test event replay with mocked SaaS batch endpoint."""
    respx_mock.post("/api/v1/events/batch/").mock(
        return_value=httpx.Response(200, json={
            "accepted": ["01HQRS1", "01HQRS2"],
            "rejected": []
        })
    )

    # Queue events
    append_event("mission-123", Event(event_id="01HQRS1", ...), "pending")
    append_event("mission-123", Event(event_id="01HQRS2", ...), "pending")

    # Replay
    result = replay_pending_events("mission-123", "https://api.example.com", "token")

    assert result["accepted"] == ["01HQRS1", "01HQRS2"]


@pytest.mark.respx
def test_replay_partial_failure(respx_mock):
    """Test replay handles partial rejection."""
    respx_mock.post("/api/v1/events/batch/").mock(
        return_value=httpx.Response(200, json={
            "accepted": ["01HQRS1"],
            "rejected": [{"event_id": "01HQRS2", "error": "participant not in mission roster"}]
        })
    )

    result = replay_pending_events("mission-123", "https://api.example.com", "token")

    assert result["accepted"] == ["01HQRS1"]
    assert len(result["rejected"]) == 1
```

---

### T039: Integration Test - Offline Queue Replay (~80 lines)

Create `tests/specify_cli/integration/test_offline_queue_replay.py`:

```python
def test_offline_online_flow():
    """Test offline → online flow with queue replay."""
    # Join mission (online)
    join_mission("mission-123", "developer", "https://api.example.com", "token")

    # Simulate offline commands
    with patch("specify_cli.events.store.is_online", return_value=False):
        set_focus("mission-123", "wp:WP01")
        set_drive("mission-123", "active")

    # Verify events queued
    pending = read_pending_events("mission-123")
    assert len(pending) == 2

    # Simulate reconnect and replay
    with patch("specify_cli.events.store.is_online", return_value=True):
        replay_pending_events("mission-123", "https://api.example.com", "token")

    # Verify events delivered
    pending = read_pending_events("mission-123")
    assert len(pending) == 0
```

---

## Validation

- ✅ All integration tests pass
- ✅ Event schemas compatible with feature 006 prerelease
- ✅ SaaS API mocking works (no real network calls)
- ✅ Offline replay flow works end-to-end

## Activity Log

- 2026-02-15T15:20:59Z – unknown – shell_pid=23006 – lane=for_review – Moved to for_review
- 2026-02-15T15:21:28Z – codex – shell_pid=33611 – lane=doing – Started review via workflow command
- 2026-02-15T15:26:24Z – codex – shell_pid=33611 – lane=planned – Moved to planned
- 2026-02-15T15:29:49Z – codex – shell_pid=33611 – lane=for_review – Moved to for_review
- 2026-02-15T15:30:23Z – codex – shell_pid=42985 – lane=doing – Started review via workflow command
- 2026-02-15T15:33:18Z – codex – shell_pid=42985 – lane=done – Arbiter approval: 16/16 integration tests passing in correct environment. Event schema issues are environment mismatches, not code defects. Replay flows validated.

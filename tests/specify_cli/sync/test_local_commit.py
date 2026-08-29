"""Unit tests for ``specify_cli.sync.local_commit``.

Covers all nine behaviours from the WP05 spec (T024):

1. emit stages the frame and performs no immediate send (was: "emit when connected —
   frame stored AND sent"; #3030 FR-032 deleted that send, see the test for why)
2. emit when disconnected — frame stored only, no send
3. flush sends frames in chronological (committed_at) order
4. ack removes entry and updates confirmed hash
5. amended commit (same build_id) replaces prior pending entry
6. load from non-existent file returns empty SyncState (no exception)
7. save / load round-trip preserves all fields
8. a global git-hash watermark cannot suppress an exact pending frame
9. record_local_commit_ack leaves other pending entries intact

These are the **lifecycle** behaviours — local capture, amend replacement,
chronological ordering, exact Ack bookkeeping, and PII absence. The flush cases
give the temporary project a real opt-in because hosted egress, unlike capture,
requires it. Denial and frame-owned identity are pinned separately in
``test_local_commit_consent_3030.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import FormatChecker

from specify_cli.sync.local_commit import (
    SyncState,
    emit_local_commit,
    flush_pending_local_commits,
    load_sync_state,
    record_local_commit_ack,
    save_sync_state,
    validate_rfc3339_datetime,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.unit, pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HASH_A = "a" * 40
_HASH_B = "b" * 40
_HASH_C = "c" * 40
_MISSION_ID = "01HT1AAAAAAAAAAAAAAAAAAAAAA"
_BUILD_ID_1 = "01HT1BBBBBBBBBBBBBBBBBBBBB1"
_BUILD_ID_2 = "01HT1BBBBBBBBBBBBBBBBBBBBB2"
_PROJECT_UUID = "11111111-2222-3333-4444-555555555555"
_FILES = ["kitty-specs/m/decisions.events.jsonl"]
_AT_1 = "2026-06-01T07:00:00Z"
_AT_2 = "2026-06-01T08:00:00Z"
_AT_3 = "2026-06-01T09:00:00Z"


@pytest.fixture(autouse=True)
def _isolated_consent_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the machine-global consent index out of the developer's real home.

    Without this the consent gate would consult (and reconcile) whatever the machine
    running the suite happens to have recorded, making these tests answer differently
    on different machines.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "_home"))
    (tmp_path / "_home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)


def _make_frame(
    git_hash: str = _HASH_A,
    mission_id: str = _MISSION_ID,
    build_id: str = _BUILD_ID_1,
    changed_files: list[str] | None = None,
    committed_at: str = _AT_1,
) -> dict[str, Any]:
    return {
        "type": "LocalCommit",
        "git_hash": git_hash,
        "mission_id": mission_id,
        "build_id": build_id,
        "project_uuid": _PROJECT_UUID,
        "changed_files": changed_files or _FILES,
        "committed_at": committed_at,
    }


class _RecordingClient:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_local_commit(self, frame: dict[str, Any]) -> bool:
        self.sent.append(frame)
        return True


def _kittify(tmp_path: Path) -> None:
    """Make *tmp_path* a checkout that has identity and has opted in to hosted sync.

    ``sync.enabled`` is the one canonical project-local consent key (``sync/consent.py``).
    """
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    (tmp_path / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {_PROJECT_UUID}\n  slug: local-commit-fixture\n  node_id: 0123456789ab\nsync:\n  enabled: true\n",
        encoding="utf-8",
    )
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(_PROJECT_UUID, actor="test:local-commit")


# ---------------------------------------------------------------------------
# T024-1  load from non-existent file returns empty SyncState
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_empty_state(tmp_path: Path) -> None:
    state = load_sync_state(tmp_path)
    assert state.last_saas_confirmed_hash is None
    assert state.pending_local_commits == []


# ---------------------------------------------------------------------------
# T024-2  save / load round-trip
# ---------------------------------------------------------------------------


def test_save_load_round_trip(tmp_path: Path) -> None:
    _kittify(tmp_path)
    original = SyncState(
        last_saas_confirmed_hash=_HASH_A,
        pending_local_commits=[_make_frame()],
    )
    save_sync_state(tmp_path, original)
    loaded = load_sync_state(tmp_path)
    assert loaded.last_saas_confirmed_hash == _HASH_A
    assert len(loaded.pending_local_commits) == 1
    assert loaded.pending_local_commits[0]["git_hash"] == _HASH_A


# ---------------------------------------------------------------------------
# T024-3  malformed file returns empty state
# ---------------------------------------------------------------------------


def test_load_malformed_file_returns_empty_state(tmp_path: Path) -> None:
    _kittify(tmp_path)
    path = tmp_path / ".kittify" / "sync-state.json"
    path.write_text("{not valid json}", encoding="utf-8")
    state = load_sync_state(tmp_path)
    assert state.last_saas_confirmed_hash is None
    assert state.pending_local_commits == []


# ---------------------------------------------------------------------------
# T024-4  emit when disconnected — frame stored, send NOT called
# ---------------------------------------------------------------------------


def test_emit_when_disconnected_stores_only(tmp_path: Path) -> None:
    _kittify(tmp_path)
    # No ``_get_saas_client`` patch any more: #3030 FR-032 deleted that helper and the
    # immediate send it fed, so "disconnected" is now the only state ``emit`` has.
    emit_local_commit(
        tmp_path,
        _HASH_A,
        _MISSION_ID,
        _BUILD_ID_1,
        _FILES,
        _AT_1,
    )

    state = load_sync_state(tmp_path)
    assert len(state.pending_local_commits) == 1
    frame = state.pending_local_commits[0]
    assert frame["type"] == "LocalCommit"
    assert frame["git_hash"] == _HASH_A
    assert frame["mission_id"] == _MISSION_ID
    assert frame["build_id"] == _BUILD_ID_1
    assert frame["changed_files"] == _FILES
    assert frame["committed_at"] == _AT_1


# ---------------------------------------------------------------------------
# T024-5  emit stages the frame and sends nothing (#3030 FR-032)
# ---------------------------------------------------------------------------


def test_emit_stages_the_frame_and_performs_no_immediate_send(tmp_path: Path) -> None:
    """Replaces ``test_emit_when_connected_stores_and_sends``.

    That case pinned an immediate send that **production could never reach**: the only
    client source was ``token_manager._ws_client``, an attribute nothing in ``src/``
    assigns, so the test's own injection was the only thing that ever made it fire.
    It was green for a behaviour that did not exist, and it would have gone green
    again the moment someone assigned the phantom — the very event #3030 FR-032
    exists to make impossible.

    Kept as a live pin in the opposite direction: ``emit_local_commit`` stages, and
    the *flush* sends. A future immediate send re-added here reds this test.
    """
    _kittify(tmp_path)
    emit_local_commit(
        tmp_path,
        _HASH_A,
        _MISSION_ID,
        _BUILD_ID_1,
        _FILES,
        _AT_1,
    )

    # Frame still stored as pending (for the on-connect flush + ack-based removal).
    state = load_sync_state(tmp_path)
    assert len(state.pending_local_commits) == 1
    assert state.pending_local_commits[0]["git_hash"] == _HASH_A


# ---------------------------------------------------------------------------
# T024-6  amended commit replaces prior pending entry (same build_id)
# ---------------------------------------------------------------------------


def test_amended_commit_replaces_prior_pending_entry(tmp_path: Path) -> None:
    _kittify(tmp_path)
    # Original commit
    emit_local_commit(tmp_path, _HASH_A, _MISSION_ID, _BUILD_ID_1, _FILES, _AT_1)
    # Amended commit: same build_id, new git_hash
    emit_local_commit(tmp_path, _HASH_B, _MISSION_ID, _BUILD_ID_1, _FILES, _AT_2)

    state = load_sync_state(tmp_path)
    assert len(state.pending_local_commits) == 1, "amend must replace, not append"
    assert state.pending_local_commits[0]["git_hash"] == _HASH_B


# ---------------------------------------------------------------------------
# T024-7  two different build_ids keep separate entries
# ---------------------------------------------------------------------------


def test_different_build_ids_keep_separate_entries(tmp_path: Path) -> None:
    _kittify(tmp_path)
    emit_local_commit(tmp_path, _HASH_A, _MISSION_ID, _BUILD_ID_1, _FILES, _AT_1)
    emit_local_commit(tmp_path, _HASH_B, _MISSION_ID, _BUILD_ID_2, _FILES, _AT_2)

    state = load_sync_state(tmp_path)
    assert len(state.pending_local_commits) == 2


# ---------------------------------------------------------------------------
# T024-8  flush sends frames in chronological order
# ---------------------------------------------------------------------------


def test_flush_sends_in_chronological_order(tmp_path: Path) -> None:
    _kittify(tmp_path)
    # Pre-populate three frames out of order
    state = SyncState(
        pending_local_commits=[
            _make_frame(_HASH_C, committed_at=_AT_3),
            _make_frame(_HASH_A, build_id=_BUILD_ID_1, committed_at=_AT_1),
            _make_frame(_HASH_B, build_id=_BUILD_ID_2, committed_at=_AT_2),
        ]
    )
    save_sync_state(tmp_path, state)

    client = _RecordingClient()
    flush_pending_local_commits(tmp_path, client)

    assert [frame["git_hash"] for frame in client.sent] == [
        _HASH_A,
        _HASH_B,
        _HASH_C,
    ]


# ---------------------------------------------------------------------------
# T024-9  flush skips frame matching last_saas_confirmed_hash
# ---------------------------------------------------------------------------


def test_flush_does_not_use_global_hash_watermark_as_project_authority(
    tmp_path: Path,
) -> None:
    _kittify(tmp_path)
    state = SyncState(
        last_saas_confirmed_hash=_HASH_A,
        pending_local_commits=[
            _make_frame(_HASH_A, build_id=_BUILD_ID_1, committed_at=_AT_1),
            _make_frame(_HASH_B, build_id=_BUILD_ID_2, committed_at=_AT_2),
        ],
    )
    save_sync_state(tmp_path, state)

    client = _RecordingClient()
    flush_pending_local_commits(tmp_path, client)

    # A bare historical hash has no project/build authority. Pending exact rows
    # remain eligible until their own full acknowledgement removes them.
    assert [frame["git_hash"] for frame in client.sent] == [_HASH_A, _HASH_B]


# ---------------------------------------------------------------------------
# T024-10  record_local_commit_ack removes entry, updates confirmed hash
# ---------------------------------------------------------------------------


def test_ack_removes_entry_and_updates_confirmed_hash(tmp_path: Path) -> None:
    state = SyncState(
        pending_local_commits=[
            _make_frame(_HASH_A, build_id=_BUILD_ID_1, committed_at=_AT_1),
            _make_frame(_HASH_B, build_id=_BUILD_ID_2, committed_at=_AT_2),
        ]
    )
    save_sync_state(tmp_path, state)

    frame = state.pending_local_commits[0]
    acknowledgement = {
        **{field: frame[field] for field in ("git_hash", "build_id", "project_uuid")},
        "type": "LocalCommitAck",
        "status": "accepted",
        "admission_generation": 9,
        "binding_audience": "private-teamspace:teamspace-1",
        "received_at": "2026-08-11T12:00:01+00:00",
    }
    expected = {
        **frame,
        "admission_generation": 9,
        "binding_audience": "private-teamspace:teamspace-1",
    }
    assert record_local_commit_ack(
        tmp_path,
        acknowledgement,
        expected_frame=expected,
    )

    updated = load_sync_state(tmp_path)
    assert updated.last_saas_confirmed_hash == _HASH_A
    assert len(updated.pending_local_commits) == 1
    assert updated.pending_local_commits[0]["git_hash"] == _HASH_B


@pytest.mark.parametrize(
    "received_at",
    [
        "2026-08-11T12:00:01",
        "2026-08-11 12:00:01+00:00",
        "2026-02-30T12:00:01Z",
    ],
)
def test_invalid_ack_datetime_does_not_remove_queue(
    tmp_path: Path,
    received_at: str,
) -> None:
    frame = _make_frame(_HASH_A, build_id=_BUILD_ID_1, committed_at=_AT_1)
    save_sync_state(tmp_path, SyncState(pending_local_commits=[frame]))
    acknowledgement = {
        **{field: frame[field] for field in ("git_hash", "build_id", "project_uuid")},
        "type": "LocalCommitAck",
        "status": "accepted",
        "admission_generation": 9,
        "binding_audience": "private-teamspace:teamspace-1",
        "received_at": received_at,
    }
    expected = {
        **frame,
        "admission_generation": 9,
        "binding_audience": "private-teamspace:teamspace-1",
    }

    assert not record_local_commit_ack(
        tmp_path,
        acknowledgement,
        expected_frame=expected,
    )
    assert load_sync_state(tmp_path).pending_local_commits == [frame]


@pytest.mark.parametrize(
    "value",
    [
        "2026-08-11T12:00:01Z",
        "2026-08-11T14:00:01+02:00",
        "2026-08-11t12:00:01+00:00",
        "2026-08-11T12:00:01z",
        "2026-08-11t12:00:01z",
    ],
)
def test_strict_rfc3339_validator_accepts_contract_controls(value: str) -> None:
    assert validate_rfc3339_datetime(value, field_name="test") == value


@pytest.mark.parametrize(
    "value",
    [
        "2026-08-11T12:00:01",
        "2026-08-11 12:00:01+00:00",
        "2026-02-30T12:00:01Z",
    ],
)
def test_strict_rfc3339_validator_rejects_loose_iso_forms(value: str) -> None:
    with pytest.raises(ValueError, match="strict RFC3339"):
        validate_rfc3339_datetime(value, field_name="test")


@pytest.mark.parametrize(
    ("value", "accepted"),
    [
        ("2026-08-11T12:00:01Z", True),
        ("2026-08-11T14:00:01+02:00", True),
        ("2026-08-11t12:00:01+00:00", True),
        ("2026-08-11T12:00:01z", True),
        ("2026-08-11t12:00:01z", True),
        ("2026-08-11T12:00:01", False),
        ("2026-08-11 12:00:01+00:00", False),
        ("2026-02-30T12:00:01Z", False),
    ],
)
def test_strict_validator_matches_live_jsonschema_format_checker(
    value: str,
    accepted: bool,
) -> None:
    checker_accepts = FormatChecker().conforms(value, "date-time")
    assert checker_accepts is accepted
    if accepted:
        assert validate_rfc3339_datetime(value, field_name="test") == value
    else:
        with pytest.raises(ValueError):
            validate_rfc3339_datetime(value, field_name="test")


# ---------------------------------------------------------------------------
# T024-11  no PII in frame or state file
# ---------------------------------------------------------------------------


def test_no_pii_in_frame_or_state_file(tmp_path: Path) -> None:
    _kittify(tmp_path)
    emit_local_commit(
        tmp_path,
        _HASH_A,
        _MISSION_ID,
        _BUILD_ID_1,
        _FILES,
        _AT_1,
    )

    raw = (tmp_path / ".kittify" / "sync-state.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    frame = data["pending_local_commits"][0]

    pii_keys = {"machine_name", "hostname", "workspace_path", "username", "email"}
    assert not pii_keys.intersection(frame.keys()), f"PII fields found in frame: {pii_keys.intersection(frame.keys())}"


# ---------------------------------------------------------------------------
# T024-12  atomic write: state file is valid JSON after save
# ---------------------------------------------------------------------------


def test_save_produces_valid_json(tmp_path: Path) -> None:
    state = SyncState(
        last_saas_confirmed_hash=_HASH_A,
        pending_local_commits=[_make_frame()],
    )
    save_sync_state(tmp_path, state)
    raw = (tmp_path / ".kittify" / "sync-state.json").read_text(encoding="utf-8")
    parsed = json.loads(raw)  # raises if not valid JSON
    assert parsed["last_saas_confirmed_hash"] == _HASH_A
    assert len(parsed["pending_local_commits"]) == 1

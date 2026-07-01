"""Unit tests for ``specify_cli.sync.local_commit``.

Covers all nine behaviours from the WP05 spec (T024):

1. emit when connected — frame stored AND sent
2. emit when disconnected — frame stored only, no send
3. flush sends frames in chronological (committed_at) order
4. ack removes entry and updates confirmed hash
5. amended commit (same build_id) replaces prior pending entry
6. load from non-existent file returns empty SyncState (no exception)
7. save / load round-trip preserves all fields
8. flush skips frame whose git_hash matches last_saas_confirmed_hash
9. record_local_commit_ack leaves other pending entries intact
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from specify_cli.sync.local_commit import (
    SyncState,
    emit_local_commit,
    flush_pending_local_commits,
    load_sync_state,
    record_local_commit_ack,
    save_sync_state,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HASH_A = "a" * 40
_HASH_B = "b" * 40
_HASH_C = "c" * 40
_MISSION_ID = "01HT1AAAAAAAAAAAAAAAAAAAAAA"
_BUILD_ID_1 = "01HT1BBBBBBBBBBBBBBBBBBBBB1"
_BUILD_ID_2 = "01HT1BBBBBBBBBBBBBBBBBBBBB2"
_FILES = ["kitty-specs/m/decisions.events.jsonl"]
_AT_1 = "2026-06-01T07:00:00Z"
_AT_2 = "2026-06-01T08:00:00Z"
_AT_3 = "2026-06-01T09:00:00Z"


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
        "changed_files": changed_files or _FILES,
        "committed_at": committed_at,
    }


def _kittify(tmp_path: Path) -> None:
    (tmp_path / ".kittify").mkdir(exist_ok=True)


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
    with patch(
        "specify_cli.sync.local_commit._get_saas_client",
        return_value=None,
    ):
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
# T024-5  emit when connected — frame stored AND sent
# ---------------------------------------------------------------------------


def test_emit_when_connected_stores_and_sends(tmp_path: Path) -> None:
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.send_event = AsyncMock()

    with (
        patch("specify_cli.sync.local_commit._get_saas_client", return_value=mock_client),
        patch(
            "specify_cli.sync.local_commit._send_event",
        ) as mock_send,
    ):
        emit_local_commit(
            tmp_path,
            _HASH_A,
            _MISSION_ID,
            _BUILD_ID_1,
            _FILES,
            _AT_1,
        )
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] is mock_client
        sent_frame = call_args[0][1]
        assert sent_frame["type"] == "LocalCommit"
        assert sent_frame["git_hash"] == _HASH_A

    # Frame also stored as pending (for ack-based removal)
    state = load_sync_state(tmp_path)
    assert len(state.pending_local_commits) == 1


# ---------------------------------------------------------------------------
# T024-6  amended commit replaces prior pending entry (same build_id)
# ---------------------------------------------------------------------------


def test_amended_commit_replaces_prior_pending_entry(tmp_path: Path) -> None:
    with patch("specify_cli.sync.local_commit._get_saas_client", return_value=None):
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
    with patch("specify_cli.sync.local_commit._get_saas_client", return_value=None):
        emit_local_commit(tmp_path, _HASH_A, _MISSION_ID, _BUILD_ID_1, _FILES, _AT_1)
        emit_local_commit(tmp_path, _HASH_B, _MISSION_ID, _BUILD_ID_2, _FILES, _AT_2)

    state = load_sync_state(tmp_path)
    assert len(state.pending_local_commits) == 2


# ---------------------------------------------------------------------------
# T024-8  flush sends frames in chronological order
# ---------------------------------------------------------------------------


def test_flush_sends_in_chronological_order(tmp_path: Path) -> None:
    # Pre-populate three frames out of order
    state = SyncState(
        pending_local_commits=[
            _make_frame(_HASH_C, committed_at=_AT_3),
            _make_frame(_HASH_A, build_id=_BUILD_ID_1, committed_at=_AT_1),
            _make_frame(_HASH_B, build_id=_BUILD_ID_2, committed_at=_AT_2),
        ]
    )
    save_sync_state(tmp_path, state)

    send_order: list[str] = []

    def _fake_send(client: Any, frame: dict[str, Any]) -> None:
        send_order.append(frame["git_hash"])

    mock_client = MagicMock()

    with patch("specify_cli.sync.local_commit._send_event", side_effect=_fake_send):
        flush_pending_local_commits(tmp_path, mock_client)

    assert send_order == [_HASH_A, _HASH_B, _HASH_C]


# ---------------------------------------------------------------------------
# T024-9  flush skips frame matching last_saas_confirmed_hash
# ---------------------------------------------------------------------------


def test_flush_skips_confirmed_hash(tmp_path: Path) -> None:
    state = SyncState(
        last_saas_confirmed_hash=_HASH_A,
        pending_local_commits=[
            _make_frame(_HASH_A, build_id=_BUILD_ID_1, committed_at=_AT_1),
            _make_frame(_HASH_B, build_id=_BUILD_ID_2, committed_at=_AT_2),
        ],
    )
    save_sync_state(tmp_path, state)

    sent: list[str] = []

    def _fake_send(client: Any, frame: dict[str, Any]) -> None:
        sent.append(frame["git_hash"])

    with patch("specify_cli.sync.local_commit._send_event", side_effect=_fake_send):
        flush_pending_local_commits(tmp_path, MagicMock())

    # Only the unconfirmed frame should be sent
    assert sent == [_HASH_B]


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

    record_local_commit_ack(tmp_path, _HASH_A)

    updated = load_sync_state(tmp_path)
    assert updated.last_saas_confirmed_hash == _HASH_A
    assert len(updated.pending_local_commits) == 1
    assert updated.pending_local_commits[0]["git_hash"] == _HASH_B


# ---------------------------------------------------------------------------
# T024-11  no PII in frame or state file
# ---------------------------------------------------------------------------


def test_no_pii_in_frame_or_state_file(tmp_path: Path) -> None:
    with patch("specify_cli.sync.local_commit._get_saas_client", return_value=None):
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
    assert not pii_keys.intersection(frame.keys()), (
        f"PII fields found in frame: {pii_keys.intersection(frame.keys())}"
    )


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

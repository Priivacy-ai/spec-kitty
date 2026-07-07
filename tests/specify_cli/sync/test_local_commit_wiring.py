"""Integration tests for the LocalCommit wiring points (WP06).

Tests three integration points:
1. ``safe_commit()`` emits a ``LocalCommit`` frame when paths are under ``kitty-specs/``
2. ``WebSocketClient._handle_message()`` dispatches ``LocalCommitAck`` to ``record_local_commit_ack``
3. ``WebSocketClient.connect()`` calls ``flush_pending_local_commits`` after snapshot

FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from specify_cli.git.commit_helpers import (
    CommitResult,
    safe_commit,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Git repo fixture (mirrors the one in test_commit_helpers.py)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(repo: Path, branch: str = "kitty/mission-test-01ABCDEF") -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", branch)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial commit")


@pytest.fixture
def lane_repo(tmp_path: Path) -> Path:
    """Return a non-protected lane branch repo."""
    _init_repo(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# T028a — safe_commit() emits for kitty-specs/ paths
# ---------------------------------------------------------------------------


def test_safe_commit_emits_local_commit_for_kitty_specs_path(lane_repo: Path) -> None:
    """safe_commit() calls emit_local_commit() when any committed path is under kitty-specs/."""
    # Create the file to commit
    kitty_path = lane_repo / "kitty-specs" / "my-mission-01KT119Y" / "status.events.jsonl"
    kitty_path.parent.mkdir(parents=True)
    kitty_path.write_text('{"event": "test"}\n', encoding="utf-8")

    # Patch at the source module level since it is lazily imported inside safe_commit
    with patch("specify_cli.sync.local_commit.emit_local_commit") as mock_emit:
        result = safe_commit(
            repo_root=lane_repo,
            worktree_root=lane_repo,
            destination_ref="kitty/mission-test-01ABCDEF",
            message="chore: test commit",
            paths=(kitty_path,),
        )

    assert isinstance(result, CommitResult)
    mock_emit.assert_called_once()

    call_kwargs = mock_emit.call_args.kwargs
    assert "my-mission-01KT119Y" in call_kwargs["mission_id"]
    assert any(
        "kitty-specs/my-mission-01KT119Y/status.events.jsonl" in f
        or "kitty-specs\\my-mission-01KT119Y\\status.events.jsonl" in f
        for f in call_kwargs["changed_files"]
    )
    assert call_kwargs["git_hash"] == result.sha
    assert "committed_at" in call_kwargs


def test_safe_commit_does_not_emit_for_non_kitty_specs_paths(lane_repo: Path) -> None:
    """safe_commit() does NOT call emit_local_commit() for paths outside kitty-specs/."""
    other_path = lane_repo / "src" / "module.py"
    other_path.parent.mkdir(parents=True)
    other_path.write_text("# code\n", encoding="utf-8")

    with patch("specify_cli.sync.local_commit.emit_local_commit") as mock_emit:
        result = safe_commit(
            repo_root=lane_repo,
            worktree_root=lane_repo,
            destination_ref="kitty/mission-test-01ABCDEF",
            message="feat: add module",
            paths=(other_path,),
        )

    assert isinstance(result, CommitResult)
    mock_emit.assert_not_called()


def test_safe_commit_emit_failure_does_not_abort_commit(lane_repo: Path) -> None:
    """If emit_local_commit raises, safe_commit still returns CommitResult successfully."""
    kitty_path = lane_repo / "kitty-specs" / "some-mission" / "file.jsonl"
    kitty_path.parent.mkdir(parents=True)
    kitty_path.write_text('{"x": 1}\n', encoding="utf-8")

    with patch(
        "specify_cli.sync.local_commit.emit_local_commit",
        side_effect=RuntimeError("network error"),
    ):
        # Should NOT raise despite emit failing
        result = safe_commit(
            repo_root=lane_repo,
            worktree_root=lane_repo,
            destination_ref="kitty/mission-test-01ABCDEF",
            message="chore: test",
            paths=(kitty_path,),
        )

    assert isinstance(result, CommitResult)
    assert result.sha  # commit was created


def test_derive_mission_id_extracts_slug_from_path() -> None:
    """_derive_mission_id correctly extracts mission slugs from kitty-specs/ paths."""
    from specify_cli.git.commit_helpers import _derive_mission_id

    assert _derive_mission_id(["kitty-specs/my-mission-01KT119Y/f.jsonl"]) == "my-mission-01KT119Y"
    assert _derive_mission_id(["kitty-specs/simple/file.md"]) == "simple"
    # With version suffix and hyphens
    assert _derive_mission_id(["kitty-specs/event-architecture-cli-git-truth-01KT119Y/x"]) == "event-architecture-cli-git-truth-01KT119Y"
    # Empty on bad input
    assert _derive_mission_id([]) == ""
    assert _derive_mission_id(["src/other/file.py"]) == ""


# ---------------------------------------------------------------------------
# T028b — LocalCommitAck dispatch in _handle_message
# ---------------------------------------------------------------------------


def test_handle_message_dispatches_local_commit_ack() -> None:
    """WebSocketClient._handle_message routes LocalCommitAck to _handle_local_commit_ack."""
    from specify_cli.sync.client import WebSocketClient

    client = WebSocketClient(repo_root=Path("/nonexistent/fake-repo"))

    with patch.object(client, "_handle_local_commit_ack", new_callable=AsyncMock) as mock_ack:
        asyncio.run(client._handle_message({"type": "LocalCommitAck", "git_hash": "abc123"}))

    mock_ack.assert_called_once_with({"type": "LocalCommitAck", "git_hash": "abc123"})


def test_handle_local_commit_ack_calls_record(tmp_path: Path) -> None:
    """_handle_local_commit_ack calls record_local_commit_ack with the correct hash.

    Patches at the source module so the lazy import inside the method gets the mock.
    """
    from specify_cli.sync.client import WebSocketClient

    client = WebSocketClient(repo_root=tmp_path)

    # Patch at the source module level — the lazy `from ... import` will resolve
    # to this mock since sys.modules already has the module cached.
    with patch("specify_cli.sync.local_commit.record_local_commit_ack") as mock_record:
        asyncio.run(client._handle_local_commit_ack({"type": "LocalCommitAck", "git_hash": "deadbeef"}))

    mock_record.assert_called_once_with(tmp_path, "deadbeef")


def test_handle_local_commit_ack_integration(tmp_path: Path) -> None:
    """_handle_local_commit_ack writes to sync-state.json via record_local_commit_ack."""
    from specify_cli.sync.client import WebSocketClient
    from specify_cli.sync.local_commit import SyncState, load_sync_state, save_sync_state

    # Pre-populate sync-state with a pending entry
    state = SyncState(
        last_saas_confirmed_hash=None,
        pending_local_commits=[
            {
                "type": "LocalCommit",
                "git_hash": "deadbeef" * 5,
                "mission_id": "m1",
                "build_id": "b1",
                "changed_files": ["kitty-specs/m1/f.jsonl"],
                "committed_at": "2026-06-01T10:00:00Z",
            }
        ],
    )
    save_sync_state(tmp_path, state)

    client = WebSocketClient(repo_root=tmp_path)
    asyncio.run(client._handle_local_commit_ack({"type": "LocalCommitAck", "git_hash": "deadbeef" * 5}))

    updated = load_sync_state(tmp_path)
    assert updated.last_saas_confirmed_hash == "deadbeef" * 5
    assert updated.pending_local_commits == []


def test_handle_local_commit_ack_missing_hash_does_not_raise(tmp_path: Path) -> None:
    """_handle_local_commit_ack silently ignores frames without git_hash."""
    from specify_cli.sync.client import WebSocketClient

    client = WebSocketClient(repo_root=tmp_path)
    # Should not raise, should not write anything
    asyncio.run(client._handle_local_commit_ack({"type": "LocalCommitAck"}))
    # sync-state.json should not be created
    assert not (tmp_path / ".kittify" / "sync-state.json").exists()


def test_handle_local_commit_ack_never_raises_on_error(tmp_path: Path) -> None:
    """_handle_local_commit_ack swallows all exceptions to protect the listener loop."""
    from specify_cli.sync.client import WebSocketClient

    client = WebSocketClient(repo_root=tmp_path)

    with patch(
        "specify_cli.sync.local_commit.record_local_commit_ack",
        side_effect=OSError("disk full"),
    ):
        # Should NOT raise
        asyncio.run(client._handle_local_commit_ack({"type": "LocalCommitAck", "git_hash": "abc"}))


# ---------------------------------------------------------------------------
# T028c — flush_pending_local_commits called on connect
# ---------------------------------------------------------------------------


async def _make_ws_mock() -> MagicMock:
    """Async factory that returns a fake websocket connection."""
    return MagicMock()


def test_connect_calls_flush_pending_local_commits(tmp_path: Path) -> None:
    """WebSocketClient.connect() calls flush_pending_local_commits after snapshot."""
    from specify_cli.sync.client import WebSocketClient

    client = WebSocketClient(repo_root=tmp_path)

    # websockets.connect() is an async function that returns a connection object directly.
    mock_ws = MagicMock()
    mock_ws.send = AsyncMock()

    async def fake_ws_connect(*args, **kwargs):  # noqa: ANN002, ANN003
        return mock_ws

    with (
        patch("specify_cli.sync.client.is_saas_sync_enabled", return_value=True),
        patch(
            "specify_cli.sync.client.resolve_private_team_id_for_ingress",
            return_value="team-123",
        ),
        patch(
            "specify_cli.sync.client.provision_ws_token",
            new_callable=AsyncMock,
            return_value={"ws_url": "wss://localhost/ws", "ws_token": "tok"},
        ),
        patch("specify_cli.sync.client.websockets.connect", side_effect=fake_ws_connect),
        patch.object(client, "_receive_snapshot", new_callable=AsyncMock),
        patch(
            "specify_cli.sync.local_commit.flush_pending_local_commits"
        ) as mock_flush,
    ):
        asyncio.run(client.connect())

    mock_flush.assert_called_once_with(tmp_path, client)


def test_connect_flush_failure_does_not_prevent_connection(tmp_path: Path) -> None:
    """If flush_pending_local_commits raises, connect() still succeeds."""
    from specify_cli.sync.client import WebSocketClient

    client = WebSocketClient(repo_root=tmp_path)

    mock_ws = MagicMock()

    async def fake_ws_connect(*args, **kwargs):  # noqa: ANN002, ANN003
        return mock_ws

    with (
        patch("specify_cli.sync.client.is_saas_sync_enabled", return_value=True),
        patch(
            "specify_cli.sync.client.resolve_private_team_id_for_ingress",
            return_value="team-123",
        ),
        patch(
            "specify_cli.sync.client.provision_ws_token",
            new_callable=AsyncMock,
            return_value={"ws_url": "wss://localhost/ws", "ws_token": "tok"},
        ),
        patch("specify_cli.sync.client.websockets.connect", side_effect=fake_ws_connect),
        patch.object(client, "_receive_snapshot", new_callable=AsyncMock),
        patch(
            "specify_cli.sync.local_commit.flush_pending_local_commits",
            side_effect=RuntimeError("flush boom"),
        ),
    ):
        # Should NOT raise despite flush failing
        asyncio.run(client.connect())

    assert client.connected is True

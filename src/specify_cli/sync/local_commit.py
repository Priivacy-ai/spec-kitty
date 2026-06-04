"""LocalCommit core: SyncState persistence and frame emission.

Implements the ``LocalCommit`` WebSocket frame lifecycle:
- ``SyncState`` dataclass: persists to ``.kittify/sync-state.json``
- ``emit_local_commit()``: stores frame + sends if WebSocket is connected
- ``flush_pending_local_commits()``: replays pending frames on connect
- ``record_local_commit_ack()``: removes acked entry; updates confirmed hash
- Amended-commit handling: same ``build_id`` → replace prior pending entry

No PII is stored: the frame contains only a git hash, ULID IDs, file paths
within the project, and an ISO timestamp.  No machine name, hostname, or
developer identity appears in any frame or state file.

FR-010–FR-017.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
import datetime as _dt
from datetime import datetime
from pathlib import Path
from typing import Any

from specify_cli.core.atomic import atomic_write

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SyncState dataclass
# ---------------------------------------------------------------------------


@dataclass
class SyncState:
    """Persistent local sync state for the ``LocalCommit`` frame pipeline.

    Attributes
    ----------
    last_saas_confirmed_hash:
        The most-recently acknowledged git hash from SaaS, or ``None`` if no
        acknowledgement has been received yet.
    pending_local_commits:
        Ordered list of ``LocalCommit`` frame dicts awaiting acknowledgement.
        Each entry mirrors the wire-format frame exactly.
    """

    last_saas_confirmed_hash: str | None = None
    pending_local_commits: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------


def _sync_state_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "sync-state.json"


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def load_sync_state(repo_root: Path) -> SyncState:
    """Load ``SyncState`` from ``.kittify/sync-state.json``.

    Returns an empty ``SyncState`` if the file does not exist or is malformed.
    Never raises.
    """
    path = _sync_state_path(repo_root)
    if not path.exists():
        return SyncState()
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return SyncState(
            last_saas_confirmed_hash=data.get("last_saas_confirmed_hash"),
            pending_local_commits=list(data.get("pending_local_commits", [])),
        )
    except Exception:  # noqa: BLE001
        logger.warning("sync-state.json is malformed; resetting to empty state")
        return SyncState()


def save_sync_state(repo_root: Path, state: SyncState) -> None:
    """Persist *state* atomically to ``.kittify/sync-state.json``."""
    path = _sync_state_path(repo_root)
    data: dict[str, Any] = {
        "last_saas_confirmed_hash": state.last_saas_confirmed_hash,
        "pending_local_commits": state.pending_local_commits,
    }
    atomic_write(path, json.dumps(data, indent=2), mkdir=True)


# ---------------------------------------------------------------------------
# emit_local_commit
# ---------------------------------------------------------------------------


def emit_local_commit(
    repo_root: Path,
    git_hash: str,
    mission_id: str,
    build_id: str,
    changed_files: list[str],
    committed_at: str,
) -> None:
    """Build and dispatch a ``LocalCommit`` frame.

    The frame is **always** stored in ``sync-state.json`` as a pending entry.
    If a WebSocket client is currently connected, the frame is also sent
    immediately.  The pending entry is only removed once ``record_local_commit_ack``
    receives the corresponding acknowledgement — this prevents frame loss when
    a send succeeds but the ack is never delivered.

    If an existing pending entry carries the same ``build_id`` (i.e. the commit
    was amended), it is replaced by the new frame so the list never contains two
    entries for the same build.
    """
    frame: dict[str, Any] = {
        "type": "LocalCommit",
        "git_hash": git_hash,
        "mission_id": mission_id,
        "build_id": build_id,
        "changed_files": changed_files,
        "committed_at": committed_at,
    }

    # Load state, replace any prior pending entry for the same build_id (amend),
    # append the new frame, then persist.
    state = load_sync_state(repo_root)
    state.pending_local_commits = [
        entry
        for entry in state.pending_local_commits
        if entry.get("build_id") != build_id
    ]
    state.pending_local_commits.append(frame)
    save_sync_state(repo_root, state)

    # Attempt immediate send if connected; errors are swallowed so the caller
    # (a git-hook or CLI command) is never interrupted.
    client = _get_saas_client()
    if client is not None:
        try:
            _send_event(client, frame)
        except Exception:  # noqa: BLE001
            logger.debug("LocalCommit send failed; frame retained as pending", exc_info=True)


# ---------------------------------------------------------------------------
# flush_pending_local_commits
# ---------------------------------------------------------------------------


def flush_pending_local_commits(repo_root: Path, client: Any) -> None:
    """Send all unacknowledged pending ``LocalCommit`` frames to *client*.

    Frames are sent in ascending ``committed_at`` (chronological) order.
    Entries whose ``git_hash`` matches ``last_saas_confirmed_hash`` are
    considered already acknowledged and skipped.

    This function is intended to be called once the WebSocket connection is
    established (on-connect replay).
    """
    state = load_sync_state(repo_root)

    unacked = [
        entry
        for entry in state.pending_local_commits
        if entry.get("git_hash") != state.last_saas_confirmed_hash
    ]

    def _sort_key(entry: dict[str, Any]) -> datetime:
        ts: str = entry.get("committed_at", "")
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=_dt.UTC)

    unacked.sort(key=_sort_key)

    for frame in unacked:
        try:
            _send_event(client, frame)
        except Exception:  # noqa: BLE001
            logger.debug("LocalCommit flush send failed for %s", frame.get("git_hash"), exc_info=True)

    logger.debug("Flushed %d pending LocalCommit frame(s)", len(unacked))


# ---------------------------------------------------------------------------
# record_local_commit_ack
# ---------------------------------------------------------------------------


def record_local_commit_ack(repo_root: Path, git_hash: str) -> None:
    """Handle a ``LocalCommitAck`` from SaaS.

    Updates ``last_saas_confirmed_hash`` and removes the corresponding entry
    from ``pending_local_commits``.
    """
    state = load_sync_state(repo_root)
    state.last_saas_confirmed_hash = git_hash
    state.pending_local_commits = [
        entry
        for entry in state.pending_local_commits
        if entry.get("git_hash") != git_hash
    ]
    save_sync_state(repo_root, state)


# ---------------------------------------------------------------------------
# Internal helpers (mirrors invocation/propagator.py)
# ---------------------------------------------------------------------------


def _get_saas_client() -> Any | None:
    """Return a connected WebSocketClient if available; ``None`` otherwise.

    Mirrors ``specify_cli.invocation.propagator._get_saas_client``.
    Never raises.
    """
    try:
        from specify_cli.auth import get_token_manager
        from specify_cli.sync.client import WebSocketClient  # noqa: F401

        token_manager = get_token_manager()
        if not bool(token_manager.is_authenticated):
            return None

        session = token_manager.get_current_session()
        if session is None:
            return None

        client: Any | None = getattr(token_manager, "_ws_client", None)
        if client is None or not getattr(client, "connected", False):
            return None
        return client
    except Exception:  # noqa: BLE001
        return None


def _send_event(client: Any, event_dict: dict[str, Any]) -> None:
    """Send *event_dict* via *client*.

    Mirrors the call pattern in ``specify_cli.invocation.propagator._send_event``:
    use ``asyncio.create_task`` when a loop is running, otherwise fall back to
    ``asyncio.run``.
    """
    import asyncio  # noqa: PLC0415

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(client.send_event(event_dict))
            _PENDING_SEND_TASKS.add(task)
            task.add_done_callback(_PENDING_SEND_TASKS.discard)
            return
        loop.run_until_complete(client.send_event(event_dict))
    except RuntimeError:
        asyncio.run(client.send_event(event_dict))


# Keep scheduled tasks alive until completion (prevents premature GC).
_PENDING_SEND_TASKS: set[Any] = set()


__all__ = [
    "SyncState",
    "load_sync_state",
    "save_sync_state",
    "emit_local_commit",
    "flush_pending_local_commits",
    "record_local_commit_ack",
]

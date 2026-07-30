"""LocalCommit core: SyncState persistence and frame emission.

Implements the ``LocalCommit`` WebSocket frame lifecycle:
- ``SyncState`` dataclass: persists to ``.kittify/sync-state.json``
- ``emit_local_commit()``: stores frame + sends if WebSocket is connected
- ``flush_pending_local_commits()``: replays pending frames on connect
- ``record_local_commit_ack()``: removes acked entry; updates confirmed hash
- Amended-commit handling: same ``build_id`` → replace prior pending entry

No PII is stored: the frame contains only a git hash, ULID IDs, a project uuid,
file paths within the project, and an ISO timestamp.  No machine name, hostname,
or developer identity appears in any frame or state file.

FR-010–FR-017.

Per-project consent (#3030 T027, FR-002/NFR-001)
------------------------------------------------
``changed_files`` are repo-relative paths under ``kitty-specs/``, i.e. **mission
slugs**; for the 2026-07-27 incident's population those slugs are client engagement
names. This module therefore has the same egress duty as the drain, and until T027
had no consent check at all. Two gates now stand on the path, and both resolve the
answer through ``sync/consent.py`` — the *one* resolver (C-003):

* :func:`emit_local_commit` refuses to stage or send a frame for a project that has
  not consented, so nothing reaches ``sync-state.json`` for the flush to replay.
* :func:`flush_pending_local_commits` re-resolves consent **per frame** before each
  send, which is what covers residual frames staged before this gate existed and
  projects whose consent was revoked after staging.

The flush's gate reads identity from the **frame**, never from the working
directory. That is not a stylistic preference: the flush is called with
``WebSocketClient._repo_root``, which defaults to ``Path.cwd()`` because
``sync/runtime.py`` constructs the client without it. A cwd-derived check would
answer the question for whichever project the operator happens to be standing in
and authorize another project's egress on its grant — the defect T025 names for
body uploads and M1 names for capture. ``build_id`` cannot substitute: it is a
one-way uuid5 of ``(project_uuid, node_id)`` and degrades to a random uuid4 when
identity is incomplete, and ``mission_id`` is a repo-local slug. So the frame
carries ``project_uuid`` explicitly.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
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
# Per-project consent gate (#3030 T027)
# ---------------------------------------------------------------------------


def _frame_project_uuid(frame: Mapping[str, Any]) -> str | None:
    """The project uuid the frame carries about **itself**.

    Blank normalizes to ``None``: NFR-001 is a subset invariant whose second half is
    ``None ∉ delivered``, and a blank key would otherwise become a groupable,
    consentable value that pools unrelated projects.
    """
    raw = frame.get("project_uuid")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _checkout_project_uuid(repo_root: Path) -> str | None:
    """Read the emitting checkout's own declared project uuid. Never raises."""
    try:
        from specify_cli.identity.project import load_identity  # noqa: PLC0415

        identity = load_identity(Path(repo_root) / ".kittify" / "config.yaml")
    except Exception:  # noqa: BLE001 - an unreadable identity is absence, and absence denies
        logger.debug("Could not read project identity at %s", repo_root, exc_info=True)
        return None
    return str(identity.project_uuid) if identity.project_uuid else None


def _frame_project_consents(frame: Mapping[str, Any], *, offered_roots: list[Path]) -> bool:
    """Does the project *this frame belongs to* consent to hosted sync?

    Delegates to ``consent.consented_project_uuids`` — the advertised seam over the
    one precedence chain — rather than re-deriving it here. A frame whose
    ``project_uuid`` is missing or blank is dropped by that helper, so an
    unidentifiable frame is permanently unsendable rather than unsent-for-now.

    ``offered_roots`` are checkouts the caller can offer for the project-local level.
    Offering the flush's cwd is safe by construction: ``_project_local_votes``
    ignores a root that declares a different uuid, so an extra root can never widen
    the answer — only supply the authoritative file when cwd *is* the frame's
    project.

    The resolver returns the consenting **subset** of its candidates, so the answer
    is checked for *this* uuid's membership rather than for the subset being
    non-empty. Emptiness is equivalent only while exactly one candidate is passed;
    the day anyone batches frames through here, one consenting project would
    authorize every other project in the batch — the "returned set not checked for
    the right element" shape T025 names for body uploads. Membership costs nothing
    and does not depend on a future editor reading this paragraph.

    Fails **closed** on any error. Everything else in this module swallows
    exceptions so a git hook is never interrupted; here that same instinct would
    turn an unanswerable consent question into egress, and inability to determine
    consent is not consent (FR-003's rule). This branch is pinned by a test rather
    than trusted: an ``except`` that quietly starts returning ``True`` is how a
    guard reports "clean" forever.
    """
    uuid = _frame_project_uuid(frame)
    try:
        from specify_cli.sync.consent import consented_project_uuids  # noqa: PLC0415

        granted = uuid in consented_project_uuids([uuid], checkout_roots=offered_roots)
    except Exception:  # noqa: BLE001 - unanswerable is not granted
        logger.warning(
            "Could not resolve hosted-sync consent for a LocalCommit frame; refusing to send it",
            exc_info=True,
        )
        return False
    if not granted:
        logger.debug(
            "LocalCommit frame withheld: project %s has not consented to hosted sync",
            uuid or "<unidentified>",
        )
    return granted


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
    """Build and dispatch a ``LocalCommit`` frame, if *repo_root*'s project consents.

    Storage is **not** unconditional. A project with no consent record gets no frame
    at all: staging it and relying on the flush to withhold it would leave the
    mission slug on disk and make the whole guarantee rest on one gate. Refusal is
    silent apart from a debug line — a local command must still succeed (FR-010).

    When consent is granted the frame is stored in ``sync-state.json`` as a pending
    entry, and also sent immediately if a WebSocket client is currently connected.
    The pending entry is only removed once ``record_local_commit_ack`` receives the
    corresponding acknowledgement — this prevents frame loss when a send succeeds
    but the ack is never delivered.

    If an existing pending entry carries the same ``build_id`` (i.e. the commit
    was amended), it is replaced by the new frame so the list never contains two
    entries for the same build.

    The stored frame carries ``project_uuid`` so the on-connect flush can re-resolve
    consent from the frame's own identity instead of from its working directory.
    """
    frame: dict[str, Any] = {
        "type": "LocalCommit",
        "git_hash": git_hash,
        "mission_id": mission_id,
        "build_id": build_id,
        "project_uuid": _checkout_project_uuid(repo_root),
        "changed_files": changed_files,
        "committed_at": committed_at,
    }

    if not _frame_project_consents(frame, offered_roots=[Path(repo_root)]):
        return

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
    """Send every consenting unacknowledged pending ``LocalCommit`` frame to *client*.

    Frames are sent in ascending ``committed_at`` (chronological) order.
    Entries whose ``git_hash`` matches ``last_saas_confirmed_hash`` are
    considered already acknowledged and skipped.

    This function is intended to be called once the WebSocket connection is
    established (on-connect replay), and in production *repo_root* is
    ``WebSocketClient._repo_root`` — which defaults to ``Path.cwd()``. It is
    therefore treated strictly as "where the queue file lives" and as one *offered*
    checkout for the project-local consent level. It is never the identity the
    decision is made from: each frame is judged on its own ``project_uuid``, so
    standing in a consenting project cannot authorize another project's frames
    (FR-002/NFR-001).

    Withheld frames are **retained**, not dropped. A frame from a project that later
    consents becomes sendable; one that carries no resolvable identity never does,
    and staying on disk keeps it available as evidence of what a pre-gate build
    queued. WP08 owns the operator's purge path.
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

    offered_roots = [Path(repo_root)]
    sent = 0
    withheld = 0
    for frame in unacked:
        if not _frame_project_consents(frame, offered_roots=offered_roots):
            withheld += 1
            continue
        try:
            _send_event(client, frame)
            sent += 1
        except Exception:  # noqa: BLE001
            logger.debug("LocalCommit flush send failed for %s", frame.get("git_hash"), exc_info=True)

    logger.debug(
        "Flushed %d pending LocalCommit frame(s); withheld %d for lack of project consent",
        sent,
        withheld,
    )


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

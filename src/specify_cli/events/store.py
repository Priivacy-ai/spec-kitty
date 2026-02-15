"""Event storage interface with queue backend and online/offline handling."""

from pathlib import Path
import json
import fcntl  # Unix file locking
import os
import httpx
from datetime import datetime

from specify_cli.events import EventAdapter
from specify_cli.events.models import EventQueueEntry
from spec_kitty_events.models import Event


class EventStore:
    """
    Event storage interface with durable queue and replay support.

    This class manages local event storage and handles online/offline transitions.
    For now, it validates that the spec-kitty-events library is available.
    Full implementation includes queue storage, replay transport, and connectivity detection.
    """

    def __init__(self, repo_root: Path) -> None:
        """
        Initialize EventStore.

        Args:
            repo_root: Root directory of the repository

        Raises:
            RuntimeError: If spec-kitty-events library is not installed
        """
        if not EventAdapter.check_library_available():
            raise RuntimeError(EventAdapter.get_missing_library_error())

        self.repo_root = repo_root


def get_queue_path(mission_id: str) -> Path:
    """Get path to local queue database."""
    return Path.home() / ".spec-kitty" / "queue.db"


def append_event(mission_id: str, event: Event, replay_status: str = "pending") -> None:
    """
    Append event to local queue store (atomic write with file locking).

    Args:
        mission_id: Mission identifier
        event: Canonical event from spec-kitty-events
        replay_status: "pending", "delivered", or "failed"

    Raises:
        IOError: If file write fails
    """
    queue_path = get_queue_path(mission_id)
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    # Create EventQueueEntry with replay metadata
    entry = EventQueueEntry(
        event=event,
        replay_status=replay_status,  # type: ignore
        retry_count=0,
        last_retry_at=None,
    )

    # Serialize to queue record
    line = json.dumps(entry.to_record(), separators=(',', ':')) + "\n"

    # Atomic write with file locking
    with open(queue_path, "a") as f:
        # Acquire exclusive lock (blocks until available)
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Set file permissions to 0600 (owner read/write only)
    queue_path.chmod(0o600)


def read_pending_events(mission_id: str) -> list[EventQueueEntry]:
    """
    Read all pending events from queue (replay_status="pending").

    Args:
        mission_id: Mission identifier

    Returns:
        List of EventQueueEntry with replay_status="pending"
    """
    queue_path = get_queue_path(mission_id)

    if not queue_path.exists():
        return []

    pending_events = []

    with open(queue_path, "r") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = EventQueueEntry.from_record(json.loads(line))
                if entry.replay_status == "pending":
                    pending_events.append(entry)
            except (json.JSONDecodeError, ValueError) as e:
                # Corrupted line: Log warning, skip line
                print(f"⚠️  Skipping corrupted line {line_num} in {queue_path}: {e}")

    return pending_events


def read_all_events(mission_id: str) -> list[EventQueueEntry]:
    """
    Read all events from queue (regardless of replay_status).

    Used by materialized view to rebuild roster state.

    Args:
        mission_id: Mission identifier

    Returns:
        List of all EventQueueEntry
    """
    queue_path = get_queue_path(mission_id)

    if not queue_path.exists():
        return []

    all_events = []

    with open(queue_path, "r") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = EventQueueEntry.from_record(json.loads(line))
                all_events.append(entry)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️  Skipping corrupted line {line_num} in {queue_path}: {e}")

    return all_events


def is_online(saas_api_url: str, timeout: float = 2.0) -> bool:
    """
    Quick connectivity check to SaaS.

    Args:
        saas_api_url: SaaS API base URL
        timeout: Request timeout in seconds (default 2s)

    Returns:
        True if SaaS reachable, False otherwise
    """
    try:
        response = httpx.get(f"{saas_api_url}/health", timeout=timeout)
        return response.status_code == 200
    except (httpx.HTTPError, httpx.TimeoutException):
        return False


def emit_event(
    mission_id: str,
    event: Event,
    saas_api_url: str,
    session_token: str,
) -> None:
    """
    Emit event to local queue and attempt immediate SaaS delivery.

    If SaaS unreachable, event queued with replay_status="pending" for later replay.

    Args:
        mission_id: Mission identifier
        event: Canonical event
        saas_api_url: SaaS API base URL
        session_token: Session token for authentication
    """
    from specify_cli.events.replay import _send_batch, _update_queue_status

    # Always append to local queue first (authoritative)
    append_event(mission_id, event, replay_status="pending")

    # Attempt immediate delivery if online
    if is_online(saas_api_url):
        result = _send_batch(
            [EventQueueEntry(event, "pending", 0, None)],  # type: ignore
            saas_api_url,
            session_token,
            max_retries=1
        )

        if result["accepted"]:
            # Mark as delivered in queue
            _update_queue_status(mission_id, result["accepted"], [])
    else:
        # Offline: Log warning, event remains pending
        print(f"⚠️  Offline: Event queued for replay (ID: {event.event_id})")

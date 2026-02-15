"""Event storage interface with queue backend and online/offline handling."""

from pathlib import Path
import json
import os
import sys
import httpx
from datetime import datetime

# Cross-platform file locking
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

from specify_cli.events import EventAdapter
from specify_cli.events.models import EventQueueEntry
from specify_cli.spec_kitty_events.models import Event


def _lock_file(file_handle) -> None:
    """Acquire exclusive lock on file (cross-platform)."""
    if sys.platform == "win32":
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(file_handle) -> None:
    """Release lock on file (cross-platform)."""
    if sys.platform == "win32":
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)


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
    """Get path to mission-specific queue file."""
    queue_dir = Path.home() / ".spec-kitty" / "queues"
    queue_dir.mkdir(parents=True, exist_ok=True)
    return queue_dir / f"{mission_id}.jsonl"


def append_event(mission_id: str, event: Event, replay_status: str = "pending") -> None:
    """
    Append event to local queue store (atomic write with file locking).

    Args:
        mission_id: Mission identifier
        event: Canonical event from spec-kitty-events
        replay_status: "pending", "delivered", or "failed"

    Raises:
        IOError: If file write fails after retries
        PermissionError: If insufficient permissions to write queue file
    """
    queue_path = get_queue_path(mission_id)

    # Check parent directory permissions early
    try:
        queue_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        raise PermissionError(
            f"Cannot create queue directory {queue_path.parent}. "
            f"Check permissions on ~/.spec-kitty directory. Error: {e}"
        ) from e

    # Create EventQueueEntry with replay metadata
    entry = EventQueueEntry(
        event=event,
        replay_status=replay_status,  # type: ignore
        retry_count=0,
        last_retry_at=None,
    )

    # Serialize to queue record
    line = json.dumps(entry.to_record(), separators=(',', ':')) + "\n"

    # Retry write on transient I/O failures
    max_retries = 2
    last_error = None

    for attempt in range(max_retries):
        try:
            # Atomic write with file locking
            with open(queue_path, "a") as f:
                # Acquire exclusive lock (blocks until available)
                _lock_file(f)
                try:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                finally:
                    _unlock_file(f)

            # Set file permissions to 0600 (owner read/write only)
            try:
                queue_path.chmod(0o600)
            except PermissionError:
                # Non-fatal: Log warning but don't fail
                print(f"⚠️  Could not set permissions on {queue_path} (continuing)")

            # Success - return
            return

        except PermissionError as e:
            # Permission errors are not transient - fail immediately
            raise PermissionError(
                f"Cannot write to queue file {queue_path}. "
                f"Check file permissions and ownership. Error: {e}"
            ) from e

        except (OSError, IOError) as e:
            last_error = e
            if attempt < max_retries - 1:
                # Transient I/O error - retry once
                import time
                time.sleep(0.1)  # Brief delay before retry
            else:
                # Final retry failed
                raise IOError(
                    f"Failed to write event to queue after {max_retries} attempts. "
                    f"Event ID: {event.event_id}. Last error: {e}"
                ) from e


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
                # Filter by mission to prevent cross-mission contamination
                if entry.event.aggregate_id != f"mission/{mission_id}":
                    continue
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
                # Filter by mission to prevent cross-mission contamination
                if entry.event.aggregate_id != f"mission/{mission_id}":
                    continue
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

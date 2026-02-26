import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

import toml


class _BatchEventResultLike(Protocol):
    """Minimal protocol for batch result records consumed by queue processing."""

    status: str
    event_id: str


@dataclass
class QueueStats:
    """Aggregate statistics about the offline event queue.

    Used by ``sync status`` to display queue health information
    including depth, age, retry distribution, and top event types.
    """

    total_queued: int = 0
    total_retried: int = 0
    oldest_event_age: Optional[timedelta] = None
    retry_distribution: dict[str, int] = field(default_factory=dict)
    top_event_types: list[tuple[str, int]] = field(default_factory=list)


def _spec_kitty_dir() -> Path:
    """Return ~/.spec-kitty for the current HOME."""
    return Path.home() / ".spec-kitty"


def _credentials_path() -> Path:
    return _spec_kitty_dir() / "credentials"


def _legacy_queue_db_path() -> Path:
    return _spec_kitty_dir() / "queue.db"


def _scoped_queue_dir() -> Path:
    return _spec_kitty_dir() / "queues"


def _active_scope_path() -> Path:
    return _spec_kitty_dir() / "active_queue_scope"


def _normalise_scope_part(value: str) -> str:
    return value.strip().lower()


def build_queue_scope(server_url: str, username: str, team_slug: str) -> str:
    """Build canonical queue scope identity for a login session."""
    server = _normalise_scope_part(server_url).rstrip("/")
    user = _normalise_scope_part(username)
    team = _normalise_scope_part(team_slug)
    return f"{server}|{user}|{team}"


def read_queue_scope_from_credentials(credentials_path: Optional[Path] = None) -> Optional[str]:
    """Read queue scope from credentials file.

    Returns None when credentials are missing, invalid, or incomplete.
    """
    path = credentials_path or _credentials_path()
    if not path.exists():
        return None

    try:
        data = toml.load(path)
    except (toml.TomlDecodeError, OSError):
        return None

    user_data = data.get("user") if isinstance(data, dict) else None
    server_data = data.get("server") if isinstance(data, dict) else None
    if not isinstance(user_data, dict) or not isinstance(server_data, dict):
        return None

    username = user_data.get("username")
    server_url = server_data.get("url")
    team_slug = user_data.get("team_slug") or "no-team"

    if not username or not server_url:
        return None
    return build_queue_scope(str(server_url), str(username), str(team_slug))


def scope_db_path(scope: str) -> Path:
    """Resolve a deterministic queue DB path for a given scope."""
    digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()[:16]
    return _scoped_queue_dir() / f"queue-{digest}.db"


def default_queue_db_path(credentials_path: Optional[Path] = None) -> Path:
    """Resolve default queue DB path.

    Unauthenticated sessions use legacy ~/.spec-kitty/queue.db.
    Authenticated sessions use scoped queues under ~/.spec-kitty/queues/.
    """
    scope = read_queue_scope_from_credentials(credentials_path=credentials_path)
    if scope:
        return scope_db_path(scope)
    return _legacy_queue_db_path()


def read_active_scope(path: Optional[Path] = None) -> Optional[str]:
    """Read previously active queue scope marker."""
    marker = path or _active_scope_path()
    if not marker.exists():
        return None
    try:
        value = marker.read_text().strip()
    except OSError:
        return None
    return value or None


def write_active_scope(scope: str, path: Optional[Path] = None) -> None:
    """Persist active queue scope marker."""
    marker = path or _active_scope_path()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(scope)


def pending_events_for_scope(scope: str) -> int:
    """Return pending event count for a scoped queue without mutating queue data."""
    db_path = scope_db_path(scope)
    if not db_path.exists():
        return 0
    queue = OfflineQueue(db_path=db_path)
    return queue.size()


class OfflineQueue:
    """
    SQLite-based offline event queue.

    Stores events locally when the CLI cannot connect to the sync server,
    allowing them to be drained and synced when connectivity is restored.

    Features:
    - Persistent storage across CLI restarts
    - FIFO ordering by timestamp
    - 10,000 event capacity limit with user warning
    - Indexes for efficient retrieval
    """

    MAX_QUEUE_SIZE = 10000

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialize offline queue.

        Args:
            db_path: Path to SQLite database. Defaults to a scope-aware path:
                - unauthenticated: ~/.spec-kitty/queue.db
                - authenticated: ~/.spec-kitty/queues/queue-<scope-hash>.db
        """
        if db_path is None:
            db_path = default_queue_db_path()

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema with indexes"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    retry_count INTEGER DEFAULT 0
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON queue(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_retry ON queue(retry_count)')
            conn.commit()
        finally:
            conn.close()

    def queue_event(self, event: dict[str, Any]) -> bool:
        """
        Add event to offline queue.

        Args:
            event: Event dict with event_id, event_type, and payload

        Returns:
            True if queued successfully, False if queue is full
        """
        if self.size() >= self.MAX_QUEUE_SIZE:
            print(f"⚠️  Offline queue full ({self.MAX_QUEUE_SIZE:,} events). Cannot sync until reconnected.")
            return False

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                'INSERT OR REPLACE INTO queue (event_id, event_type, data, timestamp) VALUES (?, ?, ?, ?)',
                (
                    str(event["event_id"]),
                    str(event["event_type"]),
                    json.dumps(event),
                    int(datetime.now().timestamp()),
                )
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Failed to queue event: {e}")
            return False
        finally:
            conn.close()

    def drain_queue(self, limit: int = 1000) -> list[dict[str, Any]]:
        """
        Retrieve events from queue (oldest first).

        Does not remove events - use mark_synced() after successful sync.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dicts ordered by timestamp, then id (FIFO)
        """
        conn = sqlite3.connect(self.db_path)
        try:
            # Order by timestamp first, then by id for deterministic FIFO ordering
            # when multiple events are queued within the same second
            cursor = conn.execute(
                'SELECT event_id, data FROM queue ORDER BY timestamp ASC, id ASC LIMIT ?',
                (limit,)
            )
            events: list[dict[str, Any]] = []
            for row in cursor:
                _, data = row
                events.append(json.loads(data))
            return events
        finally:
            conn.close()

    def mark_synced(self, event_ids: list[str]) -> None:
        """
        Remove successfully synced events from queue.

        Args:
            event_ids: List of event IDs to remove
        """
        if not event_ids:
            return

        conn = sqlite3.connect(self.db_path)
        try:
            placeholders = ','.join('?' * len(event_ids))
            conn.execute(f'DELETE FROM queue WHERE event_id IN ({placeholders})', event_ids)
            conn.commit()
        finally:
            conn.close()

    def increment_retry(self, event_ids: list[str]) -> None:
        """
        Increment retry count for events that failed to sync.

        Args:
            event_ids: List of event IDs to increment
        """
        if not event_ids:
            return

        conn = sqlite3.connect(self.db_path)
        try:
            placeholders = ','.join('?' * len(event_ids))
            conn.execute(
                f'UPDATE queue SET retry_count = retry_count + 1 WHERE event_id IN ({placeholders})',
                event_ids
            )
            conn.commit()
        finally:
            conn.close()

    def size(self) -> int:
        """
        Get current queue size.

        Returns:
            Number of events in queue
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM queue")
            row = cursor.fetchone()
            if row is None:
                return 0
            return int(row[0])
        finally:
            conn.close()

    def clear(self) -> None:
        """Remove all events from queue"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('DELETE FROM queue')
            conn.commit()
        finally:
            conn.close()

    def process_batch_results(self, results: list[_BatchEventResultLike]) -> None:
        """Process batch sync results: remove synced/duplicate, bump retry for failures.

        Wraps all queue mutations in a single SQLite transaction for
        atomicity: either all changes apply or none do.

        Args:
            results: List of ``BatchEventResult`` (or any object with
                ``.status`` and ``.event_id`` attributes).
        """
        synced_or_duplicate: list[str] = []
        rejected: list[str] = []
        for r in results:
            if r.status in ("success", "duplicate"):
                synced_or_duplicate.append(r.event_id)
            elif r.status == "rejected":
                rejected.append(r.event_id)

        conn = sqlite3.connect(self.db_path)
        try:
            # Wrap both operations in a single transaction
            if synced_or_duplicate:
                placeholders = ",".join("?" * len(synced_or_duplicate))
                conn.execute(
                    f"DELETE FROM queue WHERE event_id IN ({placeholders})",
                    synced_or_duplicate,
                )
            if rejected:
                placeholders = ",".join("?" * len(rejected))
                conn.execute(
                    f"UPDATE queue SET retry_count = retry_count + 1 WHERE event_id IN ({placeholders})",
                    rejected,
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_events_by_retry_count(self, max_retries: int = 5) -> list[dict[str, Any]]:
        """
        Get events that haven't exceeded retry limit.

        Args:
            max_retries: Maximum retry count threshold

        Returns:
            List of events with retry_count < max_retries
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                'SELECT event_id, data FROM queue WHERE retry_count < ? ORDER BY timestamp ASC, id ASC',
                (max_retries,)
            )
            events: list[dict[str, Any]] = []
            for row in cursor:
                _, data = row
                events.append(json.loads(data))
            return events
        finally:
            conn.close()

    def get_queue_stats(self) -> QueueStats:
        """
        Compute aggregate statistics about the queue.

        Returns a QueueStats with:
        - total_queued: number of events in queue
        - total_retried: number of events with retry_count > 0
        - oldest_event_age: timedelta from oldest event timestamp to now (None if empty)
        - retry_distribution: counts bucketed as '0 retries', '1-3 retries', '4+ retries'
        - top_event_types: top 5 event types by count, descending
        """
        conn = sqlite3.connect(self.db_path)
        try:
            # Total queued
            total_queued_row = conn.execute("SELECT COUNT(*) FROM queue").fetchone()
            total_queued = int(total_queued_row[0]) if total_queued_row is not None else 0

            if total_queued == 0:
                return QueueStats()

            # Total retried (retry_count > 0)
            total_retried_row = conn.execute(
                "SELECT COUNT(*) FROM queue WHERE retry_count > 0"
            ).fetchone()
            total_retried = int(total_retried_row[0]) if total_retried_row is not None else 0

            # Oldest event age
            oldest_ts_row = conn.execute("SELECT MIN(timestamp) FROM queue").fetchone()
            oldest_ts = oldest_ts_row[0] if oldest_ts_row is not None else None
            oldest_event_age: Optional[timedelta] = None
            if oldest_ts is not None:
                oldest_dt = datetime.fromtimestamp(int(oldest_ts), tz=timezone.utc)
                now_dt = datetime.now(tz=timezone.utc)
                oldest_event_age = now_dt - oldest_dt

            # Retry distribution buckets
            cursor = conn.execute('''
                SELECT
                    CASE
                        WHEN retry_count = 0 THEN '0 retries'
                        WHEN retry_count BETWEEN 1 AND 3 THEN '1-3 retries'
                        ELSE '4+ retries'
                    END as bucket,
                    COUNT(*) as count
                FROM queue
                GROUP BY bucket
            ''')
            retry_distribution: dict[str, int] = {}
            for bucket, count in cursor:
                retry_distribution[str(bucket)] = int(count)

            # Top 5 event types by count
            cursor = conn.execute('''
                SELECT event_type, COUNT(*) as count
                FROM queue
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 5
            ''')
            top_event_types: list[tuple[str, int]] = []
            for event_type, count in cursor:
                top_event_types.append((str(event_type), int(count)))

            return QueueStats(
                total_queued=total_queued,
                total_retried=total_retried,
                oldest_event_age=oldest_event_age,
                retry_distribution=retry_distribution,
                top_event_types=top_event_types,
            )
        finally:
            conn.close()

import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

import toml


class _BatchEventResultLike(Protocol):
    """Minimal protocol for batch result records consumed by queue processing."""

    status: str
    event_id: str


DEFAULT_MAX_QUEUE_SIZE = 100_000

# Event types eligible for coalescing: when a new event of one of these types
# arrives and an equivalent event (same type + coalesce key) already exists in
# the queue, the existing row is updated in-place rather than inserting a new
# row.  This prevents high-volume instrumentation from flooding the queue.
COALESCEABLE_EVENT_TYPES: dict[str, list[str]] = {
    # project_uuid scopes the key so events from different repos/branches
    # sharing the same mission_slug+artifact_key never collide.
    "MissionDossierArtifactIndexed": ["project_uuid", "mission_slug", "artifact_key"],
    # Snapshot IDs are regenerated on each scan, so coalesce by project+feature
    # to keep only the latest snapshot queued for a given dossier.
    "MissionDossierSnapshotComputed": ["project_uuid", "mission_slug"],
}


def _coalesce_key(event: dict[str, Any]) -> Optional[str]:
    """Return a deterministic coalesce key for an event, or None if not coalesceable.

    The key is built from the event_type and the fields listed in
    COALESCEABLE_EVENT_TYPES. Fields may live either on the top-level event
    envelope (for example ``project_uuid``) or inside ``payload``.
    """
    event_type = str(event.get("event_type", ""))
    key_fields = COALESCEABLE_EVENT_TYPES.get(event_type)
    if key_fields is None:
        return None
    payload = event.get("payload") or {}
    parts = [event_type]
    for field_name in key_fields:
        value = event.get(field_name)
        if value is None:
            value = payload.get(field_name, "")
        parts.append(str(value))
    return "|".join(parts)


def get_max_queue_size() -> int:
    """Read max_queue_size from ~/.spec-kitty/config.toml, falling back to DEFAULT_MAX_QUEUE_SIZE.

    Config key: [sync] max_queue_size = <int>
    """
    config_file = _spec_kitty_dir() / "config.toml"
    if not config_file.exists():
        return DEFAULT_MAX_QUEUE_SIZE
    try:
        data = toml.load(config_file)
        value = data.get("sync", {}).get("max_queue_size")
        if value is not None:
            return int(value)
    except (toml.TomlDecodeError, OSError, TypeError, ValueError):
        pass
    return DEFAULT_MAX_QUEUE_SIZE


@dataclass
class QueueStats:
    """Aggregate statistics about the offline event queue.

    Used by ``sync status`` to display queue health information
    including depth, age, retry distribution, and top event types.
    """

    total_queued: int = 0
    max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE
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


_BODY_QUEUE_SCHEMA = """
CREATE TABLE IF NOT EXISTS body_upload_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid TEXT NOT NULL,
    mission_slug TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    mission_type TEXT NOT NULL,
    manifest_version TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
    content_body TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    last_error TEXT,
    UNIQUE(project_uuid, mission_slug, target_branch, mission_type, manifest_version, artifact_path, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_body_queue_next_attempt ON body_upload_queue(next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_body_queue_namespace ON body_upload_queue(project_uuid, mission_slug, target_branch);
"""


def _migrate_body_queue_column_rename(conn: sqlite3.Connection) -> None:
    """Rename legacy columns mission_slug -> mission_slug, mission_type -> mission_type.

    Idempotent: skips if columns are already renamed or if the table does not exist.
    SQLite ALTER TABLE RENAME COLUMN requires SQLite 3.25.0+ (Python 3.11+ bundles 3.39+).
    """
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='body_upload_queue'"
    )
    if cursor.fetchone() is None:
        return  # Table doesn't exist yet; fresh install will create with new names

    col_cursor = conn.execute("PRAGMA table_info(body_upload_queue)")
    columns = {row[1] for row in col_cursor}

    if "mission_slug" not in columns and "mission_type" not in columns:
        return  # Already migrated

    if "mission_slug" in columns:
        conn.execute(
            "ALTER TABLE body_upload_queue RENAME COLUMN mission_slug TO mission_slug"
        )
    if "mission_type" in columns:
        conn.execute(
            "ALTER TABLE body_upload_queue RENAME COLUMN mission_type TO mission_type"
        )
    conn.commit()


def ensure_body_queue_schema(conn: sqlite3.Connection) -> None:
    """Create body_upload_queue table and indexes if they don't exist.

    Also runs the column rename migration for existing databases.
    """
    _migrate_body_queue_column_rename(conn)
    conn.executescript(_BODY_QUEUE_SCHEMA)


class OfflineQueue:
    """
    SQLite-based offline event queue.

    Stores events locally when the CLI cannot connect to the sync server,
    allowing them to be drained and synced when connectivity is restored.

    Features:
    - Persistent storage across CLI restarts
    - FIFO ordering by timestamp
    - Configurable capacity limit (default 100,000) with FIFO eviction
    - Event coalescing for high-volume event types
    - Indexes for efficient retrieval
    """

    MAX_QUEUE_SIZE = DEFAULT_MAX_QUEUE_SIZE  # kept as class attr for back-compat

    def __init__(self, db_path: Optional[Path] = None, max_queue_size: Optional[int] = None) -> None:
        """
        Initialize offline queue.

        Args:
            db_path: Path to SQLite database. Defaults to a scope-aware path:
                - unauthenticated: ~/.spec-kitty/queue.db
                - authenticated: ~/.spec-kitty/queues/queue-<scope-hash>.db
            max_queue_size: Override maximum queue capacity.  When None the
                value is read from ``~/.spec-kitty/config.toml`` (key
                ``[sync] max_queue_size``) or falls back to 100,000.
        """
        if db_path is None:
            db_path = default_queue_db_path()

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if max_queue_size is not None:
            self._max_queue_size = int(max_queue_size)
        else:
            self._max_queue_size = get_max_queue_size()

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema with indexes."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    coalesce_key TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON queue(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_retry ON queue(retry_count)")
            conn.commit()

            # Migrate: add coalesce_key column to legacy databases that lack it.
            # Must run BEFORE the coalesce_key index creation.
            self._migrate_add_coalesce_key(conn)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_coalesce_key ON queue(coalesce_key)")
            conn.commit()
            ensure_body_queue_schema(conn)
        finally:
            conn.close()

    @staticmethod
    def _migrate_add_coalesce_key(conn: sqlite3.Connection) -> None:
        """Add coalesce_key column to existing databases that lack it."""
        cursor = conn.execute("PRAGMA table_info(queue)")
        columns = {row[1] for row in cursor}
        if "coalesce_key" not in columns:
            conn.execute("ALTER TABLE queue ADD COLUMN coalesce_key TEXT")
            conn.commit()

    def queue_event(self, event: dict[str, Any]) -> bool:
        """
        Add event to offline queue.

        High-volume event types listed in ``COALESCEABLE_EVENT_TYPES`` are
        coalesced: if an existing row with the same coalesce key is already
        queued, the row is updated in-place (new event_id, data, timestamp)
        instead of inserting a new row.  This prevents dossier scans from
        flooding the queue.

        Args:
            event: Event dict with event_id, event_type, and payload

        Returns:
            True if queued successfully, False on database error
        """
        c_key = _coalesce_key(event)

        # Attempt coalescing before checking the size cap.
        # If an existing row can be updated, no new row is added.
        if c_key is not None:
            coalesced = self._try_coalesce(event, c_key)
            if coalesced:
                return True

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM queue")
            count_row = cursor.fetchone()
            current_size = int(count_row[0]) if count_row else 0
            if current_size >= self._max_queue_size:
                # FIFO eviction: delete the oldest events to make room
                overflow = current_size - self._max_queue_size + 1
                conn.execute(
                    "DELETE FROM queue WHERE id IN ("
                    "  SELECT id FROM queue ORDER BY timestamp ASC, id ASC LIMIT ?"
                    ")",
                    (overflow,),
                )
                print(
                    f"Offline queue at capacity ({self._max_queue_size:,} events). "
                    f"Evicted {overflow:,} oldest event(s) to make room.\n"
                    f"  Check auth and connectivity: spec-kitty sync status --check\n"
                    f"  Drain the queue manually:    spec-kitty sync now",
                    file=sys.stderr,
                )

            conn.execute(
                "INSERT OR REPLACE INTO queue (event_id, event_type, data, timestamp, coalesce_key) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    str(event["event_id"]),
                    str(event["event_type"]),
                    json.dumps(event),
                    int(datetime.now().timestamp()),
                    c_key,
                ),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Failed to queue event: {e}")
            return False
        finally:
            conn.close()

    def _try_coalesce(self, event: dict[str, Any], c_key: str) -> bool:
        """Update an existing row with the same coalesce key, if one exists.

        Returns True if a row was updated (coalesced), False otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id FROM queue WHERE coalesce_key = ? LIMIT 1",
                (c_key,),
            )
            row = cursor.fetchone()
            if row is None:
                return False
            existing_id = row[0]
            conn.execute(
                "UPDATE queue SET event_id = ?, data = ?, timestamp = ? WHERE id = ?",
                (
                    str(event["event_id"]),
                    json.dumps(event),
                    int(datetime.now().timestamp()),
                    existing_id,
                ),
            )
            conn.commit()
            return True
        except Exception:
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
            cursor = conn.execute("SELECT event_id, data FROM queue ORDER BY timestamp ASC, id ASC LIMIT ?", (limit,))
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
            placeholders = ",".join("?" * len(event_ids))
            conn.execute(f"DELETE FROM queue WHERE event_id IN ({placeholders})", event_ids)
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
            placeholders = ",".join("?" * len(event_ids))
            conn.execute(
                f"UPDATE queue SET retry_count = retry_count + 1 WHERE event_id IN ({placeholders})", event_ids
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
            conn.execute("DELETE FROM queue")
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
                "SELECT event_id, data FROM queue WHERE retry_count < ? ORDER BY timestamp ASC, id ASC", (max_retries,)
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
                return QueueStats(max_queue_size=self._max_queue_size)

            # Total retried (retry_count > 0)
            total_retried_row = conn.execute("SELECT COUNT(*) FROM queue WHERE retry_count > 0").fetchone()
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
            cursor = conn.execute("""
                SELECT
                    CASE
                        WHEN retry_count = 0 THEN '0 retries'
                        WHEN retry_count BETWEEN 1 AND 3 THEN '1-3 retries'
                        ELSE '4+ retries'
                    END as bucket,
                    COUNT(*) as count
                FROM queue
                GROUP BY bucket
            """)
            retry_distribution: dict[str, int] = {}
            for bucket, count in cursor:
                retry_distribution[str(bucket)] = int(count)

            # Top 5 event types by count
            cursor = conn.execute("""
                SELECT event_type, COUNT(*) as count
                FROM queue
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 5
            """)
            top_event_types: list[tuple[str, int]] = []
            for event_type, count in cursor:
                top_event_types.append((str(event_type), int(count)))

            return QueueStats(
                total_queued=total_queued,
                max_queue_size=self._max_queue_size,
                total_retried=total_retried,
                oldest_event_age=oldest_event_age,
                retry_distribution=retry_distribution,
                top_event_types=top_event_types,
            )
        finally:
            conn.close()

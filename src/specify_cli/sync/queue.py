"""Offline event queue using SQLite for network outage resilience"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


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

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize offline queue.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.spec-kitty/queue.db
        """
        if db_path is None:
            db_path = Path.home() / '.spec-kitty' / 'queue.db'

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
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

    def queue_event(self, event: Dict) -> bool:
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
                    event['event_id'],
                    event['event_type'],
                    json.dumps(event),
                    int(datetime.now().timestamp())
                )
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Failed to queue event: {e}")
            return False
        finally:
            conn.close()

    def drain_queue(self, limit: int = 1000) -> List[Dict]:
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
            events = []
            for row in cursor:
                event_id, data = row
                events.append(json.loads(data))
            return events
        finally:
            conn.close()

    def mark_synced(self, event_ids: List[str]):
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

    def increment_retry(self, event_ids: List[str]):
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
            cursor = conn.execute('SELECT COUNT(*) FROM queue')
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def clear(self):
        """Remove all events from queue"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('DELETE FROM queue')
            conn.commit()
        finally:
            conn.close()

    def process_batch_results(self, results: list) -> None:
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

    def get_events_by_retry_count(self, max_retries: int = 5) -> List[Dict]:
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
            events = []
            for row in cursor:
                event_id, data = row
                events.append(json.loads(data))
            return events
        finally:
            conn.close()

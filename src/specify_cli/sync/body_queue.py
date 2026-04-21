"""Offline body upload queue with SQLite persistence.

Provides durable, idempotent queuing for artifact body uploads with
per-task exponential backoff. Lives alongside the event queue in the
same SQLite DB file.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from .queue import (
    DEFAULT_MAX_QUEUE_SIZE,
    default_queue_db_path,
    ensure_body_queue_schema,
    get_max_queue_size,
)

if TYPE_CHECKING:
    from .namespace import NamespaceRef

DEFAULT_BODY_QUEUE_SIZE = DEFAULT_MAX_QUEUE_SIZE
_BACKOFF_BASE = 1.0
_BACKOFF_CAP = 300.0


@dataclass
class BodyUploadTask:
    """A single queued body upload task."""

    row_id: int
    project_uuid: str
    mission_slug: str
    target_branch: str
    mission_type: str
    manifest_version: str
    artifact_path: str
    content_hash: str
    hash_algorithm: str
    content_body: str
    size_bytes: int
    retry_count: int
    next_attempt_at: float
    created_at: float
    last_error: str | None


@dataclass
class BodyQueueStats:
    """Diagnostic information about body queue state."""

    total_count: int
    ready_count: int
    backoff_count: int
    oldest_created_at: float | None
    newest_created_at: float | None
    max_retry_count: int
    retry_histogram: dict[int, int]


class BodyEnqueueResult(StrEnum):
    """Classification of a body queue enqueue attempt."""

    ENQUEUED = "enqueued"
    ALREADY_EXISTS = "already_exists"
    QUEUE_FULL = "queue_full"


class OfflineBodyUploadQueue:
    """SQLite-backed queue for artifact body uploads.

    Shares the same DB file as the event OfflineQueue. Provides
    idempotent enqueue, per-task backoff drain, and lifecycle methods.
    """

    def __init__(
        self,
        db_path: Path | None = None,
        max_queue_size: int | None = None,
    ) -> None:
        if db_path is None:
            db_path = default_queue_db_path()
        self.db_path = db_path
        self._max_queue_size = (
            int(max_queue_size)
            if max_queue_size is not None
            else get_max_queue_size()
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            ensure_body_queue_schema(conn)
        finally:
            conn.close()

    @property
    def max_queue_size(self) -> int:
        """Configured queue capacity for body uploads."""
        return self._max_queue_size

    def enqueue(
        self,
        namespace: NamespaceRef,
        artifact_path: str,
        content_hash: str,
        content_body: str,
        size_bytes: int,
        hash_algorithm: str = "sha256",
    ) -> BodyEnqueueResult:
        """Enqueue a body upload task."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM body_upload_queue").fetchone()
            count = int(row[0]) if row else 0
            if count >= self._max_queue_size:
                # Keep normal CLI output quiet in offline-first mode. Saturation can
                # still be inspected explicitly via queue diagnostics.
                return BodyEnqueueResult.QUEUE_FULL
            # Validate outbound payload before queue write
            from specify_cli.core.contract_gate import validate_outbound_payload
            namespace_dict = namespace.to_dict()
            validate_outbound_payload(namespace_dict, "body_sync")

            cursor = conn.execute(
                """INSERT OR IGNORE INTO body_upload_queue
                   (project_uuid, mission_slug, target_branch, mission_type,
                    manifest_version, artifact_path, content_hash, hash_algorithm,
                    content_body, size_bytes, retry_count, next_attempt_at, created_at, last_error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0.0, ?, NULL)""",
                (
                    namespace.project_uuid,
                    namespace.mission_slug,
                    namespace.target_branch,
                    namespace.mission_type,
                    namespace.manifest_version,
                    artifact_path,
                    content_hash,
                    hash_algorithm,
                    content_body,
                    size_bytes,
                    time.time(),
                ),
            )
            conn.commit()
            if cursor.rowcount > 0:
                return BodyEnqueueResult.ENQUEUED
            return BodyEnqueueResult.ALREADY_EXISTS
        finally:
            conn.close()

    def drain(self, limit: int = 100) -> list[BodyUploadTask]:
        """Retrieve tasks ready for delivery (next_attempt_at <= now)."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """SELECT id, project_uuid, mission_slug, target_branch, mission_type,
                          manifest_version, artifact_path, content_hash, hash_algorithm,
                          content_body, size_bytes, retry_count, next_attempt_at,
                          created_at, last_error
                   FROM body_upload_queue
                   WHERE next_attempt_at <= ?
                   ORDER BY created_at ASC, id ASC
                   LIMIT ?""",
                (time.time(), limit),
            )
            tasks: list[BodyUploadTask] = []
            for row in cursor:
                tasks.append(
                    BodyUploadTask(
                        row_id=row[0],
                        project_uuid=row[1],
                        mission_slug=row[2],
                        target_branch=row[3],
                        mission_type=row[4],
                        manifest_version=row[5],
                        artifact_path=row[6],
                        content_hash=row[7],
                        hash_algorithm=row[8],
                        content_body=row[9],
                        size_bytes=row[10],
                        retry_count=row[11],
                        next_attempt_at=row[12],
                        created_at=row[13],
                        last_error=row[14],
                    )
                )
            return tasks
        finally:
            conn.close()

    def mark_uploaded(self, row_id: int) -> None:
        """Remove a successfully uploaded task from the queue."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM body_upload_queue WHERE id = ?", (row_id,))
            conn.commit()
        finally:
            conn.close()

    def mark_already_exists(self, row_id: int) -> None:
        """Remove a task whose content already exists on the server."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM body_upload_queue WHERE id = ?", (row_id,))
            conn.commit()
        finally:
            conn.close()

    def mark_failed_retryable(self, row_id: int, error: str) -> None:
        """Update a failed task with exponential backoff."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT retry_count FROM body_upload_queue WHERE id = ?", (row_id,)
            ).fetchone()
            if row is None:
                return
            retry_count = int(row[0])
            backoff_seconds = min(_BACKOFF_BASE * (2 ** retry_count), _BACKOFF_CAP)
            next_attempt = time.time() + backoff_seconds
            conn.execute(
                """UPDATE body_upload_queue
                   SET retry_count = retry_count + 1,
                       next_attempt_at = ?,
                       last_error = ?
                   WHERE id = ?""",
                (next_attempt, error, row_id),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_failed_permanent(self, row_id: int, _error: str) -> None:
        """Remove a permanently failed task (non-retryable error)."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM body_upload_queue WHERE id = ?", (row_id,))
            conn.commit()
        finally:
            conn.close()

    def remove_stale(self, max_retry_count: int = 20) -> int:
        """Remove tasks that have exceeded max retries. Returns count removed."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM body_upload_queue WHERE retry_count > ?",
                (max_retry_count,),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def remove_project_tasks(self, project_uuid: str) -> int:
        """Remove queued body uploads for a specific project UUID."""
        if not project_uuid:
            return 0

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM body_upload_queue WHERE project_uuid = ?",
                (project_uuid,),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def size(self) -> int:
        """Get current body queue size."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM body_upload_queue").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def get_stats(self) -> BodyQueueStats:
        """Compute diagnostic statistics about the queue."""
        conn = sqlite3.connect(self.db_path)
        try:
            now = time.time()

            row = conn.execute("SELECT COUNT(*) FROM body_upload_queue").fetchone()
            total_count = int(row[0]) if row else 0

            if total_count == 0:
                return BodyQueueStats(
                    total_count=0,
                    ready_count=0,
                    backoff_count=0,
                    oldest_created_at=None,
                    newest_created_at=None,
                    max_retry_count=0,
                    retry_histogram={},
                )

            row = conn.execute(
                "SELECT COUNT(*) FROM body_upload_queue WHERE next_attempt_at <= ?",
                (now,),
            ).fetchone()
            ready_count = int(row[0]) if row else 0

            backoff_count = total_count - ready_count

            row = conn.execute(
                "SELECT MIN(created_at), MAX(created_at), MAX(retry_count) FROM body_upload_queue"
            ).fetchone()
            oldest_created_at = float(row[0]) if row and row[0] is not None else None
            newest_created_at = float(row[1]) if row and row[1] is not None else None
            max_retry_count = int(row[2]) if row and row[2] is not None else 0

            cursor = conn.execute(
                "SELECT retry_count, COUNT(*) FROM body_upload_queue GROUP BY retry_count"
            )
            retry_histogram: dict[int, int] = {}
            for retry_val, cnt in cursor:
                retry_histogram[int(retry_val)] = int(cnt)

            return BodyQueueStats(
                total_count=total_count,
                ready_count=ready_count,
                backoff_count=backoff_count,
                oldest_created_at=oldest_created_at,
                newest_created_at=newest_created_at,
                max_retry_count=max_retry_count,
                retry_histogram=retry_histogram,
            )
        finally:
            conn.close()

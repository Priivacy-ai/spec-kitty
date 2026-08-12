"""Connection-free project-owned body upload repository."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from kernel.clock import now_epoch, now_utc_iso
from specify_cli.sync.consent import allocate_capture_sequence
from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutGenerationAuthority,
    LayoutTestHooks,
    LayoutWritePermit,
)
from specify_cli.sync.project_context import VerifiedProjectStoreIdentity
from specify_cli.sync.project_store import ProjectUnitOfWork

from .queue import DEFAULT_MAX_QUEUE_SIZE, get_max_queue_size

DEFAULT_BODY_QUEUE_SIZE = DEFAULT_MAX_QUEUE_SIZE
_BACKOFF_BASE = 1.0
_BACKOFF_CAP = 300.0


class NamespaceRef(Protocol):
    @property
    def project_uuid(self) -> str: ...

    @property
    def mission_slug(self) -> str: ...

    @property
    def target_branch(self) -> str: ...

    @property
    def mission_type(self) -> str: ...

    @property
    def manifest_version(self) -> str: ...

    def to_dict(self) -> dict[str, str]: ...


@dataclass(frozen=True, slots=True)
class BodyUploadTask:
    row_id: str
    project_uuid: str
    epoch_id: int
    capture_sequence: int
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


@dataclass(frozen=True, slots=True)
class BodyQueueStats:
    total_count: int
    ready_count: int
    backoff_count: int
    oldest_created_at: float | None
    newest_created_at: float | None
    max_retry_count: int
    retry_histogram: dict[int, int]


@dataclass(frozen=True, slots=True)
class BodyUploadFailureRecord:
    project_uuid: str
    mission_slug: str
    target_branch: str
    mission_type: str
    manifest_version: str
    artifact_path: str
    content_hash: str
    hash_algorithm: str
    size_bytes: int
    failure_reason: str
    failure_count: int
    first_failed_at: float
    last_failed_at: float


class BodyEnqueueResult(StrEnum):
    ENQUEUED = "enqueued"
    ALREADY_EXISTS = "already_exists"
    QUEUE_FULL = "queue_full"


def _require_project_destination(permit: LayoutWritePermit) -> None:
    if permit.destination is not LayoutDestination.PROJECT_STORE:
        raise RuntimeError("body outbox writes require the project_only layout")


def _task_id(
    namespace: NamespaceRef,
    artifact_path: str,
    content_hash: str,
) -> str:
    material = "\0".join(
        (
            namespace.project_uuid,
            namespace.mission_slug,
            namespace.target_branch,
            namespace.mission_type,
            namespace.manifest_version,
            artifact_path,
            content_hash,
        )
    ).encode()
    # This digest is the durable body native identity, not charter content.
    return "body-" + hashlib.sha256(material).hexdigest()  # noqa: TID251


def _encode_reference(values: dict[str, Any]) -> str:
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


class OfflineBodyUploadQueue:
    """Short-lived body outbox adapter over one active project UoW."""

    __slots__ = ("_authority", "_max_queue_size", "_unit")

    def __init__(
        self,
        unit: ProjectUnitOfWork,
        authority: LayoutGenerationAuthority,
        max_queue_size: int | None = None,
    ) -> None:
        self._unit = unit
        self._authority = authority
        self._max_queue_size = max_queue_size if max_queue_size is not None else get_max_queue_size()

    @property
    def project_uuid(self) -> str:
        return str(self._unit.project_uuid.storage_token)

    @property
    def unit_of_work_identity(self) -> int:
        return int(self._unit.connection_identity)

    @property
    def store_identity(self) -> VerifiedProjectStoreIdentity:
        """Return the opaque identity minted for this repository's active UoW."""
        return self._unit.store_identity

    @property
    def max_queue_size(self) -> int:
        return self._max_queue_size

    def enqueue(
        self,
        namespace: NamespaceRef,
        artifact_path: str,
        content_hash: str,
        content_body: str,
        size_bytes: int,
        hash_algorithm: str = "sha256",
        *,
        test_hooks: LayoutTestHooks | None = None,
    ) -> BodyEnqueueResult:
        owner = namespace.project_uuid.strip().lower()
        if owner != self.project_uuid:
            raise ValueError("body task project UUID does not match store owner")
        identity = _task_id(namespace, artifact_path, content_hash)
        exists = self._unit.execute(
            "SELECT 1 FROM body_upload_tasks WHERE project_uuid = ? AND body_task_id = ?",
            (self.project_uuid, identity),
        ).fetchone()
        if exists is not None:
            return BodyEnqueueResult.ALREADY_EXISTS
        if self.size() >= self._max_queue_size:
            return BodyEnqueueResult.QUEUE_FULL
        created = now_epoch()

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            assignment = allocate_capture_sequence(self._unit)
            reference = _encode_reference(
                {
                    "mission_slug": namespace.mission_slug,
                    "target_branch": namespace.target_branch,
                    "mission_type": namespace.mission_type,
                    "manifest_version": namespace.manifest_version,
                    "artifact_path": artifact_path,
                    "hash_algorithm": hash_algorithm,
                    "content_body": content_body,
                    "size_bytes": size_bytes,
                    "retry_count": 0,
                    "next_attempt_at": 0.0,
                    "created_at": created,
                    "last_error": None,
                }
            )
            self._unit.execute(
                "INSERT INTO body_upload_tasks "
                "(body_task_id, project_uuid, epoch_id, capture_sequence, content_hash, "
                "body_reference, state, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                (
                    identity,
                    self.project_uuid,
                    assignment.epoch_id,
                    assignment.capture_sequence,
                    content_hash,
                    reference,
                    now_utc_iso(),
                ),
            )

        self._authority.execute_write(
            self._authority.issue_write_permit(),
            write,
            test_hooks=test_hooks,
        )
        return BodyEnqueueResult.ENQUEUED

    def _rows(self, *, include_terminal: bool = False) -> list[tuple[Any, ...]]:
        if include_terminal:
            rows = self._unit.execute(
                "SELECT body_task_id, epoch_id, capture_sequence, content_hash, "
                "body_reference, state FROM body_upload_tasks WHERE project_uuid = ? "
                "ORDER BY capture_sequence, body_task_id",
                (self.project_uuid,),
            ).fetchall()
        else:
            rows = self._unit.execute(
                "SELECT body_task_id, epoch_id, capture_sequence, content_hash, "
                "body_reference, state FROM body_upload_tasks WHERE project_uuid = ? "
                "AND state NOT IN ('uploaded', 'terminal_failed') "
                "ORDER BY capture_sequence, body_task_id",
                (self.project_uuid,),
            ).fetchall()
        return [tuple(row) for row in rows]

    def _task(self, row: tuple[Any, ...]) -> BodyUploadTask:
        data: Any = json.loads(str(row[4]))
        if not isinstance(data, dict):
            raise ValueError("body reference is not an object")
        return BodyUploadTask(
            row_id=str(row[0]),
            project_uuid=self.project_uuid,
            epoch_id=int(row[1]),
            capture_sequence=int(row[2]),
            mission_slug=str(data["mission_slug"]),
            target_branch=str(data["target_branch"]),
            mission_type=str(data["mission_type"]),
            manifest_version=str(data["manifest_version"]),
            artifact_path=str(data["artifact_path"]),
            content_hash=str(row[3]),
            hash_algorithm=str(data["hash_algorithm"]),
            content_body=str(data["content_body"]),
            size_bytes=int(data["size_bytes"]),
            retry_count=int(data["retry_count"]),
            next_attempt_at=float(data["next_attempt_at"]),
            created_at=float(data["created_at"]),
            last_error=(None if data.get("last_error") is None else str(data["last_error"])),
        )

    def drain(
        self,
        limit: int = 100,
        *,
        exclude_project_uuids: Collection[str] | None = None,
        exclude_row_ids: Collection[str] | None = None,
    ) -> list[BodyUploadTask]:
        denied_projects = {value.strip().lower() for value in (exclude_project_uuids or ())}
        if self.project_uuid in denied_projects:
            return []
        denied_rows = {str(value) for value in (exclude_row_ids or ())}
        now = now_epoch()
        return [task for task in (self._task(row) for row in self._rows()) if task.row_id not in denied_rows and task.next_attempt_at <= now][:limit]

    def _update(
        self,
        row_id: str,
        *,
        state: str,
        error: str | None = None,
        retry: bool = False,
    ) -> None:
        row = next((row for row in self._rows(include_terminal=True) if str(row[0]) == str(row_id)), None)
        if row is None:
            raise ValueError("body task is not owned by this project store")
        task = self._task(row)
        data: Any = json.loads(str(row[4]))
        retry_count = task.retry_count + (1 if retry else 0)
        data["retry_count"] = retry_count
        data["next_attempt_at"] = now_epoch() + min(_BACKOFF_BASE * (2 ** max(0, retry_count - 1)), _BACKOFF_CAP) if retry else task.next_attempt_at
        data["last_error"] = error if error is not None else task.last_error

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            self._unit.execute(
                "UPDATE body_upload_tasks SET body_reference = ?, state = ? WHERE project_uuid = ? AND body_task_id = ?",
                (_encode_reference(data), state, self.project_uuid, str(row_id)),
            )

        self._authority.execute_write(self._authority.issue_write_permit(), write)

    def mark_uploaded(self, row_id: str) -> None:
        self._update(row_id, state="uploaded")

    def mark_already_exists(self, row_id: str) -> None:
        self.mark_uploaded(row_id)

    def mark_failed_retryable(self, row_id: str, error: str) -> None:
        self._update(row_id, state="retry", error=error, retry=True)

    def mark_failed_permanent(self, row_id: str, error: str) -> None:
        self._update(row_id, state="terminal_failed", error=error)

    def record_permanent_failure(self, task: BodyUploadTask, error: str) -> None:
        if task.project_uuid != self.project_uuid:
            raise ValueError("body task is not owned by this project store")
        self.mark_failed_permanent(task.row_id, error)

    def get_recent_failures(self, limit: int = 10) -> list[BodyUploadFailureRecord]:
        failed = [self._task(row) for row in self._rows(include_terminal=True) if str(row[5]) == "terminal_failed"]
        return [
            BodyUploadFailureRecord(
                project_uuid=task.project_uuid,
                mission_slug=task.mission_slug,
                target_branch=task.target_branch,
                mission_type=task.mission_type,
                manifest_version=task.manifest_version,
                artifact_path=task.artifact_path,
                content_hash=task.content_hash,
                hash_algorithm=task.hash_algorithm,
                size_bytes=task.size_bytes,
                failure_reason=task.last_error or "permanent_failure",
                failure_count=1,
                first_failed_at=task.created_at,
                last_failed_at=task.created_at,
            )
            for task in reversed(failed[-limit:])
        ]

    def failure_count(self) -> int:
        return len(self.get_recent_failures(limit=max(1, len(self._rows(include_terminal=True)))))

    def remove_stale(self, max_retry_count: int = 20) -> int:
        stale = [task for task in (self._task(row) for row in self._rows()) if task.retry_count >= max_retry_count]
        for task in stale:
            self.mark_failed_permanent(task.row_id, task.last_error or "retry_limit")
        return len(stale)

    def remove_project_tasks(self, project_uuid: str) -> int:
        if project_uuid.strip().lower() != self.project_uuid:
            raise ValueError("cannot remove body tasks from another project store")
        before = len(self._rows(include_terminal=True))

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            self._unit.execute(
                "DELETE FROM body_upload_tasks WHERE project_uuid = ?",
                (self.project_uuid,),
            )

        self._authority.execute_write(self._authority.issue_write_permit(), write)
        return before

    def count_by_project(self) -> dict[str, int]:
        total = len(self._rows(include_terminal=True))
        return {self.project_uuid: total} if total else {}

    def size(self) -> int:
        return len(self._rows())

    def get_stats(self) -> BodyQueueStats:
        tasks = [self._task(row) for row in self._rows()]
        now = now_epoch()
        histogram: dict[int, int] = {}
        for task in tasks:
            histogram[task.retry_count] = histogram.get(task.retry_count, 0) + 1
        timestamps = [task.created_at for task in tasks]
        return BodyQueueStats(
            total_count=len(tasks),
            ready_count=sum(task.next_attempt_at <= now for task in tasks),
            backoff_count=sum(task.next_attempt_at > now for task in tasks),
            oldest_created_at=min(timestamps) if timestamps else None,
            newest_created_at=max(timestamps) if timestamps else None,
            max_retry_count=max(histogram, default=0),
            retry_histogram=histogram,
        )


__all__ = [
    "BodyEnqueueResult",
    "BodyQueueStats",
    "BodyUploadFailureRecord",
    "BodyUploadTask",
    "DEFAULT_BODY_QUEUE_SIZE",
    "OfflineBodyUploadQueue",
]

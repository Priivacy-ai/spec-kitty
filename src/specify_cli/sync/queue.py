"""Project-owned event outbox plus pure legacy-discovery path helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

import toml

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.paths import get_runtime_root
from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutGenerationAuthority,
    LayoutTestHooks,
    LayoutWritePermit,
)
from specify_cli.sync.project_store import ProjectUnitOfWork

DEFAULT_MAX_QUEUE_SIZE = 100_000
DEFAULT_STRICT_CAP_SIZE = 10_000
NAMESPACE_PROJECT_UUID = "namespace.project_uuid"
NAMESPACE_MISSION_SLUG = "namespace.mission_slug"


class _BatchEventResultLike(Protocol):
    status: str
    event_id: str


class OfflineQueueFull(RuntimeError):
    def __init__(self, *, cap: int, current: int) -> None:
        super().__init__(f"Offline sync queue at capacity ({current}/{cap})")
        self.cap = cap
        self.current = current


class LegacyQueueMigrationRequiredError(RuntimeError):
    """A retired path-backed queue operation was requested on a live path."""


@dataclass(slots=True)
class QueueStats:
    total_queued: int = 0
    max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE
    total_retried: int = 0
    oldest_event_age: timedelta | None = None
    retry_distribution: dict[str, int] = field(default_factory=dict)
    top_event_types: list[tuple[str, int]] = field(default_factory=list)
    drain_blocked_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProjectOutboxTask:
    task_id: str
    event_id: str
    project_uuid: str
    epoch_id: int
    capture_sequence: int
    event: dict[str, Any]
    state: str
    retry_count: int
    created_at: str


@dataclass(frozen=True, slots=True)
class LegacyRowCounts:
    event_rows: int = 0
    body_upload_rows: int = 0
    failure_log_rows: int = 0
    per_table: dict[str, int] = field(default_factory=dict)

    @property
    def total_rows(self) -> int:
        return self.event_rows + self.body_upload_rows + self.failure_log_rows

    def __bool__(self) -> bool:
        return bool(self.per_table)

    def __len__(self) -> int:
        return len(self.per_table)

    def __iter__(self) -> Any:
        return iter(self.per_table)

    def __contains__(self, key: object) -> bool:
        return key in self.per_table

    def __getitem__(self, key: str) -> int:
        return self.per_table[key]

    def get(self, key: str, default: int = 0) -> int:
        return self.per_table.get(key, default)

    def items(self) -> Any:
        return self.per_table.items()

    def keys(self) -> Any:
        return self.per_table.keys()

    def values(self) -> Any:
        return self.per_table.values()

    def __hash__(self) -> int:
        return hash((self.event_rows, self.body_upload_rows, self.failure_log_rows))


def _spec_kitty_dir() -> Path:
    return Path(get_runtime_root().base)


def _credentials_path() -> Path:
    return _spec_kitty_dir() / "credentials"


def _auth_session_store_dir() -> Path:
    return _spec_kitty_dir() / "auth"


def _legacy_queue_db_path() -> Path:
    """Named WP10 migration input; never opened by this module."""
    return _spec_kitty_dir() / "queue.db"


def _scoped_queue_dir() -> Path:
    return _spec_kitty_dir() / "queues"


def _active_scope_path() -> Path:
    return _spec_kitty_dir() / "active_queue_scope"


def _normalise_scope_part(value: str) -> str:
    return value.strip().lower()


def build_queue_scope(server_url: str, username: str, team_slug: str) -> str:
    material = "\0".join(_normalise_scope_part(value) for value in (server_url, username, team_slug))
    return hashlib.sha256(material.encode()).hexdigest()  # noqa: TID251 - legacy path identity


def scope_db_path(scope: str) -> Path:
    return _scoped_queue_dir() / f"queue-{scope}.db"


def read_active_scope(path: Path | None = None) -> str | None:
    source = path or _active_scope_path()
    try:
        value = source.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def write_active_scope(scope: str, path: Path | None = None) -> None:
    destination = path or _active_scope_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"{scope.strip()}\n", encoding="utf-8")


def _read_json(path: Path) -> Mapping[str, Any] | None:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, Mapping) else None


def read_queue_scope_from_credentials(credentials_path: Path | None = None) -> str | None:
    data = _read_json(credentials_path or _credentials_path())
    if data is None:
        return None
    explicit = data.get("queue_scope")
    return str(explicit) if isinstance(explicit, str) and explicit.strip() else None


def read_queue_scope_from_session(*, allow_rehydrate: bool = True) -> str | None:
    del allow_rehydrate
    active = read_active_scope()
    if active:
        return active
    session = _read_json(_auth_session_store_dir() / "session.json")
    if session is None:
        return None
    explicit = session.get("queue_scope")
    return str(explicit) if isinstance(explicit, str) and explicit.strip() else None


def default_queue_db_path(*_args: object, **_kwargs: object) -> Path:
    raise LegacyQueueMigrationRequiredError("live payload queues are selected by ProjectSyncStore; legacy paths are WP10 migration inputs")


def resolved_scope_db_path(resolved_target: object) -> Path:
    del resolved_target
    raise LegacyQueueMigrationRequiredError("target identity cannot select a live payload store")


def detect_legacy_rows_for_scope(scope: str) -> LegacyRowCounts:
    del scope
    raise LegacyQueueMigrationRequiredError("inspect legacy rows through the named WP10 read-only migration adapter")


def pending_events_for_scope(scope: str) -> int:
    del scope
    raise LegacyQueueMigrationRequiredError("legacy queue counts require WP10 migration mode")


def get_max_queue_size() -> int:
    config_file = _spec_kitty_dir() / "config.toml"
    if not config_file.exists():
        return DEFAULT_MAX_QUEUE_SIZE
    try:
        data = toml.load(config_file)
        return int(data.get("sync", {}).get("max_queue_size", DEFAULT_MAX_QUEUE_SIZE))
    except (OSError, TypeError, ValueError, toml.TomlDecodeError):
        return DEFAULT_MAX_QUEUE_SIZE


def _resolve_dotted(container: Any, path: str) -> Any:
    value = container
    for segment in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(segment)
    return value


COALESCEABLE_EVENT_TYPES: dict[str, list[str]] = {
    "MissionDossierArtifactIndexed": [
        NAMESPACE_PROJECT_UUID,
        NAMESPACE_MISSION_SLUG,
        "artifact_id.path",
    ],
    "MissionDossierSnapshotComputed": [
        NAMESPACE_PROJECT_UUID,
        NAMESPACE_MISSION_SLUG,
    ],
}


def _coalesce_key(event: dict[str, Any]) -> str | None:
    fields = COALESCEABLE_EVENT_TYPES.get(str(event.get("event_type")))
    if fields is None:
        return None
    payload = event.get("payload")
    payload = payload if isinstance(payload, Mapping) else {}
    values = [_resolve_dotted(event, field) or _resolve_dotted(payload, field) for field in fields]
    if any(value is None for value in values):
        return None
    return "|".join(str(value) for value in values)


def _owner_from_event(event: Mapping[str, Any]) -> str | None:
    candidates = (
        event.get("project_uuid"),
        _resolve_dotted(event, NAMESPACE_PROJECT_UUID),
        _resolve_dotted(event.get("payload", {}), NAMESPACE_PROJECT_UUID),
        _resolve_dotted(event.get("payload", {}), "project_uuid"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lower()
    return None


def _task_metadata(event_id: str, retry_count: int = 0) -> str:
    return json.dumps(
        {"event_id": event_id, "retry_count": retry_count},
        sort_keys=True,
        separators=(",", ":"),
    )


def _require_project_destination(permit: LayoutWritePermit) -> None:
    if permit.destination is not LayoutDestination.PROJECT_STORE:
        raise RuntimeError("outbox writes require the project_only layout")


class OfflineQueue:
    """Connection-free project event outbox repository."""

    MAX_QUEUE_SIZE = DEFAULT_MAX_QUEUE_SIZE
    _QUEUE_EXCLUDED_EVENT_TYPES = frozenset({"DecisionInputRequested", "DecisionInputAnswered"})

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
    def max_queue_size(self) -> int:
        return self._max_queue_size

    def _pending_rows(self) -> list[tuple[Any, ...]]:
        return [
            tuple(row)
            for row in self._unit.execute(
                "SELECT outbox_tasks.task_id, outbox_tasks.journal_entry_id, "
                "outbox_tasks.epoch_id, outbox_tasks.state, "
                "outbox_tasks.idempotency_identity, outbox_tasks.created_at, "
                "journal_entries.capture_sequence, journal_entries.payload_json "
                "FROM outbox_tasks JOIN journal_entries "
                "ON journal_entries.project_uuid = outbox_tasks.project_uuid "
                "AND journal_entries.entry_id = outbox_tasks.journal_entry_id "
                "WHERE outbox_tasks.project_uuid = ? AND outbox_tasks.task_kind = 'event' "
                "AND outbox_tasks.state NOT IN ('synced', 'terminal_failed') "
                "ORDER BY journal_entries.capture_sequence, outbox_tasks.task_id",
                (self.project_uuid,),
            ).fetchall()
        ]

    def append(self, event: dict[str, Any], *, cap: int | None = None) -> None:
        effective = cap if cap is not None else DEFAULT_STRICT_CAP_SIZE
        if self.size() >= effective:
            raise OfflineQueueFull(cap=effective, current=self.size())
        if not self.queue_event(event):
            raise RuntimeError("project outbox rejected the event")

    def queue_event(
        self,
        event: dict[str, Any],
        *,
        test_hooks: LayoutTestHooks | None = None,
    ) -> bool:
        if event.get("event_type") in self._QUEUE_EXCLUDED_EVENT_TYPES:
            return True
        owner = _owner_from_event(event)
        if owner != self.project_uuid:
            raise ValueError("event project UUID does not match store owner")
        event_id = str(event.get("event_id", "")).strip()
        event_type = str(event.get("event_type", "")).strip()
        if not event_id or not event_type:
            raise ValueError("event_id and event_type are required")
        task_id = f"event:{event_id}"
        existing = self._unit.execute(
            "SELECT 1 FROM outbox_tasks WHERE project_uuid = ? AND task_id = ?",
            (self.project_uuid, task_id),
        ).fetchone()
        if existing is not None:
            return True
        if self.size() >= self._max_queue_size:
            return False
        timestamp = str(event.get("created_at") or now_utc_iso())
        journal_event = Event(
            event_id=event_id,
            event_type=event_type,
            payload=json.dumps(event, sort_keys=True, separators=(",", ":")).encode(),
            occurred_at=str(event.get("occurred_at") or timestamp),
            created_at=str(event.get("created_at") or timestamp),
            coalesce_key=_coalesce_key(event),
            drain_blocked_reason=(str(event["drain_blocked_reason"]) if event.get("drain_blocked_reason") is not None else None),
            project_uuid=self.project_uuid,
            project_slug=(str(event["project_slug"]) if event.get("project_slug") else None),
            repo_slug=(str(event["repo_slug"]) if event.get("repo_slug") else None),
        )
        receipt = EventJournal(self._unit, self._authority).append(
            journal_event,
            test_hooks=test_hooks,
        )

        def write(permit: LayoutWritePermit) -> None:
            _require_project_destination(permit)
            self._unit.execute(
                "INSERT INTO outbox_tasks "
                "(task_id, project_uuid, epoch_id, journal_entry_id, task_kind, state, "
                "idempotency_identity, created_at) VALUES (?, ?, ?, ?, 'event', "
                "'pending', ?, ?)",
                (
                    task_id,
                    self.project_uuid,
                    receipt.epoch_id,
                    event_id,
                    _task_metadata(event_id),
                    timestamp,
                ),
            )

        self._authority.execute_write(
            self._authority.issue_write_permit(),
            write,
            test_hooks=test_hooks,
        )
        return True

    def drain_queue(self, limit: int = 1000) -> list[ProjectOutboxTask]:
        tasks: list[ProjectOutboxTask] = []
        for row in self._pending_rows()[:limit]:
            metadata = json.loads(str(row[4] or "{}"))
            event = EventJournal(self._unit, self._authority).read_by_id(str(row[1]))
            if event is None:
                raise ValueError("outbox task references a missing project journal entry")
            envelope = json.loads(event.payload)
            tasks.append(
                ProjectOutboxTask(
                    task_id=str(row[0]),
                    event_id=str(row[1]),
                    project_uuid=self.project_uuid,
                    epoch_id=int(row[2]),
                    capture_sequence=int(row[6]),
                    event=envelope,
                    state=str(row[3]),
                    retry_count=int(metadata.get("retry_count", 0)),
                    created_at=str(row[5]),
                )
            )
        return tasks

    def _update_tasks(self, event_ids: Iterable[str], *, state: str, retry: bool = False) -> int:
        ids = list(event_ids)
        if not ids:
            return 0
        updated = 0

        def write(permit: LayoutWritePermit) -> None:
            nonlocal updated
            _require_project_destination(permit)
            for event_id in ids:
                row = self._unit.execute(
                    "SELECT idempotency_identity FROM outbox_tasks WHERE project_uuid = ? AND journal_entry_id = ? AND task_kind = 'event'",
                    (self.project_uuid, event_id),
                ).fetchone()
                if row is None:
                    continue
                metadata = json.loads(str(row[0] or "{}"))
                count = int(metadata.get("retry_count", 0)) + (1 if retry else 0)
                self._unit.execute(
                    "UPDATE outbox_tasks SET state = ?, idempotency_identity = ? WHERE project_uuid = ? AND journal_entry_id = ? AND task_kind = 'event'",
                    (state, _task_metadata(event_id, count), self.project_uuid, event_id),
                )
                updated += 1

        self._authority.execute_write(self._authority.issue_write_permit(), write)
        return updated

    def mark_synced(self, event_ids: list[str]) -> None:
        self._update_tasks(event_ids, state="synced")

    def increment_retry(self, event_ids: list[str]) -> None:
        self._update_tasks(event_ids, state="retry", retry=True)

    def remove_events(self, event_ids: list[str]) -> int:
        return self._update_tasks(event_ids, state="synced")

    def process_batch_results(self, results: list[_BatchEventResultLike]) -> None:
        for result in results:
            if result.status in {"success", "duplicate"}:
                self.mark_synced([result.event_id])
            elif result.status in {"rejected"}:
                self.increment_retry([result.event_id])
            elif result.status in {"failed_permanent", "terminal_failed"}:
                self._update_tasks([result.event_id], state="terminal_failed")

    def size(self) -> int:
        row = self._unit.execute(
            "SELECT COUNT(*) FROM outbox_tasks WHERE project_uuid = ? AND task_kind = 'event' AND state NOT IN ('synced', 'terminal_failed')",
            (self.project_uuid,),
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def clear(self) -> None:
        self.mark_synced([task.event_id for task in self.drain_queue(limit=self.size())])

    def get_events_by_retry_count(self, max_retries: int = 5) -> list[dict[str, Any]]:
        return [task.event for task in self.drain_queue() if task.retry_count <= max_retries]

    def get_drain_blocked_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for task in self.drain_queue():
            reason = task.event.get("drain_blocked_reason") or "ready"
            counts[str(reason)] = counts.get(str(reason), 0) + 1
        return counts

    def get_queue_stats(self) -> QueueStats:
        tasks = self.drain_queue()
        retries = [task.retry_count for task in tasks]
        types: dict[str, int] = {}
        for task in tasks:
            event_type = str(task.event.get("event_type", "unknown"))
            types[event_type] = types.get(event_type, 0) + 1
        oldest_age = None
        if tasks:
            try:
                oldest = min(datetime.fromisoformat(task.created_at) for task in tasks)
                oldest_age = datetime.now(UTC) - oldest.astimezone(UTC)
            except ValueError:
                oldest_age = None
        return QueueStats(
            total_queued=len(tasks),
            max_queue_size=self._max_queue_size,
            total_retried=sum(retry > 0 for retry in retries),
            oldest_event_age=oldest_age,
            retry_distribution={
                "0 retries": sum(retry == 0 for retry in retries),
                "1-3 retries": sum(1 <= retry <= 3 for retry in retries),
                "4+ retries": sum(retry >= 4 for retry in retries),
            },
            top_event_types=sorted(types.items(), key=lambda item: (-item[1], item[0]))[:5],
            drain_blocked_counts=self.get_drain_blocked_counts(),
        )


__all__ = [
    "COALESCEABLE_EVENT_TYPES",
    "DEFAULT_MAX_QUEUE_SIZE",
    "DEFAULT_STRICT_CAP_SIZE",
    "LegacyQueueMigrationRequiredError",
    "LegacyRowCounts",
    "OfflineQueue",
    "OfflineQueueFull",
    "ProjectOutboxTask",
    "QueueStats",
    "_legacy_queue_db_path",
    "build_queue_scope",
    "default_queue_db_path",
    "detect_legacy_rows_for_scope",
    "get_max_queue_size",
    "pending_events_for_scope",
    "read_active_scope",
    "read_queue_scope_from_credentials",
    "read_queue_scope_from_session",
    "resolved_scope_db_path",
    "scope_db_path",
    "write_active_scope",
]

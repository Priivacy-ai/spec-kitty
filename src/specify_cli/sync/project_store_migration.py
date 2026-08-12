"""WAL-aware copy/verify/cutover migration into UUID-owned sync stores.

The legacy databases handled here are evidence.  Main/WAL/SHM bytes are copied
with matching pre/post fingerprints into a private disposable snapshot; only
that copy is opened, and SQLite's backup API materializes its committed logical
state.  The source is never passed to a connection or schema constructor.  All
durable progress lives in a versioned migration manifest; reruns resume the last
completed phase.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from specify_cli.core.atomic import atomic_write
from kernel.clock import now_utc_iso
from specify_cli.paths import get_runtime_root
from specify_cli.sync.daemon_protocol import DaemonCutoverProtocol
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.local_commit import validate_rfc3339_datetime
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork


MIGRATION_PROTOCOL_VERSION = 1
_MANIFEST_NAME = "manifest.json"
_QUARANTINE_NAME = "quarantine.json"
_SQLITE_SUFFIXES = ("", "-wal", "-shm")
_EVENT_TABLES = frozenset({"event_journal", "queue"})
_BODY_TABLES = frozenset({"body_upload_queue"})
_ATTEMPT_TABLES = frozenset({"delivery_attempts"})
_RESULT_TABLES = frozenset({"delivery_results"})
_CONSENT_TABLES = frozenset({"legacy_consent", "project_consent"})
_MIGRATABLE_TABLES = _EVENT_TABLES | _BODY_TABLES | _ATTEMPT_TABLES | _RESULT_TABLES | _CONSENT_TABLES
_REQUIRED_COLUMNS: Mapping[str, frozenset[str]] = {
    "event_journal": frozenset({"event_id", "payload"}),
    "queue": frozenset({"event_id", "data"}),
    "body_upload_queue": frozenset({"project_uuid", "artifact_path", "content_hash", "content_body"}),
    "delivery_attempts": frozenset({"attempt_id"}),
    "delivery_results": frozenset({"result_id", "attempt_id", "outcome"}),
    "legacy_consent": frozenset({"project_uuid"}),
    "project_consent": frozenset({"project_uuid"}),
}


def _migration_token(migration_id: str) -> str:
    migration = migration_id.strip()
    if not migration or not migration.isascii() or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in migration):
        raise ValueError("migration identity must be a non-empty ASCII token")
    return migration


def migration_artifact_path(
    runtime_root: Path,
    migration_id: str,
    artifact_name: str,
) -> Path:
    """Resolve one closed-name governed artifact beneath the migration root."""
    if artifact_name not in {_MANIFEST_NAME, _QUARANTINE_NAME}:
        raise ValueError("migration artifact name is not public")
    return runtime_root.resolve() / "projects" / ".migration" / _migration_token(migration_id) / artifact_name


class MigrationError(RuntimeError):
    """A legacy migration invariant failed closed."""


class SourceChangedError(MigrationError):
    """Source evidence changed after inventory."""


class _Unset:
    """Typed sentinel for phase fields that must retain their current value."""


_UNSET = _Unset()


class MigrationPhase(StrEnum):
    """Durable, monotonic cutover phases."""

    INVENTORIED = "inventoried"
    QUIESCED = "quiesced"
    COPIED = "copied"
    VERIFIED = "verified"
    CUTOVER = "cutover"
    RESTARTED = "restarted"
    COMPLETE = "complete"
    FAILED = "failed"


_PHASE_ORDER = {
    MigrationPhase.INVENTORIED: 1,
    MigrationPhase.QUIESCED: 2,
    MigrationPhase.COPIED: 3,
    MigrationPhase.VERIFIED: 4,
    MigrationPhase.CUTOVER: 5,
    MigrationPhase.RESTARTED: 6,
    MigrationPhase.COMPLETE: 7,
    MigrationPhase.FAILED: 99,
}


class QuarantineReason(StrEnum):
    """Closed reason vocabulary for permanently non-deliverable rows."""

    MISSING_PROJECT_UUID = "missing_project_uuid"
    MALFORMED_PROJECT_UUID = "malformed_project_uuid"
    NIL_PROJECT_UUID = "nil_project_uuid"
    CONFLICTING_PROJECT_UUID = "conflicting_project_uuid"
    LEDGER_GHOST = "ledger_ghost"
    DIVERGENT_DUPLICATE = "divergent_duplicate"
    INCOMPATIBLE_ROW = "incompatible_row"
    POST_CUTOVER_RESIDUE = "post_cutover_residue"


@dataclass(frozen=True, slots=True)
class SidecarFingerprint:
    """Physical evidence for a SQLite main/WAL/SHM file."""

    path: str
    present: bool
    size_bytes: int
    sha256: str | None
    included_in_logical_snapshot: bool


@dataclass(frozen=True, slots=True)
class SourceFingerprint:
    """One read-only logical SQLite snapshot and its physical sidecars."""

    path: str
    main: SidecarFingerprint
    wal: SidecarFingerprint
    shm: SidecarFingerprint
    schema_version: int
    data_version: int
    logical_sha256: str
    row_count: int
    tables: tuple[str, ...]
    table_columns: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class LegacyRow:
    """Canonical immutable representation of one source table row."""

    source_path: str
    table: str
    row_id: str
    project_uuid: str | None
    values: Mapping[str, object]
    logical_sha256: str


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """One source row excluded from every project sender surface."""

    source_path: str
    table: str
    row_id: str
    reason: QuarantineReason
    logical_sha256: str
    evidence: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class MigrationManifest:
    """Exact inventory, partition, quarantine and durable phase record."""

    migration_id: str
    protocol_version: int
    phase: MigrationPhase
    sources: tuple[SourceFingerprint, ...]
    partitions: Mapping[str, tuple[LegacyRow, ...]]
    quarantine: tuple[QuarantineRecord, ...]
    source_digest: str
    total_rows: int
    started_at: str
    updated_at: str
    completed_at: str | None = None
    failure: str | None = None
    observed_source_digest: str | None = None
    daemon_quiesce: Mapping[str, object] | None = None
    daemon_restart: Mapping[str, object] | None = None
    residue: tuple[QuarantineRecord, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a payload-free representation for CLI and durable reports."""
        raw = asdict(self)
        raw["partitions"] = {project: [_safe_legacy_row(row) for row in rows] for project, rows in self.partitions.items()}
        raw["quarantine"] = [_safe_quarantine_row(row) for row in self.quarantine]
        raw["residue"] = [_safe_quarantine_row(row) for row in self.residue]
        return cast("dict[str, object]", _json_value(raw))


@dataclass(frozen=True, slots=True)
class MigrationTestHooks:
    """Deterministic phase boundary used only by crash-ordering tests."""

    after_phase: Callable[[MigrationPhase], None] | None = None
    before_project_only_publish: Callable[[], None] | None = None


def _json_value(value: object) -> Any:
    if isinstance(value, bytes):
        return {"$bytes": base64.b64encode(value).decode("ascii")}
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _decode_json_value(value: object) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$bytes"} and isinstance(value["$bytes"], str):
            return base64.b64decode(value["$bytes"].encode("ascii"))
        return {str(key): _decode_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return tuple(_decode_json_value(item) for item in value)
    return value


def _stable_json(value: object) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_stable_json(value).encode("ascii")).hexdigest()  # noqa: TID251 -- evidence integrity


def _safe_evidence(values: Mapping[str, object]) -> dict[str, object]:
    # Durable reports are loaded again during crash recovery.  A report-shaped
    # value is already the canonical projection; hashing it a second time would
    # make identical uninterrupted/resumed migrations disagree.
    if (
        set(values).issubset({"columns", "values_sha256", "residue_change"})
        and isinstance(values.get("columns"), (tuple, list))
        and isinstance(values.get("values_sha256"), str)
    ):
        projected: dict[str, object] = {
            "columns": tuple(str(column) for column in cast("Sequence[object]", values["columns"])),
            "values_sha256": str(values["values_sha256"]),
        }
        residue_change = values.get("residue_change")
        if residue_change in {"added", "changed", "removed"}:
            projected["residue_change"] = str(residue_change)
        return projected
    evidence: dict[str, object] = {
        "columns": tuple(sorted(str(column) for column in values)),
        "values_sha256": _digest(values),
    }
    residue_change = values.get("residue_change")
    if residue_change in {"added", "changed", "removed"}:
        evidence["residue_change"] = residue_change
    return evidence


def _safe_legacy_row(row: LegacyRow) -> dict[str, object]:
    raw = asdict(row)
    raw["values"] = _safe_evidence(row.values)
    return raw


def _safe_quarantine_row(row: QuarantineRecord) -> dict[str, object]:
    raw = asdict(row)
    raw["evidence"] = _safe_evidence(row.evidence)
    return raw


def _file_fingerprint(path: Path, *, logical: bool) -> SidecarFingerprint:
    if not path.exists():
        return SidecarFingerprint(str(path), False, 0, None, logical)
    payload = path.read_bytes()
    return SidecarFingerprint(
        path=str(path),
        present=True,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),  # noqa: TID251 -- evidence integrity
        included_in_logical_snapshot=logical,
    )


def _table_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"))


def _quoted(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_columns(
    connection: sqlite3.Connection,
    table: str,
) -> tuple[str, ...]:
    metadata = tuple(connection.execute(f"PRAGMA table_xinfo({_quoted(table)})"))
    hidden = tuple(str(row[1]) for row in metadata if int(row[6]) != 0)
    if hidden:
        raise MigrationError(f"legacy source table {table} has generated or hidden columns: {sorted(hidden)!r}")
    return tuple(str(row[1]) for row in metadata)


def _table_rows(connection: sqlite3.Connection, table: str) -> tuple[LegacyRow, ...]:
    columns = _table_columns(connection, table)
    if not columns:
        return ()
    projection = ", ".join(_quoted(column) for column in columns)
    try:
        rows = connection.execute(
            f"SELECT rowid, {projection} FROM {_quoted(table)} ORDER BY rowid"  # noqa: S608 -- identifiers are quoted source metadata
        ).fetchall()
        with_rowid = True
    except sqlite3.OperationalError:
        rows = connection.execute(
            f"SELECT {projection} FROM {_quoted(table)}"  # noqa: S608 -- identifiers are quoted source metadata
        ).fetchall()
        with_rowid = False
    result: list[LegacyRow] = []
    for index, raw in enumerate(rows, start=1):
        values_raw = raw[1:] if with_rowid else raw
        values = {column: cast("object", value) for column, value in zip(columns, values_raw, strict=True)}
        row_id = _row_identity(table, values, raw[0] if with_rowid else index)
        result.append(
            LegacyRow(
                source_path="",
                table=table,
                row_id=row_id,
                project_uuid=_project_uuid_value(values),
                values=values,
                logical_sha256=_digest((table, row_id, values)),
            )
        )
    return tuple(result)


def _row_identity(table: str, values: Mapping[str, object], fallback: object) -> str:
    candidates = {
        "event_journal": ("event_id",),
        "queue": ("event_id", "id"),
        "body_upload_queue": ("body_task_id", "id", "artifact_path"),
        "delivery_attempts": ("attempt_id",),
        "delivery_results": ("result_id",),
        "legacy_consent": ("project_uuid",),
        "project_consent": ("project_uuid",),
    }.get(table, ("id",))
    for candidate in candidates:
        value = values.get(candidate)
        if value is not None and str(value).strip():
            return str(value)
    return str(fallback)


def _project_uuid_value(values: Mapping[str, object]) -> str | None:
    raw = values.get("project_uuid")
    if raw is not None:
        return str(raw)
    for payload_field in ("payload", "data", "payload_json"):
        candidate = values.get(payload_field)
        if candidate is None:
            continue
        try:
            decoded: Any = json.loads(candidate.decode("utf-8") if isinstance(candidate, bytes) else str(candidate))
        except (UnicodeError, ValueError, TypeError):
            continue
        if isinstance(decoded, dict) and decoded.get("project_uuid") is not None:
            return str(decoded["project_uuid"])
    return None


def _payload_project_uuid(values: Mapping[str, object]) -> str | None:
    for payload_field in ("payload", "data", "payload_json"):
        candidate = values.get(payload_field)
        if candidate is None:
            continue
        try:
            decoded: Any = json.loads(candidate.decode("utf-8") if isinstance(candidate, bytes) else str(candidate))
        except (UnicodeError, ValueError, TypeError):
            continue
        if isinstance(decoded, dict) and decoded.get("project_uuid") is not None:
            return str(decoded["project_uuid"])
    return None


def _canonical_project(raw: str | None) -> tuple[str | None, QuarantineReason | None]:
    if raw is None or not raw.strip():
        return None, QuarantineReason.MISSING_PROJECT_UUID
    try:
        canonical = CanonicalProjectUUID.parse(raw)
    except ValueError as exc:
        return (
            None,
            QuarantineReason.NIL_PROJECT_UUID if "nil" in str(exc) else QuarantineReason.MALFORMED_PROJECT_UUID,
        )
    return canonical.storage_token, None


def _direct_row_identity(
    row: LegacyRow,
) -> tuple[str | None, QuarantineReason | None]:
    if row.table not in _MIGRATABLE_TABLES:
        return None, QuarantineReason.INCOMPATIBLE_ROW
    canonical, reason = _canonical_project(row.project_uuid)
    payload_identity = _payload_project_uuid(row.values)
    if canonical is not None and payload_identity is not None:
        payload_canonical, payload_reason = _canonical_project(payload_identity)
        if payload_reason is not None or payload_canonical != canonical:
            return None, QuarantineReason.CONFLICTING_PROJECT_UUID
    return canonical, reason


def _mark_divergent_duplicates(
    rows: Sequence[LegacyRow],
    resolutions: dict[tuple[str, str, str], tuple[str | None, QuarantineReason | None]],
) -> None:
    groups: dict[tuple[str, str, str], list[LegacyRow]] = {}
    for row in rows:
        canonical, reason = resolutions[(row.source_path, row.table, row.row_id)]
        if canonical is not None and reason is None:
            groups.setdefault((canonical, row.table, row.row_id), []).append(row)
    for duplicates in groups.values():
        if len({row.logical_sha256 for row in duplicates}) <= 1:
            continue
        for row in duplicates:
            resolutions[(row.source_path, row.table, row.row_id)] = (
                None,
                QuarantineReason.DIVERGENT_DUPLICATE,
            )


def _read_logical_snapshot(
    snapshot: Path,
    source: Path,
) -> tuple[
    tuple[str, ...],
    Mapping[str, tuple[str, ...]],
    tuple[LegacyRow, ...],
    str,
]:
    snapshot_connection = sqlite3.connect(f"file:{snapshot}?mode=ro", uri=True)
    snapshot_connection.execute("PRAGMA query_only = ON")
    try:
        tables = _table_names(snapshot_connection)
        table_columns = {table: _table_columns(snapshot_connection, table) for table in tables}
        for table, required in _REQUIRED_COLUMNS.items():
            if table not in table_columns:
                continue
            missing = required - set(table_columns[table])
            if missing:
                raise MigrationError(f"legacy source table {table} is incompatible; missing columns {sorted(missing)!r}")
        rows = tuple(
            LegacyRow(
                source_path=str(source),
                table=row.table,
                row_id=row.row_id,
                project_uuid=row.project_uuid,
                values=row.values,
                logical_sha256=row.logical_sha256,
            )
            for table in tables
            for row in _table_rows(snapshot_connection, table)
        )
    finally:
        snapshot_connection.close()
    logical_sha = _digest(tuple((row.table, row.row_id, row.values, row.logical_sha256) for row in rows))
    return tables, table_columns, rows, logical_sha


def _snapshot_source(
    source: Path,
    snapshot: Path,
) -> tuple[SourceFingerprint, tuple[LegacyRow, ...]]:
    if not source.is_file():
        raise MigrationError(f"legacy source is absent: {source}")
    main = _file_fingerprint(source, logical=True)
    wal = _file_fingerprint(Path(f"{source}-wal"), logical=True)
    shm = _file_fingerprint(Path(f"{source}-shm"), logical=False)
    snapshot.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    snapshot.parent.chmod(0o700)
    snapshot.unlink(missing_ok=True)
    staging = snapshot.parent / ".raw-staging"
    staging.mkdir(mode=0o700, exist_ok=True)
    staging.chmod(0o700)
    physical_copy = staging / snapshot.name
    copied_paths = tuple(Path(f"{physical_copy}{suffix}") for suffix in _SQLITE_SUFFIXES)
    source_paths = tuple(Path(f"{source}{suffix}") for suffix in _SQLITE_SUFFIXES)
    source_connection: sqlite3.Connection | None = None
    try:
        for copied in copied_paths:
            copied.unlink(missing_ok=True)
        before = tuple(_file_fingerprint(path, logical=index < 2) for index, path in enumerate(source_paths))
        for source_path, copied in zip(source_paths, copied_paths, strict=True):
            if source_path.exists():
                _copy_private_file(source_path, copied)
        after = tuple(_file_fingerprint(path, logical=index < 2) for index, path in enumerate(source_paths))
        if before != after:
            raise SourceChangedError("legacy source changed while its read-only physical evidence was copied")
        source_connection = sqlite3.connect(physical_copy, timeout=0)
        source_connection.execute("PRAGMA query_only = ON")
        source_connection.execute("PRAGMA busy_timeout = 0")
        schema_version = int(source_connection.execute("PRAGMA schema_version").fetchone()[0])
        data_version = int(source_connection.execute("PRAGMA data_version").fetchone()[0])
        _create_private_empty_file(snapshot)
        destination = sqlite3.connect(snapshot)
        try:
            source_connection.backup(destination)
        finally:
            destination.close()
    except sqlite3.Error as exc:
        raise MigrationError(f"read-only logical snapshot failed for {source}: {exc}") from exc
    finally:
        if source_connection is not None:
            source_connection.close()
        for copied in copied_paths:
            copied.unlink(missing_ok=True)
        with suppress(OSError):
            staging.rmdir()
    tables, table_columns, rows, logical_sha = _read_logical_snapshot(
        snapshot,
        source,
    )
    return (
        SourceFingerprint(
            path=str(source),
            main=main,
            wal=wal,
            shm=shm,
            schema_version=schema_version,
            data_version=data_version,
            logical_sha256=logical_sha,
            row_count=len(rows),
            tables=tables,
            table_columns=table_columns,
        ),
        rows,
    )


def _create_private_empty_file(path: Path) -> None:
    """Create an empty file that can never be broader than owner read/write."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)


def _copy_private_file(source: Path, destination: Path) -> None:
    """Copy raw evidence only after the destination exists with mode 0600."""
    _create_private_empty_file(destination)
    with source.open("rb") as input_stream, destination.open("wb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream)


def _partition(  # noqa: C901 -- closed attribution/relation classifier
    rows: Sequence[LegacyRow],
) -> tuple[dict[str, tuple[LegacyRow, ...]], tuple[QuarantineRecord, ...]]:
    row_keys = {(row.source_path, row.table, row.row_id): row for row in rows}
    resolutions = {key: _direct_row_identity(row) for key, row in row_keys.items()}
    # Duplicate identity is resolved over the immutable raw census before any
    # schema/relation filtering. One malformed divergent copy therefore poisons
    # every copy instead of allowing a superficially valid winner.
    _mark_divergent_duplicates(rows, resolutions)
    event_projects = {(row.source_path, row.row_id): resolutions[(row.source_path, row.table, row.row_id)][0] for row in rows if row.table in _EVENT_TABLES}
    attempt_projects: dict[tuple[str, str], str | None] = {}
    attempts: dict[tuple[str, str], LegacyRow] = {}
    for row in rows:
        if row.table not in _ATTEMPT_TABLES:
            continue
        key = (row.source_path, row.table, row.row_id)
        direct, reason = resolutions[key]
        if direct is not None and reason is None and not _valid_delivery_attempt(row.values):
            resolutions[key] = (None, QuarantineReason.INCOMPATIBLE_ROW)
            direct, reason = resolutions[key]
        if direct is not None and reason is None and row.values.get("outbox_task_id") is not None:
            # WP10 does not migrate the canonical outbox task/history relation.
            # Keeping the FK would fail mid-copy; dropping it would falsify exact
            # recovery identity.  Park the attempt and its dependent result.
            resolutions[key] = (None, QuarantineReason.INCOMPATIBLE_ROW)
            direct, reason = resolutions[key]
        event_id = str(row.values.get("event_id") or "")
        related = event_projects.get((row.source_path, event_id))
        if direct is not None and related is not None and direct != related:
            resolutions[key] = (None, QuarantineReason.CONFLICTING_PROJECT_UUID)
        elif direct is None and reason is QuarantineReason.MISSING_PROJECT_UUID and related is not None:
            resolutions[key] = (related, None)
        attempt_projects[(row.source_path, row.row_id)] = resolutions[key][0]
        attempts[(row.source_path, row.row_id)] = row
    for row in rows:
        if row.table not in _RESULT_TABLES:
            continue
        key = (row.source_path, row.table, row.row_id)
        if not _valid_delivery_result(row.values):
            resolutions[key] = (None, QuarantineReason.INCOMPATIBLE_ROW)
            continue
        attempt_id = str(row.values.get("attempt_id") or "")
        attempt_key = (row.source_path, attempt_id)
        if attempt_key not in attempt_projects:
            resolutions[key] = (None, QuarantineReason.LEDGER_GHOST)
            continue
        direct, reason = resolutions[key]
        related = attempt_projects[attempt_key]
        if related is None:
            resolutions[key] = (None, QuarantineReason.LEDGER_GHOST)
            continue
        related_attempt = attempts[attempt_key]
        if any(row.values[field] != related_attempt.values[field] for field in ("epoch_id", "target_generation", "admission_generation")):
            resolutions[key] = (None, QuarantineReason.INCOMPATIBLE_ROW)
            continue
        if direct is not None and related is not None and direct != related:
            resolutions[key] = (None, QuarantineReason.CONFLICTING_PROJECT_UUID)
        elif direct is None and reason is QuarantineReason.MISSING_PROJECT_UUID and related is not None:
            resolutions[key] = (related, None)

    # Duplicate classification can newly quarantine an attempt after its result
    # was initially resolved.  Reconcile the relation once more before building
    # partitions so no result can outlive its exact source-owned attempt and
    # fail only after copy has started.
    for row in rows:
        if row.table not in _RESULT_TABLES:
            continue
        key = (row.source_path, row.table, row.row_id)
        canonical, reason = resolutions[key]
        if canonical is None or reason is not None:
            continue
        attempt_id = str(row.values.get("attempt_id") or "")
        attempt_resolution = resolutions.get((row.source_path, "delivery_attempts", attempt_id))
        if attempt_resolution is None or attempt_resolution[0] is None or attempt_resolution[1] is not None:
            resolutions[key] = (None, QuarantineReason.LEDGER_GHOST)

    partitions: dict[str, list[LegacyRow]] = {}
    quarantine: list[QuarantineRecord] = []
    for row in rows:
        canonical, reason = resolutions[(row.source_path, row.table, row.row_id)]
        if reason is not None or canonical is None:
            quarantine.append(
                QuarantineRecord(
                    source_path=row.source_path,
                    table=row.table,
                    row_id=row.row_id,
                    reason=reason or QuarantineReason.INCOMPATIBLE_ROW,
                    logical_sha256=row.logical_sha256,
                    evidence=row.values,
                )
            )
            continue
        partitions.setdefault(canonical, []).append(
            LegacyRow(
                source_path=row.source_path,
                table=row.table,
                row_id=row.row_id,
                project_uuid=canonical,
                values=row.values,
                logical_sha256=row.logical_sha256,
            )
        )
    return (
        {project: tuple(sorted(project_rows, key=lambda item: (item.table, item.row_id))) for project, project_rows in sorted(partitions.items())},
        tuple(sorted(quarantine, key=lambda item: (item.source_path, item.table, item.row_id))),
    )


_ATTEMPT_COLUMNS = frozenset(
    {
        "attempt_id",
        "project_uuid",
        "epoch_id",
        "outbox_task_id",
        "consent_generation",
        "target_generation",
        "admission_generation",
        "binding_audience",
        "payload_hash",
        "payload_reference",
        "state",
        "deadline_at",
        "reconciliation_policy",
        "created_at",
    }
)
_ATTEMPT_STATES = frozenset(
    {
        "prepared",
        "in_flight",
        "pending_remote",
        "retryable_no_effect",
        "unknown",
        "terminal_unknown",
        "succeeded",
        "refused",
        "canceled",
    }
)
_RECONCILIATION_POLICIES = frozenset(
    {
        "native_identity_query",
        "native_identity_retry",
        "native_identity_retry_then_query",
        "operator_review",
    }
)
_RESULT_COLUMNS = frozenset(
    {
        "result_id",
        "project_uuid",
        "epoch_id",
        "attempt_id",
        "target_generation",
        "admission_generation",
        "outcome",
        "terminal_refusal_category",
        "recorded_at",
    }
)
_RESULT_OUTCOMES = frozenset(
    {
        "delivered",
        "duplicate",
        "pending",
        "retryable_no_effect",
        "refused",
        "unknown",
        "terminal_unknown",
    }
)


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_delivery_attempt(values: Mapping[str, object]) -> bool:
    """Accept only the complete canonical authority/recovery attempt shape."""
    if set(values) != _ATTEMPT_COLUMNS:
        return False
    if not all(_positive_int(values[field]) for field in ("epoch_id", "consent_generation", "target_generation")):
        return False
    if not all(
        _non_empty_text(values[field])
        for field in (
            "attempt_id",
            "project_uuid",
            "admission_generation",
            "binding_audience",
            "payload_hash",
            "payload_reference",
            "state",
            "deadline_at",
            "reconciliation_policy",
            "created_at",
        )
    ):
        return False
    outbox_task_id = values.get("outbox_task_id")
    if outbox_task_id is not None and not _non_empty_text(outbox_task_id):
        return False
    try:
        for field_name in ("deadline_at", "created_at"):
            validate_rfc3339_datetime(
                values[field_name],
                field_name=f"delivery attempt {field_name}",
            )
    except ValueError:
        return False
    return str(values["state"]) in _ATTEMPT_STATES and str(values["reconciliation_policy"]) in _RECONCILIATION_POLICIES


def _valid_delivery_result(values: Mapping[str, object]) -> bool:
    """Accept only exact, closed WP06 result authority and outcome shapes."""
    if set(values) != _RESULT_COLUMNS:
        return False
    if not all(_positive_int(values[field]) for field in ("epoch_id", "target_generation")):
        return False
    if not all(
        _non_empty_text(values[field])
        for field in (
            "result_id",
            "attempt_id",
            "admission_generation",
            "outcome",
            "recorded_at",
        )
    ):
        return False
    try:
        validate_rfc3339_datetime(
            values["recorded_at"],
            field_name="delivery result recorded_at",
        )
    except ValueError:
        return False
    outcome = str(values["outcome"])
    if outcome not in _RESULT_OUTCOMES:
        return False
    category = values.get("terminal_refusal_category")
    if category is not None and not _non_empty_text(category):
        return False
    if outcome == "refused":
        return _non_empty_text(category)
    if outcome in {"delivered", "duplicate"}:
        return category is None
    return True


def _manifest_from_dict(raw: Mapping[str, object]) -> MigrationManifest:
    def sidecar(value: Mapping[str, object]) -> SidecarFingerprint:
        return SidecarFingerprint(
            path=str(value["path"]),
            present=bool(value["present"]),
            size_bytes=int(cast("int | str", value["size_bytes"])),
            sha256=None if value.get("sha256") is None else str(value["sha256"]),
            included_in_logical_snapshot=bool(value["included_in_logical_snapshot"]),
        )

    sources = tuple(
        SourceFingerprint(
            path=str(item["path"]),
            main=sidecar(cast("Mapping[str, object]", item["main"])),
            wal=sidecar(cast("Mapping[str, object]", item["wal"])),
            shm=sidecar(cast("Mapping[str, object]", item["shm"])),
            schema_version=int(cast("int | str", item["schema_version"])),
            data_version=int(cast("int | str", item["data_version"])),
            logical_sha256=str(item["logical_sha256"]),
            row_count=int(cast("int | str", item["row_count"])),
            tables=tuple(str(value) for value in cast("Sequence[object]", item["tables"])),
            table_columns={
                str(table): tuple(str(column) for column in cast("Sequence[object]", columns))
                for table, columns in cast(
                    "Mapping[str, object]",
                    item.get("table_columns", {}),
                ).items()
            },
        )
        for item in cast("Sequence[Mapping[str, object]]", raw["sources"])
    )

    def legacy_row(item: Mapping[str, object]) -> LegacyRow:
        return LegacyRow(
            source_path=str(item["source_path"]),
            table=str(item["table"]),
            row_id=str(item["row_id"]),
            project_uuid=None if item.get("project_uuid") is None else str(item["project_uuid"]),
            values=cast("Mapping[str, object]", _decode_json_value(item["values"])),
            logical_sha256=str(item["logical_sha256"]),
        )

    partitions = {
        str(project): tuple(legacy_row(item) for item in cast("Sequence[Mapping[str, object]]", items))
        for project, items in cast("Mapping[str, object]", raw["partitions"]).items()
    }
    quarantine = tuple(
        QuarantineRecord(
            source_path=str(item["source_path"]),
            table=str(item["table"]),
            row_id=str(item["row_id"]),
            reason=QuarantineReason(str(item["reason"])),
            logical_sha256=str(item["logical_sha256"]),
            evidence=cast("Mapping[str, object]", _decode_json_value(item["evidence"])),
        )
        for item in cast("Sequence[Mapping[str, object]]", raw["quarantine"])
    )
    return MigrationManifest(
        migration_id=str(raw["migration_id"]),
        protocol_version=int(cast("int | str", raw["protocol_version"])),
        phase=MigrationPhase(str(raw["phase"])),
        sources=sources,
        partitions=partitions,
        quarantine=quarantine,
        source_digest=str(raw["source_digest"]),
        total_rows=int(cast("int | str", raw["total_rows"])),
        started_at=str(raw["started_at"]),
        updated_at=str(raw["updated_at"]),
        completed_at=None if raw.get("completed_at") is None else str(raw["completed_at"]),
        failure=None if raw.get("failure") is None else str(raw["failure"]),
        observed_source_digest=(None if raw.get("observed_source_digest") is None else str(raw["observed_source_digest"])),
        daemon_quiesce=cast("Mapping[str, object] | None", raw.get("daemon_quiesce")),
        daemon_restart=cast("Mapping[str, object] | None", raw.get("daemon_restart")),
        residue=tuple(
            QuarantineRecord(
                source_path=str(item["source_path"]),
                table=str(item["table"]),
                row_id=str(item["row_id"]),
                reason=QuarantineReason(str(item["reason"])),
                logical_sha256=str(item["logical_sha256"]),
                evidence=cast(
                    "Mapping[str, object]",
                    _decode_json_value(item["evidence"]),
                ),
            )
            for item in cast(
                "Sequence[Mapping[str, object]]",
                raw.get("residue", ()),
            )
        ),
    )


@dataclass
class LegacyProjectStoreMigration:
    """Resumable coordinator for one explicit set of legacy SQLite sources."""

    runtime_root: Path
    sources: Sequence[Path]
    daemon_protocol: DaemonCutoverProtocol | None = None
    _root: Path = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._root = self.runtime_root.resolve()
        configured = get_runtime_root().base.resolve()
        if self._root != configured:
            raise ValueError(f"migration runtime root {self._root} differs from canonical runtime {configured}")
        normalized = tuple(Path(path).resolve() for path in self.sources)
        if not normalized:
            raise ValueError("at least one explicit legacy source is required")
        if len(normalized) != len(set(normalized)):
            raise ValueError("legacy source paths must be unique")
        project_root = self._root / "projects"
        if any(path == project_root or project_root in path.parents for path in normalized):
            raise ValueError("legacy sources cannot be project-store or migration artifacts")
        self.sources = normalized

    def _directory(self, migration_id: str) -> Path:
        return self._root / "projects" / ".migration" / _migration_token(migration_id)

    def _manifest_path(self, migration_id: str) -> Path:
        return self._directory(migration_id) / _MANIFEST_NAME

    def _save(self, manifest: MigrationManifest) -> MigrationManifest:
        path = self._manifest_path(manifest.migration_id)
        atomic_write(
            path,
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
            mkdir=True,
        )
        atomic_write(
            path.parent / _QUARANTINE_NAME,
            json.dumps(
                [_json_value(_safe_quarantine_row(row)) for row in (*manifest.quarantine, *manifest.residue)],
                indent=2,
                sort_keys=True,
            )
            + "\n",
            mkdir=True,
        )
        return manifest

    def _load(self, migration_id: str) -> MigrationManifest | None:
        path = self._manifest_path(migration_id)
        if not path.exists():
            return None
        try:
            raw: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MigrationError(f"migration manifest is unreadable: {path}") from exc
        if not isinstance(raw, dict):
            raise MigrationError("migration manifest must be an object")
        manifest = _manifest_from_dict(raw)
        if manifest.protocol_version != MIGRATION_PROTOCOL_VERSION:
            raise MigrationError("migration manifest protocol is incompatible")
        return manifest

    def _inventory(
        self,
        migration_id: str,
        *,
        snapshot_group: str = "snapshots",
    ) -> MigrationManifest:
        directory = self._directory(migration_id)
        source_fingerprints: list[SourceFingerprint] = []
        rows: list[LegacyRow] = []
        for index, source in enumerate(self.sources):
            fingerprint, source_rows = _snapshot_source(
                source,
                directory / snapshot_group / f"source-{index}.db",
            )
            source_fingerprints.append(fingerprint)
            rows.extend(source_rows)
        partitions, quarantine = _partition(rows)
        timestamp = now_utc_iso()
        # Physical main/WAL/SHM fingerprints are retained as evidence, but the
        # verification identity is the committed logical SQLite snapshot.  A
        # checkpoint or page-layout rewrite is not a data change.
        source_digest = _digest(
            tuple(
                (
                    item.path,
                    item.schema_version,
                    item.tables,
                    item.table_columns,
                    item.row_count,
                    item.logical_sha256,
                )
                for item in source_fingerprints
            )
        )
        return MigrationManifest(
            migration_id=migration_id,
            protocol_version=MIGRATION_PROTOCOL_VERSION,
            phase=MigrationPhase.INVENTORIED,
            sources=tuple(source_fingerprints),
            partitions=partitions,
            quarantine=quarantine,
            source_digest=source_digest,
            total_rows=len(rows),
            started_at=timestamp,
            updated_at=timestamp,
        )

    def preview(self, migration_id: str) -> MigrationManifest:
        """Persist an immutable-source inventory without copying or cutting over."""
        existing = self._load(migration_id)
        if existing is not None:
            configured = tuple(str(path) for path in self.sources)
            recorded = tuple(source.path for source in existing.sources)
            if configured != recorded:
                raise MigrationError("configured legacy sources differ from the persisted inventory")
            return existing
        self._save(self._inventory(migration_id))
        persisted = self._load(migration_id)
        assert persisted is not None
        return persisted

    def status(self, migration_id: str) -> MigrationManifest:
        """Return durable status without opening a source or project store."""
        manifest = self._load(migration_id)
        if manifest is None:
            raise MigrationError(f"migration {migration_id!r} has not been previewed")
        return manifest

    def quarantine(self, migration_id: str) -> tuple[QuarantineRecord, ...]:
        """Return named local quarantine records; no sender consumes this API."""
        return self.status(migration_id).quarantine

    def diagnose_residue(
        self,
        migration_id: str,
    ) -> tuple[QuarantineRecord, ...]:
        """Record post-cutover legacy changes without copying or delivering them."""
        manifest = self.status(migration_id)
        if _PHASE_ORDER[manifest.phase] < _PHASE_ORDER[MigrationPhase.CUTOVER]:
            raise MigrationError("legacy residue diagnosis requires completed cutover")
        current = self._inventory(migration_id, snapshot_group="residue")
        baseline_rows = {
            (row.source_path, row.table, row.row_id): (
                row.logical_sha256,
                row.values,
            )
            for rows in manifest.partitions.values()
            for row in rows
        }
        baseline_rows.update(
            {
                (row.source_path, row.table, row.row_id): (
                    row.logical_sha256,
                    row.evidence,
                )
                for row in manifest.quarantine
            }
        )
        current_rows = {
            (row.source_path, row.table, row.row_id): (
                row.logical_sha256,
                row.values,
            )
            for rows in current.partitions.values()
            for row in rows
        }
        current_rows.update(
            {
                (row.source_path, row.table, row.row_id): (
                    row.logical_sha256,
                    row.evidence,
                )
                for row in current.quarantine
            }
        )
        residue: list[QuarantineRecord] = []
        for key in sorted(set(baseline_rows) | set(current_rows)):
            before = baseline_rows.get(key)
            after = current_rows.get(key)
            if before is not None and after is not None and before[0] == after[0]:
                continue
            source_path, table, row_id = key
            change = "added" if before is None else "removed" if after is None else "changed"
            selected = after or before
            assert selected is not None
            evidence = dict(selected[1])
            evidence["residue_change"] = change
            residue.append(
                QuarantineRecord(
                    source_path=source_path,
                    table=table,
                    row_id=row_id,
                    reason=QuarantineReason.POST_CUTOVER_RESIDUE,
                    logical_sha256=selected[0],
                    evidence=evidence,
                )
            )
        updated = replace(
            manifest,
            residue=tuple(residue),
            observed_source_digest=current.source_digest,
            updated_at=now_utc_iso(),
        )
        self._save(updated)
        persisted = self._load(migration_id)
        assert persisted is not None
        return persisted.residue

    def _advance(
        self,
        manifest: MigrationManifest,
        phase: MigrationPhase,
        *,
        hooks: MigrationTestHooks | None,
        daemon_quiesce: Mapping[str, object] | None | _Unset = _UNSET,
        daemon_restart: Mapping[str, object] | None | _Unset = _UNSET,
        completed_at: str | None | _Unset = _UNSET,
    ) -> MigrationManifest:
        updated = replace(
            manifest,
            phase=phase,
            updated_at=now_utc_iso(),
        )
        if not isinstance(daemon_quiesce, _Unset):
            updated = replace(updated, daemon_quiesce=daemon_quiesce)
        if not isinstance(daemon_restart, _Unset):
            updated = replace(updated, daemon_restart=daemon_restart)
        if not isinstance(completed_at, _Unset):
            updated = replace(updated, completed_at=completed_at)
        self._save(updated)
        if hooks is not None and hooks.after_phase is not None:
            hooks.after_phase(phase)
        return updated

    def _current_source_digest(self, migration_id: str) -> str:
        current = self._inventory(migration_id, snapshot_group="verification")
        return current.source_digest

    def _hydrate_quiesced_rows(
        self,
        manifest: MigrationManifest,
    ) -> MigrationManifest:
        rows: list[LegacyRow] = []
        for index, fingerprint in enumerate(manifest.sources):
            snapshot = self._directory(manifest.migration_id) / "quiesced" / f"source-{index}.db"
            if not snapshot.is_file():
                raise MigrationError(f"quiesced migration snapshot is absent: {snapshot}")
            tables, columns, source_rows, logical_sha = _read_logical_snapshot(
                snapshot,
                Path(fingerprint.path),
            )
            if (
                tables != fingerprint.tables
                or columns != fingerprint.table_columns
                or len(source_rows) != fingerprint.row_count
                or logical_sha != fingerprint.logical_sha256
            ):
                raise MigrationError("quiesced migration snapshot no longer matches its manifest")
            rows.extend(source_rows)
        partitions, quarantine = _partition(rows)
        return replace(
            manifest,
            partitions=partitions,
            quarantine=quarantine,
        )

    def _mark_failed(
        self,
        manifest: MigrationManifest,
        exc: BaseException,
        *,
        source_digest: str | None = None,
    ) -> MigrationManifest:
        failed = replace(
            manifest,
            phase=MigrationPhase.FAILED,
            observed_source_digest=source_digest,
            updated_at=now_utc_iso(),
            failure=_safe_failure(exc),
        )
        return self._save(failed)

    def _quiesce_and_refresh(
        self,
        manifest: MigrationManifest,
        *,
        hooks: MigrationTestHooks | None,
    ) -> MigrationManifest:
        """Close the recognized writer barrier, then capture the winning snapshot."""
        acknowledgement: Mapping[str, object] | None = None
        if self.daemon_protocol is not None:
            acknowledgement = _json_value(asdict(self.daemon_protocol.quiesce(manifest.migration_id)))
        current = self._inventory(
            manifest.migration_id,
            snapshot_group="quiesced",
        )
        refreshed = replace(
            manifest,
            phase=MigrationPhase.QUIESCED,
            sources=current.sources,
            partitions=current.partitions,
            quarantine=current.quarantine,
            source_digest=current.source_digest,
            total_rows=current.total_rows,
            updated_at=now_utc_iso(),
            daemon_quiesce=acknowledgement,
        )
        self._save(refreshed)
        if hooks is not None and hooks.after_phase is not None:
            hooks.after_phase(MigrationPhase.QUIESCED)
        return refreshed

    def migrate(  # noqa: C901 -- explicit monotonic durable phase state machine
        self,
        migration_id: str,
        *,
        hooks: MigrationTestHooks | None = None,
    ) -> MigrationManifest:
        """Resume copy, exact verification, exclusive cutover, and restart."""
        existing = self._load(migration_id)
        manifest = self.preview(migration_id)
        if existing is None and hooks is not None and hooks.after_phase is not None:
            hooks.after_phase(MigrationPhase.INVENTORIED)
        if manifest.phase is MigrationPhase.COMPLETE:
            return manifest
        if manifest.phase is MigrationPhase.FAILED:
            raise MigrationError(f"migration is failed; start a new migration identity: {manifest.failure}")
        if manifest.partitions:
            first_project = next(iter(manifest.partitions))
            first_store = ProjectSyncStore(first_project)
            state = first_store.layout_generation().read_state()
            if state.mode is LayoutMode.PROJECT_ONLY:
                with first_store.unit_of_work() as unit:
                    owned = unit.execute(
                        "SELECT protocol_version FROM migration_manifests WHERE project_uuid = ? AND migration_id = ?",
                        (first_project, manifest.migration_id),
                    ).fetchone()
                resumable = _PHASE_ORDER[manifest.phase] >= _PHASE_ORDER[MigrationPhase.VERIFIED] and owned == (MIGRATION_PROTOCOL_VERSION,)
                if not resumable:
                    raise MigrationError("project-only layout forbids a new legacy copy; use residue diagnosis")
        try:
            if _PHASE_ORDER[manifest.phase] < _PHASE_ORDER[MigrationPhase.QUIESCED]:
                manifest = self._quiesce_and_refresh(manifest, hooks=hooks)
            elif _PHASE_ORDER[manifest.phase] < _PHASE_ORDER[MigrationPhase.CUTOVER]:
                manifest = self._hydrate_quiesced_rows(manifest)
            if _PHASE_ORDER[manifest.phase] < _PHASE_ORDER[MigrationPhase.COPIED]:
                current_digest = self._current_source_digest(migration_id)
                if current_digest != manifest.source_digest:
                    raise SourceChangedError("legacy source changed after quiescence; verification refused")
                self._copy_partitions(manifest)
                manifest = self._advance(
                    manifest,
                    MigrationPhase.COPIED,
                    hooks=hooks,
                )
            if _PHASE_ORDER[manifest.phase] < _PHASE_ORDER[MigrationPhase.VERIFIED]:
                self._verify_partitions(manifest)
                manifest = self._advance(
                    manifest,
                    MigrationPhase.VERIFIED,
                    hooks=hooks,
                )
            if _PHASE_ORDER[manifest.phase] < _PHASE_ORDER[MigrationPhase.CUTOVER]:
                manifest = self._cutover(manifest, hooks=hooks)
                manifest = self._advance(
                    manifest,
                    MigrationPhase.CUTOVER,
                    hooks=hooks,
                )
            if _PHASE_ORDER[manifest.phase] < _PHASE_ORDER[MigrationPhase.RESTARTED]:
                restart: Mapping[str, object] | None = None
                if self.daemon_protocol is not None:
                    restart = _json_value(asdict(self.daemon_protocol.restart(migration_id)))
                manifest = self._advance(
                    manifest,
                    MigrationPhase.RESTARTED,
                    hooks=hooks,
                    daemon_restart=restart,
                )
            if _PHASE_ORDER[manifest.phase] < _PHASE_ORDER[MigrationPhase.COMPLETE]:
                manifest = self._advance(
                    manifest,
                    MigrationPhase.COMPLETE,
                    hooks=hooks,
                    completed_at=now_utc_iso(),
                )
            persisted = self._load(migration_id)
            assert persisted is not None
            return persisted
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            observed_digest: str | None = None
            try:
                observed_digest = self._current_source_digest(migration_id)
            except MigrationError:
                observed_digest = _digest(
                    tuple(
                        (
                            str(path),
                            _file_fingerprint(path, logical=True).sha256,
                            _file_fingerprint(Path(f"{path}-wal"), logical=True).sha256,
                        )
                        for path in self.sources
                    )
                )
            self._mark_failed(manifest, exc, source_digest=observed_digest)
            raise

    def _copy_partitions(self, manifest: MigrationManifest) -> None:
        for project, rows in manifest.partitions.items():
            store = ProjectSyncStore(project)
            with store.unit_of_work() as unit:
                _copy_project_rows(unit, manifest, rows)

    def _verify_partitions(self, manifest: MigrationManifest) -> None:
        for project, rows in manifest.partitions.items():
            store = ProjectSyncStore(project)
            with store.unit_of_work() as unit:
                _verify_project_rows(unit, manifest, rows)

    def _cutover(
        self,
        manifest: MigrationManifest,
        *,
        hooks: MigrationTestHooks | None,
    ) -> MigrationManifest:
        if not manifest.partitions:
            raise MigrationError("no attributable project rows authorize cutover")
        first_project = next(iter(manifest.partitions))
        authority = ProjectSyncStore(first_project).layout_generation()
        state = authority.read_state()
        if state.mode is LayoutMode.PROJECT_ONLY:
            return manifest
        authority.begin_cutover(manifest.migration_id)

        winning = manifest

        def copy_verify_winning_snapshot() -> bool:
            nonlocal winning
            current = self._inventory(
                manifest.migration_id,
                snapshot_group="winning",
            )
            winning = replace(
                manifest,
                sources=current.sources,
                partitions=current.partitions,
                quarantine=current.quarantine,
                source_digest=current.source_digest,
                total_rows=current.total_rows,
                updated_at=now_utc_iso(),
            )
            self._copy_partitions(winning)
            self._verify_partitions(winning)
            self._save(winning)
            if hooks is not None and hooks.before_project_only_publish is not None:
                hooks.before_project_only_publish()
            return True

        authority.publish_project_only(
            manifest.migration_id,
            verify_exact=copy_verify_winning_snapshot,
        )
        return winning


def _safe_failure(exc: BaseException) -> str:
    """Persist an actionable class/digest without persisting raw row values."""
    if isinstance(exc, SourceChangedError):
        return "source_changed: legacy source evidence changed during migration"
    detail = hashlib.sha256(str(exc).encode("utf-8", errors="replace")).hexdigest()  # noqa: TID251 -- redacted diagnostic correlation
    return f"{type(exc).__name__}: migration failed; diagnostic_sha256={detail}"


def _row_payload(row: LegacyRow) -> str:
    value = row.values.get("payload")
    if value is None:
        value = row.values.get("data")
    if value is None:
        value = row.values.get("payload_json")
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeError:
            return _stable_json({"legacy_bytes": value})
    return str(value if value is not None else _stable_json(row.values))


def _unique_destination_rows(rows: Sequence[LegacyRow]) -> tuple[LegacyRow, ...]:
    unique: dict[tuple[str, str], LegacyRow] = {}
    for row in rows:
        unique.setdefault((row.table, row.row_id), row)
    return tuple(unique.values())


def _copy_project_rows(  # noqa: C901 -- closed table-family migration dispatcher
    unit: ProjectUnitOfWork,
    manifest: MigrationManifest,
    rows: Sequence[LegacyRow],
) -> None:
    project = unit.project_uuid.storage_token
    destination_rows = _unique_destination_rows(rows)
    payload_rows = [row for row in destination_rows if row.table in _EVENT_TABLES | _BODY_TABLES]
    attempt_rows = [row for row in destination_rows if row.table in _ATTEMPT_TABLES]
    source_epochs = {int(cast("int", row.values["epoch_id"])): int(cast("int", row.values["consent_generation"])) for row in attempt_rows}
    for source_epoch, consent_generation in sorted(source_epochs.items()):
        existing = unit.execute(
            "SELECT project_uuid, consent_generation FROM consent_epochs WHERE epoch_id = ?",
            (source_epoch,),
        ).fetchone()
        if existing is not None and existing != (project, consent_generation):
            raise MigrationError(f"delivery attempt epoch collision for project={project} epoch={source_epoch}")
        unit.execute(
            "INSERT OR IGNORE INTO consent_epochs "
            "(epoch_id, project_uuid, opened_at_tail, state, consent_generation, sealed_at_tail, sealed_at, reason) "
            "VALUES (?, ?, 0, 'sealed', ?, 0, ?, ?)",
            (
                source_epoch,
                project,
                consent_generation,
                now_utc_iso(),
                f"legacy_migration:{manifest.migration_id}:source_epoch:{source_epoch}",
            ),
        )
    epoch_reason = f"legacy_migration:{manifest.migration_id}"
    epoch_id: int | None = None
    existing_epoch = unit.execute(
        "SELECT epoch_id, opened_at_tail FROM consent_epochs WHERE project_uuid = ? AND reason = ?",
        (project, epoch_reason),
    ).fetchone()
    if existing_epoch is not None:
        epoch_id = int(cast("int | str", existing_epoch[0]))
        sequence = int(cast("int | str", existing_epoch[1]))
    elif payload_rows or any(row.table in _ATTEMPT_TABLES | _RESULT_TABLES for row in destination_rows):
        maximum = unit.execute("SELECT COALESCE(MAX(epoch_id), 0) FROM consent_epochs").fetchone()
        epoch_id = int(cast("int | str", maximum[0] if maximum else 0)) + 1
        tail = unit.execute(
            "SELECT next_sequence FROM capture_sequences WHERE project_uuid = ?",
            (project,),
        ).fetchone()
        sequence = int(cast("int | str", tail[0])) if tail is not None else 0
        unit.execute(
            "INSERT INTO consent_epochs (epoch_id, project_uuid, opened_at_tail, state, consent_generation, sealed_at_tail, sealed_at, reason) "
            "VALUES (?, ?, ?, 'sealed', NULL, ?, ?, ?)",
            (
                epoch_id,
                project,
                sequence,
                sequence + len(payload_rows),
                now_utc_iso(),
                epoch_reason,
            ),
        )
    else:
        sequence = 0
    for row in destination_rows:
        if row.table in _EVENT_TABLES:
            sequence += 1
            if epoch_id is None:
                raise MigrationError("legacy event requires a sealed migration epoch")
            unit.execute(
                "INSERT OR IGNORE INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row.row_id,
                    project,
                    epoch_id,
                    sequence,
                    _row_payload(row),
                    str(row.values.get("created_at") or row.values.get("timestamp") or ""),
                ),
            )
        elif row.table in _BODY_TABLES:
            sequence += 1
            if epoch_id is None:
                raise MigrationError("legacy body requires a sealed migration epoch")
            # ``row_id`` is the inventory's canonical source identity (explicit
            # body_task_id, historical integer id, or the final closed
            # fallback).  Reusing it is what lets verification prove identity
            # preservation instead of inventing a second identity during copy.
            task_id = row.row_id
            unit.execute(
                "INSERT OR IGNORE INTO body_upload_tasks "
                "(body_task_id, project_uuid, epoch_id, capture_sequence, "
                "content_hash, body_reference, state, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    project,
                    epoch_id,
                    sequence,
                    str(row.values.get("content_hash") or row.logical_sha256),
                    _stable_json(row.values),
                    str(row.values.get("state") or "pending"),
                    str(row.values.get("created_at") or ""),
                ),
            )
        elif row.table in _ATTEMPT_TABLES:
            if not _valid_delivery_attempt(row.values):
                raise MigrationError("quarantined delivery attempt reached copy")
            unit.execute(
                "INSERT OR IGNORE INTO delivery_attempts "
                "(attempt_id, project_uuid, epoch_id, outbox_task_id, consent_generation, "
                "target_generation, admission_generation, binding_audience, payload_hash, "
                "payload_reference, state, deadline_at, reconciliation_policy, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row.row_id,
                    project,
                    cast("int", row.values["epoch_id"]),
                    row.values["outbox_task_id"],
                    cast("int", row.values["consent_generation"]),
                    cast("int", row.values["target_generation"]),
                    cast("str", row.values["admission_generation"]),
                    cast("str", row.values["binding_audience"]),
                    cast("str", row.values["payload_hash"]),
                    cast("str", row.values["payload_reference"]),
                    cast("str", row.values["state"]),
                    cast("str", row.values["deadline_at"]),
                    cast("str", row.values["reconciliation_policy"]),
                    cast("str", row.values["created_at"]),
                ),
            )
        elif row.table in _RESULT_TABLES:
            if not _valid_delivery_result(row.values):
                raise MigrationError("quarantined delivery result reached copy")
            attempt_id = str(row.values.get("attempt_id") or "")
            related_attempt = next(
                (item for item in attempt_rows if item.row_id == attempt_id),
                None,
            )
            if related_attempt is None:
                raise MigrationError("legacy delivery result requires its exact attempt")
            unit.execute(
                "INSERT OR IGNORE INTO delivery_results "
                "(result_id, project_uuid, epoch_id, attempt_id, "
                "target_generation, admission_generation, outcome, terminal_refusal_category, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row.row_id,
                    project,
                    cast("int", row.values["epoch_id"]),
                    attempt_id,
                    cast("int", row.values["target_generation"]),
                    cast("str", row.values["admission_generation"]),
                    cast("str", row.values["outcome"]),
                    row.values["terminal_refusal_category"],
                    cast("str", row.values["recorded_at"]),
                ),
            )
        elif row.table in _CONSENT_TABLES:
            refused = bool(row.values.get("refused")) or str(row.values.get("state") or "").lower() in {"refused", "denied", "false"}
            if refused:
                unit.execute(
                    "INSERT INTO project_consent_decisions (project_uuid, state, generation, action, actor, decided_at, decision_schema_version) "
                    "VALUES (?, 'refused', 1, 'migrated_refusal', 'project-store-migration', ?, 1) "
                    "ON CONFLICT(project_uuid) DO NOTHING",
                    (project, now_utc_iso()),
                )
    if sequence:
        unit.execute(
            "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, ?) "
            "ON CONFLICT(project_uuid) DO UPDATE SET next_sequence = MAX(next_sequence, excluded.next_sequence)",
            (project, sequence),
        )
    unit.execute(
        "INSERT INTO migration_manifests "
        "(migration_id, project_uuid, protocol_version, source_paths, "
        "source_fingerprints_json, partition_json, quarantine_json, phase, "
        "cutover_version, started_at, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'copied', NULL, ?, NULL) "
        "ON CONFLICT(migration_id) DO UPDATE SET "
        "source_fingerprints_json = excluded.source_fingerprints_json, "
        "partition_json = excluded.partition_json, "
        "quarantine_json = excluded.quarantine_json, phase = 'copied'",
        (
            manifest.migration_id,
            project,
            manifest.protocol_version,
            _stable_json(tuple(source.path for source in manifest.sources)),
            _stable_json(manifest.sources),
            _stable_json(tuple(row.logical_sha256 for row in rows)),
            _stable_json(manifest.quarantine),
            manifest.started_at,
        ),
    )


def _verify_project_rows(
    unit: ProjectUnitOfWork,
    manifest: MigrationManifest,
    rows: Sequence[LegacyRow],
) -> None:
    project = unit.project_uuid.storage_token
    expected_rows: dict[str, tuple[tuple[object, ...], ...]] = {
        "journal_entries": tuple(
            sorted(
                {
                    (
                        row.row_id,
                        _row_payload(row),
                        str(row.values.get("created_at") or row.values.get("timestamp") or ""),
                    )
                    for row in rows
                    if row.table in _EVENT_TABLES
                }
            )
        ),
        "body_upload_tasks": tuple(
            sorted(
                {
                    (
                        row.row_id,
                        str(row.values.get("content_hash") or row.logical_sha256),
                        _stable_json(row.values),
                        str(row.values.get("state") or "pending"),
                        str(row.values.get("created_at") or ""),
                    )
                    for row in rows
                    if row.table in _BODY_TABLES
                }
            )
        ),
        "delivery_attempts": tuple(
            sorted(
                {
                    (
                        row.row_id,
                        cast("int", row.values["epoch_id"]),
                        row.values["outbox_task_id"],
                        cast("int", row.values["consent_generation"]),
                        cast("int", row.values["target_generation"]),
                        cast("str", row.values["admission_generation"]),
                        cast("str", row.values["binding_audience"]),
                        cast("str", row.values["payload_hash"]),
                        cast("str", row.values["payload_reference"]),
                        cast("str", row.values["state"]),
                        cast("str", row.values["deadline_at"]),
                        cast("str", row.values["reconciliation_policy"]),
                        cast("str", row.values["created_at"]),
                    )
                    for row in rows
                    if row.table in _ATTEMPT_TABLES
                }
            )
        ),
        "delivery_results": tuple(
            sorted(
                {
                    (
                        row.row_id,
                        cast("int", row.values["epoch_id"]),
                        cast("str", row.values["attempt_id"]),
                        cast("int", row.values["target_generation"]),
                        cast("str", row.values["admission_generation"]),
                        cast("str", row.values["outcome"]),
                        row.values["terminal_refusal_category"],
                        cast("str", row.values["recorded_at"]),
                    )
                    for row in rows
                    if row.table in _RESULT_TABLES
                }
            )
        ),
    }
    projections = {
        "journal_entries": ("entry_id", "entry_id, payload_json, created_at"),
        "body_upload_tasks": (
            "body_task_id",
            "body_task_id, content_hash, body_reference, state, created_at",
        ),
        "delivery_attempts": (
            "attempt_id",
            "attempt_id, epoch_id, outbox_task_id, consent_generation, target_generation, "
            "admission_generation, binding_audience, payload_hash, payload_reference, state, "
            "deadline_at, reconciliation_policy, created_at",
        ),
        "delivery_results": (
            "result_id",
            "result_id, epoch_id, attempt_id, target_generation, admission_generation, outcome, terminal_refusal_category, recorded_at",
        ),
    }
    for table, expected in expected_rows.items():
        if not expected:
            continue
        identity, projection = projections[table]
        identifiers = tuple(str(row[0]) for row in expected)
        placeholders = ", ".join("?" for _ in identifiers)
        actual = tuple(
            tuple(value for value in result)
            for result in unit.execute(
                f"SELECT {projection} FROM {table} WHERE project_uuid = ? AND {identity} IN ({placeholders}) ORDER BY {identity}",  # noqa: S608 -- closed identifiers and bound-value placeholders
                (project, *identifiers),
            ).fetchall()
        )
        if actual != expected:
            actual_hash = _digest(actual)
            expected_hash = _digest(expected)
            raise MigrationError(
                "exact destination verification failed "
                f"for project={project} table={table} key={identity} "
                f"columns={projection} actual_sha256={actual_hash} expected_sha256={expected_hash}"
            )
    manifest_row = unit.execute(
        "SELECT protocol_version, phase FROM migration_manifests WHERE project_uuid = ? AND migration_id = ?",
        (project, manifest.migration_id),
    ).fetchone()
    if manifest_row != (MIGRATION_PROTOCOL_VERSION, "copied"):
        raise MigrationError("project migration manifest is absent or incompatible")


__all__ = [
    "LegacyProjectStoreMigration",
    "LegacyRow",
    "MIGRATION_PROTOCOL_VERSION",
    "MigrationError",
    "MigrationManifest",
    "MigrationPhase",
    "MigrationTestHooks",
    "migration_artifact_path",
    "QuarantineReason",
    "QuarantineRecord",
    "SidecarFingerprint",
    "SourceChangedError",
    "SourceFingerprint",
]

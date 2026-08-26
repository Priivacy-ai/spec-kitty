"""One verified SQLite aggregate and outer transaction per project UUID."""

from __future__ import annotations

import re
import sqlite3
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from kernel.clock import now_utc_iso
from pathlib import Path
from typing import Final, TypeAlias, cast
from uuid import UUID

from specify_cli.sync.layout_generation import (
    LayoutGenerationAuthority,
    _new_layout_generation_authority,
)
from specify_cli.sync.project_context import (
    AdmissionState,
    ConsentState,
    ProjectSyncContext,
    TargetAudience,
    VerifiedProjectStoreIdentity,
    _new_project_sync_context,
    _new_verified_project_store_identity,
)
from specify_cli.sync.project_identity import (
    CanonicalProjectUUID,
    ProjectStorePaths,
)


class ProjectStoreError(RuntimeError):
    """Base class for fail-closed project sync-store errors."""


class ProjectStoreOwnerMismatchError(ProjectStoreError):
    """The persisted store owner differs from the requested canonical UUID."""


class ProjectStoreVersionError(ProjectStoreError):
    """The store schema or layout version is incompatible with this runtime."""


class ProjectStoreCorruptError(ProjectStoreError):
    """An existing store cannot be verified as a complete project store."""


class ProjectStoreLockedError(ProjectStoreError):
    """The store's outer write transaction could not be acquired."""


class ProjectTransactionControlError(ProjectStoreError):
    """Business SQL attempted to escape the store-owned transaction boundary."""


SQLiteScalar: TypeAlias = str | int | float | bytes | None
SQLiteParameters: TypeAlias = Sequence[SQLiteScalar] | Mapping[str, SQLiteScalar]
SQLiteRow: TypeAlias = tuple[SQLiteScalar, ...] | sqlite3.Row

_SAVEPOINT_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*", flags=re.ASCII)
_LEADING_SQL_TRIVIA = re.compile(
    r"(?:\s+|\ufeff|;+|--[^\r\n]*(?:\r?\n|$)|/\*.*?\*/)*",
    flags=re.ASCII | re.DOTALL,
)
_SQL_KEYWORD = re.compile(r"[A-Za-z]+", flags=re.ASCII)
# ATTACH/DETACH are rejected alongside transaction control: `ATTACH DATABASE
# '<other-project>/sync.db'` through a live unit would open another project's
# store on this connection without a new sqlite3.connect call — invisible to
# the SC-011 connection instrumentation and an in-process escape from the
# FR-002 physical-isolation boundary.
_TRANSACTION_CONTROL_KEYWORDS: Final[frozenset[str]] = frozenset({"BEGIN", "COMMIT", "END", "RELEASE", "ROLLBACK", "SAVEPOINT", "ATTACH", "DETACH"})
# Default outer-transaction lock wait, mirrored into `PRAGMA busy_timeout` (ms)
# below so concurrent writers block-and-retry instead of racing `BEGIN
# IMMEDIATE`/reads against a committing writer (see unit_of_work).
_DEFAULT_LOCK_TIMEOUT_SECONDS: Final[float] = 5.0


class ProjectQueryResult:
    """Opaque fetch-only result that does not expose its SQLite cursor or connection."""

    __slots__ = ("__cursor",)

    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self.__cursor = cursor

    def fetchone(self) -> SQLiteRow | None:
        """Fetch the next row without exposing cursor transaction controls."""
        return cast("SQLiteRow | None", self.__cursor.fetchone())

    def fetchmany(self, size: int | None = None) -> list[SQLiteRow]:
        """Fetch a bounded row batch without exposing cursor transaction controls."""
        if size is None:
            return cast("list[SQLiteRow]", self.__cursor.fetchmany())
        return cast("list[SQLiteRow]", self.__cursor.fetchmany(size))

    def fetchall(self) -> list[SQLiteRow]:
        """Fetch all remaining rows without exposing cursor transaction controls."""
        return cast("list[SQLiteRow]", self.__cursor.fetchall())

    def __iter__(self) -> Iterator[SQLiteRow]:
        return (cast("SQLiteRow", row) for row in self.__cursor)


def _reject_transaction_control(statement: str) -> None:
    trivia = _LEADING_SQL_TRIVIA.match(statement)
    remainder = statement[trivia.end() :] if trivia is not None else statement
    keyword_match = _SQL_KEYWORD.match(remainder)
    keyword = keyword_match.group(0).upper() if keyword_match is not None else ""
    if keyword in _TRANSACTION_CONTROL_KEYWORDS:
        raise ProjectTransactionControlError(f"SQL transaction control {keyword} is owned by ProjectSyncStore")


def _ensure_wal_journal_mode(connection: sqlite3.Connection, deadline_seconds: float) -> None:
    """Idempotently put ``connection`` into WAL mode, tolerating the switch race.

    Switching *into* WAL briefly needs an exclusive schema lock that is a
    distinct SQLite lock class from the ordinary write lock ``PRAGMA
    busy_timeout`` governs -- concurrent first-time initializers of a brand
    new store can each raise ``OperationalError: database is locked`` on this
    specific pragma even with busy_timeout already set, because that lock
    class is not retried by the driver's busy handler. Once any connection
    has completed the switch this is a fast no-op read for everyone else, so
    only the initial race needs the bounded self-retry below.
    """
    deadline = time.monotonic() + deadline_seconds
    while True:
        try:
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            if str(mode).lower() == "wal":
                return
            connection.execute("PRAGMA journal_mode = WAL")
            return
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or time.monotonic() >= deadline:
                raise
            time.sleep(0.005)


def _database_has_foreign_content(connection: sqlite3.Connection) -> bool:
    """True if the file holds pages beyond the empty-database baseline.

    Must only be called while the caller already holds ``BEGIN IMMEDIATE``,
    so it is a lock-consistent read. A brand-new store created by
    ``sqlite3.connect`` (and switched to WAL) reports ``page_count <= 1``
    -- just the WAL header page -- before any schema is written, regardless
    of whether a *sibling* connection's own ``connect()`` call raced to
    create the same on-disk stub moments earlier. That makes this immune to
    the ``Path.exists()`` TOCTOU it replaces: under concurrent first-time
    bootstrap, every racing thread's pre-lock existence check could observe
    a sibling's already-created (but still schema-empty) file and wrongly
    treat it as a pre-existing corrupt store, even though nobody had
    written anything yet (see unit_of_work).
    """
    page_count = connection.execute("PRAGMA page_count").fetchone()[0]
    return bool(page_count > 1)


def _stored_positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ProjectStoreCorruptError(f"persisted {field} must be a positive integer")
    return value


class ProjectUnitOfWork:
    """Narrow SQL port that cannot commit, roll back, close, or replace its store."""

    _active: bool
    _connection_identity: int
    _execute: Callable[..., sqlite3.Cursor]
    _executemany: Callable[..., sqlite3.Cursor]
    _store_identity: VerifiedProjectStoreIdentity
    project_uuid: CanonicalProjectUUID

    __slots__ = (
        "_active",
        "_connection_identity",
        "_execute",
        "_executemany",
        "_store_identity",
        "project_uuid",
    )

    def __init__(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        raise TypeError("project units of work are created by ProjectSyncStore")

    @property
    def connection_identity(self) -> int:
        """Opaque identity used to prove nested work reuses one connection."""
        return self._connection_identity

    @property
    def store_identity(self) -> VerifiedProjectStoreIdentity:
        """Opaque store capability minted by the verified opening transaction."""
        return self._store_identity

    def _require_active(self) -> None:
        if not self._active:
            raise ProjectStoreError("project unit of work is no longer active")

    def execute(
        self,
        statement: str,
        parameters: SQLiteParameters = (),
    ) -> ProjectQueryResult:
        """Execute SQL inside the store-owned outer transaction."""
        self._require_active()
        _reject_transaction_control(statement)
        return ProjectQueryResult(self._execute(statement, parameters))

    def executemany(
        self,
        statement: str,
        parameters: Iterable[SQLiteParameters],
    ) -> ProjectQueryResult:
        """Execute a parameterized SQL batch inside the outer transaction."""
        self._require_active()
        _reject_transaction_control(statement)
        return ProjectQueryResult(self._executemany(statement, parameters))

    @contextmanager
    def savepoint(self, name: str) -> Iterator[None]:
        """Open an intentional, ASCII-named nested rollback boundary."""
        self._require_active()
        if _SAVEPOINT_NAME.fullmatch(name) is None:
            raise ValueError("savepoint name must be an ASCII SQL identifier")
        self._execute(f'SAVEPOINT "{name}"')
        try:
            yield
        except BaseException:
            self._execute(f'ROLLBACK TO SAVEPOINT "{name}"')
            self._execute(f'RELEASE SAVEPOINT "{name}"')
            raise
        else:
            self._execute(f'RELEASE SAVEPOINT "{name}"')

    def _deactivate(self) -> None:
        self._active = False


def _new_project_unit_of_work(
    connection: sqlite3.Connection,
    project_uuid: CanonicalProjectUUID,
    store_identity: VerifiedProjectStoreIdentity,
) -> ProjectUnitOfWork:
    """Create the SQL port only after ProjectSyncStore verifies the open store."""
    unit = object.__new__(ProjectUnitOfWork)
    unit.project_uuid = project_uuid
    unit._store_identity = store_identity
    unit._connection_identity = id(connection)
    unit._execute = connection.execute
    unit._executemany = connection.executemany
    unit._active = True
    return unit


_SCHEMA_STATEMENTS: Final[tuple[str, ...]] = (
    """
    CREATE TABLE project_store_metadata (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        project_uuid TEXT NOT NULL UNIQUE,
        schema_version INTEGER NOT NULL CHECK (schema_version > 0),
        layout_version INTEGER NOT NULL CHECK (layout_version > 0),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE project_consent_decisions (
        project_uuid TEXT PRIMARY KEY,
        state TEXT NOT NULL CHECK (state IN ('granted', 'refused')),
        generation INTEGER NOT NULL CHECK (generation > 0),
        action TEXT NOT NULL CHECK (
            action IN ('explicit_opt_in', 'explicit_opt_out', 'migrated_refusal')
        ),
        actor TEXT NOT NULL,
        decided_at TEXT NOT NULL,
        decision_schema_version INTEGER NOT NULL CHECK (decision_schema_version > 0),
        FOREIGN KEY (project_uuid) REFERENCES project_store_metadata(project_uuid)
    )
    """,
    """
    CREATE TABLE capture_sequences (
        project_uuid TEXT PRIMARY KEY,
        next_sequence INTEGER NOT NULL CHECK (next_sequence >= 0),
        FOREIGN KEY (project_uuid) REFERENCES project_store_metadata(project_uuid)
    )
    """,
    """
    CREATE TABLE consent_epochs (
        epoch_id INTEGER PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        opened_at_tail INTEGER NOT NULL CHECK (opened_at_tail >= 0),
        state TEXT NOT NULL CHECK (state IN ('capture_only', 'eligible', 'sealed')),
        consent_generation INTEGER,
        sealed_at_tail INTEGER,
        sealed_at TEXT,
        reason TEXT NOT NULL,
        UNIQUE (project_uuid, epoch_id),
        FOREIGN KEY (project_uuid) REFERENCES project_store_metadata(project_uuid),
        CHECK (consent_generation IS NULL OR consent_generation > 0),
        CHECK (sealed_at_tail IS NULL OR sealed_at_tail >= opened_at_tail)
    )
    """,
    """
    CREATE TABLE journal_entries (
        entry_id TEXT PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        epoch_id INTEGER NOT NULL,
        capture_sequence INTEGER NOT NULL CHECK (capture_sequence > 0),
        payload_json TEXT NOT NULL,
        created_at TEXT,
        UNIQUE (project_uuid, entry_id),
        UNIQUE (project_uuid, capture_sequence),
        FOREIGN KEY (project_uuid, epoch_id)
            REFERENCES consent_epochs(project_uuid, epoch_id)
    )
    """,
    """
    CREATE TABLE outbox_tasks (
        task_id TEXT PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        epoch_id INTEGER NOT NULL,
        journal_entry_id TEXT,
        task_kind TEXT NOT NULL,
        state TEXT NOT NULL,
        idempotency_identity TEXT,
        created_at TEXT,
        UNIQUE (project_uuid, task_id),
        FOREIGN KEY (project_uuid, epoch_id)
            REFERENCES consent_epochs(project_uuid, epoch_id),
        FOREIGN KEY (project_uuid, journal_entry_id)
            REFERENCES journal_entries(project_uuid, entry_id)
    )
    """,
    """
    CREATE TABLE body_upload_tasks (
        body_task_id TEXT PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        epoch_id INTEGER NOT NULL,
        capture_sequence INTEGER NOT NULL CHECK (capture_sequence > 0),
        content_hash TEXT NOT NULL,
        body_reference TEXT NOT NULL,
        state TEXT NOT NULL,
        created_at TEXT,
        UNIQUE (project_uuid, body_task_id),
        FOREIGN KEY (project_uuid, epoch_id)
            REFERENCES consent_epochs(project_uuid, epoch_id)
    )
    """,
    """
    CREATE TABLE project_target_admissions (
        project_uuid TEXT PRIMARY KEY,
        target_identity TEXT NOT NULL,
        account_identity TEXT NOT NULL,
        private_teamspace_id TEXT NOT NULL,
        configuration_generation INTEGER NOT NULL CHECK (configuration_generation > 0),
        admission_state TEXT NOT NULL CHECK (
            admission_state IN ('pending', 'admitted', 'refused', 'revocation_pending')
        ),
        admission_generation TEXT,
        binding_audience TEXT,
        last_error_category TEXT,
        FOREIGN KEY (project_uuid) REFERENCES project_store_metadata(project_uuid)
    )
    """,
    """
    CREATE TABLE admission_operations (
        operation_key TEXT PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        action TEXT NOT NULL CHECK (action IN ('admit', 'revoke')),
        expected_generation INTEGER CHECK (
            expected_generation IS NULL OR expected_generation > 0
        ),
        target_identity TEXT NOT NULL,
        account_identity TEXT NOT NULL,
        private_teamspace_id TEXT NOT NULL,
        configuration_generation INTEGER NOT NULL CHECK (configuration_generation > 0),
        request_payload_hash TEXT NOT NULL CHECK (length(request_payload_hash) = 64),
        request_payload_version INTEGER NOT NULL CHECK (request_payload_version > 0),
        state TEXT NOT NULL CHECK (
            state IN ('prepared', 'sent', 'acknowledged', 'refused', 'unknown')
        ),
        result_state TEXT,
        result_generation INTEGER CHECK (
            result_generation IS NULL OR result_generation > 0
        ),
        binding_audience TEXT,
        original_error_category TEXT,
        attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (project_uuid, operation_key),
        FOREIGN KEY (project_uuid) REFERENCES project_store_metadata(project_uuid)
    )
    """,
    """
    CREATE TABLE history_disclosure_actions (
        action_id TEXT PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        source_epoch_ids_json TEXT NOT NULL,
        row_ids_json TEXT NOT NULL,
        preview_count INTEGER NOT NULL CHECK (preview_count >= 0),
        preview_hash TEXT NOT NULL,
        confirmed_by TEXT,
        confirmed_at TEXT,
        consent_generation INTEGER NOT NULL CHECK (consent_generation > 0),
        target_generation INTEGER NOT NULL CHECK (target_generation > 0),
        admission_generation TEXT NOT NULL,
        binding_audience TEXT NOT NULL,
        state TEXT NOT NULL CHECK (
            state IN (
                'previewed', 'confirmed', 'sending', 'complete',
                'terminal_refused', 'canceled'
            )
        ),
        result_ids_json TEXT,
        UNIQUE (project_uuid, idempotency_key),
        FOREIGN KEY (project_uuid) REFERENCES project_store_metadata(project_uuid)
    )
    """,
    """
    CREATE TABLE delivery_attempts (
        attempt_id TEXT PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        epoch_id INTEGER NOT NULL,
        outbox_task_id TEXT,
        consent_generation INTEGER,
        target_generation INTEGER,
        admission_generation TEXT,
        binding_audience TEXT,
        payload_hash TEXT,
        payload_reference TEXT,
        state TEXT NOT NULL,
        deadline_at TEXT,
        reconciliation_policy TEXT,
        created_at TEXT,
        UNIQUE (project_uuid, attempt_id),
        FOREIGN KEY (project_uuid, epoch_id)
            REFERENCES consent_epochs(project_uuid, epoch_id),
        FOREIGN KEY (project_uuid, outbox_task_id)
            REFERENCES outbox_tasks(project_uuid, task_id)
    )
    """,
    """
    CREATE TABLE delivery_results (
        result_id TEXT PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        epoch_id INTEGER NOT NULL,
        attempt_id TEXT NOT NULL,
        target_generation INTEGER,
        admission_generation TEXT,
        outcome TEXT NOT NULL,
        terminal_refusal_category TEXT,
        recorded_at TEXT NOT NULL,
        UNIQUE (project_uuid, result_id),
        FOREIGN KEY (project_uuid, epoch_id)
            REFERENCES consent_epochs(project_uuid, epoch_id),
        FOREIGN KEY (project_uuid, attempt_id)
            REFERENCES delivery_attempts(project_uuid, attempt_id)
    )
    """,
    """
    CREATE TABLE migration_manifests (
        migration_id TEXT PRIMARY KEY,
        project_uuid TEXT NOT NULL,
        protocol_version INTEGER NOT NULL CHECK (protocol_version > 0),
        source_paths TEXT NOT NULL,
        source_fingerprints_json TEXT NOT NULL,
        partition_json TEXT NOT NULL,
        quarantine_json TEXT NOT NULL,
        phase TEXT NOT NULL,
        cutover_version INTEGER,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        UNIQUE (project_uuid, migration_id),
        FOREIGN KEY (project_uuid) REFERENCES project_store_metadata(project_uuid)
    )
    """,
    """
    CREATE TABLE migration_cutover_state (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        project_uuid TEXT NOT NULL UNIQUE,
        migration_id TEXT,
        phase TEXT NOT NULL,
        cutover_version INTEGER,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (project_uuid) REFERENCES project_store_metadata(project_uuid),
        FOREIGN KEY (project_uuid, migration_id)
            REFERENCES migration_manifests(project_uuid, migration_id)
    )
    """,
)


class ProjectSyncStore:
    """Canonical path, connection, transaction, and context owner for one UUID."""

    _active_unit: ContextVar[ProjectUnitOfWork | None]
    _paths: ProjectStorePaths
    schema_version: Final[int] = 1
    layout_version: Final[int] = 1
    __slots__ = ("_active_unit", "_paths")

    def __init__(self, project_uuid: CanonicalProjectUUID | UUID | str) -> None:
        self._paths = ProjectStorePaths.for_project(project_uuid)
        self._active_unit: ContextVar[ProjectUnitOfWork | None] = ContextVar(
            f"project-sync-uow-{self._paths.project_uuid.storage_token}-{id(self)}",
            default=None,
        )

    @property
    def project_uuid(self) -> CanonicalProjectUUID:
        """Canonical immutable UUID that owns this store."""
        return self._paths.project_uuid

    @property
    def database_path(self) -> Path:
        """Derived live database path; callers cannot replace it."""
        return self._paths.database

    @property
    def egress_lock_path(self) -> Path:
        """Derived sibling transport/result lock path."""
        return self._paths.egress_lock

    @property
    def migration_report_dir(self) -> Path:
        """Derived directory for non-sensitive migration evidence."""
        return self._paths.migration_reports

    @staticmethod
    def _metadata_table_exists(connection: sqlite3.Connection) -> bool:
        row = connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'project_store_metadata'").fetchone()
        return row is not None

    def _verify_owner(self, connection: sqlite3.Connection) -> None:
        row = connection.execute("SELECT project_uuid, schema_version, layout_version FROM project_store_metadata WHERE singleton = 1").fetchone()
        if row is None:
            raise ProjectStoreCorruptError("project store metadata is missing its singleton owner row")
        owner, schema_version, layout_version = row
        if owner != self.project_uuid.storage_token:
            raise ProjectStoreOwnerMismatchError(f"project store owner {owner!r} does not match {self.project_uuid.storage_token!r}")
        if schema_version != self.schema_version:
            raise ProjectStoreVersionError(f"project store schema {schema_version!r} is incompatible with {self.schema_version}")
        if layout_version != self.layout_version:
            raise ProjectStoreVersionError(f"project store layout {layout_version!r} is incompatible with {self.layout_version}")

    def verify_existing_readonly(self) -> VerifiedProjectStoreIdentity:
        """Verify an existing project store without creating files or a write txn."""
        if not self.database_path.exists():
            raise ProjectStoreError(f"project sync store does not exist: {self.database_path}")
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"file:{self.database_path.as_posix()}?mode=ro",
                uri=True,
                isolation_level=None,
            )
            # A read-only connection cannot itself flip journal_mode (that
            # requires a write lock on the DB header) — WAL is established by
            # writers in unit_of_work and this connection simply reads
            # whatever mode is on disk. busy_timeout is safe to set here and
            # keeps a concurrent-writer race from surfacing as an immediate
            # "locked"/"not initialized" misread instead of a bounded wait.
            connection.execute(f"PRAGMA busy_timeout = {int(_DEFAULT_LOCK_TIMEOUT_SECONDS * 1000)}")
            if not self._metadata_table_exists(connection):
                raise ProjectStoreCorruptError("existing sync.db is not an initialized project store")
            self._verify_owner(connection)
        except sqlite3.DatabaseError as exc:
            raise self._translate_open_error(exc) from exc
        finally:
            if connection is not None:
                connection.close()
        return _new_verified_project_store_identity(
            project_uuid=self.project_uuid,
            database_path=self.database_path,
            schema_version=self.schema_version,
            layout_version=self.layout_version,
        )

    @staticmethod
    def _translate_open_error(error: sqlite3.DatabaseError) -> ProjectStoreError:
        message = str(error).lower()
        if "locked" in message or "busy" in message:
            return ProjectStoreLockedError("project sync store is locked")
        return ProjectStoreCorruptError("project sync store could not be verified as SQLite")

    @contextmanager
    def unit_of_work(
        self,
        *,
        lock_timeout_seconds: float = _DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> Iterator[ProjectUnitOfWork]:
        """Own one live connection and outer transaction for a project action."""
        active = self._active_unit.get()
        if active is not None:
            yield active
            return
        if lock_timeout_seconds < 0:
            raise ValueError("lock timeout cannot be negative")

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection: sqlite3.Connection | None = None
        unit: ProjectUnitOfWork | None = None
        token = None
        exposed = False
        try:
            connection = sqlite3.connect(
                self.database_path,
                timeout=lock_timeout_seconds,
                isolation_level=None,
            )
            # WAL gives one writer + concurrent snapshot-isolated readers, so
            # a reader opened mid-commit can no longer observe a transiently
            # missing metadata table (the "not an initialized project store"
            # false corruption). busy_timeout makes a competing `BEGIN
            # IMMEDIATE` wait for the lock instead of raising immediately
            # (translated to ProjectStoreLockedError) under contention. Both
            # MUST be set before BEGIN IMMEDIATE — journal_mode cannot be
            # changed from inside a transaction. The WAL switch itself is
            # done through _ensure_wal_journal_mode, not a bare PRAGMA: it
            # needs a lock class busy_timeout does not cover (see there).
            #
            # NOTE (#3625): busy_timeout bounds the wait on the in-daemon
            # write-lock contention that shows up as "project sync store is
            # locked" on large stores. Narrowing the lock *window* itself
            # (the work held between BEGIN IMMEDIATE and commit, which scales
            # with body-drain size) would change body-drain transaction scope
            # and is deferred until a tens-of-MB repro can validate it does
            # not regress atomicity or WAL-checkpoint behavior. The bounded
            # wait guaranteed here is locked in by
            # tests/sync/test_project_store_transactions.py.
            connection.execute(f"PRAGMA busy_timeout = {int(lock_timeout_seconds * 1000)}")
            _ensure_wal_journal_mode(connection, lock_timeout_seconds)
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            initialized = not self._metadata_table_exists(connection)
            if initialized:
                if _database_has_foreign_content(connection):
                    raise ProjectStoreCorruptError("existing sync.db is not an initialized project store")
                for statement in _SCHEMA_STATEMENTS:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO project_store_metadata (singleton, project_uuid, schema_version, layout_version, created_at) VALUES (1, ?, ?, ?, ?)",
                    (
                        self.project_uuid.storage_token,
                        self.schema_version,
                        self.layout_version,
                        now_utc_iso(),
                    ),
                )
            self._verify_owner(connection)
            if initialized:
                # Bootstrap state is infrastructure, not part of the caller's
                # business action. Persist it once, then begin and reverify the
                # outer action transaction before exposing the SQL port.
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._verify_owner(connection)
            store_identity = _new_verified_project_store_identity(
                project_uuid=self.project_uuid,
                database_path=self.database_path,
                schema_version=self.schema_version,
                layout_version=self.layout_version,
            )
            unit = _new_project_unit_of_work(
                connection,
                self.project_uuid,
                store_identity,
            )
            token = self._active_unit.set(unit)
            exposed = True
            yield unit
            connection.commit()
        except BaseException as exc:
            if connection is not None:
                with suppress(sqlite3.DatabaseError):
                    connection.rollback()
            if isinstance(exc, sqlite3.DatabaseError) and not exposed:
                raise self._translate_open_error(exc) from exc
            raise
        finally:
            if unit is not None:
                unit._deactivate()
            if token is not None:
                self._active_unit.reset(token)
            if connection is not None:
                connection.close()

    def _verified_identity(
        self,
        unit: ProjectUnitOfWork,
    ) -> VerifiedProjectStoreIdentity:
        if self._active_unit.get() is not unit:
            raise ProjectStoreError("verified store identity requires the active store unit of work")
        return unit.store_identity

    def layout_generation(
        self,
        *,
        lock_timeout_seconds: float = 10.0,
    ) -> LayoutGenerationAuthority:
        """Return the sole current-writer placement authority for this store."""
        return _new_layout_generation_authority(
            project_uuid=self.project_uuid,
            runtime_root=self._paths.runtime_root,
            lock_timeout_seconds=lock_timeout_seconds,
        )

    def create_context(self) -> ProjectSyncContext:
        """Load a coherent immutable authority snapshot from the verified store."""
        with self.unit_of_work() as unit:
            return self.create_context_from_unit(unit)

    def create_context_from_unit(
        self,
        unit: ProjectUnitOfWork,
    ) -> ProjectSyncContext:
        """Mint the normal context from this store's supplied active unit.

        Callers that already own an aggregate transaction use this seam to keep
        context construction and subsequent local capture on one connection. A
        foreign or retained inactive unit is rejected before any authority rows
        are read.
        """
        store_identity = self._verified_identity(unit)
        consent_state: ConsentState | None = None
        consent_generation: int | None = None
        epoch_id: int | None = None
        target_audience: TargetAudience | None = None
        admission_state: AdmissionState | None = None
        admission_generation: str | None = None
        binding_audience: str | None = None

        consent_row = unit.execute(
            "SELECT state, generation FROM project_consent_decisions WHERE project_uuid = ?",
            (self.project_uuid.storage_token,),
        ).fetchone()
        if consent_row is not None:
            consent_state = ConsentState(str(consent_row[0]))
            consent_generation = _stored_positive_int(consent_row[1], "consent generation")

        if consent_state is ConsentState.GRANTED:
            epoch_row = unit.execute(
                "SELECT epoch_id FROM consent_epochs WHERE project_uuid = ? AND state = 'eligible' AND consent_generation = ? ORDER BY epoch_id DESC LIMIT 1",
                (self.project_uuid.storage_token, consent_generation),
            ).fetchone()
            if epoch_row is not None:
                epoch_id = _stored_positive_int(epoch_row[0], "epoch identity")

        admission_row = unit.execute(
            "SELECT target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, "
            "binding_audience FROM project_target_admissions "
            "WHERE project_uuid = ?",
            (self.project_uuid.storage_token,),
        ).fetchone()
        if admission_row is not None:
            target_audience = TargetAudience(
                project_uuid=self.project_uuid,
                target_identity=str(admission_row[0]),
                account_identity=str(admission_row[1]),
                private_teamspace_id=str(admission_row[2]),
                configuration_generation=_stored_positive_int(admission_row[3], "target configuration generation"),
            )
            admission_state = AdmissionState(str(admission_row[4]))
            admission_generation = str(admission_row[5]) if admission_row[5] is not None else None
            binding_audience = str(admission_row[6]) if admission_row[6] is not None else None

        return _new_project_sync_context(
            store_identity=store_identity,
            consent_state=consent_state,
            consent_generation=consent_generation,
            epoch_id=epoch_id,
            target_audience=target_audience,
            admission_state=admission_state,
            admission_generation=admission_generation,
            binding_audience=binding_audience,
            kill_switch_allows=False,
            transport_lease_identity=None,
        )


__all__ = [
    "ProjectStoreError",
    "ProjectStoreLockedError",
    "ProjectStoreVersionError",
    "ProjectSyncStore",
    "ProjectUnitOfWork",
]

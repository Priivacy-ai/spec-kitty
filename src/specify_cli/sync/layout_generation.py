"""Machine layout generation and current-writer permit authority."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import threading
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from kernel.clock import now_utc_iso
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from filelock import FileLock, Timeout

from specify_cli.sync.project_identity import CanonicalProjectUUID

#: Operator escape hatch: when set, a legacy-with-data root is NOT auto-migrated on
#: first write. Read at resolution time (never import time) so tests toggle per case.
NO_AUTO_CUTOVER_ENV = "SPEC_KITTY_NO_AUTO_CUTOVER"

#: The manual command an operator runs when the escape hatch refuses auto-cutover.
_MANUAL_MIGRATE_COMMAND = "sync project-store-migrate"

#: Bounded, deterministic retry budget for a live write that arrives while a
#: migration is in flight (``CUTOVER_PENDING``). Iterations — never wall-clock — so
#: the block-and-retry is reproducible; the ``before_revalidate`` hook is the sync
#: point a test uses to publish (or not) mid-wait.
_CUTOVER_WAIT_ATTEMPTS = 8

#: Thread-local marker set while THIS thread is driving the auto-cutover copy. A
#: migrating writer is authorized to write into the project store during
#: ``CUTOVER_PENDING``; every other (live) writer blocks-and-retries instead.
_drive_state = threading.local()


def _in_cutover_drive() -> bool:
    return bool(getattr(_drive_state, "active", False))


@contextlib.contextmanager
def _cutover_drive() -> Iterator[None]:
    """Mark the current thread as the authorized migrating writer for its duration."""
    previous = getattr(_drive_state, "active", False)
    _drive_state.active = True
    try:
        yield
    finally:
        _drive_state.active = previous


class LayoutMode(StrEnum):
    """Machine-wide current-writer placement mode."""

    LEGACY = "legacy"
    CUTOVER_PENDING = "cutover_pending"
    PROJECT_ONLY = "project_only"


class LayoutDestination(StrEnum):
    """The one destination authorized by a write permit."""

    LEGACY = "legacy"
    PROJECT_STORE = "project_store"


class LayoutAuthorityError(RuntimeError):
    """Base class for fail-closed layout authority failures."""


class LayoutAuthorityCorruptError(LayoutAuthorityError):
    """The machine layout record is malformed or internally inconsistent."""


class LayoutAuthorityLockedError(LayoutAuthorityError):
    """The machine layout lock could not be acquired in the bounded interval."""


class LayoutVerificationError(LayoutAuthorityError):
    """Exact migration verification did not authorize project-only publication."""


class StaleLayoutWritePermitError(LayoutAuthorityError):
    """A permit no longer matches the current machine layout generation."""


class LayoutAutoCutoverRefusedError(LayoutAuthorityError):
    """Auto-cutover was refused by ``SPEC_KITTY_NO_AUTO_CUTOVER`` on a legacy root."""


class LayoutCutoverIncompleteError(LayoutAuthorityError):
    """A live write arrived while cutover was in flight and could not yet publish.

    Distinguishable from a silent LEGACY swallow: the write is surfaced loudly so
    the caller (the emitter observability surface, IC-05) has something to report,
    rather than being routed to LEGACY and dropped (INV-5).
    """


@dataclass(frozen=True, slots=True)
class LayoutGenerationState:
    """Persisted machine layout authority state."""

    generation: int
    mode: LayoutMode
    migration_id: str | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class LayoutWritePermit:
    """Generation-bound authority for exactly one project and destination."""

    project_uuid: CanonicalProjectUUID
    generation: int
    destination: LayoutDestination
    redirect_count: int = 0


@dataclass(frozen=True, slots=True)
class LayoutTestHooks:
    """Deterministic synchronization hooks for race tests; never time based."""

    before_revalidate: Callable[[LayoutWritePermit], None] | None = None


def _utc_now() -> str:
    return now_utc_iso()


class LayoutGenerationAuthority:
    """Sole machine layout record/lock API, scoped to one project permit issuer."""

    _lock_path: Path
    _lock_timeout_seconds: float
    _marker_path: Path
    _project_uuid: CanonicalProjectUUID
    _record_path: Path

    __slots__ = (
        "_lock_path",
        "_lock_timeout_seconds",
        "_marker_path",
        "_project_uuid",
        "_record_path",
    )

    def __init__(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        raise TypeError("layout authority is created by ProjectSyncStore")

    @property
    def record_path(self) -> Path:
        """Machine authority record path, exposed read-only for diagnostics."""
        return self._record_path

    @property
    def lock_path(self) -> Path:
        """Machine authority lock path, exposed read-only for diagnostics."""
        return self._lock_path

    @property
    def marker_path(self) -> Path:
        """Durable initialization marker used to detect record disappearance."""
        return self._marker_path

    def _lock(self) -> FileLock:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        return FileLock(str(self._lock_path), timeout=self._lock_timeout_seconds)

    @staticmethod
    def _initial_state() -> LayoutGenerationState:
        return LayoutGenerationState(
            generation=1,
            mode=LayoutMode.LEGACY,
            migration_id=None,
            updated_at=_utc_now(),
        )

    def _read_existing_record_locked(
        self,
        *,
        initialized: bool,
        materialize_marker: bool,
    ) -> LayoutGenerationState:
        """Decode an existing authority record, optionally repairing its marker."""
        try:
            raw: Any = json.loads(self._record_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise TypeError("layout record must be an object")
            generation = raw["generation"]
            migration_id = raw.get("migration_id")
            updated_at = raw["updated_at"]
            if (
                not isinstance(generation, int)
                or isinstance(generation, bool)
                or generation < 1
                or not isinstance(updated_at, str)
                or (migration_id is not None and not isinstance(migration_id, str))
            ):
                raise TypeError("layout record fields have invalid types")
            state = LayoutGenerationState(
                generation=generation,
                mode=LayoutMode(raw["mode"]),
                migration_id=migration_id,
                updated_at=updated_at,
            )
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LayoutAuthorityCorruptError(f"invalid machine layout authority: {self._record_path}") from exc
        if state.mode is LayoutMode.CUTOVER_PENDING and not state.migration_id:
            raise LayoutAuthorityCorruptError("cutover_pending layout must name its migration")
        if state.mode is not LayoutMode.CUTOVER_PENDING and state.migration_id is not None:
            raise LayoutAuthorityCorruptError("only cutover_pending layout may retain a migration identity")
        if not initialized and materialize_marker:
            self._write_marker_locked()
        return state

    def _read_locked(self) -> LayoutGenerationState:
        initialized = self._read_marker_locked()
        if not self._record_path.exists():
            if initialized:
                raise LayoutAuthorityCorruptError(f"machine layout authority record is missing: {self._record_path}")
            state = self._initial_state()
            self._write_locked(state)
            self._write_marker_locked()
            return state
        return self._read_existing_record_locked(
            initialized=initialized,
            materialize_marker=True,
        )

    def _read_marker_locked(self) -> bool:
        if not self._marker_path.exists():
            return False
        try:
            marker = self._marker_path.read_text(encoding="ascii")
        except (OSError, UnicodeError) as exc:
            raise LayoutAuthorityCorruptError(f"invalid machine layout initialization marker: {self._marker_path}") from exc
        if marker != "initialized-v1\n":
            raise LayoutAuthorityCorruptError(f"invalid machine layout initialization marker: {self._marker_path}")
        return True

    def _write_marker_locked(self) -> None:
        self._marker_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._marker_path.with_name(f".{self._marker_path.name}.{os.getpid()}.{uuid4().hex}.tmp")
        try:
            with temporary.open("w", encoding="ascii") as stream:
                stream.write("initialized-v1\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._marker_path)
            self._fsync_parent(self._marker_path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _fsync_parent(path: Path) -> None:
        if os.name == "nt":
            return
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _write_locked(self, state: LayoutGenerationState) -> None:
        self._record_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._record_path.with_name(f".{self._record_path.name}.{os.getpid()}.{uuid4().hex}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(
                    asdict(state),
                    stream,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._record_path)
            self._fsync_parent(self._record_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _under_lock(
        self,
        operation: Callable[[], LayoutGenerationState],
    ) -> LayoutGenerationState:
        try:
            with self._lock():
                return operation()
        except Timeout as exc:
            raise LayoutAuthorityLockedError(f"timed out acquiring machine layout lock: {self._lock_path}") from exc

    def read_state(self) -> LayoutGenerationState:
        """Return the current verified machine layout state."""
        return self._under_lock(self._read_locked)

    def peek_state(self) -> LayoutGenerationState:
        """Read an atomic authority snapshot without creating a lock or files."""
        initialized = self._read_marker_locked()
        if not self._record_path.exists():
            if initialized:
                raise LayoutAuthorityCorruptError(f"machine layout authority record is missing: {self._record_path}")
            return self._initial_state()
        return self._read_existing_record_locked(
            initialized=initialized,
            materialize_marker=False,
        )

    @staticmethod
    def _destination(state: LayoutGenerationState) -> LayoutDestination:
        if state.mode is LayoutMode.PROJECT_ONLY:
            return LayoutDestination.PROJECT_STORE
        # The migrating writer copies legacy rows INTO the project store while the
        # machine is CUTOVER_PENDING; a silent LEGACY route here would defeat cutover.
        if state.mode is LayoutMode.CUTOVER_PENDING and _in_cutover_drive():
            return LayoutDestination.PROJECT_STORE
        return LayoutDestination.LEGACY

    def issue_write_permit(self) -> LayoutWritePermit:
        """Resolve the layout for a first live write, then issue a bound permit.

        Resolution (greenfield → ``PROJECT_ONLY`` before any LEGACY persist; legacy
        data → auto-cutover; escape hatch → loud refusal) runs here because this is
        the sole write-path seam the journal/outbox invoke. A migrating writer
        re-entering during its own copy skips resolution and reads the live state.
        """
        state = self.read_state() if _in_cutover_drive() else self._resolved_state_for_write()
        return LayoutWritePermit(
            project_uuid=self._project_uuid,
            generation=state.generation,
            destination=self._destination(state),
        )

    def _resolved_state_for_write(self) -> LayoutGenerationState:
        """Resolve layout for a write; a still-pending cutover is not fatal here.

        A ``LayoutCutoverIncompleteError`` (contention or a foreign in-flight
        migration) is caught so ``execute_write`` can block-and-retry then surface
        it loudly — never a silent LEGACY write. The escape-hatch refusal and an
        exact-verification failure propagate (they are the loud outcome themselves).
        """
        try:
            return self.resolve_layout_for_write()
        except LayoutCutoverIncompleteError:
            return self.read_state()

    def _permit_matches(
        self,
        permit: LayoutWritePermit,
        state: LayoutGenerationState,
    ) -> bool:
        return permit.project_uuid == self._project_uuid and permit.generation == state.generation and permit.destination is self._destination(state)

    def revalidate(self, permit: LayoutWritePermit) -> LayoutWritePermit:
        """Fail if *permit* is foreign or stale immediately before a write."""
        if permit.project_uuid != self._project_uuid:
            raise ValueError("layout permit project UUID does not match this store")
        state = self.read_state()
        if not self._permit_matches(permit, state):
            raise StaleLayoutWritePermitError(f"layout permit generation {permit.generation} is stale; current generation is {state.generation}")
        return permit

    def execute_write(
        self,
        permit: LayoutWritePermit,
        writer: Callable[[LayoutWritePermit], object],
        *,
        test_hooks: LayoutTestHooks | None = None,
    ) -> LayoutWritePermit:
        """Revalidate under the lock, redirect once if stale, and invoke *writer*.

        The callback runs while the machine layout lock remains held, so cutover
        cannot advance between the final revalidation and the caller's insert.
        """
        if permit.project_uuid != self._project_uuid:
            raise ValueError("layout permit project UUID does not match this store")
        if not _in_cutover_drive():
            # INV-5: a live write arriving during CUTOVER_PENDING blocks-and-retries
            # for the migration to publish, then surfaces loudly on timeout — it is
            # never handed a silent LEGACY permit via _destination.
            self._await_publish_or_loud(permit, test_hooks)
        if test_hooks is not None and test_hooks.before_revalidate is not None:
            test_hooks.before_revalidate(permit)

        candidate = permit
        for attempt in range(2):
            try:
                with self._lock():
                    state = self._read_locked()
                    if self._permit_matches(candidate, state):
                        writer(candidate)
                        return candidate
                    if attempt == 0:
                        if candidate.redirect_count >= 1:
                            break
                        candidate = LayoutWritePermit(
                            project_uuid=self._project_uuid,
                            generation=state.generation,
                            destination=self._destination(state),
                            redirect_count=candidate.redirect_count + 1,
                        )
                        continue
            except Timeout as exc:
                raise LayoutAuthorityLockedError(f"timed out acquiring machine layout lock: {self._lock_path}") from exc
            break
        raise StaleLayoutWritePermitError("layout generation changed again after the single permitted redirect")

    def begin_cutover(self, migration_id: str) -> LayoutGenerationState:
        """Advance from legacy to a migration-owned cutover-pending generation."""
        migration_id = migration_id.strip()
        if not migration_id:
            raise ValueError("migration identity is required")

        def advance() -> LayoutGenerationState:
            current = self._read_locked()
            if current.mode is LayoutMode.CUTOVER_PENDING:
                if current.migration_id == migration_id:
                    return current
                raise LayoutAuthorityError("another migration owns cutover")
            if current.mode is LayoutMode.PROJECT_ONLY:
                raise LayoutAuthorityError("layout is already project-only")
            updated = LayoutGenerationState(
                generation=current.generation + 1,
                mode=LayoutMode.CUTOVER_PENDING,
                migration_id=migration_id,
                updated_at=_utc_now(),
            )
            self._write_locked(updated)
            return updated

        return self._under_lock(advance)

    def publish_project_only(
        self,
        migration_id: str,
        *,
        verify_exact: Callable[[], bool],
    ) -> LayoutGenerationState:
        """Publish project-only placement only after exact verification passes."""
        migration_id = migration_id.strip()
        if not migration_id:
            raise ValueError("migration identity is required")

        def publish() -> LayoutGenerationState:
            current = self._read_locked()
            if current.mode is not LayoutMode.CUTOVER_PENDING or current.migration_id != migration_id:
                raise LayoutAuthorityError("project-only publication requires the owning pending migration")
            if verify_exact() is not True:
                raise LayoutVerificationError("exact migration verification did not authorize cutover")
            updated = LayoutGenerationState(
                generation=current.generation + 1,
                mode=LayoutMode.PROJECT_ONLY,
                migration_id=None,
                updated_at=_utc_now(),
            )
            self._write_locked(updated)
            return updated

        return self._under_lock(publish)

    # --- layout resolution + canonical crash-safe auto-cutover (WP03/IC-02) ----

    def _spec_kitty_dir(self) -> Path:
        """The machine runtime root that holds the legacy ``queues/`` + ``queue.db``.

        ``record_path`` is ``<runtime_root>/projects/.layout-generation.json`` — the
        legacy sources ``discover_source_dbs`` reads sit one level up, at the root.
        """
        return self._record_path.parent.parent

    def auto_migration_id(self) -> str:
        """Deterministic, root-derived migration identity for lazy auto-cutover.

        Stable across process restarts (a crash-and-retry re-enters the SAME
        migration, so ``begin_cutover``'s idempotent branch is taken) and distinct
        across roots. Never ``uuid4`` — a fresh id per run would brick a crashed
        root by tripping "another migration owns cutover".
        """
        # noqa rationale: this is a deterministic, non-cryptographic identifier
        # derivation from a stable root path — not content integrity or a charter
        # digest — so charter.hasher.hash_content() does not apply (cf. the same
        # correlation-hash pattern in project_store_migration._safe_failure).
        digest = hashlib.sha256(str(self._spec_kitty_dir()).encode("utf-8")).hexdigest()  # noqa: TID251
        return f"auto-cutover-{digest[:32]}"

    def has_legacy_data(self) -> bool:
        """Answer "does this root hold legacy data?" via the real reader.

        Uses ``discover_source_dbs`` + queued-row counts (never the retired
        ``queue.py`` stubs, which raise). A present-but-empty source DB is NOT
        legacy data awaiting migration; a malformed queue filename is skipped by
        the discoverer. An unreadable source fails closed as legacy-present so a
        root that may hold un-migrated data is never silently greenfielded.
        """
        from specify_cli.sync.migrate_journal import _read_queued_rows, discover_source_dbs

        for source in discover_source_dbs(self._spec_kitty_dir()):
            try:
                if _read_queued_rows(source.path):
                    return True
            except sqlite3.Error:
                return True
        return False

    @staticmethod
    def _auto_cutover_disabled() -> bool:
        """Read the escape hatch at resolution time (never import time)."""
        return bool(os.environ.get(NO_AUTO_CUTOVER_ENV))

    def resolve_layout_for_write(
        self,
        *,
        cutover_copy: Callable[[str], bool] | None = None,
    ) -> LayoutGenerationState:
        """Resolve the machine layout for a first live write.

        The mission-critical property (INV-1): no state returns capture-success
        while journaling zero events. A greenfield root publishes ``PROJECT_ONLY``
        *before* any LEGACY persist; a legacy-with-data root auto-migrates via the
        canonical engines under a deterministic id; the escape hatch refuses loudly.
        """
        if _in_cutover_drive():
            return self.peek_state()
        snapshot = self.peek_state()
        if snapshot.mode is LayoutMode.PROJECT_ONLY:
            return snapshot  # already migrated — no write, bytes untouched (NFR-003)
        if snapshot.mode is LayoutMode.CUTOVER_PENDING:
            return self._resume_pending(snapshot, cutover_copy)
        if not self.has_legacy_data():
            return self._publish_greenfield()
        if self._auto_cutover_disabled():
            raise LayoutAutoCutoverRefusedError(
                f"legacy queue data is present and auto-cutover is disabled "
                f"({NO_AUTO_CUTOVER_ENV}); run `{_MANUAL_MIGRATE_COMMAND}` to migrate it explicitly"
            )
        return self._begin_and_drive(cutover_copy)

    def _resume_pending(
        self,
        snapshot: LayoutGenerationState,
        cutover_copy: Callable[[str], bool] | None,
    ) -> LayoutGenerationState:
        """Re-enter a CUTOVER_PENDING root; complete OUR migration, defer a foreign one.

        The escape hatch gates *initiating* auto-cutover, not *finishing* one already
        authorized — so an in-flight cutover still converges even with the hatch set.
        """
        if snapshot.migration_id != self.auto_migration_id():
            return snapshot  # an operator-owned migration holds cutover; do not interfere
        return self._drive(self.auto_migration_id(), cutover_copy)

    def _begin_and_drive(
        self,
        cutover_copy: Callable[[str], bool] | None,
    ) -> LayoutGenerationState:
        migration_id = self.auto_migration_id()
        self.begin_cutover(migration_id)
        return self._drive(migration_id, cutover_copy)

    def _drive(
        self,
        migration_id: str,
        cutover_copy: Callable[[str], bool] | None,
    ) -> LayoutGenerationState:
        """Copy via the canonical engine, then publish only after exact verification.

        Never bricks the root: a store-lock contention (e.g. driven from inside a
        live write's own unit of work) or an unresolved copy conflict leaves the
        record CUTOVER_PENDING so a later run re-enters the same id and completes.
        """
        from specify_cli.sync.project_store import ProjectStoreLockedError

        copy = cutover_copy if cutover_copy is not None else self._default_cutover_copy
        try:
            with _cutover_drive():
                blocked = copy(migration_id)
        except ProjectStoreLockedError:
            return self.read_state()  # contended — re-enter later, never brick
        if blocked:
            return self.read_state()  # unresolved conflict — do not publish over it
        self.publish_project_only(migration_id, verify_exact=self._conservation_ok)
        return self.read_state()

    def _publish_greenfield(self) -> LayoutGenerationState:
        """Publish PROJECT_ONLY on a no-legacy-data root WITHOUT persisting LEGACY.

        Closes Hazard (b): the greenfield decision is made and published ahead of
        ``_read_locked``'s LEGACY persist, so a fresh root's "never migrated" signal
        never self-destructs and its first event lands in the journal (FR-002).
        """

        def advance() -> LayoutGenerationState:
            initialized = self._read_marker_locked()
            if self._record_path.exists():
                current = self._read_existing_record_locked(
                    initialized=initialized,
                    materialize_marker=False,
                )
                if current.mode is LayoutMode.PROJECT_ONLY:
                    return current
                if current.mode is not LayoutMode.LEGACY:
                    raise LayoutAuthorityError("greenfield publish requires an unresolved or legacy record")
                generation = current.generation + 1
            else:
                generation = 1
            updated = LayoutGenerationState(
                generation=generation,
                mode=LayoutMode.PROJECT_ONLY,
                migration_id=None,
                updated_at=_utc_now(),
            )
            self._write_locked(updated)
            self._write_marker_locked()
            return updated

        return self._under_lock(advance)

    def _default_cutover_copy(self, migration_id: str) -> bool:
        """Copy legacy queues into the journal via the canonical engine (reuse only).

        Returns ``True`` iff the migration is blocked (an unresolved divergent-payload
        conflict), in which case the drive must NOT publish. Dedup, provenance,
        quarantine, and ownerless-row attribution all live in the engine — never
        re-derived here.
        """
        del migration_id  # the engine keys provenance on (event_id, source_digest)
        from specify_cli.event_journal.journal import EventJournal
        from specify_cli.sync.migrate_journal import (
            AUDIT_DB_NAME,
            MigrationAudit,
            migrate_queues_to_journal,
        )
        from specify_cli.sync.project_store import ProjectSyncStore

        spec_kitty_dir = self._spec_kitty_dir()
        store = ProjectSyncStore(self._project_uuid)
        audit = MigrationAudit(spec_kitty_dir / AUDIT_DB_NAME)
        try:
            with store.unit_of_work() as unit:
                journal = EventJournal(unit, store.layout_generation())
                result = migrate_queues_to_journal(spec_kitty_dir, journal=journal, audit=audit)
            return bool(result.blocked)
        finally:
            with contextlib.suppress(sqlite3.Error):
                audit.close()

    def _conservation_ok(self) -> bool:
        """Exact-copy verification: every queued legacy event is present exactly once.

        The ``verify_exact`` callback ``publish_project_only`` gates on — a non-exact
        copy refuses publication (``LayoutVerificationError``) and the root stays
        CUTOVER_PENDING for a later, converging run.
        """
        from specify_cli.event_journal.journal import EventJournal
        from specify_cli.sync.migrate_journal import _read_queued_rows, discover_source_dbs
        from specify_cli.sync.project_store import ProjectSyncStore

        expected: set[str] = set()
        for source in discover_source_dbs(self._spec_kitty_dir()):
            with contextlib.suppress(sqlite3.Error):
                expected.update(row.event_id for row in _read_queued_rows(source.path))
        store = ProjectSyncStore(self._project_uuid)
        with store.unit_of_work() as unit:
            present = {event.event_id for event in EventJournal(unit, store.layout_generation()).read_all()}
        return expected <= present

    def _await_publish_or_loud(
        self,
        permit: LayoutWritePermit,
        test_hooks: LayoutTestHooks | None,
    ) -> None:
        """Block-and-retry a live write while CUTOVER_PENDING, then surface loudly.

        Deterministic (bounded iterations, never wall-clock): the ``before_revalidate``
        hook is the synchronization point a test uses to publish (or withhold) the
        migration mid-wait. On timeout the write is routed to the loud surface via
        ``LayoutCutoverIncompleteError`` — never a silent LEGACY swallow (INV-5).
        """
        for _ in range(_CUTOVER_WAIT_ATTEMPTS):
            if self.read_state().mode is not LayoutMode.CUTOVER_PENDING:
                return
            if test_hooks is not None and test_hooks.before_revalidate is not None:
                test_hooks.before_revalidate(permit)
        if self.read_state().mode is LayoutMode.CUTOVER_PENDING:
            raise LayoutCutoverIncompleteError(
                "machine layout cutover did not publish within the bounded wait; "
                "the event is routed to the loud surface rather than dropped to legacy"
            )


def _new_layout_generation_authority(
    *,
    project_uuid: CanonicalProjectUUID,
    runtime_root: Path,
    lock_timeout_seconds: float,
) -> LayoutGenerationAuthority:
    """Construct machine layout authority from ProjectSyncStore-derived paths."""
    if lock_timeout_seconds < 0:
        raise ValueError("layout lock timeout cannot be negative")
    authority = object.__new__(LayoutGenerationAuthority)
    projects_root = runtime_root / "projects"
    authority._project_uuid = project_uuid
    authority._record_path = projects_root / ".layout-generation.json"
    authority._lock_path = projects_root / ".layout-generation.lock"
    authority._marker_path = projects_root / ".layout-generation.initialized"
    authority._lock_timeout_seconds = lock_timeout_seconds
    return authority


__all__ = [
    "NO_AUTO_CUTOVER_ENV",
    "LayoutAutoCutoverRefusedError",
    "LayoutCutoverIncompleteError",
    "LayoutDestination",
    "LayoutMode",
    "LayoutTestHooks",
    "LayoutWritePermit",
]

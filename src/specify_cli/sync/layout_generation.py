"""Machine layout generation and current-writer permit authority."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from filelock import FileLock, Timeout

from specify_cli.sync.project_identity import CanonicalProjectUUID


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
    return datetime.now(UTC).isoformat()


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

    def _read_locked(self) -> LayoutGenerationState:
        initialized = self._read_marker_locked()
        if not self._record_path.exists():
            if initialized:
                raise LayoutAuthorityCorruptError(f"machine layout authority record is missing: {self._record_path}")
            state = self._initial_state()
            self._write_locked(state)
            self._write_marker_locked()
            return state
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
        if not initialized:
            self._write_marker_locked()
        return state

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

    @staticmethod
    def _destination(state: LayoutGenerationState) -> LayoutDestination:
        if state.mode is LayoutMode.PROJECT_ONLY:
            return LayoutDestination.PROJECT_STORE
        return LayoutDestination.LEGACY

    def issue_write_permit(self) -> LayoutWritePermit:
        """Issue a generation-bound permit for this store's canonical UUID."""
        state = self.read_state()
        return LayoutWritePermit(
            project_uuid=self._project_uuid,
            generation=state.generation,
            destination=self._destination(state),
        )

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
    "LayoutAuthorityCorruptError",
    "LayoutAuthorityError",
    "LayoutAuthorityLockedError",
    "LayoutDestination",
    "LayoutGenerationState",
    "LayoutMode",
    "LayoutTestHooks",
    "LayoutVerificationError",
    "LayoutWritePermit",
    "StaleLayoutWritePermitError",
]

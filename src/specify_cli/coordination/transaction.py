"""BookkeepingTransaction — atomic emit + commit on the coordination branch.

This module implements the contract in
``contracts/bookkeeping_transaction.md``.

It is the single owner of writes that target the coordination branch:

    acquire → policy gate → append → materialize → commit → outbound → release

On exception, performs **surgical truncate** rollback of the event log
(FR-010) and byte-snapshot rollback of any other artifact written via
:meth:`BookkeepingTransaction.write_artifact`. It NEVER uses
``git checkout --`` (C-009 prohibits it for any rollback path).

Spec source: FR-019, FR-020, FR-021, FR-023, FR-026, FR-033, C-009,
C-013, NFR-001, NFR-008, NFR-010.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import ClassVar

import ulid as _ulid_mod

from specify_cli.coordination.policy import (
    WorkflowMutationPolicy,
    _normalize_ref,
)
from specify_cli.coordination.types import (
    Allowed,
    CommitReceipt,
    GitChangeSet,
    PendingEventHandle,
    Refused,
)
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.git.commit_helpers import safe_commit
from specify_cli.status import reducer as _reducer
from specify_cli.status import store as _store
from specify_cli.status.locking import (
    FeatureStatusLockTimeoutError,
    feature_status_lock,
)
from specify_cli.status.models import StatusEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class BookkeepingError(Exception):
    """Base for all BookkeepingTransaction failures.

    Subclasses carry a stable ``error_code`` class attribute so callers
    can route on the code without string parsing (NFR-007).
    """

    error_code: ClassVar[str] = "BOOKKEEPING_ERROR"


class BookkeepingPolicyRefused(BookkeepingError):
    """The pre-flight policy gate refused the would-be commit.

    Carries the underlying :class:`Refused` verdict so callers can
    surface the structured diagnostic.
    """

    error_code: ClassVar[str] = "BOOKKEEPING_POLICY_REFUSED"

    def __init__(self, verdict: Refused) -> None:
        self.verdict = verdict
        super().__init__(
            f"Bookkeeping refused: {verdict.error_code}: {verdict.message}"
        )


class BookkeepingLockTimeout(BookkeepingError):
    """The feature status lock could not be acquired within the timeout."""

    error_code: ClassVar[str] = "BOOKKEEPING_LOCK_TIMEOUT"


class BookkeepingWorktreeMissing(BookkeepingError):
    """Worktree resolution found neither a coord nor a valid lane worktree."""

    error_code: ClassVar[str] = "BOOKKEEPING_WORKTREE_MISSING"


class BookkeepingCommitFailed(BookkeepingError):
    """``safe_commit()`` raised; rollback ran; the original error is chained."""

    error_code: ClassVar[str] = "BOOKKEEPING_COMMIT_FAILED"


class BookkeepingDoubleEventId(BookkeepingError):
    """The same event_id was appended twice in one transaction."""

    error_code: ClassVar[str] = "BOOKKEEPING_DOUBLE_EVENT_ID"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_EVENTS_FILENAME = "status.events.jsonl"
_SNAPSHOT_FILENAME = "status.json"


def _kitty_specs_dir_name(mission_slug: str, mid8: str) -> str:
    """Return the kitty-specs sub-directory name for this mission.

    Mirrors the heuristic in
    :func:`specify_cli.coordination.workspace._compose_mission_dir`:
    post-WP03 slugs already contain ``-<mid8>``; pre-WP03 slugs do not.
    """
    if mission_slug.endswith(f"-{mid8}"):
        return mission_slug
    return f"{mission_slug}-{mid8}"


def _generate_ulid() -> str:
    """Generate a new ULID string (same convention as status.emit)."""
    if hasattr(_ulid_mod, "new"):
        return str(_ulid_mod.new().str)
    return str(_ulid_mod.ULID())


# WP06 swap: the canonical builder now lives in ``status.emit`` so the
# status domain owns it (FR-032). Re-export under the original name to
# keep ``coordination.build_status_event`` import-compatible for any
# callers that imported it through this module.
from specify_cli.status.emit import build_status_event  # noqa: E402


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


class BookkeepingTransaction(AbstractContextManager["BookkeepingTransaction"]):
    """The single chokepoint for coordination-branch writes.

    Use :meth:`acquire` to construct; do NOT call ``__init__`` directly.
    Use as a context manager:

    .. code-block:: python

        with BookkeepingTransaction.acquire(...) as txn:
            handle = txn.append_event(event)
            receipt = txn.commit("status: WP01 → claimed")
    """

    # ---- construction is private; use acquire() ----

    def __init__(
        self,
        *,
        repo_root: Path,
        mission_id: str,
        mission_slug: str,
        mid8: str,
        destination_ref: str,
        operation: str,
        worktree_root: Path,
        feature_dir: Path,
        events_path: Path,
        snapshot_path: Path,
        pre_emit_size: int,
        lock_cm: AbstractContextManager[Path],
    ) -> None:
        # Note: most attributes are public-but-immutable-by-convention.
        # ``mypy --strict`` is satisfied because we do not annotate them
        # as ``Final`` and we never re-bind them after construction.
        self.repo_root = repo_root
        self.mission_id = mission_id
        self.mission_slug = mission_slug
        self.mid8 = mid8
        self.destination_ref = destination_ref
        self.operation = operation
        self.worktree_root = worktree_root
        self.feature_dir = feature_dir
        self._events_path = events_path
        self._snapshot_path = snapshot_path
        self._pre_emit_size = pre_emit_size
        self._lock_cm = lock_cm

        # Per-transaction mutable state.
        self._event_ids: list[str] = []
        self._seen_event_ids: set[str] = set()
        # Snapshot of every artifact ever written via write_artifact().
        # None ⇒ file did not exist pre-write (rollback unlinks it).
        self._snapshots: dict[Path, bytes | None] = {}
        # Snapshot of status.json pre-emit (used to restore exact bytes
        # on rollback, NOT re-materialise — keeps SHA-256 identical).
        self._pre_emit_snapshot_bytes: bytes | None = None
        # Paths we will pass to safe_commit() on commit().
        self._staged_paths: list[Path] = []
        # Outbound side-effects deferred until commit succeeds.
        self._deferred: list[Callable[[], None]] = []
        self._committed = False
        self._explicit_commit_message: str | None = None
        self._explicit_commit_receipt: CommitReceipt | None = None

    # ---- acquire ----

    @classmethod
    def acquire(
        cls,
        *,
        repo_root: Path,
        mission_id: str,
        mission_slug: str,
        mid8: str,
        destination_ref: str,
        operation: str,
        timeout: float = 30.0,
    ) -> BookkeepingTransaction:
        """Construct, lock, and run the pre-flight policy gate.

        On a policy refusal, the lock is NEVER acquired (and therefore
        not released), and the refusal raises :class:`BookkeepingPolicyRefused`
        before any disk write.

        On a lock-acquire timeout, raises :class:`BookkeepingLockTimeout`.

        On a missing coordination worktree, raises
        :class:`BookkeepingWorktreeMissing`.
        """
        # 1. Normalise + shape-check destination_ref FIRST. The policy
        # gate also checks shape, but normalising once here makes the
        # internal state consistent (HEAD assertion in safe_commit will
        # compare to short-form).
        normalised_ref = _normalize_ref(destination_ref)

        # 2. Resolve the coord worktree. CoordinationWorkspace.resolve
        # creates the worktree on first call. A failing git operation
        # surfaces as the underlying subprocess error → wrap in
        # BookkeepingWorktreeMissing.
        try:
            worktree_root = CoordinationWorkspace.resolve(
                repo_root, mission_slug, mid8,
            )
        except Exception as exc:  # noqa: BLE001 — surface as our domain error
            raise BookkeepingWorktreeMissing(
                f"Failed to resolve coordination worktree for "
                f"{mission_slug}-{mid8}: {exc}"
            ) from exc

        # 3. Compute the feature_dir + status files INSIDE the coord
        # worktree (FR-024: the coord branch is the canonical writer).
        kitty_dir_name = _kitty_specs_dir_name(mission_slug, mid8)
        feature_dir = worktree_root / "kitty-specs" / kitty_dir_name
        events_path = feature_dir / _EVENTS_FILENAME
        snapshot_path = feature_dir / _SNAPSHOT_FILENAME

        # 4. Build the change set and run the pre-flight policy gate.
        # IMPORTANT: this happens BEFORE the lock is acquired so a
        # refusal never blocks other emitters waiting on the lock.
        change_set = GitChangeSet(
            destination_ref=destination_ref,
            repo_root=repo_root,
            worktree_root=worktree_root,
            paths=(events_path, snapshot_path),
            message=f"<pending: {operation}>",
            operation=operation,
        )
        verdict = WorkflowMutationPolicy.assert_allowed(change_set)
        if isinstance(verdict, Refused):
            raise BookkeepingPolicyRefused(verdict)
        # ``Allowed`` — fall through.
        assert isinstance(verdict, Allowed)  # noqa: S101 — defensive

        # 5. Acquire the feature status lock. The lock context manager
        # is held open across the lifetime of the transaction object;
        # we enter it here and exit it in __exit__.
        lock_cm = feature_status_lock(
            repo_root, mission_slug, timeout=timeout,
        )
        try:
            lock_cm.__enter__()
        except FeatureStatusLockTimeoutError as exc:
            raise BookkeepingLockTimeout(str(exc)) from exc

        # 6. Capture the pre-emit size of the event log (FR-010) and
        # snapshot of status.json (so rollback is byte-identical, not
        # "re-materialised approximately the same").
        pre_emit_size = events_path.stat().st_size if events_path.exists() else 0

        # Construct + return. The pre-emit status.json snapshot is read
        # lazily on first append_event() — many transactions never
        # write events.
        txn = cls(
            repo_root=repo_root,
            mission_id=mission_id,
            mission_slug=mission_slug,
            mid8=mid8,
            destination_ref=normalised_ref,
            operation=operation,
            worktree_root=worktree_root,
            feature_dir=feature_dir,
            events_path=events_path,
            snapshot_path=snapshot_path,
            pre_emit_size=pre_emit_size,
            lock_cm=lock_cm,
        )
        return txn

    # ---- context-manager protocol ----

    def __enter__(self) -> BookkeepingTransaction:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                # Happy path: implicit commit if the caller did not call
                # commit() explicitly. Then run deferred outbound.
                if not self._committed and (self._event_ids or self._staged_paths):
                    msg = self._explicit_commit_message or (
                        f"chore(spec-kitty): {self.operation}"
                    )
                    try:
                        self.commit(msg)
                    except BookkeepingCommitFailed:
                        # commit() already performed rollback and
                        # raised; re-raise out of __exit__.
                        raise
                self._run_deferred_outbound()
            else:
                # Exception path: surgical rollback.
                self._rollback()
        finally:
            self._release_lock()
        # Do not suppress exceptions (implicit None return).

    # ---- public API ----

    def append_event(self, event: StatusEvent) -> PendingEventHandle:
        """Append ``event`` to ``status.events.jsonl`` + re-materialise.

        On first call within the transaction, also snapshots the
        pre-emit ``status.json`` bytes so rollback can restore them
        byte-identically.

        Raises:
            BookkeepingDoubleEventId: ``event.event_id`` already
                appended in this transaction.
        """
        if event.event_id in self._seen_event_ids:
            raise BookkeepingDoubleEventId(
                f"event_id {event.event_id!r} appended twice in one "
                f"transaction"
            )

        # Capture the pre-emit status.json on first event so rollback
        # restores exact bytes (not "approximately re-materialised").
        if self._pre_emit_snapshot_bytes is None:
            if self._snapshot_path.exists():
                self._pre_emit_snapshot_bytes = self._snapshot_path.read_bytes()
            else:
                # Sentinel: empty bytes means "delete on rollback".
                # We distinguish from "no snapshot taken yet" by also
                # tracking whether we have written at least one event.
                self._pre_emit_snapshot_bytes = b""

        # Ensure parent directories exist (the feature_dir may be new
        # if this is the first emission for this mission).
        self.feature_dir.mkdir(parents=True, exist_ok=True)

        # Append + verify readback (matches existing emit pipeline).
        _store.append_event_verified(self.feature_dir, event)
        # Re-materialise status.json so an external observer sees
        # consistent state immediately after the event is durable.
        try:
            _reducer.materialize(self.feature_dir)
        except Exception as mat_exc:  # noqa: BLE001
            logger.warning(
                "BookkeepingTransaction: materialise failed after "
                "event %s: %s",
                event.event_id,
                mat_exc,
            )

        self._event_ids.append(event.event_id)
        self._seen_event_ids.add(event.event_id)
        # Both status files are now part of the changeset that commit()
        # will stage.
        for path in (self._events_path, self._snapshot_path):
            if path not in self._staged_paths:
                self._staged_paths.append(path)
        return PendingEventHandle(event_id=event.event_id)

    def write_artifact(self, path: Path, content: bytes) -> None:
        """Write ``content`` to ``path`` under snapshot-and-restore tracking.

        Captures ``pre_write_bytes`` BEFORE writing so rollback can
        restore the previous content (or unlink if the file did not
        previously exist). C-009: no ``git checkout --`` in the
        rollback path.
        """
        # Capture snapshot ONLY if we have not seen this path yet.
        # Re-writing the same path repeatedly in one transaction still
        # rolls back to the *original* pre-transaction state.
        if path not in self._snapshots:
            self._snapshots[path] = (
                path.read_bytes() if path.exists() else None
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

        if path not in self._staged_paths:
            self._staged_paths.append(path)

    def stage_path(self, path: Path) -> None:
        """Add ``path`` to the commit changeset without snapshot tracking.

        Use this for paths the caller has already modified out-of-band.
        Rollback does NOT restore these (documented contract — only
        :meth:`write_artifact` paths get snapshot/restore semantics).
        """
        if path not in self._staged_paths:
            self._staged_paths.append(path)

    def defer_outbound(self, side_effect: Callable[[], None]) -> None:
        """Queue ``side_effect`` to run after a successful commit.

        Callables run in registration order. Individual callable
        failures are LOGGED but do not abort the rest (best-effort
        fanout per FR-022). Rollback skips deferred outbound entirely.
        """
        self._deferred.append(side_effect)

    def commit(self, message: str) -> CommitReceipt:
        """Commit all staged paths via :func:`safe_commit`.

        Returns a :class:`CommitReceipt` carrying the new commit SHA
        and the list of event_ids appended in this transaction.

        On commit failure: rolls back the event log + every
        :meth:`write_artifact` path, then raises
        :class:`BookkeepingCommitFailed` chaining the original error.
        """
        if self._committed:
            # Idempotent: return the receipt from the first call.
            assert self._explicit_commit_receipt is not None  # noqa: S101
            return self._explicit_commit_receipt

        if not self._staged_paths:
            raise BookkeepingCommitFailed(
                "commit() called with no events or artifacts to commit"
            )

        try:
            result = safe_commit(
                repo_root=self.repo_root,
                worktree_root=self.worktree_root,
                destination_ref=self.destination_ref,
                message=message,
                paths=tuple(self._staged_paths),
            )
        except Exception as exc:  # noqa: BLE001 — wrap as domain error
            # Rollback before re-raising. ``_rollback`` is intentionally
            # tolerant: it logs but does not raise so the caller sees
            # the original commit failure, not a rollback failure.
            self._rollback()
            raise BookkeepingCommitFailed(
                f"safe_commit failed on {self.destination_ref!r}: {exc}"
            ) from exc

        receipt = CommitReceipt(
            commit_sha=result.sha,
            committed_at=datetime.now(UTC),
            destination_ref=self.destination_ref,
            worktree_root=self.worktree_root,
            event_ids=tuple(self._event_ids),
        )
        self._committed = True
        self._explicit_commit_message = message
        self._explicit_commit_receipt = receipt
        return receipt

    # ---- private ----

    def _rollback(self) -> None:
        """Surgical rollback: truncate event log; restore artifacts.

        C-009: never uses ``git checkout --``. Every restore is from
        in-process byte snapshots.

        Idempotent and tolerant of partial failures: every step is
        guarded so a failing restore on one path still attempts the
        others.
        """
        # 1. Surgical truncate of status.events.jsonl (FR-010). This
        # restores the file byte-for-byte to the pre-emit state because
        # the file is append-only.
        try:
            if self._events_path.exists():
                with self._events_path.open("ab") as fh:
                    fh.truncate(self._pre_emit_size)
        except OSError as exc:
            logger.error(
                "BookkeepingTransaction rollback: truncate of %s "
                "failed: %s",
                self._events_path,
                exc,
            )

        # 2. Restore status.json from the byte snapshot captured at
        # first append_event() (NOT a re-materialise — preserves SHA).
        # If no event was ever appended, the snapshot is None and we
        # leave status.json alone.
        if self._pre_emit_snapshot_bytes is not None:
            try:
                if self._pre_emit_snapshot_bytes:
                    self._snapshot_path.parent.mkdir(
                        parents=True, exist_ok=True,
                    )
                    self._snapshot_path.write_bytes(
                        self._pre_emit_snapshot_bytes,
                    )
                else:
                    # Pre-emit, the file did not exist. Remove the
                    # re-materialised one.
                    self._snapshot_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.error(
                    "BookkeepingTransaction rollback: restore of %s "
                    "failed: %s",
                    self._snapshot_path,
                    exc,
                )

        # 3. Snapshot-restore each tracked write_artifact path.
        for path, prev in self._snapshots.items():
            try:
                if prev is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(prev)
            except OSError as exc:
                logger.error(
                    "BookkeepingTransaction rollback: restore of %s "
                    "failed: %s",
                    path,
                    exc,
                )

    def _run_deferred_outbound(self) -> None:
        """Run deferred outbound side effects. Individual failures log only."""
        for side_effect in self._deferred:
            try:
                side_effect()
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.warning(
                    "BookkeepingTransaction deferred outbound failed: %s",
                    exc,
                )

    def _release_lock(self) -> None:
        """Release the feature status lock. Idempotent within one __exit__."""
        try:
            self._lock_cm.__exit__(None, None, None)
        except Exception as exc:  # noqa: BLE001 — defensive
            logger.error(
                "BookkeepingTransaction: lock release failed: %s",
                exc,
            )


# A small re-entrancy sentinel so nested-lock detection happens at the
# same granularity as feature_status_lock(). This is intentionally
# thread-local: the existing locking.py is thread-aware too.
_active_transactions = threading.local()

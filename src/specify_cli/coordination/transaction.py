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

import json as _json
import logging
import subprocess
import sys
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
from specify_cli.git.commit_helpers import SafeCommitRecoveryFailed, safe_commit
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


class BookkeepingLegacyResolutionFailed(BookkeepingError):
    """Legacy mission detected but the lane worktree could not be resolved.

    Stable error code ``BOOKKEEPING_LEGACY_RESOLUTION_FAILED``.  Raised
    when ``meta.json`` lacks ``coordination_branch`` (legacy mission)
    but the operator's current working directory does not sit inside a
    recognisable lane worktree, so we cannot determine which branch is
    the legitimate write target for this mission's bookkeeping.
    """

    error_code: ClassVar[str] = "BOOKKEEPING_LEGACY_RESOLUTION_FAILED"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_EVENTS_FILENAME = "status.events.jsonl"
_SNAPSHOT_FILENAME = "status.json"


def _confine_transaction_artifact_path(path: Path, worktree_root: Path) -> Path:
    """Return a resolved artifact path confined to the coordination worktree."""
    candidate = path.resolve()
    try:
        candidate.relative_to(worktree_root.resolve())
    except ValueError as exc:
        raise ValueError(
            f"Refusing to write artifact outside coordination worktree: {candidate}"
        ) from exc
    return candidate


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


# ---------------------------------------------------------------------------
# Legacy mission helpers (WP08 T035–T036, FR-017 / FR-027 / SC-11)
# ---------------------------------------------------------------------------
#
# Missions created before the coordination-branch topology landed do not
# carry ``coordination_branch`` in their ``meta.json``.  For those, the
# bookkeeping write target is the operator's current LANE worktree + its
# checked-out branch.  Every other invariant of the transaction
# (pre-flight policy gate, lock, surgical truncate rollback, outbound
# deferral) applies uniformly.  Only ``worktree_root`` and
# ``destination_ref`` differ.


def _is_legacy_mission(repo_root: Path, mission_slug: str, mid8: str) -> bool:
    """Return ``True`` when ``meta.json`` exists and lacks ``coordination_branch``.

    Detection rule (per WP08 reviewer guidance):

    * ``meta.json`` is **present** but does not carry the
      ``coordination_branch`` key → legacy mission.
    * ``meta.json`` is **absent** → treat as new-topology mission.  This
      is the case for synthetic test fixtures and very early mission
      lifecycle states; defaulting to new-topology preserves the
      existing test surface and matches the contract that any
      well-formed post-WP03 mission has its meta written before the
      first ``acquire()``.
    * A missing/manually deleted coord branch does **not** make a
      mission legacy — FR-018 idempotency re-creates it.  Only the
      ``meta.json`` field is consulted.
    """
    kitty_dir_name = _kitty_specs_dir_name(mission_slug, mid8)
    meta_path = repo_root / "kitty-specs" / kitty_dir_name / "meta.json"
    if not meta_path.exists():
        return False
    try:
        data = _json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError):
        # A malformed meta.json is not our problem to repair here; if a
        # caller hits this they will surface it through other validators.
        # Treat as new-topology so we do not silently route legacy.
        return False
    if not isinstance(data, dict):
        return False
    return not data.get("coordination_branch")


def _resolve_legacy_lane_destination(
    _repo_root: Path,
) -> tuple[Path, str]:
    """Resolve the operator's current lane worktree + its checked-out branch.

    Returns ``(worktree_root, branch_short_name)``.

    Algorithm:

    1. Take ``Path.cwd()`` and walk ancestors until a ``.git`` entry is
       found.  A ``.git`` *file* indicates a linked worktree; a ``.git``
       *directory* indicates the main checkout.  Either is acceptable as
       a legacy write target — pre-coord-topology bookkeeping ran in
       whichever checkout the operator stood in.
    2. Read ``git symbolic-ref HEAD`` from that worktree to obtain the
       branch name and strip ``refs/heads/`` so it is comparable to the
       short-form refs used elsewhere in the transaction.

    Raises :class:`BookkeepingLegacyResolutionFailed` when no ``.git``
    marker is found or HEAD is detached.
    """
    cwd = Path.cwd().resolve()
    worktree_root: Path | None = None
    for ancestor in [cwd, *cwd.parents]:
        marker = ancestor / ".git"
        if marker.exists():
            worktree_root = ancestor
            break
    if worktree_root is None:
        raise BookkeepingLegacyResolutionFailed(
            f"Legacy mission detected but no git worktree found above {cwd}",
        )
    try:
        head = subprocess.check_output(
            ["git", "-C", str(worktree_root), "symbolic-ref", "HEAD"],
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise BookkeepingLegacyResolutionFailed(
            f"Legacy mission detected at {worktree_root} but HEAD is detached "
            f"or symbolic-ref failed: {exc.stderr or exc}"
        ) from exc
    branch = head.removeprefix("refs/heads/")
    if not branch:
        raise BookkeepingLegacyResolutionFailed(
            f"Legacy mission detected at {worktree_root} but HEAD resolves to "
            f"an empty branch name"
        )
    # Defensive: discourage running legacy bookkeeping against repo_root
    # if that happens to be the main checkout sitting on `main`.  We do
    # not refuse here — the pre-flight policy gate in `acquire()` will
    # catch protected-ref writes via the same machinery used for the
    # coord topology (SC-11 behaviour parity).
    return worktree_root, branch


def _legacy_warning_marker_path(repo_root: Path, mission_id: str) -> Path:
    """Path of the per-mission once-only deprecation warning marker."""
    return repo_root / ".kittify" / f"legacy-warning-shown-{mission_id}"


def _emit_legacy_warning_once(
    repo_root: Path, mission_id: str, mission_slug: str,
) -> None:
    """Emit a one-line stderr deprecation warning, at most once per mission.

    Idempotent: subsequent invocations within the same project see the
    marker file and no-op.  The marker lives under ``.kittify/`` so it
    is project-scoped (per-mission ID) and survives across invocations.
    """
    marker = _legacy_warning_marker_path(repo_root, mission_id)
    if marker.exists():
        return
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("", encoding="utf-8")
    except OSError as exc:
        # Marker write failure is non-fatal: we still emit the warning
        # (worst case: warning repeats next invocation).
        logger.debug(
            "BookkeepingTransaction: failed to write legacy-warning "
            "marker %s: %s",
            marker,
            exc,
        )
    print(
        f"warning: mission {mission_slug!r} uses the legacy topology "
        f"(no coordination branch). New atomicity invariants apply, "
        f"but consider migrating: see "
        f"docs/migration/legacy-to-coordination.md",
        file=sys.stderr,
    )


def _confine_path_to_worktree(worktree_root: Path, path: Path) -> Path:
    """Resolve ``path`` relative to ``worktree_root`` and reject escapes."""
    candidate = path if path.is_absolute() else worktree_root / path
    try:
        resolved_worktree = worktree_root.resolve()
        resolved_candidate = candidate.resolve(strict=False)
    except OSError as exc:
        raise ValueError(
            f"Path {candidate} could not be resolved under worktree {worktree_root}: {exc}"
        ) from exc
    if not resolved_candidate.is_relative_to(resolved_worktree):
        raise ValueError(
            f"Path {candidate} resolves outside worktree {worktree_root}: "
            f"{resolved_candidate}"
        )
    return candidate


# WP06 swap: the canonical builder now lives in ``status.emit`` so the
# status domain owns it (FR-032). Re-export under the original name to
# keep ``coordination.build_status_event`` import-compatible for any
# callers that imported it through this module.
from specify_cli.status.emit import build_status_event  # noqa: E402,F401


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
        pre_emit_events_existed: bool,
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
        self._pre_emit_events_existed = pre_emit_events_existed
        self._lock_cm = lock_cm

        # Per-transaction mutable state.
        self._event_ids: list[str] = []
        self._seen_event_ids: set[str] = set()
        # Snapshot of every artifact ever written via write_artifact().
        # None ⇒ file did not exist pre-write (rollback unlinks it).
        self._snapshots: dict[Path, bytes | None] = {}
        # Snapshot of status.json pre-emit (used to restore exact bytes
        # on rollback, NOT re-materialise — keeps SHA-256 identical).
        self._pre_emit_snapshot_existed: bool | None = None
        self._pre_emit_snapshot_bytes: bytes | None = None
        # Paths we will pass to safe_commit() on commit().
        self._staged_paths: list[Path] = []
        # Outbound side-effects deferred until commit succeeds.
        self._deferred: list[Callable[[], None]] = []
        self._committed = False
        self._commit_recovery_failed_after_commit = False
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

        The feature-status lock is acquired before worktree resolution so
        first-time coordination worktree creation is serialized across
        concurrent emitters. Policy refusal still happens before any
        bookkeeping write.

        On a lock-acquire timeout, raises :class:`BookkeepingLockTimeout`.

        On a missing coordination worktree, raises
        :class:`BookkeepingWorktreeMissing`.
        """
        # 1. Normalise + shape-check destination_ref FIRST. The policy
        # gate also checks shape, but normalising once here makes the
        # internal state consistent (HEAD assertion in safe_commit will
        # compare to short-form).
        normalised_ref = _normalize_ref(destination_ref)

        # 2. Acquire the feature status lock before worktree resolution. The
        # lock context manager is held open across the lifetime of the
        # transaction object; on any setup failure below, release it before
        # propagating the domain error.
        lock_cm = feature_status_lock(
            repo_root, mission_slug, timeout=timeout,
        )
        try:
            lock_cm.__enter__()
        except FeatureStatusLockTimeoutError as exc:
            raise BookkeepingLockTimeout(str(exc)) from exc

        try:
            return cls._acquire_locked(
                repo_root=repo_root,
                mission_id=mission_id,
                mission_slug=mission_slug,
                mid8=mid8,
                destination_ref=destination_ref,
                normalised_ref=normalised_ref,
                operation=operation,
                lock_cm=lock_cm,
            )
        except Exception:
            lock_cm.__exit__(None, None, None)
            raise

    @classmethod
    def _acquire_locked(
        cls,
        *,
        repo_root: Path,
        mission_id: str,
        mission_slug: str,
        mid8: str,
        destination_ref: str,
        normalised_ref: str,
        operation: str,
        lock_cm: AbstractContextManager[Path],
    ) -> BookkeepingTransaction:
        # Resolve the worktree.  Two paths exist (WP08 T035–T036, SC-11):
        #
        # (a) **New topology** (default): the mission's meta.json carries
        #     ``coordination_branch``.  We resolve the per-mission coord
        #     worktree at ``.worktrees/<slug>-<mid8>-coord/`` (created on
        #     first call by ``CoordinationWorkspace.resolve``).  The
        #     ``destination_ref`` passed in by the caller already names
        #     the coord branch.
        #
        # (b) **Legacy mission** (pre-WP03 / pre-PR2): the mission's
        #     ``meta.json`` lacks ``coordination_branch``.  Bookkeeping
        #     for this mission must run against the operator's current
        #     LANE worktree + its checked-out branch, exactly how it did
        #     before the coord topology landed.  We override the caller-
        #     supplied ``destination_ref`` with the actual lane branch
        #     name resolved from the worktree's ``HEAD`` so the pre-flight
        #     policy gate and the ``safe_commit`` HEAD assertion see a
        #     consistent ref.
        #
        # Crucial invariant: **every other step of acquire() below — the
        # pre-flight policy gate, the feature-status lock, the surgical
        # truncate rollback, and the outbound deferral — applies
        # uniformly to both paths.**  Only ``worktree_root`` and (in
        # legacy mode) ``destination_ref`` differ.
        legacy_mode = _is_legacy_mission(repo_root, mission_slug, mid8)
        if legacy_mode:
            try:
                worktree_root, lane_branch = _resolve_legacy_lane_destination(
                    repo_root,
                )
            except BookkeepingLegacyResolutionFailed:
                raise
            # Override caller-supplied destination_ref with the actual
            # lane branch so policy + HEAD assertion both see truth.
            normalised_ref = _normalize_ref(lane_branch)
            destination_ref = normalised_ref
            _emit_legacy_warning_once(repo_root, mission_id, mission_slug)
        else:
            # New topology — create coord worktree on first call.
            try:
                worktree_root = CoordinationWorkspace.resolve(
                    repo_root, mission_slug, mid8,
                )
            except Exception as exc:  # noqa: BLE001 — domain error surface
                raise BookkeepingWorktreeMissing(
                    f"Failed to resolve coordination worktree for "
                    f"{mission_slug}-{mid8}: {exc}"
                ) from exc

        # 3. Compute the feature_dir + status files INSIDE the resolved
        # worktree.  Both paths (coord and legacy lane) host the
        # ``kitty-specs/<slug>-<mid8>/`` tree containing
        # ``status.events.jsonl`` + ``status.json``.  In legacy mode
        # there is no sparse-checkout policy on the lane, so the files
        # are physically present and the surgical truncate rollback
        # works against the lane worktree without modification.
        kitty_dir_name = _kitty_specs_dir_name(mission_slug, mid8)
        feature_dir = worktree_root / "kitty-specs" / kitty_dir_name
        events_path = feature_dir / _EVENTS_FILENAME
        snapshot_path = feature_dir / _SNAPSHOT_FILENAME

        # 4. Build the change set and run the pre-flight policy gate.
        # This still happens before any bookkeeping write; the lock is
        # already held only to serialize first-time coord worktree setup.
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

        # 5. Capture the pre-emit size of the event log (FR-010) and
        # snapshot of status.json (so rollback is byte-identical, not
        # "re-materialised approximately the same").
        pre_emit_events_existed = events_path.exists()
        pre_emit_size = events_path.stat().st_size if pre_emit_events_existed else 0

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
            pre_emit_events_existed=pre_emit_events_existed,
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
                if self._commit_recovery_failed_after_commit:
                    return
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
                recovery_after_commit = (
                    isinstance(exc, BookkeepingCommitFailed)
                    and isinstance(exc.__cause__, SafeCommitRecoveryFailed)
                    and exc.__cause__.commit_sha is not None
                )
                if not recovery_after_commit:
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
        if self._pre_emit_snapshot_existed is None:
            self._pre_emit_snapshot_existed = self._snapshot_path.exists()
            self._pre_emit_snapshot_bytes = (
                self._snapshot_path.read_bytes()
                if self._pre_emit_snapshot_existed
                else None
            )

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
        path = _confine_path_to_worktree(self.worktree_root, path)
        # Capture snapshot ONLY if we have not seen this path yet.
        # Re-writing the same path repeatedly in one transaction still
        # rolls back to the *original* pre-transaction state.
        path = _confine_transaction_artifact_path(path, self.worktree_root)
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
        path = _confine_path_to_worktree(self.worktree_root, path)
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
        if self._commit_recovery_failed_after_commit:
            raise BookkeepingCommitFailed(
                "commit() cannot be retried: safe_commit already created a commit "
                "but failed to restore caller staging"
            )

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
        except SafeCommitRecoveryFailed as exc:
            if exc.commit_sha is None:
                self._rollback()
            else:
                self._commit_recovery_failed_after_commit = True
            raise BookkeepingCommitFailed(
                f"safe_commit recovery failed on {self.destination_ref!r}: {exc}"
            ) from exc
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
                if self._pre_emit_events_existed:
                    with self._events_path.open("ab") as fh:
                        fh.truncate(self._pre_emit_size)
                else:
                    self._events_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.error(
                "BookkeepingTransaction rollback: truncate of %s "
                "failed: %s",
                self._events_path,
                exc,
            )

        # 2. Restore status.json from the byte snapshot captured at
        # first append_event() (NOT a re-materialise — preserves SHA).
        # If no event was ever appended, _pre_emit_snapshot_existed is
        # None and we leave status.json alone.
        if self._pre_emit_snapshot_existed is not None:
            try:
                if self._pre_emit_snapshot_existed:
                    assert self._pre_emit_snapshot_bytes is not None  # noqa: S101
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

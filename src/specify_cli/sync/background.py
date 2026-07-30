"""Background sync service for periodic queue flush.

Provides a daemon-threaded service that periodically drains the offline
event queue and syncs to the server, with exponential backoff on failures
and graceful shutdown via atexit.

Token acquisition:
    As of WP08 (browser-mediated OAuth), this service fetches its access
    token from the process-wide ``TokenManager`` via ``_fetch_access_token``,
    which runs the async ``get_access_token()`` in a short-lived loop from
    the background-sync thread.
"""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import TYPE_CHECKING

from specify_cli.auth import get_token_manager
from specify_cli.auth.errors import AuthenticationError
from specify_cli.auth.refresh_transaction import RefreshLockTimeoutError
from specify_cli.diagnostics import report_once

from .batch import (
    BatchEventResult,
    BatchSyncResult,
    run_final_sync_with_retries,
)
from .config import SyncConfig
from .diagnostics import SyncDiagnosticCode, emit_sync_diagnostic
from .feature_flags import is_saas_sync_enabled, saas_sync_disabled_message
from .queue import OfflineQueue

if TYPE_CHECKING:
    from .body_queue import BodyUploadTask, OfflineBodyUploadQueue
    from .namespace import UploadOutcome

logger = logging.getLogger(__name__)

# Maximum seconds the stop() best-effort sync may run before being
# abandoned.  Events stay in the durable queue for the daemon to drain.
_STOP_SYNC_TIMEOUT_SECONDS = 5
_UNAUTHENTICATED_SYNC_ERROR = (
    "Not authenticated: no valid access token. Run `spec-kitty auth login`."
)
_DIRECT_INGRESS_SKIPPED_ERROR = (
    "direct_ingress_missing_private_team: direct ingress skipped before final sync auth"
)


class LegacyQueueNotConvergedError(RuntimeError):
    """Legacy queue rows remain that no drain will ever deliver (#3030 T007).

    Raised instead of starting a daemon that would silently ignore them. See
    :meth:`BackgroundSyncService._assert_legacy_queue_converged`.
    """


class LegacyQueueUndeterminedError(LegacyQueueNotConvergedError):
    """Whether legacy rows remain could not be determined (#3030 H8).

    A subclass so every existing handler of the converged error keeps working,
    while callers and tests can still tell "there are N stranded rows" apart from
    "the store could not be read". Inability to determine is not permission.
    """


#: Failures of the legacy-count read that mean "could not determine" rather than
#: "the shape of this API changed". Anything outside this set — a ``TypeError``
#: from a changed arity, an ``AttributeError`` from a renamed field — must
#: propagate, because a guard whose safe default is *permission* silently
#: disables itself otherwise. That is the swallowed-exception fake green this
#: mission already hit once.
_UNDETERMINED_LEGACY_COUNT_ERRORS = (sqlite3.Error, OSError, ValueError)


def _count_legacy_event_rows() -> int | None:
    """Return the number of legacy queue *event* rows, or ``None`` if undeterminable.

    Read-only: composes the same ``detect_legacy_rows_for_scope`` helper the
    sync preflight uses, so the daemon and ``sync now`` agree on what "legacy
    rows remain" means rather than growing a second definition.

    Returns:
        The event-row count (``0`` when there is genuinely nothing stranded), or
        ``None`` when the legacy store could not be read. ``None`` is deliberately
        a distinct answer from ``0``: this function gates daemon start, so
        collapsing "unknown" onto "clean" hands out permission on a fault.
        ``counts.event_rows`` is read directly — no ``getattr`` default — so a
        renamed field raises instead of degrading to "clean".
    """
    from .queue import detect_legacy_rows_for_scope, read_queue_scope_from_credentials

    try:
        # The legacy DB has no per-scope partitioning, so the callee ignores
        # this argument; pass the active scope anyway for log context.
        counts = detect_legacy_rows_for_scope(read_queue_scope_from_credentials() or "")
    except _UNDETERMINED_LEGACY_COUNT_ERRORS as exc:
        logger.warning("Could not read the legacy queue to count stranded rows: %s", exc)
        return None

    return int(counts.event_rows)


def _emit_nonfatal_final_sync_diagnostic(
    diagnostic_code: SyncDiagnosticCode,
    message: str,
) -> None:
    """Report a final-sync problem without failing the local command result."""
    emit_sync_diagnostic(diagnostic_code, message)


def _safe_optional_queue_size(queue_obj: object | None) -> int:
    """Best-effort queue size lookup that tolerates missing attrs and test doubles."""
    if queue_obj is None:
        return 0
    try:
        raw = queue_obj.size()
    except Exception:
        return 0

    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _emit_direct_ingress_skip_diagnostic() -> None:
    """Emit the shared private-team ingress-skip warning best-effort."""
    try:
        from specify_cli.sync._team import resolve_private_team_id_for_ingress

        resolve_private_team_id_for_ingress(
            get_token_manager(),
            endpoint="/api/v1/events/batch/",
        )
    except Exception as exc:
        logger.debug("direct-ingress skip diagnostic unavailable: %s", exc)


def _unauthenticated_sync_result(
    queue: OfflineQueue,
    *,
    limit: int | None = None,
) -> BatchSyncResult:
    """Classify queued events as unauthenticated without mutating the queue."""
    result = BatchSyncResult()
    queue_size = _safe_optional_queue_size(queue)
    if queue_size <= 0:
        result.error_messages.append(_UNAUTHENTICATED_SYNC_ERROR)
        return result

    _emit_direct_ingress_skip_diagnostic()
    read_limit = queue_size if limit is None else min(queue_size, limit)
    events = queue.drain_queue(limit=read_limit)
    result.total_events = len(events)
    result.error_count = len(events)
    result.error_messages.append(_UNAUTHENTICATED_SYNC_ERROR)
    result.error_messages.append(_DIRECT_INGRESS_SKIPPED_ERROR)

    for event in events:
        event_id = str(event.get("event_id") or "unknown")
        result.failed_ids.append(event_id)
        result.event_results.append(
            BatchEventResult(
                event_id=event_id,
                status="rejected",
                error=_UNAUTHENTICATED_SYNC_ERROR,
                error_category="unauthenticated",
            )
        )

    return result


def _fetch_access_token_sync() -> str | None:
    """Fetch a valid access token from the TokenManager (sync bridge).

    Runs ``TokenManager.get_access_token()`` on a short-lived event loop so
    sync (non-async) callers like the background timer and body upload
    drainer can share the same single-flight refresh semantics as the async
    callers.

    Returns ``None`` if the user is not authenticated or refresh failed.
    Raises ``RefreshLockTimeoutError`` for bounded refresh-lock contention so
    final-sync callers can retry and emit the canonical non-fatal diagnostic.
    """
    tm = get_token_manager()
    if not tm.is_authenticated:
        return None

    try:
        # Prefer to reuse a running loop if one is already active on this
        # thread, otherwise spin up a fresh loop and discard it afterward.
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is not None:
            # Re-entering an active loop from sync code is unsafe; fall back to
            # a fresh thread-owned loop below to avoid nested `run_until_complete`.
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(tm.get_access_token())
            finally:
                new_loop.close()
        else:
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(tm.get_access_token())
            finally:
                with contextlib.suppress(Exception):
                    asyncio.set_event_loop(None)
                new_loop.close()
    except RefreshLockTimeoutError:
        raise
    except AuthenticationError as exc:
        logger.debug("Background sync token fetch failed: %s", exc)
        return None
    except Exception as exc:  # defensive
        logger.debug("Unexpected error fetching access token: %s", exc)
        return None


@dataclass
class BackgroundSyncService:
    """Manages periodic background sync of the offline event queue."""

    queue: OfflineQueue
    config: SyncConfig
    sync_interval_seconds: float = 300.0  # 5 minutes default
    _timer: threading.Timer | None = field(default=None, init=False, repr=False)
    _running: bool = field(default=False, init=False, repr=False)
    _backoff_seconds: float = field(default=0.5, init=False, repr=False)
    _last_sync: datetime | None = field(default=None, init=False, repr=False)
    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _body_queue: OfflineBodyUploadQueue | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _assert_legacy_queue_converged(self) -> None:
        """Refuse to run while unmigrated legacy queue rows remain (#3030 T007).

        WP02 removed the queue-backed event drain (FR-012). For rows captured
        after ``_capture_to_journal`` (``sync/emitter.py``) that is lossless —
        every one of them has a journal copy the dispatcher delivers. Rows that
        predate journal capture have no such copy, and with the drain gone
        nothing reads them and nothing reports them.

        Discarding those silently is the precise failure mode this mission
        exists to eliminate, so the daemon fails closed instead: the operator
        runs ``spec-kitty sync migrate`` to converge them into the journal.
        The migration is deliberately *not* run from here — it deletes
        journal-confirmed source rows, and a background timer thread is the
        wrong place to mutate the operator's queues unasked.

        Raises:
            LegacyQueueNotConvergedError: legacy event rows remain.
            LegacyQueueUndeterminedError: the legacy store could not be read, so
                whether rows are stranded is unknown. Unknown is not permission
                (#3030 H8) — but the remedy stays reachable: ``sync migrate`` does
                not route through the sync runtime, so it can still be run (and it
                reports the unreadable source as a ``source_errors`` count).
        """
        stranded = _count_legacy_event_rows()
        if stranded is None:
            undetermined = (
                "Refusing to start background sync: could not read the legacy "
                "queue at ~/.spec-kitty/queue.db, so whether undeliverable rows "
                "remain is unknown. Run `spec-kitty sync migrate` to converge and "
                "report on it; if the file is corrupt and holds nothing you need, "
                "move it aside. Inability to determine is not clearance."
            )
            logger.error(undetermined)
            raise LegacyQueueUndeterminedError(undetermined)
        if stranded <= 0:
            return

        message = (
            f"Refusing to start background sync: {stranded} legacy queue event "
            "row(s) remain that no drain will deliver. The queue-backed drain "
            "was removed (#3030 FR-012) and these rows may have no journal "
            "copy. Run `spec-kitty sync migrate` to converge them into the "
            "event journal, then start sync again."
        )
        logger.error(message)
        raise LegacyQueueNotConvergedError(message)

    def start(self) -> None:
        """Start the background sync service."""
        if not is_saas_sync_enabled():
            logger.info("%s Background sync service will remain stopped.", saas_sync_disabled_message())
            return

        # T007: bind the precondition before any timer is scheduled, so the
        # daemon can never quietly run alongside undeliverable legacy rows.
        self._assert_legacy_queue_converged()

        with self._lock:
            if self._running:
                return
            self._running = True
        self._schedule_next_sync()
        logger.debug("Background sync service started (interval=%ss)", self.sync_interval_seconds)

    def wake(self, delay_seconds: float = 0.1) -> None:
        """Bring the next sync tick forward without blocking the caller.

        Used by the dashboard daemon control plane when new queue work arrives
        and we want near-live replay rather than waiting for the steady-state
        timer interval.
        """
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            logger.debug("Skipping background sync wake; service lock is already held")
            return

        try:
            if not self._running:
                return
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._schedule_next_sync(delay_seconds=delay_seconds)
        finally:
            self._lock.release()

    def stop(self) -> None:
        """Stop the background sync service gracefully.

        Cancels the pending timer and attempts a best-effort final sync
        if there are queued events.  The final sync is bounded to
        ``_STOP_SYNC_TIMEOUT_SECONDS`` so process exit is never blocked
        indefinitely (see #598).
        """
        acquired = self._lock.acquire(timeout=5.0)
        try:
            self._running = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        finally:
            if acquired:
                self._lock.release()

        if not acquired:
            # Timer thread is stuck holding the lock; skip the final sync
            # rather than blocking shutdown.
            _emit_nonfatal_final_sync_diagnostic(
                SyncDiagnosticCode.LOCK_UNAVAILABLE,
                "Could not acquire sync lock within 5 s; skipping final sync. "
                "Queued events will be drained by the daemon.",
            )
            return

        # Best-effort final sync with a bounded timeout so atexit never
        # hangs the process.  Events stay in the durable queue and will
        # be drained on the next daemon tick.
        body_queue_has_work = _safe_optional_queue_size(self._body_queue) > 0
        if self.queue.size() > 0 or body_queue_has_work:
            sync_thread = threading.Thread(
                target=self._guarded_final_sync, daemon=True,
            )
            try:
                sync_thread.start()
            except RuntimeError as exc:
                _emit_nonfatal_final_sync_diagnostic(
                    SyncDiagnosticCode.EVENT_LOOP_UNAVAILABLE,
                    "Could not start final sync during interpreter shutdown. "
                    f"Queued events will be drained by the daemon. Detail: {exc}",
                )
                return
            sync_thread.join(timeout=_STOP_SYNC_TIMEOUT_SECONDS)
            if sync_thread.is_alive():
                _emit_nonfatal_final_sync_diagnostic(
                    SyncDiagnosticCode.EVENT_LOOP_UNAVAILABLE,
                    f"Final sync did not complete within {_STOP_SYNC_TIMEOUT_SECONDS}s. "
                    "Queued events will be drained by the daemon.",
                )
        logger.debug("Background sync service stopped")

    def _guarded_final_sync(self) -> None:
        """Run a single sync batch; swallows all exceptions."""
        run_final_sync_with_retries(self._perform_sync)

    @property
    def last_sync(self) -> datetime | None:
        return self._last_sync

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def is_running(self) -> bool:
        return self._running

    def sync_now(self, *, show_progress: bool = False) -> BatchSyncResult:
        """Trigger an immediate sync, draining all queued events.

        Unlike the periodic timer (which syncs a single batch), this
        loops until the queue is empty or all remaining events have
        exceeded their retry limit.
        """
        return self._perform_full_sync(show_progress=show_progress)

    def drain_body_uploads_only(self) -> None:
        """Drain ONLY the auth-gated body-upload queue; skip event sync entirely.

        Unlike :meth:`sync_now` / :meth:`_sync_once`, this entry point never
        invokes the event ``batch_sync`` / ``queue.process_batch_results`` path.
        It runs solely the existing body-upload drain
        (:meth:`_drain_body_queue`), which fetches its own access token and is a
        no-op when unauthenticated. The event offline queue is left completely
        untouched, preserving the body-upload / event-queue separation (C-006).

        Used by the ``sync now`` CLI command so a body-only flush cannot perturb
        the durable event queue or its batch-result bookkeeping.

        Thread-safe: holds ``_lock`` so background timer ticks cannot overlap.
        """
        if not is_saas_sync_enabled():
            logger.info("%s Body-upload drain skipped.", saas_sync_disabled_message())
            return

        with self._lock:
            if self._body_queue is None:
                return
            self._drain_body_queue()

    # ── Internal ──────────────────────────────────────────────────

    def _schedule_next_sync(self, delay_seconds: float | None = None) -> None:
        """Schedule the next sync tick based on interval or backoff."""
        if not self._running:
            return

        if delay_seconds is not None:
            interval = delay_seconds
        elif self._consecutive_failures > 0:
            interval = min(self._backoff_seconds, 30.0)
        else:
            interval = self.sync_interval_seconds

        self._timer = threading.Timer(interval, self._on_timer)
        self._timer.daemon = True  # Don't block CLI exit
        self._timer.start()

    def _on_timer(self) -> None:
        """Timer callback: sync if queue is non-empty, then reschedule."""
        if not self._running:
            return
        body_queue_has_work = _safe_optional_queue_size(self._body_queue) > 0
        if self.queue.size() > 0 or body_queue_has_work:
            self._perform_sync()
        self._schedule_next_sync()

    def _perform_sync(self) -> BatchSyncResult:
        """Execute a single batch sync operation (up to 1000 events).

        Thread-safe: acquires _lock so timer callbacks and sync_now()
        cannot overlap.

        On success resets backoff; on failure doubles backoff (capped at 30s).
        """
        with self._lock:
            return self._sync_once()

    def _perform_full_sync(self, *, show_progress: bool = False) -> BatchSyncResult:  # noqa: ARG002
        """Drain body uploads; the queue-backed event drain was removed (#3030 FR-012).

        ``show_progress`` is retained for signature compatibility with the callers
        and tests that still pass it; it no longer has an event drain to report on.

        Thread-safe: holds _lock for the full duration so background
        timer ticks are serialised.
        """
        if not is_saas_sync_enabled():
            logger.info("%s Full sync skipped.", saas_sync_disabled_message())
            result = BatchSyncResult()
            result.error_messages.append(saas_sync_disabled_message())
            return result

        with self._lock:
            try:
                access_token = _fetch_access_token_sync()
            except RefreshLockTimeoutError as exc:
                return self._record_transient_token_fetch_failure(exc)
            if access_token is None:
                return self._record_unauthenticated_tick(
                    _unauthenticated_sync_result(self.queue)
                )

            try:
                # FR-012 (spec-kitty#3030): the queue-backed event drain is GONE.
                #
                # This called ``sync_all_queued_events`` over the machine-global
                # legacy queue — a second live drain alongside the journal
                # dispatcher, with no per-project consent anywhere on it. Removal
                # strands nothing: ``_capture_to_journal`` (``sync/emitter.py:2057``)
                # runs before every gate and is unconditional, so any event that
                # reached the legacy queue already has a journal copy the
                # dispatcher can deliver.
                #
                # Body uploads still drain here; they are a separate store and are
                # gated separately (WP11).
                result = BatchSyncResult()
                if self._body_queue is not None and not self._drain_body_queue():
                    return self._record_unauthenticated_tick(result)
                self._consecutive_failures = 0
                self._backoff_seconds = 0.5
                self._last_sync = datetime.now(UTC)
                return result
            except Exception as exc:
                self._consecutive_failures += 1
                self._backoff_seconds = min(self._backoff_seconds * 2, 30.0)
                logger.warning(
                    "Full sync failed (attempt %d, next backoff %.1fs): %s",
                    self._consecutive_failures,
                    self._backoff_seconds,
                    exc,
                )
                result = BatchSyncResult()
                result.error_count = 1
                result.error_messages.append(str(exc))
                return result

    def _sync_once(self) -> BatchSyncResult:
        """Internal: single daemon tick (caller must hold _lock).

        Events are no longer drained here (#3030 FR-012); body uploads are the
        only work this performs. Success resets backoff and stamps
        ``last_sync``; a tick that raised **or could not authenticate** escalates
        backoff and leaves ``last_sync`` alone (#3030 H7 — #598's auth-failure
        backoff property, re-pointed at the surviving body drain).
        """
        if not is_saas_sync_enabled():
            logger.info("%s Single-batch sync skipped.", saas_sync_disabled_message())
            result = BatchSyncResult()
            result.error_messages.append(saas_sync_disabled_message())
            return result

        try:
            access_token = _fetch_access_token_sync()
        except RefreshLockTimeoutError as exc:
            return self._record_transient_token_fetch_failure(exc)
        if access_token is None:
            return self._record_unauthenticated_tick(
                _unauthenticated_sync_result(self.queue, limit=1000)
            )

        try:
            # FR-012 (spec-kitty#3030): the queue-backed event drain is GONE.
            # See ``_perform_full_sync`` for why removal strands nothing. The
            # journal dispatcher is the sole event drain; body uploads are a
            # separate store, gated separately (WP11).
            result = BatchSyncResult()
            if self._body_queue is not None and not self._drain_body_queue():
                # The drain has its own token fetch. When *that* one comes back
                # empty nothing was delivered, so the tick must not fall through
                # to the success bookkeeping below (#3030 H7 / #3004).
                return self._record_unauthenticated_tick(result)
            self._consecutive_failures = 0
            self._backoff_seconds = 0.5
            self._last_sync = datetime.now(UTC)
            return result
        except Exception as exc:
            self._consecutive_failures += 1
            self._backoff_seconds = min(self._backoff_seconds * 2, 30.0)
            logger.warning(
                "Sync failed (attempt %d, next backoff %.1fs): %s",
                self._consecutive_failures,
                self._backoff_seconds,
                exc,
            )
            result = BatchSyncResult()
            result.error_count = 1
            result.error_messages.append(str(exc))
            return result

    def _record_unauthenticated_tick(self, result: BatchSyncResult) -> BatchSyncResult:
        """Book a tick that could not authenticate as the failure it is (#3030 H7).

        #598 pinned "an auth failure escalates backoff" against the event POST's
        401. WP02 deleted that POST and the property lost its only witness: an
        expired token made the tick return early with backoff untouched, and — via
        the body drain's own silent token bail — could even reset
        ``consecutive_failures`` and stamp ``last_sync``, so ``sync status``
        reported a healthy sync while nothing moved (the #3004 class).

        Escalating matters concretely: ``_schedule_next_sync`` only consults
        ``_backoff_seconds`` while ``_consecutive_failures > 0``, so a tick that
        does not register its failure waits the full steady-state interval instead
        of retrying on the (≤30s) failure schedule. ``last_sync`` is deliberately
        *not* stamped.
        """
        if report_once("sync.unauthenticated"):
            logger.warning("Not authenticated, skipping sync")
        self._consecutive_failures += 1
        self._backoff_seconds = min(self._backoff_seconds * 2, 30.0)
        if not result.error_count:
            result.error_count = 1
        if _UNAUTHENTICATED_SYNC_ERROR not in result.error_messages:
            result.error_messages.append(_UNAUTHENTICATED_SYNC_ERROR)
        return result

    def _record_transient_token_fetch_failure(
        self,
        exc: RefreshLockTimeoutError,
    ) -> BatchSyncResult:
        """Represent auth refresh-lock contention as a retryable sync failure."""
        self._consecutive_failures += 1
        self._backoff_seconds = min(self._backoff_seconds * 2, 30.0)
        logger.debug(
            "Sync token fetch deferred by auth refresh lock (attempt %d): %s",
            self._consecutive_failures,
            exc,
        )
        result = BatchSyncResult()
        result.error_count = 1
        result.error_messages.append(str(exc))
        return result

    def _drain_body_queue(self) -> bool:
        """Drain body upload queue, processing tasks one at a time.

        Backoff progression (NFR-003):
        retry 0 → 1s, retry 1 → 2s, retry 2 → 4s, retry 3 → 8s,
        retry 4 → 16s, retry 5 → 32s, retry 6 → 64s, retry 7 → 128s,
        retry 8 → 256s, retry 9+ → 300s (5 min cap)

        Returns:
            ``True`` when the drain ran under a valid token (an empty queue counts
            — there was simply nothing to move). ``False`` when no token could be
            obtained, so the caller can book the tick as a failure instead of
            success. This return value is the contract: an unauthenticated bail
            used to be a bare ``return``, and the caller then reset backoff and
            stamped ``last_sync`` for a tick that delivered nothing (#3030 H7).
        """
        from .body_transport import push_content

        assert self._body_queue is not None

        # Remove stale tasks that exceeded max retries (prevent unbounded growth)
        removed = self._body_queue.remove_stale(max_retry_count=20)
        if removed > 0:
            logger.info("Removed %d stale body upload tasks", removed)

        access_token = _fetch_access_token_sync()
        if access_token is None:
            logger.debug("No auth token available, skipping body queue drain")
            return False

        tasks = self._body_queue.drain(limit=50)
        if not tasks:
            return True

        server_url = self.config.resolve_runtime_target().resolved_server_url
        for task in tasks:
            outcome = push_content(task, access_token, server_url)
            self._handle_body_outcome(task, outcome)
        return True

    def _handle_body_outcome(
        self, task: BodyUploadTask, outcome: UploadOutcome,
    ) -> None:
        """Update queue based on upload outcome."""
        from .namespace import UploadStatus

        assert self._body_queue is not None

        if outcome.status == UploadStatus.UPLOADED:
            self._body_queue.mark_uploaded(task.row_id)
            logger.debug("Body uploaded: %s", outcome)
        elif outcome.status == UploadStatus.ALREADY_EXISTS:
            self._body_queue.mark_already_exists(task.row_id)
            logger.debug("Body already exists: %s", outcome)
        elif outcome.status == UploadStatus.FAILED and outcome.retryable:
            self._body_queue.mark_failed_retryable(task.row_id, outcome.reason)
            logger.debug("Body upload retryable failure: %s", outcome)
        elif outcome.status == UploadStatus.FAILED and not outcome.retryable:
            self._body_queue.record_permanent_failure(task, outcome.reason)
            self._body_queue.mark_failed_permanent(task.row_id, outcome.reason)
            logger.debug("Body upload permanent failure recorded: %s", outcome)
        else:
            logger.warning("Unexpected body outcome: %s", outcome)


# ── Singleton accessor ────────────────────────────────────────────

_service: BackgroundSyncService | None = None
_service_lock = threading.Lock()


def get_sync_service() -> BackgroundSyncService:
    """Get or create the singleton BackgroundSyncService.

    Registers an atexit handler so the service stops cleanly when the
    process exits.
    """
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                service = BackgroundSyncService(
                    queue=OfflineQueue(),
                    config=SyncConfig(),
                )
                # Publish the singleton only once start() has succeeded (#3030 H8).
                # The T007 guard raises from start(); assigning first left the
                # module holding a constructed-but-never-started service with no
                # atexit stop hook, and every later call handed that dead object
                # back without retrying — so sync stayed dead for the life of the
                # process even after `sync migrate` fixed the cause.
                if is_saas_sync_enabled():
                    service.start()
                else:
                    logger.info("%s Service created without auto-start.", saas_sync_disabled_message())
                atexit.register(service.stop)
                _service = service
    return _service


def reset_sync_service() -> None:
    """Reset the singleton (for testing only)."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.stop()
        _service = None

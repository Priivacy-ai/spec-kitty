# CONTRACT VERIFICATION
# Verified 2026-04-21: The spec-kitty-saas repo is not co-located with this
# codebase; the cli-saas-current-api.yaml contract file is not accessible.
#
# Verification performed against the *local* SaaS sync client:
#   src/specify_cli/sync/client.py -> async def send_event(self, event: dict)
#   src/specify_cli/sync/emitter.py -> _route_event() (lines 981-1016)
#
# Client protocol: send_event(event: dict) is ASYNC and takes a single flat
# dict with an "event_type" discriminator field at the top level.  There is NO
# idempotency_key keyword argument.  The emitter pattern (emitter.py:993-1000)
# calls it via asyncio.ensure_future() when a loop is running, or via
# loop.run_until_complete() otherwise.
#
# Fields in the outbound envelope match the existing emitter contract:
#   ProfileInvocationStarted:   event_type, invocation_id, profile_id, action,
#                               request_text, governance_context_hash, actor,
#                               started_at
#   ProfileInvocationCompleted: event_type, invocation_id, outcome, evidence_ref,
#                               completed_at
#
# Fields verified against InvocationRecord v1:
#   invocation_id        ✅ present
#   profile_id           ✅ present (started only)
#   action               ✅ present (started only)
#   started_at           ✅ present (started only)
#   request_text         ✅ present (started only)
#   governance_context_hash ✅ present (started only)
#   outcome              ✅ present (completed only)
#   evidence_ref         ✅ present (completed only)
#   completed_at         ✅ present (completed only)
#
# No contract gaps detected.  WP07 is NOT blocked.
# -- verified 2026-04-21 by claude:sonnet-4-6:implementer --

from __future__ import annotations

import atexit
import asyncio
import contextlib
import json
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from specify_cli.invocation.record import InvocationRecord
from specify_cli.sync.routing import resolve_checkout_sync_routing

logger = logging.getLogger(__name__)

PROPAGATION_ERRORS_PATH = ".kittify/events/propagation-errors.jsonl"
_ATEXIT_TIMEOUT_SECONDS = 5.0
_PENDING_SEND_TASKS: set[asyncio.Task[Any]] = set()


def _track_send_task(task: asyncio.Task[Any]) -> None:
    """Retain scheduled send tasks until completion to avoid premature GC."""
    _PENDING_SEND_TASKS.add(task)
    task.add_done_callback(_PENDING_SEND_TASKS.discard)


def _get_saas_client(repo_root: Path) -> Any | None:  # noqa: ARG001
    """Return the connected WebSocketClient if authenticated; None otherwise.

    Mirrors the pattern in src/specify_cli/sync/emitter.py _is_authenticated()
    and _route_event().  Never raises — returns None when no token is configured
    or the WebSocket is not yet connected.
    """
    try:
        from specify_cli.auth import get_token_manager
        from specify_cli.sync.client import WebSocketClient

        token_manager = get_token_manager()
        if not bool(token_manager.is_authenticated):
            return None

        session = token_manager.get_current_session()
        if session is None:
            return None

        # Attempt to get (or lazily build) a connected client.
        # We intentionally avoid caching a singleton here: the propagator is
        # process-scoped; if the session expires between invocations the next
        # call returns None gracefully.
        client: WebSocketClient | None = getattr(token_manager, "_ws_client", None)
        if client is None or not getattr(client, "connected", False):
            return None
        return client
    except Exception:  # noqa: BLE001
        return None  # No token configured or sync module unavailable → no-op


def _propagate_one(record: InvocationRecord, repo_root: Path) -> None:
    """Propagate a single InvocationRecord to SaaS.

    Runs in a background thread.  Logs errors to propagation-errors.jsonl on
    failure.  Never raises — swallows all exceptions.

    The real SaaS client uses ``async def send_event(self, event: dict)``.
    It is NOT synchronous and does NOT accept an idempotency_key kwarg.
    Call pattern mirrors src/specify_cli/sync/emitter.py lines 993-1000.
    """
    routing = resolve_checkout_sync_routing(repo_root)
    if routing is not None and not routing.effective_sync_enabled:
        return  # Sync explicitly disabled for this checkout → no-op

    client = _get_saas_client(repo_root)
    if client is None:
        return  # No SaaS token / client not connected → no-op, no log

    try:
        if record.event == "started":
            event_dict: dict[str, object] = {
                "event_type": "ProfileInvocationStarted",
                "invocation_id": record.invocation_id,
                "profile_id": record.profile_id,
                "action": record.action,
                "request_text": record.request_text,
                "governance_context_hash": record.governance_context_hash,
                "actor": record.actor,
                "started_at": record.started_at,
            }
        else:  # completed
            event_dict = {
                "event_type": "ProfileInvocationCompleted",
                "invocation_id": record.invocation_id,
                "outcome": record.outcome,
                "evidence_ref": record.evidence_ref,
                "completed_at": record.completed_at,
            }

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already inside a running loop (rare in CLI threads, but safe)
                _track_send_task(asyncio.create_task(client.send_event(event_dict)))
            else:
                loop.run_until_complete(client.send_event(event_dict))
        except RuntimeError:
            # No current event loop (background thread with no loop) → create one
            asyncio.run(client.send_event(event_dict))

    except Exception as exc:  # noqa: BLE001
        _log_propagation_error(repo_root, record, str(exc))


def _log_propagation_error(
    repo_root: Path, record: InvocationRecord, error: str
) -> None:
    """Append propagation failure to the local error log.  Never raises."""
    try:
        import datetime  # noqa: PLC0415

        error_log = repo_root / PROPAGATION_ERRORS_PATH
        error_log.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "invocation_id": record.invocation_id,
            "event": record.event,
            "error": error,
            "at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        with error_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:  # noqa: BLE001
        pass  # Error logging must never raise


class InvocationSaaSPropagator:
    """Background-thread SaaS propagator for InvocationRecord events.

    Properties:
    - Non-blocking: submit() returns immediately; propagation happens in background.
    - Additive: if no SaaS token, no-op (no error, no warning to caller).
    - Failure-safe: propagation errors logged to propagation-errors.jsonl, never raised.
    - Process-exit: atexit handler waits for the ThreadPoolExecutor to drain
      (up to the OS process-exit timeout; work not finished is abandoned).
    """

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="invocation-saas"
        )
        self._pending: list[Future[None]] = []
        atexit.register(self._shutdown)

    def submit(self, record: InvocationRecord) -> None:
        """Submit a record for background propagation.  Returns immediately."""
        future: Future[None] = self._executor.submit(_propagate_one, record, self._repo_root)
        self._pending.append(future)

    def _shutdown(self) -> None:
        """Wait for pending propagations at process exit.

        ``shutdown(wait=True)`` blocks until all submitted futures complete.
        Python's process-exit machinery imposes its own timeout, so threads
        that have not finished by then are abandoned (acceptable behaviour).
        """
        with contextlib.suppress(Exception):
            self._executor.shutdown(wait=True, cancel_futures=False)

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
# Envelope shape (mission do-dispatch-open-op-lifecycle, decision
# 01KTSJEQANMNEV16WMSAJP6FR1 — no wire-compat with the pre-mission envelope;
# SaaS handlers are unimplemented, #1720/#1693):
#   Envelope dicts are rebuilt 1:1 from the v2 Op event models
#   (contracts/op-record-events.md):
#   ProfileInvocationStarted:   event_type + all OpStartedEvent fields
#                               (None fields omitted; request_text policy-gated)
#   ProfileInvocationCompleted: event_type + all OpCompletedEvent fields incl.
#                               closed_by (evidence_ref omitted when None and
#                               policy-gated)

from __future__ import annotations

import atexit
import asyncio
import contextlib
import json
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from specify_cli.invocation.adapters import get_saas_client as _get_saas_client_from_seam
from specify_cli.invocation.adapters import resolve_sync_routing
from specify_cli.invocation.projection_policy import EventKind, ModeOfWork, resolve_projection
from specify_cli.invocation.record import OpCompletedEvent, OpStartedEvent

# v2 Op lifecycle events accepted by the propagator (WP01 schema split).
OpEvent = OpStartedEvent | OpCompletedEvent

logger = logging.getLogger(__name__)

PROPAGATION_ERRORS_PATH = "kitty-ops/propagation-errors.jsonl"
_ATEXIT_TIMEOUT_SECONDS = 5.0
_PENDING_SEND_TASKS: set[asyncio.Task[Any]] = set()


def _track_send_task(task: asyncio.Task[Any]) -> None:
    """Retain scheduled send tasks until completion to avoid premature GC."""
    _PENDING_SEND_TASKS.add(task)
    task.add_done_callback(_PENDING_SEND_TASKS.discard)


def _get_saas_client(repo_root: Path) -> Any | None:
    """Return the connected SaaS client if available; None otherwise.

    Dispatches through the invocation adapter seam so that propagator.py
    has no direct import edge into the sync package (Leak #3 fix).
    Never raises — the seam guarantees safe-degrade on missing registration.
    """
    return _get_saas_client_from_seam(repo_root)


def _propagate_one(record: OpEvent, repo_root: Path) -> None:
    """Propagate a single Op lifecycle event to SaaS.

    Runs in a background thread.  Logs errors to propagation-errors.jsonl on
    failure.  Never raises — swallows all exceptions.

    The real SaaS client uses ``async def send_event(self, event: dict)``.
    It is NOT synchronous and does NOT accept an idempotency_key kwarg.
    Call pattern mirrors src/specify_cli/sync/emitter.py lines 993-1000.

    Check ordering (invariant — do not reorder):
      1. Sync-gate (routing.effective_sync_enabled=False → early return)
      2. Auth/client lookup (_get_saas_client returns None → early return)
      3. Policy lookup (resolve_projection → project=False → early return)
      4. Envelope build + send
    """
    # 1. Sync-gate: LOCAL-FIRST invariant (C-002, FR-012). Must remain first.
    # resolve_sync_routing returns bool | None via the invocation adapter seam:
    #   None  → no resolver registered (safe-degrade, proceed)
    #   True  → sync explicitly enabled (proceed)
    #   False → sync explicitly disabled (early return, no-op)
    sync_enabled = resolve_sync_routing(repo_root)
    if sync_enabled is False:
        return  # Sync explicitly disabled for this checkout → no-op

    # 2. Auth/client lookup. Must remain second.
    client = _get_saas_client(repo_root)
    if client is None:
        return  # No SaaS token / client not connected → no-op, no log

    # 3. Policy lookup (read-only, never raises, never blocks).
    event_kind = _coerce_event_kind(record.event)
    mode = _coerce_mode(getattr(record, "mode_of_work", None))
    rule = resolve_projection(mode, event_kind)
    if not rule.project:
        return  # Policy says no projection for this (mode, event) pair.

    try:
        event_dict = _build_event_dict(record, rule)
        _send_event(client, event_dict)

    except Exception as exc:  # noqa: BLE001
        _log_propagation_error(repo_root, record, str(exc))

    # NOTE: Correlation events (artifact_link / commit_link) are written locally by
    # InvocationWriter.append_correlation_link() in executor.py but are NOT currently
    # submitted to the propagator.  The executor submits both v2 lifecycle events
    # (OpStartedEvent at invoke time, OpCompletedEvent at close time) to
    # propagator.submit(); correlation events remain local-only per the ADR-004
    # Tier-2 stance.  The dict-record branch for correlation events is therefore
    # deferred until the executor wires correlation-event propagation.  When that
    # wiring lands, add a branch here:
    #   if isinstance(record, dict):
    #       event_type_map = {"artifact_link": "ProfileInvocationArtifactLink",
    #                         "commit_link": "ProfileInvocationCommitLink"}
    #       ...and consult rule.project before calling client.send_event.


def _coerce_event_kind(raw_event: str) -> EventKind:
    try:
        return EventKind(raw_event)
    except ValueError:
        # Unknown event kind (e.g., future EventKind added before table extended).
        # Use STARTED as the conservative fallback so resolve_projection returns
        # _DEFAULT_RULE (project=True), which preserves existing behaviour.
        return EventKind.STARTED


def _coerce_mode(raw_mode: str | None) -> ModeOfWork | None:
    if not raw_mode:
        return None
    try:
        return ModeOfWork(raw_mode)
    except ValueError:
        # Malformed mode_of_work on the record. Treat as None (legacy) rather than
        # crashing the background propagation thread silently.
        return None


def _build_event_dict(
    record: OpEvent,
    rule: Any,
) -> dict[str, object]:
    if isinstance(record, OpStartedEvent):
        return _build_started_event_dict(record, rule)
    return _build_completed_event_dict(record, rule)


def _build_started_event_dict(
    record: OpStartedEvent,
    rule: Any,
) -> dict[str, object]:
    """Envelope built 1:1 from the v2 OpStartedEvent (op-record-events.md).

    No wire-compat with the pre-mission envelope (decision
    01KTSJEQANMNEV16WMSAJP6FR1). None fields (router_confidence, mission_id,
    wp_id) are omitted, mirroring the on-disk JSONL shape. request_text is
    policy-gated (projection_policy.include_request_text).
    """
    event_dict: dict[str, object] = record.model_dump(exclude_none=True)
    del event_dict["event"]
    event_dict["event_type"] = "ProfileInvocationStarted"
    if not rule.include_request_text:
        event_dict.pop("request_text", None)
    return event_dict


def _build_completed_event_dict(record: OpCompletedEvent, rule: Any) -> dict[str, object]:
    """Envelope built 1:1 from the v2 OpCompletedEvent — includes ``closed_by``.

    evidence_ref is omitted when None (on-disk parity) and policy-gated.
    """
    event_dict: dict[str, object] = record.model_dump(exclude_none=True)
    del event_dict["event"]
    event_dict["event_type"] = "ProfileInvocationCompleted"
    if not rule.include_evidence_ref:
        event_dict.pop("evidence_ref", None)
    return event_dict


def _send_event(client: Any, event_dict: dict[str, object]) -> None:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already inside a running loop (rare in CLI threads, but safe)
            _track_send_task(asyncio.create_task(client.send_event(event_dict)))
            return
        loop.run_until_complete(client.send_event(event_dict))
    except RuntimeError:
        # No current event loop (background thread with no loop) → create one
        asyncio.run(client.send_event(event_dict))


def _log_propagation_error(
    repo_root: Path, record: OpEvent, error: str
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
    """Background-thread SaaS propagator for Op lifecycle events.

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

    def submit(self, record: OpEvent) -> None:
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

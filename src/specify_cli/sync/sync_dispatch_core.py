"""Pure dispatch batching + exit-code decisions for ``spec-kitty sync now`` (WP08).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``, WP08)
splits the ``sync now`` dispatch subsystem out of the single
``cli/commands/sync.py`` host into two cohesive seam modules:

* **this module** — the **pure** half. It owns the :class:`DispatchSummary`
  reductions (``_combine_dispatch_summaries``), the oversized-batch predicate
  (``_batch_is_oversized``), the transient-block message builder
  (``_transient_block_message``), and — the load-bearing extraction — the pure
  ``DispatchSummary | None`` + pending-work-signal → strict-exit **decision**
  (:func:`decide_sync_now_exit`). It is provably **I/O-free**: no ``Console``,
  no ``print``, no network, no filesystem, no SQLite. Every function takes
  already-read values and returns a value, a dataclass, or a
  :class:`SyncNowExitAction`, so the arithmetic that decides the strict
  ``sync now`` exit contract can be unit-tested directly (plan IC-03/IC-04).
* the sibling :mod:`specify_cli.sync.sync_dispatch_exec` owns the SaaSQueue
  delivery **executors** (``_run_dispatch_batches`` / ``_run_event_sync_dispatch``
  / receiver resolution) that touch the journal, ledger and network.

**Retiring the ``_enforce_sync_now_exit_from_dispatch`` complexity concentration
(INV-5).** The host wrapper previously interleaved the branchy
``DispatchSummary`` → exit mapping with the ``console.print`` /
``raise typer.Exit`` side effects. This module lifts the *decision* into
:func:`decide_sync_now_exit` (returns a :class:`SyncNowExitAction`, no I/O); the
host wrapper shrinks to a small dispatch over that action, applying the console
print + ``raise typer.Exit(code)`` — the only impure step. The pure decision is
unit-tested across every exit arm (delivered / nothing-pending / transient-block /
preflight-fail / unauthenticated / ``EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE``).

This is a **behavior-preserving** split (INV-1): the reduction / predicate /
message bodies are byte-identical to the inline forms they replaced in
``cli/commands/sync.py``, and :func:`decide_sync_now_exit` reproduces the exact
arm structure of the former ``_enforce_sync_now_exit_from_dispatch`` mapping. The
WP02 golden ``now`` exit arms are the guard; the new-code coverage is in
``tests/sync/test_sync_dispatch_core.py``.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.delivery.dispatcher import DispatchSummary


# HTTP 413 is how the SaaS sync ingress (Fly proxy + edge) rejects an
# over-cap batch; see apps/sync/limits.py (512 KiB decompressed ceiling).
_HTTP_PAYLOAD_TOO_LARGE = 413
# HTTP 412 is the SaaS compatibility handshake refusing the CLI's advertised
# protocol version (apps/sync/compatibility.py, keyed on
# ``X-SpecKitty-Protocol-Version``). Environment skew, not a per-event fault:
# the receiver maps it to a batch-wide ``transient`` and the batch driver HALTS
# the pass on it instead of POSTing the rest of the journal (#1553).
_HTTP_PRECONDITION_FAILED = 412
_OVERSIZED_ERROR_MARKER = "retry with a smaller batch"
_HTTP_AUTH_STATUSES = frozenset({401, 403})

_UNAUTHENTICATED_SYNC_NOW_MESSAGE = "not authenticated: no valid access token. Run `spec-kitty auth login`."
_OVERSIZED_SYNC_NOW_MESSAGE = "sync batch exceeded the server size limit; the CLI retried with smaller batches. Re-run `spec-kitty sync now` if events remain."
_TRANSIENT_SYNC_NOW_MESSAGE = "sync delivery failed transiently; no events were lost. Re-run `spec-kitty sync now` (see `--report` for per-event detail)."
_PROTOCOL_MISMATCH_SYNC_NOW_MESSAGE = (
    "sync delivery halted: the server rejected this CLI's sync protocol version (HTTP 412); "
    "no events were lost and none were parked. Follow the guidance above, then re-run `spec-kitty sync now`."
)
#: Printed by the command that hit the 412, followed by the server's own guidance.
_PROTOCOL_MISMATCH_HALT_NOTICE = (
    "Event sync halted: the server rejected this CLI's sync protocol version (HTTP 412); the remaining events were retained for the next run, not parked."
)


class SyncNowExitAction(Enum):
    """The pure verdict of the strict ``sync now`` exit-code decision.

    Each member names *what* the host wrapper must do; the wrapper owns the
    impure step (``console.print`` / ``raise typer.Exit`` / teamspace recovery):

    * :attr:`NONE` — nothing pending or nothing to report; the wrapper returns.
    * :attr:`EXIT_STRICT_FAILURE` — a strict-mode failure; the wrapper raises
      ``typer.Exit(1)``. Only ever returned when ``strict`` is set.
    * :attr:`HANDLE_UNAUTHENTICATED` — pending work that the dispatcher could not
      progress via a pure gate/auth block; the wrapper routes it through the
      teamspace-aware recovery (interactive login, structured exit 4 via
      ``EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE``, or legacy exit 1 under strict).
    * :attr:`TRANSIENT_BLOCK` — a wholesale-transient drain; the wrapper prints
      the classified :func:`_transient_block_message` and, under ``strict``,
      raises ``typer.Exit(1)``.
    * :attr:`ADMISSION_BLOCKED` — a gate/admission block (``admission_gated``),
      NOT a real 401/403 (#3620, Finding 2). The real reason was already
      printed by the exec layer (``_AdmissionGatedNoDelivery.reason``); the
      wrapper must NOT route this through unauthenticated recovery — it only
      honors ``strict`` (``typer.Exit(1)``) like :attr:`EXIT_STRICT_FAILURE`,
      without the misleading "not authenticated" message.
    """

    NONE = "none"
    EXIT_STRICT_FAILURE = "exit_strict_failure"
    HANDLE_UNAUTHENTICATED = "handle_unauthenticated"
    TRANSIENT_BLOCK = "transient_block"
    ADMISSION_BLOCKED = "admission_blocked"


def _combine_dispatch_summaries(left: DispatchSummary, right: DispatchSummary) -> DispatchSummary:
    from specify_cli.delivery.dispatcher import DispatchSummary

    return DispatchSummary(
        target_id=left.target_id or right.target_id,
        selected=left.selected + right.selected,
        delivered=left.delivered + right.delivered,
        duplicate=left.duplicate + right.duplicate,
        pending=left.pending + right.pending,
        rejected=left.rejected + right.rejected,
        transient=left.transient + right.transient,
        terminal_failed=left.terminal_failed + right.terminal_failed,
        failures=(*left.failures, *right.failures),
        retryable_event_ids=(
            *left.retryable_event_ids,
            *right.retryable_event_ids,
        ),
    )


def _is_wholesale_transient(summary: DispatchSummary) -> bool:
    """Whether every selected event of *summary* came back ``transient`` (one failure each)."""
    return bool(summary.selected > 0 and summary.transient == summary.selected and len(summary.failures) == summary.selected)


def _batch_is_oversized(summary: DispatchSummary) -> bool:
    """Whether a batch was rejected wholesale for exceeding the server size cap.

    The count-based batch limit cannot see decompressed byte size, so a backlog
    whose events fit the 1000-event limit can still crowd the SaaS 512 KiB
    ceiling (apps/sync/limits.py). The edge proxy answers HTTP 413 and the WP06
    receiver maps that to a batch-wide ``transient`` carrying the oversized
    error (``_BATCH_OVERSIZED_ERROR`` = "retry with a smaller batch"). This is
    the signal that we should honor that documented contract and shrink.
    """
    return _is_wholesale_transient(summary) and all(
        failure.outcome == "transient"
        and (failure.http_status == _HTTP_PAYLOAD_TOO_LARGE or (failure.error is not None and _OVERSIZED_ERROR_MARKER in failure.error.lower()))
        for failure in summary.failures
    )


def _batch_is_protocol_mismatch(summary: DispatchSummary) -> bool:
    """Whether a batch was refused wholesale by the server's protocol handshake (HTTP 412).

    The receiver maps a 412 to a batch-wide ``transient`` (retained, re-selectable)
    carrying the server's upgrade/pin guidance as the failure error. Unlike a 413
    the right reaction is neither to halve nor to skip-and-advance: every further
    POST this pass would get the same answer, so the batch driver halts the pass
    (#1553). Parking is never correct here — the skew is environmental, and a
    parked (``terminal_failed``) row is excluded from selection forever.
    """
    return _is_wholesale_transient(summary) and all(
        failure.outcome == "transient" and failure.http_status == _HTTP_PRECONDITION_FAILED for failure in summary.failures
    )


def _protocol_mismatch_guidance(summary: DispatchSummary) -> str | None:
    """The server's upgrade/pin guidance if a 412 halted this pass, else ``None``.

    Read off the first 412 failure so it is found even when earlier batches of the
    same pass delivered (the combined summary is then not wholesale-transient).
    """
    for failure in summary.failures:
        if failure.outcome == "transient" and failure.http_status == _HTTP_PRECONDITION_FAILED:
            error = failure.error
            return None if error is None else str(error)
    return None


def _transient_block_message(summary: DispatchSummary) -> str:
    """Explain a wholesale-transient drain accurately instead of always blaming auth.

    The legacy heuristic reported every all-transient batch as "not
    authenticated", which mislabels a 413 (batch too large), a 412 (protocol
    skew, #1553) or a 5xx as a logged-out session and sends operators chasing
    auth. Classify by the actual failure status instead.
    """
    statuses = {f.http_status for f in summary.failures if f.http_status is not None}
    if _HTTP_PRECONDITION_FAILED in statuses:
        return _PROTOCOL_MISMATCH_SYNC_NOW_MESSAGE
    if _HTTP_PAYLOAD_TOO_LARGE in statuses:
        return _OVERSIZED_SYNC_NOW_MESSAGE
    if statuses & _HTTP_AUTH_STATUSES:
        return _UNAUTHENTICATED_SYNC_NOW_MESSAGE
    return _TRANSIENT_SYNC_NOW_MESSAGE


def decide_sync_now_exit(
    strict: bool,
    queue_size: int,
    summary: DispatchSummary | None,
    *,
    retained_work_present: bool = False,
    intentional_no_delivery: bool = False,
    admission_gated: bool = False,
) -> SyncNowExitAction:
    """Map the dispatch outcome to the strict ``sync now`` exit **decision** (pure).

    This is the extracted decision core of the former
    ``_enforce_sync_now_exit_from_dispatch`` host wrapper: it takes the
    :class:`DispatchSummary` (or ``None`` when dispatch infrastructure was
    unavailable) plus the pending-work signal and returns the
    :class:`SyncNowExitAction` the host must apply. It performs **no I/O**; the
    ``console.print`` / ``raise typer.Exit`` / teamspace recovery all stay in the
    host wrapper.

    The journal-based dispatcher is the sole event-delivery path, so the legacy
    ``_enforce_sync_now_exit`` semantics are mapped onto its ``DispatchSummary``
    plus the pending-work signal. The base code drew a deliberate line between
    two unauthenticated shapes and this mapping keeps it:

    * The dispatcher *selected* events and attempted delivery but none
      progressed (every selected event came back rejected / transient /
      terminal-failed — a logged-out 401 maps the whole batch to ``transient``;
      see :mod:`specify_cli.delivery.receivers`). This is the dispatch analogue
      of the legacy per-event ``unauthenticated`` result → the *graceful*
      "unauthenticated / sync-blocked" report with exit 1 (Issue #829). It must
      NOT be reclassified as the "nothing attempted / blocked" teamspace-recovery
      case below.
    * There is pending work (a non-empty legacy queue, or events selected) but
      the dispatcher attempted *nothing* — the dispatch analogue of the legacy
      "queue non-empty but all-zero result". This is routed through the
      teamspace-aware recovery so the unauthenticated UX (interactive login,
      structured exit 4, legacy exit 1) is preserved regardless of ``strict``.
    * Partial progress with any rejected, transient, or terminal failure → exit
      1 under ``strict``.

    A ``None`` summary means dispatch infrastructure was unavailable. Under
    ``strict`` that is a failure only when retained or legacy work exists.

    ``admission_gated`` (#3620, Finding 2) narrows the two "nothing attempted"
    arms below: when the exec layer explicitly detected a gate/admission
    block (``_AdmissionGatedNoDelivery``) rather than a genuine 401/403, the
    verdict is :attr:`SyncNowExitAction.ADMISSION_BLOCKED` instead of
    :attr:`SyncNowExitAction.HANDLE_UNAUTHENTICATED`, so the host does not
    route it through unauthenticated recovery and print "not authenticated"
    for a problem that has nothing to do with the local session. The true
    401/403 path (``_HTTP_AUTH_STATUSES`` / :attr:`SyncNowExitAction.TRANSIENT_BLOCK`)
    is untouched by this parameter.
    """
    if summary is None:
        if strict and (queue_size > 0 or retained_work_present):
            return SyncNowExitAction.EXIT_STRICT_FAILURE
        return SyncNowExitAction.NONE

    selected = summary.selected
    progressed = summary.delivered + summary.duplicate + summary.pending

    if strict and retained_work_present and selected == 0 and not intentional_no_delivery:
        # A zero-selection summary does not prove the canonical store is empty;
        # gate/admission failures can produce this shape while retained reads are
        # unavailable. Only the dispatcher's explicit receiver=None outcome for
        # an operator-selected retention mode is a clean deliberate no-delivery;
        # unknown or refused selection remains a strict failure.
        return SyncNowExitAction.EXIT_STRICT_FAILURE

    # Selected work made no durable progress. A pure gate/auth block records no
    # rows, so route it through teamspace-aware recovery — UNLESS the exec
    # layer identified it as a gate/admission block rather than a real
    # unauthenticated shape (admission_gated, #3620 Finding 2). Transport/
    # content failures still use the legacy strict exit.
    if selected > 0 and progressed == 0 and summary.recorded == 0:
        return SyncNowExitAction.ADMISSION_BLOCKED if admission_gated else SyncNowExitAction.HANDLE_UNAUTHENTICATED
    if selected > 0 and progressed == 0 and summary.transient > 0:
        return SyncNowExitAction.TRANSIENT_BLOCK
    if selected > 0 and progressed == 0 and summary.recorded > 0:
        # Rejected and terminal-failed rows are concrete delivery outcomes, not
        # evidence that authentication blocked the attempt. Preserve --strict
        # semantics without sending the operator through auth recovery.
        return SyncNowExitAction.EXIT_STRICT_FAILURE if strict else SyncNowExitAction.NONE

    # Pending work but nothing was even attempted → teamspace-aware recovery,
    # unless it is the same admission_gated shape as above.
    work_present = queue_size > 0 or selected > 0
    if work_present and progressed == 0:
        return SyncNowExitAction.ADMISSION_BLOCKED if admission_gated else SyncNowExitAction.HANDLE_UNAUTHENTICATED
    errors = summary.rejected + summary.transient + summary.terminal_failed
    if strict and errors > 0:
        return SyncNowExitAction.EXIT_STRICT_FAILURE
    return SyncNowExitAction.NONE

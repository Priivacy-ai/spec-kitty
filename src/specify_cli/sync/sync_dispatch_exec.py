"""SaaSQueue delivery executors for ``spec-kitty sync now`` (WP08).

The **exec** half of the dispatch core/exec split (mission
``sync-cli-degod-wave4-01M0B0MX``, WP08). Everything here touches an I/O
boundary — the event journal, the delivery ledger, the WP06 receiver, the
network POST, or the operator ``Console`` — and so it is deliberately kept
**out** of the pure :mod:`specify_cli.sync.sync_dispatch_core`, which owns the
``DispatchSummary`` reductions, the oversized-batch predicate, the transient
message builder and the strict exit-code decision.

What lives here:

* **Receiver resolution** — ``_resolve_active_receiver`` (mode → WP06 receiver
  via ``EventSyncConfig.resolve``) and ``_resolve_gated_receiver`` (resolve +
  evaluate gates, data only). WP07 relocated the admission-authority *asserts*
  into :mod:`specify_cli.sync.sync_authority`; this WP relocates the delivery /
  receiver-resolution **execution** path. The gate-context builder
  (``_event_sync_gate_context``) stays on the host and is reached late-bound.
* **Batch driver** — ``_run_dispatch_batches``: the count-limit + byte-cap retry
  loop that drives ``delivery.dispatcher.dispatch`` until the selection drains.
* **The sole event-delivery path** — ``_run_event_sync_dispatch``: opens the
  project dispatch runtime, resolves the gated receiver, drives the batches and
  returns the ``DispatchSummary`` (or an ``_IntentionalNoDelivery`` wrapper, or
  ``None`` on infrastructure failure) for the host ``now`` shell to map onto the
  strict exit contract.

**Late-bound host access (INV-4 / WP03 convention).** The monkeypatch seam
callees these executors invoke — ``_EVENT_SYNC_DISPATCH_BATCH_LIMIT``,
``is_saas_sync_enabled``, ``_open_project_dispatch_runtime``,
``_load_event_sync_config``, ``_event_sync_access_token``,
``_resolve_active_receiver``, ``_resolve_gated_receiver`` — and the host-owned
helpers that stay put (``_event_sync_gate_context``,
``_count_project_retained_events``, ``_print_dispatch_summary``,
``_report_empty_selection``, ``_IntentionalNoDelivery``) are reached by ATTRIBUTE
ACCESS on the host module object (``sync_module.<name>``), never by an
early-bound ``from ...cli.commands.sync import <name>``. A
``monkeypatch.setattr("...cli.commands.sync.<name>", <double>)`` therefore still
intercepts. ``tests/architectural/test_sync_no_early_bind.py`` is the AST guard.

This is a **behavior-preserving** move (INV-1): every executor body is
byte-for-byte the inline form it replaced in ``cli/commands/sync.py``, save the
seam-callee dereferences rewritten to the ``sync_module.<name>`` late-bound form
and the typed-local absorption the strict-typed seam module requires (the host
is mypy strict-quarantined / ``Any``-typed; this module is not). The WP02 golden
``now`` arms + the ``sync``-monkeypatch suites are the guard.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from specify_cli.sync.sync_dispatch_core import (
    _HTTP_PAYLOAD_TOO_LARGE,
    _batch_is_oversized,
    _combine_dispatch_summaries,
)

_LOG = logging.getLogger(__name__)

if TYPE_CHECKING:
    from specify_cli.cli.commands.sync import _IntentionalNoDelivery
    from specify_cli.delivery.config import EventSyncConfig
    from specify_cli.delivery.dispatcher import DispatchSummary
    from specify_cli.delivery.receivers import DeliveryReceiver, GateDecision
    from specify_cli.sync.sync_runtime import _ProjectDispatchRuntime
    from specify_cli.sync.target_authority import ResolvedSyncTarget


def _resolve_active_receiver(target: ResolvedSyncTarget, config: EventSyncConfig, *, auth_token: str | None = None) -> DeliveryReceiver | None:
    """Resolve the WP06 receiver for the active mode via WP09 (or ``None``).

    Mode→receiver resolution is owned by ``EventSyncConfig.resolve``; the CLI
    only supplies the Teamspace Bearer token to the default factory.
    """
    import specify_cli.cli.commands.sync as sync_module
    from specify_cli.delivery.config import DefaultReceiverFactory

    token: str = sync_module._event_sync_access_token() if auth_token is None else auth_token
    factory = DefaultReceiverFactory(teamspace_auth_token=token)
    policy = config.resolve(resolved_target=target, receiver_factory=factory)
    receiver: DeliveryReceiver | None = policy.receiver
    return receiver


def _resolve_gated_receiver(target: ResolvedSyncTarget, config: EventSyncConfig, *, auth_token: str) -> tuple[DeliveryReceiver | None, GateDecision | None]:
    """Resolve the active receiver and evaluate its gates — data only, no policy.

    Shared by ``sync now`` (:func:`_run_event_sync_dispatch`) and
    ``import-history --apply`` (``_resolve_history_import_receiver``); the two
    callers previously duplicated this resolve+evaluate sequence and had already
    diverged (#2884 P2). Returns ``(None, None)`` when the mode has no receiver
    (retention-only). Otherwise returns the receiver and its
    :class:`GateDecision` — each caller decides what a blocked decision means:
    ``sync now`` degrades to a dim best-effort notice, ``import-history`` fails
    closed with ``typer.Exit(1)``. Neither policy lives here.
    """
    import specify_cli.cli.commands.sync as sync_module
    from specify_cli.delivery.receivers import evaluate_gates

    receiver: DeliveryReceiver | None = sync_module._resolve_active_receiver(target, config, auth_token=auth_token)
    if receiver is None:
        return None, None
    gate_decision: GateDecision = evaluate_gates(receiver, sync_module._event_sync_gate_context(receiver, target, auth_token=auth_token))
    return receiver, gate_decision


def _run_dispatch_batches(
    runtime: _ProjectDispatchRuntime,
    receiver: DeliveryReceiver,
    delivery_target: Any,
) -> DispatchSummary:
    import specify_cli.cli.commands.sync as sync_module
    from specify_cli.delivery.dispatcher import DispatchSummary, dispatch

    combined = DispatchSummary.empty()
    batch_limit: int = sync_module._EVENT_SYNC_DISPATCH_BATCH_LIMIT
    limit = batch_limit
    skip: set[str] = set()
    retry_no_effect: set[str] = set()
    while True:
        batch = dispatch(
            store=runtime.store,
            journal=None,
            ledger=None,
            receiver=receiver,
            target=delivery_target,
            context=runtime.context,
            limit=limit,
            exclude=frozenset(skip),
            recovery_event_ids=frozenset(retry_no_effect),
        )
        # Honor the documented "retry with a smaller batch" contract: a
        # byte-oversized batch (HTTP 413, nothing delivered) is halved and
        # retried rather than surrendered as transient. dispatch() leaves those
        # events undelivered, so the smaller re-selection picks the same events
        # up. A single oversized event is terminal-failed by the receiver (not
        # transient), so limit==1 can never loop forever.
        if limit > 1 and batch.delivered == 0 and _batch_is_oversized(batch):
            retry_no_effect.update(failure.event_id for failure in batch.failures)
            limit = max(1, limit // 2)
            continue
        combined = _combine_dispatch_summaries(combined, batch)
        retry_no_effect.difference_update(
            failure.event_id for failure in batch.failures if failure.outcome != "transient" or failure.http_status != _HTTP_PAYLOAD_TOO_LARGE
        )
        # Advance past retryable events that made no terminal-success this pass
        # (pending, content rejection, persistent transient). Skipping them for
        # the REST OF THIS PASS lets deliverable events behind them drain
        # instead of a poison batch halting the loop; the ledger keeps them
        # selectable for the next `sync now`, so retryability is preserved.
        before = len(skip)
        skip.update(batch.retryable_event_ids)
        skip.update(failure.event_id for failure in batch.failures if failure.outcome == "terminal_failed")
        terminal_progress = (batch.delivered + batch.duplicate + batch.terminal_failed) > 0
        # Grow a shrunk limit back after terminal progress. A single event over
        # the server byte cap forces `limit` down to 1 and is parked
        # (terminal_failed); without recovery the entire *healthy* tail would
        # then drain one-event-per-POST for the rest of the pass -- correct but
        # a throughput cliff. Multiplicative increase mirrors the halving and is
        # capped at the count default, so throughput recovers within a few
        # batches while the per-batch byte contract is still honored: an
        # over-grown batch simply 413s and re-halves, which is bounded.
        if terminal_progress and limit < batch_limit:
            limit = min(batch_limit, limit * 2)
        advanced = terminal_progress or len(skip) > before
        if batch.selected == 0 or not advanced:
            break
    return combined


def _run_event_sync_dispatch() -> DispatchSummary | _IntentionalNoDelivery | None:
    """Drive the WP07 dispatcher over the resolved active target.

    This is the SOLE event-delivery path for ``sync now`` (the destructive
    legacy offline-queue event drain is retired). Returns the
    :class:`DispatchSummary` so the caller can derive the strict exit code; any
    infrastructure failure degrades to a dim notice and ``None`` rather than
    crashing the command (NFR-006). An operator-selected mode with no receiver
    returns an explicit wrapper around an empty summary so strict handling can
    distinguish deliberate retention from gate/admission failure.
    Delivery outcomes surface via the printed summary; the journal is never
    deleted on success (FR-001).
    """
    import specify_cli.cli.commands.sync as sync_module
    from specify_cli.delivery.dispatcher import DispatchSummary

    if not sync_module.is_saas_sync_enabled():
        return DispatchSummary.empty()
    from specify_cli.delivery.config import Mode

    runtime: _ProjectDispatchRuntime | None = None
    try:
        opened: _ProjectDispatchRuntime = sync_module._open_project_dispatch_runtime()
        runtime = opened
        config: EventSyncConfig = sync_module._load_event_sync_config()
        auth_token: str = sync_module._event_sync_access_token()
        receiver: DeliveryReceiver | None = None
        gate_decision: GateDecision | None = None
        receiver, gate_decision = sync_module._resolve_gated_receiver(opened.target, config, auth_token=auth_token)
        if receiver is None:
            sync_module.console.print(f"[dim]Event sync mode {config.mode.name}: retention only; no delivery attempted.[/dim]")
            empty = DispatchSummary.empty()
            if config.mode is Mode.LOCAL_RETENTION:
                intentional: _IntentionalNoDelivery = sync_module._IntentionalNoDelivery(empty)
                return intentional
            return empty
        if gate_decision is None:
            # Invariant: a resolved (non-None) receiver always carries a
            # decision from _resolve_gated_receiver. An explicit raise (not
            # assert) keeps this guard live under `python -O`; the
            # surrounding `except Exception` still degrades it to a dim
            # notice + None, same as before (this function must never break
            # the command — NFR-006).
            raise RuntimeError("resolved receiver carries no gate decision")
        if gate_decision.blocked:
            names = ", ".join(gate.name for gate in gate_decision.unsatisfied)
            sync_module.console.print(f"[dim]Event sync gated: {names}[/dim]")
            gated_selected: int = sync_module._count_project_retained_events(opened)
            return DispatchSummary(
                target_id=None,
                selected=gated_selected,
                delivered=0,
                duplicate=0,
                pending=0,
                rejected=0,
                transient=0,
                terminal_failed=0,
            )
        delivery_target = opened.delivery_target
        if delivery_target is None:
            sync_module.console.print("[dim]Event sync gated: admission_not_current[/dim]")
            admission_selected: int = sync_module._count_project_retained_events(opened)
            return DispatchSummary(
                target_id=None,
                selected=admission_selected,
                delivered=0,
                duplicate=0,
                pending=0,
                rejected=0,
                transient=0,
                terminal_failed=0,
            )
        summary: DispatchSummary = sync_module._run_dispatch_batches(opened, receiver, delivery_target)
        sync_module._print_dispatch_summary(summary, config.mode.name)
        with opened.store.unit_of_work() as unit:
            from specify_cli.event_journal.journal import EventJournal

            sync_module._report_empty_selection(
                summary,
                EventJournal(unit, opened.store.layout_generation()),
            )
        return summary
    except Exception as exc:  # additive drain must never break the command
        _LOG.debug("event-sync dispatch skipped: %s", exc)
        sync_module.console.print(f"[dim]Event sync unavailable: {str(exc)[:80]}[/dim]")
        return None
    finally:
        if runtime is not None:
            runtime.close()

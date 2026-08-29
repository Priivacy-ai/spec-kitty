"""Unit coverage for the pure ``sync now`` dispatch core (WP08).

New-code coverage for :mod:`specify_cli.sync.sync_dispatch_core` — the pure half
of the WP08 dispatch split. Every function here is I/O-free, so the tests drive
it with direct stub inputs and assert exact values:

* :func:`decide_sync_now_exit` across **every** exit arm — delivered,
  nothing-pending, transient-block, unauthenticated (the graceful exit-1 shape),
  the ``EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE`` shape (which is
  ``HANDLE_UNAUTHENTICATED`` at the pure layer; the exit-4 vs exit-1 choice lives
  in the host recovery, exercised in the wrapper tests below), the retained-work
  strict failure, and the rejected/terminal strict failure.
* :func:`_combine_dispatch_summaries` identity + reduction.
* :func:`_batch_is_oversized` boundary.
* :func:`_transient_block_message` text classification.

The thinned host wrapper (``_enforce_sync_now_exit_from_dispatch``) is also
exercised here so the four :class:`SyncNowExitAction` outcomes are proven to map
to the correct side effect (``typer.Exit(1)``, teamspace recovery / exit 4, the
transient print), keeping the frozen ``now`` exit-code contract honest.
"""

from __future__ import annotations

import pytest
import typer

from specify_cli.delivery.dispatcher import DispatchFailure, DispatchSummary
from specify_cli.sync.sync_dispatch_core import (
    _OVERSIZED_SYNC_NOW_MESSAGE,
    _PROTOCOL_MISMATCH_SYNC_NOW_MESSAGE,
    _TRANSIENT_SYNC_NOW_MESSAGE,
    _UNAUTHENTICATED_SYNC_NOW_MESSAGE,
    SyncNowExitAction,
    _batch_is_oversized,
    _batch_is_protocol_mismatch,
    _combine_dispatch_summaries,
    _protocol_mismatch_guidance,
    _transient_block_message,
    decide_sync_now_exit,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def _summary(
    *,
    selected: int = 0,
    delivered: int = 0,
    duplicate: int = 0,
    pending: int = 0,
    rejected: int = 0,
    transient: int = 0,
    terminal_failed: int = 0,
    failures: tuple[DispatchFailure, ...] = (),
    target_id: str | None = None,
    retryable_event_ids: tuple[str, ...] = (),
) -> DispatchSummary:
    return DispatchSummary(
        target_id=target_id,
        selected=selected,
        delivered=delivered,
        duplicate=duplicate,
        pending=pending,
        rejected=rejected,
        transient=transient,
        terminal_failed=terminal_failed,
        failures=failures,
        retryable_event_ids=retryable_event_ids,
    )


# --------------------------------------------------------------------------- #
# decide_sync_now_exit — every arm                                            #
# --------------------------------------------------------------------------- #


class TestDecideSyncNowExit:
    def test_none_summary_strict_with_queue_is_strict_failure(self) -> None:
        assert decide_sync_now_exit(True, 3, None) is SyncNowExitAction.EXIT_STRICT_FAILURE

    def test_none_summary_strict_with_retained_is_strict_failure(self) -> None:
        assert decide_sync_now_exit(True, 0, None, retained_work_present=True) is SyncNowExitAction.EXIT_STRICT_FAILURE

    def test_none_summary_strict_no_work_is_none(self) -> None:
        assert decide_sync_now_exit(True, 0, None) is SyncNowExitAction.NONE

    def test_none_summary_not_strict_is_none(self) -> None:
        assert decide_sync_now_exit(False, 9, None, retained_work_present=True) is SyncNowExitAction.NONE

    def test_delivered_happy_path_is_none(self) -> None:
        summary = _summary(selected=2, delivered=2)
        assert decide_sync_now_exit(True, 0, summary) is SyncNowExitAction.NONE

    def test_nothing_pending_empty_selection_is_none(self) -> None:
        assert decide_sync_now_exit(True, 0, DispatchSummary.empty()) is SyncNowExitAction.NONE

    def test_retained_work_zero_selection_strict_is_strict_failure(self) -> None:
        # Gate/admission failure shape: strict + retained present + selected 0 +
        # not a deliberate no-delivery → strict failure.
        assert decide_sync_now_exit(True, 0, DispatchSummary.empty(), retained_work_present=True) is SyncNowExitAction.EXIT_STRICT_FAILURE

    def test_intentional_no_delivery_empty_is_none(self) -> None:
        # Deliberate retention with an empty summary and no queue is clean.
        assert (
            decide_sync_now_exit(
                True,
                0,
                DispatchSummary.empty(),
                retained_work_present=True,
                intentional_no_delivery=True,
            )
            is SyncNowExitAction.NONE
        )

    def test_selected_no_progress_no_records_is_unauthenticated(self) -> None:
        # The graceful "unauthenticated / sync-blocked" shape (Issue #829): pure
        # gate/auth block records no rows.
        summary = _summary(selected=4)
        assert decide_sync_now_exit(True, 0, summary) is SyncNowExitAction.HANDLE_UNAUTHENTICATED

    def test_logged_out_401_batch_is_transient_block(self) -> None:
        # A logged-out 401 maps the whole batch to transient (recorded > 0), so
        # at the pure layer it is the transient-block arm; the classified message
        # (_transient_block_message) then names the 401 as "not authenticated".
        summary = _summary(
            selected=2,
            transient=2,
            failures=(
                DispatchFailure(event_id="e1", outcome="transient", http_status=401),
                DispatchFailure(event_id="e2", outcome="transient", http_status=401),
            ),
        )
        # transient > 0 with recorded > 0 and no progress → transient-block arm.
        assert decide_sync_now_exit(True, 0, summary) is SyncNowExitAction.TRANSIENT_BLOCK

    def test_selected_no_progress_transient_is_transient_block(self) -> None:
        summary = _summary(selected=1, transient=1)
        assert decide_sync_now_exit(True, 0, summary) is SyncNowExitAction.TRANSIENT_BLOCK

    def test_selected_no_progress_recorded_rejected_strict_is_strict_failure(self) -> None:
        summary = _summary(selected=1, rejected=1)
        assert decide_sync_now_exit(True, 0, summary) is SyncNowExitAction.EXIT_STRICT_FAILURE

    def test_selected_no_progress_recorded_rejected_not_strict_is_none(self) -> None:
        summary = _summary(selected=1, rejected=1)
        assert decide_sync_now_exit(False, 0, summary) is SyncNowExitAction.NONE

    def test_pending_queue_nothing_attempted_is_unauthenticated(self) -> None:
        # Legacy queue non-empty but the dispatcher attempted nothing (empty
        # summary) → teamspace-aware recovery.
        assert decide_sync_now_exit(True, 5, DispatchSummary.empty()) is SyncNowExitAction.HANDLE_UNAUTHENTICATED

    def test_partial_progress_with_errors_strict_is_strict_failure(self) -> None:
        summary = _summary(selected=3, delivered=1, transient=2)
        assert decide_sync_now_exit(True, 0, summary) is SyncNowExitAction.EXIT_STRICT_FAILURE

    def test_partial_progress_with_errors_not_strict_is_none(self) -> None:
        summary = _summary(selected=3, delivered=1, transient=2)
        assert decide_sync_now_exit(False, 0, summary) is SyncNowExitAction.NONE

    # ----------------------------------------------------------------- #
    # admission_gated (#3620 Finding 2 + AC-9 regression guard)         #
    # ----------------------------------------------------------------- #

    def test_admission_gated_zero_recorded_is_admission_blocked_not_unauthenticated(self) -> None:
        # Same shape as test_selected_no_progress_no_records_is_unauthenticated
        # (a pure gate/admission block records no rows) but admission_gated=True
        # means the exec layer identified it as a gate/admission block, not a
        # real 401/403 — so the verdict must NOT be HANDLE_UNAUTHENTICATED.
        summary = _summary(selected=4)
        assert decide_sync_now_exit(True, 0, summary, admission_gated=True) is SyncNowExitAction.ADMISSION_BLOCKED

    def test_admission_gated_pending_nothing_attempted_is_admission_blocked(self) -> None:
        assert decide_sync_now_exit(True, 5, DispatchSummary.empty(), admission_gated=True) is SyncNowExitAction.ADMISSION_BLOCKED

    def test_admission_gated_false_preserves_legacy_unauthenticated_routing(self) -> None:
        # AC-9 regression guard, direction 1: without the marker, the legacy
        # "nothing attempted" shape still routes through teamspace-aware
        # recovery — admission_gated must never become the default behavior.
        summary = _summary(selected=4)
        assert decide_sync_now_exit(True, 0, summary, admission_gated=False) is SyncNowExitAction.HANDLE_UNAUTHENTICATED

    def test_genuine_401_batch_stays_transient_block_even_when_admission_gated(self) -> None:
        # AC-9 regression guard, direction 2 (Finding 2's other half): a REAL
        # 401/403 must never be relabeled as admission_blocked, even if a
        # caller mistakenly passed admission_gated=True. The transient-with-
        # recorded-rows shape takes precedence over the zero-recorded arm this
        # parameter touches, so genuine auth failures are untouched by design.
        summary = _summary(
            selected=2,
            transient=2,
            failures=(
                DispatchFailure(event_id="e1", outcome="transient", http_status=401),
                DispatchFailure(event_id="e2", outcome="transient", http_status=401),
            ),
        )
        assert decide_sync_now_exit(True, 0, summary, admission_gated=True) is SyncNowExitAction.TRANSIENT_BLOCK


# --------------------------------------------------------------------------- #
# _combine_dispatch_summaries                                                 #
# --------------------------------------------------------------------------- #


class TestCombineDispatchSummaries:
    def test_empty_is_identity(self) -> None:
        right = _summary(selected=3, delivered=2, pending=1, target_id="t1")
        combined = _combine_dispatch_summaries(DispatchSummary.empty(), right)
        assert combined.selected == 3
        assert combined.delivered == 2
        assert combined.pending == 1
        assert combined.target_id == "t1"

    def test_reduces_all_fields_and_tuples(self) -> None:
        f1 = DispatchFailure(event_id="a", outcome="rejected")
        f2 = DispatchFailure(event_id="b", outcome="transient", http_status=503)
        left = _summary(selected=2, delivered=1, rejected=1, failures=(f1,), retryable_event_ids=("a",), target_id="L")
        right = _summary(selected=3, delivered=1, transient=1, terminal_failed=1, failures=(f2,), retryable_event_ids=("b",), target_id="R")
        combined = _combine_dispatch_summaries(left, right)
        assert combined.selected == 5
        assert combined.delivered == 2
        assert combined.rejected == 1
        assert combined.transient == 1
        assert combined.terminal_failed == 1
        assert combined.failures == (f1, f2)
        assert combined.retryable_event_ids == ("a", "b")
        # target_id keeps the first non-empty (left).
        assert combined.target_id == "L"


# --------------------------------------------------------------------------- #
# _batch_is_oversized                                                         #
# --------------------------------------------------------------------------- #


class TestBatchIsOversized:
    def test_wholesale_413_transient_is_oversized(self) -> None:
        failures = tuple(DispatchFailure(event_id=f"e{i}", outcome="transient", http_status=413) for i in range(2))
        assert _batch_is_oversized(_summary(selected=2, transient=2, failures=failures)) is True

    def test_wholesale_transient_by_error_marker_is_oversized(self) -> None:
        failures = (DispatchFailure(event_id="e0", outcome="transient", error="Please retry with a smaller batch."),)
        assert _batch_is_oversized(_summary(selected=1, transient=1, failures=failures)) is True

    def test_partial_413_is_not_oversized(self) -> None:
        # Only one of two selected came back transient → not wholesale.
        failures = (DispatchFailure(event_id="e0", outcome="transient", http_status=413),)
        assert _batch_is_oversized(_summary(selected=2, transient=1, failures=failures)) is False

    def test_content_rejection_is_not_oversized(self) -> None:
        failures = tuple(DispatchFailure(event_id=f"e{i}", outcome="transient", http_status=500) for i in range(2))
        assert _batch_is_oversized(_summary(selected=2, transient=2, failures=failures)) is False

    def test_empty_batch_is_not_oversized(self) -> None:
        assert _batch_is_oversized(DispatchSummary.empty()) is False


# --------------------------------------------------------------------------- #
# _batch_is_protocol_mismatch / _protocol_mismatch_guidance (#1553)           #
# --------------------------------------------------------------------------- #


def _mismatch_failures(count: int, *, error: str | None = "Run `spec-kitty upgrade` to update to a supported release.") -> tuple[DispatchFailure, ...]:
    return tuple(DispatchFailure(event_id=f"e{i}", outcome="transient", http_status=412, error=error) for i in range(count))


class TestBatchIsProtocolMismatch:
    def test_wholesale_412_transient_is_protocol_mismatch(self) -> None:
        assert _batch_is_protocol_mismatch(_summary(selected=2, transient=2, failures=_mismatch_failures(2))) is True

    def test_412_with_local_terminal_failure_is_protocol_mismatch(self) -> None:
        summary = _summary(
            selected=2,
            transient=1,
            terminal_failed=1,
            failures=(
                *_mismatch_failures(1),
                DispatchFailure(event_id="local", outcome="terminal_failed"),
            ),
        )
        assert _batch_is_protocol_mismatch(summary) is True

    def test_wholesale_413_is_not_protocol_mismatch(self) -> None:
        failures = tuple(DispatchFailure(event_id=f"e{i}", outcome="transient", http_status=413) for i in range(2))
        assert _batch_is_protocol_mismatch(_summary(selected=2, transient=2, failures=failures)) is False
        # ...and the two wholesale predicates never both fire for one batch.
        assert _batch_is_oversized(_summary(selected=2, transient=2, failures=_mismatch_failures(2))) is False

    def test_empty_batch_is_not_protocol_mismatch(self) -> None:
        assert _batch_is_protocol_mismatch(DispatchSummary.empty()) is False


class TestProtocolMismatchGuidance:
    def test_surfaces_the_server_guidance_from_the_first_412_failure(self) -> None:
        summary = _summary(selected=2, transient=2, failures=_mismatch_failures(2))
        assert _protocol_mismatch_guidance(summary) == "Run `spec-kitty upgrade` to update to a supported release."

    def test_found_even_after_partial_progress_in_the_same_pass(self) -> None:
        # Earlier batches delivered, then the 412 halted the pass: the combined
        # summary is not wholesale-transient, but the guidance must still surface.
        delivered = _summary(selected=3, delivered=3)
        halted = _summary(selected=2, transient=2, failures=_mismatch_failures(2, error="Pin spec-kitty to a supported release."))
        combined = _combine_dispatch_summaries(delivered, halted)
        assert _protocol_mismatch_guidance(combined) == "Pin spec-kitty to a supported release."

    def test_none_when_no_412_failure(self) -> None:
        failures = (DispatchFailure(event_id="e0", outcome="transient", http_status=503, error="boom"),)
        assert _protocol_mismatch_guidance(_summary(selected=1, transient=1, failures=failures)) is None
        assert _protocol_mismatch_guidance(DispatchSummary.empty()) is None


# --------------------------------------------------------------------------- #
# _transient_block_message                                                    #
# --------------------------------------------------------------------------- #


class TestTransientBlockMessage:
    def test_413_reports_oversized(self) -> None:
        failures = (DispatchFailure(event_id="e0", outcome="transient", http_status=413),)
        assert _transient_block_message(_summary(selected=1, transient=1, failures=failures)) == _OVERSIZED_SYNC_NOW_MESSAGE

    def test_auth_status_reports_unauthenticated(self) -> None:
        failures = (DispatchFailure(event_id="e0", outcome="transient", http_status=401),)
        assert _transient_block_message(_summary(selected=1, transient=1, failures=failures)) == _UNAUTHENTICATED_SYNC_NOW_MESSAGE

    def test_412_reports_protocol_mismatch_not_auth(self) -> None:
        # A halted-on-412 pass is a wholesale-transient drain; it must not be
        # relabeled "not authenticated" nor "batch too large".
        assert _transient_block_message(_summary(selected=2, transient=2, failures=_mismatch_failures(2))) == _PROTOCOL_MISMATCH_SYNC_NOW_MESSAGE

    def test_other_status_reports_generic_transient(self) -> None:
        failures = (DispatchFailure(event_id="e0", outcome="transient", http_status=503),)
        assert _transient_block_message(_summary(selected=1, transient=1, failures=failures)) == _TRANSIENT_SYNC_NOW_MESSAGE

    def test_no_status_reports_generic_transient(self) -> None:
        failures = (DispatchFailure(event_id="e0", outcome="transient", error="socket hang up"),)
        assert _transient_block_message(_summary(selected=1, transient=1, failures=failures)) == _TRANSIENT_SYNC_NOW_MESSAGE


# --------------------------------------------------------------------------- #
# Host wrapper — SyncNowExitAction → side-effect translation (frozen contract) #
# --------------------------------------------------------------------------- #


class TestEnforceSyncNowExitWrapper:
    """The thinned host wrapper maps each pure action to the right side effect."""

    def test_none_action_returns_without_raise(self) -> None:
        import specify_cli.cli.commands.sync as sync_module

        # Delivered happy path → NONE → no raise.
        sync_module._enforce_sync_now_exit_from_dispatch(True, 0, _summary(selected=1, delivered=1))

    def test_strict_failure_action_raises_exit_1(self) -> None:
        import specify_cli.cli.commands.sync as sync_module

        with pytest.raises(typer.Exit) as exc:
            sync_module._enforce_sync_now_exit_from_dispatch(True, 0, _summary(selected=1, rejected=1))
        assert exc.value.exit_code == 1

    def test_transient_block_action_prints_and_raises_under_strict(self) -> None:
        import specify_cli.cli.commands.sync as sync_module

        summary = _summary(selected=1, transient=1)
        with pytest.raises(typer.Exit) as exc:
            sync_module._enforce_sync_now_exit_from_dispatch(True, 0, summary)
        assert exc.value.exit_code == 1

    def test_transient_block_action_not_strict_prints_no_raise(self) -> None:
        import specify_cli.cli.commands.sync as sync_module

        # No raise under --no-strict; the classified message still prints.
        sync_module._enforce_sync_now_exit_from_dispatch(False, 0, _summary(selected=1, transient=1))

    def test_unauthenticated_action_delegates_to_recovery(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import specify_cli.cli.commands.sync as sync_module

        calls: list[bool] = []
        monkeypatch.setattr(sync_module, "_handle_sync_now_unauthenticated", lambda strict: calls.append(strict))
        # selected>0, no progress, no records → HANDLE_UNAUTHENTICATED.
        sync_module._enforce_sync_now_exit_from_dispatch(True, 0, _summary(selected=4))
        assert calls == [True]

    def test_admission_blocked_action_never_calls_unauthenticated_recovery(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # #3620 Finding 2: the same "selected>0, no progress, no records" shape
        # as the unauthenticated test above, but admission_gated=True. The
        # wrapper must NOT print/route the "not authenticated" message — that
        # is exactly the misreport this fix closes.
        import specify_cli.cli.commands.sync as sync_module

        calls: list[bool] = []
        monkeypatch.setattr(sync_module, "_handle_sync_now_unauthenticated", lambda strict: calls.append(strict))
        with pytest.raises(typer.Exit) as exc:
            sync_module._enforce_sync_now_exit_from_dispatch(True, 0, _summary(selected=4), admission_gated=True)
        assert exc.value.exit_code == 1
        assert calls == [], "admission_gated must never route through unauthenticated recovery"

    def test_admission_blocked_action_not_strict_returns_without_raise(self) -> None:
        import specify_cli.cli.commands.sync as sync_module

        # Under --no-strict, an admission-gated block is reported (by the exec
        # layer, upstream) but does not raise.
        sync_module._enforce_sync_now_exit_from_dispatch(False, 0, _summary(selected=4), admission_gated=True)

    def test_logged_out_on_connected_teamspace_raises_exit_4(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import specify_cli.cli.commands.sync as sync_module
        from specify_cli.cli.commands._auth_recovery import (
            EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE,
            RecoveryOutcome,
        )

        # Drive the real recovery with a stubbed teamspace outcome so the wrapper
        # → recovery → structured exit-4 arm (contract item 5) is exercised end
        # to end. The pending-queue/no-attempt shape routes to recovery.
        monkeypatch.setattr(
            sync_module,
            "handle_unauthenticated_with_teamspace",
            lambda **_kwargs: RecoveryOutcome.EXIT_4,
        )
        with pytest.raises(typer.Exit) as exc:
            sync_module._enforce_sync_now_exit_from_dispatch(True, 7, DispatchSummary.empty())
        assert exc.value.exit_code == EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE

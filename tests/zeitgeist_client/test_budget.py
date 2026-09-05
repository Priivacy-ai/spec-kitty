"""Z1-T1 §3.2 item 5: budget.py — 750ms offer budget nested inside the
existing 4.0s hook-wide HOOK_BUDGET_S.

``run_with_deadline`` is the primitive N3 depends on: a TOTAL wall-clock
bound on a callable regardless of what it is internally blocked on (a slow
TCP drip defeats a bare ``socket``/``urlopen`` per-operation timeout — see
zeitgeist/integrations/client_budget.py's own docstring for the measured
87s/89s stalls this pattern exists to prevent). It runs the callable in a
daemon worker thread and returns as soon as the deadline elapses, whether or
not the worker has finished.
"""

from __future__ import annotations

import time

import pytest

from specify_cli.zeitgeist_client import budget

# See tests/zeitgeist_client/test_grammar.py's pytestmark comment.
pytestmark = pytest.mark.fast


def test_offer_budget_s_is_750ms():
    assert budget.OFFER_BUDGET_S == 0.75


def test_hook_budget_s_is_4_seconds_unchanged_from_zeitgeist():
    # zeitgeist/integrations/client_budget.py HOOK_BUDGET_S
    assert budget.HOOK_BUDGET_S == 4.0


def test_offer_budget_nests_inside_hook_budget_with_margin():
    assert budget.OFFER_BUDGET_S < budget.HOOK_BUDGET_S
    # comfortable margin for git/spool work after the offer step completes
    assert budget.HOOK_BUDGET_S - budget.OFFER_BUDGET_S >= 1.0


def test_run_with_deadline_returns_completed_result_when_fast():
    outcome = budget.run_with_deadline(lambda: 42, deadline_s=0.75)
    assert outcome.completed is True
    assert outcome.result == 42
    assert outcome.error is None
    assert outcome.elapsed_s < 0.75


def test_run_with_deadline_times_out_on_a_slow_callable():
    def _slow():
        time.sleep(2.0)
        return "too-late"

    start = time.monotonic()
    outcome = budget.run_with_deadline(_slow, deadline_s=0.1)
    elapsed = time.monotonic() - start
    assert outcome.completed is False
    assert outcome.result is None
    # returns at ~the deadline, not after the slow callable finishes
    assert elapsed < 1.0
    assert 0.05 <= outcome.elapsed_s <= 0.5


def test_run_with_deadline_propagates_exception_when_completed():
    def _boom():
        raise ValueError("kaboom")

    outcome = budget.run_with_deadline(_boom, deadline_s=0.75)
    assert outcome.completed is True
    assert isinstance(outcome.error, ValueError)
    assert outcome.result is None

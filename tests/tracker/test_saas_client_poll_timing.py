"""Timing contract of ``_poll_operation`` — deterministic, seam-based.

Reinstates the coverage the retired ``TestPolling`` interval/timeout tests
carried, WITHOUT their failure mode: those tests patched the stdlib
``time.sleep`` process-wide (``@patch("...saas_client.time.sleep")``), whose
call recorder counted sleeps from any live thread in the worker process and
went red under ``--dist loadfile`` pollution (#3115 — 71 and 556 recorded
calls against expected 3 and 1). The #3187 instance-scoped seams exist for
exactly this test: ``client._sleep`` and ``jitter_randbelow`` are per-instance
attributes, so nothing outside the client under test can touch the recorder.

Pinned contract (`saas_client.py` poll tail):

* base delay 1.0s, doubling per iteration, capped at 30s;
* each sleep is ``min(delay, 30) * jitter`` with jitter in ``[0.8, 1.2)``
  derived from ``_randbelow(4000) / 10000 + 0.8``;
* when the next sleep would meet or exceed the remaining transport budget the
  loop refuses with ``recovery_required`` instead of sleeping past the
  transport deadline.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from kernel.clock import now_utc, timedelta

from specify_cli.tracker import saas_client as saas_client_module
from specify_cli.tracker.saas_client import SaaSTrackerClientError


def _deadline() -> Any:
    return now_utc() + timedelta(seconds=3600)


pytestmark = [pytest.mark.fast]

_OPERATION_ID = "op-poll-timing"


def _running_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={"operation_id": _OPERATION_ID, "status": "running"},
        request=httpx.Request("GET", "http://testserver/operations"),
    )


def _completed_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "operation_id": _OPERATION_ID,
            "status": "completed",
            "result": {"ok": True},
        },
        request=httpx.Request("GET", "http://testserver/operations"),
    )


def _poll(monkeypatch: pytest.MonkeyPatch, *, running_polls: int, remaining_seconds: float) -> tuple[list[float], Any]:
    """Drive the real poll loop with instance-scoped seams only.

    Returns the recorded per-iteration sleep durations and either the terminal
    response or the raised ``SaaSTrackerClientError``.
    """
    client = SaaSTrackerClientHarness()
    sleeps: list[float] = []
    client._sleep = sleeps.append
    client._randbelow = lambda _n: 2000  # jitter factor pinned to exactly 1.0

    responses = [_running_response() for _ in range(running_polls)] + [_completed_response()]

    def _fake_query(*args: Any, **kwargs: Any) -> httpx.Response:
        del args, kwargs
        return responses.pop(0)

    monkeypatch.setattr(type(client), "_physical_request_with_retry", _fake_query)
    monkeypatch.setattr(
        type(client),
        "_remaining_transport_seconds",
        lambda self, deadline, monotonic_deadline: remaining_seconds,
    )

    try:
        value = client._poll_operation(
            authority=None,
            operation_id=_OPERATION_ID,
            method="POST",
            path="/api/v1/tracker/bind/",
            deadline=_deadline(),
            monotonic_deadline=0.0,
        )
    except SaaSTrackerClientError as exc:
        return sleeps, exc
    return sleeps, value


class SaaSTrackerClientHarness(saas_client_module.SaaSTrackerClient):
    """Bypass __init__ (network/config wiring); the loop touches seams only."""

    def __init__(self) -> None:  # noqa: D401 - deliberate minimal construction
        self._base_url = "http://testserver"
        self._sleep = lambda _s: None
        self._randbelow = lambda _n: 2000


def test_backoff_doubles_from_one_second_and_every_interval_is_jittered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps, value = _poll(monkeypatch, running_polls=4, remaining_seconds=3600.0)

    assert isinstance(value, httpx.Response) and value.status_code == 200
    assert sleeps == [1.0, 2.0, 4.0, 8.0], "base 1.0s doubling per still-running poll (jitter pinned to 1.0)"


def test_backoff_interval_is_capped_at_thirty_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps, value = _poll(monkeypatch, running_polls=7, remaining_seconds=3600.0)

    assert isinstance(value, httpx.Response)
    assert sleeps == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0], "delay saturates at the 30s cap"


def test_jitter_scales_the_interval_within_its_documented_band(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_sleeps: list[float] = []

    def run(randbelow_value: int) -> list[float]:
        client = SaaSTrackerClientHarness()
        sleeps: list[float] = []
        client._sleep = sleeps.append
        client._randbelow = lambda _n: randbelow_value
        responses = [_running_response(), _completed_response()]
        monkeypatch.setattr(
            type(client),
            "_physical_request_with_retry",
            lambda *args, **kwargs: responses.pop(0),
        )
        monkeypatch.setattr(
            type(client),
            "_remaining_transport_seconds",
            lambda self, deadline, monotonic_deadline: 3600.0,
        )
        client._poll_operation(
            authority=None,
            operation_id=_OPERATION_ID,
            method="POST",
            path="/api/v1/tracker/bind/",
            deadline=_deadline(),
            monotonic_deadline=0.0,
        )
        return sleeps

    assert run(0) == [pytest.approx(0.8)], "randbelow=0 -> jitter floor 0.8"
    assert run(3999) == [pytest.approx(1.1999)], "randbelow=3999 -> just under the 1.2 ceiling"
    del client_sleeps


def test_deadline_refuses_instead_of_sleeping_past_the_persisted_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The would-be first sleep (1.0s) meets the remaining budget — no sleep, refusal."""
    sleeps, error = _poll(monkeypatch, running_polls=1, remaining_seconds=1.0)

    assert sleeps == [], "the loop must refuse rather than start a sleep it cannot afford"
    assert isinstance(error, SaaSTrackerClientError)
    assert error.error_code == "recovery_required"
    assert "deadline" in str(error)

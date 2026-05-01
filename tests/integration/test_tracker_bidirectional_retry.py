"""Integration test: tracker bidirectional sync retry semantics (FR-031, T037).

Drives :func:`run_bidirectional_sync_with_retry` against a synthetic
``sync_call`` that simulates the tracker connector. We verify:

* fail-3-then-succeed → 4 total attempts, returns success.
* fail-forever → :class:`TrackerSyncFailed` after the retry budget is
  exhausted, with structured ``retry_history`` entries.
* wall-clock cap → loop terminates before ``max_retries`` when the
  total budget would be exceeded.
* non-retryable predicate → fail-fast with a single
  :class:`TrackerSyncFailed`.
"""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.sync.tracker_client_glue import (
    TrackerSyncFailed,
    TrackerSyncPolicy,
    run_bidirectional_sync_with_retry,
)


class _FakeHTTPError(RuntimeError):
    """Synthetic connector exception with HTTP-style attributes."""

    def __init__(self, message: str, *, status_code: int = 503, body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _no_jitter_policy(**overrides: Any) -> TrackerSyncPolicy:
    base: dict[str, Any] = {
        "max_retries": 5,
        "max_backoff_seconds": 30.0,
        "total_timeout_seconds": 300.0,
        "initial_backoff_seconds": 1.0,
        "backoff_multiplier": 2.0,
        "jitter": False,
    }
    base.update(overrides)
    return TrackerSyncPolicy(**base)


class _FakeClock:
    """Monotonic clock that advances only when sleep() is called."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def monotonic(self) -> float:
        return self.now


class TestTrackerBidirectionalRetry:
    """FR-031: bounded retries, structured failure, no silent infinite retry."""

    def test_fail_three_then_succeed(self) -> None:
        clock = _FakeClock()
        attempts = {"count": 0}

        def sync_call() -> str:
            attempts["count"] += 1
            if attempts["count"] <= 3:
                raise _FakeHTTPError("transient", status_code=503, body="Try again")
            return "ok"

        result = run_bidirectional_sync_with_retry(
            sync_call,
            policy=_no_jitter_policy(),
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )

        assert result == "ok"
        assert attempts["count"] == 4
        # Three sleeps, exponential 1, 2, 4.
        assert clock.sleeps == [1.0, 2.0, 4.0]

    def test_fail_forever_raises_after_retries(self) -> None:
        clock = _FakeClock()

        def sync_call() -> None:
            raise _FakeHTTPError("forever", status_code=500, body="boom")

        with pytest.raises(TrackerSyncFailed) as exc_info:
            run_bidirectional_sync_with_retry(
                sync_call,
                policy=_no_jitter_policy(max_retries=5),
                sleep=clock.sleep,
                monotonic=clock.monotonic,
            )

        err = exc_info.value
        assert err.error_code == "tracker_sync_failed"
        # Five attempts, five history entries.
        assert len(err.retry_history) == 5
        # Every history record has the structured cause chain fields.
        for entry in err.retry_history:
            assert entry.error_type == "_FakeHTTPError"
            assert entry.http_status == 500
            assert entry.body_excerpt == "boom"
        # Last error is preserved on the exception too.
        assert isinstance(err.last_error, _FakeHTTPError)

    def test_wall_clock_cap_short_circuits(self) -> None:
        clock = _FakeClock()

        def sync_call() -> None:
            raise _FakeHTTPError("slow", status_code=502)

        # Tight wall-clock cap + slow backoff floor → cap hits before
        # max_retries.
        policy = _no_jitter_policy(
            max_retries=20,
            initial_backoff_seconds=10.0,
            max_backoff_seconds=10.0,
            total_timeout_seconds=15.0,
        )

        with pytest.raises(TrackerSyncFailed) as exc_info:
            run_bidirectional_sync_with_retry(
                sync_call,
                policy=policy,
                sleep=clock.sleep,
                monotonic=clock.monotonic,
            )
        err = exc_info.value
        assert "wall-clock cap" in str(err)
        # Sanity: didn't reach max_retries.
        assert len(err.retry_history) < policy.max_retries

    def test_non_retryable_short_circuits(self) -> None:
        clock = _FakeClock()
        attempts = {"count": 0}

        class _AuthError(RuntimeError):
            pass

        def sync_call() -> None:
            attempts["count"] += 1
            raise _AuthError("permission denied")

        def is_retryable(exc: BaseException) -> bool:
            return not isinstance(exc, _AuthError)

        with pytest.raises(TrackerSyncFailed) as exc_info:
            run_bidirectional_sync_with_retry(
                sync_call,
                policy=_no_jitter_policy(),
                sleep=clock.sleep,
                monotonic=clock.monotonic,
                is_retryable=is_retryable,
            )

        # Exactly one attempt — no further retries.
        assert attempts["count"] == 1
        err = exc_info.value
        assert "non-retryable" in str(err)
        assert len(err.retry_history) == 1
        assert clock.sleeps == []

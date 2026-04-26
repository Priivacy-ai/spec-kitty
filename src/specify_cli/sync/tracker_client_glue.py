"""Spec-kitty side glue for ``spec-kitty-tracker.bidirectional_sync()`` (FR-031).

This module owns the bounded-retry policy that wraps tracker bidirectional
sync calls: exponential backoff capped at a per-attempt ceiling, plus a
total wall-clock cap, plus a structured failure type that carries the
retry history. It exists so:

* the spec-kitty side has exactly one place that knows the policy
  (paired with the contract in
  ``kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/contracts/tracker-public-imports.md``);
* tests can drive the retry loop deterministically with a mock callable;
* the user-facing failure line is gated by the dedup helper from
  ``specify_cli.auth.transport`` (FR-029 pairing).

The glue is intentionally generic: it accepts any zero-arg callable as
the ``sync_call`` and translates exceptions into retries until the cap
is hit. This keeps the module decoupled from the upstream
``spec_kitty_tracker`` import surface (which lives behind a dependency
boundary documented in
``contracts/tracker-public-imports.md``).
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar


__all__ = [
    "RetryHistoryEntry",
    "TrackerSyncFailed",
    "TrackerSyncPolicy",
    "run_bidirectional_sync_with_retry",
]


logger = logging.getLogger(__name__)


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Errors and policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetryHistoryEntry:
    """One entry in the retry history attached to :class:`TrackerSyncFailed`."""

    attempt: int
    error_type: str
    error_message: str
    http_status: int | None
    body_excerpt: str | None
    backoff_seconds: float


class TrackerSyncFailed(RuntimeError):
    """Raised when tracker bidirectional sync exhausts its retry budget.

    Attributes:
        message: Human-readable failure summary.
        retry_history: Ordered list of :class:`RetryHistoryEntry` with
            one entry per attempt (success attempts are NOT recorded;
            this list captures every recoverable failure leading to
            exhaustion).
        last_error: The exception raised by the final attempt
            (preserved on ``__cause__`` as well).
    """

    error_code: str = "tracker_sync_failed"

    def __init__(
        self,
        message: str,
        *,
        retry_history: list[RetryHistoryEntry],
        last_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_history = retry_history
        self.last_error = last_error


@dataclass(frozen=True)
class TrackerSyncPolicy:
    """Bounded-retry policy for tracker bidirectional sync (FR-031).

    Defaults match the contract in
    ``contracts/tracker-public-imports.md``:

    * ``max_retries = 5``
    * ``max_backoff_seconds = 30`` (per-attempt cap)
    * ``total_timeout_seconds = 300`` (wall-clock cap)
    """

    max_retries: int = 5
    max_backoff_seconds: float = 30.0
    total_timeout_seconds: float = 300.0
    initial_backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

    def backoff_for_attempt(self, attempt: int) -> float:
        """Compute the backoff for *attempt* (1-indexed)."""
        base = self.initial_backoff_seconds * (
            self.backoff_multiplier ** max(0, attempt - 1)
        )
        capped = min(base, self.max_backoff_seconds)
        if self.jitter:
            # Full-jitter: pick uniformly from [0, capped].
            capped = random.uniform(0, capped)
        return float(capped)


# ---------------------------------------------------------------------------
# Public driver
# ---------------------------------------------------------------------------


def _http_status_of(exc: BaseException) -> int | None:
    """Best-effort extraction of an HTTP status from arbitrary exceptions."""
    for attr in ("status_code", "http_status", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _body_excerpt_of(exc: BaseException, max_bytes: int = 2048) -> str | None:
    """Return up to *max_bytes* bytes of the body associated with *exc*.

    Looks at common attribute names so connectors that surface their
    response body via ``.body`` / ``.response_body`` / ``.details`` can
    feed the retry-history record.
    """
    for attr in ("body_excerpt", "body", "response_body"):
        value = getattr(exc, attr, None)
        if isinstance(value, (bytes, bytearray)):
            try:
                return value[:max_bytes].decode("utf-8", errors="replace")
            except Exception:
                return None
        if isinstance(value, str):
            return value[:max_bytes]
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        try:
            import json as _json

            return _json.dumps(details, sort_keys=True)[:max_bytes]
        except Exception:
            return None
    return None


def run_bidirectional_sync_with_retry(
    sync_call: Callable[[], T],
    *,
    policy: TrackerSyncPolicy | None = None,
    sleep: Callable[[float], None] | None = None,
    monotonic: Callable[[], float] | None = None,
    is_retryable: Callable[[BaseException], bool] | None = None,
) -> T:
    """Execute *sync_call* under a bounded-retry policy.

    Args:
        sync_call: Zero-arg callable that performs one bidirectional
            sync attempt. Returning normally short-circuits the loop.
        policy: Optional :class:`TrackerSyncPolicy` override (defaults
            to the contract values).
        sleep: Injectable sleep function for tests (defaults to
            :func:`time.sleep`).
        monotonic: Injectable wall-clock for tests (defaults to
            :func:`time.monotonic`).
        is_retryable: Predicate that decides whether a given exception
            is retryable. By default, every exception is treated as
            retryable; supply a stricter predicate when calling from
            higher-level glue that already knows which errors are
            terminal (e.g. auth errors).

    Returns:
        The value returned by *sync_call* on the first successful
        attempt.

    Raises:
        TrackerSyncFailed: When *sync_call* raises retryable errors
            until the retry budget or wall-clock cap is exhausted, OR
            when a non-retryable error is encountered (the latter
            short-circuits without further attempts but still produces
            a structured :class:`TrackerSyncFailed` so the caller has a
            single failure type to handle).
    """
    eff_policy = policy or TrackerSyncPolicy()
    eff_sleep = sleep or time.sleep
    eff_monotonic = monotonic or time.monotonic
    eff_predicate = is_retryable or (lambda _exc: True)

    history: list[RetryHistoryEntry] = []
    started_at = eff_monotonic()
    attempt = 0
    last_error: Exception | None = None

    while True:
        attempt += 1
        try:
            return sync_call()
        except Exception as exc:  # broad: caller's predicate decides retryability
            last_error = exc
            backoff = eff_policy.backoff_for_attempt(attempt)
            history.append(
                RetryHistoryEntry(
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    http_status=_http_status_of(exc),
                    body_excerpt=_body_excerpt_of(exc),
                    backoff_seconds=backoff,
                )
            )

            if not eff_predicate(exc):
                logger.debug(
                    "tracker.sync.non_retryable attempt=%d error=%s",
                    attempt,
                    exc,
                )
                raise TrackerSyncFailed(
                    f"Tracker bidirectional sync failed (non-retryable): {exc}",
                    retry_history=history,
                    last_error=exc,
                ) from exc

            elapsed = eff_monotonic() - started_at
            if attempt >= eff_policy.max_retries:
                raise TrackerSyncFailed(
                    f"Tracker bidirectional sync failed after {attempt} attempts: {exc}",
                    retry_history=history,
                    last_error=exc,
                ) from exc

            # Wall-clock cap — fail fast if even the smallest backoff
            # would push us past the deadline.
            if elapsed + backoff >= eff_policy.total_timeout_seconds:
                raise TrackerSyncFailed(
                    "Tracker bidirectional sync failed: "
                    f"wall-clock cap of {eff_policy.total_timeout_seconds:g}s exceeded "
                    f"after {attempt} attempts (last error: {exc})",
                    retry_history=history,
                    last_error=exc,
                ) from exc

            logger.debug(
                "tracker.sync.retry attempt=%d backoff=%.3f error=%s",
                attempt,
                backoff,
                exc,
            )
            eff_sleep(backoff)
            # loop continues
            continue

    # Unreachable — every path returns or raises above. The branch
    # exists to keep the type-checker happy if extra exit paths are
    # added later.
    raise TrackerSyncFailed(  # pragma: no cover
        "Tracker bidirectional sync exited the retry loop without a result",
        retry_history=history,
        last_error=last_error,
    )

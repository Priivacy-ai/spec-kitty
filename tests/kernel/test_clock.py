"""Tests for kernel.clock — the single door to wall-clock time (WP01a).

Covers the relocated :func:`now_utc_iso` producer only; the remaining
producer family, parse/format helpers, and the injectable ``Clock`` land in
later work packages of mission ``kernel-clock-single-door`` (see
``kitty-specs/kernel-clock-single-door``) and are tested there.
"""

from __future__ import annotations

import pytest

import kernel.clock as clock_module
from kernel.clock import UTC, datetime, now_utc_iso, parse_iso

pytestmark = pytest.mark.fast

_FIXED_INSTANT = datetime(2026, 7, 8, 12, 34, 56, 789123, tzinfo=UTC)


class _FixedDatetime(datetime):
    """A ``datetime`` subclass whose ``now()`` always returns the fixed instant."""

    @classmethod
    def now(cls, tz=None):  # noqa: ANN001 - mirrors datetime.now's signature
        return _FIXED_INSTANT if tz is not None else _FIXED_INSTANT.replace(tzinfo=None)


def test_now_utc_iso_returns_aware_iso8601_string() -> None:
    """The producer returns a string that round-trips through
    ``datetime.fromisoformat`` and carries timezone info (aware, not naive)."""
    value = now_utc_iso()
    assert isinstance(value, str)
    parsed = parse_iso(value)
    assert parsed.tzinfo is not None


def test_now_utc_iso_byte_identical_under_fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-vacuity (C-009): under a frozen clock the producer returns the
    EXACT expected byte string, not merely "a string that parses".

    C-009 mutation verified: replacing ``now_utc_iso``'s body with
    ``return ""`` turns both this test AND
    ``test_now_utc_iso_returns_aware_iso8601_string`` red (ValueError /
    AssertionError respectively) -- run, observed failing, reverted.
    """
    monkeypatch.setattr(clock_module, "datetime", _FixedDatetime)
    assert clock_module.now_utc_iso() == "2026-07-08T12:34:56.789123+00:00"

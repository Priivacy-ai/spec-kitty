"""Producer-family byte-identity goldens (WP03, FR-004/005/006, NFR-001, C-003).

Every producer owns a DISTINCT on-disk serialization contract (C-003): this
module proves each one's exact byte output under a fixed clock, AND that the
contracts are mutually distinct from one another (a regression that folded
two contracts together -- e.g. dropping ``now_utc_stamp``'s trailing ``Z`` so
it degenerated into ``now_utc_seconds`` -- would collapse two of these
strings to the same value and this file would catch it).
"""

from __future__ import annotations

import pytest

import kernel.clock as clock_module
from kernel.clock import (
    UTC,
    FrozenClock,
    datetime,
    now_epoch,
    now_utc,
    now_utc_compact_stamp,
    now_utc_iso,
    now_utc_seconds,
    now_utc_stamp,
)

pytestmark = pytest.mark.fast

_FIXED_INSTANT = datetime(2026, 3, 4, 5, 6, 7, 891234, tzinfo=UTC)


@pytest.fixture
def frozen(monkeypatch: pytest.MonkeyPatch) -> datetime:
    monkeypatch.setattr(clock_module, "DEFAULT_CLOCK", FrozenClock(instant=_FIXED_INSTANT))
    return _FIXED_INSTANT


def test_now_utc_stamp_golden(frozen: datetime) -> None:
    """``%Y-%m-%dT%H:%M:%SZ`` -- second precision, ``Z`` suffix, no offset.

    C-009 mutation verified: dropping the ``Z`` suffix (or swapping in
    ``UTC_SECOND_TIMESTAMP_FORMAT``'s definition for the compact format)
    turns this red -- run, observed failing, reverted.
    """
    assert now_utc_stamp() == "2026-03-04T05:06:07Z"


def test_now_utc_compact_stamp_golden(frozen: datetime) -> None:
    """``%Y%m%dT%H%M%SZ`` -- no separators, distinct from :func:`now_utc_stamp`."""
    assert now_utc_compact_stamp() == "20260304T050607Z"


def test_now_utc_seconds_golden(frozen: datetime) -> None:
    """``isoformat(timespec="seconds")`` -- ISO shape, second precision, ``+00:00`` offset."""
    assert now_utc_seconds() == "2026-03-04T05:06:07+00:00"


def test_now_utc_returns_the_frozen_datetime(frozen: datetime) -> None:
    """``now_utc()`` -- the datetime-returning contract (FR-006)."""
    assert now_utc() == frozen
    assert now_utc().tzinfo is not None


def test_now_epoch_golden(frozen: datetime) -> None:
    """``now_epoch()`` -- float Unix epoch, matching the frozen instant's ``.timestamp()``."""
    assert now_epoch() == frozen.timestamp()


def test_now_utc_iso_golden_still_native_precision(frozen: datetime) -> None:
    """Sanity cross-check: :func:`now_utc_iso` (WP01a/WP02) keeps native
    (microsecond) precision -- distinct from :func:`now_utc_seconds`."""
    assert now_utc_iso() == "2026-03-04T05:06:07.891234+00:00"


def test_all_contracts_are_mutually_distinct(frozen: datetime) -> None:
    """C-003: distinct serialization contracts must never collapse to the
    same string under the same instant.

    C-009 mutation verified: replacing ``now_utc_seconds``'s body with
    ``return now_utc_stamp()`` (folding the two contracts together) turns
    this assertion red -- run, observed failing, reverted.
    """
    values = {
        now_utc_iso(),
        now_utc_stamp(),
        now_utc_compact_stamp(),
        now_utc_seconds(),
    }
    assert len(values) == 4, f"expected 4 mutually distinct contract strings, got {values}"

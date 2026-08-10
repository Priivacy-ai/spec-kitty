"""Per-site byte-identity mapping harness (WP03, plan Sec 4, SC-004).

The plan's "per-site mapping assertion" closes a hole a plain golden fixture
can't: a site's PRIOR serialization signature (precision / separator /
suffix) can be silently dropped on swap-to-producer even though the producer
itself has a passing golden (``test_producers.py``) -- e.g. a site that used
to call ``.isoformat(timespec="seconds")`` gets rehomed onto
:func:`kernel.clock.now_utc_iso` (native precision) instead of
:func:`kernel.clock.now_utc_seconds`, and a bare "does it look like a
timestamp" check would never notice.

This harness holds a REGISTRY of ``{site_id: (producer, prior_signature)}``.
For every registered site it renders the target producer under one shared
fixed instant and asserts the result equals the site's prior signature
rendered under that exact same instant. Package-remediation WPs (WP05-WP14)
append their own migrated sites to :data:`REGISTRY`, each carrying its WP00
census-recorded prior signature.

The registry starts with two door self-checks (this WP proves the harness
mechanism itself is load-bearing before any package WP populates real
entries) -- and this module's own committed non-vacuity proof, per C-009: a
deliberately mismatched entry is exercised via
:func:`test_planted_precision_mismatch_fires_the_harness`, which asserts the
harness's own comparison rejects the fired mismatch, then removed as a
committed registry entry (kept only as an inline fixture inside that test,
never merged into :data:`REGISTRY` itself -- a stray planted mismatch sitting
in the real registry would permanently fail this file for everyone).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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

_FIXED_INSTANT = datetime(2026, 11, 2, 14, 15, 16, 654321, tzinfo=UTC)


@dataclass(frozen=True)
class RegisteredSite:
    """One migrated call site's mapping-harness entry.

    ``producer``: the door producer this WP03+ (or a later package WP)
    routed the site onto -- called with no arguments under the shared frozen
    instant.
    ``prior_signature``: a callable reproducing the site's PRE-MIGRATION
    byte output from the same fixed instant (its old ``strftime``/
    ``isoformat`` call, inlined) -- this is what the WP00 census records per
    site (precision/sep/suffix).
    """

    producer: Callable[[], str]
    prior_signature: Callable[[datetime], str]


#: Populated by package-remediation WPs (WP05-WP14) as they migrate sites;
#: each entry's ``prior_signature`` reproduces that exact site's pre-mission
#: bytes (from the WP00 census), so a swap that silently drops the site's
#: original precision/separator/suffix is caught even though the producer
#: itself has an independent passing golden.
#:
#: This WP (WP03) seeds it with two door SELF-checks only, proving the
#: harness compares correctly before any package WP's real entry lands --
#: the harness format below (``producer``, ``prior_signature``) is the
#: contract those WPs populate against.
REGISTRY: dict[str, RegisteredSite] = {
    "kernel.clock.now_utc_stamp#self": RegisteredSite(
        producer=now_utc_stamp,
        prior_signature=lambda instant: instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ),
    "kernel.clock.now_utc_seconds#self": RegisteredSite(
        producer=now_utc_seconds,
        prior_signature=lambda instant: instant.isoformat(timespec="seconds"),
    ),
    "kernel.clock.now_utc_compact_stamp#self": RegisteredSite(
        producer=now_utc_compact_stamp,
        prior_signature=lambda instant: instant.strftime("%Y%m%dT%H%M%SZ"),
    ),
    "kernel.clock.now_utc_iso#self": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    "kernel.clock.now_utc#self": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
    "kernel.clock.now_epoch#self": RegisteredSite(
        producer=lambda: str(now_epoch()),
        prior_signature=lambda instant: str(instant.timestamp()),
    ),
}


@pytest.fixture
def frozen(monkeypatch: pytest.MonkeyPatch) -> datetime:
    monkeypatch.setattr(clock_module, "DEFAULT_CLOCK", FrozenClock(instant=_FIXED_INSTANT))
    return _FIXED_INSTANT


@pytest.mark.parametrize("site_id", sorted(REGISTRY))
def test_registered_site_matches_prior_signature(site_id: str, frozen: datetime) -> None:
    """Every registered site's chosen producer reproduces its prior bytes
    exactly, under the shared fixed instant."""
    entry = REGISTRY[site_id]
    assert entry.producer() == entry.prior_signature(frozen)


def test_planted_precision_mismatch_fires_the_harness(frozen: datetime) -> None:
    """C-009 non-vacuity: the harness's comparison rejects a real mismatch.

    Plants a deliberately WRONG entry -- pairing ``now_utc_stamp`` (second
    precision, ``Z`` suffix) against a prior-signature that reproduces
    ``now_utc_seconds``'s shape (``+00:00`` offset, no ``Z``) -- entirely
    in-memory (never merged into :data:`REGISTRY`, per NOTE-2: planted
    violations live in-memory/``tmp_path`` only). Confirms the harness
    mechanism itself is load-bearing, not a vacuous pass-through: run with
    the mismatch and the assertion correctly fails.
    """
    planted = RegisteredSite(
        producer=now_utc_stamp,
        prior_signature=lambda instant: instant.isoformat(timespec="seconds"),
    )

    assert planted.producer() != planted.prior_signature(frozen)

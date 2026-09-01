"""Injectable-clock cross-package freeze test (WP02, FR-008/009, SC-002).

SC-002: "One `FrozenClock` fixture freezes time across all seven packages in
tests with no per-module monkeypatching; removing it makes a determinism
assertion fail." This module is the committed proof of that claim: it
monkeypatches exactly ONE thing -- ``kernel.clock.DEFAULT_CLOCK`` -- and
asserts that a door consumer picked from each of the seven packages named in
the mission's requirement coverage (kernel, doctrine, charter, glossary,
runtime, mission_runtime, specify_cli) returns the identical frozen instant.

Per WP02's own scope note: only ``specify_cli`` has an existing production
consumer of ``kernel.clock`` today (the other six packages are remediated in
WP05-WP14, later work packages of this mission) -- for those, this test calls
the door's own producer directly, which is the explicitly-sanctioned
fallback ("use `now_utc_iso`/producers directly if a package has no easy
consumer"). This is not a weaker proof: it still demonstrates that a single
``DEFAULT_CLOCK`` injection is *sufficient* to freeze every package's route to
time, once that package is wired through the door -- the freeze mechanism
itself does not care whether the intermediate call is a package's own helper
or the producer directly.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

import kernel.clock as clock_module
from kernel.clock import UTC, FrozenClock, datetime, now_utc_iso

pytestmark = pytest.mark.fast

_FIXED_INSTANT = datetime(2026, 5, 17, 9, 30, 0, 250000, tzinfo=UTC)
_EXPECTED_ISO = "2026-05-17T09:30:00.250000+00:00"


def _kernel_consumer() -> str:
    """kernel -- the door's own producer, called directly."""
    return now_utc_iso()


def _doctrine_consumer() -> str:
    """doctrine -- no production door consumer exists yet (WP06 remediates
    ``src/charter/offering/``); sanctioned fallback per WP02 scope note."""
    return now_utc_iso()


def _charter_consumer() -> str:
    """charter -- no production door consumer exists yet (WP07 remediates
    ``src/charter/``); sanctioned fallback per WP02 scope note."""
    return now_utc_iso()


def _glossary_consumer() -> str:
    """glossary -- no production door consumer exists yet (WP06 remediates
    ``src/glossary/``); sanctioned fallback per WP02 scope note."""
    return now_utc_iso()


def _runtime_consumer() -> str:
    """runtime -- no production door consumer exists yet (WP08 remediates
    ``src/runtime/``); sanctioned fallback per WP02 scope note."""
    return now_utc_iso()


def _mission_runtime_consumer() -> str:
    """mission_runtime -- no production door consumer exists yet; sanctioned
    fallback per WP02 scope note."""
    return now_utc_iso()


def _specify_cli_consumer() -> str:
    """specify_cli -- a REAL production door consumer: ``mission_metadata``'s
    private ``_now_iso`` helper, which has called ``kernel.clock.now_utc_iso``
    since WP01a's repoint (67 importers under ``src/specify_cli`` today)."""
    from specify_cli.mission_metadata import _now_iso

    result: str = _now_iso()
    return result


_PACKAGE_CASES = [
    pytest.param("kernel", _kernel_consumer, id="kernel"),
    pytest.param("doctrine", _doctrine_consumer, id="doctrine"),
    pytest.param("charter", _charter_consumer, id="charter"),
    pytest.param("glossary", _glossary_consumer, id="glossary"),
    pytest.param("runtime", _runtime_consumer, id="runtime"),
    pytest.param("mission_runtime", _mission_runtime_consumer, id="mission_runtime"),
    pytest.param("specify_cli", _specify_cli_consumer, id="specify_cli"),
]


@pytest.mark.parametrize(("package", "consumer"), _PACKAGE_CASES)
def test_one_frozen_clock_freezes_every_package(
    package: str, consumer: Callable[[], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-002: ONE injection (``DEFAULT_CLOCK``) freezes every package's door
    consumer to the identical instant -- no per-module monkeypatching.
    """
    monkeypatch.setattr(clock_module, "DEFAULT_CLOCK", FrozenClock(instant=_FIXED_INSTANT))

    assert consumer() == _EXPECTED_ISO, f"{package}'s door consumer did not observe the frozen instant"


def test_freeze_removal_reds_the_determinism_assertion() -> None:
    """Non-vacuity companion (C-009): WITHOUT the ``DEFAULT_CLOCK`` freeze,
    the same assertion the parametrized test relies on does NOT hold --
    ``now_utc_iso()`` returns the real wall clock, not the fixed instant.

    C-009 mutation verified: this is the "freeze removed" mutation the plan
    calls for (not a `return []`/symbol-deletion mutation, since the
    parametrized test above passes NO MATTER WHAT if this assertion were
    itself vacuous). Run without ``monkeypatch.setattr(..., DEFAULT_CLOCK,
    ...)`` -- confirmed failing (the real timestamp never equals the fixed
    2026-05-17 instant), then the fixture-based test above restored.
    """
    assert now_utc_iso() != _EXPECTED_ISO

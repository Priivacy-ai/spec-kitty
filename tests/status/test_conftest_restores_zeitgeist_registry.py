"""The status conftest re-registers the Zeitgeist moment handlers (#136).

#123 gave this directory an autouse fixture that restored the default fan-out
wiring around every test, because many files here call
``adapters.reset_handlers()`` and never put production wiring back. #114 then
deleted the sync package by rewriting that same fixture, and the merge kept
#114's version wholesale — leaving the directory with no restoration at all
while ``adapters.py``'s docstrings still claimed "the status conftest does
exactly that around every test".

#146: the original proof here was a same-file two-test sequence (the first
wipes the registry, the second asserts the *following* test still sees the
wiring) that only worked because pytest happened to run the pair in
declaration order — true today because the repo pins ``--dist loadfile`` and
installs no randomizing plugin, but nothing pinned that assumption, so a
future reordering or resharding could silently stop exercising the fixture's
teardown half while still reporting green. Driving the fixture's own
generator through one setup/wipe/teardown cycle inside a single test proves
the same property without depending on collection order at all.
"""

from __future__ import annotations

import contextlib

from specify_cli.status import adapters
from tests.status.conftest import (
    _restore_zeitgeist_moment_handlers_around_every_status_test,
)


def test_conftest_fixture_restores_the_registry_after_a_test_wipes_it() -> None:
    """Drives the autouse fixture through setup, a wipe, then teardown."""
    fixture = _restore_zeitgeist_moment_handlers_around_every_status_test.__wrapped__()
    next(fixture)  # setup half: re-registers before the "test" body runs

    adapters.reset_handlers()  # simulate one of the surrounding files wiping it

    with contextlib.suppress(StopIteration):
        next(fixture)  # teardown half: must restore before the next test runs

    assert [h.__qualname__ for h in adapters._saas_handlers] == ["saas_moment_handler"]
    assert [h.__qualname__ for h in adapters._lifecycle_saas_handlers] == ["lifecycle_moment_handler"]
    assert [h.__qualname__ for h in adapters._resolved_binding_handlers] == ["resolved_binding_moment_handler"]

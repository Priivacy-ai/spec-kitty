"""The status conftest re-registers the Zeitgeist moment handlers (#136).

#123 gave this directory an autouse fixture that restored the default fan-out
wiring around every test, because many files here call
``adapters.reset_handlers()`` and never put production wiring back. #114 then
deleted the sync package by rewriting that same fixture, and the merge kept
#114's version wholesale — leaving the directory with no restoration at all
while ``adapters.py``'s docstrings still claimed "the status conftest does
exactly that around every test".

The two tests below are ordered on purpose: the first wipes the registry the
way the surrounding files do, the second asserts that the *following* test
still sees the Zeitgeist wiring. Without the conftest fixture the second one
fails.
"""

from __future__ import annotations

from specify_cli.status import adapters


def test_wipes_the_registry_like_the_surrounding_tests_do() -> None:
    adapters.reset_handlers()


def test_next_test_still_sees_the_zeitgeist_wiring_registered() -> None:
    """Runs after the wipe above: the conftest teardown must have restored."""
    assert [h.__qualname__ for h in adapters._saas_handlers] == ["saas_moment_handler"]
    assert [h.__qualname__ for h in adapters._lifecycle_saas_handlers] == ["lifecycle_moment_handler"]
    assert [h.__qualname__ for h in adapters._resolved_binding_handlers] == ["resolved_binding_moment_handler"]

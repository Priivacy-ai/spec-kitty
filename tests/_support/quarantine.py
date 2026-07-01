"""Env-gated quarantine deselection for the test suite.

A *quarantined* test is an irreducible **environmental** flake (Tier 3 in the
flakiness policy) that we cannot fully isolate but refuse to fix by retry. It is
held out of every normal/blocking run so it can never turn ``main`` red or block
an unrelated PR — yet it stays *visible* (never silently retried to green): the
dedicated, non-blocking ``quarantine-visibility`` CI job sets
``SPEC_KITTY_RUN_QUARANTINE=1`` and runs ``-m quarantine`` for real.

The actual deselection happens in ``tests/conftest.py``'s
``pytest_collection_modifyitems`` — this module holds the pure, unit-testable
decision so the policy can be verified without driving a full pytest session.

See ``docs/guides/testing-flakiness.md``.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

#: Opt-in env var. Only the literal ``"1"`` enables quarantined tests.
RUN_QUARANTINE_ENV_VAR = "SPEC_KITTY_RUN_QUARANTINE"

#: The marker name. Deliberately distinct from ``flaky`` (mutmut deselection).
QUARANTINE_MARKER = "quarantine"

_SKIP_REASON = (
    "quarantine: environmental flake under tracking — held out of normal runs. "
    f"Set {RUN_QUARANTINE_ENV_VAR}=1 to run it. "
    "See docs/guides/testing-flakiness.md"
)


def quarantine_opted_in(environ: Mapping[str, str]) -> bool:
    """Return whether quarantined tests should actually run.

    Strict: only the exact string ``"1"`` opts in, so a stray ``"0"`` /
    ``"false"`` / empty value keeps tests quarantined (fail-closed to *skip*).
    """
    return environ.get(RUN_QUARANTINE_ENV_VAR) == "1"


def quarantine_skip_mark() -> pytest.MarkDecorator:
    """The ``skip`` marker applied to quarantined items in normal runs."""
    return pytest.mark.skip(reason=_SKIP_REASON)

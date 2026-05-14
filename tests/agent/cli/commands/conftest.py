"""Shared fixtures for ``tests/agent/cli/commands``.

The M7 ``enforce_teamspace_mission_state_ready`` gate audits the local
project root before any sync/tracker/auth call path runs. In the test
environment, spec-kitty's own ``.kittify/`` contains TeamSpace blockers
(FORBIDDEN_KEY) — so the gate raises ``typer.Exit(1)`` before the test's
intended assertion can run.

These tests assert on the *post-gate* contract (auth, readiness, sync
result codes, tracker discovery, etc.), so the gate is stubbed
automatically at every call-site (sync.py, tracker.py, _auth_login.py)
via an autouse fixture.

Pattern mirrors the per-class fixture introduced for
``TestSyncNowExitCodes`` (commit 80f71fe14 + e0261dbf8) and the
``test_sync_logged_out_recovery.py`` class fixture; lifted to the
directory level here because the tracker test suite is module-level
(no class scope to attach an autouse fixture to).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _stub_teamspace_gate(monkeypatch):
    """Bypass enforce_teamspace_mission_state_ready at every call-site.

    The gate is imported by name into sync.py, tracker.py, and
    _auth_login.py — each import creates an independent attribute that
    must be patched separately for monkeypatch to take effect.
    """
    import specify_cli.cli.commands._auth_login as auth_mod
    import specify_cli.cli.commands.sync as sync_mod
    import specify_cli.cli.commands.tracker as tracker_mod

    stub = lambda **kwargs: None  # noqa: E731 — fixture-local lambda

    for module in (sync_mod, tracker_mod, auth_mod):
        monkeypatch.setattr(
            module,
            "enforce_teamspace_mission_state_ready",
            stub,
        )

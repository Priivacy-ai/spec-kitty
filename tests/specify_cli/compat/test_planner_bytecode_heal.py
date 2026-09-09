"""#4124 — the planner registry-load seam heals stale bytecode and degrades loudly.

``_ensure_registry_loaded`` sits on the startup path of every command (the
upgrade-nag hook). These tests pin its two #4124 behaviors: a stale-cache
import failure is healed and retried once, and any remaining failure degrades
to an empty registry with one loud warning instead of a silent pass (or a
crash). The healable shape here is the *real laundered* one —
``MigrationDiscoveryError`` chained to the original corrupt-``.pyc`` import
failure, exactly what ``auto_discover_migrations`` raises; the end-to-end
corrupt-``.pyc`` regression against the real discovery walk lives in
``tests/specify_cli/cli/test_bytecode_heal_startup.py``.
"""

from __future__ import annotations

import logging

import pytest

import specify_cli.compat.planner as planner
import specify_cli.upgrade.migrations as migrations
from specify_cli import bytecode_heal

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.fixture()
def registry_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the once-per-process registry flag around each test."""
    monkeypatch.setattr(planner, "_REGISTRY_AUTOLOADED", False)


def _laundered_discovery_error() -> migrations.MigrationDiscoveryError:
    """The exact shape ``auto_discover_migrations`` raises for a corrupt ``.pyc``.

    The launder site wraps every per-module import failure in a fresh
    ``MigrationDiscoveryError`` chained to the first original exception
    (``raise ... from``), so the corrupt-cache signature lives on the cause.
    """
    root = bytecode_heal.package_root()
    assert root is not None
    fake_pyc = root / "upgrade" / "migrations" / "__pycache__" / "base.cpython-311.pyc"
    cause = ImportError(f"Non-code object in '{fake_pyc}'")
    error = migrations.MigrationDiscoveryError(f"Failed to import migration module(s): base: {cause}")
    error.__cause__ = cause
    return error


def test_registry_load_degrades_loudly_when_discovery_fails(registry_gate: None, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> None:
        raise RuntimeError("discovery exploded")

    monkeypatch.setattr(migrations, "auto_discover_migrations", boom)
    with caplog.at_level(logging.WARNING, logger=planner._LOGGER.name):
        planner._ensure_registry_loaded()

    assert "upgrade migrations unavailable" in caplog.text
    assert "discovery exploded" in caplog.text
    assert "__pycache__" in caplog.text  # the one-line manual fix is named
    assert planner._REGISTRY_AUTOLOADED is True


def test_registry_load_heals_laundered_stale_bytecode_once(registry_gate: None, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """A corrupt-``.pyc`` discovery failure — laundered through ``MigrationDiscoveryError`` — heals.

    Non-vacuity: this is the production shape (the seam's stand-in raises the
    real laundered error; the original corrupt-cache exception rides the
    ``__cause__`` chain). With the cause-chain walk removed from
    ``failure_during_package_import``, the wrapper matches no direct shape and
    this test fails with "unavailable" instead of healing.
    """
    calls: list[int] = []

    def flaky() -> None:
        calls.append(1)
        if len(calls) == 1:
            raise _laundered_discovery_error()

    monkeypatch.setattr(migrations, "auto_discover_migrations", flaky)
    monkeypatch.setattr(bytecode_heal, "purge_package_bytecode", lambda: 3)
    with caplog.at_level(logging.WARNING, logger=planner._LOGGER.name):
        planner._ensure_registry_loaded()

    assert len(calls) == 2  # healed, then retried exactly once
    assert "repaired 3 stale bytecode cache file" in caplog.text
    assert "unavailable" not in caplog.text


def test_registry_load_leaves_laundered_genuine_bug_degraded_loudly(registry_gate: None, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """A genuinely broken migration module (``SyntaxError``) degrades loudly, unhealed.

    The discriminator must separate a corrupt ``.pyc`` from a broken module
    through the identical launder wrapper: healing the latter would purge every
    cache and fail again (#4124).
    """
    calls: list[int] = []

    def broken_module() -> None:
        calls.append(1)
        cause = SyntaxError("invalid syntax (m_0_10_12_charter_cleanup.py, line 1)")
        error = migrations.MigrationDiscoveryError(f"Failed to import migration module(s): m_0_10_12_charter_cleanup: {cause}")
        error.__cause__ = cause
        raise error

    purged: list[int] = []
    monkeypatch.setattr(migrations, "auto_discover_migrations", broken_module)
    monkeypatch.setattr(bytecode_heal, "purge_package_bytecode", lambda: purged.append(1) or 0)
    with caplog.at_level(logging.WARNING, logger=planner._LOGGER.name):
        planner._ensure_registry_loaded()

    assert len(calls) == 1  # no retry — the failure is genuine, not a stale cache
    assert purged == []
    assert "upgrade migrations unavailable" in caplog.text
    assert "invalid syntax" in caplog.text
    assert planner._REGISTRY_AUTOLOADED is True


def test_registry_load_real_discovery_still_succeeds(registry_gate: None) -> None:
    planner._ensure_registry_loaded()

    from specify_cli.upgrade.registry import MigrationRegistry

    assert MigrationRegistry._migrations  # the real migrations registered
    assert planner._REGISTRY_AUTOLOADED is True

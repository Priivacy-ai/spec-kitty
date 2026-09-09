"""#4124 — the planner registry-load seam heals stale bytecode and degrades loudly.

``_ensure_registry_loaded`` sits on the startup path of every command (the
upgrade-nag hook). These tests pin its two #4124 behaviors: a stale-cache
import failure is healed and retried once, and any remaining failure degrades
to an empty registry with one loud warning instead of a silent pass (or a
crash).
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


def _healable_import_error() -> ImportError:
    """An ImportError shaped like a corrupt-cache failure (names a package .pyc)."""
    root = bytecode_heal.package_root()
    assert root is not None
    fake_pyc = root / "upgrade" / "migrations" / "__pycache__" / "base.cpython-311.pyc"
    return ImportError(f"Non-code object in '{fake_pyc}'")


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


def test_registry_load_heals_stale_bytecode_once(registry_gate: None, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def flaky() -> None:
        calls.append(1)
        if len(calls) == 1:
            raise _healable_import_error()

    monkeypatch.setattr(migrations, "auto_discover_migrations", flaky)
    monkeypatch.setattr(bytecode_heal, "purge_package_bytecode", lambda: 3)
    with caplog.at_level(logging.WARNING, logger=planner._LOGGER.name):
        planner._ensure_registry_loaded()

    assert len(calls) == 2  # healed, then retried exactly once
    assert "repaired 3 stale bytecode cache file" in caplog.text
    assert "unavailable" not in caplog.text


def test_registry_load_real_discovery_still_succeeds(registry_gate: None) -> None:
    planner._ensure_registry_loaded()

    from specify_cli.upgrade.registry import MigrationRegistry

    assert MigrationRegistry._migrations  # the real migrations registered
    assert planner._REGISTRY_AUTOLOADED is True

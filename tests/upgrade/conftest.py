"""Upgrade-suite isolation for the process-global migration registry."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from specify_cli.upgrade.migrations import auto_discover_migrations
from specify_cli.upgrade.registry import MigrationRegistry


@pytest.fixture(scope="session", autouse=True)
def _seed_migration_registry() -> None:
    """Materialize the production registry before per-test snapshots begin."""
    auto_discover_migrations()


@pytest.fixture(autouse=True)
def _restore_migration_registry() -> Iterator[None]:
    """Restore collection-time registrations after every upgrade test.

    Upgrade tests intentionally exercise ``MigrationRegistry.clear()`` and
    temporary registrations.  Under loadfile scheduling, a later file runs in
    the same worker process; without restoration it observes whichever test
    last replaced the registry rather than the decorated production classes
    imported during collection.
    """
    original_mapping = MigrationRegistry._migrations
    original_entries = original_mapping.copy()
    try:
        yield
    finally:
        original_mapping.clear()
        original_mapping.update(original_entries)
        MigrationRegistry._migrations = original_mapping

"""Migration implementations for Spec Kitty upgrade system.

Auto-discovers all migration modules from the filesystem.
No manual imports needed - just create m_*.py files!
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path


def auto_discover_migrations() -> None:
    """
    Auto-discover and import all migration modules.

    Scans the migrations directory for all modules matching m_*.py pattern
    and imports them. Each module's @MigrationRegistry.register decorators
    will fire during import, populating the registry.

    This eliminates the need for manual import statements that developers
    frequently forget to update.

    Handles both fresh imports and re-registration after MigrationRegistry.clear()
    by reloading already-imported modules (only if they're not already registered).
    """
    import sys

    # Get the migrations package directory
    migrations_dir = Path(__file__).parent

    # Find all modules in the migrations directory
    for module_info in pkgutil.iter_modules([str(migrations_dir)]):
        module_name = module_info.name

        # Only import migration modules (m_*.py) and base.py
        # Skip test files, __pycache__, and other non-migration files
        if module_name.startswith("m_") or module_name == "base":
            try:
                module_full_name = f"{__name__}.{module_name}"

                # Check if module was already imported
                if module_full_name in sys.modules:
                    # Only reload if the migration isn't already registered
                    # This handles test scenarios where MigrationRegistry.clear()
                    # was called but modules are still in sys.modules
                    # For normal use, if module is imported (e.g., for utility functions),
                    # the migration is already registered so skip reload
                    from ..registry import MigrationRegistry

                    # Check if any migration from this module is already registered
                    # If so, skip reload to avoid duplicate registration errors
                    module = sys.modules[module_full_name]
                    has_registered_migration = False

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and hasattr(attr, "migration_id")
                            and attr.migration_id in MigrationRegistry._migrations
                        ):
                            has_registered_migration = True
                            break

                    if not has_registered_migration:
                        # Module imported but migration not registered (test scenario)
                        importlib.reload(sys.modules[module_full_name])
                    # else: Migration already registered, skip reload
                else:
                    # Fresh import
                    importlib.import_module(f".{module_name}", package=__name__)
            except Exception as e:
                # Log but don't fail - let the migration registry validation catch it
                print(
                    f"Warning: Failed to import migration module {module_name}: {e}",
                    file=sys.stderr,
                )


# Auto-discover all migrations on module import
auto_discover_migrations()

# Export the auto_discover function for testing
__all__ = ["auto_discover_migrations"]

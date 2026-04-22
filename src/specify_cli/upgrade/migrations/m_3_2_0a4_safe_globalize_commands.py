"""Migration 3.2.0a4: Safely clean up remaining local command copies.

Projects already upgraded beyond 3.1.2 do not re-run that migration, so any
remaining local ``spec-kitty.*`` command files must be handled here on the
3.2.0a4 upgrade path. The safety rules match the 3.1.2 migration exactly:
only proven generated files with exact global replacements are removed.
"""

from __future__ import annotations

from ..registry import MigrationRegistry
from .m_3_1_2_globalize_commands import _SafeGlobalizeCommandsBase


@MigrationRegistry.register
class SafeGlobalizeCommandsMigration(_SafeGlobalizeCommandsBase):
    """Safely remove lingering project-local spec-kitty command files."""

    migration_id = "3.2.0a4_safe_globalize_commands"
    description = "Safely remove lingering per-project spec-kitty command files"
    target_version = "3.2.0a4"

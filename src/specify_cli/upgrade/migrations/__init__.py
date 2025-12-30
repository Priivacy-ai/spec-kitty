"""Migration implementations for Spec Kitty upgrade system.

Import all migrations here to register them with the MigrationRegistry.
"""

from __future__ import annotations

# Import migrations to register them
from . import m_0_2_0_specify_to_kittify
from . import m_0_4_8_gitignore_agents
from . import m_0_5_0_encoding_hooks
from . import m_0_6_5_commands_rename
from . import m_0_6_7_ensure_missions
from . import m_0_7_2_worktree_commands_dedup
from . import m_0_7_3_update_scripts
from . import m_0_8_0_remove_active_mission
from . import m_0_8_0_worktree_agents_symlink
from . import m_0_9_0_frontmatter_only_lanes
from . import m_0_9_1_complete_lane_migration
from . import m_0_10_0_python_only
from . import m_0_10_1_populate_slash_commands
from . import m_0_10_2_update_slash_commands
from . import m_0_10_6_workflow_simplification
from . import m_0_10_8_fix_memory_structure

__all__ = [
    "m_0_2_0_specify_to_kittify",
    "m_0_4_8_gitignore_agents",
    "m_0_5_0_encoding_hooks",
    "m_0_6_5_commands_rename",
    "m_0_6_7_ensure_missions",
    "m_0_7_2_worktree_commands_dedup",
    "m_0_7_3_update_scripts",
    "m_0_8_0_remove_active_mission",
    "m_0_8_0_worktree_agents_symlink",
    "m_0_9_0_frontmatter_only_lanes",
    "m_0_9_1_complete_lane_migration",
    "m_0_10_0_python_only",  # Python-only CLI migration
    "m_0_10_1_populate_slash_commands",  # Populate missing slash commands
    "m_0_10_2_update_slash_commands",  # Update to Python CLI and flat structure
    "m_0_10_6_workflow_simplification",  # Simplify implement/review to use workflow commands
    "m_0_10_8_fix_memory_structure",  # Fix memory/ and AGENTS.md structure
]

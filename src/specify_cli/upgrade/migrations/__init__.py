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
    "m_0_9_1_complete_lane_migration",  # Now includes worktree cleanup
]

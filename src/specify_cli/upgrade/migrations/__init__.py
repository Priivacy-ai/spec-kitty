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
from . import m_0_9_2_research_mission_templates
from . import m_0_10_0_python_only
from . import m_0_10_1_populate_slash_commands
from . import m_0_10_2_update_slash_commands
from . import m_0_10_6_workflow_simplification
from . import m_0_10_8_fix_memory_structure
from . import m_0_10_9_repair_templates
from . import m_0_10_12_constitution_cleanup
from . import m_0_10_14_update_implement_slash_command
from . import m_0_11_0_workspace_per_wp
from . import m_0_11_1_improved_workflow_templates
from . import m_0_11_1_update_implement_slash_command
from . import m_0_11_2_improved_workflow_templates
from . import m_0_11_3_workflow_agent_flag
from . import m_0_12_0_documentation_mission
from . import m_0_12_1_remove_kitty_specs_from_gitignore
from . import m_0_13_0_research_csv_schema_check
from . import m_0_13_0_update_constitution_templates
from . import m_0_13_0_update_research_implement_templates
from . import m_0_13_1_exclude_worktrees
from . import m_0_13_5_fix_clarify_template
from . import m_0_13_5_add_commit_workflow_to_templates
from . import m_0_13_8_target_branch
from . import m_0_14_0_centralized_feature_detection

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
    "m_0_9_2_research_mission_templates",
    "m_0_10_0_python_only",
    "m_0_10_1_populate_slash_commands",
    "m_0_10_2_update_slash_commands",
    "m_0_10_6_workflow_simplification",
    "m_0_10_8_fix_memory_structure",
    "m_0_10_9_repair_templates",
    "m_0_10_12_constitution_cleanup",
    "m_0_10_14_update_implement_slash_command",
    "m_0_11_0_workspace_per_wp",
    "m_0_11_1_improved_workflow_templates",
    "m_0_11_1_update_implement_slash_command",
    "m_0_11_2_improved_workflow_templates",
    "m_0_11_3_workflow_agent_flag",
    "m_0_12_0_documentation_mission",
    "m_0_12_1_remove_kitty_specs_from_gitignore",
    "m_0_13_0_research_csv_schema_check",
    "m_0_13_0_update_constitution_templates",
    "m_0_13_0_update_research_implement_templates",
    "m_0_13_1_exclude_worktrees",
    "m_0_13_5_fix_clarify_template",
    "m_0_13_5_add_commit_workflow_to_templates",
    "m_0_13_8_target_branch",
    "m_0_14_0_centralized_feature_detection",
]

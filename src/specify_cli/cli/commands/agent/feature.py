"""Backward-compatibility shim — canonical module is now ``mission.py``.

This re-export keeps existing ``patch("specify_cli.cli.commands.agent.feature.…")``
paths working in tests and any third-party integrations.
"""

from specify_cli.cli.commands.agent.mission import *  # noqa: F401,F403
from specify_cli.cli.commands.agent.mission import (  # explicit re-exports for patch targets
    app,
    create_mission,
    create_mission_alias,
    check_prerequisites,
    setup_plan,
    accept_mission,
    merge_mission,
    finalize_tasks,
    branch_context,
    _find_mission_directory,
    _show_branch_context,
    _get_current_branch,
    _find_mission_worktree,
    _resolve_planning_branch,
    _ensure_branch_checked_out,
    _commit_to_branch,
    _emit_json,
    _build_setup_plan_detection_error,
    _read_mission_meta,
    _resolve_mission_target_branch,
    _inject_branch_contract,
    _enforce_git_preflight,
    _list_mission_spec_candidates,
    _find_latest_mission_worktree,
    locate_project_root,
    is_git_repo,
    get_current_branch,
    is_worktree_context,
    safe_commit,
    run_command,
    get_emitter,
    top_level_accept,
    top_level_merge,
)

# Deprecated aliases for backward compatibility
create_feature = create_mission
create_feature_alias = create_mission_alias
accept_feature = accept_mission
merge_feature = merge_mission
_find_feature_directory = _find_mission_directory
_find_feature_worktree = _find_mission_worktree
_find_latest_feature_worktree = _find_latest_mission_worktree
_read_feature_meta = _read_mission_meta
_resolve_feature_target_branch = _resolve_mission_target_branch
_list_feature_spec_candidates = _list_mission_spec_candidates

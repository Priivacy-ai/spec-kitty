"""Backward-compatibility shim — canonical module is now ``mission_type.py``.

This re-export keeps existing ``from specify_cli.cli.commands.mission import …``
paths working in tests and any third-party integrations.
"""

from specify_cli.cli.commands.mission_type import *  # noqa: F401,F403
from specify_cli.cli.commands.mission_type import (  # explicit re-exports for patch/import targets
    app,
    list_cmd,
    current_cmd,
    info_cmd,
    switch_cmd,
    _detect_current_feature,
    _print_available_missions,
    _mission_details_lines,
    _resolve_primary_repo_root,
    _list_active_worktrees,
    _print_active_worktrees,
)

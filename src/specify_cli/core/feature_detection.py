"""Backward-compatibility shim — canonical module is now ``mission_detection.py``.

This re-export keeps existing ``from specify_cli.core.feature_detection import …``
and ``patch("specify_cli.core.feature_detection.…")`` paths working in tests
and any third-party integrations.
"""

from specify_cli.core.mission_detection import *  # noqa: F401,F403
from specify_cli.core.mission_detection import (  # explicit re-exports for patch targets
    # Canonical names (new code should import these directly from mission_detection)
    MissionContext,
    MissionDetectionError,
    MultipleMissionsError,
    NoMissionFoundError,
    detect_mission,
    detect_mission_slug,
    detect_mission_directory,
    get_mission_target_branch,
    is_mission_complete,
    _list_all_missions,
    _validate_mission_exists,
    _is_mission_runnable,
    _resolve_numeric_mission_slug,
    # Backward-compat aliases (deprecated names)
    FeatureContext,
    FeatureDetectionError,
    MultipleFeaturesError,
    NoFeatureFoundError,
    detect_feature,
    detect_feature_slug,
    detect_feature_directory,
    get_feature_target_branch,
    is_feature_complete,
    _list_all_features,
    _validate_feature_exists,
    _is_feature_runnable,
    _resolve_numeric_feature_slug,
    # Internal helpers
    _detect_from_cwd,
    _detect_from_git_branch,
    _get_main_repo_root,
)

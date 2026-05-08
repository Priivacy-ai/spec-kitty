"""Public re-export surface for scanner utilities used by the dashboard service layer.

The canonical implementations live in ``specify_cli.dashboard.scanner``.
This module provides a clean import path for ``dashboard.*`` service objects
that must not import directly from ``specify_cli.dashboard.*`` (FR-010).

removal_release: When the scanner is relocated outside of specify_cli.dashboard,
update this shim to point at the new canonical location.
"""
# ruff: noqa: F401
from specify_cli.dashboard.scanner import (
    format_path_for_display,
    resolve_active_feature,
    resolve_feature_dir,
    scan_all_features,
    scan_feature_kanban,
)

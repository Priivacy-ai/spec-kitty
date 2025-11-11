"""Dashboard package public API."""

from .diagnostics import run_diagnostics
from .lifecycle import ensure_dashboard_running, stop_dashboard
from .scanner import (
    format_path_for_display,
    get_feature_artifacts,
    get_workflow_status,
    resolve_feature_dir,
    scan_all_features,
    scan_feature_kanban,
)
from .server import find_free_port, run_dashboard_server, start_dashboard

__all__ = [
    "ensure_dashboard_running",
    "stop_dashboard",
    "find_free_port",
    "start_dashboard",
    "run_dashboard_server",
    "scan_all_features",
    "scan_feature_kanban",
    "get_feature_artifacts",
    "get_workflow_status",
    "resolve_feature_dir",
    "format_path_for_display",
    "run_diagnostics",
]

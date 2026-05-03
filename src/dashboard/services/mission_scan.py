"""Mission scanning and kanban assembly service."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from dashboard.api_types import FeaturesListResponse, KanbanResponse, MissionContext


def parse_kanban_path(path: str) -> str | None:
    """Extract the feature_id segment from a `/api/kanban/<id>` request path.

    Returns None when the path is too short to contain a feature segment.
    Module-level (not a staticmethod) so seam tests that patch
    ``MissionScanService`` do not also intercept this pure function.
    """
    parts = path.split("/")
    if len(parts) < 4:
        return None
    return parts[3]


class MissionScanService:
    """Scans all missions, resolves active mission, assembles kanban state.

    All callable dependencies accept overrides (``_scan_all``, ``_resolve_active``,
    etc.) so the handler can pass its own module-level names — which tests may
    mock via ``patch.object(features_module, "scan_all_features", ...)``.
    Production callers pass nothing and the service imports from its own defaults.
    """

    def __init__(
        self,
        project_dir: Path,
        *,
        _scan_all: Callable[..., Any] | None = None,
        _resolve_active: Callable[..., Any] | None = None,
        _is_legacy: Callable[..., Any] | None = None,
        _get_mission: Callable[..., Any] | None = None,
        _format_path: Callable[..., Any] | None = None,
        _resolve_feature: Callable[..., Any] | None = None,
        _scan_kanban: Callable[..., Any] | None = None,
    ) -> None:
        from specify_cli.legacy_detector import is_legacy_format
        from specify_cli.mission import get_mission_by_name
        from specify_cli.scanner import (
            format_path_for_display,
            resolve_active_feature,
            resolve_feature_dir,
            scan_all_features,
            scan_feature_kanban,
        )

        self._project_dir = project_dir.resolve()
        self._scan_all = _scan_all if _scan_all is not None else scan_all_features
        self._resolve_active = _resolve_active if _resolve_active is not None else resolve_active_feature
        self._is_legacy = _is_legacy if _is_legacy is not None else is_legacy_format
        self._get_mission = _get_mission if _get_mission is not None else get_mission_by_name
        self._format_path = _format_path if _format_path is not None else format_path_for_display
        self._resolve_feature = _resolve_feature if _resolve_feature is not None else resolve_feature_dir
        self._scan_kanban = _scan_kanban if _scan_kanban is not None else scan_feature_kanban

    def get_features_list(self) -> FeaturesListResponse:
        """Scan all missions and return the full features-list payload."""
        from specify_cli.mission import MissionError

        features = self._scan_all(self._project_dir)

        for feature in features:
            feature_dir = self._project_dir / feature["path"]
            feature["is_legacy"] = self._is_legacy(feature_dir)

        mission_context: MissionContext = {
            "name": "No active feature",
            "domain": "unknown",
            "version": "",
            "slug": "",
            "description": "",
            "path": "",
        }

        active_feature = self._resolve_active(self._project_dir)

        if active_feature:
            feature_mission_type = active_feature.get("meta", {}).get("mission", "software-dev")
            try:
                kittify_dir = self._project_dir / ".kittify"
                mission = self._get_mission(feature_mission_type, kittify_dir)
                mission_context = {
                    "name": mission.name,
                    "domain": mission.config.domain,
                    "version": mission.config.version,
                    "slug": mission.path.name,
                    "description": mission.config.description or "",
                    "path": self._format_path(str(mission.path)),
                    "feature": active_feature.get("name", ""),
                }
            except MissionError:
                mission_context = {
                    "name": f"Unknown ({feature_mission_type})",
                    "domain": "unknown",
                    "version": "",
                    "slug": feature_mission_type,
                    "description": "",
                    "path": "",
                    "feature": active_feature.get("name", ""),
                }

        worktrees_root_path = self._project_dir / ".worktrees"
        try:
            worktrees_root_resolved = worktrees_root_path.resolve()
        except Exception:
            worktrees_root_resolved = worktrees_root_path

        try:
            current_path = Path.cwd().resolve()
        except Exception:
            current_path = Path.cwd()

        worktrees_root_exists = worktrees_root_path.exists()
        worktrees_root_display = (
            self._format_path(str(worktrees_root_resolved)) if worktrees_root_exists else None
        )

        active_worktree_display: str | None = None
        if worktrees_root_exists:
            try:
                current_path.relative_to(worktrees_root_resolved)
                active_worktree_display = self._format_path(str(current_path))
            except ValueError:
                active_worktree_display = None

        if not active_worktree_display and current_path != self._project_dir:
            active_worktree_display = self._format_path(str(current_path))

        return {
            "features": features,
            "active_feature_id": active_feature.get("id") if active_feature else None,
            "project_path": self._format_path(str(self._project_dir)),
            "worktrees_root": worktrees_root_display,
            "active_worktree": active_worktree_display,
            "active_mission": mission_context,
        }

    def get_kanban(self, feature_id: str) -> KanbanResponse:
        """Return kanban lanes and weighted progress for a specific feature."""
        from specify_cli.status.progress import compute_weighted_progress
        from specify_cli.status.reducer import materialize

        kanban_data = self._scan_kanban(self._project_dir, feature_id)

        feature_dir = self._resolve_feature(self._project_dir, feature_id)
        is_legacy = self._is_legacy(feature_dir) if feature_dir else False

        weighted_pct = None
        if feature_dir and not is_legacy:
            try:
                snap = materialize(feature_dir)
                progress = compute_weighted_progress(snap)
                weighted_pct = round(progress.percentage, 1)
            except Exception:
                pass

        return {
            "lanes": kanban_data,
            "is_legacy": is_legacy,
            "upgrade_needed": is_legacy,
            "weighted_percentage": weighted_pct,
        }

"""Feature-centric dashboard handlers."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .base import DashboardHandler
# These module-level imports serve as the patchable surface for tests.
# Handler methods pass them to service objects so that test mocks take effect.
from ..scanner import (
    format_path_for_display,
    resolve_active_feature,
    resolve_feature_dir,
    scan_all_features,
    scan_feature_kanban,
)
from specify_cli.legacy_detector import is_legacy_format
from specify_cli.mission import get_mission_by_name

__all__ = ["FeatureHandler"]


logger = logging.getLogger(__name__)


class FeatureHandler(DashboardHandler):
    """Serve feature lists, kanban lanes, and artifact viewers."""

    def handle_features_list(self) -> None:
        """Return summary data for all features."""
        # Lazy import breaks the circular dependency: specify_cli.__init__ loads
        # handlers/features, which would loop if mission_scan were imported eagerly.
        from dashboard.services.mission_scan import MissionScanService

        try:
            if self.project_dir is None:
                raise RuntimeError("dashboard project_dir is not configured")
            service = MissionScanService(
                Path(self.project_dir),
                _scan_all=scan_all_features,
                _resolve_active=resolve_active_feature,
                _is_legacy=is_legacy_format,
                _get_mission=get_mission_by_name,
                _format_path=format_path_for_display,
            )
            response = service.get_features_list()
            self._send_json(200, response)  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Failed to scan dashboard features")
            self._send_json(500, {"error": "failed_to_scan_features", "detail": str(exc)})

    def handle_kanban(self, path: str) -> None:
        """Return kanban data for a specific feature slug."""
        if self.project_dir is None:
            raise RuntimeError("dashboard project_dir is not configured")
        from dashboard.services.mission_scan import MissionScanService, parse_kanban_path

        feature_id = parse_kanban_path(path)
        if feature_id is None:
            self.send_response(404)
            self.end_headers()
            return
        service = MissionScanService(
            Path(self.project_dir),
            _is_legacy=is_legacy_format,
            _resolve_feature=resolve_feature_dir,
            _scan_kanban=scan_feature_kanban,
        )
        response = service.get_kanban(feature_id)
        self._send_json(200, response)  # type: ignore[arg-type]

    def handle_research(self, path: str) -> None:
        """Return research.md contents + artifacts, or serve a specific file."""
        if self.project_dir is None:
            raise RuntimeError("dashboard project_dir is not configured")
        from dashboard.file_reader import DashboardFileReader

        parts = path.split("/")
        if len(parts) < 4:
            self.send_response(404)
            self.end_headers()
            return
        reader = DashboardFileReader(Path(self.project_dir))
        if len(parts) == 4:
            self._send_json(200, reader.read_research(parts[3]))  # type: ignore[arg-type]
            return
        result = reader.read_artifact_file(parts[3], parts[4])
        if not result.found:
            self.send_response(404)
            self.end_headers()
            return
        self._send_text_nocache(200, result.content or "")

    def _handle_artifact_directory(self, path: str, directory_name: str, md_icon: str = "📝") -> None:
        """Delegate artifact directory listing or file serving to DashboardFileReader."""
        if self.project_dir is None:
            raise RuntimeError("dashboard project_dir is not configured")
        from dashboard.file_reader import DashboardFileReader

        parts = path.split("/")
        if len(parts) < 4:
            self.send_response(404)
            self.end_headers()
            return
        reader = DashboardFileReader(Path(self.project_dir))
        if len(parts) == 4:
            self._send_json(200, reader.read_artifact_directory(parts[3], directory_name, md_icon))  # type: ignore[arg-type]
            return
        result = reader.read_artifact_file(parts[3], parts[4])
        if not result.found:
            self.send_response(404)
            self.end_headers()
            return
        self._send_text_nocache(200, result.content or "")

    def handle_contracts(self, path: str) -> None:
        """Return contracts directory listing or serve a specific file."""
        self._handle_artifact_directory(path, "contracts", md_icon="📝")

    def handle_checklists(self, path: str) -> None:
        """Return checklists directory listing or serve a specific file."""
        self._handle_artifact_directory(path, "checklists", md_icon="✅")

    def handle_artifact(self, path: str) -> None:
        """Serve primary artifacts like spec.md and plan.md."""
        if self.project_dir is None:
            raise RuntimeError("dashboard project_dir is not configured")
        from dashboard.file_reader import DashboardFileReader

        parts = path.split("/")
        if len(parts) < 5:
            self.send_response(404)
            self.end_headers()
            return
        reader = DashboardFileReader(Path(self.project_dir))
        result = reader.read_named_artifact(parts[3], parts[4])
        if not result.found:
            self.send_response(404)
            self.end_headers()
            return
        self._send_text_nocache(200, result.content or "")

"""Tests for MissionHandler dashboard endpoints.

Covers handle_missions_list() and handle_kanban() using the _DummyHandler
pattern from test_api_constitution.py.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.dashboard.handlers.missions import MissionHandler

pytestmark = pytest.mark.fast


class _DummyMissionHandler:
    """Minimal handler shim to execute MissionHandler methods in isolation."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = str(project_dir)
        self.status_code: int | None = None
        self.headers: dict[str, str] = {}
        self.wfile = io.BytesIO()

    def send_response(self, code: int) -> None:
        self.status_code = code

    def send_header(self, key: str, value: str) -> None:
        self.headers[key] = value

    def end_headers(self) -> None:
        return None


# ---------------------------------------------------------------------------
# handle_missions_list
# ---------------------------------------------------------------------------


class TestHandleMissionsList:
    """Tests for MissionHandler.handle_missions_list()."""

    def test_empty_missions(self, tmp_path: Path) -> None:
        """Returns empty missions list when no missions exist."""
        handler = _DummyMissionHandler(tmp_path)

        with patch(
            "specify_cli.dashboard.handlers.missions.scan_all_missions",
            return_value=[],
        ), patch(
            "specify_cli.dashboard.handlers.missions.resolve_active_mission",
            return_value=None,
        ):
            MissionHandler.handle_missions_list(handler)  # type: ignore[arg-type]

        assert handler.status_code == 200
        body = json.loads(handler.wfile.getvalue())
        assert body["missions"] == []
        assert body["active_mission_id"] is None

    def test_multiple_missions(self, tmp_path: Path) -> None:
        """Returns all missions with legacy flag and active mission context."""
        missions = [
            {"id": "010-ws-per-wp", "name": "Workspace per WP", "path": "kitty-specs/010-ws-per-wp"},
            {"id": "020-cli-refactor", "name": "CLI Refactor", "path": "kitty-specs/020-cli-refactor"},
        ]
        # Create mission directories for is_legacy_format check
        for m in missions:
            (tmp_path / m["path"]).mkdir(parents=True)

        handler = _DummyMissionHandler(tmp_path)

        with patch(
            "specify_cli.dashboard.handlers.missions.scan_all_missions",
            return_value=missions,
        ), patch(
            "specify_cli.dashboard.handlers.missions.resolve_active_mission",
            return_value=None,
        ), patch(
            "specify_cli.dashboard.handlers.missions.is_legacy_format",
            return_value=False,
        ):
            MissionHandler.handle_missions_list(handler)  # type: ignore[arg-type]

        body = json.loads(handler.wfile.getvalue())
        assert len(body["missions"]) == 2
        assert body["active_mission_id"] is None

    def test_active_mission_context(self, tmp_path: Path) -> None:
        """Active mission populates mission_context in response."""
        active = {
            "id": "010-ws-per-wp",
            "name": "Workspace per WP",
            "path": "kitty-specs/010-ws-per-wp",
            "meta": {"mission": "software-dev"},
        }
        (tmp_path / active["path"]).mkdir(parents=True)

        from unittest.mock import MagicMock

        mock_mission = MagicMock()
        mock_mission.name = "Software Development"
        mock_mission.config.domain = "engineering"
        mock_mission.config.version = "1.0"
        mock_mission.config.description = "Dev mission"
        mock_mission.path = tmp_path / "kitty-specs" / "010-ws-per-wp"

        handler = _DummyMissionHandler(tmp_path)

        with patch(
            "specify_cli.dashboard.handlers.missions.scan_all_missions",
            return_value=[active],
        ), patch(
            "specify_cli.dashboard.handlers.missions.resolve_active_mission",
            return_value=active,
        ), patch(
            "specify_cli.dashboard.handlers.missions.is_legacy_format",
            return_value=False,
        ), patch(
            "specify_cli.dashboard.handlers.missions.get_mission_by_name",
            return_value=mock_mission,
        ):
            MissionHandler.handle_missions_list(handler)  # type: ignore[arg-type]

        body = json.loads(handler.wfile.getvalue())
        assert body["active_mission"]["name"] == "Software Development"
        assert body["active_mission"]["domain"] == "engineering"
        assert body["active_mission_id"] == "010-ws-per-wp"


# ---------------------------------------------------------------------------
# handle_kanban
# ---------------------------------------------------------------------------


class TestHandleKanban:
    """Tests for MissionHandler.handle_kanban()."""

    def test_valid_mission_id(self, tmp_path: Path) -> None:
        """Returns kanban lanes for a valid mission slug."""
        kanban_data = {
            "planned": [{"id": "WP01", "title": "Setup"}],
            "doing": [],
            "for_review": [],
            "done": [],
        }
        handler = _DummyMissionHandler(tmp_path)

        with patch(
            "specify_cli.dashboard.handlers.missions.scan_mission_kanban",
            return_value=kanban_data,
        ), patch(
            "specify_cli.dashboard.handlers.missions.resolve_mission_dir",
            return_value=tmp_path / "kitty-specs" / "010-ws",
        ), patch(
            "specify_cli.dashboard.handlers.missions.is_legacy_format",
            return_value=False,
        ):
            MissionHandler.handle_kanban(handler, "/api/kanban/010-ws")  # type: ignore[arg-type]

        assert handler.status_code == 200
        body = json.loads(handler.wfile.getvalue())
        assert body["lanes"] == kanban_data
        assert body["is_legacy"] is False

    def test_invalid_path_returns_404(self, tmp_path: Path) -> None:
        """Short path without mission ID returns 404."""
        handler = _DummyMissionHandler(tmp_path)
        MissionHandler.handle_kanban(handler, "/api/kanban")  # type: ignore[arg-type]
        assert handler.status_code == 404

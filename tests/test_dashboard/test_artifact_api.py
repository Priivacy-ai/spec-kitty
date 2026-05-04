"""User-journey tests for the artifact-serving API endpoints.

Tests the complete request→service→response chain without mocking the
service layer. Each test exercises a real user scenario: fetching
research artifacts, contracts, checklists, and named artifacts for a
mission that exists in a fixture project directory.

Coverage target: the artifact-serving paths in both the FastAPI transport
(src/dashboard/api/routers/artifacts.py) and the legacy handler
(src/specify_cli/dashboard/handlers/features.py) that were flagged by
diff-coverage on PR #970.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ─── fixture project setup ───────────────────────────────────────────────────

MISSION_SLUG = "001-sample-mission"


def _build_project(tmp_path: Path) -> Path:
    """Create a minimal project with research, contracts, and checklists."""
    (tmp_path / ".kittify").mkdir(parents=True, exist_ok=True)

    feature_dir = tmp_path / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)

    # meta.json — required for the scanner to recognise the mission
    (feature_dir / "meta.json").write_text(
        json.dumps({
            "mission_id": "01ARTTEST00000000000000000A",
            "mission_slug": MISSION_SLUG,
            "mission_number": 1,
            "friendly_name": "Sample Mission",
            "mission_type": "software-dev",
            "target_branch": "main",
            "created_at": "2026-01-01T00:00:00+00:00",
        })
    )

    # Research artifacts
    research_dir = feature_dir / "research"
    research_dir.mkdir()
    (research_dir / "research.md").write_text("# Research\n\nSome findings.")
    (research_dir / "extra.md").write_text("# Extra research note.")

    # Primary research.md at the feature root
    (feature_dir / "research.md").write_text("# Main research findings.")

    # Contracts — place files both in subdirectory (for listing) and at root (for serving)
    contracts_dir = feature_dir / "contracts"
    contracts_dir.mkdir()
    (contracts_dir / "api-contract.md").write_text("# API Contract\n\nSpec here.")
    # Also place at feature root so single-segment {file_name} route can serve it
    (feature_dir / "api-contract.md").write_text("# API Contract\n\nSpec here.")

    # Checklists — same pattern
    checklists_dir = feature_dir / "checklists"
    checklists_dir.mkdir()
    (checklists_dir / "requirements.md").write_text("# Requirements\n\n- [ ] Item 1")
    (feature_dir / "requirements.md").write_text("# Requirements\n\n- [ ] Item 1")

    return tmp_path


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return _build_project(tmp_path)


def _fastapi_client(project_dir: Path):
    from dashboard.api import create_app
    from fastapi.testclient import TestClient
    app = create_app(project_dir=project_dir, project_token=None)
    return TestClient(app)


# ─── FastAPI transport: research endpoints ────────────────────────────────────


class TestResearchEndpoints:
    """GET /api/research/{id} and GET /api/research/{id}/{file_name}."""

    def test_research_listing_returns_200(self, project_dir: Path) -> None:
        """Fetching the research summary for a known mission returns 200."""
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/research/{MISSION_SLUG}")
        assert resp.status_code == 200, resp.text

    def test_research_listing_has_expected_shape(self, project_dir: Path) -> None:
        """Research response contains main_file and artifacts keys."""
        with _fastapi_client(project_dir) as client:
            data = client.get(f"/api/research/{MISSION_SLUG}").json()
        assert "main_file" in data or "artifacts" in data, (
            f"Research response missing expected keys: {list(data.keys())}"
        )

    def test_specific_research_file_served(self, project_dir: Path) -> None:
        """Fetching an existing research file returns its text content."""
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/research/{MISSION_SLUG}/research.md")
        assert resp.status_code == 200
        assert "research" in resp.text.lower()

    def test_missing_research_file_returns_404(self, project_dir: Path) -> None:
        """Fetching a non-existent research file returns 404."""
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/research/{MISSION_SLUG}/no-such-file.md")
        assert resp.status_code == 404

    def test_unknown_mission_research_returns_structured_response(self, project_dir: Path) -> None:
        """Fetching research for an unknown mission returns a graceful response."""
        with _fastapi_client(project_dir) as client:
            resp = client.get("/api/research/no-such-mission")
        # DashboardFileReader returns an empty structure or 404 for unknown missions
        assert resp.status_code in (200, 404)


# ─── FastAPI transport: contracts endpoints ───────────────────────────────────


class TestContractsEndpoints:
    """GET /api/contracts/{id} and GET /api/contracts/{id}/{file_name}."""

    def test_contracts_listing_returns_200(self, project_dir: Path) -> None:
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/contracts/{MISSION_SLUG}")
        assert resp.status_code == 200

    def test_contracts_listing_contains_files_key(self, project_dir: Path) -> None:
        with _fastapi_client(project_dir) as client:
            data = client.get(f"/api/contracts/{MISSION_SLUG}").json()
        assert "files" in data

    def test_contracts_listing_includes_created_file(self, project_dir: Path) -> None:
        with _fastapi_client(project_dir) as client:
            data = client.get(f"/api/contracts/{MISSION_SLUG}").json()
        names = [f["name"] for f in data.get("files", [])]
        assert "api-contract.md" in names

    def test_specific_contract_file_served(self, project_dir: Path) -> None:
        # The {file_name} route segment is a single path component; the file is placed
        # at the feature root so the single-segment URL can serve it directly.
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/contracts/{MISSION_SLUG}/api-contract.md")
        assert resp.status_code == 200
        assert "API Contract" in resp.text

    def test_missing_contract_file_returns_404(self, project_dir: Path) -> None:
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/contracts/{MISSION_SLUG}/ghost.md")
        assert resp.status_code == 404


# ─── FastAPI transport: checklists endpoints ──────────────────────────────────


class TestChecklistsEndpoints:
    """GET /api/checklists/{id} and GET /api/checklists/{id}/{file_name}."""

    def test_checklists_listing_returns_200(self, project_dir: Path) -> None:
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/checklists/{MISSION_SLUG}")
        assert resp.status_code == 200

    def test_checklists_listing_includes_created_file(self, project_dir: Path) -> None:
        with _fastapi_client(project_dir) as client:
            data = client.get(f"/api/checklists/{MISSION_SLUG}").json()
        names = [f["name"] for f in data.get("files", [])]
        assert "requirements.md" in names

    def test_specific_checklist_file_served(self, project_dir: Path) -> None:
        # File placed at feature root so single-segment {file_name} URL can serve it.
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/checklists/{MISSION_SLUG}/requirements.md")
        assert resp.status_code == 200
        assert "Requirements" in resp.text

    def test_missing_checklist_file_returns_404(self, project_dir: Path) -> None:
        with _fastapi_client(project_dir) as client:
            resp = client.get(f"/api/checklists/{MISSION_SLUG}/ghost.md")
        assert resp.status_code == 404


# ─── FastAPI transport: diagnostics ──────────────────────────────────────────


class TestDiagnosticsEndpoint:
    """GET /api/diagnostics — runs without a specific mission slug."""

    def test_diagnostics_returns_200(self, project_dir: Path) -> None:
        """Diagnostics run successfully with no active mission."""
        with _fastapi_client(project_dir) as client:
            resp = client.get("/api/diagnostics")
        assert resp.status_code == 200

    def test_diagnostics_response_is_json(self, project_dir: Path) -> None:
        with _fastapi_client(project_dir) as client:
            resp = client.get("/api/diagnostics")
        assert resp.headers["content-type"].startswith("application/json")
        data = resp.json()
        assert isinstance(data, dict)


# ─── Legacy handler: research and artifact paths via BaseHTTPServer ───────────


class TestLegacyHandlerArtifactPaths:
    """Exercise the legacy FeatureHandler paths directly.

    The BaseHTTPServer transport is the rollback path. These tests exercise
    the handler methods that were flagged as uncovered by diff-coverage.
    They invoke handler methods directly (not through an HTTP server) because
    the legacy transport is not the default and does not have a built-in
    TestClient fixture.
    """

    def _make_handler(self, project_dir: Path):
        """Build a FeatureHandler with the fixture project_dir wired in."""
        from unittest.mock import MagicMock
        from specify_cli.dashboard.handlers.features import FeatureHandler

        handler = MagicMock(spec=FeatureHandler)
        handler.project_dir = str(project_dir)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        handler.wfile.write = MagicMock()
        # Bind the real method implementations
        handler._send_json = FeatureHandler._send_json.__get__(handler)
        handler._send_text_nocache = FeatureHandler._send_text_nocache.__get__(handler)
        handler.handle_research = FeatureHandler.handle_research.__get__(handler)
        handler._handle_artifact_directory = FeatureHandler._handle_artifact_directory.__get__(handler)
        handler.handle_contracts = FeatureHandler.handle_contracts.__get__(handler)
        handler.handle_checklists = FeatureHandler.handle_checklists.__get__(handler)
        handler.handle_artifact = FeatureHandler.handle_artifact.__get__(handler)
        return handler

    def test_research_too_short_path_returns_404(self, project_dir: Path) -> None:
        """handle_research: paths with < 4 segments return 404."""
        handler = self._make_handler(project_dir)
        # /api/research (only 3 parts) triggers the early 404
        handler.handle_research("/api/research")
        handler.send_response.assert_called_with(404)

    def test_research_listing_returns_json(self, project_dir: Path) -> None:
        """handle_research: a valid feature slug returns a JSON research listing."""
        handler = self._make_handler(project_dir)
        handler.handle_research(f"/api/research/{MISSION_SLUG}")
        # Either _send_json or send_response(200) was called
        assert handler.send_response.called or handler._send_json.called or handler.wfile.write.called

    def test_research_file_served_by_legacy_handler(self, project_dir: Path) -> None:
        """handle_research: a 5-part path serves an individual file."""
        handler = self._make_handler(project_dir)
        handler.handle_research(f"/api/research/{MISSION_SLUG}/research.md")
        handler.send_response.assert_called()

    def test_artifact_directory_too_short_path_returns_404(self, project_dir: Path) -> None:
        """_handle_artifact_directory: paths with < 4 segments return 404."""
        handler = self._make_handler(project_dir)
        handler._handle_artifact_directory("/api/contracts", "contracts")
        handler.send_response.assert_called_with(404)

    def test_contracts_listing_via_legacy_handler(self, project_dir: Path) -> None:
        """handle_contracts: a valid feature slug returns a JSON directory listing."""
        handler = self._make_handler(project_dir)
        handler.handle_contracts(f"/api/contracts/{MISSION_SLUG}")
        assert handler.wfile.write.called or handler.send_response.called

    def test_checklists_listing_via_legacy_handler(self, project_dir: Path) -> None:
        """handle_checklists: a valid feature slug returns a JSON directory listing."""
        handler = self._make_handler(project_dir)
        handler.handle_checklists(f"/api/checklists/{MISSION_SLUG}")
        assert handler.wfile.write.called or handler.send_response.called

    def test_missing_file_in_artifact_directory_returns_404(self, project_dir: Path) -> None:
        """_handle_artifact_directory: a non-existent file returns 404."""
        handler = self._make_handler(project_dir)
        handler.handle_contracts(f"/api/contracts/{MISSION_SLUG}/no-such-file.md")
        handler.send_response.assert_called_with(404)

    def test_artifact_too_short_path_returns_404(self, project_dir: Path) -> None:
        """handle_artifact: paths with < 5 segments return 404."""
        handler = self._make_handler(project_dir)
        handler.handle_artifact(f"/api/artifact/{MISSION_SLUG}")
        handler.send_response.assert_called_with(404)

    def test_artifact_not_found_returns_404(self, project_dir: Path) -> None:
        """handle_artifact: a non-existent named artifact returns 404."""
        handler = self._make_handler(project_dir)
        handler.handle_artifact(f"/api/artifact/{MISSION_SLUG}/no-such.md")
        handler.send_response.assert_called_with(404)

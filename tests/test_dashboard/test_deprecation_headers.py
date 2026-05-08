"""Tests for the retired /api/features and /api/kanban routes (HTTP 410 Gone).

FR-007, FR-008: both legacy routes now return 410 with a structured JSON body
containing ``"error": "endpoint_retired"`` and a ``"successor"`` key pointing
clients to the canonical replacement route. The routes are hidden from the
OpenAPI schema (``include_in_schema=False``).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

SAMPLE_MISSION_SLUG = "sample-dep-mission-01ABCDEFGH"


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Build a minimal fixture project the dashboard can scan."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True, exist_ok=True)

    feature_dir = tmp_path / "kitty-specs" / SAMPLE_MISSION_SLUG
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Sample Spec\n", encoding="utf-8")

    meta = {
        "mission_id": "01ABCDEFGHJKMNPQRSTVWXYZ99",
        "mission_slug": SAMPLE_MISSION_SLUG,
        "friendly_name": "Sample Deprecation Mission",
        "mission_number": None,
        "mission": "software-dev",
    }
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return tmp_path


def _client(project_dir: Path):
    """Build a TestClient for the FastAPI app rooted at ``project_dir``."""
    from dashboard.api import create_app
    from fastapi.testclient import TestClient

    app = create_app(project_dir=project_dir, project_token=None)
    return TestClient(app)


# ---------------------------------------------------------------------------
# /api/features — retired, returns 410
# ---------------------------------------------------------------------------


class TestFeaturesRetired:
    """GET /api/features must return 410 with a structured error body."""

    def test_features_returns_410(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get("/api/features")
        assert resp.status_code == 410

    def test_features_body_contains_endpoint_retired(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get("/api/features")
        data = resp.json()
        assert data.get("error") == "endpoint_retired"

    def test_features_body_contains_successor(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get("/api/features")
        data = resp.json()
        assert "successor" in data

    def test_features_successor_points_to_missions(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get("/api/features")
        data = resp.json()
        assert data["successor"] == "/api/missions"


# ---------------------------------------------------------------------------
# /api/kanban/{id} — retired, returns 410
# ---------------------------------------------------------------------------


class TestKanbanRetired:
    """GET /api/kanban/{id} must return 410 with a structured error body."""

    def test_kanban_returns_410(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get(f"/api/kanban/{SAMPLE_MISSION_SLUG}")
        assert resp.status_code == 410

    def test_kanban_body_contains_endpoint_retired(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get(f"/api/kanban/{SAMPLE_MISSION_SLUG}")
        data = resp.json()
        assert data.get("error") == "endpoint_retired"

    def test_kanban_body_contains_successor(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get(f"/api/kanban/{SAMPLE_MISSION_SLUG}")
        data = resp.json()
        assert "successor" in data

    def test_kanban_successor_points_to_missions_status(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get(f"/api/kanban/{SAMPLE_MISSION_SLUG}")
        data = resp.json()
        assert data["successor"] == f"/api/missions/{SAMPLE_MISSION_SLUG}/status"

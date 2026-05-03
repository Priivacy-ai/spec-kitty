"""Deprecation header tests for the legacy /api/features and /api/kanban routes.

FR-009 / FR-010 / FR-011: the two pre-mission routes carry ``Deprecation: true``
and a ``Link`` header pointing clients at the successor resource. These tests
verify:

1. The headers are present on every 200 response (T021).
2. The response bodies retain their pre-mission shape (T022).
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
# T021: Deprecation headers present
# ---------------------------------------------------------------------------


class TestDeprecationHeadersPresent:
    """GET /api/features and GET /api/kanban/{id} must emit deprecation headers."""

    def test_features_has_deprecation_header(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get("/api/features")
        assert resp.status_code == 200
        # HTTP headers are case-insensitive; httpx normalises them to lower-case.
        assert resp.headers.get("deprecation") == "true", (
            f"Expected Deprecation: true header, got: {dict(resp.headers)!r}"
        )

    def test_features_has_link_header_pointing_to_missions(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get("/api/features")
        assert resp.status_code == 200
        link = resp.headers.get("link", "")
        assert "/api/missions" in link, (
            f"Expected Link header to contain /api/missions, got: {link!r}"
        )

    def test_kanban_has_deprecation_header(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get(f"/api/kanban/{SAMPLE_MISSION_SLUG}")
        assert resp.status_code == 200
        assert resp.headers.get("deprecation") == "true", (
            f"Expected Deprecation: true header, got: {dict(resp.headers)!r}"
        )

    def test_kanban_has_link_header_pointing_to_missions_status(
        self, project_dir: Path
    ) -> None:
        with _client(project_dir) as client:
            resp = client.get(f"/api/kanban/{SAMPLE_MISSION_SLUG}")
        assert resp.status_code == 200
        link = resp.headers.get("link", "")
        assert "/api/missions" in link, (
            f"Expected Link header to contain /api/missions, got: {link!r}"
        )
        assert SAMPLE_MISSION_SLUG in link, (
            f"Expected Link header to contain the feature_id, got: {link!r}"
        )
        assert "successor-version" in link, (
            f"Expected rel=successor-version in Link header, got: {link!r}"
        )


# ---------------------------------------------------------------------------
# T022: Deprecated routes still return the same body shape
# ---------------------------------------------------------------------------


class TestDeprecatedRoutesBodyShapeUnchanged:
    """Body shape of deprecated routes must match the pre-mission contract."""

    def test_features_body_shape_unchanged(self, project_dir: Path) -> None:
        from dashboard.api.models import FeaturesListResponse

        with _client(project_dir) as client:
            resp = client.get("/api/features")

        assert resp.status_code == 200
        data = resp.json()
        # Validate via Pydantic response model — same check the transport parity
        # tests use. This ensures the deprecation header injection did not alter
        # the serialized body.
        FeaturesListResponse.model_validate(data)
        # Core keys that existing frontend consumers rely on:
        assert "features" in data
        assert "active_feature_id" in data or "project_path" in data

    def test_features_body_contains_at_least_one_feature(
        self, project_dir: Path
    ) -> None:
        with _client(project_dir) as client:
            resp = client.get("/api/features")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("features"), list), (
            "features key must be a list"
        )
        assert len(data["features"]) >= 1, (
            "Fixture project should produce at least one feature entry"
        )

    def test_kanban_body_shape_unchanged(self, project_dir: Path) -> None:
        from dashboard.api.models import KanbanResponse

        with _client(project_dir) as client:
            resp = client.get(f"/api/kanban/{SAMPLE_MISSION_SLUG}")

        assert resp.status_code == 200
        data = resp.json()
        # Validate via Pydantic response model.
        KanbanResponse.model_validate(data)
        # Core keys that existing frontend consumers rely on:
        assert "lanes" in data
        assert "weighted_percentage" in data

    def test_kanban_body_lanes_is_dict(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            resp = client.get(f"/api/kanban/{SAMPLE_MISSION_SLUG}")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("lanes"), dict), (
            "KanbanResponse.lanes must be a dict"
        )

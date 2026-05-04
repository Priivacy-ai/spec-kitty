"""Tests for the resource-oriented mission and workpackage API endpoints.

Covers:
  - GET /api/missions
  - GET /api/missions/{mission_id}
  - GET /api/missions/{mission_id}/status
  - GET /api/missions/{mission_id}/workpackages
  - GET /api/missions/{mission_id}/workpackages/{wp_id}
  - 404 for unknown mission and unknown WP
  - 409 for ambiguous mid8 selector

Owned by WP02 of mission resource-oriented-mission-api-01KQQRF2.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


# ─── fixture helpers ─────────────────────────────────────────────────────────

SAMPLE_MISSION_ID = "01ABCDEFGHJKMNPQRSTVWXYZ00"
SAMPLE_MID8 = "01ABCDEF"
SAMPLE_SLUG = "sample-mission-01ABCDEF"
SAMPLE_WP_ID = "WP01"


def _write_meta(
    feature_dir: Path,
    *,
    mission_id: str,
    mission_slug: str | None = None,
    friendly_name: str | None = None,
    mission_number: int | None = None,
    mission_type: str = "software-dev",
    target_branch: str = "main",
    created_at: str = "2026-05-03T00:00:00+00:00",
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "mission_id": mission_id,
        "mission_slug": mission_slug or feature_dir.name,
        "friendly_name": friendly_name or feature_dir.name,
        "mission_number": mission_number,
        "mission_type": mission_type,
        "target_branch": target_branch,
        "created_at": created_at,
    }
    (feature_dir / "meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_wp(
    feature_dir: Path,
    *,
    wp_id: str,
    title: str = "Some WP",
    dependencies: list[str] | None = None,
    requirement_refs: list[str] | None = None,
) -> None:
    tasks = feature_dir / "tasks"
    tasks.mkdir(exist_ok=True)
    deps = dependencies or []
    refs = requirement_refs or []
    body = (
        "---\n"
        f"work_package_id: {wp_id}\n"
        f"title: {title}\n"
        f"dependencies: {json.dumps(deps)}\n"
        f"requirement_refs: {json.dumps(refs)}\n"
        "subtasks: []\n"
        "agent: claude\n"
        "agent_profile: python-pedro\n"
        "role: implementer\n"
        "---\n\n"
        f"# Work Package Prompt: {title}\n"
    )
    (tasks / f"{wp_id}-test.md").write_text(body, encoding="utf-8")


def _write_event(
    feature_dir: Path,
    *,
    wp_id: str,
    from_lane: str,
    to_lane: str,
    actor: str = "claude",
    event_id: str | None = None,
    at: str = "2026-05-03T00:00:00+00:00",
    feature_slug: str | None = None,
) -> None:
    record = {
        "actor": actor,
        "at": at,
        "event_id": event_id or f"01EV{wp_id}{to_lane}",
        "evidence": None,
        "execution_mode": "code_change",
        "feature_slug": feature_slug or feature_dir.name,
        "force": False,
        "from_lane": from_lane,
        "reason": None,
        "review_ref": None,
        "to_lane": to_lane,
        "wp_id": wp_id,
    }
    line = json.dumps(record, sort_keys=True) + "\n"
    (feature_dir / "status.events.jsonl").open("a", encoding="utf-8").write(line)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Build a minimal fixture project with one mission and one WP."""
    (tmp_path / ".kittify").mkdir(parents=True, exist_ok=True)

    feature_dir = tmp_path / "kitty-specs" / SAMPLE_SLUG
    _write_meta(
        feature_dir,
        mission_id=SAMPLE_MISSION_ID,
        mission_slug=SAMPLE_SLUG,
        friendly_name="Sample Mission",
        mission_number=1,
        mission_type="software-dev",
        target_branch="main",
    )
    _write_wp(feature_dir, wp_id=SAMPLE_WP_ID, title="First Work Package")
    # Finalize with an event log so the mission is not legacy.
    _write_event(
        feature_dir,
        wp_id=SAMPLE_WP_ID,
        from_lane="planned",
        to_lane="in_progress",
        event_id="01EVWP01inprogress",
        feature_slug=SAMPLE_SLUG,
    )
    return tmp_path


def _client(project_dir: Path):
    """Build a TestClient for the FastAPI app rooted at ``project_dir``."""
    from dashboard.api import create_app
    from fastapi.testclient import TestClient

    app = create_app(project_dir=project_dir, project_token=None)
    return TestClient(app)


# ─── GET /api/missions ────────────────────────────────────────────────────────


class TestListMissions:
    """GET /api/missions → list[MissionSummary]."""

    def test_returns_200_json(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get("/api/missions")
        assert response.status_code == 200
        ctype = response.headers.get("content-type", "")
        assert ctype.startswith("application/json"), f"Unexpected content-type: {ctype!r}"

    def test_returns_non_empty_list_for_fixture_project(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get("/api/missions").json()
        assert isinstance(payload, list), "Expected a list"
        assert len(payload) >= 1, "Expected at least one mission in the fixture project"

    def test_each_item_has_required_fields(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get("/api/missions").json()
        item = payload[0]
        assert "mission_id" in item
        assert "mission_slug" in item
        assert "mid8" in item
        assert "friendly_name" in item
        assert "lane_counts" in item

    def test_each_item_has_links_self_status_workpackages(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get("/api/missions").json()
        item = payload[0]
        assert "_links" in item, "_links must be present on each MissionSummary"
        links = item["_links"]
        assert "self" in links, "_links.self must be present"
        assert "status" in links, "_links.status must be present"
        assert "workpackages" in links, "_links.workpackages must be present"
        assert "href" in links["self"], "_links.self.href must be present"


# ─── GET /api/missions/{mission_id} ───────────────────────────────────────────


class TestGetMission:
    """GET /api/missions/{mission_id} → Mission or 404/409."""

    def test_returns_200_for_known_mission_id(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get(f"/api/missions/{SAMPLE_MISSION_ID}")
        assert response.status_code == 200

    def test_response_has_required_fields(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get(f"/api/missions/{SAMPLE_MISSION_ID}").json()
        assert payload["mission_id"] == SAMPLE_MISSION_ID
        assert payload["mission_slug"] == SAMPLE_SLUG
        assert "lane_counts" in payload
        assert "_links" in payload

    def test_links_shape_on_single_mission(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get(f"/api/missions/{SAMPLE_MISSION_ID}").json()
        links = payload["_links"]
        assert "self" in links
        assert "status" in links
        assert "workpackages" in links

    def test_resolve_by_slug(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get(f"/api/missions/{SAMPLE_SLUG}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["mission_id"] == SAMPLE_MISSION_ID

    def test_returns_404_for_unknown_mission(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get("/api/missions/nonexistent-mission-id")
        assert response.status_code == 404

    def test_returns_409_for_ambiguous_mid8(self, tmp_path: Path) -> None:
        """Two missions sharing the same mid8 → 409 on mid8 lookup."""
        (tmp_path / ".kittify").mkdir(parents=True, exist_ok=True)
        # Two missions whose mission_id shares the first 8 characters.
        shared_mid8 = "01SHARED"
        _write_meta(
            tmp_path / "kitty-specs" / "alpha-mission",
            mission_id=shared_mid8 + "AAAAAAAAAAAAAAAA00",
            mission_slug="alpha-mission",
            friendly_name="Alpha",
        )
        _write_event(
            tmp_path / "kitty-specs" / "alpha-mission",
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
            feature_slug="alpha-mission",
        )
        _write_meta(
            tmp_path / "kitty-specs" / "beta-mission",
            mission_id=shared_mid8 + "BBBBBBBBBBBBBBBB00",
            mission_slug="beta-mission",
            friendly_name="Beta",
        )
        _write_event(
            tmp_path / "kitty-specs" / "beta-mission",
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
            feature_slug="beta-mission",
        )
        with _client(tmp_path) as client:
            response = client.get(f"/api/missions/{shared_mid8}")
        assert response.status_code == 409
        body = response.json()
        assert body["detail"]["error"] == "MISSION_AMBIGUOUS_SELECTOR"


# ─── GET /api/missions/{mission_id}/status ────────────────────────────────────


class TestGetMissionStatus:
    """GET /api/missions/{mission_id}/status → MissionStatus."""

    def test_returns_200(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get(f"/api/missions/{SAMPLE_MISSION_ID}/status")
        assert response.status_code == 200

    def test_response_fields(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get(f"/api/missions/{SAMPLE_MISSION_ID}/status").json()
        assert payload["mission_id"] == SAMPLE_MISSION_ID
        assert "lane_counts" in payload
        assert "done_count" in payload
        assert "total_count" in payload
        assert payload["total_count"] >= 0

    def test_links_self_and_mission(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get(f"/api/missions/{SAMPLE_MISSION_ID}/status").json()
        links = payload["_links"]
        assert "self" in links, "_links.self must be present"
        assert "mission" in links, "_links.mission must be present"

    def test_returns_404_for_unknown_mission(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get("/api/missions/unknown-id/status")
        assert response.status_code == 404


# ─── GET /api/missions/{mission_id}/workpackages ──────────────────────────────


class TestListWorkPackages:
    """GET /api/missions/{mission_id}/workpackages → list[WorkPackageSummary]."""

    def test_returns_200(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get(f"/api/missions/{SAMPLE_MISSION_ID}/workpackages")
        assert response.status_code == 200

    def test_returns_list(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get(f"/api/missions/{SAMPLE_MISSION_ID}/workpackages").json()
        assert isinstance(payload, list)

    def test_each_wp_has_assignment_and_links(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get(f"/api/missions/{SAMPLE_MISSION_ID}/workpackages").json()
        assert len(payload) >= 1, "Fixture mission should have at least one WP"
        item = payload[0]
        assert "wp_id" in item
        assert "title" in item
        assert "assignment" in item
        assert item["assignment"]["wp_id"] == SAMPLE_WP_ID
        assert "_links" in item
        assert "self" in item["_links"]
        assert "mission" in item["_links"]

    def test_returns_404_for_unknown_mission(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get("/api/missions/unknown-id/workpackages")
        assert response.status_code == 404


# ─── GET /api/missions/{mission_id}/workpackages/{wp_id} ─────────────────────


class TestGetWorkPackage:
    """GET /api/missions/{mission_id}/workpackages/{wp_id} → WorkPackage or 404."""

    def test_returns_200_for_known_wp(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get(
                f"/api/missions/{SAMPLE_MISSION_ID}/workpackages/{SAMPLE_WP_ID}"
            )
        assert response.status_code == 200

    def test_response_fields(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get(
                f"/api/missions/{SAMPLE_MISSION_ID}/workpackages/{SAMPLE_WP_ID}"
            ).json()
        assert payload["wp_id"] == SAMPLE_WP_ID
        assert "title" in payload
        assert "assignment" in payload
        assert "subtasks_done" in payload
        assert "subtasks_total" in payload
        assert "dependencies" in payload
        assert "requirement_refs" in payload

    def test_links_self_mission_workpackages(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            payload = client.get(
                f"/api/missions/{SAMPLE_MISSION_ID}/workpackages/{SAMPLE_WP_ID}"
            ).json()
        links = payload["_links"]
        assert "self" in links
        assert "mission" in links
        assert "workpackages" in links

    def test_returns_404_for_unknown_wp(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get(
                f"/api/missions/{SAMPLE_MISSION_ID}/workpackages/WP_NONEXISTENT"
            )
        assert response.status_code == 404

    def test_returns_404_for_unknown_mission(self, project_dir: Path) -> None:
        with _client(project_dir) as client:
            response = client.get(
                f"/api/missions/unknown-id/workpackages/{SAMPLE_WP_ID}"
            )
        assert response.status_code == 404

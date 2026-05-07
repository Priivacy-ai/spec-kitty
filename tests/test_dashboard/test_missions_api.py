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


# ─── Dashboard UI contract — fields the kanban modal renders ─────────────────
#
# Regression coverage for the empty-modal bug surfaced post-merge in mission
# dashboard-services-domain-migration-01KR151P. The dashboard JS reads
# task.agent (tool), task.model, task.agent_profile, task.role, task.phase,
# task.prompt_path, task.prompt_markdown, task.subtasks_done/total,
# task.dependencies. If any of these silently disappears at the API boundary
# again, the modal renders blank without any backend test failing — until
# Playwright lands (see #1008), this contract test is the durable guard.


class TestWorkPackageAssignmentAgentIdentity:
    """`assignment.agent` (tool) must round-trip from WP frontmatter."""

    def test_summary_endpoint_exposes_agent_tool_profile_role(
        self, project_dir: Path
    ) -> None:
        """Fixture WP has `agent: claude`, `agent_profile: python-pedro`, `role: implementer`.

        All three must appear on the summary endpoint; without them the
        kanban card cannot render its identity badges.
        """
        with _client(project_dir) as client:
            payload = client.get(
                f"/api/missions/{SAMPLE_MISSION_ID}/workpackages"
            ).json()
        assert payload, "fixture mission must have at least one WP"
        assignment = payload[0]["assignment"]
        # Bug: pre-fix this field did not exist on WorkPackageAssignment.
        assert "agent" in assignment, (
            "assignment.agent (tool name) is required by the kanban UI"
        )
        assert assignment["agent"] == "claude"
        assert assignment["agent_profile"] == "python-pedro"
        assert assignment["role"] == "implementer"

    def test_compound_agent_string_is_decomposed(self, tmp_path: Path) -> None:
        """A WP whose `agent` frontmatter is `tool:model:profile:role` must
        surface each part on the assignment so the modal can render four
        distinct badges."""
        feature_dir = tmp_path / "kitty-specs" / "compound-agent-mission-01XYZ"
        _write_meta(
            feature_dir,
            mission_id="01XYZAGENTMODEL00000000000",
            mission_slug="compound-agent-mission-01XYZ",
            friendly_name="Compound Agent Mission",
            mission_number=2,
        )
        # Compound form documented in the implement-review skill — the form
        # actually written to WP frontmatter by `agent action implement`.
        tasks = feature_dir / "tasks"
        tasks.mkdir(exist_ok=True)
        (tasks / "WP01-test.md").write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Compound Agent\n"
            "dependencies: []\n"
            "requirement_refs: []\n"
            "subtasks: []\n"
            "agent: \"claude:sonnet-4-6:implementer:implementer\"\n"
            "---\n",
            encoding="utf-8",
        )
        _write_event(
            feature_dir,
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
            event_id="01EVCOMPOUND",
            feature_slug="compound-agent-mission-01XYZ",
        )

        with _client(tmp_path) as client:
            payload = client.get(
                "/api/missions/01XYZAGENTMODEL00000000000/workpackages/WP01"
            ).json()
        assignment = payload["assignment"]
        assert assignment["agent"] == "claude"
        assert assignment["model"] == "sonnet-4-6"
        # The compound role/profile fall back into the explicit fields when
        # there's no separate frontmatter entry — verifies the OR fallback.
        assert assignment["agent_profile"] == "implementer"
        assert assignment["role"] == "implementer"


class TestWorkPackageDetailUIFields:
    """Detail endpoint must include phase, prompt_path, prompt_markdown.

    The dashboard JS modal reads all three. Pre-fix none were on the
    response, so the modal showed "Prompt content unavailable" with no
    identity, no phase, no source path.
    """

    def test_detail_includes_prompt_path_and_markdown(
        self, project_dir: Path
    ) -> None:
        with _client(project_dir) as client:
            payload = client.get(
                f"/api/missions/{SAMPLE_MISSION_ID}/workpackages/{SAMPLE_WP_ID}"
            ).json()
        assert "prompt_path" in payload
        assert "prompt_markdown" in payload
        assert payload["prompt_path"] is not None
        assert payload["prompt_markdown"] is not None
        # The H1 from the markdown body must round-trip (proves the file was
        # actually read, not just stubbed to empty string).
        assert "First Work Package" in payload["prompt_markdown"]

    def test_prompt_markdown_strips_yaml_frontmatter(
        self, project_dir: Path
    ) -> None:
        """The YAML frontmatter block must be stripped before sending.

        Otherwise marked.parse() in the dashboard renders the raw YAML keys
        ('work_package_id', 'dependencies', 'authoritative_surface', etc.)
        as plain text at the top of the modal — the bug surfaced post-merge.
        """
        with _client(project_dir) as client:
            payload = client.get(
                f"/api/missions/{SAMPLE_MISSION_ID}/workpackages/{SAMPLE_WP_ID}"
            ).json()
        markdown = payload["prompt_markdown"]
        assert markdown is not None
        # The body should NOT start with the frontmatter delimiter.
        assert not markdown.lstrip().startswith("---"), (
            "Frontmatter delimiter still present in prompt_markdown"
        )
        # The frontmatter keys must not appear at all in the body. The
        # structured equivalents are exposed elsewhere on the response.
        for forbidden_key in (
            "work_package_id:",
            "agent_profile:",
            "owned_files:",
            "authoritative_surface:",
        ):
            assert forbidden_key not in markdown, (
                f"YAML key {forbidden_key!r} leaked into prompt_markdown body"
            )

    def test_detail_includes_phase_field(self, project_dir: Path) -> None:
        """`phase` is the kanban-board phase grouping (e.g. "Phase 1 - Setup").

        It MAY be None when the WP frontmatter omits it, but the field must
        exist on the response.
        """
        with _client(project_dir) as client:
            payload = client.get(
                f"/api/missions/{SAMPLE_MISSION_ID}/workpackages/{SAMPLE_WP_ID}"
            ).json()
        assert "phase" in payload

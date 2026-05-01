"""Integration tests for orchestrator_api commands.

Uses CliRunner to invoke commands against a fake mission directory
with a real event log (no subprocess, no git).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from specify_cli.orchestrator_api.commands import app
from specify_cli.orchestrator_api.envelope import CONTRACT_VERSION
from specify_cli.status.models import TransitionRequest

import pytest

pytestmark = pytest.mark.git_repo

runner = CliRunner()


@pytest.fixture(autouse=True)
def _disable_status_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.status.emit as status_emit

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    monkeypatch.setattr(status_emit, "fire_dossier_sync", lambda *args, **kwargs: None)


# ── Fixtures ──────────────────────────────────────────────────────


def _make_mission(tmp_path: Path, mission_slug: str = "099-test-mission") -> tuple[Path, Path]:
    """Create a minimal mission directory with tasks.

    Returns:
        (repo_root, mission_dir)
    """
    repo_root = tmp_path / "repo"
    mission_dir = repo_root / "kitty-specs" / mission_slug
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    for wp_id in ("WP01", "WP02"):
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\ntitle: Test {wp_id}\nlane: planned\ndependencies: []\n---\n\n# {wp_id}\n",
            encoding="utf-8",
        )

    meta = {
        "mission_number": mission_slug.split("-")[0],
        "slug": mission_slug,
        "mission_slug": mission_slug,
        "friendly_name": "Test Mission",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-03-18T00:00:00+00:00",
        "status_phase": 1,
    }
    (mission_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return repo_root, mission_dir


def _valid_policy_json() -> str:
    return json.dumps(
        {
            "orchestrator_id": "test-orch",
            "orchestrator_version": "0.1.0",
            "agent_family": "claude",
            "approval_mode": "supervised",
            "sandbox_mode": "sandbox",
            "network_mode": "restricted",
            "dangerous_flags": [],
        }
    )


def _emit_event(mission_dir: Path, wp_id: str, from_lane: str, to_lane: str, actor: str = "test") -> None:
    """Helper to emit a status event directly."""
    from specify_cli.status.emit import emit_status_transition

    slug = mission_dir.parent.parent.name + "-" + mission_dir.name
    if to_lane == "in_progress" and from_lane == "planned":
        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=slug, wp_id=wp_id, to_lane="claimed", actor=actor))
        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=slug, wp_id=wp_id, to_lane="in_progress", actor=actor))
    else:
        emit_status_transition(TransitionRequest(
            feature_dir=mission_dir,
            mission_slug=slug,
            wp_id=wp_id,
            to_lane=to_lane,
            actor=actor,
        ))


def _emit_planned_to_done(mission_dir: Path, mission_slug: str, wp_id: str, actor: str = "test") -> None:
    """Transition a WP all the way to done."""
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.models import ReviewResult

    emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id=wp_id, to_lane="claimed", actor=actor))
    emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id=wp_id, to_lane="in_progress", actor=actor))
    emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id=wp_id, to_lane="for_review", actor=actor))
    emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id=wp_id, to_lane="in_review", actor=actor))
    emit_status_transition(TransitionRequest(
        feature_dir=mission_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        to_lane="done",
        actor=actor,
        evidence={
            "review": {
                "reviewer": "reviewer-agent",
                "verdict": "approved",
                "reference": "review-001",
            }
        },
        review_result=ReviewResult(
            reviewer="reviewer-agent",
            verdict="approved",
            reference="review-001",
        ),
    ))


# ── contract-version ──────────────────────────────────────────────


class TestContractVersion:
    def test_envelope_shape_and_version(self, tmp_path):
        result = runner.invoke(app, ["contract-version"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["error_code"] is None
        assert data["data"]["api_version"] == CONTRACT_VERSION
        assert "min_supported_provider_version" in data["data"]
        assert data["command"] == "orchestrator-api.contract-version"


# ── mission-state ─────────────────────────────────────────────────


class TestMissionState:
    def test_mission_state_with_event_log(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        # Emit one transition
        from specify_cli.status.emit import emit_status_transition

        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="claimed", actor="test-actor"))

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["mission-state", "--mission", mission_slug])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["mission_slug"] == mission_slug
        wps = {wp["wp_id"]: wp for wp in data["data"]["work_packages"]}
        assert "WP01" in wps
        assert wps["WP01"]["lane"] == "claimed"

    def test_mission_not_found(self, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["mission-state", "--mission", "nonexistent-mission"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error_code"] == "MISSION_NOT_FOUND"

    def test_mission_state_does_not_write_status_snapshot(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"
        status_path = mission_dir / "status.json"
        assert not status_path.exists()

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["mission-state", "--mission", mission_slug])

        assert result.exit_code == 0, result.output
        assert not status_path.exists()


# ── list-ready ────────────────────────────────────────────────────


class TestListReady:
    def test_planned_wp_with_satisfied_deps_is_ready(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["list-ready", "--mission", mission_slug])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["mission_slug"] == mission_slug
        ready = {wp["wp_id"] for wp in data["data"]["ready_work_packages"]}
        # Both WP01 and WP02 have no deps, so both should be ready
        assert "WP01" in ready
        assert "WP02" in ready

    def test_in_progress_wp_not_in_ready(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        from specify_cli.status.emit import emit_status_transition

        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="claimed", actor="test"))
        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="in_progress", actor="test"))

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["list-ready", "--mission", mission_slug])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        ready_ids = {wp["wp_id"] for wp in data["data"]["ready_work_packages"]}
        assert "WP01" not in ready_ids
        assert "WP02" in ready_ids

    def test_list_ready_does_not_write_status_snapshot(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"
        status_path = mission_dir / "status.json"
        assert not status_path.exists()

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["list-ready", "--mission", mission_slug])

        assert result.exit_code == 0, result.output
        assert not status_path.exists()


# ── start-implementation ──────────────────────────────────────────


class TestStartImplementation:
    def test_no_policy_returns_error(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                ["start-implementation", "--mission", "099-test-mission", "--wp", "WP01", "--actor", "claude"],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "POLICY_METADATA_REQUIRED"

    def test_planned_wp_composite_transition(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["from_lane"] == "planned"
        assert data["data"]["to_lane"] == "in_progress"
        assert data["data"]["policy_metadata_recorded"] is True
        assert data["data"]["no_op"] is False
        from specify_cli.status.store import read_events

        events = read_events(mission_dir)
        assert [(event.from_lane, event.to_lane) for event in events] == [
            ("planned", "claimed"),
            ("claimed", "in_progress"),
        ]

    def test_claimed_same_actor_resumes_to_in_progress(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        from specify_cli.status.emit import emit_status_transition

        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="claimed", actor="claude"))

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["from_lane"] == "claimed"
        assert data["data"]["to_lane"] == "in_progress"
        assert data["data"]["no_op"] is False

    def test_already_in_progress_same_actor_noop(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        # First put WP01 in_progress as claude
        from specify_cli.status.emit import emit_status_transition

        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="claimed", actor="claude"))
        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="in_progress", actor="claude"))

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["no_op"] is True

    def test_already_claimed_different_actor_rejected(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        # Put WP01 in claimed state as "other-agent"
        from specify_cli.status.emit import emit_status_transition

        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="claimed", actor="other-agent"))

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "WP_ALREADY_CLAIMED"


# ── start-review ──────────────────────────────────────────────────


class TestStartReview:
    def test_no_review_ref_rejected(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-review",
                    "--mission",
                    "099-test-mission",
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "TRANSITION_REJECTED"

    def test_valid_start_review(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        # Put WP01 in for_review state
        from specify_cli.status.emit import emit_status_transition

        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="claimed", actor="claude"))
        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="in_progress", actor="claude"))
        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug=mission_slug, wp_id="WP01", to_lane="for_review", actor="claude"))

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-review",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--actor",
                    "reviewer",
                    "--policy",
                    _valid_policy_json(),
                    "--review-ref",
                    "review-feedback-001",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["to_lane"] == "in_review"
        assert data["data"]["policy_metadata_recorded"] is True


# ── transition ────────────────────────────────────────────────────


class TestTransition:
    def test_invalid_transition_rejected(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            # planned -> done is not a valid transition
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--to",
                    "done",
                    "--actor",
                    "claude",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "TRANSITION_REJECTED"

    def test_terminal_transition_no_policy_required(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            # planned -> canceled should succeed without --policy
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--to",
                    "canceled",
                    "--actor",
                    "claude",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["to_lane"] == "canceled"
        assert data["data"]["policy_metadata_recorded"] is False

    def test_run_affecting_transition_requires_policy(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--to",
                    "claimed",
                    "--actor",
                    "claude",
                    # no --policy
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "POLICY_METADATA_REQUIRED"

    def test_transition_passes_review_handoff_flags_to_status_emit(self, tmp_path):
        repo_root, _ = _make_mission(tmp_path, "099-test-feature")
        mission_slug = "099-test-feature"

        emit_mock = MagicMock()
        with (
            patch(
                "specify_cli.orchestrator_api.commands._get_main_repo_root",
                return_value=repo_root,
            ),
            patch(
                "specify_cli.status.emit.emit_status_transition",
                emit_mock,
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--to",
                    "for_review",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                    "--subtasks-complete",
                    "--implementation-evidence-present",
                ],
            )

        assert result.exit_code == 0, result.output
        req = emit_mock.call_args.args[0]
        assert req.subtasks_complete is True
        assert req.implementation_evidence_present is True

    def test_transition_passes_done_evidence_to_status_emit(self, tmp_path):
        repo_root, _ = _make_mission(tmp_path, "099-test-feature")
        mission_slug = "099-test-feature"

        emit_mock = MagicMock()
        with (
            patch(
                "specify_cli.orchestrator_api.commands._get_main_repo_root",
                return_value=repo_root,
            ),
            patch(
                "specify_cli.status.emit.emit_status_transition",
                emit_mock,
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--to",
                    "done",
                    "--actor",
                    "reviewer",
                    "--review-ref",
                    "review-001",
                    "--evidence-json",
                    '{"review":{"reviewer":"reviewer","verdict":"approved","reference":"review-001"}}',
                ],
            )

        assert result.exit_code == 0, result.output
        req = emit_mock.call_args.args[0]
        assert req.review_ref == "review-001"
        assert req.evidence == {
            "review": {
                "reviewer": "reviewer",
                "verdict": "approved",
                "reference": "review-001",
            }
        }

    def test_transition_rejects_invalid_evidence_json(self, tmp_path):
        repo_root, _ = _make_mission(tmp_path, "099-test-feature")
        mission_slug = "099-test-feature"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--to",
                    "done",
                    "--actor",
                    "reviewer",
                    "--evidence-json",
                    '{"review":',
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "USAGE_ERROR"


# ── append-history ────────────────────────────────────────────────


class TestAppendHistory:
    def test_appends_entry_and_returns_history_id(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        with (
            patch(
                "specify_cli.orchestrator_api.commands._get_main_repo_root",
                return_value=repo_root,
            ),
            patch(
                "specify_cli.git.commit_helpers.safe_commit",
                return_value=True,
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "append-history",
                    "--mission",
                    mission_slug,
                    "--wp",
                    "WP01",
                    "--actor",
                    "claude",
                    "--note",
                    "Started implementation",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["history_entry_id"].startswith("hist-")
        assert data["data"]["wp_id"] == "WP01"

    def test_wp_not_found_error(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "append-history",
                    "--mission",
                    "099-test-mission",
                    "--wp",
                    "WP99",
                    "--actor",
                    "claude",
                    "--note",
                    "nonexistent",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "WP_NOT_FOUND"


# ── accept-mission ────────────────────────────────────────────────


class TestAcceptMission:
    def test_all_done_accepted(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        # Transition all WPs to done
        _emit_planned_to_done(mission_dir, mission_slug, "WP01")
        _emit_planned_to_done(mission_dir, mission_slug, "WP02")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "accept-mission",
                    "--mission",
                    mission_slug,
                    "--actor",
                    "claude",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["mission_slug"] == mission_slug
        assert data["data"]["accepted"] is True

        # Verify meta.json was written
        meta = json.loads((mission_dir / "meta.json").read_text())
        assert "accepted_at" in meta
        assert meta["accepted_by"] == "claude"

    def test_incomplete_wps_returns_error(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        # Only do WP01
        _emit_planned_to_done(mission_dir, mission_slug, "WP01")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "accept-mission",
                    "--mission",
                    mission_slug,
                    "--actor",
                    "claude",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "MISSION_NOT_READY"
        assert "WP02" in data["data"]["incomplete_wps"]


# ── merge-mission ─────────────────────────────────────────────────


class TestMergeMission:
    def test_preflight_fails_returns_error(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        mock_preflight = MagicMock()
        mock_preflight.target_branch = "main"
        mock_preflight.errors = ["lanes.json is missing for this mission"]

        with (
            patch(
                "specify_cli.orchestrator_api.commands._get_main_repo_root",
                return_value=repo_root,
            ),
            patch(
                "specify_cli.orchestrator_api.commands._build_merge_preflight",
                return_value=mock_preflight,
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "merge-mission",
                    "--mission",
                    mission_slug,
                    "--target",
                    "main",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "PREFLIGHT_FAILED"
        assert "lanes.json" in data["data"]["errors"][0]

    def test_merge_success(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        mock_preflight = MagicMock()
        mock_preflight.target_branch = "main"
        mock_preflight.errors = []

        with (
            patch(
                "specify_cli.orchestrator_api.commands._get_main_repo_root",
                return_value=repo_root,
            ),
            patch(
                "specify_cli.orchestrator_api.commands._build_merge_preflight",
                return_value=mock_preflight,
            ),
            patch(
                "specify_cli.orchestrator_api.commands._execute_lane_merge",
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "merge-mission",
                    "--mission",
                    mission_slug,
                    "--target",
                    "main",
                    "--strategy",
                    "merge",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["mission_slug"] == mission_slug
        assert data["data"]["merged"] is True
        assert data["data"]["target_branch"] == "main"
        assert data["data"]["strategy"] == "merge"

    def test_rebase_strategy_success(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        mock_preflight = MagicMock()
        mock_preflight.target_branch = "main"
        mock_preflight.errors = []

        with (
            patch(
                "specify_cli.orchestrator_api.commands._get_main_repo_root",
                return_value=repo_root,
            ),
            patch(
                "specify_cli.orchestrator_api.commands._build_merge_preflight",
                return_value=mock_preflight,
            ),
            patch(
                "specify_cli.orchestrator_api.commands._execute_lane_merge",
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "merge-mission",
                    "--mission",
                    mission_slug,
                    "--target",
                    "main",
                    "--strategy",
                    "rebase",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["strategy"] == "rebase"

    def test_unsupported_strategy_rejected(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "merge-mission",
                    "--mission",
                    mission_slug,
                    "--target",
                    "main",
                    "--strategy",
                    "octopus",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "UNSUPPORTED_STRATEGY"
        assert data["data"]["strategy"] == "octopus"
        assert "merge" in data["data"]["supported"]


# ── contract-version (version mismatch) ───────────────────────────


class TestContractVersionMismatch:
    def test_compatible_provider_version_succeeds(self, tmp_path):
        from specify_cli.orchestrator_api.envelope import MIN_PROVIDER_VERSION

        result = runner.invoke(
            app,
            ["contract-version", "--provider-version", MIN_PROVIDER_VERSION],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["api_version"] is not None

    def test_below_min_provider_version_returns_mismatch(self, tmp_path):
        result = runner.invoke(
            app,
            ["contract-version", "--provider-version", "0.0.1"],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "CONTRACT_VERSION_MISMATCH"
        assert "provider_version" in data["data"]
        assert "min_supported_provider_version" in data["data"]

    def test_invalid_provider_version_returns_mismatch(self, tmp_path):
        result = runner.invoke(
            app,
            ["contract-version", "--provider-version", "not-a-version"],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "CONTRACT_VERSION_MISMATCH"


# ── WP_NOT_FOUND for state-mutating commands ──────────────────────


class TestWPNotFound:
    def test_start_implementation_ghost_wp_rejected(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--mission",
                    "099-test-mission",
                    "--wp",
                    "WP99",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "WP_NOT_FOUND"

    def test_start_review_ghost_wp_rejected(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-review",
                    "--mission",
                    "099-test-mission",
                    "--wp",
                    "WP99",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                    "--review-ref",
                    "ref-001",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "WP_NOT_FOUND"

    def test_transition_ghost_wp_rejected(self, tmp_path):
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--mission",
                    "099-test-mission",
                    "--wp",
                    "WP99",
                    "--to",
                    "canceled",
                    "--actor",
                    "claude",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "WP_NOT_FOUND"


# ── mission-state with no events ──────────────────────────────────


class TestMissionStateNoEvents:
    def test_untouched_wps_appear_as_planned(self, tmp_path):
        """WPs with no events still appear in mission-state with lane=planned."""
        repo_root, mission_dir = _make_mission(tmp_path, "099-test-mission")
        mission_slug = "099-test-mission"

        # No events emitted at all
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["mission-state", "--mission", mission_slug])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        wps = {wp["wp_id"]: wp for wp in data["data"]["work_packages"]}
        assert "WP01" in wps
        assert "WP02" in wps
        assert wps["WP01"]["lane"] == "planned"
        assert wps["WP02"]["lane"] == "planned"


# ── Suffixed WP filenames (P0 regression) ─────────────────────────


def _make_mission_with_suffixed_wps(tmp_path: Path, mission_slug: str = "040-test-mission") -> tuple[Path, Path]:
    """Create a mission directory whose WP files have hyphen-suffixed names.

    e.g. WP07-adapter-implementations.md instead of WP07.md
    """
    repo_root = tmp_path / "repo"
    mission_dir = repo_root / "kitty-specs" / mission_slug
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    (tasks_dir / "WP01-core-setup.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Core Setup\nlane: planned\ndependencies: []\n---\n\n# WP01\n",
        encoding="utf-8",
    )
    (tasks_dir / "WP07-adapter-implementations.md").write_text(
        "---\nwork_package_id: WP07\ntitle: Adapter Implementations\nlane: planned\ndependencies: []\n---\n\n# WP07\n",
        encoding="utf-8",
    )
    # Also include a non-WP file to verify it is excluded
    (tasks_dir / "README.md").write_text("# Tasks\n", encoding="utf-8")

    (mission_dir / "meta.json").write_text(json.dumps({"status_phase": 1}), encoding="utf-8")
    return repo_root, mission_dir


class TestSuffixedWPFilenames:
    """Commands must accept WP IDs whose task files have hyphen-suffixed names."""

    def test_start_implementation_accepts_suffixed_file(self, tmp_path):
        repo_root, mission_dir = _make_mission_with_suffixed_wps(tmp_path)
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--mission",
                    "040-test-mission",
                    "--wp",
                    "WP07",
                    "--actor",
                    "claude",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["wp_id"] == "WP07"
        # prompt_path must point to the real (suffixed) file
        assert "WP07-adapter-implementations" in data["data"]["prompt_path"]

    def test_transition_accepts_suffixed_file(self, tmp_path):
        from specify_cli.status.emit import emit_status_transition

        repo_root, mission_dir = _make_mission_with_suffixed_wps(tmp_path)
        # Put WP07 in_progress so we can cancel it
        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug="040-test-mission", wp_id="WP07", to_lane="claimed", actor="claude"))
        emit_status_transition(TransitionRequest(feature_dir=mission_dir, mission_slug="040-test-mission", wp_id="WP07", to_lane="in_progress", actor="claude"))

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--mission",
                    "040-test-mission",
                    "--wp",
                    "WP07",
                    "--to",
                    "canceled",
                    "--actor",
                    "claude",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["wp_id"] == "WP07"
        assert data["data"]["to_lane"] == "canceled"

    def test_mission_state_emits_canonical_ids_only(self, tmp_path):
        """mission-state must not include raw filename stems like 'WP07-adapter-implementations'."""
        repo_root, _ = _make_mission_with_suffixed_wps(tmp_path)
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["mission-state", "--mission", "040-test-mission"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        wp_ids = {wp["wp_id"] for wp in data["data"]["work_packages"]}

        # Canonical IDs must be present
        assert "WP01" in wp_ids
        assert "WP07" in wp_ids

        # Raw stems must NOT appear
        assert "WP01-core-setup" not in wp_ids
        assert "WP07-adapter-implementations" not in wp_ids

        # Non-WP file must NOT appear
        assert "README" not in wp_ids


# ── JSON-only stdout contract ─────────────────────────────────────


class TestJsonOnlyStdoutContract:
    """Orchestrator-api commands must emit exactly one JSON object on stdout.

    Even when sync/event fan-out emits warnings (e.g. read-only filesystem),
    those warnings must go to stderr — never polluting stdout.  The
    ``sync/emitter.py`` console is ``Console(stderr=True)``, so in a real
    terminal warnings go to fd 2.  CliRunner merges both streams into
    ``result.output``, so these tests validate the contract by asserting
    the *last* line of output is valid JSON (the envelope) and confirming
    the envelope structure.
    """

    def test_start_implementation_last_line_is_valid_json(self, tmp_path):
        """Even if non-JSON diagnostic lines precede the envelope,
        the final line must be the JSON envelope."""
        repo_root, mission_dir = _make_mission(tmp_path)

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--mission",
                    "099-test-mission",
                    "--wp",
                    "WP01",
                    "--actor",
                    "test-agent",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        # The canonical envelope is always the last non-empty line
        last_line = result.output.strip().rsplit("\n", 1)[-1]
        data = json.loads(last_line)
        assert data["success"] is True
        assert data["data"]["wp_id"] == "WP01"

    def test_stdout_is_single_json_object(self, tmp_path):
        """Under normal conditions, output must be exactly one JSON object."""
        repo_root, mission_dir = _make_mission(tmp_path)

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--mission",
                    "099-test-mission",
                    "--wp",
                    "WP01",
                    "--actor",
                    "test-agent",
                    "--policy",
                    _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        stripped = result.output.strip()
        # Must parse as a single JSON object (no extra data)
        data = json.loads(stripped)
        assert isinstance(data, dict)
        assert data["command"] == "orchestrator-api.start-implementation"


# ── Old command names must fail ───────────────────────────────────


class TestOldCommandNamesFail:
    """Old feature-era command names must fail as unknown commands."""

    def test_feature_state_rejected(self):
        result = runner.invoke(app, ["feature-state", "--mission", "dummy"])
        assert result.exit_code != 0

    def test_accept_feature_rejected(self):
        result = runner.invoke(app, ["accept-feature", "--mission", "dummy"])
        assert result.exit_code != 0

    def test_merge_feature_rejected(self):
        result = runner.invoke(app, ["merge-feature", "--mission", "dummy"])
        assert result.exit_code != 0


# ── Old --feature flag must fail ──────────────────────────────────


class TestOldFeatureFlagFails:
    """The --feature flag must no longer be accepted on any command."""

    def test_mission_state_rejects_feature_flag(self, tmp_path):
        result = runner.invoke(app, ["mission-state", "--feature", "dummy"])
        assert result.exit_code != 0

    def test_list_ready_rejects_feature_flag(self, tmp_path):
        result = runner.invoke(app, ["list-ready", "--feature", "dummy"])
        assert result.exit_code != 0

    def test_start_implementation_rejects_feature_flag(self, tmp_path):
        result = runner.invoke(
            app,
            [
                "start-implementation",
                "--feature",
                "dummy",
                "--wp",
                "WP01",
                "--actor",
                "claude",
                "--policy",
                _valid_policy_json(),
            ],
        )
        assert result.exit_code != 0

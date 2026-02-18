"""Integration tests for orchestrator_api commands.

Uses CliRunner to invoke commands against a fake feature directory
with a real event log (no subprocess, no git).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.orchestrator_api.commands import app
from specify_cli.orchestrator_api.envelope import CONTRACT_VERSION

runner = CliRunner()


# ── Fixtures ──────────────────────────────────────────────────────


def _make_feature(tmp_path: Path, feature_slug: str = "099-test-feature") -> tuple[Path, Path]:
    """Create a minimal feature directory with tasks.

    Returns:
        (repo_root, feature_dir)
    """
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    for wp_id in ("WP01", "WP02"):
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\ntitle: Test {wp_id}\n"
            f"lane: planned\ndependencies: []\n---\n\n# {wp_id}\n",
            encoding="utf-8",
        )

    (feature_dir / "meta.json").write_text(
        json.dumps({"status_phase": 1}), encoding="utf-8"
    )
    return repo_root, feature_dir


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


def _emit_event(feature_dir: Path, wp_id: str, from_lane: str, to_lane: str, actor: str = "test") -> None:
    """Helper to emit a status event directly."""
    from specify_cli.status.emit import emit_status_transition

    if to_lane == "in_progress" and from_lane == "planned":
        emit_status_transition(feature_dir, feature_dir.parent.parent.name + "-" + feature_dir.name,
                               wp_id, "claimed", actor)
        emit_status_transition(feature_dir, feature_dir.parent.parent.name + "-" + feature_dir.name,
                               wp_id, "in_progress", actor)
    else:
        emit_status_transition(
            feature_dir,
            feature_dir.parent.parent.name + "-" + feature_dir.name,
            wp_id,
            to_lane,
            actor,
        )


def _emit_planned_to_done(feature_dir: Path, feature_slug: str, wp_id: str, actor: str = "test") -> None:
    """Transition a WP all the way to done."""
    from specify_cli.status.emit import emit_status_transition

    emit_status_transition(feature_dir, feature_slug, wp_id, "claimed", actor)
    emit_status_transition(feature_dir, feature_slug, wp_id, "in_progress", actor)
    emit_status_transition(feature_dir, feature_slug, wp_id, "for_review", actor)
    emit_status_transition(
        feature_dir, feature_slug, wp_id, "done", actor,
        evidence={
            "review": {
                "reviewer": "reviewer-agent",
                "verdict": "approved",
                "reference": "review-001",
            }
        },
    )


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


# ── feature-state ─────────────────────────────────────────────────


class TestFeatureState:
    def test_feature_state_with_event_log(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        # Emit one transition
        from specify_cli.status.emit import emit_status_transition
        emit_status_transition(feature_dir, feature_slug, "WP01", "claimed", "test-actor")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["feature-state", "--feature", feature_slug])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["feature_slug"] == feature_slug
        wps = {wp["wp_id"]: wp for wp in data["data"]["work_packages"]}
        assert "WP01" in wps
        assert wps["WP01"]["lane"] == "claimed"

    def test_feature_not_found(self, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["feature-state", "--feature", "nonexistent-feature"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error_code"] == "FEATURE_NOT_FOUND"


# ── list-ready ────────────────────────────────────────────────────


class TestListReady:
    def test_planned_wp_with_satisfied_deps_is_ready(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["list-ready", "--feature", feature_slug])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        ready = {wp["wp_id"] for wp in data["data"]["ready_work_packages"]}
        # Both WP01 and WP02 have no deps, so both should be ready
        assert "WP01" in ready
        assert "WP02" in ready

    def test_in_progress_wp_not_in_ready(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        from specify_cli.status.emit import emit_status_transition
        emit_status_transition(feature_dir, feature_slug, "WP01", "claimed", "test")
        emit_status_transition(feature_dir, feature_slug, "WP01", "in_progress", "test")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(app, ["list-ready", "--feature", feature_slug])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        ready_ids = {wp["wp_id"] for wp in data["data"]["ready_work_packages"]}
        assert "WP01" not in ready_ids
        assert "WP02" in ready_ids


# ── start-implementation ──────────────────────────────────────────


class TestStartImplementation:
    def test_no_policy_returns_error(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                ["start-implementation", "--feature", "099-test-feature", "--wp", "WP01", "--actor", "claude"],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "POLICY_METADATA_REQUIRED"

    def test_planned_wp_composite_transition(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--feature", feature_slug,
                    "--wp", "WP01",
                    "--actor", "claude",
                    "--policy", _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["from_lane"] == "planned"
        assert data["data"]["to_lane"] == "in_progress"
        assert data["data"]["policy_metadata_recorded"] is True
        assert data["data"]["no_op"] is False

    def test_already_in_progress_same_actor_noop(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        # First put WP01 in_progress as claude
        from specify_cli.status.emit import emit_status_transition
        emit_status_transition(feature_dir, feature_slug, "WP01", "claimed", "claude")
        emit_status_transition(feature_dir, feature_slug, "WP01", "in_progress", "claude")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--feature", feature_slug,
                    "--wp", "WP01",
                    "--actor", "claude",
                    "--policy", _valid_policy_json(),
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["no_op"] is True

    def test_already_claimed_different_actor_rejected(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        # Put WP01 in claimed state as "other-agent"
        from specify_cli.status.emit import emit_status_transition
        emit_status_transition(feature_dir, feature_slug, "WP01", "claimed", "other-agent")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-implementation",
                    "--feature", feature_slug,
                    "--wp", "WP01",
                    "--actor", "claude",
                    "--policy", _valid_policy_json(),
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "WP_ALREADY_CLAIMED"


# ── start-review ──────────────────────────────────────────────────


class TestStartReview:
    def test_no_review_ref_rejected(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-review",
                    "--feature", "099-test-feature",
                    "--wp", "WP01",
                    "--actor", "claude",
                    "--policy", _valid_policy_json(),
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "TRANSITION_REJECTED"

    def test_valid_start_review(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        # Put WP01 in for_review state
        from specify_cli.status.emit import emit_status_transition
        emit_status_transition(feature_dir, feature_slug, "WP01", "claimed", "claude")
        emit_status_transition(feature_dir, feature_slug, "WP01", "in_progress", "claude")
        emit_status_transition(feature_dir, feature_slug, "WP01", "for_review", "claude")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "start-review",
                    "--feature", feature_slug,
                    "--wp", "WP01",
                    "--actor", "reviewer",
                    "--policy", _valid_policy_json(),
                    "--review-ref", "review-feedback-001",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["to_lane"] == "in_progress"
        assert data["data"]["policy_metadata_recorded"] is True


# ── transition ────────────────────────────────────────────────────


class TestTransition:
    def test_invalid_transition_rejected(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            # planned → done is not a valid transition
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--feature", feature_slug,
                    "--wp", "WP01",
                    "--to", "done",
                    "--actor", "claude",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "TRANSITION_REJECTED"

    def test_terminal_transition_no_policy_required(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            # planned → canceled should succeed without --policy
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--feature", feature_slug,
                    "--wp", "WP01",
                    "--to", "canceled",
                    "--actor", "claude",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["to_lane"] == "canceled"
        assert data["data"]["policy_metadata_recorded"] is False

    def test_run_affecting_transition_requires_policy(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "transition",
                    "--feature", feature_slug,
                    "--wp", "WP01",
                    "--to", "claimed",
                    "--actor", "claude",
                    # no --policy
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "POLICY_METADATA_REQUIRED"


# ── append-history ────────────────────────────────────────────────


class TestAppendHistory:
    def test_appends_entry_and_returns_history_id(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ), patch(
            "specify_cli.git.commit_helpers.safe_commit",
            return_value=True,
        ):
            result = runner.invoke(
                app,
                [
                    "append-history",
                    "--feature", feature_slug,
                    "--wp", "WP01",
                    "--actor", "claude",
                    "--note", "Started implementation",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["history_entry_id"].startswith("hist-")
        assert data["data"]["wp_id"] == "WP01"

    def test_wp_not_found_error(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "append-history",
                    "--feature", "099-test-feature",
                    "--wp", "WP99",
                    "--actor", "claude",
                    "--note", "nonexistent",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "WP_NOT_FOUND"


# ── accept-feature ────────────────────────────────────────────────


class TestAcceptFeature:
    def test_all_done_accepted(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        # Transition all WPs to done
        _emit_planned_to_done(feature_dir, feature_slug, "WP01")
        _emit_planned_to_done(feature_dir, feature_slug, "WP02")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "accept-feature",
                    "--feature", feature_slug,
                    "--actor", "claude",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["accepted"] is True

        # Verify meta.json was written
        meta = json.loads((feature_dir / "meta.json").read_text())
        assert "accepted_at" in meta
        assert meta["accepted_by"] == "claude"

    def test_incomplete_wps_returns_error(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        # Only do WP01
        _emit_planned_to_done(feature_dir, feature_slug, "WP01")

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ):
            result = runner.invoke(
                app,
                [
                    "accept-feature",
                    "--feature", feature_slug,
                    "--actor", "claude",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "FEATURE_NOT_READY"
        assert "WP02" in data["data"]["incomplete_wps"]


# ── merge-feature ─────────────────────────────────────────────────


class TestMergeFeature:
    def test_preflight_fails_returns_error(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        mock_preflight = MagicMock()
        mock_preflight.passed = False
        mock_preflight.errors = ["Missing worktree for WP01"]

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ), patch(
            "specify_cli.orchestrator_api.commands.run_preflight",
            return_value=mock_preflight,
        ), patch(
            "specify_cli.orchestrator_api.commands.get_merge_order",
            return_value=[],
        ):
            result = runner.invoke(
                app,
                [
                    "merge-feature",
                    "--feature", feature_slug,
                    "--target", "main",
                ],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error_code"] == "PREFLIGHT_FAILED"
        assert "Missing worktree" in data["data"]["errors"][0]

    def test_merge_success(self, tmp_path):
        repo_root, feature_dir = _make_feature(tmp_path, "099-test-feature")
        feature_slug = "099-test-feature"

        mock_preflight = MagicMock()
        mock_preflight.passed = True
        mock_preflight.errors = []

        with patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ), patch(
            "specify_cli.orchestrator_api.commands.run_preflight",
            return_value=mock_preflight,
        ), patch(
            "specify_cli.orchestrator_api.commands.get_merge_order",
            return_value=[],
        ):
            result = runner.invoke(
                app,
                [
                    "merge-feature",
                    "--feature", feature_slug,
                    "--target", "main",
                    "--strategy", "merge",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["merged"] is True
        assert data["data"]["target_branch"] == "main"
        assert data["data"]["strategy"] == "merge"

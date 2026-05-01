"""Tests for WP02: verdict guard + lane guard UX improvements.

Covers:
- T007 / T008: _get_latest_review_cycle_verdict helper and unknown-verdict warning
- T009: force-approve blocked when verdict: rejected
- T010: --skip-review-artifact-check bypasses the rejected-verdict guard
- T011 / T012 / T013: lane guard names the planning branch (or falls back for legacy)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import (
    _get_latest_review_cycle_verdict,
    _VALID_VERDICTS,
    app,
)
from specify_cli.status.store import append_event
from specify_cli.status.models import StatusEvent, Lane

pytestmark = pytest.mark.fast

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_review_cycle(wp_dir: Path, cycle_n: int, verdict: str) -> Path:
    """Write a review-cycle-N.md with the given verdict."""
    wp_dir.mkdir(parents=True, exist_ok=True)
    artifact = wp_dir / f"review-cycle-{cycle_n}.md"
    artifact.write_text(
        f"---\n"
        f"cycle_number: {cycle_n}\n"
        f"mission_slug: test-mission\n"
        f"reviewed_at: '2026-04-30T12:00:00Z'\n"
        f"reviewer_agent: test-reviewer\n"
        f"verdict: {verdict}\n"
        f"wp_id: WP01\n"
        f"---\n\nReview body.\n",
        encoding="utf-8",
    )
    return artifact


def _build_wp_file(tmp_path: Path, mission_slug: str, wp_id: str) -> tuple[Path, Path]:
    """Create minimal WP + feature structure.

    Returns (feature_dir, wp_file_path).
    """
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kittify").mkdir(exist_ok=True)

    wp_file = tasks_dir / f"{wp_id}-test.md"
    wp_file.write_text(
        f"---\n"
        f"work_package_id: {wp_id}\n"
        f"title: Test {wp_id}\n"
        f"execution_mode: code_change\n"
        f"agent: testbot\n"
        f"owned_files:\n  - src/{wp_id.lower()}/**\n"
        f"authoritative_surface: src/{wp_id.lower()}/\n"
        f"---\n\n# {wp_id}\n\n## Activity Log\n",
        encoding="utf-8",
    )
    return feature_dir, wp_file


def _seed_wp_event(feature_dir: Path, wp_id: str, to_lane: str) -> None:
    """Seed a WP event so the canonical event log knows the WP exists."""
    event = StatusEvent(
        event_id=f"test-{wp_id}-{to_lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(to_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


# ---------------------------------------------------------------------------
# T007: _get_latest_review_cycle_verdict helper
# ---------------------------------------------------------------------------


class TestGetLatestReviewCycleVerdict:
    """Unit tests for the _get_latest_review_cycle_verdict helper."""

    def test_returns_none_none_when_no_artifacts(self, tmp_path: Path) -> None:
        """Empty wp_dir returns (None, None)."""
        wp_dir = tmp_path / "WP01-test"
        wp_dir.mkdir()
        verdict, path = _get_latest_review_cycle_verdict(wp_dir)
        assert verdict is None
        assert path is None

    def test_reads_verdict_from_single_cycle(self, tmp_path: Path) -> None:
        """Single review-cycle returns its verdict."""
        wp_dir = tmp_path / "WP01-test"
        artifact = _write_review_cycle(wp_dir, 1, "rejected")
        verdict, path = _get_latest_review_cycle_verdict(wp_dir)
        assert verdict == "rejected"
        assert path == artifact

    def test_picks_highest_numbered_cycle(self, tmp_path: Path) -> None:
        """When multiple cycles exist, the highest-numbered one wins."""
        wp_dir = tmp_path / "WP01-test"
        _write_review_cycle(wp_dir, 1, "rejected")
        cycle2 = _write_review_cycle(wp_dir, 2, "approved")
        verdict, path = _get_latest_review_cycle_verdict(wp_dir)
        assert verdict == "approved"
        assert path == cycle2

    def test_returns_none_artifact_when_frontmatter_absent(self, tmp_path: Path) -> None:
        """Artifact without frontmatter returns (None, artifact_path)."""
        wp_dir = tmp_path / "WP01-test"
        wp_dir.mkdir()
        artifact = wp_dir / "review-cycle-1.md"
        artifact.write_text("No frontmatter here.\n", encoding="utf-8")
        verdict, path = _get_latest_review_cycle_verdict(wp_dir)
        assert verdict is None
        assert path == artifact

    def test_valid_verdicts_frozenset_contents(self) -> None:
        """_VALID_VERDICTS contains the four canonical values."""
        assert "approved" in _VALID_VERDICTS
        assert "approved_after_orchestrator_fix" in _VALID_VERDICTS
        assert "arbiter_override" in _VALID_VERDICTS
        assert "rejected" in _VALID_VERDICTS


# ---------------------------------------------------------------------------
# T008: unknown-verdict warning
# ---------------------------------------------------------------------------


class TestUnknownVerdictWarning:
    """Unknown verdict values produce a warning, not a block."""

    def test_unknown_verdict_emits_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A verdict not in _VALID_VERDICTS produces a logger.warning."""
        wp_dir = tmp_path / "WP01-test"
        _write_review_cycle(wp_dir, 1, "super_approved")  # not in _VALID_VERDICTS
        with caplog.at_level(logging.WARNING, logger="specify_cli.cli.commands.agent.tasks"):
            verdict, _ = _get_latest_review_cycle_verdict(wp_dir)
        assert verdict == "super_approved"
        assert any("unrecognized verdict" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# T009 + T010: verdict guard in move_task  (decorator-style patches)
# ---------------------------------------------------------------------------


class TestVerdictGuardInMoveTask:
    """move_task blocks force-approve/force-done when verdict == rejected."""

    @patch("specify_cli.cli.commands.agent.tasks.safe_commit")
    @patch("specify_cli.cli.commands.agent.tasks.emit_status_transition")
    @patch("specify_cli.cli.commands.agent.tasks.read_events")
    @patch("specify_cli.cli.commands.agent.tasks.feature_status_lock")
    @patch("specify_cli.cli.commands.agent.tasks._validate_ready_for_review")
    @patch("specify_cli.cli.commands.agent.tasks._check_unchecked_subtasks")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.locate_work_package")
    @patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning")
    @patch("specify_cli.cli.commands.agent.tasks.get_auto_commit_default", return_value=False)
    def test_force_approve_blocked_by_rejected_verdict(
        self,
        _mock_auto_commit: MagicMock,
        _mock_sparse: MagicMock,
        mock_locate_wp: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        mock_unchecked: MagicMock,
        mock_review_valid: MagicMock,
        mock_lock: MagicMock,
        mock_read_events: MagicMock,
        mock_emit: MagicMock,
        mock_safe_commit: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Force-approve exits 1 when latest review artifact has verdict: rejected."""
        mission_slug = "test-mission-001"
        wp_id = "WP01"
        feature_dir, wp_file = _build_wp_file(tmp_path, mission_slug, wp_id)
        _seed_wp_event(feature_dir, wp_id, "in_review")

        # Write a review-cycle-1.md with verdict: rejected inside the WP sub-dir
        wp_dir = wp_file.parent / wp_file.stem  # tasks/WP01-test/
        _write_review_cycle(wp_dir, 1, "rejected")

        from specify_cli.tasks_support import WorkPackage

        mock_wp = WorkPackage(
            feature=mission_slug,
            path=wp_file,
            current_lane="in_review",
            relative_subpath=Path(f"tasks/{wp_file.name}"),
            frontmatter=f"work_package_id: {wp_id}\ntitle: Test\nagent: testbot\n",
            body="\n## Activity Log\n",
            padding="\n",
        )
        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")
        mock_unchecked.return_value = []
        mock_review_valid.return_value = (True, [])
        mock_lock.return_value.__enter__ = MagicMock(return_value=None)
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        mock_locate_wp.return_value = mock_wp

        from specify_cli.status.store import read_events as _real_re
        mock_read_events.return_value = _real_re(feature_dir)
        mock_emit.return_value = MagicMock()

        result = runner.invoke(
            app,
            ["move-task", wp_id, "--to", "approved", "--force", "--mission", mission_slug, "--no-auto-commit"],
        )

        assert result.exit_code == 1, f"Expected exit 1, got {result.exit_code}. Output:\n{result.output}"
        assert "review-cycle-1.md" in result.output, f"Expected artifact name in output:\n{result.output}"
        assert "rejected" in result.output, f"Expected 'rejected' in output:\n{result.output}"

    @patch("specify_cli.cli.commands.agent.tasks.safe_commit")
    @patch("specify_cli.cli.commands.agent.tasks.emit_status_transition")
    @patch("specify_cli.cli.commands.agent.tasks.read_events")
    @patch("specify_cli.cli.commands.agent.tasks.feature_status_lock")
    @patch("specify_cli.cli.commands.agent.tasks._validate_ready_for_review")
    @patch("specify_cli.cli.commands.agent.tasks._check_unchecked_subtasks")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.locate_work_package")
    @patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning")
    @patch("specify_cli.cli.commands.agent.tasks.get_auto_commit_default", return_value=False)
    def test_force_done_blocked_by_rejected_verdict(
        self,
        _mock_auto_commit: MagicMock,
        _mock_sparse: MagicMock,
        mock_locate_wp: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        mock_unchecked: MagicMock,
        mock_review_valid: MagicMock,
        mock_lock: MagicMock,
        mock_read_events: MagicMock,
        mock_emit: MagicMock,
        mock_safe_commit: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Force-done exits 1 when latest review artifact has verdict: rejected."""
        mission_slug = "test-mission-002"
        wp_id = "WP01"
        feature_dir, wp_file = _build_wp_file(tmp_path, mission_slug, wp_id)
        _seed_wp_event(feature_dir, wp_id, "approved")

        wp_dir = wp_file.parent / wp_file.stem
        _write_review_cycle(wp_dir, 1, "rejected")

        from specify_cli.tasks_support import WorkPackage

        mock_wp = WorkPackage(
            feature=mission_slug,
            path=wp_file,
            current_lane="approved",
            relative_subpath=Path(f"tasks/{wp_file.name}"),
            frontmatter=f"work_package_id: {wp_id}\ntitle: Test\nagent: testbot\n",
            body="\n## Activity Log\n",
            padding="\n",
        )
        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")
        mock_unchecked.return_value = []
        mock_review_valid.return_value = (True, [])
        mock_lock.return_value.__enter__ = MagicMock(return_value=None)
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        mock_locate_wp.return_value = mock_wp

        from specify_cli.status.store import read_events as _real_re
        mock_read_events.return_value = _real_re(feature_dir)
        mock_emit.return_value = MagicMock()

        result = runner.invoke(
            app,
            ["move-task", wp_id, "--to", "done", "--force", "--mission", mission_slug, "--no-auto-commit"],
        )

        assert result.exit_code == 1, f"Expected exit 1. Output:\n{result.output}"
        assert "review-cycle-1.md" in result.output, f"Expected artifact name in output:\n{result.output}"


class TestSkipReviewArtifactCheck:
    """--skip-review-artifact-check suppresses the rejected-verdict block."""

    @patch("specify_cli.cli.commands.agent.tasks.safe_commit")
    @patch("specify_cli.cli.commands.agent.tasks.emit_status_transition")
    @patch("specify_cli.cli.commands.agent.tasks.read_events")
    @patch("specify_cli.cli.commands.agent.tasks.feature_status_lock")
    @patch("specify_cli.cli.commands.agent.tasks._validate_ready_for_review")
    @patch("specify_cli.cli.commands.agent.tasks._check_unchecked_subtasks")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.locate_work_package")
    @patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning")
    @patch("specify_cli.cli.commands.agent.tasks.get_auto_commit_default", return_value=False)
    def test_force_approve_allowed_with_skip_flag(
        self,
        _mock_auto_commit: MagicMock,
        _mock_sparse: MagicMock,
        mock_locate_wp: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        mock_unchecked: MagicMock,
        mock_review_valid: MagicMock,
        mock_lock: MagicMock,
        mock_read_events: MagicMock,
        mock_emit: MagicMock,
        mock_safe_commit: MagicMock,
        tmp_path: Path,
    ) -> None:
        """With --skip-review-artifact-check, rejected verdict does not block."""
        mission_slug = "test-mission-004"
        wp_id = "WP01"
        feature_dir, wp_file = _build_wp_file(tmp_path, mission_slug, wp_id)
        _seed_wp_event(feature_dir, wp_id, "in_review")

        wp_dir = wp_file.parent / wp_file.stem
        _write_review_cycle(wp_dir, 1, "rejected")

        from specify_cli.tasks_support import WorkPackage

        mock_wp = WorkPackage(
            feature=mission_slug,
            path=wp_file,
            current_lane="in_review",
            relative_subpath=Path(f"tasks/{wp_file.name}"),
            frontmatter=f"work_package_id: {wp_id}\ntitle: Test\nagent: testbot\n",
            body="\n## Activity Log\n",
            padding="\n",
        )
        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")
        mock_unchecked.return_value = []
        mock_review_valid.return_value = (True, [])
        mock_lock.return_value.__enter__ = MagicMock(return_value=None)
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        mock_locate_wp.return_value = mock_wp

        from specify_cli.status.store import read_events as _real_re
        mock_read_events.return_value = _real_re(feature_dir)
        mock_emit.return_value = MagicMock()

        result = runner.invoke(
            app,
            [
                "move-task",
                wp_id,
                "--to",
                "approved",
                "--force",
                "--skip-review-artifact-check",
                "--mission",
                mission_slug,
                "--no-auto-commit",
            ],
        )

        # Must NOT exit with the rejected-verdict guard (exit 1 with artifact name)
        # The guard message is: "Error: WP01 review-cycle-1.md has verdict: rejected."
        guard_triggered = result.exit_code == 1 and "review-cycle-1.md" in result.output and "rejected" in result.output
        assert not guard_triggered, (
            f"Verdict guard fired despite --skip-review-artifact-check.\nOutput:\n{result.output}"
        )


# ---------------------------------------------------------------------------
# T023 / T025: user-facing status command warnings
# ---------------------------------------------------------------------------


class TestTasksStatusReviewWarnings:
    """`spec-kitty agent tasks status` surfaces review artifact problems."""

    def _invoke_status(self, tmp_path: Path, mission_slug: str):
        with (
            patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.agent.tasks._find_mission_slug", return_value=mission_slug),
            patch(
                "specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out",
                return_value=(tmp_path, "main"),
            ),
            patch(
                "specify_cli.cli.commands.agent.tasks.resolve_workspace_for_wp",
                side_effect=FileNotFoundError,
            ),
            patch("specify_cli.cli.commands.agent.tasks.get_auto_commit_default", return_value=False),
        ):
            return runner.invoke(app, ["status", "--mission", mission_slug])

    def test_status_warns_for_done_wp_with_rejected_review_artifact(
        self, tmp_path: Path
    ) -> None:
        """The CLI status command checks tasks/<WP-slug>/review-cycle-N.md."""
        mission_slug = "test-status-stale-verdict"
        feature_dir, wp_file = _build_wp_file(tmp_path, mission_slug, "WP01")
        _seed_wp_event(feature_dir, "WP01", "done")

        wp_dir = wp_file.parent / wp_file.stem
        _write_review_cycle(wp_dir, 1, "rejected")

        result = self._invoke_status(tmp_path, mission_slug)

        assert result.exit_code == 0, result.output
        assert "review artifact: verdict=rejected" in result.output

    def test_status_warns_for_stalled_in_review_wp(self, tmp_path: Path) -> None:
        """The CLI status command flags in_review WPs past the review threshold."""
        mission_slug = "test-status-stalled-review"
        feature_dir, _wp_file = _build_wp_file(tmp_path, mission_slug, "WP01")
        event_time = datetime.now(UTC) - timedelta(minutes=45)
        event = StatusEvent(
            event_id="test-WP01-in-review",
            mission_slug=feature_dir.name,
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_REVIEW,
            at=event_time.isoformat(),
            actor="test",
            force=False,
            execution_mode="worktree",
        )
        append_event(feature_dir, event)

        result = self._invoke_status(tmp_path, mission_slug)

        assert result.exit_code == 0, result.output
        assert "STALLED" in result.output
        assert "no move-task" in result.output


# ---------------------------------------------------------------------------
# T011 / T012 / T013: lane guard error message variants
# ---------------------------------------------------------------------------


class TestLaneGuardErrorMessage:
    """_validate_ready_for_review names planning branch (or falls back)."""

    def _run_lane_guard(
        self,
        tmp_path: Path,
        mission_slug: str,
        feature_dir: Path,
        meta: dict | None,
        contamination: list[str],
    ) -> tuple[bool, list[str]]:
        """Helper: invoke _validate_ready_for_review with contamination mocked."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        if meta is not None:
            (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        fake_worktree = tmp_path / "worktree"
        fake_worktree.mkdir(exist_ok=True)

        def _mock_subprocess(cmd: object, *args: object, **kwargs: object) -> MagicMock:
            result_mock = MagicMock()
            result_mock.returncode = 0
            result_mock.stdout = ""
            cmd_list = cmd if isinstance(cmd, list) else []
            cmd_str = " ".join(str(c) for c in cmd_list)
            if "status" in cmd_str and "--porcelain" in cmd_str:
                # No uncommitted changes in main or worktree
                result_mock.stdout = ""
            elif "rev-list" in cmd_str and "HEAD.." in cmd_str:
                # branch-behind count: 0 (not behind)
                result_mock.stdout = "0\n"
            elif "rev-list" in cmd_str and "..HEAD" in cmd_str:
                # commits ahead of base: 1 (so we reach the contamination guard)
                result_mock.stdout = "1\n"
            elif "rev-parse" in cmd_str and any(
                ref in cmd_str for ref in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD")
            ):
                # No in-progress git operation
                result_mock.returncode = 1
                result_mock.stdout = ""
            return result_mock

        with (
            patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root", return_value=tmp_path),
            patch(
                "specify_cli.cli.commands.agent.tasks._list_wp_branch_kitty_specs_changes",
                return_value=contamination,
            ),
            patch("specify_cli.cli.commands.agent.tasks.resolve_workspace_for_wp") as mock_ws,
            patch("specify_cli.cli.commands.agent.tasks.get_feature_target_branch", return_value="main"),
            patch("specify_cli.cli.commands.agent.tasks.get_mission_type", return_value="software-dev"),
            # Patch get_current_branch so the worktree doesn't look detached
            patch(
                "specify_cli.core.git_ops.get_current_branch",
                return_value=f"kitty/mission-{mission_slug}-lane-a",
            ),
            patch("subprocess.run", side_effect=_mock_subprocess),
        ):
            mock_workspace = MagicMock()
            mock_workspace.resolution_kind = "lane_workspace"
            mock_workspace.worktree_path = fake_worktree
            mock_workspace.context = MagicMock()
            mock_workspace.context.base_branch = f"kitty/mission-{mission_slug}"
            mock_ws.return_value = mock_workspace

            return _validate_ready_for_review(
                repo_root=tmp_path,
                mission_slug=mission_slug,
                wp_id="WP01",
                force=False,
                target_lane="for_review",
            )

    def test_lane_guard_names_planning_branch(self, tmp_path: Path) -> None:
        """When meta.json has planning_base_branch, error names the branch."""
        mission_slug = "test-lane-guard-001"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        feature_dir.mkdir(parents=True)

        meta = {
            "mission_slug": mission_slug,
            "mission_id": "01KQFF35TESTTEST01",
            "planning_base_branch": "my-planning-branch",
            "mission_type": "software-dev",
        }
        contamination = ["kitty-specs/test-lane-guard-001/extra-plan.md"]

        is_valid, guidance = self._run_lane_guard(tmp_path, mission_slug, feature_dir, meta, contamination)

        assert not is_valid, "Expected validation to fail (lane contamination)"
        guidance_text = "\n".join(guidance)
        assert "my-planning-branch" in guidance_text, (
            f"Expected planning branch name in guidance; got:\n{guidance_text}"
        )
        assert "git show" in guidance_text, (
            f"Expected git show example in guidance; got:\n{guidance_text}"
        )
        assert "git show my-planning-branch:kitty-specs/test-lane-guard-001/extra-plan.md" in guidance_text

    def test_lane_guard_fallback_no_meta(self, tmp_path: Path) -> None:
        """When meta.json is absent, error says 'planning branch unknown'."""
        mission_slug = "test-lane-guard-002"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        feature_dir.mkdir(parents=True)

        # No meta.json — legacy mission
        contamination = ["kitty-specs/test-lane-guard-002/extra-plan.md"]

        is_valid, guidance = self._run_lane_guard(tmp_path, mission_slug, feature_dir, None, contamination)

        assert not is_valid, "Expected validation to fail (lane contamination)"
        guidance_text = "\n".join(guidance)
        assert "planning branch unknown" in guidance_text, (
            f"Expected fallback message; got:\n{guidance_text}"
        )

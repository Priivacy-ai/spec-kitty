"""Regression tests for merge mission branch preflight -- FR-016 through FR-019."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import typer

import specify_cli.cli.commands.merge as merge_mod
from specify_cli.cli.commands.merge import _check_mission_branch

pytestmark = pytest.mark.fast


MISSION_SLUG = "stable-320-release-blocker-cleanup-01KQW4DF"


def _blocker(slug: str = MISSION_SLUG) -> dict[str, str | bool]:
    expected_branch = f"kitty/mission-{slug}"
    return {
        "ready": False,
        "blocker": "missing_mission_branch",
        "expected_branch": expected_branch,
        "remediation": f"git branch {expected_branch} abc1234def56",
    }


def _manifest(slug: str = MISSION_SLUG) -> SimpleNamespace:
    lane = SimpleNamespace(
        lane_id="lane-d",
        wp_ids=["WP04"],
        to_dict=lambda: {"lane_id": "lane-d", "wp_ids": ["WP04"]},
    )
    return SimpleNamespace(
        mission_branch=f"kitty/mission-{slug}",
        target_branch="main",
        lanes=[lane],
    )


def _compact_output(output: str) -> str:
    return " ".join(output.split())


def _prepare_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    branch_ok: bool,
) -> None:
    monkeypatch.setattr(merge_mod, "show_banner", lambda: None)
    monkeypatch.setattr(merge_mod, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(merge_mod, "get_main_repo_root", lambda repo_root: repo_root)
    monkeypatch.setattr(merge_mod, "_enforce_git_preflight", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(merge_mod, "_resolve_target_branch", lambda *_args, **_kwargs: ("main", "flag"))
    monkeypatch.setattr(merge_mod, "_validate_target_branch", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(merge_mod, "require_lanes_json", lambda _feature_dir: _manifest())
    monkeypatch.setattr(
        merge_mod,
        "_enforce_target_branch_sync_preflight",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        merge_mod,
        "_check_mission_branch",
        lambda _mission_slug, _repo_root: (branch_ok, None if branch_ok else _blocker()),
    )


def _invoke_merge_dry_run(*, json_output: bool) -> None:
    command = merge_mod.merge.__wrapped__
    command(
        strategy=None,
        delete_branch=True,
        remove_worktree=True,
        push=False,
        target_branch=None,
        dry_run=True,
        json_output=json_output,
        mission=MISSION_SLUG,
        feature=None,
        resume=False,
        abort=False,
        context_token=None,
        keep_workspace=False,
        allow_sparse_checkout=False,
    )


class TestCheckMissionBranch:
    def test_branch_exists_returns_true(self, tmp_path: Path) -> None:
        with patch(
            "specify_cli.cli.commands.merge._has_branch_ref",
            return_value=True,
        ):
            exists, blocker = _check_mission_branch("my-mission-01KQ", tmp_path)

        assert exists is True
        assert blocker is None

    def test_branch_missing_returns_false_with_payload(self, tmp_path: Path) -> None:
        with patch(
            "specify_cli.cli.commands.merge._has_branch_ref",
            return_value=False,
        ), patch("specify_cli.cli.commands.merge.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "abc1234def5678\n"
            exists, blocker = _check_mission_branch("my-mission-01KQ", tmp_path)

        assert exists is False
        assert blocker is not None
        assert blocker["ready"] is False
        assert blocker["blocker"] == "missing_mission_branch"
        assert blocker["expected_branch"] == "kitty/mission-my-mission-01KQ"
        assert blocker["remediation"] == "git branch kitty/mission-my-mission-01KQ abc1234def56"


class TestMergeDryRunMissingBranch:
    """Integration tests for merge --dry-run with missing mission branch."""

    def test_dry_run_json_missing_branch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """merge --dry-run --json reports ready:false with structured blocker."""
        _prepare_dry_run(monkeypatch, tmp_path, branch_ok=False)
        monkeypatch.setattr(
            merge_mod,
            "needs_number_assignment",
            Mock(side_effect=AssertionError("lane preview should not run")),
        )

        with pytest.raises(typer.Exit) as exc_info:
            _invoke_merge_dry_run(json_output=True)

        assert exc_info.value.exit_code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload == _blocker()

    def test_dry_run_human_missing_branch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """merge --dry-run (no --json) shows remediation in human text."""
        _prepare_dry_run(monkeypatch, tmp_path, branch_ok=False)
        monkeypatch.setattr(
            merge_mod,
            "needs_number_assignment",
            Mock(side_effect=AssertionError("lane preview should not run")),
        )

        with pytest.raises(typer.Exit) as exc_info:
            _invoke_merge_dry_run(json_output=False)

        assert exc_info.value.exit_code == 1
        output = _compact_output(capsys.readouterr().out)
        assert "Cannot proceed: mission branch missing." in output
        assert f"Expected branch: kitty/mission-{MISSION_SLUG}" in output
        assert f"Remediation: git branch kitty/mission-{MISSION_SLUG} abc1234def56" in output

    def test_real_merge_blocked_missing_branch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Real merge is blocked before irreversible git operations."""
        monkeypatch.setattr(merge_mod, "get_main_repo_root", lambda repo_root: repo_root)
        monkeypatch.setattr(merge_mod, "require_no_sparse_checkout", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(merge_mod, "require_lanes_json", lambda _feature_dir: _manifest())
        monkeypatch.setattr(
            merge_mod,
            "_enforce_target_branch_sync_preflight",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(
            merge_mod,
            "_check_mission_branch",
            lambda _mission_slug, _repo_root: (False, _blocker()),
        )
        acquire_lock = Mock(return_value=True)
        monkeypatch.setattr(merge_mod, "acquire_merge_lock", acquire_lock)

        with pytest.raises(typer.Exit) as exc_info:
            merge_mod._run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=MISSION_SLUG,
                push=False,
                delete_branch=True,
                remove_worktree=True,
            )

        assert exc_info.value.exit_code == 1
        acquire_lock.assert_not_called()
        output = _compact_output(capsys.readouterr().out)
        assert f"Missing mission branch: kitty/mission-{MISSION_SLUG}" in output
        assert f"git branch kitty/mission-{MISSION_SLUG} abc1234def56" in output


class TestMergeDryRunHappyPath:
    def test_dry_run_ready_with_branch_present(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Existing happy-path preflight behavior is unaffected."""
        _prepare_dry_run(monkeypatch, tmp_path, branch_ok=True)
        monkeypatch.setattr(merge_mod, "needs_number_assignment", lambda _feature_dir: False)

        _invoke_merge_dry_run(json_output=True)

        payload = json.loads(capsys.readouterr().out)
        assert payload["mission_slug"] == MISSION_SLUG
        assert payload["mission_branch"] == f"kitty/mission-{MISSION_SLUG}"
        assert payload["target_branch"] == "main"
        assert payload["lanes"] == [{"lane_id": "lane-d", "wp_ids": ["WP04"]}]
        assert payload["would_assign_mission_number"] is None

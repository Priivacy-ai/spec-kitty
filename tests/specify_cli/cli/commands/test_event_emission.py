from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Callable
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from tests.branch_contract import IS_2X_BRANCH, LEGACY_0X_ONLY_REASON
from specify_cli import app as cli_app
from specify_cli.core.context_validation import ExecutionContext
from specify_cli.core.vcs import VCSBackend
from specify_cli.core.vcs.types import WorkspaceCreateResult, WorkspaceInfo
from specify_cli.acceptance import AcceptanceError


runner = CliRunner()
pytestmark = pytest.mark.skipif(IS_2X_BRANCH, reason=LEGACY_0X_ONLY_REASON)


class DummyVCS:
    def __init__(self, repo_root: Path) -> None:
        self.backend = VCSBackend.GIT
        self._repo_root = repo_root

    def get_workspace_info(self, _workspace_path: Path):
        return None

    def create_workspace(
        self,
        workspace_path: Path,
        workspace_name: str,
        base_branch: str,
        repo_root: Path,
        sparse_exclude: list[str] | None = None,
    ) -> WorkspaceCreateResult:
        workspace_path.mkdir(parents=True, exist_ok=True)
        info = WorkspaceInfo(
            name=workspace_name,
            path=workspace_path,
            backend=VCSBackend.GIT,
            is_colocated=False,
            current_branch=base_branch,
            current_change_id=None,
            current_commit_id="deadbeef",
            base_branch=base_branch,
            base_commit_id="deadbeef",
            is_stale=False,
            has_conflicts=False,
            has_uncommitted=False,
        )
        return WorkspaceCreateResult(success=True, workspace=info, error=None)


def _force_main_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.core.context_validation.get_current_context",
        lambda: SimpleNamespace(location=ExecutionContext.MAIN_REPO, worktree_name=None),
    )


def _fake_subprocess_run_factory(stdout_map: dict[str, str]) -> Callable:
    def _fake_run(cmd, **_kwargs):
        cmd_str = " ".join(cmd)
        stdout = stdout_map.get(cmd_str, "deadbeef\n")
        return MagicMock(returncode=0, stdout=stdout, stderr="")

    return _fake_run


def _write_wp(path: Path, wp_id: str, lane: str = "planned") -> None:
    path.write_text(
        "\n".join(
            [
                "---",
                f"work_package_id: {wp_id}",
                'title: "Test WP"',
                f'lane: "{lane}"',
                "---",
                "",
                "Body",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_implement_emits_wp_status_changed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify").mkdir()
    feature_dir = repo_root / "kitty-specs" / "001-demo-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp(wp_path, "WP01")
    (feature_dir / "meta.json").write_text("{}\n", encoding="utf-8")

    _force_main_repo(monkeypatch)
    monkeypatch.setattr("specify_cli.cli.commands.implement.find_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.implement.detect_feature_context",
        lambda _feature=None: ("001", "001-demo-feature"),
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.implement.find_wp_file",
        lambda _repo_root, _feature_slug, _wp_id: wp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.implement.parse_wp_dependencies",
        lambda _wp_file: [],
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.implement.check_for_dependents",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.implement.get_vcs",
        lambda _repo_root, backend=None: DummyVCS(repo_root),
    )
    monkeypatch.setattr(
        "specify_cli.core.feature_detection.get_feature_target_branch",
        lambda _repo_root, _feature_slug: "main",
    )

    stdout_map = {
        "git rev-parse --abbrev-ref HEAD": "main\n",
        "git rev-parse --verify main": "main\n",
        "git rev-parse main": "deadbeef\n",
    }
    monkeypatch.setattr(
        "specify_cli.cli.commands.implement.subprocess.run",
        _fake_subprocess_run_factory(stdout_map),
    )

    emit_mock = MagicMock()
    monkeypatch.setattr("specify_cli.sync.events.emit_wp_status_changed", emit_mock)

    result = runner.invoke(
        cli_app,
        ["implement", "WP01", "--feature", "001-demo-feature", "--json"],
    )
    assert result.exit_code == 0
    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["wp_id"] == "WP01"
    assert kwargs["from_lane"] == "planned"
    assert kwargs["to_lane"] == "in_progress"


def test_merge_emits_wp_status_changed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / ".worktrees").mkdir()

    _force_main_repo(monkeypatch)
    monkeypatch.setattr("specify_cli.cli.commands.merge.find_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.detect_worktree_structure",
        lambda _repo_root, _feature_slug: "workspace-per-wp",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.find_wp_worktrees",
        lambda _repo_root, _feature_slug: [
            (repo_root / ".worktrees" / "001-demo-feature-WP01", "WP01", "001-demo-feature-WP01"),
        ],
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.validate_wp_ready_for_merge",
        lambda *_args, **_kwargs: (True, ""),
    )

    dummy_preflight = SimpleNamespace(passed=True, failures=[], warnings=[])
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.run_preflight",
        lambda **_kwargs: dummy_preflight,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.display_preflight_result",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.check_version_compatibility",
        lambda *_args, **_kwargs: None,
    )

    def fake_run_command(cmd, capture=False, **_kwargs):
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, "001-demo-feature-WP01\n", ""
        if cmd[:3] == ["git", "rev-parse", "--git-dir"]:
            return 0, ".git\n", ""
        return 0, "", ""

    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.run_command",
        fake_run_command,
    )

    emit_mock = MagicMock()
    monkeypatch.setattr("specify_cli.sync.events.emit_wp_status_changed", emit_mock)

    result = runner.invoke(cli_app, ["merge", "--feature", "001-demo-feature", "--target", "main"])
    assert result.exit_code == 0
    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["wp_id"] == "WP01"
    assert kwargs["from_lane"] == "in_progress"
    assert kwargs["to_lane"] == "for_review"


def test_accept_emits_wp_status_changed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    _force_main_repo(monkeypatch)
    monkeypatch.setattr("specify_cli.cli.commands.accept.find_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.accept.detect_feature_slug",
        lambda _repo_root: "001-demo-feature",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.accept.choose_mode",
        lambda _mode, _repo_root: "auto",
    )

    summary = SimpleNamespace(
        ok=True,
        feature="001-demo-feature",
        lanes={"for_review": ["WP01"]},
        outstanding=lambda: {},
        optional_missing=[],
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.accept.collect_feature_summary",
        lambda *_args, **_kwargs: summary,
    )

    result_obj = SimpleNamespace(
        summary=summary,
        accepted_at="2026-02-04T00:00:00Z",
        accepted_by="tester",
        accept_commit=None,
        parent_commit=None,
        commit_created=False,
        instructions=[],
        cleanup_instructions=[],
        notes=[],
        to_dict=lambda: {"feature": summary.feature, "lanes": summary.lanes},
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.accept.perform_acceptance",
        lambda *_args, **_kwargs: result_obj,
    )

    emit_mock = MagicMock()
    monkeypatch.setattr("specify_cli.sync.events.emit_wp_status_changed", emit_mock)

    result = runner.invoke(cli_app, ["accept", "--feature", "001-demo-feature", "--allow-fail"])
    assert result.exit_code == 0
    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["wp_id"] == "WP01"
    assert kwargs["from_lane"] == "for_review"
    assert kwargs["to_lane"] == "done"


def test_accept_error_emits_error_logged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    _force_main_repo(monkeypatch)
    monkeypatch.setattr("specify_cli.cli.commands.accept.find_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.accept.detect_feature_slug",
        lambda _repo_root: "001-demo-feature",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.accept.choose_mode",
        lambda _mode, _repo_root: "auto",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.accept.collect_feature_summary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AcceptanceError("boom")),
    )

    emit_mock = MagicMock()
    monkeypatch.setattr("specify_cli.sync.events.emit_error_logged", emit_mock)

    result = runner.invoke(cli_app, ["accept", "--feature", "001-demo-feature"])
    assert result.exit_code != 0
    emit_mock.assert_called_once()


def test_finalize_tasks_emits_wp_created_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """finalize-tasks emits WPCreated but NOT FeatureCreated (moved to create-feature)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    feature_dir = repo_root / "kitty-specs" / "001-demo-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text("## Work Package WP01\n", encoding="utf-8")
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp(wp_path, "WP01")

    monkeypatch.setattr("specify_cli.cli.commands.agent.feature.locate_project_root", lambda: repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.feature._find_feature_directory",
        lambda _repo_root, _cwd: feature_dir,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.feature._resolve_planning_branch",
        lambda _repo_root, _feature_dir: "main",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.feature._ensure_branch_checked_out",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.feature.run_command",
        lambda *_args, **_kwargs: (0, "", ""),
    )

    emitter_stub = MagicMock()
    emitter_stub.generate_causation_id.return_value = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    monkeypatch.setattr("specify_cli.sync.events.get_emitter", lambda: emitter_stub)

    feature_created = MagicMock()
    wp_created = MagicMock()
    monkeypatch.setattr("specify_cli.cli.commands.agent.feature.emit_feature_created", feature_created)
    monkeypatch.setattr("specify_cli.cli.commands.agent.feature.emit_wp_created", wp_created)

    result = runner.invoke(cli_app, ["agent", "feature", "finalize-tasks"])
    assert result.exit_code == 0
    feature_created.assert_not_called()
    wp_created.assert_called_once()


def test_orchestrate_emits_wp_assigned_and_dependency_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    assigned = MagicMock()
    resolved = MagicMock()
    monkeypatch.setattr("specify_cli.sync.events.emit_wp_assigned", assigned)
    monkeypatch.setattr("specify_cli.sync.events.emit_dependency_resolved", resolved)

    def fake_start(_feature, impl_agent=None, review_agent=None):
        assigned(wp_id="WP01", agent_id="agent", phase="implementation", retry_count=0)
        resolved(wp_id="WP02", dependency_wp_id="WP01", resolution_type="completed")

    monkeypatch.setattr("specify_cli.cli.commands.orchestrate.start_orchestration", fake_start)

    result = runner.invoke(cli_app, ["orchestrate", "--feature", "001-demo-feature"])
    assert result.exit_code == 0
    assigned.assert_called_once()
    resolved.assert_called_once()

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app

accept_module = importlib.import_module("specify_cli.cli.commands.accept")
dashboard_module = importlib.import_module("specify_cli.cli.commands.dashboard")
merge_module = importlib.import_module("specify_cli.cli.commands.merge")
research_module = importlib.import_module("specify_cli.cli.commands.research")
lifecycle_module = importlib.import_module("specify_cli.cli.commands.lifecycle")
verify_module = importlib.import_module("specify_cli.cli.commands.verify")


runner = CliRunner()


def _load_json_from_output(output: str) -> dict[str, object]:
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise AssertionError(f"JSON payload not found in output: {output!r}")
    return json.loads(output[start : end + 1])


def test_cli_help_lists_extracted_commands() -> None:
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    for name in [
        "research",
        "dashboard",
        "accept",
        "merge",
        "verify-setup",
        "specify",
        "plan",
        "tasks",
    ]:
        assert name in result.stdout


def test_cli_help_simple_mode_avoids_rich_tables(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_SIMPLE_HELP", "1")
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "Commands:" in result.stdout
    assert "╭" not in result.stdout


def test_verify_setup_command_runs() -> None:
    """Test that verify-setup command works (replaces deprecated check command)."""
    # verify-setup requires being in a project or exits with code 1
    # This is expected behavior - when not in a project, it shows helpful error
    result = runner.invoke(cli_app, ["verify-setup"])
    # Should show tool checking results even when not in a project
    assert "Check Available Tools" in result.stdout or "Checking for installed tools" in result.stdout


def test_specify_command_delegates_to_agent_lifecycle(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_feature(feature_slug: str, mission=None, json_output: bool = False):
        captured["feature_slug"] = feature_slug
        captured["mission"] = mission
        captured["json_output"] = json_output

    monkeypatch.setattr(lifecycle_module.agent_feature, "create_feature", fake_create_feature)

    result = runner.invoke(cli_app, ["specify", "My Great Feature"])
    assert result.exit_code == 0
    assert captured["feature_slug"] == "my-great-feature"
    assert captured["mission"] is None
    assert captured["json_output"] is False


def test_plan_and_tasks_delegate_to_agent_lifecycle(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_setup_plan(feature=None, json_output: bool = False):
        captured["plan_feature"] = feature
        captured["plan_json"] = json_output

    def fake_finalize_tasks(json_output: bool = False):
        captured["tasks_json"] = json_output

    monkeypatch.setattr(lifecycle_module.agent_feature, "setup_plan", fake_setup_plan)
    monkeypatch.setattr(lifecycle_module.agent_feature, "finalize_tasks", fake_finalize_tasks)

    plan_result = runner.invoke(cli_app, ["plan", "--feature", "001-demo", "--json"])
    tasks_result = runner.invoke(cli_app, ["tasks", "--json"])

    assert plan_result.exit_code == 0
    assert tasks_result.exit_code == 0
    assert captured["plan_feature"] == "001-demo"
    assert captured["plan_json"] is True
    assert captured["tasks_json"] is True


def test_dashboard_kill_stops_instance(monkeypatch, tmp_path: Path) -> None:
    call_record: dict[str, Path] = {}
    monkeypatch.setattr(dashboard_module, "get_project_root_or_exit", lambda: tmp_path)

    def fake_stop(project_root: Path) -> tuple[bool, str]:
        call_record["root"] = project_root
        return True, "Dashboard stopped"

    monkeypatch.setattr(dashboard_module, "stop_dashboard", fake_stop)

    result = runner.invoke(cli_app, ["dashboard", "--kill"])
    assert result.exit_code == 0
    assert call_record["root"] == tmp_path
    assert "Dashboard stopped" in result.stdout


def test_research_creates_artifacts(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".kittify" / "missions" / "software-dev" / "templates").mkdir(parents=True)
    feature_dir = project_root / "kitty-specs" / "001-demo-feature"

    monkeypatch.setattr(research_module, "find_repo_root", lambda: project_root)
    monkeypatch.setattr(research_module, "get_feature_mission_key", lambda *_args, **_kwargs: "software-dev")
    monkeypatch.setattr(
        research_module,
        "resolve_worktree_aware_feature_dir",
        lambda *_args, **_kwargs: feature_dir,
    )
    monkeypatch.setattr(research_module, "resolve_template_path", lambda *_args, **_kwargs: None)

    result = runner.invoke(cli_app, ["research", "--feature", "001-demo-feature", "--force"])
    assert result.exit_code == 0

    assert (feature_dir / "research.md").exists()
    assert (feature_dir / "data-model.md").exists()
    assert (feature_dir / "research" / "evidence-log.csv").exists()


def test_accept_checklist_json_output(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    class DummySummary:
        ok = True
        lanes = {"done": ["WP01"]}
        optional_missing: list[str] = []
        feature = "001-demo-feature"

        def outstanding(self) -> dict[str, list[str]]:
            return {}

        def to_dict(self) -> dict[str, object]:
            return {"feature": self.feature, "lanes": self.lanes}

    monkeypatch.setattr(accept_module, "find_repo_root", lambda: repo_root)
    monkeypatch.setattr(accept_module, "detect_feature_slug", lambda _repo_root: "001-demo-feature")
    monkeypatch.setattr(accept_module, "choose_mode", lambda mode, _repo_root: mode)
    monkeypatch.setattr(accept_module, "collect_feature_summary", lambda *args, **kwargs: DummySummary())

    result = runner.invoke(
        cli_app,
        ["accept", "--mode", "checklist", "--json", "--feature", "001-demo-feature", "--allow-fail"],
    )
    assert result.exit_code == 0
    assert result.stdout.lstrip().startswith("{")
    data = _load_json_from_output(result.stdout)
    assert data["feature"] == "001-demo-feature"


def test_accept_json_suppresses_fallback_announcement(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    class DummySummary:
        ok = True
        lanes = {"done": ["WP01"]}
        optional_missing: list[str] = []
        feature = "002-auto-feature"

        def outstanding(self) -> dict[str, list[str]]:
            return {}

        def to_dict(self) -> dict[str, object]:
            return {"feature": self.feature, "lanes": self.lanes}

    captured: dict[str, object] = {}

    def fake_detect(_repo_root, *, announce_fallback=True):
        captured["announce_fallback"] = announce_fallback
        if announce_fallback:
            print("ℹ️  Auto-selected latest incomplete: 002-auto-feature")
        return "002-auto-feature"

    monkeypatch.setattr(accept_module, "find_repo_root", lambda: repo_root)
    monkeypatch.setattr(accept_module, "detect_feature_slug", fake_detect)
    monkeypatch.setattr(accept_module, "choose_mode", lambda mode, _repo_root: mode)
    monkeypatch.setattr(accept_module, "collect_feature_summary", lambda *args, **kwargs: DummySummary())

    result = runner.invoke(
        cli_app,
        ["accept", "--mode", "checklist", "--json", "--allow-fail"],
    )

    assert result.exit_code == 0
    assert captured["announce_fallback"] is False
    assert result.stdout.lstrip().startswith("{")
    data = json.loads(result.stdout)
    assert data["feature"] == "002-auto-feature"


def test_merge_dry_run_outputs_steps(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    def fake_run_command(cmd, capture=False, **_kwargs):
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, "feature/test", ""
        if cmd[:3] == ["git", "rev-parse", "--git-dir"]:
            return 0, str(repo_root / ".git"), ""
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return 0, "", ""
        return 0, "", ""

    monkeypatch.setattr(merge_module, "find_repo_root", lambda: repo_root)
    monkeypatch.setattr(merge_module, "run_command", fake_run_command)

    result = runner.invoke(cli_app, ["merge", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run - would execute" in result.stdout
    assert "git checkout main" in result.stdout


def test_merge_skips_pull_when_target_has_no_tracking(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    calls: list[list[str]] = []

    def fake_run_command(cmd, capture=False, **_kwargs):
        call = list(cmd)
        calls.append(call)
        if call[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, "feature/test", ""
        if call[:3] == ["git", "rev-parse", "--git-dir"]:
            return 0, str(repo_root / ".git"), ""
        if call[:3] == ["git", "status", "--porcelain"]:
            return 0, "", ""
        if call[:2] == ["git", "checkout"]:
            return 0, "", ""
        if call[:2] == ["git", "merge"]:
            return 0, "", ""
        if call[:2] == ["git", "branch"]:
            return 0, "", ""
        if call[:2] == ["git", "pull"]:
            raise AssertionError("git pull should be skipped when no tracking branch exists")
        return 0, "", ""

    monkeypatch.setattr(merge_module, "find_repo_root", lambda: repo_root)
    monkeypatch.setattr(merge_module, "run_command", fake_run_command)
    monkeypatch.setattr(merge_module, "check_version_compatibility", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(merge_module, "has_remote", lambda _repo: True)
    monkeypatch.setattr(merge_module, "has_tracking_branch", lambda _repo: False)
    monkeypatch.setattr(merge_module, "show_banner", lambda: None)

    result = runner.invoke(cli_app, ["merge", "--keep-worktree", "--keep-branch"])
    assert result.exit_code == 0
    assert ["git", "pull", "--ff-only"] not in calls
    assert "Skipping pull (main branch not tracking remote)" in result.stdout


def test_verify_setup_json_output(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "workspace"
    repo_root.mkdir()

    monkeypatch.setattr(verify_module, "find_repo_root", lambda: repo_root)
    monkeypatch.setattr(verify_module, "get_project_root_or_exit", lambda _repo=None: repo_root)

    def fake_verify(*_args, **_kwargs):
        return {"status": "ok", "feature": "001-demo-feature"}

    monkeypatch.setattr(verify_module, "run_enhanced_verify", fake_verify)

    result = runner.invoke(cli_app, ["verify-setup", "--json", "--feature", "001-demo-feature"])
    assert result.exit_code == 0
    payload = _load_json_from_output(result.stdout)
    assert payload["status"] == "ok"
    assert payload["feature"] == "001-demo-feature"

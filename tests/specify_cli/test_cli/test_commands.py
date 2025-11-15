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
    for name in ["research", "dashboard", "accept", "merge", "verify-setup"]:
        assert name in result.stdout


def test_verify_setup_command_runs() -> None:
    """Test that verify-setup command works (replaces deprecated check command)."""
    result = runner.invoke(cli_app, ["verify-setup"])
    assert result.exit_code == 0
    # verify-setup shows completion message
    assert "Verification complete" in result.stdout or "✓" in result.stdout


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
    monkeypatch.setattr(research_module, "get_active_mission_key", lambda _project: "software-dev")
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
    data = _load_json_from_output(result.stdout)
    assert data["feature"] == "001-demo-feature"


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

"""Selector resolution helper and command integration tests."""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import click
import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from specify_cli.cli import selector_resolution
from specify_cli.cli.commands.agent.mission import app as agent_mission_app
from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.cli.commands.mission import app as mission_app
from specify_cli.cli.commands.next_cmd import next_step
from specify_cli.cli.selector_resolution import resolve_selector

pytestmark = pytest.mark.fast

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_selector_resolution_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset warning state and env vars between tests."""
    selector_resolution._warned.clear()
    monkeypatch.delenv("SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION", raising=False)
    yield
    selector_resolution._warned.clear()


@pytest.fixture()
def warning_stream(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    """Capture rendered warning output without terminal wrapping."""
    stream = io.StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None, width=200)
    monkeypatch.setattr(selector_resolution, "_err_console", console)
    return stream


def _build_task_repo(tmp_path: Path, mission_slug: str = "077-demo-mission") -> Path:
    """Create a minimal repo structure for agent task status tests."""
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    feature_dir = repo_root / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-demo.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Demo WP\n"
        "execution_mode: code_change\n"
        "owned_files:\n"
        "  - src/demo/**\n"
        "authoritative_surface: src/demo/\n"
        "---\n\n"
        "# WP01 Demo\n\n"
        "## Activity Log\n",
        encoding="utf-8",
    )
    return repo_root


def _extract_json(output: str) -> dict:
    """Extract the first JSON object from mixed stdout output."""
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        pass
    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No valid JSON found in output:\n{output}")


def test_canonical_only_returns_value(warning_stream: io.StringIO) -> None:
    result = resolve_selector(
        canonical_value="077-demo",
        canonical_flag="--mission",
        alias_value=None,
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
    )

    assert result.canonical_value == "077-demo"
    assert result.alias_used is False
    assert result.alias_flag is None
    assert result.warning_emitted is False
    assert warning_stream.getvalue() == ""


def test_alias_only_returns_canonical_value(warning_stream: io.StringIO) -> None:
    result = resolve_selector(
        canonical_value=None,
        canonical_flag="--mission",
        alias_value="077-demo",
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
    )

    assert result.canonical_value == "077-demo"
    assert result.alias_used is True
    assert result.alias_flag == "--feature"
    assert result.warning_emitted is True
    assert "Warning: --feature is deprecated; use --mission." in warning_stream.getvalue()


def test_both_equal_returns_value_with_warning(warning_stream: io.StringIO) -> None:
    result = resolve_selector(
        canonical_value="077-demo",
        canonical_flag="--mission",
        alias_value="077-demo",
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
    )

    assert result.canonical_value == "077-demo"
    assert result.alias_used is True
    assert result.warning_emitted is True
    assert warning_stream.getvalue().count("Warning:") == 1


def test_both_different_raises_bad_parameter() -> None:
    with pytest.raises(typer.BadParameter, match="Conflicting selectors"):
        resolve_selector(
            canonical_value="077-a",
            canonical_flag="--mission",
            alias_value="077-b",
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
        )


def test_neither_raises_bad_parameter() -> None:
    with pytest.raises(typer.BadParameter, match="--mission <slug>"):
        resolve_selector(
            canonical_value=None,
            canonical_flag="--mission",
            alias_value=None,
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
            command_hint="--mission <slug>",
        )


def test_both_empty_strings_raise_bad_parameter() -> None:
    with pytest.raises(typer.BadParameter, match="--mission <slug>"):
        resolve_selector(
            canonical_value="",
            canonical_flag="--mission",
            alias_value="",
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
            command_hint="--mission <slug>",
        )


def test_canonical_whitespace_only_treated_as_none(warning_stream: io.StringIO) -> None:
    result = resolve_selector(
        canonical_value="   ",
        canonical_flag="--mission",
        alias_value="077-demo",
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
    )

    assert result.canonical_value == "077-demo"
    assert result.alias_used is True
    assert result.warning_emitted is True
    assert "Warning:" in warning_stream.getvalue()


def test_warning_emitted_for_each_direct_call_without_click_context(warning_stream: io.StringIO) -> None:
    first = resolve_selector(
        canonical_value=None,
        canonical_flag="--mission",
        alias_value="077-demo",
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
    )
    second = resolve_selector(
        canonical_value=None,
        canonical_flag="--mission",
        alias_value="077-demo-2",
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
    )

    assert first.warning_emitted is True
    assert second.warning_emitted is True
    assert warning_stream.getvalue().count("Warning:") == 2


def test_warning_emitted_only_once_within_click_invocation(warning_stream: io.StringIO) -> None:
    command = click.Command("dummy")
    with click.Context(command):
        first = resolve_selector(
            canonical_value=None,
            canonical_flag="--mission",
            alias_value="077-demo",
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
        )
        second = resolve_selector(
            canonical_value=None,
            canonical_flag="--mission",
            alias_value="077-demo-2",
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
        )

    assert first.warning_emitted is True
    assert second.warning_emitted is False
    assert warning_stream.getvalue().count("Warning:") == 1


def test_warning_emitted_again_for_different_pair_in_same_click_invocation(
    warning_stream: io.StringIO,
) -> None:
    command = click.Command("dummy")
    with click.Context(command):
        resolve_selector(
            canonical_value=None,
            canonical_flag="--mission",
            alias_value="077-demo",
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
        )
        resolve_selector(
            canonical_value=None,
            canonical_flag="--mission-type",
            alias_value="software-dev",
            alias_flag="--mission",
            suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
        )

    assert warning_stream.getvalue().count("Warning:") == 2


def test_warning_emitted_again_for_different_pair(warning_stream: io.StringIO) -> None:
    resolve_selector(
        canonical_value=None,
        canonical_flag="--mission",
        alias_value="077-demo",
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
    )
    resolve_selector(
        canonical_value=None,
        canonical_flag="--mission-type",
        alias_value="software-dev",
        alias_flag="--mission",
        suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
    )

    assert warning_stream.getvalue().count("Warning:") == 2


def test_suppression_env_var_skips_warning(
    monkeypatch: pytest.MonkeyPatch,
    warning_stream: io.StringIO,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION", "1")
    result = resolve_selector(
        canonical_value=None,
        canonical_flag="--mission",
        alias_value="077-demo",
        alias_flag="--feature",
        suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
    )

    assert result.alias_used is True
    assert result.warning_emitted is False
    assert warning_stream.getvalue() == ""


def test_inverse_direction_works_identically(warning_stream: io.StringIO) -> None:
    result = resolve_selector(
        canonical_value="software-dev",
        canonical_flag="--mission-type",
        alias_value="software-dev",
        alias_flag="--mission",
        suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
    )

    assert result.canonical_value == "software-dev"
    assert result.alias_used is True
    assert result.alias_flag == "--mission"
    assert result.warning_emitted is True
    assert "Warning: --mission is deprecated; use --mission-type." in warning_stream.getvalue()


def test_conflict_error_format() -> None:
    with pytest.raises(typer.BadParameter) as exc_info:
        resolve_selector(
            canonical_value="software-dev",
            canonical_flag="--mission-type",
            alias_value="research",
            alias_flag="--mission",
            suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
        )

    assert (
        str(exc_info.value)
        == "Conflicting selectors: --mission-type='software-dev' and --mission='research' were both provided with different values. --mission is a hidden deprecated alias for --mission-type; pass only --mission-type."
    )


def test_mission_current_canonical_succeeds(tmp_path: Path) -> None:
    mission_slug = "077-demo-mission"
    (tmp_path / "kitty-specs" / mission_slug).mkdir(parents=True)

    with (
        patch("specify_cli.cli.commands.mission.get_project_root_or_exit", return_value=tmp_path),
        patch("specify_cli.cli.commands.mission.check_version_compatibility"),
        patch("specify_cli.cli.commands.mission.get_mission_for_feature", return_value=SimpleNamespace(name="software-dev")),
        patch("specify_cli.cli.commands.mission._mission_details_lines", return_value=["ok"]),
    ):
        result = runner.invoke(mission_app, ["current", "--mission", mission_slug])

    assert result.exit_code == 0, result.output
    assert "Warning:" not in result.output
    assert mission_slug in result.output


def test_mission_current_alias_succeeds_with_warning(tmp_path: Path, warning_stream: io.StringIO) -> None:
    mission_slug = "077-demo-mission"
    (tmp_path / "kitty-specs" / mission_slug).mkdir(parents=True)

    with (
        patch("specify_cli.cli.commands.mission.get_project_root_or_exit", return_value=tmp_path),
        patch("specify_cli.cli.commands.mission.check_version_compatibility"),
        patch("specify_cli.cli.commands.mission.get_mission_for_feature", return_value=SimpleNamespace(name="software-dev")),
        patch("specify_cli.cli.commands.mission._mission_details_lines", return_value=["ok"]),
    ):
        result = runner.invoke(mission_app, ["current", "--feature", mission_slug])

    assert result.exit_code == 0, result.output
    assert "--feature is deprecated; use --mission" in warning_stream.getvalue()


def test_mission_current_alias_overrides_detected_mission(tmp_path: Path, warning_stream: io.StringIO) -> None:
    detected = "077-detected"
    explicit = "077-explicit"
    (tmp_path / "kitty-specs" / detected).mkdir(parents=True)
    (tmp_path / "kitty-specs" / explicit).mkdir(parents=True)

    with (
        patch("specify_cli.cli.commands.mission.get_project_root_or_exit", return_value=tmp_path),
        patch("specify_cli.cli.commands.mission.check_version_compatibility"),
        patch("specify_cli.cli.commands.mission._detect_current_feature", return_value=detected),
        patch("specify_cli.cli.commands.mission.get_mission_for_feature", return_value=SimpleNamespace(name="software-dev")),
        patch("specify_cli.cli.commands.mission._mission_details_lines", return_value=["ok"]),
    ):
        result = runner.invoke(mission_app, ["current", "--feature", explicit])

    assert result.exit_code == 0, result.output
    assert explicit in result.output
    assert detected not in result.output
    assert "--feature is deprecated; use --mission" in warning_stream.getvalue()


def test_mission_current_dual_flag_conflict_fails(tmp_path: Path) -> None:
    with (
        patch("specify_cli.cli.commands.mission.get_project_root_or_exit", return_value=tmp_path),
        patch("specify_cli.cli.commands.mission.check_version_compatibility"),
    ):
        result = runner.invoke(mission_app, ["current", "--mission", "077-a", "--feature", "077-b"])

    assert result.exit_code != 0
    assert "Conflicting selectors" in result.output


def test_agent_mission_create_canonical_succeeds(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "new-thing"
    feature_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    def _fake_create_mission_core(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            mission_slug="new-thing",
            mission_number="077",
            meta={
                "mission_type": "software-dev",
                "slug": "new-thing",
                "friendly_name": "New Thing",
                "created_at": "2026-04-08T00:00:00Z",
            },
            feature_dir=feature_dir,
            target_branch="main",
            current_branch="main",
        )

    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path),
        patch("specify_cli.core.mission_creation.create_mission_core", side_effect=_fake_create_mission_core),
    ):
        result = runner.invoke(agent_mission_app, ["create", "new-thing", "--mission-type", "software-dev", "--json"])

    assert result.exit_code == 0, result.output
    assert captured["mission"] == "software-dev"
    payload = _extract_json(result.output)
    assert payload["mission_type"] == "software-dev"
    assert "Warning:" not in result.output


def test_agent_mission_create_alias_succeeds_with_warning(
    tmp_path: Path,
    warning_stream: io.StringIO,
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "new-thing"
    feature_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    def _fake_create_mission_core(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            mission_slug="new-thing",
            mission_number="077",
            meta={
                "mission_type": "software-dev",
                "slug": "new-thing",
                "friendly_name": "New Thing",
                "created_at": "2026-04-08T00:00:00Z",
            },
            feature_dir=feature_dir,
            target_branch="main",
            current_branch="main",
        )

    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path),
        patch("specify_cli.core.mission_creation.create_mission_core", side_effect=_fake_create_mission_core),
    ):
        result = runner.invoke(agent_mission_app, ["create", "new-thing", "--mission", "software-dev", "--json"])

    assert result.exit_code == 0, result.output
    assert captured["mission"] == "software-dev"
    assert "--mission is deprecated; use --mission-type" in warning_stream.getvalue()


def test_agent_mission_create_dual_flag_conflict_fails(tmp_path: Path) -> None:
    with patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path):
        result = runner.invoke(
            agent_mission_app,
            ["create", "new-thing", "--mission-type", "software-dev", "--mission", "research", "--json"],
        )

    assert result.exit_code != 0
    assert "Conflicting selectors" in result.output


def test_next_step_canonical_selector_passes_mission_slug(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    def _fake_query(agent: str, mission_slug: str, repo_root: Path):
        captured.update({"agent": agent, "mission_slug": mission_slug, "repo_root": repo_root})
        return SimpleNamespace(
            to_dict=lambda: {"kind": "query", "mission": mission_slug},
            is_query=True,
            mission=mission_slug,
            mission_state="planned",
            progress=None,
            run_id=None,
        )

    with (
        patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
        patch("specify_cli.next.runtime_bridge.query_current_state", side_effect=_fake_query),
    ):
        next_step.__wrapped__(
            agent="codex",
            mission="077-demo-mission",
            feature=None,
            json_output=True,
            result=None,
            answer=None,
            decision_id=None,
        )

    out = capsys.readouterr()
    assert captured["mission_slug"] == "077-demo-mission"
    assert json.loads(out.out)["mission"] == "077-demo-mission"


def test_next_step_alias_selector_warns_and_passes_mission_slug(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    def _fake_query(agent: str, mission_slug: str, repo_root: Path):
        captured.update({"agent": agent, "mission_slug": mission_slug, "repo_root": repo_root})
        return SimpleNamespace(
            to_dict=lambda: {"kind": "query", "mission": mission_slug},
            is_query=True,
            mission=mission_slug,
            mission_state="planned",
            progress=None,
            run_id=None,
        )

    with (
        patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
        patch("specify_cli.next.runtime_bridge.query_current_state", side_effect=_fake_query),
    ):
        next_step.__wrapped__(
            agent="codex",
            mission=None,
            feature="077-demo-mission",
            json_output=True,
            result=None,
            answer=None,
            decision_id=None,
        )

    out = capsys.readouterr()
    assert captured["mission_slug"] == "077-demo-mission"
    assert "--feature is deprecated; use --mission" in out.err


def test_next_step_dual_flag_conflict_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path):
        with pytest.raises(typer.Exit):
            next_step.__wrapped__(
                agent="codex",
                mission="077-a",
                feature="077-b",
                json_output=True,
                result=None,
                answer=None,
                decision_id=None,
            )

    out = capsys.readouterr()
    assert "Conflicting selectors" in out.err


def test_agent_tasks_status_canonical_selector_succeeds(tmp_path: Path) -> None:
    repo_root = _build_task_repo(tmp_path)

    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=repo_root),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(repo_root, "main")),
        patch("specify_cli.cli.commands.agent.tasks.get_auto_commit_default", return_value=True),
    ):
        result = runner.invoke(tasks_app, ["status", "--mission", "077-demo-mission", "--json"])

    assert result.exit_code == 0, result.output
    payload = _extract_json(result.output)
    assert payload["total_wps"] == 1
    assert payload["work_packages"][0]["id"] == "WP01"


def test_agent_tasks_status_alias_selector_succeeds_with_warning(
    tmp_path: Path,
    warning_stream: io.StringIO,
) -> None:
    repo_root = _build_task_repo(tmp_path)

    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=repo_root),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(repo_root, "main")),
        patch("specify_cli.cli.commands.agent.tasks.get_auto_commit_default", return_value=True),
    ):
        result = runner.invoke(tasks_app, ["status", "--feature", "077-demo-mission", "--json"])

    assert result.exit_code == 0, result.output
    assert "--feature is deprecated; use --mission" in warning_stream.getvalue()


def test_agent_tasks_status_dual_flag_conflict_fails(tmp_path: Path) -> None:
    repo_root = _build_task_repo(tmp_path)

    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=repo_root),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(repo_root, "main")),
    ):
        result = runner.invoke(tasks_app, ["status", "--mission", "077-a", "--feature", "077-b", "--json"])

    assert result.exit_code != 0
    assert "Conflicting selectors" in result.output

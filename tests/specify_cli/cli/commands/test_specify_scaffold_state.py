from __future__ import annotations

import json

import pytest
import typer
from typer.testing import CliRunner

import specify_cli.cli.commands.lifecycle as lifecycle
from specify_cli.cli.commands.lifecycle import specify
from specify_cli.workspace.assert_initialized import SpecKittyNotInitialized
from mission_runtime import MissionTopology


pytestmark = [pytest.mark.unit, pytest.mark.fast]

_app = typer.Typer()
_app.command()(specify)
runner = CliRunner()


def test_specify_json_exposes_scaffold_only_state(monkeypatch) -> None:
    monkeypatch.setattr(
        lifecycle,
        "_enforce_initialized",
        lambda *, require_specs=True, json_output=False: None,
    )

    def fake_create_mission(
        *,
        mission_slug: str,
        mission_type: str | None,
        json_output: bool,
        topology: MissionTopology,
    ) -> None:
        assert mission_slug == "my-feature"
        assert mission_type is None
        assert json_output is True
        assert topology is MissionTopology.COORD  # default when --topology omitted (#2218)
        print(
            json.dumps(
                {
                    "result": "success",
                    "mission_slug": mission_slug,
                    "spec_file": "/tmp/project/kitty-specs/my-feature/spec.md",
                    "next_step": "old agent guidance",
                }
            )
        )

    monkeypatch.setattr(lifecycle.agent_feature, "create_mission", fake_create_mission)

    result = runner.invoke(_app, ["my feature", "--json"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["scaffold_only"] is True
    assert payload["spec_state"] == "scaffold_only"
    assert "complete specification" in payload["next_action"]
    assert payload["next_step"] == payload["next_action"]
    assert "spec-kitty plan --mission my-feature" in payload["next_action"]


def test_specify_json_uninitialized_error_is_json(monkeypatch, tmp_path) -> None:
    def fail_initialized(*, require_specs: bool = True) -> None:
        raise SpecKittyNotInitialized(
            tmp_path,
            [tmp_path / ".kittify" / "config.yaml"],
        )

    monkeypatch.setattr(lifecycle, "assert_initialized", fail_initialized)

    result = runner.invoke(_app, ["my feature", "--json"], catch_exceptions=False)

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["error_code"] == "SPEC_KITTY_REPO_NOT_INITIALIZED"
    assert "Spec Kitty is not initialized" in payload["error"]


def test_specify_human_output_explains_scaffold_only_state(monkeypatch) -> None:
    monkeypatch.setattr(
        lifecycle,
        "_enforce_initialized",
        lambda *, require_specs=True, json_output=False: None,
    )
    monkeypatch.setattr(lifecycle, "locate_project_root", lambda: None)

    def fake_create_mission(
        *,
        mission_slug: str,
        mission_type: str | None,
        json_output: bool,
        topology: MissionTopology,
    ) -> None:
        assert mission_slug == "my-feature"
        assert mission_type is None
        assert json_output is False
        assert topology is MissionTopology.COORD  # default when --topology omitted (#2218)
        lifecycle._console.print("[green]OK[/green] Mission created: my-feature")

    monkeypatch.setattr(lifecycle.agent_feature, "create_mission", fake_create_mission)

    result = runner.invoke(_app, ["my feature"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "Scaffold-only:" in result.output
    assert "no complete spec was authored" in result.output
    assert "spec-kitty plan --mission my-feature" in result.output

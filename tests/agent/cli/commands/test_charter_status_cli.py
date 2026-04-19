"""CLI tests for `spec-kitty charter status` operator surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app
from specify_cli.tasks_support import TaskCliError

pytestmark = pytest.mark.fast

runner = CliRunner()


VALID_DIRECTIVE_BODY = {
    "id": "PROJECT_001",
    "schema_version": "1.0",
    "title": "Mission Scope Directive",
    "intent": "Capture project mission scope for governance synthesis tests.",
    "enforcement": "required",
}


def _write_interview_answers(repo_root: Path) -> None:
    answers_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    answers_path.write_text(
        """\
schema_version: '1'
mission: software-dev
profile: minimal
answers:
  mission_type: software_dev
  testing_philosophy: ''
  neutrality_posture: ''
  risk_appetite: ''
selected_paradigms: []
selected_directives: []
available_tools: []
""",
        encoding="utf-8",
    )


def _write_url_config(repo_root: Path) -> None:
    config_path = repo_root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """\
charter:
  synthesis_inputs:
    url_list:
      - https://example.com/governance
""",
        encoding="utf-8",
    )


def _write_generated_directive(repo_root: Path, body: dict[str, object]) -> None:
    path = (
        repo_root
        / ".kittify"
        / "charter"
        / "generated"
        / "directives"
        / "001-mission-type-scope-directive.directive.yaml"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(body, fh)


class TestCharterStatus:
    def test_status_json_gracefully_degrades_without_charter_bundle(
        self, tmp_path: Path
    ) -> None:
        _write_url_config(tmp_path)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ), patch(
            "specify_cli.cli.commands.charter.ensure_charter_bundle_fresh",
            side_effect=TaskCliError("Charter not found"),
        ):
            result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["charter_sync"]["available"] is False
        assert data["synthesis"]["generation_state"] == "not_started"
        assert data["synthesis"]["evidence"]["configured_url_count"] == 1

    def test_generated_host_roundtrip_status_reports_promoted_provenance(
        self, tmp_path: Path
    ) -> None:
        _write_interview_answers(tmp_path)
        _write_url_config(tmp_path)
        _write_generated_directive(tmp_path, VALID_DIRECTIVE_BODY)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ):
            synth_result = runner.invoke(app, ["synthesize"])
        assert synth_result.exit_code == 0, synth_result.output

        doctrine_path = (
            tmp_path
            / ".kittify"
            / "doctrine"
            / "directives"
            / "001-mission-type-scope-directive.directive.yaml"
        )
        provenance_path = (
            tmp_path
            / ".kittify"
            / "charter"
            / "provenance"
            / "directive-mission-type-scope-directive.yaml"
        )
        manifest_path = (
            tmp_path / ".kittify" / "charter" / "synthesis-manifest.yaml"
        )

        assert doctrine_path.exists()
        assert provenance_path.exists()
        assert manifest_path.exists()

        updated_body = dict(VALID_DIRECTIVE_BODY)
        updated_body["title"] = "Mission Scope Directive Updated"
        updated_body["intent"] = "Updated mission scope after host-directed resynthesis."
        _write_generated_directive(tmp_path, updated_body)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ):
            resynth_result = runner.invoke(
                app,
                ["resynthesize", "--topic", "directive:PROJECT_001"],
            )
        assert resynth_result.exit_code == 0, resynth_result.output

        yaml = YAML(typ="safe")
        doctrine_data = yaml.load(doctrine_path.read_text(encoding="utf-8"))
        assert doctrine_data["title"] == "Mission Scope Directive Updated"
        assert "host-directed resynthesis" in doctrine_data["intent"]

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ), patch(
            "specify_cli.cli.commands.charter.ensure_charter_bundle_fresh",
            side_effect=TaskCliError("Charter not found"),
        ):
            status_result = runner.invoke(app, ["status", "--json", "--provenance"])

        assert status_result.exit_code == 0, status_result.output
        data = json.loads(status_result.output)
        assert data["charter_sync"]["available"] is False
        assert data["synthesis"]["generation_state"] == "promoted"
        assert data["synthesis"]["manifest"]["state"] == "valid"
        assert data["synthesis"]["generated_inputs"]["counts"]["directive"] == 1
        assert data["synthesis"]["provenance"]["parsed_count"] == 1
        assert data["synthesis"]["evidence"]["configured_url_count"] == 1
        entry = data["synthesis"]["provenance"]["entries"][0]
        assert entry["artifact_urn"] == "directive:PROJECT_001"
        assert entry["adapter_id"] == "generated"

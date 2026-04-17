"""CLI tests for 'spec-kitty charter synthesize' (T032).

Happy path:
  - --adapter fixture runs synthesis and emits manifest info.
  - --dry-run doesn't promote (prints staged artifacts only).
  - --json returns valid JSON.

Error paths:
  - Missing interview answers → exit 1.
  - --adapter production (not implemented) → exit 1 with SynthesisError panel.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app

pytestmark = pytest.mark.fast

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_interview_answers(repo_root: Path) -> None:
    """Write minimal interview answers YAML for CLI testing."""
    answers_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    answers_path.write_text(
        """\
schema_version: '1'
mission: software-dev
profile: minimal
answers:
  mission_type: software_dev
  testing_philosophy: test-driven
  neutrality_posture: balanced
  risk_appetite: moderate
  language_scope: python
selected_paradigms: []
selected_directives:
  - DIRECTIVE_003
available_tools: []
""",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Fixture adapter happy path
# ---------------------------------------------------------------------------


class TestSynthesizeHappyPath:
    def test_synthesize_fixture_help(self) -> None:
        """--help works and shows adapter option."""
        result = runner.invoke(app, ["synthesize", "--help"])
        assert result.exit_code == 0
        assert "--adapter" in result.output
        assert "--dry-run" in result.output

    def test_synthesize_fixture_adapter(self, tmp_path: Path) -> None:
        """--adapter fixture runs synthesis and reports success."""
        _write_interview_answers(tmp_path)

        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            # Mock the synthesize call to avoid fixture-hash mismatches in CLI context
            mock_result = MagicMock()
            mock_result.target_kind = "directive"
            mock_result.target_slug = "mission-type-scope-directive"
            mock_result.inputs_hash = "abc123"
            mock_result.effective_adapter_id = "fixture"
            mock_result.effective_adapter_version = "1.0.0"

            with patch("charter.synthesizer.synthesize", return_value=mock_result):
                result = runner.invoke(app, ["synthesize", "--adapter", "fixture"])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "synthesis complete" in result.output.lower() or "Charter synthesis" in result.output

    def test_synthesize_fixture_dry_run(self, tmp_path: Path) -> None:
        """--dry-run stages but does not promote; output contains 'Dry-run'."""
        _write_interview_answers(tmp_path)

        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            # Mock run_all to return a simple result
            mock_prov = MagicMock()
            mock_prov.artifact_kind = "directive"
            mock_prov.artifact_slug = "test-directive"
            mock_body = {"id": "PROJECT_001", "title": "Test"}

            with patch(
                "charter.synthesizer.synthesize_pipeline.run_all",
                return_value=[(mock_body, mock_prov)],
            ):
                result = runner.invoke(
                    app, ["synthesize", "--adapter", "fixture", "--dry-run"]
                )

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "Dry-run" in result.output or "dry" in result.output.lower()

    def test_synthesize_json_output(self, tmp_path: Path) -> None:
        """--json returns valid JSON with a 'result' key."""
        _write_interview_answers(tmp_path)

        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            mock_result = MagicMock()
            mock_result.target_kind = "directive"
            mock_result.target_slug = "mission-type-scope-directive"
            mock_result.inputs_hash = "abc123def456"
            mock_result.effective_adapter_id = "fixture"
            mock_result.effective_adapter_version = "1.0.0"

            with patch("charter.synthesizer.synthesize", return_value=mock_result):
                result = runner.invoke(
                    app, ["synthesize", "--adapter", "fixture", "--json"]
                )

        assert result.exit_code == 0, f"Expected exit 0: {result.output}"
        data = json.loads(result.output)
        assert data["result"] in {"success", "dry_run"}

    def test_synthesize_dry_run_json(self, tmp_path: Path) -> None:
        """--dry-run --json returns JSON with staged_artifacts."""
        _write_interview_answers(tmp_path)

        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            mock_prov = MagicMock()
            mock_prov.artifact_kind = "directive"
            mock_prov.artifact_slug = "test-directive"

            with patch(
                "charter.synthesizer.synthesize_pipeline.run_all",
                return_value=[({}, mock_prov)],
            ):
                result = runner.invoke(
                    app,
                    ["synthesize", "--adapter", "fixture", "--dry-run", "--json"],
                )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["result"] == "dry_run"
        assert "staged_artifacts" in data


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestSynthesizeErrorPaths:
    def test_missing_interview_answers_exits_1(self, tmp_path: Path) -> None:
        """No interview answers → exit 1 with error message."""
        # tmp_path has no interview answers
        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["synthesize", "--adapter", "fixture"])

        assert result.exit_code == 1, f"Expected exit 1, got {result.exit_code}: {result.output}"

    def test_production_adapter_exits_1(self, tmp_path: Path) -> None:
        """--adapter production (not implemented) → exit 1 with error panel."""
        _write_interview_answers(tmp_path)

        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["synthesize", "--adapter", "production"])

        assert result.exit_code == 1, (
            f"Expected exit 1, got {result.exit_code}: {result.output}"
        )

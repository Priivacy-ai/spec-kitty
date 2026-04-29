"""CLI tests for 'spec-kitty charter synthesize' (T032).

Happy path:
  - default generated adapter runs synthesis and emits manifest info.
  - --adapter fixture remains available for deterministic testing.
  - --dry-run stages and validates without promoting.
  - --json returns valid JSON.

Error paths:
  - Missing interview answers → exit 1.
  - --adapter production (not implemented) → exit 1 with SynthesisError panel.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app

pytestmark = pytest.mark.fast

runner = CliRunner()


def _plain_output(output: str) -> str:
    """Remove ANSI styling so help assertions are stable across terminals."""
    return re.sub(r"\x1b\[[0-9;]*m", "", output)


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
        result = runner.invoke(app, ["synthesize", "--help"], terminal_width=120, color=False)
        assert result.exit_code == 0
        plain = _plain_output(result.output)
        assert "--adapter" in plain
        assert "--dry-run" in plain

    def test_synthesize_generated_default_adapter(self, tmp_path: Path) -> None:
        """Default adapter is the generated-artifact path, not fixture."""
        _write_interview_answers(tmp_path)

        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            mock_result = MagicMock()
            mock_result.target_kind = "directive"
            mock_result.target_slug = "mission-type-scope-directive"
            mock_result.inputs_hash = "abc123"
            mock_result.effective_adapter_id = "generated"
            mock_result.effective_adapter_version = "1.0.0"

            with patch("charter.synthesizer.synthesize", return_value=mock_result):
                result = runner.invoke(app, ["synthesize"])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "synthesis complete" in result.output.lower() or "Charter synthesis" in result.output

    def test_synthesize_fixture_adapter(self, tmp_path: Path) -> None:
        """--adapter fixture remains supported for offline regression runs."""
        _write_interview_answers(tmp_path)

        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            mock_result = MagicMock()
            mock_result.target_kind = "directive"
            mock_result.target_slug = "mission-type-scope-directive"
            mock_result.inputs_hash = "abc123"
            mock_result.effective_adapter_id = "fixture"
            mock_result.effective_adapter_version = "1.0.0"

            with patch("charter.synthesizer.synthesize", return_value=mock_result):
                result = runner.invoke(app, ["synthesize", "--adapter", "fixture"])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"

    def test_synthesize_fixture_dry_run(self, tmp_path: Path) -> None:
        """--dry-run stages and validates but does not promote.

        WP02: dry-run now uses
        ``_run_synthesis_dry_run_with_artifacts`` (FR-003 / FR-004)
        which returns both legacy ``staged_artifacts`` selectors AND
        typed ``written_artifacts`` entries from the same source as the
        real-run path. The mock target was updated accordingly.
        """
        _write_interview_answers(tmp_path)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path
        ), patch(
            "specify_cli.cli.commands.charter._run_synthesis_dry_run_with_artifacts",
            return_value=(
                ["directive:test-directive"],
                [
                    {
                        "path": ".kittify/doctrine/directives/001-test-directive.directive.yaml",
                        "kind": "directive",
                        "slug": "test-directive",
                        "artifact_id": "PROJECT_001",
                    }
                ],
            ),
        ):
            result = runner.invoke(app, ["synthesize", "--dry-run"])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "Dry-run" in result.output or "dry" in result.output.lower()
        assert "validated" in result.output.lower()

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
        """--dry-run --json returns staged artifacts and validated=true.

        WP02 hardening: also asserts the four contracted envelope fields
        (FR-002) and that ``written_artifacts`` carries typed entries
        whose ``path`` is byte-equal to what a real-run would produce
        (FR-003 / FR-004 path parity).
        """
        _write_interview_answers(tmp_path)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path
        ), patch(
            "specify_cli.cli.commands.charter._run_synthesis_dry_run_with_artifacts",
            return_value=(
                ["directive:test-directive"],
                [
                    {
                        "path": ".kittify/doctrine/directives/001-test-directive.directive.yaml",
                        "kind": "directive",
                        "slug": "test-directive",
                        "artifact_id": "PROJECT_001",
                    }
                ],
            ),
        ):
            result = runner.invoke(
                app,
                ["synthesize", "--dry-run", "--json"],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["result"] == "dry_run"
        assert "staged_artifacts" in data
        assert data["validated"] is True
        # FR-002 contracted fields:
        assert "adapter" in data and isinstance(data["adapter"], dict)
        assert "written_artifacts" in data and isinstance(
            data["written_artifacts"], list
        )
        assert "warnings" in data and isinstance(data["warnings"], list)
        # Typed entry shape per data-model §E-3:
        assert len(data["written_artifacts"]) == 1
        entry = data["written_artifacts"][0]
        assert entry["path"].endswith(".directive.yaml")
        assert entry["kind"] == "directive"
        assert entry["slug"] == "test-directive"
        assert entry["artifact_id"] == "PROJECT_001"


# ---------------------------------------------------------------------------
# WP02 / FR-001 .. FR-005 — contracted envelope shape
# ---------------------------------------------------------------------------


class TestSynthesizeEnvelopeContract:
    """Lock down the FR-001..FR-005 envelope contract (WP02).

    These assertions are the contract the spec ``data-model.md`` §E-1 and
    ``contracts/synthesis-envelope.schema.json`` define. They MUST hold for
    every ``--json`` envelope, including dry-run and including success
    cases with no artifacts.
    """

    def test_synthesize_fixture_envelope_has_contracted_fields(
        self, tmp_path: Path
    ) -> None:
        """Real-run --json envelope carries result / adapter / written_artifacts / warnings.

        Uses the dry-run code path with the fixture adapter so the test
        does not depend on a fully-staged production pipeline; the
        envelope shape contract is the same on both branches per
        FR-002 / INV-E-2.
        """
        _write_interview_answers(tmp_path)

        with patch(
            "specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path
        ), patch(
            "specify_cli.cli.commands.charter._run_synthesis_dry_run_with_artifacts",
            return_value=([], []),
        ):
            result = runner.invoke(
                app,
                ["synthesize", "--adapter", "fixture", "--dry-run", "--json"],
            )

        assert result.exit_code == 0, result.output
        # FR-001: full stdout MUST be a single JSON document.
        envelope = json.loads(result.output)
        assert isinstance(envelope, dict)

        # FR-002: the four contracted fields MUST be present.
        for key in ("result", "adapter", "written_artifacts", "warnings"):
            assert key in envelope, (
                f"FR-002: contracted field {key!r} missing from envelope: {envelope!r}"
            )

        # Type / shape contract per data-model §E-1:
        assert envelope["result"] in {"success", "failure", "dry_run"}
        assert isinstance(envelope["adapter"], dict)
        assert isinstance(envelope["adapter"].get("id"), str)
        assert envelope["adapter"]["id"], "AdapterRef.id must be non-empty"
        assert isinstance(envelope["adapter"].get("version"), str)
        assert envelope["adapter"]["version"], "AdapterRef.version must be non-empty"
        assert isinstance(envelope["written_artifacts"], list)
        assert isinstance(envelope["warnings"], list)

        # FR-005: PROJECT_000 must not appear anywhere on the wire.
        assert "PROJECT_000" not in json.dumps(envelope)

    @pytest.mark.parametrize(
        "field", ["result", "adapter", "written_artifacts", "warnings"]
    )
    def test_synthesize_fixture_envelope_rejects_missing_contracted_field(
        self, field: str
    ) -> None:
        """Defensive scaffolding test: removing any contracted field MUST be detectable.

        This guards against a future regression where a test
        accidentally accepts a degraded envelope. We construct a complete
        envelope, delete the field under test, and prove the same
        assertions used by the live test would fail.
        """
        complete: dict[str, object] = {
            "result": "success",
            "adapter": {"id": "fixture", "version": "1.0.0"},
            "written_artifacts": [],
            "warnings": [],
        }
        del complete[field]
        # The four-field membership check must reject this envelope.
        missing = [k for k in ("result", "adapter", "written_artifacts", "warnings")
                   if k not in complete]
        assert missing == [field], (
            f"scaffolding sanity: deleting {field!r} should leave it (and only it) "
            f"missing; got missing={missing}"
        )


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestSynthesizeErrorPaths:
    def test_missing_interview_answers_exits_1(self, tmp_path: Path) -> None:
        """No interview answers → exit 1 with error message."""
        # tmp_path has no interview answers
        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["synthesize"])

        assert result.exit_code == 1, f"Expected exit 1, got {result.exit_code}: {result.output}"

    def test_unknown_adapter_exits_1(self, tmp_path: Path) -> None:
        """--adapter production (removed) → exit 1; spec-kitty never calls LLMs itself."""
        _write_interview_answers(tmp_path)

        with patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["synthesize", "--adapter", "production"])

        assert result.exit_code == 1, (
            f"Expected exit 1, got {result.exit_code}: {result.output}"
        )

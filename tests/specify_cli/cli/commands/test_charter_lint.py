"""CLI integration tests for ``spec-kitty charter lint`` (T037).

Uses Typer CliRunner with LintEngine.run() mocked to avoid needing a real DRG.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.charter_lint.findings import DecayReport, LintFinding
from specify_cli.cli.commands.charter import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_finding(
    category: str = "orphan",
    type_: str = "orphaned_directive",
    id_: str = "directive:DIR-001",
    severity: str = "medium",
    message: str = "Test finding",
    feature_id: str | None = None,
    remediation_hint: str | None = "Fix it",
) -> LintFinding:
    return LintFinding(
        category=category,
        type=type_,
        id=id_,
        severity=severity,
        message=message,
        feature_id=feature_id,
        remediation_hint=remediation_hint,
    )


def _make_report(findings: list[LintFinding] | None = None) -> DecayReport:
    return DecayReport(
        findings=findings or [],
        scanned_at="2026-04-22T12:00:00+00:00",
        feature_scope=None,
        duration_seconds=0.123,
        drg_node_count=5,
        drg_edge_count=3,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCharterlintJsonOutput:
    """T037-S1: --json output is valid JSON with no extra text."""

    def test_json_output_valid(self, tmp_path: Path) -> None:
        findings = [
            _make_finding(category="orphan", severity="medium"),
            _make_finding(category="contradiction", severity="high", type_="adr_topic_clash", id_="topic:caching"),
        ]
        mock_report = _make_report(findings)

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=mock_report),
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint", "--json"])

        assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output!r}"
        # Output must be parseable as JSON
        parsed = json.loads(result.output)
        assert "findings" in parsed
        assert parsed["finding_count"] == 2

    def test_json_output_no_extra_text(self, tmp_path: Path) -> None:
        mock_report = _make_report([_make_finding()])

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=mock_report),
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint", "--json"])

        assert result.exit_code == 0
        # The entire output must be valid JSON (no leading/trailing non-JSON text)
        stripped = result.output.strip()
        parsed = json.loads(stripped)
        assert isinstance(parsed, dict)


class TestCharterlintSeverityFilter:
    """T037-S2: --severity high filters out low/medium findings."""

    def test_severity_high_filters_low_medium(self, tmp_path: Path) -> None:
        findings = [
            _make_finding(category="orphan", severity="low"),
            _make_finding(category="staleness", severity="medium", type_="stale_synthesized_artifact", id_="syn:SYN-001"),
            _make_finding(category="contradiction", severity="high", type_="adr_topic_clash", id_="topic:db"),
        ]
        # Simulate filter_by_severity by only returning the high finding
        high_only = DecayReport(
            findings=[findings[2]],
            scanned_at="2026-04-22T12:00:00+00:00",
            feature_scope=None,
            duration_seconds=0.05,
            drg_node_count=3,
            drg_edge_count=1,
        )

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=high_only),
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint", "--json", "--severity", "high"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        for f in parsed["findings"]:
            assert f["severity"] not in {"low", "medium"}, (
                f"Found low/medium severity in --severity high output: {f}"
            )


class TestCharterlintFeatureScope:
    """T037-S3: --feature scopes findings."""

    def test_feature_flag_passed_to_engine(self, tmp_path: Path) -> None:
        mock_report = _make_report([
            _make_finding(feature_id="042-my-feature"),
        ])

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=mock_report) as mock_run,
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint", "--feature", "042-my-feature", "--json"])

        assert result.exit_code == 0
        # Verify the feature was passed through
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("feature_scope") == "042-my-feature"

    def test_feature_scoped_run_succeeds(self, tmp_path: Path) -> None:
        mock_report = _make_report([])

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=mock_report),
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint", "--feature", "042", "--json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["finding_count"] == 0


class TestCharterlintOrphansOnly:
    """T037-S4: --orphans flag limits checks to orphan category."""

    def test_orphans_flag_passed_to_engine(self, tmp_path: Path) -> None:
        mock_report = _make_report([_make_finding(category="orphan")])

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=mock_report) as mock_run,
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint", "--orphans", "--json"])

        assert result.exit_code == 0
        # Engine must have been called with checks={"orphans"}
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("checks") == {"orphans"}

    def test_human_readable_orphans_output(self, tmp_path: Path) -> None:
        mock_report = _make_report([
            _make_finding(category="orphan", type_="orphaned_directive"),
        ])

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=mock_report),
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint", "--orphans"])

        assert result.exit_code == 0
        assert "orphan" in result.output


class TestCharterlintNoDRG:
    """T037-S5: no DRG → exit 0, no exception, 'No decay detected' output."""

    def test_no_drg_exits_zero(self, tmp_path: Path) -> None:
        empty_report = _make_report([])

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=empty_report),
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint"])

        assert result.exit_code == 0

    def test_no_drg_no_decay_message(self, tmp_path: Path) -> None:
        empty_report = _make_report([])

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=empty_report),
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint"])

        assert result.exit_code == 0
        assert "No decay detected" in result.output or "no decay" in result.output.lower()

    def test_no_drg_json_empty_findings(self, tmp_path: Path) -> None:
        empty_report = _make_report([])

        with (
            patch("specify_cli.charter_lint.engine.LintEngine.run", return_value=empty_report),
            patch("specify_cli.tasks_support.find_repo_root", return_value=tmp_path),
        ):
            result = runner.invoke(app, ["lint", "--json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["finding_count"] == 0
        assert parsed["findings"] == []

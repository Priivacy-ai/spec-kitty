from __future__ import annotations

from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.analysis_report import (
    ANALYSIS_REPORT_FILENAME,
    check_analysis_report_current,
    write_analysis_report,
)
from specify_cli.cli.commands.agent.mission import app as mission_app
from specify_cli.cli.commands.agent.workflow import _require_current_analysis_report
from specify_cli.frontmatter import FrontmatterManager


def _write_required_artifacts(feature_dir):
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-001.\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")


def test_write_analysis_report_records_input_hashes(tmp_path):
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    result = write_analysis_report(
        feature_dir=feature_dir,
        repo_root=repo_root,
        body="# Specification Analysis Report\n\nCritical Issues Count: 0\nHigh Issues Count: 0\nPASS\n",
        analyzer_agent="codex",
    )

    assert result.path == feature_dir / ANALYSIS_REPORT_FILENAME
    frontmatter, body = FrontmatterManager().read(result.path)
    assert frontmatter["artifact_type"] == "spec-kitty.analysis-report"
    assert frontmatter["command"] == "/spec-kitty.analyze"
    assert frontmatter["analyzer_agent"] == "codex"
    assert frontmatter["input_artifacts"]["spec.md"]["sha256"]
    assert frontmatter["verdict"] == "ready"
    assert "# Specification Analysis Report" in body


def test_analysis_report_freshness_detects_stale_inputs(tmp_path):
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)
    write_analysis_report(
        feature_dir=feature_dir,
        repo_root=repo_root,
        body="# Report\n\nPASS\n",
    )

    assert check_analysis_report_current(feature_dir, repo_root).ok is True

    (feature_dir / "tasks.md").write_text("# Tasks\n\nChanged.\n", encoding="utf-8")
    freshness = check_analysis_report_current(feature_dir, repo_root)
    assert freshness.ok is False
    assert freshness.reason == "stale_analysis_report"
    assert "tasks.md" in freshness.mismatches


def test_implement_gate_blocks_missing_analysis_report(tmp_path, capsys):
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    with pytest.raises(typer.Exit):
        _require_current_analysis_report(feature_dir, repo_root, "sample-01KS")

    out = capsys.readouterr().out
    assert "analysis_report_required" in out
    assert "/spec-kitty.analyze --mission sample-01KS" in out


def test_implement_gate_allows_current_analysis_report(tmp_path):
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)
    write_analysis_report(
        feature_dir=feature_dir,
        repo_root=repo_root,
        body="# Report\n\nPASS\n",
    )

    _require_current_analysis_report(feature_dir, repo_root, "sample-01KS")


def test_record_analysis_command_persists_report(tmp_path, monkeypatch):
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)
    input_file = tmp_path / "analysis.md"
    input_file.write_text("# Analysis\n\nCritical Issues Count: 0\nPASS\n", encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission.locate_project_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission.get_main_repo_root",
        lambda path: path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission.resolve_mission_handle",
        lambda _handle, _repo_root: SimpleNamespace(feature_dir=feature_dir),
    )
    emitted: dict[str, object] = {}
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission._emit_json",
        lambda payload: emitted.update(payload),
    )

    result = CliRunner().invoke(
        mission_app,
        [
            "record-analysis",
            "--mission",
            feature_dir.name,
            "--input-file",
            str(input_file),
            "--agent",
            "codex",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert emitted["success"] is True
    report_path = feature_dir / ANALYSIS_REPORT_FILENAME
    assert emitted["path"] == str(report_path)
    frontmatter, body = FrontmatterManager().read(report_path)
    assert frontmatter["analyzer_agent"] == "codex"
    assert frontmatter["input_artifacts"]["tasks.md"]["sha256"]
    assert "# Analysis" in body

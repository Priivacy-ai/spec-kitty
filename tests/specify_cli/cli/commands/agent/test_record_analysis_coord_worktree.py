"""WP01 (#1989): record-analysis must write to the PRIMARY checkout under coord topology.

Regression coverage for the root-cause defect: ``record_analysis`` resolved the
write destination via the coord-aware ``_find_feature_directory`` and handed the
coordination-worktree path (which lacks ``spec.md``) to ``write_analysis_report``,
which then failed with "Required artifact missing". The fix anchors the write to
the topology-blind ``primary_feature_dir_for_mission``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

pytestmark = [pytest.mark.integration]

from specify_cli.analysis_report import ANALYSIS_REPORT_FILENAME, write_analysis_report
from specify_cli.cli.commands.agent.mission import app as mission_app
from specify_cli.cli.commands.agent.workflow import _require_current_analysis_report

_CARRIER_READY = (
    "---\n"
    "schema: analysis-findings/v1\n"
    "findings: []\n"
    "counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\n"
    "---\n\n"
    "# Specification Analysis Report\n\nNo blocking findings.\n"
)


def _make_primary(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-001.\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")


def _make_coord_without_spec(coord_feature_dir: Path) -> None:
    # The coordination worktree is populated with plan.md but NOT spec.md —
    # exactly the topology that produced #1989.
    coord_feature_dir.mkdir(parents=True)
    (coord_feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")


def _patch_resolution(monkeypatch, repo_root: Path, coord_feature_dir: Path) -> None:
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission.locate_project_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission.get_main_repo_root",
        lambda path: path,
    )
    # _find_feature_directory is the coord-aware resolver; force it to return the
    # coordination-worktree path (the buggy input the write path must NOT use).
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission._find_feature_directory",
        lambda *_args, **_kwargs: coord_feature_dir,
    )


def test_record_analysis_writes_to_primary_when_coord_lacks_spec(tmp_path, monkeypatch):
    slug = "sample-01KS"
    repo_root = tmp_path
    primary_feature_dir = repo_root / "kitty-specs" / slug
    coord_feature_dir = repo_root / ".worktrees" / f"{slug}-coord" / "kitty-specs" / slug
    _make_primary(primary_feature_dir)
    _make_coord_without_spec(coord_feature_dir)

    input_file = tmp_path.parent / f"{tmp_path.name}-analysis.md"
    input_file.write_text(_CARRIER_READY, encoding="utf-8")

    _patch_resolution(monkeypatch, repo_root, coord_feature_dir)
    emitted: dict[str, object] = {}
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission._emit_json",
        lambda payload: emitted.update(payload),
    )

    result = CliRunner().invoke(
        mission_app,
        ["record-analysis", "--mission", slug, "--input-file", str(input_file), "--json"],
    )

    # Before the fix: exit 1 with "Required artifact missing" (coord lacks spec.md).
    assert result.exit_code == 0, emitted
    assert emitted["success"] is True
    # The report must land in the PRIMARY checkout, never the coord worktree.
    assert emitted["path"] == str(primary_feature_dir / ANALYSIS_REPORT_FILENAME)
    assert (primary_feature_dir / ANALYSIS_REPORT_FILENAME).exists()
    assert not (coord_feature_dir / ANALYSIS_REPORT_FILENAME).exists()


def test_record_analysis_writes_to_primary_without_coord_worktree(tmp_path, monkeypatch):
    """Regression: the no-coord-worktree path is unchanged (write still lands in primary)."""
    slug = "sample-01KS"
    repo_root = tmp_path
    primary_feature_dir = repo_root / "kitty-specs" / slug
    _make_primary(primary_feature_dir)

    input_file = tmp_path.parent / f"{tmp_path.name}-analysis-2.md"
    input_file.write_text(_CARRIER_READY, encoding="utf-8")

    # No coord worktree: _find_feature_directory resolves to the primary dir.
    _patch_resolution(monkeypatch, repo_root, primary_feature_dir)
    emitted: dict[str, object] = {}
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission._emit_json",
        lambda payload: emitted.update(payload),
    )

    result = CliRunner().invoke(
        mission_app,
        ["record-analysis", "--mission", slug, "--input-file", str(input_file), "--json"],
    )

    assert result.exit_code == 0, emitted
    assert emitted["success"] is True
    assert emitted["path"] == str(primary_feature_dir / ANALYSIS_REPORT_FILENAME)


# --- Read-side companion (#1989): the implement gate must READ the report from
# the primary checkout, where record-analysis writes it. The implement command
# previously located analysis-report.md via the topology-aware
# ``candidate_feature_dir_for_mission`` (→ coordination worktree, which lacks the
# report), so it falsely reported "missing" under coord topology. The gate now
# resolves via the topology-blind ``primary_feature_dir_for_mission``.


def test_implement_gate_finds_report_in_primary_not_coord(tmp_path):
    slug = "sample-01KS"
    repo_root = tmp_path
    primary_feature_dir = repo_root / "kitty-specs" / slug
    coord_feature_dir = repo_root / ".worktrees" / f"{slug}-coord" / "kitty-specs" / slug
    _make_primary(primary_feature_dir)
    _make_coord_without_spec(coord_feature_dir)

    # Persist a valid outer-wrapper report in the PRIMARY checkout (as the fixed
    # record-analysis does).
    write_analysis_report(
        feature_dir=primary_feature_dir,
        repo_root=repo_root,
        body=_CARRIER_READY,
        analyzer_agent="test",
    )

    # Passing the PRIMARY dir (what the fixed gate does) → the gate is satisfied.
    _require_current_analysis_report(primary_feature_dir, repo_root, slug)

    # Passing the COORD dir (the old buggy behavior) → the gate fails: the report
    # is absent there. This documents why the gate must anchor to primary.
    with pytest.raises(typer.Exit):
        _require_current_analysis_report(coord_feature_dir, repo_root, slug)

from __future__ import annotations

from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

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


def _init_committed_git_project(repo_root: Path, *, branch: str = "feature") -> None:
    (repo_root / ".kittify").mkdir(exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_root, check=True)
    subprocess.run(["git", "branch", "-M", branch], cwd=repo_root, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_root, check=True, capture_output=True)


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


def test_analysis_report_survives_subtask_checkbox_churn(tmp_path):
    """#1764: ``mark-status``/``move-task`` flipping subtask checkboxes in tasks.md
    must NOT invalidate a recorded analysis (only substantive changes should)."""
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-001.\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T001 Do the thing (WP01)\n- [ ] T002 Do the other thing (WP01)\n",
        encoding="utf-8",
    )
    write_analysis_report(feature_dir=feature_dir, repo_root=repo_root, body="# Report\n\nPASS\n")
    assert check_analysis_report_current(feature_dir, repo_root).ok is True

    # Status churn: a subtask is marked done (mark-status flips [ ] -> [x]).
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [x] T001 Do the thing (WP01)\n- [ ] T002 Do the other thing (WP01)\n",
        encoding="utf-8",
    )
    assert check_analysis_report_current(feature_dir, repo_root).ok is True

    # Substantive change to a task definition: still goes stale.
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [x] T001 Do a DIFFERENT thing (WP01)\n- [ ] T002 Do the other thing (WP01)\n",
        encoding="utf-8",
    )
    freshness = check_analysis_report_current(feature_dir, repo_root)
    assert freshness.ok is False
    assert "tasks.md" in freshness.mismatches


def test_charter_hash_resolves_canonical_root_from_worktree(tmp_path):
    """#1823: analysis reports read from a linked worktree must hash the
    canonical (main checkout) charter, not the worktree-local copy."""
    from charter.resolution import resolve_canonical_repo_root

    from specify_cli.analysis_report import _sha256_file, collect_input_artifact_hashes

    main = tmp_path / "main"
    charter_file = main / ".kittify" / "charter" / "charter.md"
    charter_file.parent.mkdir(parents=True)
    charter_file.write_text("# Canonical charter\n", encoding="utf-8")
    _init_committed_git_project(main)

    worktree = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "lane", str(worktree)],
        cwd=main, check=True, capture_output=True,
    )
    # Diverge the worktree-local copy: hashing it instead of the canonical
    # charter is exactly the #1823 bug.
    worktree_charter = worktree / ".kittify" / "charter" / "charter.md"
    worktree_charter.write_text("# Worktree-local drift\n", encoding="utf-8")

    feature_dir = worktree / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    resolve_canonical_repo_root.cache_clear()
    hashes = collect_input_artifact_hashes(feature_dir, worktree)

    assert hashes["charter"]["path"] == str(charter_file.resolve())
    assert hashes["charter"]["sha256"] == _sha256_file(charter_file)
    assert hashes["charter"]["sha256"] != _sha256_file(worktree_charter)


def test_charter_hash_falls_back_to_repo_root_outside_git(tmp_path):
    """Outside any git repo the resolver cannot run; the charter probe must
    degrade to the passed repo_root instead of raising."""
    from charter.resolution import resolve_canonical_repo_root

    from specify_cli.analysis_report import collect_input_artifact_hashes

    charter_file = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_file.parent.mkdir(parents=True)
    charter_file.write_text("# Local charter\n", encoding="utf-8")
    feature_dir = tmp_path / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    resolve_canonical_repo_root.cache_clear()
    hashes = collect_input_artifact_hashes(feature_dir, tmp_path)

    assert hashes["charter"]["path"] == str(charter_file)
    assert hashes["charter"]["sha256"] is not None


def test_charter_hash_propagates_git_common_dir_unavailable(tmp_path):
    """If git/common-dir resolution is unavailable, do not synthesize a local
    charter hash that pretends canonical evidence was available."""
    from charter.resolution import GitCommonDirUnavailableError, resolve_canonical_repo_root

    from specify_cli.analysis_report import collect_input_artifact_hashes

    charter_file = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_file.parent.mkdir(parents=True)
    charter_file.write_text("# Local charter\n", encoding="utf-8")
    feature_dir = tmp_path / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    resolve_canonical_repo_root.cache_clear()
    with (
        patch("charter.resolution.subprocess.run", side_effect=FileNotFoundError("git")),
        pytest.raises(GitCommonDirUnavailableError),
    ):
        collect_input_artifact_hashes(feature_dir, tmp_path)


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


def test_record_analysis_refuses_dirty_worktree_before_write(tmp_path, monkeypatch):
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)
    _init_committed_git_project(repo_root, branch="feature")
    (repo_root / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")
    input_file = tmp_path.parent / f"{tmp_path.name}-analysis.md"
    input_file.write_text("# Analysis\n\nPASS\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission.locate_project_root", lambda: repo_root)
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission.get_main_repo_root", lambda path: path)
    emitted: dict[str, object] = {}
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission._emit_json", lambda payload: emitted.update(payload))

    result = CliRunner().invoke(
        mission_app,
        ["record-analysis", "--mission", feature_dir.name, "--input-file", str(input_file), "--json"],
    )

    assert result.exit_code == 1
    assert emitted["error_code"] == "DIRTY_WORKTREE"
    assert not (feature_dir / ANALYSIS_REPORT_FILENAME).exists()


def test_record_analysis_refuses_protected_branch_before_write(tmp_path, monkeypatch):
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)
    _init_committed_git_project(repo_root, branch="main")
    input_file = tmp_path.parent / f"{tmp_path.name}-analysis.md"
    input_file.write_text("# Analysis\n\nPASS\n", encoding="utf-8")

    # _enforce_analysis_report_write_preflight uses subprocess git rev-parse --show-toplevel
    # to get the CWD git root for the branch check. chdir into tmp_path so the subprocess
    # sees the tmp repo (branch "main", protected) rather than the CI runner's checkout.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission.locate_project_root", lambda: repo_root)
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission.get_main_repo_root", lambda path: path)
    emitted: dict[str, object] = {}
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission._emit_json", lambda payload: emitted.update(payload))

    result = CliRunner().invoke(
        mission_app,
        ["record-analysis", "--mission", feature_dir.name, "--input-file", str(input_file), "--json"],
    )

    assert result.exit_code == 1
    assert emitted["error_code"] == "PROTECTED_BRANCH_REFUSED"
    assert not (feature_dir / ANALYSIS_REPORT_FILENAME).exists()

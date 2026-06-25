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


_CARRIER_READY = (
    "---\n"
    "schema: analysis-findings/v1\n"
    "findings: []\n"
    "counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\n"
    "---\n\n"
    "# Specification Analysis Report\n\nNo blocking findings.\n"
)


def test_write_analysis_report_records_input_hashes(tmp_path):
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    result = write_analysis_report(
        feature_dir=feature_dir,
        repo_root=repo_root,
        body=_CARRIER_READY,
        analyzer_agent="codex",
    )

    assert result.path == feature_dir / ANALYSIS_REPORT_FILENAME
    frontmatter, body = FrontmatterManager().read(result.path)
    assert frontmatter["artifact_type"] == "spec-kitty.analysis-report"
    assert frontmatter["command"] == "/spec-kitty.analyze"
    assert frontmatter["analyzer_agent"] == "codex"
    assert frontmatter["input_artifacts"]["spec.md"]["sha256"]
    assert frontmatter["verdict"] == "ready"
    # The carrier frontmatter is consumed by the recorder; the persisted body is
    # the human-readable report only.
    assert "# Specification Analysis Report" in body
    assert "schema: analysis-findings/v1" not in body


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
    # Missing-report branch now emits a two-step recovery (WP03 / FR-005).
    assert "Run step 1: /spec-kitty.analyze" in out
    assert (
        "Run step 2: spec-kitty agent mission record-analysis "
        "--mission sample-01KS --input-file -"
    ) in out


def test_require_analysis_report_missing_emits_two_step_recovery(tmp_path, capsys):
    """_require_current_analysis_report emits two-step recovery for a missing report."""
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "my-mission"
    _write_required_artifacts(feature_dir)
    # Do NOT write analysis-report.md.

    with pytest.raises(typer.Exit):
        _require_current_analysis_report(feature_dir, repo_root, "my-mission")

    out = capsys.readouterr().out
    assert "Error: analysis_report_required:" in out
    assert "Run step 1: /spec-kitty.analyze" in out
    assert (
        "Run step 2: spec-kitty agent mission record-analysis "
        "--mission my-mission --input-file -"
    ) in out


def test_require_analysis_report_carrier_format_emits_recovery_command(tmp_path, capsys):
    """_require_current_analysis_report emits the exact carrier-format recovery command."""
    from specify_cli.analysis_report import ANALYSIS_REPORT_FILENAME

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "my-mission"
    _write_required_artifacts(feature_dir)

    # Write a carrier-format file (analysis-findings/v1 schema, not outer-wrapper).
    carrier_content = (
        "---\n"
        "schema: analysis-findings/v1\n"
        "findings: []\n"
        "counts:\n"
        "  critical: 0\n"
        "  high: 0\n"
        "  medium: 0\n"
        "  low: 0\n"
        "verdict_hint: ready\n"
        "---\n\n"
        "Report body.\n"
    )
    report_path = feature_dir / ANALYSIS_REPORT_FILENAME
    report_path.write_text(carrier_content, encoding="utf-8")

    with pytest.raises(typer.Exit):
        _require_current_analysis_report(feature_dir, repo_root, "my-mission")

    out = capsys.readouterr().out
    assert "Error: analysis_report_required:" in out
    # The raw reason code must NOT be shown; the explanatory message is shown instead.
    assert "carrier_format_not_wrapped" not in out
    assert "carrier format (analysis-findings/v1)" in out
    assert "Recovery: spec-kitty agent mission record-analysis" in out
    assert "--mission my-mission" in out
    assert str(report_path) in out


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
        "specify_cli.cli.commands.agent.mission_record_analysis.locate_project_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis.get_main_repo_root",
        lambda path: path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission.resolve_mission_handle",
        lambda _handle, _repo_root: SimpleNamespace(feature_dir=feature_dir),
    )
    emitted: dict[str, object] = {}
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis._emit_json",
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
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission_record_analysis.locate_project_root", lambda: repo_root)
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission_record_analysis.get_main_repo_root", lambda path: path)
    emitted: dict[str, object] = {}
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission_record_analysis._emit_json", lambda payload: emitted.update(payload))

    result = CliRunner().invoke(
        mission_app,
        ["record-analysis", "--mission", feature_dir.name, "--input-file", str(input_file), "--json"],
    )

    assert result.exit_code == 1
    assert emitted["error_code"] == "DIRTY_WORKTREE"
    assert not (feature_dir / ANALYSIS_REPORT_FILENAME).exists()


def test_record_analysis_succeeds_on_protected_branch_via_materialize(tmp_path, monkeypatch):
    """record-analysis no longer REFUSES on a protected primary (01KVMBD6 / WP02).

    The protected-branch hard-refusal was removed: the report is written to the
    primary checkout (a plain file write, not a git op) and the commit is routed
    best-effort through ``commit_for_mission`` (materialize-then-retry). So on a
    protected ``main`` the command now SUCCEEDS (exit 0, report written) rather
    than failing with ``PROTECTED_BRANCH_REFUSED``. (Was
    ``test_record_analysis_refuses_protected_branch_before_write`` — renamed; the
    old refuse contract is superseded by the materialize-then-retry contract that
    ``test_accept_protected_branch_materialize_then_retry`` pins for accept.)
    """
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)
    _init_committed_git_project(repo_root, branch="main")
    input_file = tmp_path.parent / f"{tmp_path.name}-analysis.md"
    input_file.write_text("# Analysis\n\nPASS\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission_record_analysis.locate_project_root", lambda: repo_root)
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission_record_analysis.get_main_repo_root", lambda path: path)
    emitted: dict[str, object] = {}
    monkeypatch.setattr("specify_cli.cli.commands.agent.mission_record_analysis._emit_json", lambda payload: emitted.update(payload))

    result = CliRunner().invoke(
        mission_app,
        ["record-analysis", "--mission", feature_dir.name, "--input-file", str(input_file), "--json"],
    )

    assert result.exit_code == 0, result.output
    assert emitted["success"] is True
    assert (feature_dir / ANALYSIS_REPORT_FILENAME).exists()


# --- analysis-findings/v1 structured carrier (FR-004 / #1819) ----------------


def _carrier(findings_yaml: str, counts_yaml: str, *, hint: str | None = None) -> str:
    hint_line = f"verdict_hint: {hint}\n" if hint else ""
    return (
        "---\n"
        "schema: analysis-findings/v1\n"
        f"findings:\n{findings_yaml}"
        f"counts: {counts_yaml}\n"
        f"{hint_line}"
        "---\n\n"
    )


def test_find1_verdict_ignores_scary_prose_when_no_blocking_findings(tmp_path):
    """C-FIND-1: clean frontmatter + scary prose ("CRITICAL"/"HIGH"/"BLOCK") → ready."""
    from specify_cli.analysis_report import VERDICT_READY

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    body = _carrier(
        "  - {id: A1, severity: low, category: style, summary: nit}\n"
        "  - {id: A2, severity: medium, category: coverage, summary: gap}\n",
        "{critical: 0, high: 0, medium: 1, low: 1, info: 0}",
    ) + "We found CRITICAL HIGH issues that BLOCK everything (prose only).\n"

    result = write_analysis_report(feature_dir=feature_dir, repo_root=repo_root, body=body)
    assert result.verdict == VERDICT_READY
    frontmatter, _ = FrontmatterManager().read(result.path)
    assert frontmatter["verdict"] == "ready"
    assert frontmatter["issue_counts"]["medium"] == 1


def test_find1_verdict_blocked_despite_reassuring_prose(tmp_path):
    """C-FIND-1: one critical finding + "ready for implementation" prose → blocked."""
    from specify_cli.analysis_report import VERDICT_BLOCKED

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    body = _carrier(
        "  - {id: C1, severity: critical, category: charter, summary: violation}\n",
        "{critical: 1, high: 0, medium: 0, low: 0, info: 0}",
    ) + "No issues at all. PASS. READY FOR IMPLEMENTATION.\n"

    result = write_analysis_report(feature_dir=feature_dir, repo_root=repo_root, body=body)
    assert result.verdict == VERDICT_BLOCKED
    frontmatter, _ = FrontmatterManager().read(result.path)
    assert frontmatter["verdict"] == "blocked"


def test_find2_unknown_severity_fails_loudly_on_write(tmp_path):
    """C-FIND-2: unknown severity value → structured validation error on write."""
    from specify_cli.analysis_report import FindingsCarrierError

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    body = _carrier(
        "  - {id: X1, severity: catastrophic, category: x, summary: y}\n",
        "{critical: 0, high: 0, medium: 0, low: 0, info: 0}",
    )
    with pytest.raises(FindingsCarrierError, match="severity"):
        write_analysis_report(feature_dir=feature_dir, repo_root=repo_root, body=body)
    assert not (feature_dir / ANALYSIS_REPORT_FILENAME).exists()


def test_find2_counts_mismatch_fails_loudly_on_write(tmp_path):
    """C-FIND-2: counts not equal to findings[] tally → loud error."""
    from specify_cli.analysis_report import FindingsCarrierError

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    body = _carrier(
        "  - {id: H1, severity: high, category: x, summary: y}\n",
        "{critical: 0, high: 0, medium: 0, low: 0, info: 0}",  # claims 0 high, but 1 present
    )
    with pytest.raises(FindingsCarrierError, match="tally"):
        write_analysis_report(feature_dir=feature_dir, repo_root=repo_root, body=body)
    assert not (feature_dir / ANALYSIS_REPORT_FILENAME).exists()


def test_find2_verdict_hint_disagreement_fails_loudly(tmp_path):
    """C-FIND-2: verdict_hint disagreeing with computed verdict → loud error."""
    from specify_cli.analysis_report import FindingsCarrierError

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    body = _carrier(
        "  - {id: H1, severity: high, category: x, summary: y}\n",
        "{critical: 0, high: 1, medium: 0, low: 0, info: 0}",
        hint="ready",  # computed verdict is blocked
    )
    with pytest.raises(FindingsCarrierError, match="verdict_hint"):
        write_analysis_report(feature_dir=feature_dir, repo_root=repo_root, body=body)
    assert not (feature_dir / ANALYSIS_REPORT_FILENAME).exists()


def test_find3_legacy_report_records_unknown_without_exception(tmp_path):
    """C-FIND-3: a pre-v1 report (no carrier) records verdict unknown, never raises."""
    from specify_cli.analysis_report import VERDICT_UNKNOWN

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KS"
    _write_required_artifacts(feature_dir)

    # No carrier; prose says scary things — must NOT be substring-inferred.
    body = "# Report\n\nCRITICAL issues, BLOCK, no go.\n"
    result = write_analysis_report(feature_dir=feature_dir, repo_root=repo_root, body=body)
    assert result.verdict == VERDICT_UNKNOWN
    assert all(v is None for v in result.issue_counts.values())
    # Read/freshness path tolerates the legacy report (no exception, stays current).
    assert check_analysis_report_current(feature_dir, repo_root).ok is True


def test_no_substring_inference_symbols_remain():
    """T025: the prose substring inference is deleted — no magic strings remain."""
    import specify_cli.analysis_report as module

    assert not hasattr(module, "infer_verdict")
    assert not hasattr(module, "infer_issue_counts")
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "READY FOR IMPLEMENTATION" not in source


def test_implement_gate_detects_carrier_format_file(tmp_path):
    """check_analysis_report_current returns carrier_format_not_wrapped for v1 carrier files."""
    from specify_cli.analysis_report import (
        ANALYSIS_REPORT_FILENAME,
        ANALYSIS_REPORT_REASON_CARRIER_FORMAT,
        check_analysis_report_current,
    )

    feature_dir = tmp_path / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)

    # Write a carrier-format file (analysis-findings/v1 schema, not outer-wrapper)
    carrier_content = (
        "---\n"
        "schema: analysis-findings/v1\n"
        "findings: []\n"
        "counts:\n"
        "  critical: 0\n"
        "  high: 0\n"
        "  medium: 0\n"
        "  low: 0\n"
        "verdict_hint: ready\n"
        "---\n\n"
        "Report body.\n"
    )
    (feature_dir / ANALYSIS_REPORT_FILENAME).write_text(carrier_content, encoding="utf-8")

    result = check_analysis_report_current(feature_dir, tmp_path)

    assert result.ok is False
    assert result.stale is True
    assert result.missing is False
    assert result.reason == ANALYSIS_REPORT_REASON_CARRIER_FORMAT


def test_implement_gate_returns_generic_reason_for_arbitrary_frontmatter(tmp_path):
    """Arbitrary frontmatter (no schema, no artifact_type) falls through to the generic reason."""
    from specify_cli.analysis_report import check_analysis_report_current

    feature_dir = tmp_path / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)
    (feature_dir / "analysis-report.md").write_text(
        "---\ntitle: Some Random File\nauthor: Alice\n---\n\nBody.\n",
        encoding="utf-8",
    )

    result = check_analysis_report_current(feature_dir, tmp_path)

    assert result.reason == "invalid_analysis_report_artifact_type"

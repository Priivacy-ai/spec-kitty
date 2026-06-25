"""WP01 (#1989): record-analysis must write to the PRIMARY checkout under coord topology.

Regression coverage for the root-cause defect: ``record_analysis`` resolved the
write destination via the coord-aware ``_find_feature_directory`` and handed the
coordination-worktree path (which lacks ``spec.md``) to ``write_analysis_report``,
which then failed with "Required artifact missing". The fix anchors the write to
the topology-blind ``primary_feature_dir_for_mission``.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest
import typer
from typer.testing import CliRunner

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

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
        "specify_cli.cli.commands.agent.mission_record_analysis.locate_project_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis.get_main_repo_root",
        lambda path: path,
    )
    # _find_feature_directory is the coord-aware resolver; force it to return the
    # coordination-worktree path (the buggy input the write path must NOT use).
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis._find_feature_directory",
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
        "specify_cli.cli.commands.agent.mission_record_analysis._emit_json",
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
        "specify_cli.cli.commands.agent.mission_record_analysis._emit_json",
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


# --- Note #2 (mission review): pin the implement-gate read-anchor WIRING, not just
# the helper behavior. _analysis_report_gate_dir MUST route through the topology-blind
# primary_feature_dir_for_mission, never the coord-aware candidate_feature_dir_for_mission.
# Monkeypatching both resolvers to distinguishable sentinels makes a call-site swap
# (primary_ -> candidate_) fail this test.


def test_analysis_report_gate_dir_uses_primary_not_candidate(tmp_path, monkeypatch):
    from specify_cli.cli.commands.agent import workflow as workflow_mod

    primary_sentinel = tmp_path / "PRIMARY" / "mission"
    candidate_sentinel = tmp_path / "COORD" / "mission"
    monkeypatch.setattr(
        workflow_mod, "primary_feature_dir_for_mission", lambda _root, _slug: primary_sentinel
    )
    monkeypatch.setattr(
        workflow_mod, "candidate_feature_dir_for_mission", lambda _root, _slug: candidate_sentinel
    )

    resolved = workflow_mod._analysis_report_gate_dir(tmp_path, "sample-01KS")

    assert resolved == primary_sentinel
    assert resolved != candidate_sentinel  # a topology-aware (coord) resolution must NOT be used


# --- Note #1 (mission review): FR-002 — the persisted report must always be in the
# outer-wrapper format (artifact_type: spec-kitty.analysis-report), including under
# coord topology. The path is asserted elsewhere; here we open the written file and
# assert its frontmatter identity directly.


def test_record_analysis_persists_outer_wrapper_format_under_coord(tmp_path, monkeypatch):
    from specify_cli.analysis_report import ANALYSIS_REPORT_ARTIFACT_TYPE
    from specify_cli.frontmatter import FrontmatterManager

    slug = "sample-01KS"
    repo_root = tmp_path
    primary_feature_dir = repo_root / "kitty-specs" / slug
    coord_feature_dir = repo_root / ".worktrees" / f"{slug}-coord" / "kitty-specs" / slug
    _make_primary(primary_feature_dir)
    _make_coord_without_spec(coord_feature_dir)

    input_file = tmp_path.parent / f"{tmp_path.name}-analysis-fmt.md"
    input_file.write_text(_CARRIER_READY, encoding="utf-8")

    _patch_resolution(monkeypatch, repo_root, coord_feature_dir)
    emitted: dict[str, object] = {}
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis._emit_json",
        lambda payload: emitted.update(payload),
    )

    result = CliRunner().invoke(
        mission_app,
        ["record-analysis", "--mission", slug, "--input-file", str(input_file), "--json"],
    )
    assert result.exit_code == 0, emitted

    report_path = primary_feature_dir / ANALYSIS_REPORT_FILENAME
    frontmatter, _body = FrontmatterManager().read(report_path)
    # The carrier input (schema: analysis-findings/v1) MUST be wrapped, not persisted raw.
    assert frontmatter.get("artifact_type") == ANALYSIS_REPORT_ARTIFACT_TYPE
    assert frontmatter.get("schema") != "analysis-findings/v1"


def test_record_analysis_materialise_then_retry_when_invoked_from_coord_worktree(tmp_path, monkeypatch):
    """T014 / WP02: protected primary + coord topology → materialize-then-retry (exit 0).

    Previously (#1989 guard) the command refused with PROTECTED_BRANCH_REFUSED (exit 1).
    After T014 the protected-branch check is removed from the preflight and the commit
    is routed through commit_for_mission (materialise-then-retry). The report must be
    written to the PRIMARY checkout; the subsequent commit attempt is best-effort and
    may no-op in a test environment (no real coordination worktree wired to a branch).

    Invariants:
    - exit_code == 0 (no refusal on protected primary).
    - Report written to primary checkout (not refused before write).
    - commit_for_mission is called (the router was invoked).
    - The old PROTECTED_BRANCH_REFUSED error_code is NOT emitted.
    """
    from mission_runtime import CommitTarget
    from unittest.mock import patch
    from specify_cli.coordination.commit_router import CommitRouterResult

    slug = "sample-01KS"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify").mkdir()
    (repo_root / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
    primary_feature_dir = repo_root / "kitty-specs" / slug
    _make_primary(primary_feature_dir)

    def git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")
    git("branch", "-M", "main")
    git("add", ".")
    git("commit", "-m", "seed protected primary")

    coord_root = repo_root / ".worktrees" / f"{slug}-coord"
    git("worktree", "add", "-b", "analysis-work", str(coord_root))
    coord_feature_dir = coord_root / "kitty-specs" / slug

    input_file = tmp_path / "analysis.md"
    input_file.write_text(_CARRIER_READY, encoding="utf-8")

    monkeypatch.chdir(coord_root)
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis.locate_project_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis.get_main_repo_root",
        lambda _path: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis._find_feature_directory",
        lambda *_args, **_kwargs: coord_feature_dir,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis._resolve_record_analysis_placement_ref",
        lambda *_args, **_kwargs: CommitTarget(
            ref="kitty/sample-01KS",
        ),
    )
    emitted: dict[str, object] = {}
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.mission_record_analysis._emit_json",
        lambda payload: emitted.update(payload),
    )

    # Stub commit_for_mission so it reports a successful commit without needing
    # a real git environment. The stub proves the router was called (materialize-
    # then-retry path) and returns a committed result.
    # NOTE: commit_for_mission is imported locally inside the mission.py function,
    # so we patch it at the canonical module level (specify_cli.coordination.commit_router)
    # so that any `from specify_cli.coordination.commit_router import commit_for_mission`
    # inside the record_analysis body picks up the stub.
    commit_router_calls: list[dict] = []

    def _fake_commit_for_mission(**kwargs):
        commit_router_calls.append(kwargs)
        return CommitRouterResult(
            status="committed",
            placement_ref="kitty/sample-01KS",
            commit_hash="abcdef1234567",
        )

    with patch(
        "specify_cli.coordination.commit_router.commit_for_mission",
        side_effect=_fake_commit_for_mission,
    ):
        result = CliRunner().invoke(
            mission_app,
            ["record-analysis", "--mission", slug, "--input-file", str(input_file), "--json"],
        )

    # T014 invariant: no refusal — the command succeeds.
    assert result.exit_code == 0, f"Expected exit 0; got {result.exit_code}. Output: {result.output!r}; emitted: {emitted!r}"
    assert emitted.get("success") is True
    # The report must be written to the PRIMARY checkout.
    assert (primary_feature_dir / ANALYSIS_REPORT_FILENAME).exists()
    # The old refused-error must NOT appear.
    assert emitted.get("error_code") != "PROTECTED_BRANCH_REFUSED"
    # The commit router must have been called (materialize-then-retry path active).
    assert len(commit_router_calls) >= 1, "commit_for_mission was not called — materialize-then-retry path not wired"

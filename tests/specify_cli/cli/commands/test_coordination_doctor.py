"""Focused per-helper tests for ``_coordination_doctor`` (WP07, #2059).

Exercise the git-version detect/check branches, the tracked-.worktrees/ hygiene
check, the decomposed lane sparse-checkout drift sub-helpers, the finding
aggregation + emission, and the entrypoint exit contract. Also asserts the H2
invariant: the ``merge.path_is_under_worktrees`` import is function-local and no
``doctor <-> merge`` cycle exists.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import typer

from specify_cli.cli.commands import _coordination_doctor as cd

pytestmark = [pytest.mark.fast]


# --- _detect_git_version -----------------------------------------------------


def test_detect_git_version_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "git version 2.45.1\n")
    assert cd._detect_git_version() == (2, 45)


def test_detect_git_version_command_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a: Any, **_k: Any) -> str:
        raise OSError("no git")

    monkeypatch.setattr(subprocess, "check_output", _boom)
    assert cd._detect_git_version() is None


def test_detect_git_version_unparseable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "weird output")
    assert cd._detect_git_version() is None


def test_detect_git_version_non_numeric(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "git version x.y.z")
    assert cd._detect_git_version() is None


# --- _check_git_version ------------------------------------------------------


def test_check_git_version_too_old() -> None:
    out = cd._check_git_version((2, 20))
    assert out[0].severity == "error"
    assert out[0].error_code == "GIT_VERSION_TOO_OLD"


def test_check_git_version_ok() -> None:
    out = cd._check_git_version((2, 40))
    assert out[0].severity == "ok"


def test_check_git_version_undetectable_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cd, "_detect_git_version", lambda: None)
    out = cd._check_git_version()
    assert out[0].error_code == "GIT_VERSION_UNDETECTABLE"


# --- _check_tracked_worktrees_content ----------------------------------------


def test_tracked_worktrees_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "")
    out = cd._check_tracked_worktrees_content(tmp_path)
    assert out[0].severity == "ok"


def test_tracked_worktrees_flagged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        subprocess, "check_output", lambda *a, **k: ".worktrees/m-coord/file.txt\n"
    )
    out = cd._check_tracked_worktrees_content(tmp_path)
    assert out[0].severity == "error"
    assert out[0].error_code == "TRACKED_WORKTREES_CONTENT"


def test_tracked_worktrees_git_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _boom(*_a: Any, **_k: Any) -> str:
        raise OSError("not a repo")

    monkeypatch.setattr(subprocess, "check_output", _boom)
    assert cd._check_tracked_worktrees_content(tmp_path) == []


# --- _coordination_identity --------------------------------------------------


def test_coordination_identity_legacy() -> None:
    assert cd._coordination_identity({}) is None


def test_coordination_identity_incomplete() -> None:
    assert cd._coordination_identity({"coordination_branch": "x"}) == ("", "", "")


def test_coordination_identity_complete() -> None:
    meta = {"coordination_branch": "kitty/x", "mission_slug": "m", "mission_id": "01ABC"}
    assert cd._coordination_identity(meta) == ("kitty/x", "m", "01ABC")


# --- _check_coordination_worktree_health -------------------------------------


def test_coord_health_legacy_skips() -> None:
    assert cd._check_coordination_worktree_health(Path("/x"), {}) == []


def test_coord_health_incomplete_meta() -> None:
    out = cd._check_coordination_worktree_health(Path("/x"), {"coordination_branch": "y"})
    assert out[0].error_code == "COORDINATION_META_INCOMPLETE"


def test_coord_health_missing_worktree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from specify_cli import coordination as coord_mod

    monkeypatch.setattr(
        coord_mod.CoordinationWorkspace,
        "worktree_path",
        staticmethod(lambda *_a: tmp_path / "missing-coord"),
    )
    from specify_cli.lanes import branch_naming

    monkeypatch.setattr(branch_naming, "resolve_mid8", lambda *a, **k: "01ABCDEF")
    meta = {"coordination_branch": "kitty/x", "mission_slug": "m", "mission_id": "01ABCDEF"}
    out = cd._check_coordination_worktree_health(tmp_path, meta)
    assert out[0].error_code == "COORDINATION_WORKTREE_MISSING"


# --- _scan_lane_sparse_drift -------------------------------------------------


def test_scan_lane_unresolvable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cd, "_lane_sparse_file", lambda _d: None)
    finding = cd._scan_lane_sparse_drift(tmp_path, "m", {"a"})
    assert finding is not None
    assert finding.error_code == cd._LANE_DRIFT_CODE


def test_scan_lane_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cd, "_lane_sparse_file", lambda _d: tmp_path / "nope")
    finding = cd._scan_lane_sparse_drift(tmp_path, "m", {"a"})
    assert finding is not None
    assert "missing the sparse-checkout" in finding.message


def test_scan_lane_drift_detected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sparse = tmp_path / "sparse"
    sparse.write_text("pattern-a\n", encoding="utf-8")
    monkeypatch.setattr(cd, "_lane_sparse_file", lambda _d: sparse)
    finding = cd._scan_lane_sparse_drift(tmp_path, "m", {"pattern-a", "pattern-b"})
    assert finding is not None
    assert finding.extra["missing_patterns"] == ["pattern-b"]


def test_scan_lane_healthy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sparse = tmp_path / "sparse"
    sparse.write_text("pattern-a\npattern-b\n", encoding="utf-8")
    monkeypatch.setattr(cd, "_lane_sparse_file", lambda _d: sparse)
    assert cd._scan_lane_sparse_drift(tmp_path, "m", {"pattern-a"}) is None


def test_check_lane_drift_legacy_skips() -> None:
    assert cd._check_lane_sparse_checkout_drift(Path("/x"), {}) == []


# --- emission + entrypoint ---------------------------------------------------


def test_emit_findings_json() -> None:
    findings = [cd.DoctorFinding(severity="ok", message="fine")]
    cd._emit_coordination_findings(findings, json_output=True)


def test_emit_findings_human() -> None:
    findings = [
        cd.DoctorFinding(severity="error", message="bad", next_step="fix it"),
        cd.DoctorFinding(severity="warning", message="meh"),
    ]
    cd._emit_coordination_findings(findings, json_output=False)


def test_run_coordination_health_not_in_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cd, "locate_project_root", lambda: None)
    with pytest.raises(typer.Exit) as exc:
        cd.run_coordination_health(json_output=False)
    assert exc.value.exit_code == 1


def test_run_coordination_health_error_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cd, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(
        cd,
        "_collect_coordination_findings",
        lambda _r: [cd.DoctorFinding(severity="error", message="boom")],
    )
    with pytest.raises(typer.Exit) as exc:
        cd.run_coordination_health(json_output=True)
    assert exc.value.exit_code == 1


def test_run_coordination_health_clean_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cd, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(
        cd,
        "_collect_coordination_findings",
        lambda _r: [cd.DoctorFinding(severity="ok", message="fine")],
    )
    with pytest.raises(typer.Exit) as exc:
        cd.run_coordination_health(json_output=False)
    assert exc.value.exit_code == 0


def test_collect_findings_no_specs_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cd, "_check_git_version", lambda: [])
    monkeypatch.setattr(cd, "_check_tracked_worktrees_content", lambda _r: [])
    # No kitty-specs dir → only the (stubbed-empty) repo-level checks.
    assert cd._collect_coordination_findings(tmp_path) == []


# --- coord worktree head/dirty helpers ---------------------------------------


def test_coord_head_finding_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "refs/heads/other\n")
    finding = cd._coord_worktree_head_finding(tmp_path, "kitty/x", "m")
    assert finding is not None
    assert finding.error_code == "COORDINATION_WORKTREE_BRANCH_MISMATCH"


def test_coord_head_finding_match(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "refs/heads/kitty/x\n")
    assert cd._coord_worktree_head_finding(tmp_path, "kitty/x", "m") is None


def test_coord_head_finding_detached(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _boom(*_a: Any, **_k: Any) -> str:
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(subprocess, "check_output", _boom)
    finding = cd._coord_worktree_head_finding(tmp_path, "kitty/x", "m")
    assert finding is not None


def test_coord_dirty_finding(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: " M file.py\n")
    finding = cd._coord_worktree_dirty_finding(tmp_path)
    assert finding is not None
    assert finding.error_code == "COORDINATION_WORKTREE_DIRTY"


def test_coord_dirty_finding_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "")
    assert cd._coord_worktree_dirty_finding(tmp_path) is None


def test_coord_health_healthy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli import coordination as coord_mod
    from specify_cli.lanes import branch_naming

    worktree = tmp_path / "coord"
    worktree.mkdir()
    monkeypatch.setattr(
        coord_mod.CoordinationWorkspace, "worktree_path", staticmethod(lambda *_a: worktree)
    )
    monkeypatch.setattr(branch_naming, "resolve_mid8", lambda *a, **k: "01ABCDEF")
    monkeypatch.setattr(cd, "_coord_worktree_head_finding", lambda *a: None)
    monkeypatch.setattr(cd, "_coord_worktree_dirty_finding", lambda *a: None)
    meta = {"coordination_branch": "kitty/x", "mission_slug": "m", "mission_id": "01ABCDEF"}
    out = cd._check_coordination_worktree_health(tmp_path, meta)
    assert out[0].severity == "ok"


# --- _lane_sparse_file -------------------------------------------------------


def test_lane_sparse_file_unresolvable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _boom(*_a: Any, **_k: Any) -> str:
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(subprocess, "check_output", _boom)
    assert cd._lane_sparse_file(tmp_path) is None


def test_lane_sparse_file_relative(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: ".git/info/sparse-checkout\n")
    resolved = cd._lane_sparse_file(tmp_path)
    assert resolved == tmp_path / ".git/info/sparse-checkout"


# --- _check_lane_sparse_checkout_drift full loop -----------------------------


def test_check_lane_drift_no_worktrees_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from specify_cli import coordination as coord_mod
    from specify_cli.lanes import branch_naming

    monkeypatch.setattr(branch_naming, "resolve_mid8", lambda *a, **k: "01ABCDEF")
    monkeypatch.setattr(coord_mod, "lane_sparse_checkout_patterns", lambda *a: ["p"])
    meta = {"coordination_branch": "kitty/x", "mission_slug": "m", "mission_id": "01ABCDEF"}
    # No .worktrees dir under tmp_path → returns [].
    assert cd._check_lane_sparse_checkout_drift(tmp_path, meta) == []


def test_check_lane_drift_all_clean(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from specify_cli import coordination as coord_mod
    from specify_cli.lanes import branch_naming

    wt = tmp_path / ".worktrees" / "m-lane-a"
    wt.mkdir(parents=True)
    monkeypatch.setattr(branch_naming, "resolve_mid8", lambda *a, **k: "01ABCDEF")
    monkeypatch.setattr(coord_mod, "lane_sparse_checkout_patterns", lambda *a: ["p"])
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: str(wt.resolve()) + "\n")
    monkeypatch.setattr(cd, "_scan_lane_sparse_drift", lambda *a: None)
    meta = {"coordination_branch": "kitty/x", "mission_slug": "m", "mission_id": "01ABCDEF"}
    out = cd._check_lane_sparse_checkout_drift(tmp_path, meta)
    assert out[0].severity == "ok"


# --- _collect_coordination_findings mission loop -----------------------------


def test_collect_findings_iterates_missions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import json as _json

    specs = tmp_path / "kitty-specs"
    mission = specs / "083-a"
    mission.mkdir(parents=True)
    (mission / "meta.json").write_text(_json.dumps({"slug": "083-a"}), encoding="utf-8")
    monkeypatch.setattr(cd, "_check_git_version", lambda: [])
    monkeypatch.setattr(cd, "_check_tracked_worktrees_content", lambda _r: [])
    monkeypatch.setattr(
        cd, "_check_coordination_worktree_health",
        lambda _r, _m: [cd.DoctorFinding(severity="ok", message="coord")],
    )
    monkeypatch.setattr(cd, "_check_lane_sparse_checkout_drift", lambda _r, _m: [])
    out = cd._collect_coordination_findings(tmp_path)
    assert any(f.message == "coord" for f in out)


# --- H2 / cycle invariants ---------------------------------------------------


def test_merge_import_is_function_local() -> None:
    import ast

    source = Path(cd.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    # No module-level (depth-1) import of the merge module.
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "specify_cli.cli.commands.merge":
            raise AssertionError("merge import must not be module-level (H2)")
    # It must appear somewhere nested (inside a function).
    assert "from specify_cli.cli.commands.merge import path_is_under_worktrees" in source


def test_no_doctor_merge_import_cycle() -> None:
    import importlib

    importlib.import_module("specify_cli.cli.commands.doctor")
    importlib.import_module("specify_cli.cli.commands.merge")

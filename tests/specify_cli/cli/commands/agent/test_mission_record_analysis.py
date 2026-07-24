"""Direct unit tests for the record-analysis seam (#2056 WP04, Seam A).

Exercises the relocated helpers in
``specify_cli.cli.commands.agent.mission_record_analysis`` directly: the
dirty-tree write preflight (clean / dirty / coord-residue-drop branches), the
placement-ref resolver's conservative None-on-failure contract, and the
``_git_dirty_paths`` git helper. The end-to-end command behavior remains pinned
by the existing ``test_record_analysis_coord_worktree.py`` and the WP01 golden
harness; these add the missing focused branch coverage.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from mission_runtime import ActionContextError, CommitTarget, MissionTopology
from specify_cli.cli.commands.agent import mission_record_analysis as seam
from specify_cli.cli.commands.agent.mission import app as mission_app

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# _git_dirty_paths
# ---------------------------------------------------------------------------


def test_git_dirty_paths_empty_outside_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: False)
    assert seam._git_dirty_paths(tmp_path) == []


def test_git_dirty_paths_parses_porcelain(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: True)

    class _Result:
        returncode = 0
        stdout = " M src/a.py\n?? new.txt\n\n"
        stderr = ""

    monkeypatch.setattr(seam.subprocess, "run", lambda *a, **k: _Result())
    assert seam._git_dirty_paths(tmp_path) == ["src/a.py", "new.txt"]


def test_git_dirty_paths_raises_on_git_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: True)

    class _Result:
        returncode = 1
        stdout = ""
        stderr = "fatal: boom"

    monkeypatch.setattr(seam.subprocess, "run", lambda *a, **k: _Result())
    with pytest.raises(RuntimeError, match="boom"):
        seam._git_dirty_paths(tmp_path)


# ---------------------------------------------------------------------------
# _resolve_record_analysis_placement_ref (conservative None on failure)
# ---------------------------------------------------------------------------


def test_placement_ref_none_on_resolution_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A resolution failure degrades to None (conservative; never breaks the lifecycle)."""
    import mission_runtime
    from mission_runtime import ActionContextError

    def _boom(*_a: object, **_k: object) -> object:
        raise ActionContextError("X", "no context")

    # The helper lazily imports placement_seam from mission_runtime and calls
    # write_target(ANALYSIS_REPORT); a raised ActionContextError must degrade to
    # None (unchanged Optional contract).
    monkeypatch.setattr(mission_runtime, "placement_seam", _boom, raising=False)
    assert seam._resolve_record_analysis_placement_ref(tmp_path, tmp_path / "001-demo") is None


# ---------------------------------------------------------------------------
# _enforce_analysis_report_write_preflight
# ---------------------------------------------------------------------------


def test_preflight_noop_outside_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: False)
    # Must return without raising even with a dirty stub (not consulted).
    seam._enforce_analysis_report_write_preflight(tmp_path, json_output=True)


def test_preflight_clean_tree_passes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(seam, "_git_dirty_paths", lambda _root: [])
    seam._enforce_analysis_report_write_preflight(tmp_path, json_output=True)


def test_preflight_dirty_tree_gates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(seam, "_git_dirty_paths", lambda _root: ["src/dirty.py"])
    with pytest.raises(typer.Exit):
        seam._enforce_analysis_report_write_preflight(tmp_path, json_output=True)


def test_preflight_coord_drops_residue(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(seam, "_git_dirty_paths", lambda _root: ["kitty-specs/001-demo/spec.md"])
    monkeypatch.setattr(
        seam, "is_coord_residue_churn", lambda _p, *, mission_slug=None: True
    )
    monkeypatch.setattr(seam, "resolve_topology", lambda _r, _s: MissionTopology.COORD)
    # Residue dropped → empty dirty set → no gate.
    seam._enforce_analysis_report_write_preflight(
        tmp_path,
        json_output=True,
        placement_ref=CommitTarget(ref="kitty/mission-001-demo-AAAA1111"),
        mission_slug="001-demo",
    )


def test_preflight_non_coord_keeps_residue_and_gates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(seam, "_git_dirty_paths", lambda _root: ["kitty-specs/001-demo/spec.md"])
    monkeypatch.setattr(
        seam, "is_coord_residue_churn", lambda _p, *, mission_slug=None: True
    )
    monkeypatch.setattr(seam, "resolve_topology", lambda _r, _s: MissionTopology.SINGLE_BRANCH)
    with pytest.raises(typer.Exit):
        seam._enforce_analysis_report_write_preflight(
            tmp_path,
            json_output=True,
            placement_ref=CommitTarget(ref="main"),
            mission_slug="001-demo",
        )


def test_preflight_no_slug_skips_residue_filter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without a mission_slug the residue filter is skipped → full dirty set gates."""
    monkeypatch.setattr(seam, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(seam, "_git_dirty_paths", lambda _root: ["kitty-specs/001-demo/spec.md"])
    with pytest.raises(typer.Exit):
        seam._enforce_analysis_report_write_preflight(
            tmp_path,
            json_output=True,
            placement_ref=CommitTarget(ref="kitty/mission-001-demo-AAAA1111"),
            mission_slug=None,
        )


# ---------------------------------------------------------------------------
# record_analysis command — error / edge branches via CliRunner
# ---------------------------------------------------------------------------


_RUNNER = CliRunner()


def test_command_project_root_not_found_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seam, "locate_project_root", lambda: None)
    result = _RUNNER.invoke(
        mission_app, ["record-analysis", "--json"], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert seam.PROJECT_ROOT_NOT_FOUND in result.stdout


def test_command_project_root_not_found_human(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seam, "locate_project_root", lambda: None)
    result = _RUNNER.invoke(mission_app, ["record-analysis"], catch_exceptions=False)
    assert result.exit_code == 1
    assert seam.PROJECT_ROOT_NOT_FOUND in result.stdout


def test_command_feature_detection_error_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(seam, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(seam, "get_main_repo_root", lambda _r: tmp_path)

    def _raise(*_a: object, **_k: object) -> Path:
        raise ActionContextError("FEATURE_CONTEXT_UNRESOLVED", "no mission")

    monkeypatch.setattr(seam, "_find_feature_directory", _raise)
    result = _RUNNER.invoke(
        mission_app, ["record-analysis", "--json", "--mission", "nope"], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "FEATURE_CONTEXT_UNRESOLVED" in result.stdout


def test_command_empty_body_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    monkeypatch.setattr(seam, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(seam, "get_main_repo_root", lambda _r: tmp_path)
    monkeypatch.setattr(seam, "_find_feature_directory", lambda *_a, **_k: feature_dir)
    # WP03 / D11: placement must resolve for the command to reach the empty-body
    # check at all -- a ``None`` placement now fails closed BEFORE this branch
    # (see test_record_analysis_placement.py). This test is about the empty-body
    # validation, so it supplies a resolved placement to reach that branch.
    monkeypatch.setattr(
        seam,
        "_resolve_record_analysis_placement_ref",
        lambda *_a, **_k: CommitTarget(ref="main"),
    )
    monkeypatch.setattr(seam, "_enforce_analysis_report_write_preflight", lambda *_a, **_k: None)
    # Empty stdin → empty body.
    result = _RUNNER.invoke(
        mission_app, ["record-analysis", "--json"], input="   \n", catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "empty" in result.stdout.lower()


def test_command_unexpected_exception_human(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The top-level except handler renders a human error and exits 1."""
    monkeypatch.setattr(seam, "locate_project_root", lambda: tmp_path)

    def _boom(_r: object) -> Path:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(seam, "get_main_repo_root", _boom)
    result = _RUNNER.invoke(mission_app, ["record-analysis"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "kaboom" in result.stdout

"""Seam test for ``specify_cli.merge.git_probes`` (mission #2057, WP03).

Covers the relocated low-level git primitives (porcelain classification,
linear-history detection, worktree-path predicate, branch/tree probes,
post-merge refresh) and proves the command shim re-exports the same objects so
``doctor.py`` / ``agent/mission.py`` and the public ``path_is_under_worktrees``
importer need zero edits (FR-006, C-006). Also enforces one-way imports (INV-2).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.cli.commands import merge as shim
from specify_cli.merge import git_probes

# The subprocess-backed probes below spawn real ``git`` on a tmp repo, so this
# file is an integration test that requires a git repo (Rule 1) and must NOT
# carry ``fast`` (Rule 2 — subprocess work would poison the inner-loop profile).
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# --- Re-export / one-way-import contract ------------------------------------

RELOCATED_NAMES = [
    "_lane_already_integrated",
    "_branch_trees_equal",
    "path_is_under_worktrees",
    "_raw_porcelain_status",
    "_classify_porcelain_lines",
    "_is_linear_history_rejection",
    "_emit_remediation_hint",
    "_refresh_primary_checkout_after_merge",
    "_paths_have_status_changes",
    "_is_git_repo",
    "_has_branch_ref",
]


@pytest.mark.parametrize("name", RELOCATED_NAMES)
def test_shim_re_exports_the_same_object(name: str) -> None:
    assert getattr(shim, name) is getattr(git_probes, name)


def test_git_probes_does_not_import_the_command_shim() -> None:
    """One-way import (C-006/INV-2): the seam never imports the merge command shim.

    Importing shared helpers (``cli.helpers.console``) is allowed — the rule
    forbids reaching back into ``cli.commands.merge`` (the shim), which would
    create a cycle.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(git_probes))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    assert "specify_cli.cli.commands.merge" not in modules, sorted(modules)
    assert not any(
        m.startswith("specify_cli.cli.commands.merge") for m in modules
    ), sorted(modules)


# --- path_is_under_worktrees -----------------------------------------------


def test_path_is_under_worktrees_true_and_false() -> None:
    assert git_probes.path_is_under_worktrees(Path(".worktrees/mission-lane-a/x"))
    assert git_probes.path_is_under_worktrees(Path("repo/.worktrees/m/file.py"))
    assert not git_probes.path_is_under_worktrees(Path("src/specify_cli/x.py"))


# --- _is_linear_history_rejection ------------------------------------------


@pytest.mark.parametrize(
    "stderr",
    [
        "remote: error: GH006 Protected branch update failed",
        "Updates were rejected because the remote contains work (non-fast-forward)",
        "branch requires linear history",
        "merge commits are not allowed",
        "fast-forward only",
    ],
)
def test_linear_history_rejection_detects_locked_tokens(stderr: str) -> None:
    assert git_probes._is_linear_history_rejection(stderr)


def test_linear_history_rejection_is_fail_open() -> None:
    assert not git_probes._is_linear_history_rejection("some unrelated push error")
    # Case-insensitive match.
    assert git_probes._is_linear_history_rejection("LINEAR HISTORY required")


# --- _classify_porcelain_lines ---------------------------------------------


def test_classify_porcelain_lines_buckets_correctly() -> None:
    lines = [
        " M src/changed.py",     # tracked modification -> offending
        "?? untracked.txt",      # untracked -> skipped, counted
        "M  kitty-specs/x.md",   # staged, but expected -> dropped
        "",                      # blank -> ignored
        "bad",                   # malformed shape -> ignored
        " D removed.py",         # deletion -> offending
    ]
    offending, skipped = git_probes._classify_porcelain_lines(
        lines, expected_paths={"kitty-specs/x.md"}
    )
    assert offending == [" M src/changed.py", " D removed.py"]
    assert skipped == 1


def test_classify_porcelain_lines_residue_predicate_drops_residue() -> None:
    lines = [" M kitty-specs/m/status.json", " M src/real.py"]
    offending, skipped = git_probes._classify_porcelain_lines(
        lines,
        expected_paths=set(),
        residue_predicate=lambda p: p.startswith("kitty-specs/"),
    )
    assert offending == [" M src/real.py"]
    assert skipped == 0


# --- _emit_remediation_hint ------------------------------------------------


def test_emit_remediation_hint_prints_squash_guidance() -> None:
    captured: list[str] = []

    class _FakeConsole:
        def print(self, msg: str) -> None:
            captured.append(msg)

    git_probes._emit_remediation_hint(_FakeConsole())  # type: ignore[arg-type]
    assert any("--strategy squash" in line for line in captured)
    assert any("linear-history" in line for line in captured)


# --- run_command-backed probes (mocked) ------------------------------------


def test_lane_already_integrated_reads_rev_list_count() -> None:
    with patch.object(git_probes, "run_command", return_value=(0, "0", "")):
        assert git_probes._lane_already_integrated(Path("/r"), "lane", "mission")
    with patch.object(git_probes, "run_command", return_value=(0, "3", "")):
        assert not git_probes._lane_already_integrated(Path("/r"), "lane", "mission")
    # git error -> conservative False (run the merge).
    with patch.object(git_probes, "run_command", return_value=(128, "", "err")):
        assert not git_probes._lane_already_integrated(Path("/r"), "lane", "mission")


def test_branch_trees_equal_uses_diff_quiet() -> None:
    with patch.object(git_probes, "run_command", return_value=(0, "", "")):
        assert git_probes._branch_trees_equal(Path("/r"), "a", "b")
    with patch.object(git_probes, "run_command", return_value=(1, "", "")):
        assert not git_probes._branch_trees_equal(Path("/r"), "a", "b")


def test_has_branch_ref_true_false() -> None:
    with patch.object(git_probes, "run_command", return_value=(0, "sha", "")):
        assert git_probes._has_branch_ref(Path("/r"), "main")
    with patch.object(git_probes, "run_command", return_value=(128, "", "bad")):
        assert not git_probes._has_branch_ref(Path("/r"), "nope")


def test_paths_have_status_changes_detects_dirty_and_clean(tmp_path: Path) -> None:
    with patch.object(git_probes, "run_command", return_value=(0, " M a.py\n", "")):
        assert git_probes._paths_have_status_changes(tmp_path, [tmp_path / "a.py"])
    with patch.object(git_probes, "run_command", return_value=(0, "", "")):
        assert not git_probes._paths_have_status_changes(tmp_path, [tmp_path / "a.py"])
    # git failure -> conservative True.
    with patch.object(git_probes, "run_command", return_value=(1, "", "err")):
        assert git_probes._paths_have_status_changes(tmp_path, [tmp_path / "a.py"])


def test_refresh_primary_checkout_warns_on_reset_failure() -> None:
    printed: list[str] = []
    with (
        patch.object(git_probes, "run_command", return_value=(1, "", "reset boom")),
        patch("specify_cli.merge.git_probes.console.print", side_effect=lambda m: printed.append(m)),
    ):
        git_probes._refresh_primary_checkout_after_merge(Path("/r"))
    assert any("refresh failed" in line for line in printed)


def test_refresh_primary_checkout_reset_then_refresh() -> None:
    calls: list[list[str]] = []

    def _fake(cmd: list[str], **_kw: object) -> tuple[int, str, str]:
        calls.append(cmd)
        return (0, "", "")

    with patch.object(git_probes, "run_command", side_effect=_fake):
        git_probes._refresh_primary_checkout_after_merge(Path("/r"))
    assert calls[0][:3] == ["git", "reset", "--hard"]
    assert calls[1][:2] == ["git", "update-index"]


# --- subprocess-backed probes (real git on a tmp repo) ----------------------


def _init_repo(path: Path) -> None:
    import subprocess

    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)


def test_is_git_repo_true_inside_false_outside(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    assert git_probes._is_git_repo(repo)
    outside = tmp_path / "plain"
    outside.mkdir()
    assert not git_probes._is_git_repo(outside)


def test_raw_porcelain_status_preserves_leading_column(tmp_path: Path) -> None:
    import subprocess

    repo = tmp_path / "repo"
    _init_repo(repo)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    # Modify the tracked file without staging -> porcelain " M a.txt".
    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    rc, out = git_probes._raw_porcelain_status(repo)
    assert rc == 0
    assert out.startswith(" M a.txt"), repr(out)

"""Integration test: remediation across primary + multiple lane worktrees.

This is the canonical "realistic spec-kitty layout" case: a primary repo with
``core.sparseCheckout=true`` plus two lane worktrees under ``.worktrees/`` that
each carry their own worktree-scoped sparse flag. Validates that remediation
clears sparse state in all three targets, rehydrates any hidden files, and
leaves every target's ``git status --porcelain`` empty.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from specify_cli.git.sparse_checkout import scan_repo
from specify_cli.git.sparse_checkout_remediation import (
    STEP_VERIFY_CLEAN,
    remediate,
)


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


def _seed_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "test@example.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "Test User"])
    (repo / "README.md").write_text("# Hello\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (repo / "src" / "b.py").write_text("print('b')\n", encoding="utf-8")
    _run(["git", "-C", str(repo), "add", "-A"])
    _run(["git", "-C", str(repo), "commit", "-m", "seed"])
    # Exclude .worktrees/ so the primary never reports it as untracked.
    excl = repo / ".git" / "info" / "exclude"
    excl.parent.mkdir(parents=True, exist_ok=True)
    excl.write_text(".worktrees/\n", encoding="utf-8")


def test_remediation_across_primary_and_two_worktrees(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _seed_repo(repo)

    # Create worktrees first — before any sparse state is live — so their
    # initial checkout runs on a normal (non-sparse) config.
    wt_a = repo / ".worktrees" / "feature-lane-a"
    wt_b = repo / ".worktrees" / "feature-lane-b"
    _run(["git", "-C", str(repo), "worktree", "add", "-b", "feature/a", str(wt_a)])
    _run(["git", "-C", str(repo), "worktree", "add", "-b", "feature/b", str(wt_b)])

    # Enable sparse on primary AND apply a restrictive pattern that hides
    # src/. Then repeat for each worktree using worktree-scoped config so each
    # has its own per-worktree sparse flag.
    _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])
    pf = repo / ".git" / "info" / "sparse-checkout"
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text("README.md\n", encoding="utf-8")
    _run(["git", "-C", str(repo), "read-tree", "-mu", "HEAD"])

    _run(["git", "-C", str(repo), "config", "extensions.worktreeConfig", "true"])
    for wt in (wt_a, wt_b):
        _run(
            [
                "git",
                "-C",
                str(wt),
                "config",
                "--worktree",
                "core.sparseCheckout",
                "true",
            ],
        )
        # Write a pattern file into the per-worktree sparse-checkout info dir.
        rev_parse = _run(["git", "-C", str(wt), "rev-parse", "--git-dir"])
        git_dir = Path(rev_parse.stdout.strip())
        if not git_dir.is_absolute():
            git_dir = (wt / git_dir).resolve()
        wt_pf = git_dir / "info" / "sparse-checkout"
        wt_pf.parent.mkdir(parents=True, exist_ok=True)
        wt_pf.write_text("README.md\n", encoding="utf-8")
        # Apply via read-tree so the filter actually hides src/.
        _run(["git", "-C", str(wt), "read-tree", "-mu", "HEAD"])

    # Pre-conditions: all three targets have sparse active, src/ is hidden in
    # primary and both worktrees.
    assert not (repo / "src" / "a.py").exists()
    assert not (wt_a / "src" / "a.py").exists()
    assert not (wt_b / "src" / "a.py").exists()

    report = scan_repo(repo)
    assert report.primary.is_active is True
    assert len(report.worktrees) == 2
    assert all(w.is_active for w in report.worktrees)

    result = remediate(report, interactive=False)

    assert result.overall_success is True, result
    assert result.primary_result.success is True
    assert len(result.worktree_results) == 2
    for wr in result.worktree_results:
        assert wr.success is True, wr
        assert wr.steps_completed[-1] == STEP_VERIFY_CLEAN

    # Post-conditions: hidden files are back, no porcelain changes anywhere,
    # no sparse state detected.
    for target in (repo, wt_a, wt_b):
        assert (target / "src" / "a.py").read_text(encoding="utf-8") == "print('a')\n"
        porcelain = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert porcelain.stdout.strip() == "", f"{target} still dirty after remediation: {porcelain.stdout!r}"

    final_report = scan_repo(repo)
    assert final_report.any_active is False

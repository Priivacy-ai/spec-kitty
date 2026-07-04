"""Regression: upgrade auto-commits churn in worktrees too, not just main (#2385).

`spec-kitty upgrade` applies migrations across sibling worktrees but historically
committed only the main checkout, leaving worktrees dirty — which then blocked
`spec-kitty merge` (the #1826/NFR-002 guard refuses to advance a branch whose
worktree has uncommitted changes). These tests pin the fix: upgrade commits each
worktree's new churn on its own branch, while a per-worktree baseline protects
any pre-existing uncommitted work.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.upgrade import (
    _auto_commit_worktree_upgrade_changes,
    _capture_worktree_baselines,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "README.md").write_text("# repo\n", encoding="utf-8")
    (root / ".kittify").mkdir()
    (root / ".kittify" / "metadata.yaml").write_text("version: 3.2.1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")


def _add_worktree(root: Path, name: str, branch: str) -> Path:
    wt = root / ".worktrees" / name
    _git(root, "worktree", "add", "-q", "-b", branch, str(wt))
    return wt


def _dirty(wt: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(wt), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def test_worktree_upgrade_churn_is_committed_clean(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    wt = _add_worktree(root, "m-lane-a", "kitty/mission-m-lane-a")

    # Baseline captured before any upgrade change (worktree is clean).
    baselines = _capture_worktree_baselines(root)
    assert wt in baselines
    assert baselines[wt] == set()

    # Simulate upgrade migration churn in the worktree.
    (wt / ".kittify" / "metadata.yaml").write_text("version: 3.2.4\n", encoding="utf-8")
    assert _dirty(wt), "precondition: worktree is dirty after the churn"

    warnings = _auto_commit_worktree_upgrade_changes(baselines, "3.2.1", "3.2.4")

    assert warnings == [], warnings
    assert _dirty(wt) == [], "worktree must be clean (churn committed) after upgrade"
    # The commit landed on the worktree's own branch.
    subject = subprocess.run(
        ["git", "-C", str(wt), "log", "-1", "--pretty=%s"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert "spec-kitty upgrade" in subject


def test_preexisting_uncommitted_work_in_worktree_is_not_committed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    wt = _add_worktree(root, "m-lane-b", "kitty/mission-m-lane-b")

    # Pre-existing uncommitted work exists BEFORE the upgrade baseline.
    (wt / ".kittify" / "wip.json").write_text('{"wip": true}\n', encoding="utf-8")
    baselines = _capture_worktree_baselines(root)
    assert ".kittify/wip.json" in baselines[wt]  # captured as pre-existing

    # Now the upgrade introduces its own churn.
    (wt / ".kittify" / "metadata.yaml").write_text("version: 3.2.4\n", encoding="utf-8")

    _auto_commit_worktree_upgrade_changes(baselines, "3.2.1", "3.2.4")

    # metadata churn committed; the pre-existing WIP file remains uncommitted.
    remaining = _dirty(wt)
    assert any("wip.json" in ln for ln in remaining), remaining
    assert not any("metadata.yaml" in ln for ln in remaining), remaining

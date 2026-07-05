"""Upgrade-worktree coherence: the runner commits each checkout it touches (#2392).

`spec-kitty upgrade` applies migrations across sibling worktrees but
historically committed only the main checkout, leaving worktrees dirty — which
then blocked `spec-kitty merge` (the #1826/NFR-002 guard refuses to advance a
branch whose worktree has uncommitted changes). These tests pin the canonical
seam fix (epic #2392):

* #2385 — ``MigrationRunner._upgrade_worktrees`` auto-commits each worktree's
  new churn on that worktree's own branch, with a per-worktree baseline
  protecting pre-existing uncommitted work.
* #1873 — freshly synthesized worktree metadata is persisted (and committed)
  even when the detected version already equals the target.
* Invariant (Slice C): after an upgrade run, every touched checkout has no
  porcelain diff beyond what was already dirty before the run.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.upgrade.runner import MigrationRunner

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_METADATA_YAML = (
    "spec_kitty:\n"
    "  version: '{version}'\n"
    "  initialized_at: '2026-01-01T00:00:00'\n"
    "environment:\n"
    "  python_version: '3.12'\n"
    "  platform: linux\n"
    "  platform_version: ''\n"
    "migrations:\n"
    "  applied: []\n"
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def _git_out(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _init_repo(root: Path, version: str = "3.2.1") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "README.md").write_text("# repo\n", encoding="utf-8")
    # Real spec-kitty projects gitignore the execution worktrees.
    (root / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
    (root / ".kittify").mkdir()
    (root / ".kittify" / "metadata.yaml").write_text(
        _METADATA_YAML.format(version=version), encoding="utf-8"
    )
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


def test_worktree_upgrade_churn_is_committed_on_its_own_branch(tmp_path: Path) -> None:
    """#2385: the runner commits worktree upgrade churn; the tree ends clean."""
    root = tmp_path / "repo"
    _init_repo(root)
    wt = _add_worktree(root, "m-lane-a", "kitty/mission-m-lane-a")

    result = MigrationRunner(root)._upgrade_worktrees(
        "3.2.9", [], dry_run=False, auto_commit=True
    )

    assert result["errors"] == []
    assert not any("auto-commit" in w.lower() for w in result["warnings"]), result["warnings"]
    assert _dirty(wt) == [], "worktree must be clean (churn committed) after upgrade"
    # The commit landed on the worktree's own branch.
    assert _git_out(wt, "branch", "--show-current") == "kitty/mission-m-lane-a"
    assert "spec-kitty upgrade" in _git_out(wt, "log", "-1", "--pretty=%s")
    # And main's branch did NOT receive the worktree commit.
    assert "spec-kitty upgrade" not in _git_out(root, "log", "-1", "--pretty=%s")


def test_preexisting_uncommitted_work_in_worktree_is_not_committed(tmp_path: Path) -> None:
    """#2385 baseline: in-flight WP edits are never swept into the upgrade commit."""
    root = tmp_path / "repo"
    _init_repo(root)
    wt = _add_worktree(root, "m-lane-b", "kitty/mission-m-lane-b")

    # Pre-existing uncommitted work exists BEFORE the upgrade runs.
    (wt / "kitty-specs").mkdir()
    (wt / "kitty-specs" / "wip.md").write_text("wip\n", encoding="utf-8")
    (wt / "README.md").write_text("# repo (edited in lane)\n", encoding="utf-8")

    MigrationRunner(root)._upgrade_worktrees("3.2.9", [], dry_run=False, auto_commit=True)

    remaining = _dirty(wt)
    # Untracked dirs are reported as a single `?? kitty-specs/` entry.
    assert any("kitty-specs" in ln for ln in remaining), remaining
    assert any("README.md" in ln for ln in remaining), remaining
    assert not any("metadata.yaml" in ln for ln in remaining), remaining


def test_synthesized_worktree_metadata_is_saved_when_version_matches_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#1873: metadata synthesized from None must be persisted (and committed)
    even when the detected version already equals the target."""
    root = tmp_path / "repo"
    _init_repo(root)
    wt = _add_worktree(root, "m-lane-c", "kitty/mission-m-lane-c")

    # The worktree has a .kittify dir but no metadata.yaml (the self-healing
    # scenario from #1857), and its detected version already equals the target.
    (wt / ".kittify" / "metadata.yaml").unlink()
    _git(wt, "commit", "-q", "-am", "drop worktree metadata")

    class _StubDetector:
        def __init__(self, _path: Path) -> None:
            pass

        def detect_version(self) -> str:
            return "3.2.9"

    monkeypatch.setattr("specify_cli.upgrade.runner.VersionDetector", _StubDetector)

    MigrationRunner(root)._upgrade_worktrees("3.2.9", [], dry_run=False, auto_commit=True)

    assert (wt / ".kittify" / "metadata.yaml").exists(), (
        "synthesized worktree metadata must be saved to disk (#1873)"
    )
    assert _dirty(wt) == [], "the healed metadata must also be committed"


def test_dry_run_writes_and_commits_nothing_in_worktrees(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    wt = _add_worktree(root, "m-lane-d", "kitty/mission-m-lane-d")
    head_before = _git_out(wt, "rev-parse", "HEAD")

    MigrationRunner(root)._upgrade_worktrees("3.2.9", [], dry_run=True, auto_commit=True)

    assert _dirty(wt) == []
    assert _git_out(wt, "rev-parse", "HEAD") == head_before


def test_upgrade_invariant_every_touched_checkout_ends_clean(tmp_path: Path) -> None:
    """Slice C invariant (#2392): after `runner.upgrade(..., auto_commit=True)`,
    no checkout the run touched has porcelain dirt beyond what pre-existed."""
    root = tmp_path / "repo"
    _init_repo(root)
    wt = _add_worktree(root, "m-lane-e", "kitty/mission-m-lane-e")

    # Pre-existing dirt in the lane worktree (must survive uncommitted).
    (wt / "kitty-specs").mkdir()
    (wt / "kitty-specs" / "wip.md").write_text("wip\n", encoding="utf-8")

    result = MigrationRunner(root).upgrade("3.2.9", dry_run=False, auto_commit=True)
    assert result.success, result.errors

    # The worktree's only remaining dirt is the pre-existing WIP file
    # (reported by porcelain as its untracked directory).
    assert [ln for ln in _dirty(wt) if "kitty-specs" not in ln] == []
    # The runner does not commit the main checkout (that is the CLI's half of
    # the seam) — but everything it wrote there is upgrade churn the CLI's
    # commit_touched_checkout would pick up (.kittify/* and .gitignore).
    main_dirt = _dirty(root)
    assert all(".kittify/" in ln or ".gitignore" in ln for ln in main_dirt), main_dirt

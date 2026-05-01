"""Integration test: remediation refuses on any dirty target (FR-005).

The all-or-nothing contract says: if ANY target in the scan report has
uncommitted changes at the moment ``remediate()`` is called, NO target is
touched. Every result in the returned report must carry
``dirty_before_remediation=True``, and the on-disk sparse-checkout state must
be identical before and after the call.

Two scenarios are covered:

1. Primary dirty, worktree clean — primary's uncommitted file survives; no
   git config or pattern files are mutated anywhere.
2. Primary clean, worktree dirty — same all-or-nothing outcome.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from specify_cli.git.sparse_checkout import scan_repo
from specify_cli.git.sparse_checkout_remediation import remediate


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


def _seed_sparse_primary_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "test@example.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "Test User"])
    (repo / "README.md").write_text("# Hello\n", encoding="utf-8")
    _run(["git", "-C", str(repo), "add", "-A"])
    _run(["git", "-C", str(repo), "commit", "-m", "seed"])

    # Exclude .worktrees/ from untracked listings.
    excl = repo / ".git" / "info" / "exclude"
    excl.write_text(".worktrees/\n", encoding="utf-8")

    wt = repo / ".worktrees" / "lane-a"
    _run(["git", "-C", str(repo), "worktree", "add", "-b", "feature/a", str(wt)])

    # Enable sparse on the primary (after worktree creation, so the worktree
    # starts out non-sparse) and write a pattern file.
    _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])
    pf = repo / ".git" / "info" / "sparse-checkout"
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text("README.md\n", encoding="utf-8")

    # Enable sparse on the worktree too via worktree-scoped config, so it is
    # also an active target in the scan report.
    _run(["git", "-C", str(repo), "config", "extensions.worktreeConfig", "true"])
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
    return repo, wt


def _snapshot_sparse_state(repo: Path, wt: Path) -> dict[str, str]:
    """Capture the bits of sparse/worktree state we expect remediation to leave untouched."""
    snapshot: dict[str, str] = {}
    for key, path in [("repo", repo), ("wt", wt)]:
        cfg = subprocess.run(
            ["git", "-C", str(path), "config", "--get", "core.sparseCheckout"],
            capture_output=True,
            text=True,
            check=False,
        )
        snapshot[f"{key}.config_rc"] = str(cfg.returncode)
        snapshot[f"{key}.config_out"] = cfg.stdout.strip()
    # Pattern files.
    pf_primary = repo / ".git" / "info" / "sparse-checkout"
    snapshot["repo.pattern_exists"] = str(pf_primary.exists())
    if pf_primary.exists():
        snapshot["repo.pattern_body"] = pf_primary.read_text(encoding="utf-8")
    return snapshot


def test_refuses_when_primary_has_dirty_changes(tmp_path: Path) -> None:
    repo, wt = _seed_sparse_primary_with_worktree(tmp_path)

    # Dirty the primary with a tracked-file modification.
    (repo / "README.md").write_text("# Hello — edited\n", encoding="utf-8")

    before = _snapshot_sparse_state(repo, wt)

    report = scan_repo(repo)
    result = remediate(report, interactive=False)

    # All-or-nothing refusal across the board.
    assert result.overall_success is False
    assert result.primary_result.dirty_before_remediation is True
    assert result.primary_result.success is False
    assert result.primary_result.steps_completed == ()
    for wr in result.worktree_results:
        assert wr.dirty_before_remediation is True
        assert wr.success is False
        assert wr.steps_completed == ()

    # The operator's uncommitted edit must survive verbatim.
    assert (
        (repo / "README.md").read_text(encoding="utf-8") == "# Hello — edited\n"
    )

    # Sparse state on disk must be unchanged.
    after = _snapshot_sparse_state(repo, wt)
    assert after == before


def test_refuses_when_worktree_has_dirty_changes(tmp_path: Path) -> None:
    repo, wt = _seed_sparse_primary_with_worktree(tmp_path)

    # Dirty the worktree only, with an untracked file.
    (wt / "scratch.txt").write_text("work in progress\n", encoding="utf-8")

    before = _snapshot_sparse_state(repo, wt)

    report = scan_repo(repo)
    result = remediate(report, interactive=False)

    # Primary is clean but still refuses (all-or-nothing).
    assert result.overall_success is False
    assert result.primary_result.dirty_before_remediation is True
    assert result.primary_result.success is False
    for wr in result.worktree_results:
        assert wr.dirty_before_remediation is True
        assert wr.success is False

    # Operator's in-progress file must survive.
    assert (wt / "scratch.txt").read_text(encoding="utf-8") == "work in progress\n"

    after = _snapshot_sparse_state(repo, wt)
    assert after == before

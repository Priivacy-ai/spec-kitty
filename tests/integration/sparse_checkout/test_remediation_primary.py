"""Integration test: primary-only remediation against a real sparse repo.

Exercises :func:`specify_cli.git.sparse_checkout_remediation.remediate` end-to-
end against a real ``git init`` layout whose primary has ``core.sparseCheckout``
set to ``true`` and a realistic pattern file. Verifies that after a successful
run:

- ``core.sparseCheckout`` is unset (step 2).
- The ``.git/info/sparse-checkout`` pattern file is gone (step 3).
- Every tracked file previously hidden by the sparse filter is rehydrated
  (step 4) — the real regression that motivated FR-003.
- ``git status --porcelain`` is empty (step 5 / NFR-003).
- The result carries all five step names in order.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from specify_cli.git.sparse_checkout import scan_repo
from specify_cli.git.sparse_checkout_remediation import (
    STEP_REFRESH_WORKING_TREE,
    STEP_REMOVE_PATTERN_FILE,
    STEP_SPARSE_DISABLE,
    STEP_UNSET_CONFIG,
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


def _init_repo_with_multiple_tracked_files(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "test@example.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "Test User"])
    # Seed enough files that a restrictive sparse pattern actually hides some
    # of them — so step 4's rehydration is a non-trivial operation.
    (repo / "README.md").write_text("# Hello\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (repo / "src" / "b.py").write_text("print('b')\n", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "one.md").write_text("one\n", encoding="utf-8")
    (repo / "docs" / "two.md").write_text("two\n", encoding="utf-8")
    _run(["git", "-C", str(repo), "add", "-A"])
    _run(["git", "-C", str(repo), "commit", "-m", "seed"])


def test_primary_remediation_rehydrates_and_leaves_tree_clean(tmp_path: Path) -> None:
    repo = tmp_path / "sparse-primary"
    _init_repo_with_multiple_tracked_files(repo)

    # Enable sparse-checkout with a pattern that only matches README.md, then
    # apply it via `git read-tree` (the same mechanism `git sparse-checkout`
    # uses) so the filter actually hides src/ and docs/ from disk.
    _run(["git", "-C", str(repo), "config", "core.sparseCheckout", "true"])
    pf = repo / ".git" / "info" / "sparse-checkout"
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text("README.md\n", encoding="utf-8")
    _run(["git", "-C", str(repo), "read-tree", "-mu", "HEAD"])

    # Pre-conditions: sparse is active, some tracked files are hidden.
    assert not (repo / "src" / "a.py").exists()
    assert not (repo / "docs" / "one.md").exists()

    report = scan_repo(repo)
    assert report.primary.is_active is True
    assert report.worktrees == ()

    result = remediate(report, interactive=False)

    assert result.overall_success is True
    pr = result.primary_result
    assert pr.success is True
    assert pr.dirty_before_remediation is False
    assert pr.error_step is None
    assert pr.steps_completed == (
        STEP_SPARSE_DISABLE,
        STEP_UNSET_CONFIG,
        STEP_REMOVE_PATTERN_FILE,
        STEP_REFRESH_WORKING_TREE,
        STEP_VERIFY_CLEAN,
    )

    # Post-conditions.
    # 1. core.sparseCheckout is unset.
    cfg = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "core.sparseCheckout"],
        capture_output=True,
        text=True,
        check=False,
    )
    # Exit code 1 == key not set; 0 with "false" would also be acceptable.
    assert cfg.returncode != 0 or cfg.stdout.strip() == "false"
    # 2. Pattern file gone.
    assert not pf.exists()
    # 3. Previously hidden files have been rehydrated.
    assert (repo / "src" / "a.py").read_text(encoding="utf-8") == "print('a')\n"
    assert (repo / "docs" / "one.md").read_text(encoding="utf-8") == "one\n"
    # 4. Working tree clean.
    porcelain = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert porcelain.stdout.strip() == ""
    # 5. Final scan agrees — no sparse-checkout state detected anywhere.
    final_report = scan_repo(repo)
    assert final_report.any_active is False

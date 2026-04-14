"""Integration regression test for the safe_commit data-loss backstop.

Reproduces the sparse-checkout + index-refresh + phantom-deletion cascade
documented in Priivacy-ai/spec-kitty#588, and asserts that the commit-layer
backstop in :func:`safe_commit` aborts the commit before any data is lost.

Tagged ``#588`` so future developers can locate it when they see the cascade
again.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.git.commit_helpers import SafeCommitBackstopError, safe_commit

pytestmark = [pytest.mark.git_repo, pytest.mark.integration]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _git_ok(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git but do not raise on non-zero exit."""
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _head_count(repo: Path) -> int:
    result = _git(repo, "rev-list", "--count", "HEAD")
    return int(result.stdout.strip())


@pytest.fixture
def sparse_cascade_repo(tmp_path: Path) -> Path:
    """Build a repo that reproduces the #588 sparse-checkout cascade.

    Recipe:

    1. Init repo, commit files both inside and outside the future sparse cone.
    2. Enable ``core.sparseCheckout`` with a restrictive pattern.
    3. Advance ``HEAD`` with a second commit (mimics a merge advancing HEAD).
    4. Refresh the index so the working tree reflects the sparse filter against
       the new HEAD, producing phantom deletions in the staging area for the
       out-of-cone paths.
    """
    repo = tmp_path / "cascade"
    repo.mkdir()

    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")

    # Step 1: commit initial files.
    # - status.md is IN the future sparse cone.
    # - docs/long-runbook.md is OUT of the cone (the sparse filter excludes it).
    (repo / "status.md").write_text("status v1\n")
    docs = repo / "docs"
    docs.mkdir()
    (docs / "long-runbook.md").write_text("runbook v1\n" * 20)
    _git(repo, "add", "status.md", "docs/long-runbook.md")
    _git(repo, "commit", "-q", "-m", "initial")

    # Step 2: enable sparse checkout (cone mode) -- only include "status.md".
    _git(repo, "config", "core.sparseCheckout", "true")
    sparse_file = repo / ".git" / "info" / "sparse-checkout"
    sparse_file.parent.mkdir(parents=True, exist_ok=True)
    # Include only status.md at the top of the tree.
    sparse_file.write_text("/status.md\n")

    # Step 3: second commit advances HEAD (mimics a merge commit).
    (repo / "status.md").write_text("status v2\n")
    _git(repo, "add", "status.md")
    _git(repo, "commit", "-q", "-m", "advance HEAD")

    # Step 4: mark the out-of-cone path with skip-worktree + remove the working
    # copy, so the next `git add` against the committed path will stage a
    # phantom deletion (this is the exact cascade from #588).
    _git_ok(repo, "update-index", "--skip-worktree", "docs/long-runbook.md")
    runbook = repo / "docs" / "long-runbook.md"
    if runbook.exists():
        runbook.unlink()

    return repo


def test_backstop_catches_sparse_checkout_phantom_deletion(
    sparse_cascade_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression for Priivacy-ai/spec-kitty#588.

    The real cascade involves a chain of ``git stash`` / ``git stash pop``
    interactions with ``core.sparseCheckout`` + ``skip-worktree`` that
    re-introduce phantom deletions into the staging area between safe_commit's
    ``git add`` call and its ``git commit`` call.

    We reproduce the invariant the backstop must enforce: between the time
    safe_commit has staged the caller's requested file and the time it runs
    ``git commit``, the staging area contains an unexpected path (a phantom
    deletion of an out-of-cone file). The backstop must abort the commit
    BEFORE it is created --- preventing the 243-line phantom reversion that
    hit ``kg-automation`` ``main`` in mission 023.

    We inject the phantom deletion by intercepting ``subprocess.run`` and
    adding an ``update-index --force-remove`` for ``docs/long-runbook.md``
    immediately after safe_commit's ``git add`` step. That simulates the
    exact post-stage / pre-commit state the cascade produces.
    """
    repo = sparse_cascade_repo

    commits_before = _head_count(repo)

    # Write the caller's intended change.
    (repo / "status.md").write_text("status v3 -- housekeeping\n")

    # Intercept subprocess.run inside commit_helpers. The first time
    # ``git add --force -- status.md`` runs, we inject a phantom deletion
    # of docs/long-runbook.md into the staging area immediately after.
    import specify_cli.git.commit_helpers as helpers

    real_run = helpers.subprocess.run
    injected = {"done": False}

    def intercepting_run(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        result = real_run(*args, **kwargs)
        cmd = args[0] if args else kwargs.get("args")
        if (
            not injected["done"]
            and isinstance(cmd, list)
            and len(cmd) >= 2
            and cmd[0] == "git"
            and cmd[1] == "add"
            and "status.md" in cmd
        ):
            # Inject phantom deletion cascade without using subprocess.run
            # (so we don't recurse). ``--force-remove`` bypasses the sparse
            # filter --- this matches what stash-pop effectively does in the
            # real cascade.
            import subprocess as _sp

            _sp.run(
                [
                    "git",
                    "update-index",
                    "--force-remove",
                    "docs/long-runbook.md",
                ],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            injected["done"] = True
        return result

    monkeypatch.setattr(helpers.subprocess, "run", intercepting_run)

    # Act: the backstop must fire because docs/long-runbook.md is staged as
    # deleted but is NOT on the expected-paths list.
    with pytest.raises(SafeCommitBackstopError) as exc_info:
        safe_commit(
            repo_path=repo,
            files_to_commit=[repo / "status.md"],
            commit_message="chore: record done transitions",
            allow_empty=False,
        )

    err = exc_info.value
    unexpected_paths = {p.path for p in err.unexpected}
    assert "docs/long-runbook.md" in unexpected_paths, (
        f"expected docs/long-runbook.md in unexpected, got {unexpected_paths!r}"
    )

    # No new commit must exist --- the backstop fired BEFORE git commit.
    commits_after = _head_count(repo)
    assert commits_after == commits_before, (
        f"Backstop did not prevent the commit: {commits_before} -> {commits_after}"
    )


def test_backstop_has_no_force_bypass(tmp_path: Path) -> None:
    """``safe_commit`` does not expose a force parameter --- the backstop is unconditional.

    This guards against regressions where a future change introduces a bypass
    flag. The backstop protects every caller regardless of any upstream
    ``--force`` semantics in the outer command.
    """
    import inspect

    sig = inspect.signature(safe_commit)
    forbidden = {"force", "allow_force", "skip_backstop", "bypass_backstop"}
    offending = forbidden.intersection(sig.parameters)
    assert not offending, (
        f"safe_commit must NOT expose a backstop bypass parameter; found {offending}"
    )


def test_backstop_allows_clean_commit(tmp_path: Path) -> None:
    """Happy path: when the staging area contains only the expected paths,
    safe_commit proceeds normally."""
    repo = tmp_path / "clean-repo"
    repo.mkdir()

    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")

    (repo / "seed.md").write_text("seed\n")
    _git(repo, "add", "seed.md")
    _git(repo, "commit", "-q", "-m", "initial")

    (repo / "wp.md").write_text("wp content\n")

    result = safe_commit(
        repo_path=repo,
        files_to_commit=[repo / "wp.md"],
        commit_message="feat: add wp",
        allow_empty=False,
    )

    assert result is True
    # One extra commit was created.
    assert _head_count(repo) == 2

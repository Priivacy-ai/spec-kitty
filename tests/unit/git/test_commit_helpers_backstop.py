"""Unit tests for the safe_commit data-loss backstop.

These tests exercise :func:`assert_staging_area_matches_expected` directly
against a minimal git repository. They never call :func:`safe_commit` and
never create commits --- they only drive the staging-area probe.

See Priivacy-ai/spec-kitty#588 for the cascade this backstop defends against.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.git.commit_helpers import (
    SafeCommitBackstopError,
    UnexpectedStagedPath,
    assert_staging_area_matches_expected,
)

pytestmark = pytest.mark.git_repo


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Minimal git repo with two committed files for staging tests."""
    repo = tmp_path / "repo"
    repo.mkdir()

    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")

    (repo / "alpha.txt").write_text("alpha\n")
    (repo / "beta.txt").write_text("beta\n")
    _git(repo, "add", "alpha.txt", "beta.txt")
    _git(repo, "commit", "-q", "-m", "initial")

    return repo


def test_empty_stage_empty_expected_passes(git_repo: Path) -> None:
    """Empty staging area + empty expected list → no exception."""
    assert_staging_area_matches_expected(git_repo, [])


def test_empty_stage_nonempty_expected_passes(git_repo: Path) -> None:
    """Expected list with files but nothing staged → no exception (vacuous)."""
    assert_staging_area_matches_expected(git_repo, ["alpha.txt", "beta.txt"])


def test_staged_matches_expected_passes(git_repo: Path) -> None:
    """All staged paths are in expected list → no exception."""
    (git_repo / "alpha.txt").write_text("alpha v2\n")
    _git(git_repo, "add", "alpha.txt")

    # Expected contains the one staged file → pass.
    assert_staging_area_matches_expected(git_repo, ["alpha.txt"])


def test_extra_deletion_raises(git_repo: Path) -> None:
    """An unexpected deletion on stage → raise with status 'D '."""
    # Stage the actual caller file.
    (git_repo / "alpha.txt").write_text("alpha v2\n")
    _git(git_repo, "add", "alpha.txt")

    # Independently stage a phantom deletion of beta.txt (simulates the
    # sparse-checkout cascade).
    (git_repo / "beta.txt").unlink()
    _git(git_repo, "add", "beta.txt")

    with pytest.raises(SafeCommitBackstopError) as exc_info:
        assert_staging_area_matches_expected(git_repo, ["alpha.txt"])

    err = exc_info.value
    assert any(
        p.path == "beta.txt" and p.status_code.startswith("D")
        for p in err.unexpected
    ), f"expected phantom deletion of beta.txt, got {err.unexpected!r}"
    # The requested list should be preserved.
    assert "alpha.txt" in err.requested
    # Error message is human-readable and includes the unexpected path.
    assert "beta.txt" in str(err)
    assert "Commit aborted" in str(err)


def test_extra_modification_raises(git_repo: Path) -> None:
    """An unexpected modification on stage → raise with status 'M '."""
    # Caller expects to commit alpha.txt only.
    (git_repo / "alpha.txt").write_text("alpha v2\n")
    _git(git_repo, "add", "alpha.txt")

    # Unexpected modification of beta.txt sneaks into the stage.
    (git_repo / "beta.txt").write_text("beta v2\n")
    _git(git_repo, "add", "beta.txt")

    with pytest.raises(SafeCommitBackstopError) as exc_info:
        assert_staging_area_matches_expected(git_repo, ["alpha.txt"])

    err = exc_info.value
    assert any(
        p.path == "beta.txt" and p.status_code.startswith("M")
        for p in err.unexpected
    ), f"expected modification of beta.txt, got {err.unexpected!r}"


def test_extra_addition_raises(git_repo: Path) -> None:
    """An unexpected new file on stage → raise with status 'A '."""
    (git_repo / "alpha.txt").write_text("alpha v2\n")
    _git(git_repo, "add", "alpha.txt")

    # Add a brand-new file that the caller did not request.
    (git_repo / "gamma.txt").write_text("gamma\n")
    _git(git_repo, "add", "gamma.txt")

    with pytest.raises(SafeCommitBackstopError) as exc_info:
        assert_staging_area_matches_expected(git_repo, ["alpha.txt"])

    err = exc_info.value
    assert any(
        p.path == "gamma.txt" and p.status_code.startswith("A")
        for p in err.unexpected
    ), f"expected addition of gamma.txt, got {err.unexpected!r}"


def test_windows_separator_in_expected_is_normalized(git_repo: Path) -> None:
    """Windows-style backslashes in the expected list are normalized before compare.

    We stage a file at ``subdir/alpha.txt`` (POSIX, as git reports it) and
    pass the expected path with backslashes. No false positive must fire.
    """
    subdir = git_repo / "subdir"
    subdir.mkdir()
    (subdir / "alpha.txt").write_text("nested\n")
    _git(git_repo, "add", "subdir/alpha.txt")

    # Pass Windows-style path: must be normalized to POSIX before compare.
    assert_staging_area_matches_expected(git_repo, ["subdir\\alpha.txt"])


def test_git_probe_failure_raises(tmp_path: Path) -> None:
    """If the ``git diff --cached`` probe fails, raise with '<probe-failed>' sentinel."""
    # Not a git repo → git diff returns non-zero.
    non_repo = tmp_path / "not-a-repo"
    non_repo.mkdir()

    with pytest.raises(SafeCommitBackstopError) as exc_info:
        assert_staging_area_matches_expected(non_repo, ["anything.txt"])

    err = exc_info.value
    assert len(err.unexpected) == 1
    assert err.unexpected[0].path == "<probe-failed>"
    assert err.unexpected[0].status_code == "??"
    assert err.requested == ("anything.txt",)


def test_unexpected_staged_path_is_frozen_dataclass() -> None:
    """UnexpectedStagedPath is a frozen dataclass --- instances are immutable."""
    from dataclasses import FrozenInstanceError

    p = UnexpectedStagedPath(path="a.txt", status_code="D ")
    with pytest.raises(FrozenInstanceError):
        p.path = "b.txt"  # type: ignore[misc]

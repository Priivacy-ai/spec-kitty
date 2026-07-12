"""Tests for the shared lanes git existence-check helpers (issue #1904).

Uses real git repos (not mocks), matching the lanes test-suite convention, so
the helpers are exercised against actual ``git rev-parse`` behavior.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from specify_cli.lanes._git import (
    branch_exists,
    lane_has_commit_beyond_base,
    ref_exists,
)

pytestmark = pytest.mark.git_repo


def _make_git_repo(path: Path) -> None:
    """Create a minimal git repo with an initial commit on ``main``."""
    subprocess.run(["git", "init", "-b", "main", str(path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(path), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(path), capture_output=True, check=True,
    )
    (path / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(path), capture_output=True, check=True,
    )


def test_branch_exists_true_for_existing_local_branch(tmp_path: Path) -> None:
    _make_git_repo(tmp_path)
    assert branch_exists(tmp_path, "main") is True


def test_branch_exists_false_for_absent_branch(tmp_path: Path) -> None:
    _make_git_repo(tmp_path)
    assert branch_exists(tmp_path, "does-not-exist") is False


def test_branch_exists_true_for_created_branch(tmp_path: Path) -> None:
    _make_git_repo(tmp_path)
    subprocess.run(
        ["git", "branch", "feature/x"],
        cwd=str(tmp_path), capture_output=True, check=True,
    )
    assert branch_exists(tmp_path, "feature/x") is True


def test_branch_exists_false_for_tag_only(tmp_path: Path) -> None:
    """A tag of the same name must not register as a branch (refs/heads only)."""
    _make_git_repo(tmp_path)
    subprocess.run(
        ["git", "tag", "v1"],
        cwd=str(tmp_path), capture_output=True, check=True,
    )
    assert branch_exists(tmp_path, "v1") is False


def test_branch_exists_with_explicit_env(tmp_path: Path) -> None:
    """A composed env (the merge-pipeline pattern) is honored, not ignored."""
    _make_git_repo(tmp_path)
    env = os.environ.copy()
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    assert branch_exists(tmp_path, "main", env=env) is True
    assert branch_exists(tmp_path, "nope", env=env) is False


def test_ref_exists_true_for_branch_name(tmp_path: Path) -> None:
    _make_git_repo(tmp_path)
    assert ref_exists(tmp_path, "main") is True


def test_ref_exists_true_for_head(tmp_path: Path) -> None:
    _make_git_repo(tmp_path)
    assert ref_exists(tmp_path, "HEAD") is True


def test_ref_exists_false_for_unresolvable_ref(tmp_path: Path) -> None:
    _make_git_repo(tmp_path)
    assert ref_exists(tmp_path, "2.x") is False


def test_ref_exists_true_for_tag(tmp_path: Path) -> None:
    """ref_exists accepts any revspec that peels to a commit, including tags."""
    _make_git_repo(tmp_path)
    subprocess.run(
        ["git", "tag", "v1"],
        cwd=str(tmp_path), capture_output=True, check=True,
    )
    assert ref_exists(tmp_path, "v1") is True


def test_ref_exists_with_explicit_env(tmp_path: Path) -> None:
    _make_git_repo(tmp_path)
    env = os.environ.copy()
    assert ref_exists(tmp_path, "main", env=env) is True
    assert ref_exists(tmp_path, "missing", env=env) is False


def _commit(path: Path, name: str) -> None:
    (path / name).write_text("x\n")
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", name], cwd=str(path), capture_output=True, check=True
    )


def test_lane_has_commit_beyond_base_false_when_at_base(tmp_path: Path) -> None:
    """No commit beyond base (HEAD == base) -> False (the gate rejects)."""
    _make_git_repo(tmp_path)
    subprocess.run(
        ["git", "branch", "base"], cwd=str(tmp_path), capture_output=True, check=True
    )
    assert lane_has_commit_beyond_base(tmp_path, "base") is False


def test_lane_has_commit_beyond_base_true_with_a_commit(tmp_path: Path) -> None:
    """A commit on HEAD beyond base -> True (the gate passes)."""
    _make_git_repo(tmp_path)
    subprocess.run(
        ["git", "branch", "base"], cwd=str(tmp_path), capture_output=True, check=True
    )
    _commit(tmp_path, "impl.py")
    assert lane_has_commit_beyond_base(tmp_path, "base") is True


def test_lane_has_commit_beyond_base_false_for_unresolvable_base(tmp_path: Path) -> None:
    """Fail-closed: an unresolvable base ref (rev-list errors) -> False."""
    _make_git_repo(tmp_path)
    assert lane_has_commit_beyond_base(tmp_path, "no-such-branch") is False


def test_lane_has_commit_beyond_base_false_on_unparseable_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-closed: rev-list exits 0 but emits a non-integer count -> False.

    Real ``git rev-list --count`` always prints an integer, so the defensive
    ``ValueError`` branch (returncode 0, unparseable stdout) is unreachable with
    real git. Simulate the pathological success-with-garbage-stdout to pin the
    fail-closed contract: an unverifiable count must reject (False), never wave
    the for_review commit gate through.
    """
    import specify_cli.lanes._git as git_mod

    def _fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not-a-number\n", stderr=""
        )

    monkeypatch.setattr(git_mod.subprocess, "run", _fake_run)
    assert lane_has_commit_beyond_base(tmp_path, "base") is False


# ---------------------------------------------------------------------------
# Alert #69 (SonarCloud S6350): option-injection separator for ``_verify``
#
# ``_verify`` (the shared plumbing behind both ``branch_exists`` and
# ``ref_exists``) passes an internally-derived refspec to
# ``git rev-parse --verify`` unprefixed. ``--end-of-options`` makes the value
# unambiguously positional, so a hostile refspec starting with ``-`` cannot be
# parsed as an option.
# ---------------------------------------------------------------------------


def test_verify_inserts_end_of_options_before_refspec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import specify_cli.lanes._git as git_mod

    calls: list[list[str]] = []

    def _fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(git_mod.subprocess, "run", _fake_run)

    hostile_ref = "--upload-pack=touch /pwned-marker"
    assert git_mod._verify(Path("/fake/repo"), hostile_ref) is True

    assert len(calls) == 1
    argv = calls[0]
    assert argv == [
        "git",
        "-C",
        "/fake/repo",
        "rev-parse",
        "--verify",
        "--quiet",
        "--end-of-options",
        hostile_ref,
    ]
    sep_index = argv.index("--end-of-options")
    assert argv[sep_index + 1] == hostile_ref


def test_branch_exists_with_hostile_name_places_it_after_separator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``branch_exists`` composes ``refs/heads/<branch>`` — still lands after the separator."""
    import specify_cli.lanes._git as git_mod

    calls: list[list[str]] = []

    def _fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(git_mod.subprocess, "run", _fake_run)

    hostile_branch = "-D"
    assert branch_exists(Path("/fake/repo"), hostile_branch) is True

    argv = calls[0]
    sep_index = argv.index("--end-of-options")
    assert argv[sep_index + 1] == f"refs/heads/{hostile_branch}"

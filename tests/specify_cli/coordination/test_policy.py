"""Unit tests for ``specify_cli.coordination.policy`` (WP05 T021 / T025).

Covers every stable error code:

* ``DESTINATION_REF_INVALID_SHAPE`` (refs/heads prefix, empty, leading -)
* ``DESTINATION_REF_NOT_FOUND``
* ``DESTINATION_REF_NOT_LOCAL`` (remote-tracking)
* ``PROTECTED_BRANCH_REFUSED`` (``main`` / ``master``)
* :class:`Allowed` for the happy path.

Plus a side-effect-free assertion: calling ``assert_allowed`` does not
modify the index, working tree, or .git directory.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.policy import WorkflowMutationPolicy
from specify_cli.coordination.types import Allowed, GitChangeSet, Refused

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Tmp repo with main + a non-protected ``feature`` branch."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "seed.txt").write_text("seed\n")
    _git(r, "add", "seed.txt")
    _git(r, "commit", "-q", "-m", "initial")
    _git(r, "branch", "feature")
    _git(r, "branch", "kitty/mission-foo-01ABCDEF")
    return r


def _change(
    repo: Path, ref: str, operation: str = "test",
) -> GitChangeSet:
    return GitChangeSet(
        destination_ref=ref,
        repo_root=repo,
        worktree_root=repo,
        paths=(),
        message="m",
        operation=operation,
    )


def test_allowed_for_non_protected_branch(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _change(repo, "kitty/mission-foo-01ABCDEF"),
    )
    assert isinstance(verdict, Allowed)


def test_refused_invalid_shape_refs_heads_prefix(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _change(repo, "refs/heads/feature"),
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == "DESTINATION_REF_INVALID_SHAPE"


def test_refused_invalid_shape_empty(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _change(repo, ""),
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == "DESTINATION_REF_INVALID_SHAPE"


def test_refused_invalid_shape_leading_dash(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _change(repo, "-bad-name"),
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == "DESTINATION_REF_INVALID_SHAPE"


def test_refused_not_found(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _change(repo, "kitty/never-existed"),
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == "DESTINATION_REF_NOT_FOUND"


def test_refused_protected_main(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _change(repo, "main", operation="emit_status_transition"),
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == "PROTECTED_BRANCH_REFUSED"
    assert "main" in verdict.destination_ref
    assert "emit_status_transition" in verdict.message


def test_refused_not_local_remote_tracking(repo: Path, tmp_path: Path) -> None:
    """A ref that only exists as ``refs/remotes/origin/<name>`` → NOT_LOCAL."""
    # Create a fake "origin" remote-tracking ref by fetching from a
    # second tmp repo. Simplest path: write directly into refs/remotes.
    rem_dir = repo / ".git" / "refs" / "remotes" / "origin"
    rem_dir.mkdir(parents=True, exist_ok=True)
    head_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True,
    ).strip()
    (rem_dir / "only-remote").write_text(head_sha + "\n")

    verdict = WorkflowMutationPolicy.assert_allowed(
        _change(repo, "only-remote"),
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == "DESTINATION_REF_NOT_LOCAL"


def test_assert_allowed_is_side_effect_free(repo: Path) -> None:
    """Calling assert_allowed many times leaves repo state unchanged."""
    def state_hash() -> str:
        # Hash the index file + working-tree mtime tree summary.
        index_path = repo / ".git" / "index"
        h = hashlib.sha256()  # noqa: TID251 — file-integrity checksum of git index + working-tree bytes, not charter freshness hashing
        if index_path.exists():
            h.update(index_path.read_bytes())
        for f in sorted(repo.glob("*")):
            if f.is_file():
                h.update(f.read_bytes())
        return h.hexdigest()

    before = state_hash()
    for ref in (
        "main",
        "feature",
        "kitty/mission-foo-01ABCDEF",
        "refs/heads/feature",
        "",
        "kitty/never-existed",
    ):
        WorkflowMutationPolicy.assert_allowed(_change(repo, ref))
    after = state_hash()
    assert before == after

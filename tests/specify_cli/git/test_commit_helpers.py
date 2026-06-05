"""Unit tests for the destination-ref-aware ``safe_commit()`` helper.

These tests exercise the HEAD-assertion contract introduced by mission
``mission-coordination-branch-atomic-event-log`` (WP01) for issue
Priivacy-ai/spec-kitty#1348.

Every test uses a tmp git repo on a non-protected branch unless the test is
specifically about the protected-branch refusal.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.git.commit_helpers import (
    CommitResult,
    ProtectedBranchRefused,
    SafeCommitDestinationNotFound,
    SafeCommitDestinationRefShape,
    SafeCommitEmptyChangeset,
    SafeCommitHeadMismatch,
    SafeCommitNotAWorktree,
    safe_commit,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(repo: Path, initial_branch: str = "kitty/mission-test-01ABCDEF") -> None:
    """Initialize a tmp git repo on ``initial_branch`` with one initial commit."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", initial_branch)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial commit")


@pytest.fixture
def lane_repo(tmp_path: Path) -> Path:
    """Tmp git repo checked out to a non-protected lane branch."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="kitty/mission-test-01ABCDEF")
    return repo


# ---------------------------------------------------------------------------
# T004: happy path + error paths
# ---------------------------------------------------------------------------


def test_safe_commit_happy_path(lane_repo: Path) -> None:
    """Worktree on destination_ref + non-protected → commit succeeds."""
    target = lane_repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    result = safe_commit(
        repo_root=lane_repo,
        worktree_root=lane_repo,
        destination_ref="kitty/mission-test-01ABCDEF",
        message="WP01: add alpha",
        paths=(target,),
    )

    assert isinstance(result, CommitResult)
    assert len(result.sha) == 40, "expected full SHA-1"
    assert result.destination_ref == "kitty/mission-test-01ABCDEF"
    assert result.worktree_root == lane_repo

    # Verify commit landed on the expected branch.
    log = subprocess.run(
        ["git", "log", "-1", "--format=%H %s"],
        cwd=lane_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert result.sha in log
    assert "WP01: add alpha" in log


def test_safe_commit_accepts_realpath_under_symlinked_worktree(lane_repo: Path, tmp_path: Path) -> None:
    """Absolute paths resolved via the real path still normalize under a symlinked worktree."""
    repo_alias = tmp_path / "repo-alias"
    repo_alias.symlink_to(lane_repo, target_is_directory=True)

    target = (lane_repo / "alpha.txt").resolve()
    target.write_text("alpha v1\n", encoding="utf-8")

    result = safe_commit(
        repo_root=repo_alias,
        worktree_root=repo_alias,
        destination_ref="kitty/mission-test-01ABCDEF",
        message="WP01: add alpha via alias",
        paths=(target,),
    )

    assert isinstance(result, CommitResult)


def test_safe_commit_head_mismatch(lane_repo: Path) -> None:
    """Worktree on a different branch → SafeCommitHeadMismatch with structured fields."""
    # Create + check out an *other* branch.
    _git(lane_repo, "checkout", "-q", "-b", "kitty/mission-other-99ZZZZZZ")

    target = lane_repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    with pytest.raises(SafeCommitHeadMismatch) as exc_info:
        safe_commit(
            repo_root=lane_repo,
            worktree_root=lane_repo,
            destination_ref="kitty/mission-test-01ABCDEF",
            message="WP01: add alpha",
            paths=(target,),
        )

    err = exc_info.value
    assert err.error_code == "SAFE_COMMIT_HEAD_MISMATCH"
    assert err.destination_ref == "kitty/mission-test-01ABCDEF"
    assert err.observed_head == "kitty/mission-other-99ZZZZZZ"
    assert err.worktree_root == lane_repo
    # JSON-serializable.
    payload = err.to_dict()
    assert payload["error_code"] == "SAFE_COMMIT_HEAD_MISMATCH"
    assert payload["destination_ref"] == "kitty/mission-test-01ABCDEF"
    assert payload["observed_head"] == "kitty/mission-other-99ZZZZZZ"
    assert payload["worktree_root"] == str(lane_repo)


def test_safe_commit_protected_branch(tmp_path: Path) -> None:
    """destination_ref=main → ProtectedBranchRefused."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    target = repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    with pytest.raises(ProtectedBranchRefused) as exc_info:
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="main",
            message="WP01: add alpha",  # NOT a documented exception
            paths=(target,),
        )

    err = exc_info.value
    assert err.error_code == "SAFE_COMMIT_PROTECTED_BRANCH"
    assert err.destination_ref == "main"
    assert err.worktree_root == repo
    assert err.commit_message == "WP01: add alpha"


def test_safe_commit_allows_completed_op_record_on_protected_branch(tmp_path: Path) -> None:
    """The explicit Op policy can commit one completed Op file on protected branches."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    op_id = "01KTBTTSWK43WGCPYKBMRCCY8T"
    op_path = repo / "kitty-ops" / f"{op_id}.jsonl"
    op_path.parent.mkdir()
    op_path.write_text(
        '{"event":"started","invocation_id":"01KTBTTSWK43WGCPYKBMRCCY8T"}\n'
        '{"event":"completed","invocation_id":"01KTBTTSWK43WGCPYKBMRCCY8T"}\n',
        encoding="utf-8",
    )

    (repo / "seed.txt").write_text("seed staged outside Op commit\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")

    result = safe_commit(
        repo_root=repo,
        worktree_root=repo,
        destination_ref="main",
        message=f"op(implementer-fixture): implement [{op_id[:8]}]",
        paths=(op_path,),
        allow_completed_op_on_protected_branch=True,
    )

    assert isinstance(result, CommitResult)
    assert result.destination_ref == "main"

    committed_files = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout.splitlines()
    assert committed_files == [f"kitty-ops/{op_id}.jsonl"]

    staged_files = _git(repo, "diff", "--cached", "--name-only").stdout.splitlines()
    assert staged_files == ["seed.txt"]


def test_safe_commit_rejects_op_record_on_protected_branch_without_policy(
    tmp_path: Path,
) -> None:
    """A valid Op path still refuses on main unless the Op policy is explicit."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    op_id = "01KTBTTSWK43WGCPYKBMRCCY8T"
    op_path = repo / "kitty-ops" / f"{op_id}.jsonl"
    op_path.parent.mkdir()
    op_path.write_text('{"event":"completed"}\n', encoding="utf-8")

    with pytest.raises(ProtectedBranchRefused):
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="main",
            message=f"op(implementer-fixture): implement [{op_id[:8]}]",
            paths=(op_path,),
        )


@pytest.mark.parametrize(
    "content",
    [
        '{"event":"started","invocation_id":"01KTBTTSWK43WGCPYKBMRCCY8T"}\n',
        '{"event":"completed","invocation_id":"01KTBTTSWK43WGCPYKBMRCCY8U"}\n',
        "not json\n",
    ],
)
def test_safe_commit_op_policy_requires_completed_event_for_matching_op_id(
    tmp_path: Path,
    content: str,
) -> None:
    """Protected-branch Op exception is content-aware, not path-only."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    op_id = "01KTBTTSWK43WGCPYKBMRCCY8T"
    op_path = repo / "kitty-ops" / f"{op_id}.jsonl"
    op_path.parent.mkdir()
    op_path.write_text(content, encoding="utf-8")

    with pytest.raises(ProtectedBranchRefused):
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="main",
            message=f"op(implementer-fixture): implement [{op_id[:8]}]",
            paths=(op_path,),
            allow_completed_op_on_protected_branch=True,
        )


@pytest.mark.parametrize(
    "relative_path",
    [
        Path("kitty-ops/ops-index.jsonl"),
        Path("kitty-ops/lifecycle.jsonl"),
        Path("kitty-ops/01KTBTTSWK43WGCPYKBMRCCY8T.txt"),
        Path("kitty-ops/not-a-ulid.jsonl"),
        Path("other/01KTBTTSWK43WGCPYKBMRCCY8T.jsonl"),
    ],
)
def test_safe_commit_op_policy_rejects_non_op_paths_on_protected_branch(
    tmp_path: Path,
    relative_path: Path,
) -> None:
    """The Op protected-branch policy is limited to one kitty-ops/<op-id>.jsonl."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("not a completed Op record\n", encoding="utf-8")

    with pytest.raises(ProtectedBranchRefused):
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="main",
            message="op(implementer-fixture): implement [01KTBTTS]",
            paths=(target,),
            allow_completed_op_on_protected_branch=True,
        )


def test_safe_commit_op_policy_rejects_extra_paths_on_protected_branch(tmp_path: Path) -> None:
    """The Op protected-branch policy never widens to multi-path commits."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    op_id = "01KTBTTSWK43WGCPYKBMRCCY8T"
    op_path = repo / "kitty-ops" / f"{op_id}.jsonl"
    op_path.parent.mkdir()
    op_path.write_text('{"event":"completed"}\n', encoding="utf-8")
    extra_path = repo / "extra.txt"
    extra_path.write_text("extra\n", encoding="utf-8")

    with pytest.raises(ProtectedBranchRefused):
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="main",
            message=f"op(implementer-fixture): implement [{op_id[:8]}]",
            paths=(op_path, extra_path),
            allow_completed_op_on_protected_branch=True,
        )


def test_safe_commit_op_policy_requires_op_commit_message(tmp_path: Path) -> None:
    """The protected-branch Op policy also requires the op(...) convention."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    op_id = "01KTBTTSWK43WGCPYKBMRCCY8T"
    op_path = repo / "kitty-ops" / f"{op_id}.jsonl"
    op_path.parent.mkdir()
    op_path.write_text('{"event":"completed"}\n', encoding="utf-8")

    with pytest.raises(ProtectedBranchRefused):
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="main",
            message="chore: arbitrary protected branch commit",
            paths=(op_path,),
            allow_completed_op_on_protected_branch=True,
        )


def test_safe_commit_protected_branch_allows_documented_exception(tmp_path: Path) -> None:
    """Documented exception messages may land on a protected branch."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    target = repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    # "chore: apply spec-kitty upgrade changes" is on the documented exception list.
    result = safe_commit(
        repo_root=repo,
        worktree_root=repo,
        destination_ref="main",
        message="chore: apply spec-kitty upgrade changes (3.0.0 -> 3.1.0)",
        paths=(target,),
    )
    assert isinstance(result, CommitResult)
    assert result.destination_ref == "main"


def test_safe_commit_protected_branch_rejects_test_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test mode must not bypass safe_commit protected-branch policy."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")
    monkeypatch.setenv("SPEC_KITTY_TEST_MODE", "1")

    target = repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    with pytest.raises(ProtectedBranchRefused):
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="main",
            message="WP01: add alpha",
            paths=(target,),
        )


def test_safe_commit_protected_branch_rejects_planning_artifact_message(tmp_path: Path) -> None:
    """The removed 'chore: planning artifacts for' exception must NOT bypass."""
    repo = tmp_path / "repo"
    _init_repo(repo, initial_branch="main")

    target = repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    with pytest.raises(ProtectedBranchRefused):
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="main",
            message="chore: planning artifacts for 099-demo",
            paths=(target,),
        )


def test_safe_commit_empty_paths(lane_repo: Path) -> None:
    """Empty paths tuple → SafeCommitEmptyChangeset."""
    with pytest.raises(SafeCommitEmptyChangeset) as exc_info:
        safe_commit(
            repo_root=lane_repo,
            worktree_root=lane_repo,
            destination_ref="kitty/mission-test-01ABCDEF",
            message="WP01: empty",
            paths=(),
        )
    assert exc_info.value.error_code == "SAFE_COMMIT_EMPTY_CHANGESET"
    assert exc_info.value.destination_ref == "kitty/mission-test-01ABCDEF"


def test_safe_commit_destination_not_found(lane_repo: Path) -> None:
    """Non-existent destination ref → SafeCommitDestinationNotFound.

    We force this by checking out a detached HEAD onto the same commit so the
    HEAD-assertion gate would still fire first if we pointed there. Easier:
    create a *new* branch at HEAD called ``ghost``, delete it, then ask
    safe_commit to commit to a *different* non-existent ref while sitting on
    the live branch — but that fails the HEAD-mismatch gate first.

    The cleanest path: rename the current branch on disk so the HEAD points
    at it but it doesn't exist as a ref. That's not possible (HEAD is a
    symbolic ref to a ref that must exist for git to operate). So we
    instead exercise this by spoofing: create a worktree on a branch, then
    have the HEAD point at a different (non-existent) ref — impossible. The
    practical way to hit SAFE_COMMIT_DESTINATION_NOT_FOUND: the gate fires
    when HEAD matches destination_ref but rev-parse fails. The only way HEAD
    can equal a name whose ref doesn't exist is via an unborn branch (no
    initial commit). So initialize a repo, do NOT create the first commit,
    and call safe_commit.
    """
    repo = lane_repo.parent / "unborn"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "kitty/mission-test-01ABCDEF")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")
    # No commit -> branch ref does not exist yet, but HEAD points at it.
    target = repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    with pytest.raises(SafeCommitDestinationNotFound) as exc_info:
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            destination_ref="kitty/mission-test-01ABCDEF",
            message="WP01: add alpha",
            paths=(target,),
        )
    err = exc_info.value
    assert err.error_code == "SAFE_COMMIT_DESTINATION_NOT_FOUND"
    assert err.destination_ref == "kitty/mission-test-01ABCDEF"
    assert err.worktree_root == repo


def test_safe_commit_destination_ref_shape(lane_repo: Path) -> None:
    """Passing fully-qualified ref → SafeCommitDestinationRefShape (C-016)."""
    target = lane_repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    with pytest.raises(SafeCommitDestinationRefShape) as exc_info:
        safe_commit(
            repo_root=lane_repo,
            worktree_root=lane_repo,
            destination_ref="refs/heads/kitty/mission-test-01ABCDEF",
            message="WP01: add alpha",
            paths=(target,),
        )
    err = exc_info.value
    assert err.error_code == "SAFE_COMMIT_DESTINATION_REF_SHAPE"
    assert err.destination_ref == "refs/heads/kitty/mission-test-01ABCDEF"


def test_safe_commit_normalizes_symbolic_ref(lane_repo: Path) -> None:
    """``git symbolic-ref HEAD`` returns ``refs/heads/<branch>``; helper strips it.

    Without normalization, comparing raw symbolic-ref output to the short
    destination_ref would always mismatch. This test pins the normalization.
    """
    # Sanity: raw symbolic-ref includes the prefix.
    raw = subprocess.run(
        ["git", "symbolic-ref", "HEAD"],
        cwd=lane_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert raw == "refs/heads/kitty/mission-test-01ABCDEF"

    # Helper compares the short form and accepts the commit.
    target = lane_repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    result = safe_commit(
        repo_root=lane_repo,
        worktree_root=lane_repo,
        destination_ref="kitty/mission-test-01ABCDEF",
        message="WP01: normalize check",
        paths=(target,),
    )
    assert result.destination_ref == "kitty/mission-test-01ABCDEF"


def test_safe_commit_not_a_worktree(tmp_path: Path, lane_repo: Path) -> None:
    """``worktree_root`` not a git worktree → SafeCommitNotAWorktree."""
    not_a_worktree = tmp_path / "not-a-worktree"
    not_a_worktree.mkdir()

    target = not_a_worktree / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    with pytest.raises(SafeCommitNotAWorktree) as exc_info:
        safe_commit(
            repo_root=lane_repo,
            worktree_root=not_a_worktree,
            destination_ref="kitty/mission-test-01ABCDEF",
            message="WP01: add alpha",
            paths=(target,),
        )
    err = exc_info.value
    assert err.error_code == "SAFE_COMMIT_NOT_A_WORKTREE"
    assert err.worktree_root == not_a_worktree


def test_safe_commit_absolute_path_outside_worktree(lane_repo: Path) -> None:
    """Absolute paths that don't sit under ``worktree_root`` pass through as-is.

    This exercises the ``ValueError`` fall-through in path normalization
    (it does NOT mean the commit succeeds — staging will fail). We assert
    that the helper raises a clear RuntimeError, not a confusing AttributeError.
    """
    foreign = Path("/tmp/this-path-is-not-in-the-worktree.txt")

    # The helper either fails to stage (RuntimeError) or fails the backstop.
    # Either way, no commit lands.
    with pytest.raises((RuntimeError,)):
        safe_commit(
            repo_root=lane_repo,
            worktree_root=lane_repo,
            destination_ref="kitty/mission-test-01ABCDEF",
            message="WP01: foreign path",
            paths=(foreign,),
        )


def test_safe_commit_relative_path(lane_repo: Path) -> None:
    """Relative paths under the worktree are accepted directly."""
    (lane_repo / "beta.txt").write_text("beta\n", encoding="utf-8")
    result = safe_commit(
        repo_root=lane_repo,
        worktree_root=lane_repo,
        destination_ref="kitty/mission-test-01ABCDEF",
        message="WP01: relative path",
        paths=(Path("beta.txt"),),
    )
    assert isinstance(result, CommitResult)


def test_safe_commit_keyword_only(lane_repo: Path) -> None:
    """Positional call → TypeError (signature is keyword-only)."""
    target = lane_repo / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    with pytest.raises(TypeError):
        # Intentional bad call: positional args.
        # Routed through a dynamic dispatch so mypy doesn't flag the bad call
        # at static-check time; runtime still raises TypeError.
        _dispatch = safe_commit
        _dispatch(  # type: ignore[misc]
            lane_repo,
            lane_repo,
            "kitty/mission-test-01ABCDEF",
            "WP01: add alpha",
            (target,),
        )

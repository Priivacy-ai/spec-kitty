"""The single sanctioned protected-flow bookkeeping-commit surface (#2280 / PR #2281).

Two flows land a post-completion bookkeeping commit on a (possibly protected)
target branch:

* the **merge executor** (``merge/executor.py``) — the done-transition
  bookkeeping that persists status events before worktree teardown (INV-5); and
* the **retrospective terminus** (``post_merge/retrospective_terminus.py``) —
  which commits the auto-captured ``retrospective.yaml`` + its event-log append
  and runs from BOTH the ``spec-kitty merge`` path AND the ``mission close``
  path.

Both route their guarded commit through THIS one function so there is a SINGLE
``GuardCapability.MERGE_BOOKKEEPING`` protected-flow commit surface, rather than
a second guard-capability call site outside the merge executor (the #1850
guard-bypass class the architectural ratchet in
``tests/architectural/test_guard_capability_call_sites.py`` defends against).

The seam is a thin, policy-free wrapper: it performs the guarded commit and
returns / raises exactly as :func:`safe_commit` does. Each caller keeps its own
failure policy — the merge executor restores snapshots and RE-RAISES (a
bookkeeping failure aborts the merge), while the retrospective terminus is
fail-open (it warns and never aborts merge/close).
"""

from __future__ import annotations

from pathlib import Path

from mission_runtime import CommitTarget

from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.commit_helpers import CommitResult, safe_commit


def commit_merge_bookkeeping(
    *,
    repo_root: Path,
    worktree_root: Path,
    branch: str,
    message: str,
    paths: tuple[Path, ...],
) -> CommitResult:
    """Commit ``paths`` onto ``branch`` as an authorized merge-bookkeeping flow.

    ``branch`` is the short destination ref (never ``refs/heads/...``); it is
    wrapped in the canonical :class:`CommitTarget` before the guarded commit, so
    this surface uses the preferred ``target=`` API rather than the retired
    two-arg ``destination_ref=`` shim.

    Args:
        repo_root: Path to the primary git repository.
        worktree_root: Path to the worktree the commit lands in (may equal
            ``repo_root``).
        branch: Short destination branch name the commit must land on.
        message: The commit message.
        paths: The exact file paths to stage and commit.

    Returns:
        The :class:`CommitResult` from :func:`safe_commit`.

    Raises:
        Whatever :func:`safe_commit` raises — callers own their fail-open /
        fail-closed policy.
    """
    return safe_commit(
        repo_root=repo_root,
        worktree_root=worktree_root,
        target=CommitTarget(ref=branch),
        message=message,
        paths=paths,
        capability=GuardCapability.MERGE_BOOKKEEPING,
    )

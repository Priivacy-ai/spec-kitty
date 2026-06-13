"""Branch ref advance with checked-out-worktree resync (#1826).

The merge pipeline advances ``refs/heads/<branch>`` via ``git update-ref``
from detached temporary worktrees. ``update-ref`` is plumbing: it bypasses
git's checked-out-branch protection and updates nothing in any worktree that
has the branch checked out. That worktree is left with an index/working tree
*behind its own HEAD* — the next safe-commit through it sees phantom staged
deletions, and a plain ``git commit`` from its stale index would silently
delete the advanced commits' files from the branch (#1826).

:func:`advance_branch_ref` is the single sanctioned way for the merge
pipeline to advance a branch ref. **Invariant: no worktree may be left
checked out behind a ref this function advanced.** An architectural ratchet
(``tests/architectural/test_merge_pipeline_ratchets.py``) enforces that no
raw ``update-ref`` subprocess invocation exists in ``src/specify_cli``
outside this module (AC-B3).

Locking: the three merge-pipeline call sites (``lanes/merge.py`` Stage-1
lane→mission advances and ``cli/commands/merge.py`` mission-number baking)
all run inside the global merge lock
(``acquire_merge_lock("__global_merge__", ...)``), which serializes every
merge operation. This helper therefore acquires NO lock of its own — adding
one would introduce a second lock ordering. Callers outside the merge
pipeline must hold an equivalent serialization guarantee.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class RefAdvanceError(RuntimeError):
    """A branch-ref advance failed at the git level (non-dirty cause)."""

    error_code = "REF_ADVANCE_FAILED"


class RefAdvanceNonFastForwardError(RefAdvanceError):
    """The requested ref advance would move a branch backwards or sideways."""

    error_code = "REF_ADVANCE_NON_FAST_FORWARD"

    def __init__(self, *, branch: str, old_sha: str, new_sha: str) -> None:
        self.branch = branch
        self.old_sha = old_sha
        self.new_sha = new_sha
        super().__init__(
            f"Refusing to advance branch {branch!r} "
            f"({old_sha[:12]} -> {new_sha[:12]}): target is not a "
            "fast-forward descendant of the current branch tip."
        )


@dataclass
class _WorktreeEntry:
    """One ``git worktree list --porcelain`` block."""

    path: Path
    branch: str | None = None
    detached: bool = False
    lines: list[str] = field(default_factory=list)


class RefAdvanceDirtyWorktreeError(RuntimeError):
    """A worktree with the advanced branch checked out holds local state.

    Raised BEFORE the ref is advanced and BEFORE any ``reset --hard`` runs
    (NFR-002: no silent data discard). Carries the full divergence context
    (NFR-003) so operators can resolve without forensic git archaeology.
    """

    error_code = "REF_ADVANCE_DIRTY_WORKTREE"

    def __init__(
        self,
        *,
        worktree_path: Path,
        branch: str,
        old_sha: str,
        new_sha: str,
        dirty_entries: list[str],
    ) -> None:
        self.worktree_path = worktree_path
        self.branch = branch
        self.old_sha = old_sha
        self.new_sha = new_sha
        self.dirty_entries = dirty_entries
        entries = "\n".join(f"    {entry}" for entry in dirty_entries)
        super().__init__(
            f"Refusing to advance branch {branch!r} "
            f"({old_sha[:12]} -> {new_sha[:12]}): the worktree at "
            f"{worktree_path} has it checked out and holds uncommitted local "
            f"changes that a resync (`git reset --hard`) would destroy "
            f"(#1826 / NFR-002).\n"
            f"  Dirty entries:\n{entries}\n"
            f"  Commit, stash, or revert these changes in {worktree_path}, "
            f"then resume the merge (`spec-kitty merge --resume`)."
        )


def _run_git(
    cwd: Path,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _list_worktrees(repo_root: Path, env: dict[str, str] | None) -> list[_WorktreeEntry]:
    """Parse ``git worktree list --porcelain`` into entries."""
    result = _run_git(repo_root, ["worktree", "list", "--porcelain"], env=env)
    if result.returncode != 0:
        raise RefAdvanceError(
            f"Could not enumerate worktrees of {repo_root}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    entries: list[_WorktreeEntry] = []
    current: _WorktreeEntry | None = None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current = _WorktreeEntry(path=Path(line.removeprefix("worktree ")))
            entries.append(current)
        elif current is not None and line.startswith("branch "):
            current.branch = line.removeprefix("branch ")
        elif current is not None and line == "detached":
            current.detached = True
    return entries


def _target_tree_paths(repo_root: Path, new_sha: str, env: dict[str, str] | None) -> set[str]:
    """Return tracked paths present at ``new_sha``."""
    result = _run_git(repo_root, ["ls-tree", "-r", "--name-only", new_sha], env=env)
    if result.returncode != 0:
        raise RefAdvanceError(
            f"Could not inspect target tree {new_sha}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return {line for line in result.stdout.splitlines() if line}


def _porcelain_path(line: str) -> str:
    """Extract the path field from a porcelain v1 status line."""
    path = line[3:]
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    return path.rstrip("/")


def _path_obstructs_target_tree(path: str, target_paths: set[str]) -> bool:
    """Return True when an untracked/ignored path may be clobbered by reset."""
    if not path:
        return False
    prefix = f"{path}/"
    return any(target == path or target.startswith(prefix) for target in target_paths)


def _dirty_entries(
    worktree: Path,
    env: dict[str, str] | None,
    *,
    new_sha: str,
    target_paths: set[str],
    excluded_filenames: frozenset[str] | None = None,
) -> list[str]:
    """Return porcelain entries that a ``reset --hard`` would destroy.

    Most untracked/ignored files survive ``git reset --hard``, but an
    untracked or ignored path that obstructs a tracked path in ``new_sha`` is
    overwritten by git during the reset. Treat those obstructions as local
    state and refuse before moving the ref (NFR-002).

    Everything staged or unstaged against tracked paths is also unique local
    state and blocks the resync.

    Args:
        excluded_filenames: Basenames to exclude from the dirty check.  Used
            to suppress coord-owned residue (e.g. ``status.events.jsonl``,
            ``status.json``) that is legitimately present on the primary
            checkout after a coordination-branch write (#1878 / T041).
    """
    result = _run_git(worktree, ["status", "--porcelain", "--ignored"], env=env)
    if result.returncode != 0:
        raise RefAdvanceError(
            f"Could not inspect worktree state at {worktree}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    dirty: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = _porcelain_path(line)
        if line.startswith(("??", "!!")):
            if excluded_filenames and Path(path).name in excluded_filenames:
                continue
            if _path_obstructs_target_tree(path, target_paths):
                dirty.append(
                    f"{line} (would be overwritten by reset --hard to {new_sha[:12]})"
                )
            continue
        dirty.append(line)
    return dirty


def advance_branch_ref(
    repo_root: Path,
    branch: str,
    new_sha: str,
    *,
    env: dict[str, str] | None = None,
    coord_owned_filenames: frozenset[str] | None = None,
) -> None:
    """Advance ``refs/heads/<branch>`` to ``new_sha`` and resync checkouts.

    Invariant (#1826): **no worktree may be left checked out behind a ref
    this function advanced.** After a successful return, every worktree with
    ``branch`` checked out has HEAD == index == working tree == ``new_sha``
    (CONSISTENT). With no such checkout, behavior is identical to a raw
    ``git update-ref`` plus the worktree scan.

    Order of operations (atomic refusal): all checked-out worktrees are
    dirty-checked BEFORE the ref moves, so a refusal leaves the ref, every
    worktree, and the merge state exactly as found.

    Args:
        repo_root: Primary repository root (where the ref lives).
        branch: Short branch name (no ``refs/heads/`` prefix).
        new_sha: Commit SHA the branch ref advances to.
        env: Optional subprocess environment (merge pipeline passes its
            ``_make_merge_env()`` result through).
        coord_owned_filenames: Basenames that are legitimately present as
            residue on the primary checkout after a coordination-branch write
            (e.g. ``status.events.jsonl``, ``status.json``).  These are
            excluded from the dirty-file check so they do not abort a
            post-write ff-advance (#1878 / T041).  Pass
            ``COORD_OWNED_STATUS_FILES`` from ``specify_cli.status`` here.

    Raises:
        RefAdvanceDirtyWorktreeError: a worktree with ``branch`` checked out
            holds uncommitted tracked changes (NFR-002/NFR-003); nothing was
            mutated.
        RefAdvanceError: the worktree scan, ``update-ref``, or a resync
            failed at the git level.
    """
    ref = f"refs/heads/{branch}"

    old_sha_result = _run_git(repo_root, ["rev-parse", "--verify", "--quiet", ref], env=env)
    old_sha = old_sha_result.stdout.strip() if old_sha_result.returncode == 0 else "<unborn>"

    if old_sha != "<unborn>":
        ff_check = _run_git(
            repo_root,
            ["merge-base", "--is-ancestor", old_sha, new_sha],
            env=env,
        )
        if ff_check.returncode == 1:
            raise RefAdvanceNonFastForwardError(
                branch=branch,
                old_sha=old_sha,
                new_sha=new_sha,
            )
        if ff_check.returncode != 0:
            raise RefAdvanceError(
                f"Could not verify fast-forward ancestry for {branch}: "
                f"{ff_check.stderr.strip() or ff_check.stdout.strip()}"
            )

    checkouts = [
        entry.path
        for entry in _list_worktrees(repo_root, env)
        if not entry.detached and entry.branch == ref
    ]
    target_paths = _target_tree_paths(repo_root, new_sha, env)

    # Dirty check strictly BEFORE the ref mutation and BEFORE any reset path:
    # a refusal must be atomic (nothing advanced, nothing reset).
    for worktree in checkouts:
        dirty = _dirty_entries(
            worktree,
            env,
            new_sha=new_sha,
            target_paths=target_paths,
            excluded_filenames=coord_owned_filenames,
        )
        if dirty:
            raise RefAdvanceDirtyWorktreeError(
                worktree_path=worktree.resolve(),
                branch=branch,
                old_sha=old_sha,
                new_sha=new_sha,
                dirty_entries=dirty,
            )

    result = _run_git(repo_root, ["update-ref", ref, new_sha], env=env)
    if result.returncode != 0:
        raise RefAdvanceError(
            f"Failed to update {branch} ref: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    for worktree in checkouts:
        reset = _run_git(worktree, ["reset", "--hard", branch], env=env)
        if reset.returncode != 0:
            raise RefAdvanceError(
                f"Advanced {branch} ({old_sha[:12]} -> {new_sha[:12]}) but "
                f"failed to resync the checked-out worktree at {worktree}: "
                f"{reset.stderr.strip() or reset.stdout.strip()}. "
                f"The worktree is behind its own HEAD (#1826); repair with "
                f"`git -C {worktree} reset --hard` once the cause is fixed."
            )

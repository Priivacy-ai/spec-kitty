"""Mission-creation helpers for the per-mission coordination branch.

This module owns the **topology** half of issue #1348: every mission gets a
canonical coordination branch ``kitty/mission-<slug>-<mid8>`` parented off the
target branch at creation time. Later work packages (WP04, WP05) build on top
of this — they materialise the coordination *worktree* and the
``BookkeepingTransaction`` — but neither of those can do anything useful until
the branch ref exists. WP03 is the foundation.

Contract
--------

``ensure_coordination_branch()`` is idempotent and structural:

* The branch name is derived deterministically from ``mission_slug`` and the
  mission's ULID via :func:`specify_cli.lanes.branch_naming.mission_branch_name`.
  There is no per-call randomness; re-running mission-create on the same
  mission slug produces the same branch name.

* If the branch does not exist, it is created at the same commit as
  ``target_branch``.

* If the branch already exists *and* is an ancestor of ``target_branch`` (i.e.
  fast-forwardable / already up-to-date with the target), the helper is a
  silent no-op. This is what makes re-running ``agent mission create`` safe.

* If the branch already exists *and* has diverged from ``target_branch``,
  :class:`CoordinationBranchDiverged` is raised with a stable
  ``error_code`` so scripted callers (CI, doctor) can detect and act.

* The ``force_recreate`` flag is an explicit operator escape hatch: when set,
  any existing branch at the coordination name is deleted and re-created at
  ``target_branch``. This is **never** the default — the caller must opt in.

The structured error carries enough data for an operator to fix the situation
without guessing: ``coordination_branch``, ``target_branch``, divergence
point, and a ``next_step`` hint.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from specify_cli.lanes.branch_naming import mid8 as _mid8
from specify_cli.lanes.branch_naming import strip_numeric_prefix

__all__ = [
    "CoordinationBranchDiverged",
    "CoordinationBranchResult",
    "coordination_branch_name",
    "ensure_coordination_branch",
]


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class CoordinationBranchDiverged(RuntimeError):
    """Raised when an existing coordination branch has diverged from the target.

    Carries a stable ``error_code`` (per NFR-007) plus the coordination branch
    name, the target branch name, and an operator-facing ``next_step`` hint.
    """

    error_code = "COORDINATION_BRANCH_DIVERGED"

    def __init__(
        self,
        *,
        coordination_branch: str,
        target_branch: str,
        next_step: str | None = None,
    ) -> None:
        self.coordination_branch = coordination_branch
        self.target_branch = target_branch
        self.next_step = next_step or (
            f"Either rebase '{coordination_branch}' onto '{target_branch}', "
            f"or re-run mission create with --force-recreate-coordination-branch "
            f"to reset the branch to the target."
        )
        super().__init__(
            f"Coordination branch '{coordination_branch}' has diverged from "
            f"target '{target_branch}'. {self.next_step}"
        )

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serialisable representation for structured CLI output."""
        return {
            "error_code": self.error_code,
            "coordination_branch": self.coordination_branch,
            "target_branch": self.target_branch,
            "next_step": self.next_step,
        }


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class CoordinationBranchResult:
    """Outcome of :func:`ensure_coordination_branch`.

    Attributes:
        branch_name: The full branch name (e.g. ``kitty/mission-foo-01ABCDEF``).
        created: ``True`` if the branch was newly created on this call,
            ``False`` if it already existed and was reused.
        force_recreated: ``True`` if the branch existed but was reset via the
            ``force_recreate`` flag.
        skipped_reason: When non-``None``, the branch was *not* materialised on
            disk because preconditions were not met (e.g. ``target_branch``
            does not exist as a local ref).  ``branch_name`` is still the
            canonical name the branch *would* carry, so downstream callers
            (``meta.json``, JSON output) remain self-describing.  WP04 / WP05
            will catch the missing branch at consumption time.
    """

    branch_name: str
    created: bool
    force_recreated: bool = False
    skipped_reason: str | None = None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def coordination_branch_name(mission_slug: str, mission_id: str) -> str:
    """Compute the deterministic coordination branch name for a mission.

    The branch name is ``kitty/mission-<human-slug>-<mid8>`` where ``mid8`` is
    the first 8 characters of ``mission_id`` (a ULID).  The function accepts
    either form of ``mission_slug``:

    * **Formatted** (the on-disk form already containing ``-<mid8>``, e.g.
      ``"my-feature-01KSPTVW"``) — used as-is.
    * **Bare** (no mid8 suffix, e.g. ``"my-feature"``, optionally with a
      legacy ``NNN-`` numeric prefix) — the prefix is stripped and the
      ``-<mid8>`` token is appended.

    This dual-mode keeps the helper safe regardless of whether callers hand it
    the ``meta["mission_slug"]`` (formatted) or a raw bare slug, and avoids
    the ``mission_branch_name`` double-mid8 trap when the formatted form is
    passed.  The ``-coord`` suffix is *not* applied at the branch level (it
    is reserved for the worktree path in WP04, per spec).
    """
    mid8_token = _mid8(mission_id)
    suffix = f"-{mid8_token}"
    if mission_slug.endswith(suffix):
        # Formatted slug already carries the mid8 — use as-is.
        human_part = mission_slug
    else:
        # Bare slug (with or without numeric prefix) — derive the formatted form.
        human_part = f"{strip_numeric_prefix(mission_slug)}{suffix}"
    return f"kitty/mission-{human_part}"


def ensure_coordination_branch(
    *,
    repo_root: Path,
    mission_slug: str,
    mission_id: str,
    target_branch: str,
    force_recreate: bool = False,
) -> CoordinationBranchResult:
    """Mint or validate the coordination branch for a mission.

    Args:
        repo_root: Absolute path to the project root checkout.
        mission_slug: The mission slug (typically the on-disk
            ``<human-slug>-<mid8>`` directory name).
        mission_id: Full mission ULID (used to derive the ``mid8`` segment of
            the branch name).
        target_branch: The branch the coordination branch is parented off of
            (typically the operator's current branch at mission-create time).
        force_recreate: When ``True``, an existing coordination branch is
            deleted and re-created at ``target_branch``. Operator escape hatch.

    Returns:
        CoordinationBranchResult describing the outcome.

    Raises:
        CoordinationBranchDiverged: When the branch already exists, diverges
            from ``target_branch``, and ``force_recreate`` is ``False``.
        RuntimeError: When a git subprocess fails for an unexpected reason.
    """
    branch = coordination_branch_name(mission_slug, mission_id)

    # Guard: if ``target_branch`` does not resolve to a real ref, do not try to
    # create the coordination branch.  The canonical name is still returned
    # (so ``meta.json`` and ``--json`` output are self-describing), and the
    # downstream consumers (WP04 worktree, WP05 transaction) will surface the
    # missing branch when they actually try to use it.  This keeps mission
    # creation usable in synthetic / test contexts where the operator pins a
    # target like ``"2.x"`` that has no on-disk counterpart.
    if not _ref_resolves(repo_root, target_branch):
        return CoordinationBranchResult(
            branch_name=branch,
            created=False,
            skipped_reason=f"target_branch '{target_branch}' does not resolve to a ref",
        )

    existing = _branch_exists(repo_root, branch)

    if existing and force_recreate:
        _delete_branch(repo_root, branch)
        _create_branch(repo_root, branch, target_branch)
        return CoordinationBranchResult(
            branch_name=branch, created=True, force_recreated=True
        )

    if existing:
        if _is_ancestor(repo_root, branch, target_branch):
            # Branch is already at-or-behind target → reusable as-is.
            return CoordinationBranchResult(branch_name=branch, created=False)
        # Existing branch has diverged from the target.
        raise CoordinationBranchDiverged(
            coordination_branch=branch,
            target_branch=target_branch,
        )

    _create_branch(repo_root, branch, target_branch)
    return CoordinationBranchResult(branch_name=branch, created=True)


# ---------------------------------------------------------------------------
# Git plumbing
# ---------------------------------------------------------------------------


def _branch_exists(repo_root: Path, branch: str) -> bool:
    """Return True if a local branch with this name exists."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _ref_resolves(repo_root: Path, ref: str) -> bool:
    """Return True if ``ref`` resolves to a commit in the repo.

    Distinct from :func:`_branch_exists` — this accepts any revspec
    (``main``, ``origin/main``, ``HEAD``, ``2.x``…) and only confirms that
    git can resolve it to a real object.  Used by
    :func:`ensure_coordination_branch` to detect synthetic ``target_branch``
    values that should skip branch creation rather than crash mission
    creation.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _is_ancestor(repo_root: Path, candidate: str, descendant: str) -> bool:
    """Return True if ``candidate`` is an ancestor of (or equal to) ``descendant``.

    Used to decide whether an existing coordination branch is safely reusable
    without recreation: if the existing branch is at or behind the target, the
    next ``BookkeepingTransaction`` (WP05) will simply fast-forward it.
    """
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            candidate,
            descendant,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _create_branch(repo_root: Path, branch: str, parent: str) -> None:
    """Create a new branch parented off ``parent``.

    The branch is created as a plain ref (no checkout). Callers that want a
    worktree on this branch will create it separately (WP04 territory).
    """
    result = subprocess.run(
        ["git", "-C", str(repo_root), "branch", branch, parent],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create coordination branch '{branch}' off '{parent}': "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def _delete_branch(repo_root: Path, branch: str) -> None:
    """Delete a local branch (force). Used by the --force-recreate path only."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "branch", "-D", branch],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to delete coordination branch '{branch}': "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

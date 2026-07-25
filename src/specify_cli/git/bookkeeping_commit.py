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

from mission_runtime import (
    ActionContextError,
    CommitTarget,
    MissionArtifactKind,
    resolve_placement_only,
)

from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.commit_helpers import CommitResult, safe_commit
from specify_cli.missions._read_path_resolver import (
    StatusReadPathNotFound,
    candidate_feature_dir_for_mission,
)

# Mirrors mission_runtime.resolution's private ``_FEATURE_CONTEXT_UNRESOLVED_CODE``
# (not exported at the package root) for the locally-raised unresolvable-mission
# error below.
_FEATURE_CONTEXT_UNRESOLVED_CODE = "FEATURE_CONTEXT_UNRESOLVED"

# coord-write-placement-closure-01KYCF83 WP03 / FR-003: this surface's OWN
# contract (module docstring above) is that BOTH flows land their commit on
# the PRIMARY ``target_branch`` for every topology — never the coordination
# branch. Any PRIMARY-partition kind therefore resolves the identical
# ``target_branch`` ref via :func:`resolve_placement_only`;
# ``PRIMARY_METADATA`` is used as the selector because this surface commits
# mission bookkeeping metadata (status/meta/baseline artifacts, the captured
# retrospective). This is NOT a re-classification of the committed paths —
# it is the fixed partition this seam has always targeted, now derived
# through the placement port instead of an ambient/CWD-derived ref.
_BOOKKEEPING_COMMIT_KIND = MissionArtifactKind.PRIMARY_METADATA


def commit_merge_bookkeeping(
    *,
    repo_root: Path,
    worktree_root: Path,
    mission_slug: str,
    message: str,
    paths: tuple[Path, ...],
    branch: str | None = None,
) -> CommitResult:
    """Commit ``paths`` as an authorized merge-bookkeeping flow.

    The destination ref is resolved through the placement port
    (:func:`mission_runtime.resolve_placement_only`) for ``mission_slug`` —
    NOT an ambient caller-supplied branch string or the checkout's current
    HEAD (coord-write-placement-closure-01KYCF83 WP03 / FR-003: this closes
    the CWD-dependent ``get_current_branch`` fallback the retrospective
    terminus used to compute its destination with).

    Args:
        repo_root: Path to the primary git repository.
        worktree_root: Path to the worktree the commit lands in (may equal
            ``repo_root``).
        mission_slug: The mission slug the bookkeeping commit belongs to —
            resolves the destination via the placement port.
        message: The commit message.
        paths: The exact file paths to stage and commit.
        branch: Optional degrade-path destination used ONLY when the
            placement port cannot resolve ``mission_slug`` (no ``meta.json``
            yet, or an ad-hoc fixture outside a resolvable mission) —
            mirrors the established degrade-path idiom in
            ``coordination.status_transition._resolve_write_target``. When
            omitted and resolution fails, the resolution error propagates.

    Returns:
        The :class:`CommitResult` from :func:`safe_commit`.

    Raises:
        Whatever :func:`safe_commit` raises — callers own their fail-open /
        fail-closed policy. Also propagates the placement resolution error
        when ``mission_slug`` cannot be resolved and no ``branch`` degrade
        path was supplied.
    """
    target = _resolve_bookkeeping_commit_target(repo_root, mission_slug, branch)
    return safe_commit(
        repo_root=repo_root,
        worktree_root=worktree_root,
        target=target,
        message=message,
        paths=paths,
        capability=GuardCapability.MERGE_BOOKKEEPING,
    )


def _mission_meta_exists(repo_root: Path, mission_slug: str) -> bool:
    """Return True when ``mission_slug`` has a primary ``meta.json`` on disk.

    A cheap, read-only existence gate — NOT a ref derivation — that
    distinguishes a genuinely bootstrapped mission from an ad-hoc fixture or
    the create→first-write window. ``resolve_placement_only`` never raises
    for a merely-absent mission (:func:`candidate_feature_dir_for_mission`'s
    own contract): it silently degrades to the repo's generic default branch
    instead of signalling unresolvability, so this gate is checked BEFORE
    consulting the classifier rather than relying on an exception that would
    never fire.
    """
    try:
        # Explicit ``Path`` annotation: under the project's
        # ``follow_imports = "skip"`` mypy config the cross-module
        # ``candidate_feature_dir_for_mission`` return is seen as ``Any``; the
        # annotation re-narrows it (the function IS typed ``-> Path``).
        candidate: Path = candidate_feature_dir_for_mission(repo_root, mission_slug)
    except Exception:  # noqa: BLE001 — any resolution hiccup means "not resolvable"
        return False
    return (candidate / "meta.json").exists()


def _resolve_bookkeeping_commit_target(
    repo_root: Path, mission_slug: str, branch: str | None
) -> CommitTarget:
    """Resolve this surface's commit target via the placement port (FR-003).

    Degrades to ``CommitTarget(ref=branch)`` ONLY when the mission cannot be
    resolved (no ``meta.json`` yet, or an ad-hoc fixture outside a resolvable
    mission) AND a degrade-path ``branch`` was supplied — mirroring
    ``coordination.status_transition._resolve_write_target``. When no
    degrade path is available, an :class:`ActionContextError` is raised (the
    caller decides fail-open/fail-closed policy).
    """
    if not _mission_meta_exists(repo_root, mission_slug):
        if branch is not None:
            return CommitTarget(ref=branch)
        raise ActionContextError(
            _FEATURE_CONTEXT_UNRESOLVED_CODE,
            f"commit_merge_bookkeeping: mission {mission_slug!r} has no "
            "resolvable meta.json and no degrade-path 'branch' was supplied.",
        )
    try:
        return resolve_placement_only(
            repo_root, mission_slug, kind=_BOOKKEEPING_COMMIT_KIND
        )
    except (ActionContextError, StatusReadPathNotFound, FileNotFoundError):
        if branch is not None:
            return CommitTarget(ref=branch)
        raise

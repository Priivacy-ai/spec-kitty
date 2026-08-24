"""Select the repository and mission anchor for a lifecycle operation.

Spec Kitty has two different roots in a linked-worktree invocation:

* the repository root, used for Git topology and branch identity; and
* the caller-owned checkout, where the mission files may actually live.

The old CLI selected only the first root.  That made an explicit mission handle
look missing whenever the command was run from a task-owned worktree.  This
module keeps the two roots explicit and chooses the caller-owned root only when
the requested mission is present there.  If both roots resolve the selector to
different immutable identities, resolution fails closed instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from specify_cli.context.mission_resolver import (
    AmbiguousHandleError,
    MissionNotFoundError,
    ResolvedMission,
    resolve_mission,
)
from specify_cli.core.paths import get_main_repo_root, get_status_read_root


@dataclass(frozen=True, slots=True)
class MissionOperationContext:
    """Roots and identity selected for one read/resolve operation."""

    repository_root: Path
    mission_anchor_root: Path
    identity: ResolvedMission | None


class MissionSurfaceConflictError(RuntimeError):
    """Raised when primary and caller-owned surfaces disagree on identity."""

    def __init__(self, primary: ResolvedMission, caller: ResolvedMission) -> None:
        self.primary = primary
        self.caller = caller
        super().__init__(
            "Mission selector resolves to different identities in the primary "
            f"checkout ({primary.mission_slug}, {primary.mission_id}) and the "
            "caller-owned checkout "
            f"({caller.mission_slug}, {caller.mission_id}); refusing to guess."
        )


_AMBIGUOUS: Final = object()


def _probe(root: Path, selector: str) -> ResolvedMission | None | object:
    """Probe one root without turning a not-found miss into a hard failure."""

    try:
        return resolve_mission(selector, root)
    except MissionNotFoundError:
        return None
    except AmbiguousHandleError:
        # Let the canonical CLI resolver render the stable ambiguity diagnostic
        # after the correct root has been selected.
        return _AMBIGUOUS


def resolve_mission_operation_context(
    repository_root: Path,
    selector: str,
    *,
    cwd: Path | None = None,
) -> MissionOperationContext:
    """Resolve a mission while preserving caller-owned linked-worktree state.

    ``repository_root`` is the canonical Git root (normally from
    :func:`locate_project_root`).  The current worktree is considered only when
    it belongs to that same repository.  A worktree with no matching mission is
    not allowed to shadow the primary checkout.
    """

    primary_root = get_main_repo_root(repository_root).resolve()
    caller_root = get_status_read_root(cwd).resolve()

    primary_probe = _probe(primary_root, selector)
    if caller_root == primary_root or get_main_repo_root(caller_root).resolve() != primary_root:
        return MissionOperationContext(
            primary_root,
            primary_root,
            primary_probe if isinstance(primary_probe, ResolvedMission) else None,
        )

    caller_probe = _probe(caller_root, selector)
    if (
        isinstance(primary_probe, ResolvedMission)
        and isinstance(caller_probe, ResolvedMission)
        and primary_probe.mission_id != caller_probe.mission_id
    ):
        raise MissionSurfaceConflictError(primary_probe, caller_probe)

    selected = caller_probe if caller_probe is not None else primary_probe
    if isinstance(selected, ResolvedMission):
        return MissionOperationContext(
            primary_root,
            caller_root if caller_probe is not None else primary_root,
            selected,
        )

    # ``resolve_mission_handle`` is responsible for the user-facing diagnostic.
    # The identity field is only unreachable on a miss/ambiguous selector; keep
    # the function total for the CLI's follow-up canonical resolution.
    return MissionOperationContext(
        primary_root,
        caller_root if caller_probe is not None else primary_root,
        None,
    )


__all__ = [
    "MissionOperationContext",
    "MissionSurfaceConflictError",
    "resolve_mission_operation_context",
]

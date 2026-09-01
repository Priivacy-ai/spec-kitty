"""Mission retention-contract enforcement for merge cleanup."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from mission_runtime import MissionArtifactKind, placement_seam

MISSION_RETENTION_CLEANUP_CONFLICT = "MISSION_RETENTION_CLEANUP_CONFLICT"
_CONSTRAINT_ROW_ID = re.compile(r"^C-\d+$", re.IGNORECASE)
_NEGATED_RETENTION = re.compile(
    r"\b(?:do not|must not|never)\b[^.;\n]*\b(?:keep|retain|preserve)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MissionRetention:
    """An accepted mission constraint that retains merge cleanup artifacts."""

    constraint_id: str
    constraint: str


def load_mission_retention(repo_root: Path, mission_slug: str) -> MissionRetention | None:
    """Read the mission's canonical spec and return its retention constraint.

    Only an ``Accepted`` constraint row can retain cleanup artifacts. Returning
    ``None`` means either no spec exists or no accepted retention constraint is
    present; both retain the historical cleanup defaults.
    """

    spec_path = placement_seam(repo_root, mission_slug).read_dir(MissionArtifactKind.SPEC) / "spec.md"
    if not spec_path.is_file():
        return None

    for row in spec_path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        if not _CONSTRAINT_ROW_ID.fullmatch(cells[0]):
            continue
        if cells[-1].casefold() != "accepted":
            continue
        if _is_retention_constraint(cells[2]):
            return MissionRetention(constraint_id=cells[0], constraint=cells[2])
    return None


def _is_retention_constraint(constraint: str) -> bool:
    lowered = constraint.casefold()
    if _NEGATED_RETENTION.search(constraint):
        return False
    has_retention_verb = any(word in lowered for word in ("keep", "retain", "preserve"))
    has_branch = "branch" in lowered or "branches" in lowered
    has_worktree = "worktree" in lowered or "worktrees" in lowered
    has_merge_timing = any(phrase in lowered for phrase in ("after merge", "after merging", "post-merge"))
    return has_retention_verb and has_branch and has_worktree and has_merge_timing


def retention_cleanup_conflicts(
    retention: MissionRetention | None,
    *,
    delete_branch: bool | None,
    remove_worktree: bool | None,
) -> tuple[str, ...]:
    """Return cleanup fields whose default value conflicts with retention.

    ``None`` means the operator omitted the bidirectional flag. An explicit
    ``--keep-*`` choice honors retention; an explicit ``--delete-branch`` or
    ``--remove-worktree`` choice is the separately directed override allowed by
    the mission constraint.
    """

    if retention is None:
        return ()
    conflicts: list[str] = []
    if delete_branch is None:
        conflicts.append("branch")
    if remove_worktree is None:
        conflicts.append("worktree")
    return tuple(conflicts)

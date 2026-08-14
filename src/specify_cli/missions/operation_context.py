"""Resolve one Mission identity and checkout context for a lifecycle request.

The repository root remains the Git/topology anchor. The Mission anchor may be
an explicit root, a Spec Kitty managed checkout, or a caller-owned linked
worktree. Resolution is read-only and fails closed when allowed surfaces carry
different immutable Mission identities.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

from specify_cli.context.mission_resolver import (
    FakeMissionResolver,
    FsMissionResolver,
    MissionNotFoundError,
    ResolvedMission,
    resolve_mission,
)
from specify_cli.coordination.surface_resolver import (
    WorktreeTopology,
    classify_worktree_topology,
)
from specify_cli.core.constants import KITTIFY_DIR
from specify_cli.core.paths import (
    _nearest_checkout_root,
    get_main_repo_root,
    git_common_dir_for_checkout,
    is_worktree_context,
)


class CheckoutKind(StrEnum):
    """Provenance of the selected Mission anchor."""

    EXPLICIT = "explicit"
    MANAGED = "managed"
    CALLER_OWNED = "caller_owned"
    REPOSITORY_ROOT = "repository_root"


@dataclass(frozen=True)
class MissionOperationContext:
    """Dual-root identity context shared by Mission lifecycle consumers."""

    repository_root: Path
    mission_anchor_root: Path
    identity: ResolvedMission
    checkout_kind: CheckoutKind

    @property
    def mission_id(self) -> str:
        return cast(str, self.identity.mission_id)

    @property
    def mission_slug(self) -> str:
        return cast(str, self.identity.mission_slug)


@dataclass(frozen=True)
class MissionConflictCandidate:
    """Safe diagnostic projection of a conflicting Mission surface."""

    root: Path
    mission_id: str
    mission_slug: str


class MissionSurfaceConflictError(RuntimeError):
    """Raised before writes when allowed surfaces disagree on Mission identity."""

    error_code = "MISSION_SURFACE_CONFLICT"

    def __init__(
        self,
        *,
        selector: str,
        candidates: tuple[MissionConflictCandidate, ...],
    ) -> None:
        self.selector = selector
        self.candidates = candidates
        roots = ", ".join(str(candidate.root) for candidate in candidates)
        super().__init__(f"{self.error_code}: selector {selector!r} resolves to conflicting Mission identities across: {roots}")

    def to_dict(self) -> dict[str, object]:
        """Return a stable, secret-free CLI diagnostic payload."""
        return {
            "error": self.error_code,
            "selector": self.selector,
            "candidates": [
                {
                    "root": str(candidate.root),
                    "mission_id": candidate.mission_id,
                    "mission_slug": candidate.mission_slug,
                }
                for candidate in self.candidates
            ],
        }


@dataclass(frozen=True)
class _Candidate:
    root: Path
    kind: CheckoutKind
    selectable: bool = True


@dataclass(frozen=True)
class _IndexedCandidate:
    candidate: _Candidate
    missions: tuple[ResolvedMission, ...]


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _same_git_identity(left: Path, right: Path) -> bool:
    left_common = git_common_dir_for_checkout(left)
    right_common = git_common_dir_for_checkout(right)
    if left_common is None or right_common is None:
        return False
    return _path_key(left_common) == _path_key(right_common)


def _deduplicate_candidates(candidates: list[_Candidate]) -> list[_Candidate]:
    unique: list[_Candidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = _path_key(candidate.root)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _implicit_candidates(
    repository_root: Path,
    cwd: Path,
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    current_checkout = _nearest_checkout_root(cwd)
    if (
        current_checkout is not None
        and current_checkout != repository_root
        and (current_checkout / KITTIFY_DIR).is_dir()
        and _same_git_identity(repository_root, current_checkout)
    ):
        topology = classify_worktree_topology(
            current_checkout,
            repo_root=repository_root,
        )
        if topology in {
            WorktreeTopology.COORD_WORKTREE,
            WorktreeTopology.LANE_WORKTREE,
        }:
            # Managed topology keeps the repository-root checkout as the
            # PRIMARY Mission anchor. The current managed checkout remains a
            # conflict probe only, so a stale copy cannot hide split-brain.
            candidates.append(_Candidate(repository_root, CheckoutKind.MANAGED))
            candidates.append(
                _Candidate(
                    current_checkout,
                    CheckoutKind.MANAGED,
                    selectable=False,
                )
            )
        elif topology is WorktreeTopology.PRIMARY and is_worktree_context(current_checkout):
            candidates.append(_Candidate(current_checkout, CheckoutKind.CALLER_OWNED))

    candidates.append(_Candidate(repository_root, CheckoutKind.REPOSITORY_ROOT))
    return _deduplicate_candidates(candidates)


def _index_candidate(candidate: _Candidate) -> _IndexedCandidate:
    missions = tuple(FsMissionResolver(candidate.root).all_missions())
    return _IndexedCandidate(candidate=candidate, missions=missions)


def _resolve_from_index(
    indexed: _IndexedCandidate,
    selector: str,
) -> ResolvedMission | None:
    try:
        return resolve_mission(
            selector,
            indexed.candidate.root,
            resolver=FakeMissionResolver(list(indexed.missions)),
        )
    except MissionNotFoundError:
        return None


def _conflict_projection(
    indexed: list[_IndexedCandidate],
    resolved: list[tuple[_IndexedCandidate, ResolvedMission]],
) -> tuple[MissionConflictCandidate, ...]:
    relevant: dict[tuple[str, str], MissionConflictCandidate] = {}
    selected_slugs = {mission.mission_slug for _, mission in resolved}
    for source, mission in resolved:
        projection = MissionConflictCandidate(
            root=source.candidate.root,
            mission_id=mission.mission_id,
            mission_slug=mission.mission_slug,
        )
        relevant[(_path_key(projection.root), projection.mission_id)] = projection
    for source in indexed:
        for mission in source.missions:
            if mission.mission_slug not in selected_slugs:
                continue
            projection = MissionConflictCandidate(
                root=source.candidate.root,
                mission_id=mission.mission_id,
                mission_slug=mission.mission_slug,
            )
            relevant[(_path_key(projection.root), projection.mission_id)] = projection
    return tuple(
        sorted(
            relevant.values(),
            key=lambda candidate: (
                _path_key(candidate.root),
                candidate.mission_id,
                candidate.mission_slug,
            ),
        )
    )


def resolve_mission_operation_context(
    project_root: Path,
    selector: str,
    *,
    cwd: Path | None = None,
    explicit_root: bool = False,
) -> MissionOperationContext:
    """Resolve the immutable Mission identity and its two checkout roots.

    ``explicit_root`` narrows resolution to ``project_root``. Otherwise the
    current same-repository managed/caller-owned worktree is considered before
    the repository-root fallback. All candidate indexes are built once.
    """
    explicit_anchor = _nearest_checkout_root(project_root) or project_root.resolve()
    repository_root = get_main_repo_root(explicit_anchor).resolve()
    candidates = [_Candidate(explicit_anchor, CheckoutKind.EXPLICIT)] if explicit_root else _implicit_candidates(repository_root, (cwd or Path.cwd()).resolve())
    indexed = [_index_candidate(candidate) for candidate in candidates]
    resolved = [(candidate, mission) for candidate in indexed if (mission := _resolve_from_index(candidate, selector)) is not None]
    if not resolved:
        raise MissionNotFoundError(selector)

    conflict_candidates = _conflict_projection(indexed, resolved)
    if len({candidate.mission_id for candidate in conflict_candidates}) > 1:
        raise MissionSurfaceConflictError(
            selector=selector,
            candidates=conflict_candidates,
        )

    selectable = [
        (source, mission)
        for source, mission in resolved
        if source.candidate.selectable
    ]
    if not selectable:
        raise MissionNotFoundError(selector)
    selected_source, selected_mission = selectable[0]
    return MissionOperationContext(
        repository_root=repository_root,
        mission_anchor_root=selected_source.candidate.root,
        identity=selected_mission,
        checkout_kind=selected_source.candidate.kind,
    )

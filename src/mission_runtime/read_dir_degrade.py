"""Shared read-dir degrade helper (FR-006, #3462).

Read-side companion to
:func:`mission_runtime.write_target_degrade.resolve_write_target_or_degrade`.
Where the write helper unifies "resolve a commit target, or degrade to a caller
ref", this one unifies "resolve a read directory via the placement seam, or
degrade to a caller-supplied directory / re-raise".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from mission_runtime.artifacts import MissionArtifactKind
from mission_runtime.resolution import placement_seam

__all__ = [
    "ReadDegradeStrategy",
    "ReadDirDecision",
    "resolve_read_dir_or_degrade",
]

_LOGGER = logging.getLogger(__name__)


class ReadDegradeStrategy(Enum):
    """The caller's declared fallback contract when resolution raises a caught error."""

    DEGRADE_TO_FEATURE_DIR = "degrade_to_feature_dir"
    ZERO_EVIDENCE = "zero_evidence"
    FAIL_CLOSED = "fail_closed"


_DEGRADE_TO_TARGET: frozenset[ReadDegradeStrategy] = frozenset(
    {
        ReadDegradeStrategy.DEGRADE_TO_FEATURE_DIR,
        ReadDegradeStrategy.ZERO_EVIDENCE,
    }
)


@dataclass(frozen=True)
class ReadDirDecision:
    """The resolved read directory plus whether the strategy's fallback was applied."""

    read_dir: Path
    degraded: bool
    strategy: ReadDegradeStrategy


def resolve_read_dir_or_degrade(
    repo_root: Path,
    mission_slug: str,
    kind: MissionArtifactKind,
    *,
    strategy: ReadDegradeStrategy,
    caught: tuple[type[BaseException], ...],
    degrade_target: Path | None = None,
) -> ReadDirDecision:
    """Resolve the read directory for ``kind`` via the placement seam, or degrade."""
    try:
        resolved = placement_seam(repo_root, mission_slug).read_dir(kind)
    except caught as exc:
        if strategy is ReadDegradeStrategy.FAIL_CLOSED:
            raise
        return _degrade(mission_slug, kind, strategy, degrade_target, exc)
    return ReadDirDecision(read_dir=resolved, degraded=False, strategy=strategy)


def _degrade(
    mission_slug: str,
    kind: MissionArtifactKind,
    strategy: ReadDegradeStrategy,
    degrade_target: Path | None,
    exc: BaseException,
) -> ReadDirDecision:
    """Apply a non-fail-closed degrade: validate the target, log, return the decision."""
    if strategy not in _DEGRADE_TO_TARGET:
        raise ValueError(f"Unsupported read degrade strategy: {strategy!r}")
    if degrade_target is None:
        raise ValueError(
            f"resolve_read_dir_or_degrade: strategy {strategy.name} requires a "
            f"degrade_target, but none was supplied for mission {mission_slug!r}."
        )
    _LOGGER.warning(
        "Read surface for mission %s (kind=%s) unreachable: %s. Degrading via %s to %s "
        "(this omission may hide real content; see #1848).",
        mission_slug,
        kind.name,
        exc,
        strategy.name,
        degrade_target,
    )
    return ReadDirDecision(read_dir=degrade_target, degraded=True, strategy=strategy)

"""Shared read-dir degrade helper (FR-006, #3462).

Read-side companion to :func:`mission_runtime.write_target_degrade.resolve_write_target_or_degrade`.
Where the write helper unifies "resolve a commit target, or degrade to a caller ref", this one unifies
"resolve a read directory via the placement seam, or degrade to a caller-supplied directory / re-raise".

The two genuine resolve-then-degrade consumers this helper serves (contracts/read-dir-degrade.md):

* ``specify_cli.retrospective.generator._load_traces`` — ``ZERO_EVIDENCE``: a deleted-coord tracer
  surface degrades to a zero-evidence read (the caller returns an empty trace list), logged at WARNING.
* ``specify_cli.core.worktree_topology.materialize_worktree_topology`` — ``DEGRADE_TO_FEATURE_DIR``:
  an unreachable STATUS_STATE surface degrades ``status_feature_dir`` back to the primary ``feature_dir``.

The ``FAIL_CLOSED`` pass-through sites (``agent/status.py``) and the bespoke sites
(``status/aggregate.py``'s #1848 re-raise ordering, ``_review_cycle_reconcile_doctor.py``'s
absorb-before-read) are NOT migrated onto this seam — they are parked on the WP3 allowlist.

Layering (CRITICAL — else ``tests/architectural/test_layer_rules.py`` reds): ``mission_runtime`` may not
import ``specify_cli.*`` at module scope. This module needs NO ``specify_cli`` symbol at all: the typed
resolution errors it degrades on are passed IN by each caller via ``caught`` (so it catches them by the
caller's own tuple, never by importing them), and resolution goes through the in-layer
:func:`mission_runtime.resolution.placement_seam`. The sibling ``write_target_degrade.py`` DOES carry
function-scoped ``specify_cli`` imports (it ``isinstance``-discriminates to preserve ``error_code``); this
read helper has no such need, so it stays cleanly within-layer and adds nothing to the layer-rules ledger.

See spec: FR-006; contract: contracts/read-dir-degrade.md (INV-R1..R3); data model: ``ReadDirDecision`` /
``ReadDegradeStrategy``.
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
    """The caller's declared fallback contract when resolution raises a ``caught`` error."""

    DEGRADE_TO_FEATURE_DIR = "degrade_to_feature_dir"
    ZERO_EVIDENCE = "zero_evidence"
    FAIL_CLOSED = "fail_closed"


# Strategies that return the caller-supplied ``degrade_target`` (i.e. NOT ``FAIL_CLOSED``).
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
    """Resolve the read directory for ``kind`` via the placement seam, or degrade.

    Resolution is attempted FIRST regardless of ``strategy`` — a resolvable surface is always
    returned (``degraded=False``), even for ``FAIL_CLOSED`` callers. The strategy's fallback applies
    ONLY when resolution raises an exception whose type is in ``caught``:

    * a degrade strategy (``DEGRADE_TO_FEATURE_DIR`` / ``ZERO_EVIDENCE``) returns
      ``ReadDirDecision(read_dir=degrade_target, degraded=True, ...)`` and
      logs at WARNING (evidence/authority loss is operator-visible, not a silent substitution);
    * ``FAIL_CLOSED`` re-raises the caught exception verbatim (its traceback and ``error_code`` intact).

    An exception whose type is NOT in ``caught`` propagates verbatim (never swallowed). This is how the
    #1848 data-loss contract is preserved: a site whose ``caught`` set excludes ``CoordinationBranchDeleted``
    lets that data-loss subclass surface as ``COORDINATION_BRANCH_DELETED`` instead of degrading.

    Args:
        repo_root: The git repository root the placement seam resolves against.
        mission_slug: The mission slug to resolve the read surface for.
        kind: The artifact kind (drives partition/topology routing inside the seam).
        strategy: The caller's declared fallback contract.
        caught: The exception types this call degrades (or fail-closes) on. Types outside this tuple
            propagate verbatim.
        degrade_target: The directory returned when a degrade strategy fires. Required for every
            strategy except ``FAIL_CLOSED``; passing ``None`` there is a caller error.

    Returns:
        ``ReadDirDecision`` with the resolved surface (``degraded=False``) or the degrade target
        (``degraded=True``).

    Raises:
        The caught exception verbatim under ``FAIL_CLOSED``; any resolution exception outside ``caught``
        verbatim; ``ValueError`` when a degrade strategy fires with no ``degrade_target``.
    """
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
    """Apply a (non-fail-closed) degrade: validate the target, log at WARNING, return the decision."""
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

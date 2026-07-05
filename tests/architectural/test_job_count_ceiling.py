"""NFR-005 — quality-gate job-count ceiling invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 (red-first). Promoting worklist
dirs to dedicated ``fast/integration-tests-<D>`` jobs would balloon
``quality-gate.needs``; the plan caps growth with **composite** filter groups so
the aggregate stays under a pinned ceiling (NFR-005).

``CEILING`` is pinned from the plan's composite design (``plan.md`` Complexity
Tracking: "~32 dedicated jobs balloon ``quality-gate.needs`` (~45 today) past the
NFR-005 ceiling; composites cap it (~57)"). Today the count is ~45, comfortably
under 57, so the live assertion is GREEN. Because this relation could pass
vacuously, a fault-injection test proves it BITES when the graph exceeds the
ceiling.

Consumes only the additive WP01 parse surface; it does not re-derive the model.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_CI_QUALITY = "ci-quality.yml"
_QUALITY_GATE = "quality-gate"

# Pinned from plan.md (Complexity Tracking): composite groups cap
# len(quality-gate.needs) at ~57 vs the ~45 baseline. A post-WP03 graph must
# stay at or under this ceiling.
CEILING = 57


def _within_ceiling(needs: Sequence[str], ceiling: int) -> bool:
    """Pure ceiling predicate (fault-injectable): the graph fits under ``ceiling``."""
    return len(needs) <= ceiling


def _quality_gate_needs() -> tuple[str, ...]:
    model = gc.load_workflow_models()[_CI_QUALITY]
    return model.job_needs[_QUALITY_GATE]


def test_quality_gate_needs_within_ceiling() -> None:
    """GREEN today: len(quality-gate.needs) stays at or under the pinned ceiling."""
    needs = _quality_gate_needs()
    assert _within_ceiling(needs, CEILING), (
        f"len(quality-gate.needs)={len(needs)} exceeds the NFR-005 ceiling {CEILING}"
    )


def test_ceiling_leaves_headroom_for_composite_design() -> None:
    """The pinned ceiling sits above today's baseline (composites add headroom)."""
    assert CEILING == 57  # noqa: PLR2004 — the plan-pinned composite-design ceiling
    assert len(_quality_gate_needs()) < CEILING


def test_ceiling_relation_bites_when_graph_exceeds_it() -> None:
    """Fault-injection: a synthetic over-ceiling graph reds the relation.

    The synthetic size (``CEILING + 1``) proves the predicate bites without
    hard-coding the live job count into the assertion's meaning.
    """
    over_ceiling = tuple(f"job-{index}" for index in range(CEILING + 1))
    assert not _within_ceiling(over_ceiling, CEILING), (
        "ceiling predicate failed to red on a graph that exceeds the ceiling"
    )

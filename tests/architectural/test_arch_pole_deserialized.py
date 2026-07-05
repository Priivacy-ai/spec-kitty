"""FR-013 — architectural pole de-serialization invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 (red-first). The arch/adversarial
suite must run **in parallel** with the fast lane. Today it runs as the
``architectural`` matrix shard of ``integration-tests-core-misc``, whose
``needs: [changes, fast-tests-core-misc]`` serializes it behind the fast lane —
and ``if: always()`` does NOT de-serialize it (``always()`` only relaxes the
*result* gate; the job still waits on ``fast-tests-core-misc``'s timeline before
starting). Only DROPPING the ``needs`` edge de-serializes it (FR-013).

This pins the BEHAVIORAL relation: the parsed ``needs`` set of every job that
runs the architectural suite contains **no fast-lane job** (a job whose name
starts with ``fast-tests``). It is a NATURAL RED today (the serialization edge
is present) and flips GREEN when WP03 extracts the always-on arch pole. Never
pins a workflow line number.

Consumes only the additive WP01 parse surfaces; it does not re-derive the model.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_ARCH_MARKER = "architectural"
_FAST_LANE_PREFIX = "fast-tests"


def _arch_running_jobs() -> set[tuple[str, str]]:
    """``(workflow, job)`` pairs whose gate positively selects the arch marker."""
    return {
        (gate.workflow, gate.job)
        for gate in gc.load_gates()
        if _ARCH_MARKER in gc.positive_marker_tokens(gate.marker_expr)
    }


def test_architectural_suite_has_a_running_job() -> None:
    """Guard against a vacuous relation: some job runs the arch/adversarial suite."""
    assert _arch_running_jobs(), "no job positively selects the architectural marker"


def test_arch_pole_needs_no_fast_lane_job() -> None:
    """RED today: the arch job's ``needs`` set contains no fast-lane job.

    ``integration-tests-core-misc`` (which runs the arch shard today) declares
    ``needs: [changes, fast-tests-core-misc]`` — a fast-lane serialization edge.
    WP03's standalone always-on arch pole drops it.
    """
    models = gc.load_workflow_models()
    serialized: dict[str, list[str]] = {}
    for workflow, job in sorted(_arch_running_jobs()):
        needs = models[workflow].job_needs.get(job, ())
        fast_lane = sorted(n for n in needs if n.startswith(_FAST_LANE_PREFIX))
        if fast_lane:
            serialized[f"{workflow}::{job}"] = fast_lane
    assert not serialized, (
        "arch-running jobs still serialized behind a fast lane via needs "
        f"(pre-WP03 RED): {serialized}"
    )

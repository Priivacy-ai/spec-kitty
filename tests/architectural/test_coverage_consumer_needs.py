"""Coverage-producing jobs remain connected to real consumers.

Authority: open CI-integrity epic #1931 and the accepted CI dependency/test
surface ADR (2026-05-28).  Only live graph oracles remain.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = pytest.mark.architectural

_CONSUMERS = gc.NON_EMITTER_JOBS
_ORDERING_NEEDS = frozenset({"changes", "lint"})


def _src_emitters(model: gc.WorkflowModel) -> set[str]:
    return {
        job
        for job, targets in model.cov_targets.items()
        if job not in _CONSUMERS
        and any(gc.is_src_cov_target(target) for target in targets)
    }


def test_src_coverage_emitters_reach_sonarcloud() -> None:
    model = gc.load_workflow_models()["ci-quality.yml"]
    emitters = _src_emitters(model)
    assert emitters, "no source-coverage emitters parsed"
    dropped = sorted(emitters - set(model.job_needs["sonarcloud"]))
    assert not dropped, f"coverage emitters absent from sonarcloud.needs: {dropped}"


def test_coverage_consumers_depend_only_on_emitters() -> None:
    model = gc.load_workflow_models()["ci-quality.yml"]
    emitters = {
        job for job, targets in model.cov_targets.items() if targets
    } - _CONSUMERS
    assert emitters, "no coverage emitters parsed"
    for consumer in ("diff-coverage", "mutation-testing"):
        phantom = sorted(
            need
            for need in model.job_needs[consumer]
            if need not in _ORDERING_NEEDS and need not in emitters
        )
        assert not phantom, f"{consumer}.needs non-emitting jobs: {phantom}"

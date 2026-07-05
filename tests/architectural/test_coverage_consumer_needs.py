"""C-005 / FR-006 / FR-007 — coverage-consumer integrity invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 (red-first). A ``fast-tests-<D>``
(or the new always-on arch job) that emits a ``--cov`` XML but is forgotten from
a coverage consumer's ``needs:`` silently drops its coverage. This binds, by
construction:

* every **src-coverage-emitting** job is in ``sonarcloud.needs`` (the aggregator
  that collects every upstream coverage XML); and
* the coverage-consumer binding targets ``sonarcloud`` / ``diff-coverage`` — it
  must **NOT** be bound to ``slow-tests.needs`` (a fast-jobs-only ordering list;
  binding coverage integrity to it would red on arrival — the spec's explicit
  C-005 correction).

Authored FAILING against today's topology: ``mission-loader-coverage`` emits
``--cov=src/specify_cli/mission_loader`` and uploads its XML, yet is absent from
``sonarcloud.needs`` — a genuine coverage-consumer drop of exactly the C-005
class. WP03 (sole owner of ``ci-quality.yml``) closes it and adds the new
composite / arch emitters to the consumer lists.

The strict "critical-path emitters ⊆ ``diff-coverage.needs``" direction is NOT
asserted as a hard subset: today diff-coverage draws critical-path coverage from
a deliberate *mix* of fast and integration providers (e.g. ``fast-tests-charter``
but ``integration-tests-status``), so a naive subset would false-red on
intentional redundancy (Directive 041). Instead the diff-coverage / mutation
binding is guarded from the safe direction — every consumer ``needs`` entry is a
real coverage emitter (no phantom dependency).

Consumes only the additive WP01 parse surfaces; it does not re-derive the model.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_CI_QUALITY = "ci-quality.yml"
_SRC_PREFIX = "src/"
# Jobs that *consume* coverage rather than emit it; excluded from the emitter set
# (a consumer need not list itself). ``sonarcloud`` also carries a documentation
# ``--cov=src/<package>`` placeholder in its script that is not a real emitter.
_CONSUMER_JOBS = frozenset({"sonarcloud", "diff-coverage", "mutation-testing"})
# Graph-ordering / non-test needs that legitimately emit no coverage XML.
_ORDERING_NEEDS = frozenset({"changes", "lint"})


@pytest.fixture(scope="module")
def ci_model() -> gc.WorkflowModel:
    """The parsed ``ci-quality.yml`` relation model (needs + cov targets)."""
    return gc.load_workflow_models()[_CI_QUALITY]


def _src_cov_emitters(model: gc.WorkflowModel) -> set[str]:
    """Jobs emitting a ``--cov`` target under ``src/`` (excluding consumer jobs)."""
    emitters: set[str] = set()
    for job, targets in model.cov_targets.items():
        if job in _CONSUMER_JOBS:
            continue
        if any(target.startswith(_SRC_PREFIX) for target in targets):
            emitters.add(job)
    return emitters


def test_emitter_set_is_non_empty(ci_model: gc.WorkflowModel) -> None:
    """Guard against a vacuous subset: real src-coverage emitters exist."""
    assert _src_cov_emitters(ci_model), "no src-coverage emitters parsed"


def test_src_coverage_emitters_are_sonarcloud_consumers(
    ci_model: gc.WorkflowModel,
) -> None:
    """RED today: every src-coverage emitter is in ``sonarcloud.needs``.

    ``mission-loader-coverage`` emits ``src/specify_cli/mission_loader`` coverage
    but is missing from ``sonarcloud.needs`` today — its XML is dropped from the
    aggregator (the C-005 defect class).
    """
    emitters = _src_cov_emitters(ci_model)
    consumed = set(ci_model.job_needs["sonarcloud"])
    dropped = sorted(emitters - consumed)
    assert not dropped, (
        "src-coverage emitters absent from sonarcloud.needs (pre-WP03 RED, "
        f"{len(dropped)}): {dropped}"
    )


def test_coverage_binding_is_not_slow_tests_needs(
    ci_model: gc.WorkflowModel,
) -> None:
    """C-005 correction (GREEN): coverage integrity is NOT bound to slow-tests.

    ``slow-tests.needs`` lists fast jobs only; integration-tier emitters are
    absent from it, so binding the coverage-consumer subset to ``slow-tests``
    would red on arrival. This asserts that wrong target is genuinely wrong —
    the emitter set is not a subset of ``slow-tests.needs``.
    """
    emitters = _src_cov_emitters(ci_model)
    slow_needs = set(ci_model.job_needs["slow-tests"])
    assert not emitters <= slow_needs, (
        "src-coverage emitters are a subset of slow-tests.needs — the C-005 "
        "correction (bind to sonarcloud/diff-coverage, never slow-tests) is moot"
    )


def test_diff_coverage_and_mutation_needs_are_real_emitters(
    ci_model: gc.WorkflowModel,
) -> None:
    """Phantom-needs guard (GREEN): each coverage consumer waits only on emitters.

    Every ``diff-coverage`` / ``mutation-testing`` dependency (ordering jobs
    aside) must actually emit a ``--cov`` XML — otherwise the consumer blocks on
    a job that provides no coverage. Guards the future arch/composite additions
    from the safe direction without the false-red risk of a strict critical-path
    subset.
    """
    all_emitters = {
        job for job, targets in ci_model.cov_targets.items() if targets
    } - _CONSUMER_JOBS
    for consumer in ("diff-coverage", "mutation-testing"):
        phantom = sorted(
            need
            for need in ci_model.job_needs[consumer]
            if need not in _ORDERING_NEEDS and need not in all_emitters
        )
        assert not phantom, (
            f"{consumer}.needs entries that emit no coverage XML: {phantom}"
        )

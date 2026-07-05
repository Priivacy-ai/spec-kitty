"""SC-003a — catch-all shard-universe boundedness invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 (red-first). Same-tier uniqueness
(NFR-003) alone does NOT prove the catch-all monolith was split: one giant shard
trivially satisfies uniqueness. This closes that gap — over the parsed
shard-command set, NO single shard may collect the **full** catch-all universe
of its job.

For each catch-all job (the ``core-misc`` family, plus ``arch-adversarial``
since mission ``ci-health-charter-path-and-arch-shard-01KWRTB2`` / #2397 —
see below), the "catch-all universe" is the union of tests its shards select;
the invariant is that the largest single shard selects strictly fewer tests
than that union (i.e. the job is genuinely sharded). Today ``fast-tests-core-misc``
is a single, unsharded monolith that collects its whole ~11k-test catch-all
universe, so this is a NATURAL RED; WP03's matrix split of the fast core-misc
job flips it GREEN. ``integration-tests-core-misc`` is already a 6-shard matrix
and passes.

The relation is pinned over the parsed shards + selection, never a line number.
Consumes only the additive WP01 substrate; it does not re-derive the model.

Mission ``ci-health-charter-path-and-arch-shard-01KWRTB2`` (#2397): before this
mission, ``arch-adversarial`` was a SINGLE-shard job (``shard: architectural``)
that this guard's catch-all scope did not recognize at all (jobs were matched
only by the ``"core-misc"`` substring) — so sharding it without extending this
guard would have shipped FR-005 (union = full universe, no drops, no
double-counts) gate-unmasked (charter Standing Order 5: "a gate-unmask cannot
self-validate"). ``arch-adversarial`` is named EXPLICITLY below (not folded
into a looser substring match) so this mechanism can never silently absorb an
unrelated future job. Authored FAILING against the pre-split single-shard
``arch-adversarial`` topology (one shard trivially collects its whole
catch-all universe), mirroring this file's own WP02 red-first discipline; the
mission's 3-shard (``arch_shard_1/2/3``) matrix split flips it GREEN.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

# The catch-all job family: jobs whose name contains this substring absorb every
# test not owned by a dedicated shard (fast-tests-core-misc / integration-tests-
# core-misc). This is the stable structural handle the whole model uses.
_CATCH_ALL_SUBSTR = "core-misc"

# The always-on arch/adversarial pole (mission
# ci-health-charter-path-and-arch-shard-01KWRTB2, #2397) — named explicitly
# (not merged into a broader substring) so extending this guard's coverage can
# never silently widen to absorb an unrelated future job.
_ARCH_ADVERSARIAL_JOB = "arch-adversarial"


def _is_catch_all_job(job: str) -> bool:
    """True for a job this guard treats as part of the catch-all family."""
    return _CATCH_ALL_SUBSTR in job or job == _ARCH_ADVERSARIAL_JOB


@pytest.fixture(scope="module")
def gates() -> list[gc.Gate]:
    """All parsed CI selection gates."""
    return gc.load_gates()


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    """Every collected test with its marker set (one ``--collect-only`` pass)."""
    return gc.collect_universe()


def _shard_key(gate: gc.Gate) -> str:
    return gate.shard if gate.shard is not None else "<single>"


def _catch_all_shard_universes(
    gates: list[gc.Gate],
    universe: list[gc.TestRecord],
) -> dict[str, dict[str, set[str]]]:
    """``job -> shard -> selected nodeids`` for every catch-all job."""
    catch_all = [gate for gate in gates if _is_catch_all_job(gate.job)]
    compiled = [(gc.CompiledGate(gate), gate) for gate in catch_all]
    result: dict[str, dict[str, set[str]]] = {}
    for test in universe:
        relpath, nodeid, markers = test["relpath"], test["nodeid"], set(test["markers"])
        for compiled_gate, gate in compiled:
            if compiled_gate.selects(relpath, nodeid, markers):
                shard_map = result.setdefault(gate.job, {})
                shard_map.setdefault(_shard_key(gate), set()).add(nodeid)
    return result


def test_catch_all_jobs_are_present(gates: list[gc.Gate]) -> None:
    """Guard against a vacuous relation: the catch-all family exists."""
    jobs = {gate.job for gate in gates if _is_catch_all_job(gate.job)}
    assert jobs, (
        f"no catch-all ({_CATCH_ALL_SUBSTR!r} substring or "
        f"{_ARCH_ADVERSARIAL_JOB!r}) jobs parsed"
    )


def test_no_single_shard_collects_the_full_catch_all_universe(
    gates: list[gc.Gate],
    universe: list[gc.TestRecord],
) -> None:
    """RED today: no catch-all job is a single shard holding its whole universe.

    ``fast-tests-core-misc`` is one unsharded shard whose selection equals the
    full fast catch-all universe today, so its ``max_shard == |universe|`` and
    this REDS until WP03 (ci-topology-shrink) matrix-splits it.

    ``arch-adversarial`` joined the catch-all family in mission
    ci-health-charter-path-and-arch-shard-01KWRTB2 (#2397): before that
    mission's WP03 split it into ``arch_shard_1/2/3``, it was a single
    ``architectural`` shard whose selection also equalled its whole catch-all
    universe — this assertion is RED against that pre-split topology (proving
    it is genuinely exercised, not vacuous) and GREEN once the 3-shard split
    lands.
    """
    monolithic: dict[str, dict[str, int]] = {}
    for job, shard_map in _catch_all_shard_universes(gates, universe).items():
        job_universe = set().union(*shard_map.values()) if shard_map else set()
        if not job_universe:
            continue
        max_single = max(len(selected) for selected in shard_map.values())
        if max_single >= len(job_universe):
            monolithic[job] = {
                "max_single_shard": max_single,
                "job_catch_all_universe": len(job_universe),
                "shard_count": len(shard_map),
            }
    assert not monolithic, (
        "catch-all jobs where one shard collects the full catch-all universe "
        f"(pre-WP03 RED): {monolithic}"
    )

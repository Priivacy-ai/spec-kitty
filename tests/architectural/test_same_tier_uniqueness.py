"""NFR-003 / SC-004 — same-tier shard-selection uniqueness invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 (red-first). Asserts no test is
selected by **> 1 fast shard** nor by **> 1 integration shard** (over the WP01
same-tier relation :func:`_gate_coverage.same_tier_shard_counts`) — distinct
from the existing *report-only* cross-tier duplicate warning. The split must
also drop no test (``orphan_count`` stays 0, SC-004).

Authored FAILING against today's topology: nested ``tests/specify_cli/<D>``
roots and the ``fast-tests-core-misc`` / ``fast-tests-docs`` overlap cause
pervasive same-tier double-runs today, so the uniqueness assertions RED until
WP03 consolidates the shard roots. A fault-injection test additionally proves
the relation BITES on a synthetic double-run, independent of the live suite
size.

Consumes only the additive WP01 relation; it does not re-derive the model.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_MAX_SHARDS_PER_TIER = 1
_SAMPLE_LIMIT = 8


@pytest.fixture(scope="module")
def gates() -> list[gc.Gate]:
    """All parsed CI selection gates across the four suite-running workflows."""
    return gc.load_gates()


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    """Every collected test with its marker set (one ``--collect-only`` pass)."""
    return gc.collect_universe()


def test_no_test_selected_by_multiple_fast_shards(
    gates: list[gc.Gate],
    universe: list[gc.TestRecord],
) -> None:
    """RED today: each test is selected by at most one fast-tier shard."""
    counts = gc.same_tier_shard_counts(gates, universe)
    offenders = sorted(
        nid
        for nid, count in counts.items()
        if count["count_fast_shards"] > _MAX_SHARDS_PER_TIER
    )
    assert not offenders, (
        f"tests selected by >1 fast shard (pre-WP03 RED, {len(offenders)}); "
        f"sample: {offenders[:_SAMPLE_LIMIT]}"
    )


def test_no_test_selected_by_multiple_integration_shards(
    gates: list[gc.Gate],
    universe: list[gc.TestRecord],
) -> None:
    """RED today: each test is selected by at most one integration-tier shard."""
    counts = gc.same_tier_shard_counts(gates, universe)
    offenders = sorted(
        nid
        for nid, count in counts.items()
        if count["count_integration_shards"] > _MAX_SHARDS_PER_TIER
    )
    assert not offenders, (
        f"tests selected by >1 integration shard (pre-WP03 RED, {len(offenders)}); "
        f"sample: {offenders[:_SAMPLE_LIMIT]}"
    )


def test_split_preserves_zero_orphans(
    gates: list[gc.Gate],
    universe: list[gc.TestRecord],
) -> None:
    """SC-004 no-drop floor (GREEN): the selection covers every test (0 orphans)."""
    report = gc.analyze(gates, universe)
    assert report.orphan_count == 0, (
        f"orphaned tests (selected by 0 gates): {report.orphan_nodeids[:_SAMPLE_LIMIT]}"
    )


def test_same_tier_relation_bites_on_synthetic_double_run() -> None:
    """Fault-injection: the relation flags a test in two fast shards.

    Two synthetic fast-tier gates select the same synthetic test; the relation
    must report ``count_fast_shards == 2`` — proving the uniqueness check bites
    regardless of the live suite. The synthetic size stays out of the assertion's
    meaning (no live census count is hard-coded).
    """
    double_run_test: gc.TestRecord = {
        "nodeid": "tests/synthetic/test_double.py::test_a",
        "relpath": "tests/synthetic/test_double.py",
        "markers": ["fast"],
    }
    shard_a = gc.Gate(
        workflow="synthetic",
        job="fast-tests-alpha",
        shard=None,
        paths=["tests/synthetic/"],
        marker_expr="fast",
    )
    shard_b = gc.Gate(
        workflow="synthetic",
        job="fast-tests-beta",
        shard=None,
        paths=["tests/synthetic/"],
        marker_expr="fast",
    )
    counts = gc.same_tier_shard_counts([shard_a, shard_b], [double_run_test])
    fault = {
        nid: count
        for nid, count in counts.items()
        if count["count_fast_shards"] > _MAX_SHARDS_PER_TIER
    }
    assert fault, "same-tier relation failed to flag a synthetic fast double-run"

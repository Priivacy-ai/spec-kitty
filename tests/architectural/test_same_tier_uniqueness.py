"""NFR-003 / SC-004 — same-tier shard-selection uniqueness invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02. Asserts no test is selected by
**> 1 fast shard** nor by **> 1 integration shard** (over the WP01 same-tier
relation :func:`_gate_coverage.same_tier_shard_counts`) — distinct from the
existing *report-only* cross-tier duplicate warning. The split must also drop
no test (``orphan_count`` stays 0, SC-004).

The invariant holds today: WP03 consolidated the shard roots, and it is
GREEN on ``main``. One fast-tier gate, ``fast-tests-corpus`` (#3008), is a
deliberate exception — it re-runs ``@pytest.mark.corpus`` reader tests under
a data-path trigger that is disjoint from the home shards' code-path
triggers, so its overlap with a home shard is intentional redundancy, not a
same-tier double-run. It is carved out of the uniqueness PEER set via
``_TRIGGER_DISJOINT_FAST_JOBS`` below; the invariant still bites on a test
selected by >= 2 *non-corpus* fast shards. Durable NFR-003 model
reconciliation (folding the overlay concept into the same-tier relation
itself) is tracked in #3315.

A fault-injection test additionally proves the relation BITES on a synthetic
double-run, independent of the live suite size.

Consumes only the additive WP01 relation; it does not re-derive the model.

Retired (planning#57): the three LIVE checks above (``test_no_test_selected_by_multiple_fast_shards``,
``test_no_test_selected_by_multiple_integration_shards``, ``test_split_preserves_zero_orphans``)
asserted the relation against ``_gate_coverage.load_gates()``, which parses the
real ``.github/workflows/*.yml`` — the leftover pre-programme GitHub Actions
YAML deleted per PROGRAM.md §2. With no workflow YAML left to parse, that half
(and the now-unused ``gates``/``universe`` fixtures backing it) has no
remaining subject matter and was removed with the files. The fault-injection
tests below never read a real workflow — each builds its OWN synthetic
``gc.Gate``/``gc.TestRecord`` objects — and stay as non-fakeable evidence that
``gc.same_tier_shard_counts`` itself still catches a planted same-tier
double-run.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_MAX_SHARDS_PER_TIER = 1

# fast-tests-corpus (#3008) re-runs @pytest.mark.corpus readers under a
# data-path trigger disjoint from the home shards' code-path triggers, so its
# overlap with a home shard is intentional redundancy, not a same-tier
# double-run; excluded from the uniqueness PEER set. Durable NFR-003
# reconciliation tracked in #3315.
_TRIGGER_DISJOINT_FAST_JOBS = frozenset({"fast-tests-corpus"})


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


def test_same_tier_exemption_is_narrow_not_a_blanket_pass() -> None:
    """The corpus-overlay exemption is scoped, not a blanket suppression.

    Two synthetic gates: one home fast shard and one trigger-disjoint overlay
    gate (job name in ``_TRIGGER_DISJOINT_FAST_JOBS``) both select the same
    synthetic test — after the overlay is filtered from the peer set (exactly
    as the real assertion filters it), that test must NOT be flagged, because
    corpus-plus-one-home-shard is the intentional, accepted overlap shape.

    A second synthetic test is selected by two *non-corpus* home fast shards;
    that double-run must still be flagged after the same filtering — proving
    the exemption only swallows the corpus overlay, not genuine same-tier
    double-runs.
    """
    corpus_only_overlap_test: gc.TestRecord = {
        "nodeid": "tests/synthetic/corpus_case/test_corpus_overlap.py::test_a",
        "relpath": "tests/synthetic/corpus_case/test_corpus_overlap.py",
        "markers": ["fast", "corpus"],
    }
    genuine_double_run_test: gc.TestRecord = {
        "nodeid": "tests/synthetic/genuine_case/test_genuine_double.py::test_b",
        "relpath": "tests/synthetic/genuine_case/test_genuine_double.py",
        "markers": ["fast"],
    }
    # home_shard covers both synthetic cases; other_home_shard covers only the
    # genuine-double-run case, so the corpus case is selected by exactly one
    # home shard (plus the overlay), while the genuine case is selected by
    # two home shards regardless of the overlay.
    home_shard = gc.Gate(
        workflow="synthetic",
        job="fast-tests-alpha",
        shard=None,
        paths=["tests/synthetic/corpus_case/", "tests/synthetic/genuine_case/"],
        marker_expr="fast",
    )
    other_home_shard = gc.Gate(
        workflow="synthetic",
        job="fast-tests-beta",
        shard=None,
        paths=["tests/synthetic/genuine_case/"],
        marker_expr="fast",
    )
    corpus_overlay = gc.Gate(
        workflow="synthetic",
        job="fast-tests-corpus",
        shard=None,
        paths=["tests/synthetic/corpus_case/"],
        marker_expr="corpus",
    )

    gates = [home_shard, other_home_shard, corpus_overlay]
    universe = [corpus_only_overlap_test, genuine_double_run_test]

    peer_gates = [g for g in gates if g.job not in _TRIGGER_DISJOINT_FAST_JOBS]
    counts = gc.same_tier_shard_counts(peer_gates, universe)

    assert (
        counts["tests/synthetic/corpus_case/test_corpus_overlap.py::test_a"][
            "count_fast_shards"
        ]
        <= _MAX_SHARDS_PER_TIER
    ), (
        "corpus-overlay-plus-one-home-shard overlap must not be flagged "
        "once the overlay is excluded from the peer set"
    )
    assert (
        counts["tests/synthetic/genuine_case/test_genuine_double.py::test_b"][
            "count_fast_shards"
        ]
        > _MAX_SHARDS_PER_TIER
    ), "a genuine two-non-corpus-home-shard double-run must still be flagged"

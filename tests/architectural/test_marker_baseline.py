"""GC-5 — marker-baseline stability guard (C-005).

Mission ``ci-test-topology-performance-01KXBJRT`` WP04. Replaces spec
constraint C-005's unfalsifiable "no marker moved purely to hit a budget"
intent clause with an enforced baseline diff: the committed
``tests/architectural/marker_baseline.txt`` snapshots today's exact
``@slow``/``@stress``/``@quarantine``-marked node-id set (via a real
collection, ``tests.architectural._gate_coverage.collect_universe()`` — the
existing collect-only helper already used by
``test_arch_shard_marker_completeness.py`` / ``test_same_tier_uniqueness.py``
/ ``test_shard_universe_bounded.py``, reused here rather than hand-rolling a
second collector), and this guard asserts the *live* set does not GROW
against it during this mission.

Deliberately **not** a hard membership-equality check: the invariant is
"count/identity does not grow", not "does not change". A test being removed,
or a node-id being renamed because the underlying test file moved, is
allowed and does not fail this guard — WP06 (or any later WP in this
mission) may legitimately rename/rescope files without adding new
slow/stress/quarantine-marked tests. Only *growth* — a currently-collected
node-id that was not already in the committed baseline — fails it, because
that is exactly the signal C-005 exists to catch: a test re-marked
``@slow``/``@stress``/``@quarantine`` purely to dodge a CI time budget rather
than because it is genuinely one of those tiers.

If baseline regeneration is ever legitimately required later in this mission
(e.g. a test is discovered to be mis-marked and should be re-tiered),
regenerate ``marker_baseline.txt`` deliberately with a comment noting *why* —
never silently, per this same invariant's own regenerate-on-legitimate-change
policy (mirrors E3's baseline-manifest invariant in ``data-model.md``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_TARGET_MARKERS = frozenset({"slow", "stress", "quarantine"})
_BASELINE_PATH = Path(__file__).with_name("marker_baseline.txt")
_SAMPLE_LIMIT = 10


def _load_baseline(path: Path = _BASELINE_PATH) -> frozenset[str]:
    """Committed node-id set, ignoring blank lines and ``#``-prefixed comments."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(
        stripped
        for line in lines
        if (stripped := line.strip()) and not stripped.startswith("#")
    )


def marker_selected_node_ids(universe: list[gc.TestRecord]) -> frozenset[str]:
    """Pure: node-ids of every collected test carrying @slow/@stress/@quarantine."""
    return frozenset(
        test["nodeid"] for test in universe if _TARGET_MARKERS & set(test["markers"])
    )


def growth_violations(current: frozenset[str], baseline: frozenset[str]) -> list[str]:
    """C-005: the marker-selected set must not GROW vs the committed baseline.

    Every currently-collected node-id must already be present in the
    baseline; a shrink (baseline entries with no current counterpart) is not
    a violation — only the set difference ``current - baseline`` (genuine
    additions) is.
    """
    return sorted(current - baseline)


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    """Every collected test with its marker set (one ``--collect-only`` pass)."""
    return gc.collect_universe()


def test_baseline_file_is_non_empty() -> None:
    """Anti-vacuous canary: an empty/corrupted baseline must not pass this
    guard green by having nothing to grow against.
    """
    baseline = _load_baseline()
    assert baseline, "marker_baseline.txt is empty — GC-5 guard would be vacuous"


def test_marker_set_does_not_grow_vs_baseline(universe: list[gc.TestRecord]) -> None:
    current = marker_selected_node_ids(universe)
    assert current, "collection found zero @slow/@stress/@quarantine tests — guard would be vacuous"
    baseline = _load_baseline()
    violations = growth_violations(current, baseline)
    assert not violations, (
        f"@slow/@stress/@quarantine marker set GREW vs the committed baseline "
        f"({len(violations)} new node-id(s), showing up to {_SAMPLE_LIMIT}): "
        f"{violations[:_SAMPLE_LIMIT]}. If this growth is a genuine new "
        f"slow/stress/quarantine test (not a budget-motivated re-mark), "
        f"regenerate tests/architectural/marker_baseline.txt deliberately with "
        f"a comment noting why — see this module's docstring."
    )


def test_fault_injection_growth_bites() -> None:
    """A synthetic 'current' set with one extra node-id not in the baseline
    must red the core comparison function.
    """
    baseline = frozenset({"tests/foo.py::test_a", "tests/bar.py::test_b"})
    current = frozenset({"tests/foo.py::test_a", "tests/bar.py::test_b", "tests/baz.py::test_new_slow"})
    violations = growth_violations(current, baseline)
    assert violations == ["tests/baz.py::test_new_slow"], (
        "checker missed a genuinely grown node-id"
    )


def test_fault_injection_shrink_is_not_a_violation() -> None:
    """Removing a baseline entry (test deleted, or node-id renamed because the
    underlying test moved) must NOT be flagged — only growth fails this guard.
    """
    baseline = frozenset({"tests/foo.py::test_a", "tests/bar.py::test_removed"})
    current = frozenset({"tests/foo.py::test_a"})
    assert not growth_violations(current, baseline), (
        "checker incorrectly flagged a shrink (removed node-id) as growth"
    )


def test_fault_injection_identical_sets_pass() -> None:
    baseline = frozenset({"tests/foo.py::test_a"})
    assert not growth_violations(baseline, baseline), (
        "checker flagged an unchanged set as growth"
    )

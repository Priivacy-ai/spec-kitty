"""IC-03 — arch-adversarial shard-marker completeness invariant (FR-005).

Mission ``ci-health-charter-path-and-arch-shard-01KWRTB2`` WP02 (red-first,
#2397). This closes the FR-005 gap the post-plan brownfield adversarial squad
flagged: the shard mechanism (marker registration + assignment table +
collection hook) must PROVE the partition it applies is total, not just claim
it by convention.

Authored FAILING against today's topology: before ``tests/conftest.py``'s
``pytest_collection_modifyitems`` hook is extended to apply
``arch_shard_1``/``arch_shard_2``/``arch_shard_3`` from
``tests/_arch_shard_map.shard_for()``, NO collected test under the 4 pole
roots (``tests/adversarial``, ``tests/architectural``, ``tests/architecture``,
``tests/lint``) carries any ``arch_shard_N`` marker — every one of the two
invariants below is a NATURAL RED. Wiring the hook (T006) flips both GREEN.

Two invariants, both required by ``data-model.md``'s shard-assignment-table
entity:

1. **Total partition** — every test collected under the 4 pole roots carries
   **exactly one** ``arch_shard_N`` marker (no gaps, no double-assignment).
2. **Union = full pre-split universe** — the union of the three
   marker-selected node-ID sets equals the full set of tests collected under
   the 4 roots (no test falls outside all three).

Reuses ``tests/architectural/_gate_coverage.py``'s ``collect_universe()`` (one
shared ``--collect-only`` pass) rather than re-deriving a second full
collection walk.
"""

from __future__ import annotations

import pytest

from tests import _arch_shard_map as shard_map
from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_ARCH_SHARD_MARKERS: tuple[str, ...] = ("arch_shard_1", "arch_shard_2", "arch_shard_3")


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    """Every collected test with its marker set (one ``--collect-only`` pass)."""
    return gc.collect_universe()


def _under_pole_roots(relpath: str) -> bool:
    normalized = relpath.replace("\\", "/")
    return any(
        normalized == root or normalized.startswith(f"{root}/")
        for root in shard_map.POLE_ROOTS
    )


def _pole_root_records(universe: list[gc.TestRecord]) -> list[gc.TestRecord]:
    return [test for test in universe if _under_pole_roots(test["relpath"])]


def test_pole_root_universe_is_nonempty(universe: list[gc.TestRecord]) -> None:
    """Guard against a vacuous relation: the 4 pole roots collect real tests."""
    records = _pole_root_records(universe)
    assert records, (
        "no test collected under any of the 4 pole roots "
        f"({', '.join(shard_map.POLE_ROOTS)}) — the completeness guard would "
        "otherwise pass vacuously"
    )


def test_every_pole_root_test_has_exactly_one_shard_marker(
    universe: list[gc.TestRecord],
) -> None:
    """Total partition: every pole-root test carries exactly one arch_shard_N mark.

    RED today: no ``arch_shard_N`` marker exists on any collected test until
    the T006 collection hook is wired. Fails loudly, naming every offending
    node ID, on zero marks (unmarked) or on more than one (double-assigned).
    """
    unmarked: list[str] = []
    double_marked: dict[str, list[str]] = {}
    for test in _pole_root_records(universe):
        applied = sorted(set(test["markers"]) & set(_ARCH_SHARD_MARKERS))
        if len(applied) == 0:
            unmarked.append(test["nodeid"])
        elif len(applied) > 1:
            double_marked[test["nodeid"]] = applied

    assert not unmarked, (
        f"{len(unmarked)} pole-root test(s) carry NO arch_shard_N marker "
        "(assignment gap — add the missing unit to tests/_arch_shard_map.py):\n"
        + "\n".join(sorted(unmarked)[:20])
        + ("\n... (truncated)" if len(unmarked) > 20 else "")
    )
    assert not double_marked, (
        f"{len(double_marked)} pole-root test(s) carry MORE THAN ONE "
        "arch_shard_N marker (double-assignment — a unit is listed under two "
        "shards in tests/_arch_shard_map.py):\n"
        + "\n".join(f"{nid}: {marks}" for nid, marks in sorted(double_marked.items())[:20])
    )


def test_shard_union_equals_full_pole_root_universe(
    universe: list[gc.TestRecord],
) -> None:
    """Union of the three shard-selected node-ID sets equals the full universe.

    RED today for the same reason as above: with zero markers applied, every
    shard's selected set is empty, so the union is empty while the full
    pole-root universe is not.
    """
    pole_root_nodeids = {test["nodeid"] for test in _pole_root_records(universe)}
    shard_union: set[str] = set()
    for test in _pole_root_records(universe):
        if set(test["markers"]) & set(_ARCH_SHARD_MARKERS):
            shard_union.add(test["nodeid"])

    missing = pole_root_nodeids - shard_union
    assert not missing, (
        f"{len(missing)} pole-root test(s) are collected but selected by NO "
        "arch_shard_N marker (union does not equal the full pre-split "
        "universe, FR-005):\n" + "\n".join(sorted(missing)[:20])
    )
    # union can never exceed the pole-root universe: every arch_shard_N-marked
    # test in `universe` was filtered by `_pole_root_records` already, so a
    # strict equality check doubles as a paranoia assertion.
    assert shard_union == pole_root_nodeids

"""GC-1 — shard-marker completeness invariant, per group (FR-002/FR-005).

Originated as IC-03's arch-adversarial-only guard (mission
``ci-health-charter-path-and-arch-shard-01KWRTB2`` WP02, red-first, #2397):
this closed the FR-005 gap the post-plan brownfield adversarial squad flagged
— the shard mechanism (marker registration + assignment table + collection
hook) must PROVE the partition it applies is total, not just claim it by
convention.

Generalized (mission ``ci-test-topology-performance-01KXBJRT`` WP01,
FR-002/C-003/D-044): the three invariant-checking bodies below are
**group-parametrized helpers** — ``group: str`` selects the
:data:`tests._arch_shard_map.SHARD_GROUPS` row to check — so this file's own
``arch`` tests and the sibling ``test_next_shard_marker_completeness.py``'s
``next`` tests share one guard engine, not two near-identical copies. The
helpers are public (module-level, no leading underscore) precisely so the
sibling file can import and call them with ``group="next"``.

Authored FAILING against the pre-generalization topology: before
``tests/conftest.py``'s ``pytest_collection_modifyitems`` hook applies
``arch_shard_1``/``arch_shard_2``/``arch_shard_3`` from
``tests/_arch_shard_map.shard_for()``, NO collected test under the 4 arch pole
roots (``tests/adversarial``, ``tests/architectural``, ``tests/architecture``,
``tests/lint``) carries any ``arch_shard_N`` marker — every one of the two
invariants below is a NATURAL RED. Wiring the hook flips both GREEN.

Two invariants, both required by ``data-model.md``'s shard-assignment-table
entity (GC-1):

1. **Total partition** — every test collected under a group's roots carries
   **exactly one** ``<marker_prefix>_N`` marker (no gaps, no
   double-assignment).
2. **Union = full pre-split universe** — the union of the shard-selected
   node-ID sets equals the full set of tests collected under the group's
   roots (no test falls outside all shards).

Reuses ``tests/architectural/_gate_coverage.py``'s ``collect_universe()`` (one
shared ``--collect-only`` pass) rather than re-deriving a second full
collection walk.
"""

from __future__ import annotations

import pytest

from tests import _arch_shard_map as shard_map
from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_MAX_REPORTED_OFFENDERS = 20


def _group_markers(group: str) -> frozenset[str]:
    """The ``<marker_prefix>_1..shard_count`` marker names for *group*."""
    spec = shard_map.SHARD_GROUPS[group]
    return frozenset(
        f"{spec.marker_prefix}_{n}" for n in range(1, spec.shard_count + 1)
    )


def _under_group_roots(group: str, relpath: str) -> bool:
    spec = shard_map.SHARD_GROUPS[group]
    normalized = relpath.replace("\\", "/")
    return any(
        normalized == root or normalized.startswith(f"{root}/")
        for root in spec.roots
    )


def _group_root_records(
    group: str, universe: list[gc.TestRecord],
) -> list[gc.TestRecord]:
    return [test for test in universe if _under_group_roots(group, test["relpath"])]


def assert_group_root_universe_is_nonempty(
    group: str, universe: list[gc.TestRecord],
) -> None:
    """Guard against a vacuous relation: the group's roots collect real tests."""
    records = _group_root_records(group, universe)
    roots = shard_map.SHARD_GROUPS[group].roots
    assert records, (
        f"no test collected under any of group {group!r}'s roots "
        f"({', '.join(roots)}) — the completeness guard would otherwise pass "
        "vacuously"
    )


def assert_every_group_root_test_has_exactly_one_shard_marker(
    group: str, universe: list[gc.TestRecord],
) -> None:
    """Total partition: every group-root test carries exactly one shard mark.

    RED before the collection hook applies ``<marker_prefix>_N``: no such
    marker exists on any collected test. Fails loudly, naming every offending
    node ID, on zero marks (unmarked) or on more than one (double-assigned).
    """
    markers = _group_markers(group)
    unmarked: list[str] = []
    double_marked: dict[str, list[str]] = {}
    for test in _group_root_records(group, universe):
        applied = sorted(set(test["markers"]) & markers)
        if len(applied) == 0:
            unmarked.append(test["nodeid"])
        elif len(applied) > 1:
            double_marked[test["nodeid"]] = applied

    assert not unmarked, (
        f"{len(unmarked)} test(s) under group {group!r} carry NO shard marker "
        f"(assignment gap — add the missing unit to the {group!r} row's shard "
        "map):\n"
        + "\n".join(sorted(unmarked)[:_MAX_REPORTED_OFFENDERS])
        + ("\n... (truncated)" if len(unmarked) > _MAX_REPORTED_OFFENDERS else "")
    )
    assert not double_marked, (
        f"{len(double_marked)} test(s) under group {group!r} carry MORE THAN "
        "ONE shard marker (double-assignment — a unit is listed under two "
        f"shards in the {group!r} row's shard map):\n"
        + "\n".join(
            f"{nid}: {marks}"
            for nid, marks in sorted(double_marked.items())[:_MAX_REPORTED_OFFENDERS]
        )
    )


def assert_shard_union_equals_full_group_root_universe(
    group: str, universe: list[gc.TestRecord],
) -> None:
    """Union of the shard-selected node-ID sets equals the full group universe.

    RED for the same reason as above: with zero markers applied, every
    shard's selected set is empty, so the union is empty while the full
    group-root universe is not.
    """
    markers = _group_markers(group)
    records = _group_root_records(group, universe)
    root_nodeids = {test["nodeid"] for test in records}
    shard_union = {
        test["nodeid"] for test in records if set(test["markers"]) & markers
    }

    missing = root_nodeids - shard_union
    assert not missing, (
        f"{len(missing)} test(s) under group {group!r} are collected but "
        "selected by NO shard marker (union does not equal the full "
        f"pre-split universe, GC-1):\n"
        + "\n".join(sorted(missing)[:_MAX_REPORTED_OFFENDERS])
    )
    # union can never exceed the group-root universe: every marked test in
    # `universe` was filtered by `_group_root_records` already, so a strict
    # equality check doubles as a paranoia assertion.
    assert shard_union == root_nodeids


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    """Every collected test with its marker set (one ``--collect-only`` pass)."""
    return gc.collect_universe()


def test_pole_root_universe_is_nonempty(universe: list[gc.TestRecord]) -> None:
    assert_group_root_universe_is_nonempty("arch", universe)


def test_every_pole_root_test_has_exactly_one_shard_marker(
    universe: list[gc.TestRecord],
) -> None:
    assert_every_group_root_test_has_exactly_one_shard_marker("arch", universe)


def test_shard_union_equals_full_pole_root_universe(
    universe: list[gc.TestRecord],
) -> None:
    assert_shard_union_equals_full_group_root_universe("arch", universe)

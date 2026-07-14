"""GC-1 — shard-marker completeness invariant, per group (FR-002/FR-005).

Originated as IC-03's arch-adversarial-only guard (mission
``ci-health-charter-path-and-arch-shard-01KWRTB2`` WP02, red-first, #2397):
this closed the FR-005 gap the post-plan brownfield adversarial squad flagged
— the shard mechanism (marker registration + assignment table + collection
hook) must PROVE the partition it applies is total, not just claim it by
convention.

Generalized (mission ``ci-test-topology-performance-01KXBJRT`` WP01,
FR-002/C-003/D-044): the three invariant-checking bodies below are
**group-parametrized helpers** — ``group: str`` selects the registered
:class:`tests._shard_registry.ShardGroup` row to check — so this file's own
``arch`` tests and the sibling ``test_next_shard_marker_completeness.py``'s
``next`` tests share one guard engine, not two near-identical copies. The
helpers are public (module-level, no leading underscore) precisely so the
sibling file can import and call them with ``group="next"``.

Authored FAILING against the pre-generalization topology: before
``tests/conftest.py``'s ``pytest_collection_modifyitems`` hook applies
``arch_shard_1``/``arch_shard_2``/``arch_shard_3`` from
``tests/_shard_registry.shard_for()``, NO collected test under the 4 arch pole
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

Mission ``test-suite-friction-remediation-01KXDKBX`` WP16 (FR-011, #2621)
replaced the direct ``tests._arch_shard_map.SHARD_GROUPS[group]`` dict
indexing this file used with ``tests._shard_registry.get_group(group)``: a
group named in :data:`tests._shard_registry.EXPECTED_GROUPS` (the manifest of
groups that MUST be registered) but not actually registered now fails with a
diagnosable "group `<name>` not registered" message
(:class:`tests._shard_registry.ShardGroupNotRegisteredError`) instead of a
bare ``KeyError`` — see :func:`test_expected_groups_are_all_registered` and
the T079 regressions below.

Reuses ``tests/architectural/_gate_coverage.py``'s ``collect_universe()`` (one
shared ``--collect-only`` pass) rather than re-deriving a second full
collection walk.
"""

from __future__ import annotations

import pytest

from tests import _shard_registry as shard_registry
from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_MAX_REPORTED_OFFENDERS = 20


def _group_markers(group: str) -> frozenset[str]:
    """The ``<marker_prefix>_1..shard_count`` marker names for *group*."""
    spec = shard_registry.get_group(group)
    return frozenset(
        f"{spec.marker_prefix}_{n}" for n in range(1, spec.shard_count + 1)
    )


def _under_group_roots(group: str, relpath: str) -> bool:
    spec = shard_registry.get_group(group)
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
    roots = shard_registry.get_group(group).roots
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


# ---------------------------------------------------------------------------
# T077/T079 — diagnosable-message + unmarked-universe regressions (FR-011,
# #2621). These prove the seam's failure mode directly, without depending on
# whether every real row-owner module happens to be imported in this test
# run: a missing registration must never surface as a bare ``KeyError``, and
# a test collected under a group's roots with zero shard markers must never
# be silently treated as "covered."


def test_expected_groups_are_all_registered() -> None:
    """Every :data:`shard_registry.EXPECTED_GROUPS` manifest entry resolves.

    Operationalizes the contract's first invariant directly against the REAL
    shared registry: if a manifest group (``arch``, ``next``) were ever left
    unregistered — e.g. a row-owner module's import got dropped from
    ``tests/conftest.py`` — this fails with the diagnosable
    ``ShardGroupNotRegisteredError`` message, naming the missing group,
    instead of a downstream bare ``KeyError`` somewhere else.
    """
    for name in sorted(shard_registry.EXPECTED_GROUPS):
        shard_registry.get_group(name)


def test_removed_registration_fails_with_diagnosable_message() -> None:
    """(T079a) A group missing from the registry fails diagnosably, not KeyError.

    Simulates "the ``_next_shard_map`` registration was dropped" using an
    ISOLATED :class:`shard_registry.ShardRegistry` (only ``arch`` registered,
    ``next`` never registered) rather than mutating the real shared registry
    — this asserts on the exact message text, not merely that *some*
    exception is raised.
    """
    isolated = shard_registry.ShardRegistry()
    isolated.register(
        shard_registry.ShardGroup(
            group="arch",
            roots=("tests/architectural",),
            shard_count=1,
            marker_prefix="arch_shard",
        )
    )

    with pytest.raises(
        shard_registry.ShardGroupNotRegisteredError,
        match=r"group `next` not registered",
    ) as excinfo:
        isolated.get_group("next")

    assert not isinstance(excinfo.value, KeyError)


def test_duplicate_key_registration_with_different_definition_is_rejected() -> None:
    """A second, DIFFERENT ``ShardGroup`` under an already-used key is rejected.

    Contrasted with idempotent re-registration of the identical group, which
    must be a silent no-op (order-independent assembly).
    """
    isolated = shard_registry.ShardRegistry()
    original = shard_registry.ShardGroup(
        group="arch", roots=("tests/architectural",), shard_count=1,
        marker_prefix="arch_shard",
    )
    isolated.register(original)

    # Idempotent: re-registering the SAME definition is a no-op.
    isolated.register(original)
    assert isolated.all_groups() == {"arch": original}

    # Rejected: a DIFFERENT definition under the same key is a real collision.
    conflicting = shard_registry.ShardGroup(
        group="arch", roots=("tests/adversarial",), shard_count=2,
        marker_prefix="arch_shard",
    )
    with pytest.raises(ValueError, match=r"already registered"):
        isolated.register(conflicting)


def test_unmarked_next_universe_fails_not_passes() -> None:
    """(T079b) A ``tests/next`` test collected with NO shard marker fails loud.

    Builds a synthetic universe (one ``tests/next`` test record carrying no
    ``next_shard_N`` marker at all) and proves the completeness invariant
    REJECTS it rather than passing vacuously — this is what protects against
    "an unmarked ``tests/next`` universe silently looks covered" regardless
    of *why* the marker is missing (dropped import, hook bug, or a
    genuinely-unregistered group).
    """
    unmarked_universe: list[gc.TestRecord] = [
        {
            "nodeid": "tests/next/test_example.py::test_something",
            "relpath": "tests/next/test_example.py",
            "markers": [],
        },
    ]

    with pytest.raises(AssertionError, match="carry NO shard marker"):
        assert_every_group_root_test_has_exactly_one_shard_marker(
            "next", unmarked_universe
        )

    with pytest.raises(AssertionError, match="selected by NO shard marker"):
        assert_shard_union_equals_full_group_root_universe(
            "next", unmarked_universe
        )

"""GC-1 — ``integration-tests-next`` shard-marker completeness invariant (FR-002).

Mission ``ci-test-topology-performance-01KXBJRT`` WP01. Proves GC-1 for the
``next`` group registered by ``tests/_next_shard_map.py``: the union of
``next_shard_1``/``next_shard_2``/``next_shard_3``-selected tests under the 3
``integration-tests-next`` roots (``tests/next``, ``tests/specify_cli/next``,
``tests/runtime``) is a total, disjoint partition of every test collected
under those roots.

Imports its three assertion bodies from
``tests.architectural.test_arch_shard_marker_completeness`` (the
group-parametrized helpers ``arch``'s own completeness guard is built from)
and calls them with ``group="next"`` — proving both files are driven by one
shared guard engine, not a parallel copy (D-044/C-003).

Must be RED until ``tests/conftest.py``'s collection hook applies
``next_shard_N`` markers (wired in this same WP, T002) — with zero markers
applied, the "every test has exactly one marker" and "union == full universe"
invariants both fail naturally, the same authored-failing discipline the
``arch`` guard used.
"""

from __future__ import annotations

import pytest

from tests.architectural import _gate_coverage as gc
from tests.architectural.test_arch_shard_marker_completeness import (
    assert_every_group_root_test_has_exactly_one_shard_marker,
    assert_group_root_universe_is_nonempty,
    assert_shard_union_equals_full_group_root_universe,
)

pytestmark = [pytest.mark.architectural]

_GROUP = "next"


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    """Every collected test with its marker set (one ``--collect-only`` pass)."""
    return gc.collect_universe()


def test_next_root_universe_is_nonempty(universe: list[gc.TestRecord]) -> None:
    assert_group_root_universe_is_nonempty(_GROUP, universe)


def test_every_next_root_test_has_exactly_one_shard_marker(
    universe: list[gc.TestRecord],
) -> None:
    assert_every_group_root_test_has_exactly_one_shard_marker(_GROUP, universe)


def test_shard_union_equals_full_next_root_universe(
    universe: list[gc.TestRecord],
) -> None:
    assert_shard_union_equals_full_group_root_universe(_GROUP, universe)

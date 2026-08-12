"""Live shard groups form non-empty, total partitions.

Authority: ``tests._shard_registry`` plus open CI-integrity epic #1931.  The
old module carried three equivalent partition assertions and four registry
self-tests; one live-corpus invariant covers the defect class directly.
"""

from __future__ import annotations

import pytest

from tests import _shard_registry as shard_registry
from tests.architectural import _gate_coverage as gc

pytestmark = pytest.mark.architectural


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    return gc.collect_universe()


@pytest.mark.parametrize("group", sorted(shard_registry.EXPECTED_GROUPS))
def test_every_group_root_node_has_exactly_one_shard_marker(
    group: str,
    universe: list[gc.TestRecord],
) -> None:
    spec = shard_registry.get_group(group)
    markers = {
        f"{spec.marker_prefix}_{number}"
        for number in range(1, spec.shard_count + 1)
    }
    records = [
        record
        for record in universe
        if any(
            record["relpath"] == root
            or record["relpath"].startswith(f"{root}/")
            for root in spec.roots
        )
    ]
    assert records, f"{group!r} shard roots collect no tests"

    invalid = {
        record["nodeid"]: sorted(set(record["markers"]) & markers)
        for record in records
        if len(set(record["markers"]) & markers) != 1
    }
    assert not invalid, (
        f"{group!r} nodes must carry exactly one shard marker: "
        f"{dict(sorted(invalid.items())[:20])}"
    )

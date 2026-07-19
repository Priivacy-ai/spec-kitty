"""Red-first contract tests for the batch-partition SSOT leaf (WP01).

These pin the two pure primitives before implementation exists:

- ``split_in_half`` — the plain keep-left ``//2`` cut (SSOT midpoint math).
- ``create_aware_midpoint`` — pure key-adjacency snap so an adjacent same-key
  pair is not split across the boundary. Shape-blind: ``key_of`` is the only
  injected policy (T004), so the same primitive drives a top-level ``dict`` key
  and a key nested inside ``payload`` without branching on either shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from specify_cli.core.batch_partition import create_aware_midpoint, split_in_half


# --------------------------------------------------------------------------- #
# split_in_half — even / odd halving + singleton edge (T002)
# --------------------------------------------------------------------------- #


def test_split_in_half_even() -> None:
    assert split_in_half(["a", "b", "c", "d"]) == (["a", "b"], ["c", "d"])


def test_split_in_half_odd_keeps_left_smaller() -> None:
    # mid = len // 2 = 1 -> left gets the floor slice.
    assert split_in_half(["a", "b", "c"]) == (["a"], ["b", "c"])


def test_split_in_half_singleton_edge_non_empty_left() -> None:
    # max(1, 0) == 1 -> left stays non-empty so the recursion always progresses.
    assert split_in_half(["x"]) == (["x"], [])


def test_split_in_half_empty() -> None:
    assert split_in_half([]) == ([], [])


def test_split_in_half_returns_fresh_lists_and_does_not_mutate_input() -> None:
    source = ["a", "b", "c", "d"]
    left, right = split_in_half(source)
    left.append("mutated")
    right.append("mutated")
    # Input untouched, and the returned slices are independent list objects.
    assert source == ["a", "b", "c", "d"]
    assert isinstance(left, list)
    assert isinstance(right, list)


def test_split_in_half_deterministic() -> None:
    source = ["a", "b", "c", "d", "e"]
    assert split_in_half(source) == split_in_half(source)


# --------------------------------------------------------------------------- #
# create_aware_midpoint — pure key-adjacency snap (T003)
# --------------------------------------------------------------------------- #


def _key(event: dict[str, Any]) -> str:
    return str(event["aggregate_id"])


def _events(*keys: str) -> list[dict[str, Any]]:
    return [{"aggregate_id": k, "seq": i} for i, k in enumerate(keys)]


def test_naive_midpoint_splits_adjacent_same_key_pair() -> None:
    # Guard assertion: prove the naive len//2 cut WOULD split the pair, so the
    # snap below is doing real work rather than trivially agreeing.
    events = _events("A", "B", "B", "C")  # pair at index 1,2 straddles cut 2
    naive = len(events) // 2
    assert naive == 2
    assert _key(events[naive - 1]) == _key(events[naive])


def test_create_aware_snaps_boundary_off_the_pair() -> None:
    events = _events("A", "B", "B", "C")
    idx = create_aware_midpoint(events, _key)
    # Must NOT fall between the two matching-key events (naive would be 2).
    assert idx != 2
    # The adjacent same-key pair lands wholly on one side of the split.
    left_keys = [_key(e) for e in events[:idx]]
    right_keys = [_key(e) for e in events[idx:]]
    assert left_keys.count("B") in (0, 2)
    assert right_keys.count("B") in (0, 2)


def test_create_aware_leaves_boundary_when_pair_not_adjacent() -> None:
    events = _events("A", "B", "C", "D")  # nothing straddles -> keep naive
    assert create_aware_midpoint(events, _key) == len(events) // 2


def test_create_aware_singleton_and_empty_return_zero() -> None:
    assert create_aware_midpoint([], _key) == 0
    assert create_aware_midpoint(_events("A"), _key) == 0


def test_create_aware_degenerate_two_same_key_keeps_pair_together() -> None:
    # len == 2, both same key: the only way to keep the pair together is an
    # edge index. Deterministic snap to 0 (pair on the right).
    events = _events("A", "A")
    idx = create_aware_midpoint(events, _key)
    assert idx in (0, 2)
    left_keys = [_key(e) for e in events[:idx]]
    right_keys = [_key(e) for e in events[idx:]]
    assert left_keys.count("A") in (0, 2)
    assert right_keys.count("A") in (0, 2)


def test_create_aware_is_pure_and_does_not_mutate() -> None:
    events = _events("A", "B", "B", "C")
    snapshot = [dict(e) for e in events]
    first = create_aware_midpoint(events, _key)
    second = create_aware_midpoint(events, _key)
    assert first == second  # deterministic
    assert events == snapshot  # no mutation


# --------------------------------------------------------------------------- #
# T004 — element-generic: same primitive, two unrelated shapes, no sniffing
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _OutboundEventStub:
    """Stand-in whose key lives INSIDE ``payload`` (unrelated to dict shape)."""

    payload: dict[str, Any] = field(default_factory=dict)


def _stub_key(event: _OutboundEventStub) -> str:
    """Key accessor for the payload-nested stub (mirrors :func:`_key` for dicts)."""
    return str(event.payload["wp_id"])


def test_create_aware_works_with_key_nested_in_payload() -> None:
    events = [
        _OutboundEventStub(payload={"wp_id": "WP-A"}),
        _OutboundEventStub(payload={"wp_id": "WP-B"}),
        _OutboundEventStub(payload={"wp_id": "WP-B"}),
        _OutboundEventStub(payload={"wp_id": "WP-C"}),
    ]

    idx = create_aware_midpoint(events, _stub_key)
    assert idx != len(events) // 2  # snapped off the adjacent WP-B pair
    left = [_stub_key(e) for e in events[:idx]]
    right = [_stub_key(e) for e in events[idx:]]
    assert left.count("WP-B") in (0, 2)
    assert right.count("WP-B") in (0, 2)


def test_same_index_for_equivalent_key_streams_across_shapes() -> None:
    # A dict stream and a payload-nested stream carrying the identical key
    # sequence must yield the identical index — proof the primitive branches on
    # the injected key alone, never on element shape.
    keys = ["A", "B", "B", "C", "C", "D"]
    dict_events = _events(*keys)
    stub_events = [_OutboundEventStub(payload={"wp_id": k}) for k in keys]

    dict_idx = create_aware_midpoint(dict_events, _key)
    stub_idx = create_aware_midpoint(stub_events, _stub_key)
    assert dict_idx == stub_idx

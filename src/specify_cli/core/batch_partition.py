"""Single canonical authority for splitting an ordered batch of events.

This is a **pure, dependency-free leaf** (DIR-044). It imports nothing from
``specify_cli`` and holds only index/partition arithmetic — no I/O, no clock,
no event-shape knowledge. It deliberately lives in ``core/`` (not ``delivery/``)
so both ``delivery`` and ``sync`` can import it downward without creating a
runtime ``sync -> delivery`` cycle (WP01 placement contract, alphonso).

Two primitives, two distinct policies:

- :func:`split_in_half` — the plain keep-left ``//2`` cut. The genuinely-shared
  midpoint math consumed later by BOTH the receiver bisect and the legacy 413
  shrink (#2755).
- :func:`create_aware_midpoint` — a **pure key-adjacency** snap: if the two
  events straddling the naive midpoint share the same ``key_of(...)``, nudge the
  boundary by one so that adjacent same-key pair is not split across the cut.

Both functions are ordering-agnostic: :func:`create_aware_midpoint` returns an
index and never reorders. It also does NOT and cannot guarantee
create-before-status for a batch-*spanning* pair — no midpoint can. That
guarantee is WP02's sequential recursion; this module stays a pure helper.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from typing import TypeVar

T = TypeVar("T")


def split_in_half(events: Sequence[T]) -> tuple[list[T], list[T]]:
    """Split ``events`` into a keep-left pair at ``max(1, len // 2)``.

    The ``max(1, ...)`` floor guarantees a non-empty left slice on the singleton
    edge (``[x] -> ([x], [])``), so a bisecting recursion always makes progress
    toward its ``len == 1`` base case. Returns fresh lists; the input is never
    mutated and may be any :class:`~collections.abc.Sequence`.
    """
    mid = max(1, len(events) // 2)
    return list(events[:mid]), list(events[mid:])


def create_aware_midpoint(
    events: Sequence[T], key_of: Callable[[T], Hashable]
) -> int:
    """Return a split index that keeps an adjacent same-key pair together.

    Starts from the naive midpoint ``len // 2``. If the two events straddling
    that cut share the same ``key_of(...)``, the boundary is nudged by one so the
    pair lands wholly on one side, preferring the direction that keeps both
    slices non-empty. ``key_of`` is the *only* injected policy — the primitive
    never inspects event shape or role (no create/status sniffing), which is what
    makes it element-generic across ``dict`` and structured event types alike.

    For ``len(events) < 2`` there is no interior boundary, so ``0`` is returned.
    """
    naive = len(events) // 2
    if naive == 0:
        # len 0 or 1: no interior pair can straddle a cut.
        return naive
    if key_of(events[naive - 1]) == key_of(events[naive]):
        nudged = naive + 1
        # Prefer nudging right (keeps both slices non-empty); on the degenerate
        # two-same-key batch that would empty the right slice, snap left instead
        # so the pair still stays together on one side.
        return nudged if nudged < len(events) else naive - 1
    return naive

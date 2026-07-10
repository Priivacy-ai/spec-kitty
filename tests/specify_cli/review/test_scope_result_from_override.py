"""Tests for ``ScopeResult.from_override`` (FR-007, mission merge-base-diff-ssot-01KX44SD).

``from_override`` retires the hand-built ``ScopeResult(...)`` construction that
``tasks_move_task``'s FR-004 override tier (``_mt_pre_review_gate_with_override_scope``)
used to build directly. This test pins that the classmethod yields the exact
same object the hand-built form produced — a pure constructor, no gate-policy
change.
"""
from __future__ import annotations

import pytest

from specify_cli.review.pre_review_gate import ScopeResult

pytestmark = pytest.mark.fast


def _hand_built(targets: tuple[str, ...]) -> ScopeResult:
    """Reproduce the exact pre-refactor hand-built construction for comparison."""
    return ScopeResult(
        test_targets=targets,
        matched_shard_groups=(),
        matched_composite_dirs=(),
        empty_cone_composite_dirs=(),
        excluded_scope_files=(),
    )


def test_from_override_matches_hand_built_construction() -> None:
    targets = ("tests/specify_cli/review/test_arbiter.py",)
    assert ScopeResult.from_override(targets) == _hand_built(targets)


def test_from_override_empty_targets_matches_hand_built() -> None:
    targets: tuple[str, ...] = ()
    result = ScopeResult.from_override(targets)
    assert result == _hand_built(targets)
    assert result.is_empty


def test_from_override_preserves_target_order_and_duplicates() -> None:
    # An override IS the test scope by definition — no dedup/reordering applies.
    targets = ("tests/a_test.py", "tests/b_test.py", "tests/a_test.py")
    result = ScopeResult.from_override(targets)
    assert result.test_targets == targets

"""Unit tests for the §4.5.1 inequality predicate.

Covers:
  - Exact-match case: resolved == required → holds, no violations
  - Missing case: resolved ⊄ required → holds=False, missing_urns populated
  - Over-broad case: resolved ⊋ required (no known_irrelevant) → holds=False
  - Over-broad tolerated: resolved ⊋ required but extras in known_irrelevant → holds
  - Empty inputs: trivially pass
  - Partial: some missing AND some over-broad simultaneously
"""

from __future__ import annotations

import pytest

from specify_cli.calibration.inequality import InequalityResult, assert_inequality_holds


class TestExactMatch:
    def test_exact_match_holds(self) -> None:
        scope = frozenset({"directive:D001", "tactic:T001"})
        result = assert_inequality_holds(
            resolved_scope=scope,
            required_scope=scope,
        )
        assert result.holds is True
        assert result.missing_urns == frozenset()
        assert result.over_broad_urns == frozenset()

    def test_returns_inequality_result_type(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset({"directive:D001"}),
            required_scope=frozenset({"directive:D001"}),
        )
        assert isinstance(result, InequalityResult)


class TestMissingContext:
    def test_missing_urn_detected(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset({"directive:D001"}),
            required_scope=frozenset({"directive:D001", "tactic:T_MISSING"}),
        )
        assert result.holds is False
        assert "tactic:T_MISSING" in result.missing_urns
        assert result.over_broad_urns == frozenset()

    def test_multiple_missing_urns(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset(),
            required_scope=frozenset({"directive:D001", "directive:D002"}),
        )
        assert result.holds is False
        assert result.missing_urns == frozenset({"directive:D001", "directive:D002"})

    def test_missing_does_not_raises(self) -> None:
        """Predicate never raises regardless of inputs."""
        result = assert_inequality_holds(
            resolved_scope=frozenset(),
            required_scope=frozenset({"directive:D001"}),
        )
        assert isinstance(result, InequalityResult)
        assert result.holds is False


class TestOverBroadContext:
    def test_over_broad_detected_without_known_irrelevant(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset({"directive:D001", "tactic:EXTRA"}),
            required_scope=frozenset({"directive:D001"}),
        )
        assert result.holds is False
        assert "tactic:EXTRA" in result.over_broad_urns
        assert result.missing_urns == frozenset()

    def test_over_broad_tolerated_by_known_irrelevant(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset({"directive:D001", "tactic:EXTRA"}),
            required_scope=frozenset({"directive:D001"}),
            known_irrelevant=frozenset({"tactic:EXTRA"}),
        )
        assert result.holds is True
        assert result.over_broad_urns == frozenset()
        assert result.missing_urns == frozenset()

    def test_partial_known_irrelevant(self) -> None:
        """One extra is tolerated, another is truly over-broad."""
        result = assert_inequality_holds(
            resolved_scope=frozenset({"directive:D001", "tactic:TOLERATED", "tactic:BAD"}),
            required_scope=frozenset({"directive:D001"}),
            known_irrelevant=frozenset({"tactic:TOLERATED"}),
        )
        assert result.holds is False
        assert "tactic:BAD" in result.over_broad_urns
        assert "tactic:TOLERATED" not in result.over_broad_urns


class TestEmptyInputs:
    def test_all_empty(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset(),
            required_scope=frozenset(),
        )
        assert result.holds is True

    def test_resolved_empty_required_empty(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset(),
            required_scope=frozenset(),
            known_irrelevant=frozenset({"some:urn"}),
        )
        assert result.holds is True

    def test_resolved_superset_required_empty(self) -> None:
        """If required_scope is empty, resolved is only over-broad if known_irrelevant
        doesn't cover everything."""
        result = assert_inequality_holds(
            resolved_scope=frozenset({"tactic:X"}),
            required_scope=frozenset(),
        )
        assert result.holds is False
        assert "tactic:X" in result.over_broad_urns

    def test_resolved_superset_required_empty_all_tolerated(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset({"tactic:X"}),
            required_scope=frozenset(),
            known_irrelevant=frozenset({"tactic:X"}),
        )
        assert result.holds is True


class TestCombinedViolations:
    def test_missing_and_over_broad_simultaneously(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset({"directive:D001", "tactic:SPURIOUS"}),
            required_scope=frozenset({"directive:D001", "tactic:NEEDED"}),
        )
        assert result.holds is False
        assert "tactic:NEEDED" in result.missing_urns
        assert "tactic:SPURIOUS" in result.over_broad_urns

    def test_frozen_fields_immutable(self) -> None:
        result = assert_inequality_holds(
            resolved_scope=frozenset({"directive:D001"}),
            required_scope=frozenset({"directive:D001"}),
        )
        with pytest.raises(AttributeError):
            result.holds = False  # type: ignore[misc]

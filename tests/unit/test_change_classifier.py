"""Unit tests for the complexity classifier (WP03).

Tests cover:
- classify_from_scores() with various score combinations
- Threshold boundary tests at 3/4 split and 6/7 split
- Classification and packaging mode selection
- Continue/stop gating behavior
- Score invariants (total == sum of factors, recommend_specify iff high)
- Input clamping (out-of-range values handled gracefully)
- Backward-compatible classify_change_request()
"""

from __future__ import annotations

import json

import pytest

from specify_cli.core.change_classifier import (
    COMPLEX_MAX,
    SIMPLE_MAX,
    TOTAL_MAX,
    ComplexityClassification,
    ComplexityScore,
    PackagingMode,
    ReviewAttention,
    _classify,
    _select_packaging_mode,
    classify_change_request,
    classify_from_scores,
)

# ============================================================================
# classify_from_scores API
# ============================================================================


class TestClassifyFromScores:
    """Test the primary classify_from_scores() API."""

    def test_all_zeros_is_simple(self):
        score = classify_from_scores(0, 0, 0, 0, 0)
        assert score.classification == ComplexityClassification.SIMPLE
        assert score.total_score == 0

    def test_simple_threshold(self):
        """Total 3 is still simple."""
        score = classify_from_scores(3, 0, 0, 0, 0)
        assert score.classification == ComplexityClassification.SIMPLE
        assert score.total_score == 3

    def test_complex_threshold(self):
        """Total 4 crosses into complex."""
        score = classify_from_scores(2, 2, 0, 0, 0)
        assert score.classification == ComplexityClassification.COMPLEX
        assert score.total_score == 4

    def test_high_threshold(self):
        """Total 7 crosses into high."""
        score = classify_from_scores(3, 2, 2, 0, 0)
        assert score.classification == ComplexityClassification.HIGH
        assert score.total_score == 7

    def test_max_scores(self):
        """Maximum possible scores."""
        score = classify_from_scores(3, 2, 2, 2, 1)
        assert score.total_score == 10
        assert score.classification == ComplexityClassification.HIGH

    def test_total_equals_sum(self):
        """Total must equal sum of all factors."""
        score = classify_from_scores(2, 1, 1, 2, 1)
        assert score.total_score == 2 + 1 + 1 + 2 + 1

    def test_recommend_specify_iff_high(self):
        """recommend_specify is True iff classification is HIGH."""
        simple = classify_from_scores(1, 0, 0, 0, 0)
        assert simple.recommend_specify is False

        complex_score = classify_from_scores(2, 1, 1, 0, 0)
        assert complex_score.recommend_specify is False

        high = classify_from_scores(3, 2, 2, 0, 0)
        assert high.recommend_specify is True


class TestInputClamping:
    """Test that out-of-range inputs are clamped gracefully."""

    def test_negative_values_clamped_to_zero(self):
        score = classify_from_scores(-1, -5, -2, -1, -1)
        assert score.scope_breadth_score == 0
        assert score.coupling_score == 0
        assert score.dependency_churn_score == 0
        assert score.ambiguity_score == 0
        assert score.integration_risk_score == 0
        assert score.total_score == 0

    def test_over_max_clamped(self):
        score = classify_from_scores(10, 10, 10, 10, 10)
        assert score.scope_breadth_score == 3
        assert score.coupling_score == 2
        assert score.dependency_churn_score == 2
        assert score.ambiguity_score == 2
        assert score.integration_risk_score == 1
        assert score.total_score == 10


# ============================================================================
# Classification Thresholds
# ============================================================================


class TestClassificationThresholds:
    """Test deterministic threshold boundaries."""

    def test_simple_max_boundary(self):
        assert _classify(3) == ComplexityClassification.SIMPLE

    def test_complex_min_boundary(self):
        assert _classify(4) == ComplexityClassification.COMPLEX

    def test_complex_max_boundary(self):
        assert _classify(6) == ComplexityClassification.COMPLEX

    def test_high_min_boundary(self):
        assert _classify(7) == ComplexityClassification.HIGH

    def test_zero_is_simple(self):
        assert _classify(0) == ComplexityClassification.SIMPLE

    def test_max_is_high(self):
        assert _classify(TOTAL_MAX) == ComplexityClassification.HIGH

    @pytest.mark.parametrize("score", range(0, SIMPLE_MAX + 1))
    def test_all_simple_scores(self, score: int):
        assert _classify(score) == ComplexityClassification.SIMPLE

    @pytest.mark.parametrize("score", range(SIMPLE_MAX + 1, COMPLEX_MAX + 1))
    def test_all_complex_scores(self, score: int):
        assert _classify(score) == ComplexityClassification.COMPLEX

    @pytest.mark.parametrize("score", range(COMPLEX_MAX + 1, TOTAL_MAX + 1))
    def test_all_high_scores(self, score: int):
        assert _classify(score) == ComplexityClassification.HIGH


# ============================================================================
# Packaging Mode Selection
# ============================================================================


class TestPackagingMode:
    """Test packaging mode selection."""

    def test_simple_always_single_wp(self):
        assert (
            _select_packaging_mode(ComplexityClassification.SIMPLE, 0, 0)
            == PackagingMode.SINGLE_WP
        )
        assert (
            _select_packaging_mode(ComplexityClassification.SIMPLE, 2, 3)
            == PackagingMode.SINGLE_WP
        )

    def test_complex_high_coupling_orchestration(self):
        assert (
            _select_packaging_mode(ComplexityClassification.COMPLEX, 2, 0)
            == PackagingMode.ORCHESTRATION
        )

    def test_complex_broad_scope_targeted_multi(self):
        assert (
            _select_packaging_mode(ComplexityClassification.COMPLEX, 0, 2)
            == PackagingMode.TARGETED_MULTI
        )
        assert (
            _select_packaging_mode(ComplexityClassification.COMPLEX, 1, 3)
            == PackagingMode.TARGETED_MULTI
        )

    def test_complex_low_both_single_wp(self):
        assert (
            _select_packaging_mode(ComplexityClassification.COMPLEX, 0, 1)
            == PackagingMode.SINGLE_WP
        )
        assert (
            _select_packaging_mode(ComplexityClassification.COMPLEX, 1, 0)
            == PackagingMode.SINGLE_WP
        )

    def test_high_follows_same_rules(self):
        assert (
            _select_packaging_mode(ComplexityClassification.HIGH, 2, 0)
            == PackagingMode.ORCHESTRATION
        )
        assert (
            _select_packaging_mode(ComplexityClassification.HIGH, 0, 3)
            == PackagingMode.TARGETED_MULTI
        )
        assert (
            _select_packaging_mode(ComplexityClassification.HIGH, 0, 0)
            == PackagingMode.SINGLE_WP
        )

    def test_mode_propagated_through_classify_from_scores(self):
        """Verify mode is set correctly via classify_from_scores."""
        score = classify_from_scores(0, 2, 2, 0, 0)  # complex, high coupling
        assert score.proposed_mode == PackagingMode.ORCHESTRATION

        score = classify_from_scores(3, 0, 1, 0, 0)  # complex, broad scope
        assert score.proposed_mode == PackagingMode.TARGETED_MULTI


# ============================================================================
# Score Invariants
# ============================================================================


class TestScoreInvariants:
    """Test invariants across various score combinations."""

    SCORE_COMBOS = [
        (0, 0, 0, 0, 0),
        (1, 0, 0, 0, 0),
        (3, 2, 2, 2, 1),
        (2, 1, 1, 1, 0),
        (0, 0, 0, 2, 1),
        (1, 2, 0, 0, 1),
        (3, 0, 2, 0, 0),
        (0, 2, 0, 2, 0),
    ]

    @pytest.mark.parametrize("combo", SCORE_COMBOS)
    def test_total_equals_sum_of_factors(self, combo):
        score = classify_from_scores(*combo)
        assert score.total_score == sum(combo)

    @pytest.mark.parametrize("combo", SCORE_COMBOS)
    def test_recommend_specify_iff_high(self, combo):
        score = classify_from_scores(*combo)
        assert score.recommend_specify == (
            score.classification == ComplexityClassification.HIGH
        )

    @pytest.mark.parametrize("combo", SCORE_COMBOS)
    def test_factor_within_ranges(self, combo):
        score = classify_from_scores(*combo)
        assert 0 <= score.scope_breadth_score <= 3
        assert 0 <= score.coupling_score <= 2
        assert 0 <= score.dependency_churn_score <= 2
        assert 0 <= score.ambiguity_score <= 2
        assert 0 <= score.integration_risk_score <= 1


# ============================================================================
# Review Attention
# ============================================================================


class TestReviewAttention:
    """Test FR-011 elevated review attention behavior."""

    def test_normal_review_by_default(self):
        score = classify_from_scores(0, 0, 0, 0, 0)
        assert score.review_attention == ReviewAttention.NORMAL

    def test_elevated_when_continuing_past_high(self):
        score = classify_from_scores(3, 2, 2, 0, 0, continued_after_warning=True)
        assert score.classification == ComplexityClassification.HIGH
        assert score.review_attention == ReviewAttention.ELEVATED

    def test_normal_even_with_continue_when_not_high(self):
        score = classify_from_scores(1, 0, 0, 0, 0, continued_after_warning=True)
        assert score.review_attention == ReviewAttention.NORMAL


# ============================================================================
# to_dict Serialization
# ============================================================================


class TestToDict:
    """Test ComplexityScore.to_dict() serialization."""

    def test_to_dict_has_all_fields(self):
        score = classify_from_scores(1, 1, 0, 0, 0)
        d = score.to_dict()
        assert "scopeBreadthScore" in d
        assert "couplingScore" in d
        assert "dependencyChurnScore" in d
        assert "ambiguityScore" in d
        assert "integrationRiskScore" in d
        assert "totalScore" in d
        assert "classification" in d
        assert "recommendSpecify" in d
        assert "proposedMode" in d
        assert "reviewAttention" in d

    def test_to_dict_values_are_serializable(self):
        score = classify_from_scores(2, 1, 1, 0, 1)
        d = score.to_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)


# ============================================================================
# Backward Compatibility
# ============================================================================


class TestBackwardCompatibility:
    """Test that classify_change_request still works."""

    def test_returns_simple_by_default(self):
        """Without pre-assessed scores, returns simple classification."""
        score = classify_change_request("any request text")
        assert score.classification == ComplexityClassification.SIMPLE
        assert score.total_score == 0

    def test_continued_after_warning_flag(self):
        """continued_after_warning flag still works."""
        score = classify_change_request("any text", continued_after_warning=True)
        # Not HIGH, so review attention stays normal
        assert score.review_attention == ReviewAttention.NORMAL

    def test_empty_request(self):
        score = classify_change_request("")
        assert score.total_score == 0
        assert score.classification == ComplexityClassification.SIMPLE

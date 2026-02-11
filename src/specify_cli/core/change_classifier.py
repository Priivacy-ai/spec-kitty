"""Complexity classifier for mid-stream change requests.

Provides the ComplexityScore dataclass and scoring infrastructure (FR-009).
Classification thresholds map total scores to simple/complex/high.

The actual scoring of the 5 factors is done by the AI agent executing the
/spec-kitty.change command template -- the agent assesses scope_breadth,
coupling, dependency_churn, ambiguity, and integration_risk, then passes
the scores to `classify_from_scores()`.

A legacy `classify_change_request()` function is retained for backward
compatibility but delegates to simple heuristic defaults (all zeros).

Thresholds:
    0-3  -> simple   (single change WP)
    4-6  -> complex  (adaptive packaging)
    7-10 -> high     (recommend /spec-kitty.specify, explicit decision required)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ============================================================================
# Types
# ============================================================================


class ComplexityClassification(str, Enum):
    """Complexity classification for a change request."""

    SIMPLE = "simple"
    COMPLEX = "complex"
    HIGH = "high"


class PackagingMode(str, Enum):
    """Adaptive packaging mode selected from score factors.

    single_wp      - One change WP with multiple tasks (low coupling)
    orchestration  - One coordinating change WP for tightly coupled multi-area changes
    targeted_multi - Multiple focused change WPs (parallelizable)
    """

    SINGLE_WP = "single_wp"
    ORCHESTRATION = "orchestration"
    TARGETED_MULTI = "targeted_multi"


class ReviewAttention(str, Enum):
    """Review attention level for generated change work packages."""

    NORMAL = "normal"
    ELEVATED = "elevated"


# ============================================================================
# Score Component Ranges (fixed weights)
# ============================================================================

#: Maximum values for each scoring factor
SCOPE_BREADTH_MAX = 3
COUPLING_MAX = 2
DEPENDENCY_CHURN_MAX = 2
AMBIGUITY_MAX = 2
INTEGRATION_RISK_MAX = 1
TOTAL_MAX = (
    SCOPE_BREADTH_MAX
    + COUPLING_MAX
    + DEPENDENCY_CHURN_MAX
    + AMBIGUITY_MAX
    + INTEGRATION_RISK_MAX
)

#: Classification threshold boundaries
SIMPLE_MAX = 3  # 0-3 inclusive
COMPLEX_MAX = 6  # 4-6 inclusive
# 7-10 -> high


# ============================================================================
# Data Classes
# ============================================================================


@dataclass(frozen=True)
class ComplexityScore:
    """Full score breakdown for a change request.

    Invariants:
        - total_score == scope_breadth + coupling + dependency_churn + ambiguity + integration_risk
        - recommend_specify == True iff classification == HIGH
    """

    scope_breadth_score: int
    coupling_score: int
    dependency_churn_score: int
    ambiguity_score: int
    integration_risk_score: int
    total_score: int
    classification: ComplexityClassification
    recommend_specify: bool
    proposed_mode: PackagingMode
    review_attention: ReviewAttention

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-friendly dictionary (camelCase keys)."""
        return {
            "scopeBreadthScore": self.scope_breadth_score,
            "couplingScore": self.coupling_score,
            "dependencyChurnScore": self.dependency_churn_score,
            "ambiguityScore": self.ambiguity_score,
            "integrationRiskScore": self.integration_risk_score,
            "totalScore": self.total_score,
            "classification": self.classification.value,
            "recommendSpecify": self.recommend_specify,
            "proposedMode": self.proposed_mode.value,
            "reviewAttention": self.review_attention.value,
        }


# ============================================================================
# Classification and Packaging Mode Selection
# ============================================================================


def _classify(total_score: int) -> ComplexityClassification:
    """Map total score to classification (deterministic thresholds)."""
    if total_score <= SIMPLE_MAX:
        return ComplexityClassification.SIMPLE
    if total_score <= COMPLEX_MAX:
        return ComplexityClassification.COMPLEX
    return ComplexityClassification.HIGH


def _select_packaging_mode(
    classification: ComplexityClassification,
    coupling_score: int,
    scope_breadth_score: int,
) -> PackagingMode:
    """Select adaptive packaging mode.

    Rules:
      - simple -> always single_wp
      - complex/high with high coupling (>=2) -> orchestration
      - complex/high with scope_breadth >= 2 and coupling < 2 -> targeted_multi
      - complex/high otherwise -> single_wp
    """
    if classification == ComplexityClassification.SIMPLE:
        return PackagingMode.SINGLE_WP

    if coupling_score >= 2:
        return PackagingMode.ORCHESTRATION

    if scope_breadth_score >= 2:
        return PackagingMode.TARGETED_MULTI

    return PackagingMode.SINGLE_WP


def _clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp value to [min_val, max_val]."""
    return max(min_val, min(value, max_val))


# ============================================================================
# Public API
# ============================================================================


def classify_from_scores(
    scope_breadth: int,
    coupling: int,
    dependency_churn: int,
    ambiguity: int,
    integration_risk: int,
    continued_after_warning: bool = False,
) -> ComplexityScore:
    """Build a ComplexityScore from pre-assessed factor scores.

    This is the primary API. The AI agent assesses the 5 factors based on
    the change request context and passes the scores here. Scores are
    clamped to valid ranges.

    Args:
        scope_breadth: 0-3 (breadth of areas affected)
        coupling: 0-2 (coupling between affected areas)
        dependency_churn: 0-2 (dependency/library changes)
        ambiguity: 0-2 (residual uncertainty in request)
        integration_risk: 0-1 (CI/CD, deployment, infra risk)
        continued_after_warning: True if user chose to continue past
            a high-complexity warning (sets elevated review attention)

    Returns:
        ComplexityScore with full breakdown and classification
    """
    scope_breadth = _clamp(scope_breadth, 0, SCOPE_BREADTH_MAX)
    coupling = _clamp(coupling, 0, COUPLING_MAX)
    dependency_churn = _clamp(dependency_churn, 0, DEPENDENCY_CHURN_MAX)
    ambiguity = _clamp(ambiguity, 0, AMBIGUITY_MAX)
    integration_risk = _clamp(integration_risk, 0, INTEGRATION_RISK_MAX)

    total = scope_breadth + coupling + dependency_churn + ambiguity + integration_risk
    classification = _classify(total)
    recommend_specify = classification == ComplexityClassification.HIGH
    proposed_mode = _select_packaging_mode(classification, coupling, scope_breadth)

    # FR-011: elevated review attention when continuing after warning
    if continued_after_warning and classification == ComplexityClassification.HIGH:
        review_attention = ReviewAttention.ELEVATED
    else:
        review_attention = ReviewAttention.NORMAL

    return ComplexityScore(
        scope_breadth_score=scope_breadth,
        coupling_score=coupling,
        dependency_churn_score=dependency_churn,
        ambiguity_score=ambiguity,
        integration_risk_score=integration_risk,
        total_score=total,
        classification=classification,
        recommend_specify=recommend_specify,
        proposed_mode=proposed_mode,
        review_attention=review_attention,
    )


def classify_change_request(
    request_text: str,
    continued_after_warning: bool = False,
) -> ComplexityScore:
    """Classify a change request with default scores.

    This is a backward-compatible entry point. When called without
    pre-assessed scores, it returns a simple (all-zeros) classification.
    The actual scoring is done by the AI agent via the command template,
    which calls classify_from_scores() with assessed values.

    Args:
        request_text: Natural-language change request text (unused - kept
            for backward compatibility)
        continued_after_warning: True if user explicitly chose to continue
            past a high-complexity warning

    Returns:
        ComplexityScore with simple/default classification
    """
    return classify_from_scores(
        scope_breadth=0,
        coupling=0,
        dependency_churn=0,
        ambiguity=0,
        integration_risk=0,
        continued_after_warning=continued_after_warning,
    )

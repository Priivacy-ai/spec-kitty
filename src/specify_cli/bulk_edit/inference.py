"""Keyword-based inference for bulk edit detection in spec content.

Scans spec.md content for rename/migration keywords and returns a scored
result indicating whether the spec describes a bulk-edit operation. The
module is purely analytical -- no Rich output, no CLI interaction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Weight tables
# ---------------------------------------------------------------------------

# High-specificity phrases (3 points) -- strong signal for bulk edit
HIGH_WEIGHT_PHRASES: list[str] = [
    "rename across",
    "bulk edit",
    "codemod",
    "find-and-replace",
    "find and replace",
    "replace everywhere",
    "terminology migration",
    "rename all occurrences",
]

# Medium-specificity keywords (2 points)
MEDIUM_WEIGHT_KEYWORDS: list[str] = [
    "rename",
    "migrate",
    "replace all",
    "across the codebase",
    "globally",
    "sed",
    "search and replace",
]

# Low-specificity keywords (1 point) -- common words, ambiguous alone
LOW_WEIGHT_KEYWORDS: list[str] = [
    "update",
    "change",
    "modify",
    "refactor",
]

INFERENCE_THRESHOLD: int = 4

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InferenceResult:
    """Outcome of scanning spec content for bulk-edit indicators."""

    score: int
    threshold: int
    triggered: bool  # score >= threshold
    matched_phrases: list[tuple[str, int]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _word_boundary_match(keyword: str, text: str) -> bool:
    """Return True if *keyword* appears in *text* respecting word boundaries.

    Multi-word keywords use substring matching (they inherently carry enough
    context). Single-word keywords use ``\\b`` regex boundaries so that, for
    example, ``"update"`` does not match inside ``"updated_at"``.
    """
    if " " in keyword or "-" in keyword:
        return keyword in text
    return bool(re.search(rf"\b{re.escape(keyword)}\b", text))


def score_spec_for_bulk_edit(spec_content: str) -> InferenceResult:
    """Score *spec_content* for bulk-edit likelihood.

    Higher-weight phrases are matched first. A lower-weight keyword that is a
    substring of an already-matched higher-weight phrase is skipped to prevent
    double counting.
    """
    lowered = spec_content.lower()
    matched: list[tuple[str, int]] = []
    consumed_phrases: list[str] = []

    # --- High-weight phrases (3 points each) ---
    for phrase in HIGH_WEIGHT_PHRASES:
        if phrase in lowered:
            matched.append((phrase, 3))
            consumed_phrases.append(phrase)

    # --- Medium-weight keywords (2 points each) ---
    for keyword in MEDIUM_WEIGHT_KEYWORDS:
        # Skip if this keyword is a substring of any already-matched phrase
        if any(keyword in consumed for consumed in consumed_phrases):
            continue
        if _word_boundary_match(keyword, lowered):
            matched.append((keyword, 2))
            consumed_phrases.append(keyword)

    # --- Low-weight keywords (1 point each) ---
    for keyword in LOW_WEIGHT_KEYWORDS:
        if any(keyword in consumed for consumed in consumed_phrases):
            continue
        if _word_boundary_match(keyword, lowered):
            matched.append((keyword, 1))
            consumed_phrases.append(keyword)

    total = sum(weight for _, weight in matched)
    return InferenceResult(
        score=total,
        threshold=INFERENCE_THRESHOLD,
        triggered=total >= INFERENCE_THRESHOLD,
        matched_phrases=matched,
    )


# ---------------------------------------------------------------------------
# File-level scanning
# ---------------------------------------------------------------------------


def scan_spec_file(feature_dir: Path) -> InferenceResult:
    """Read ``spec.md`` from *feature_dir* and score it for bulk-edit signals.

    Returns a zero-score, non-triggered result when ``spec.md`` is missing.
    """
    spec_path = feature_dir / "spec.md"
    if not spec_path.exists():
        return InferenceResult(
            score=0,
            threshold=INFERENCE_THRESHOLD,
            triggered=False,
        )

    content = spec_path.read_text(encoding="utf-8")
    return score_spec_for_bulk_edit(content)

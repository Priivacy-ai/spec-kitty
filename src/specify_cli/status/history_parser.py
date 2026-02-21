"""History parser for reconstructing transition chains from WP frontmatter.

Provides pure functions that convert raw frontmatter history[] arrays
into normalized, deduplicated transition chains suitable for creating
canonical StatusEvent records. This module performs NO I/O — it only
transforms data structures.

Exports:
    NormalizedHistoryEntry - Intermediate representation of a history entry
    Transition - A single lane-to-lane transition
    TransitionChain - Ordered list of transitions with metadata
    build_transition_chain() - Main entry point for reconstruction
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .models import DoneEvidence, ReviewApproval
from .transitions import resolve_lane_alias

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NormalizedHistoryEntry:
    """A single history entry with alias-resolved lane and extracted fields."""

    timestamp: str  # ISO 8601 UTC
    lane: str  # Canonical lane (never an alias)
    actor: str  # Agent identifier or "migration"


@dataclass(frozen=True)
class Transition:
    """A single lane-to-lane transition derived from adjacent history entries."""

    from_lane: str
    to_lane: str
    timestamp: str  # Timestamp of the transition (from target entry)
    actor: str  # Actor who caused the transition
    evidence: DoneEvidence | None = None


@dataclass
class TransitionChain:
    """Ordered list of transitions reconstructed from frontmatter history."""

    transitions: list[Transition]
    history_entries: int  # Number of raw history entries parsed
    has_evidence: bool  # Whether any transition has DoneEvidence


def normalize_entries(history: list[dict[str, Any]]) -> list[NormalizedHistoryEntry]:
    """Convert raw Format A history entries into NormalizedHistoryEntry objects.

    Resolves lane aliases, extracts timestamps and actors, and skips
    malformed entries gracefully.

    Args:
        history: List of raw history dicts from frontmatter.

    Returns:
        List of NormalizedHistoryEntry in original order.
    """
    entries: list[NormalizedHistoryEntry] = []
    for entry in history:
        if not isinstance(entry, dict):
            logger.warning("Skipping non-dict history entry: %r", entry)
            continue

        raw_lane = entry.get("lane")
        if not raw_lane:
            logger.warning("Skipping history entry with missing lane: %r", entry)
            continue

        lane = resolve_lane_alias(str(raw_lane).strip())
        timestamp = str(entry.get("timestamp", "")) or datetime.now(timezone.utc).isoformat()
        actor = str(entry.get("agent", "")) or "migration"

        entries.append(NormalizedHistoryEntry(timestamp=timestamp, lane=lane, actor=actor))
    return entries


def collapse_duplicates(
    entries: list[NormalizedHistoryEntry],
) -> list[NormalizedHistoryEntry]:
    """Remove consecutive entries with the same lane.

    Always keeps the first entry. For consecutive duplicates, only the
    first occurrence is retained.

    Args:
        entries: Normalized history entries.

    Returns:
        Collapsed list with no consecutive duplicate lanes.
    """
    if not entries:
        return []

    collapsed: list[NormalizedHistoryEntry] = [entries[0]]
    for entry in entries[1:]:
        if entry.lane != collapsed[-1].lane:
            collapsed.append(entry)
    return collapsed


def pair_transitions(entries: list[NormalizedHistoryEntry]) -> list[Transition]:
    """Convert normalized entries into transitions by pairing adjacent entries.

    Each transition uses the target entry's timestamp and actor (the agent
    who caused the transition TO the new lane).

    Args:
        entries: Normalized, collapsed history entries.

    Returns:
        List of Transition objects. Empty if fewer than 2 entries.
    """
    if len(entries) < 2:
        return []

    transitions: list[Transition] = []
    for i in range(len(entries) - 1):
        transitions.append(
            Transition(
                from_lane=entries[i].lane,
                to_lane=entries[i + 1].lane,
                timestamp=entries[i + 1].timestamp,
                actor=entries[i + 1].actor,
            )
        )
    return transitions


def gap_fill(
    transitions: list[Transition],
    last_history_lane: str | None,
    current_lane: str,
    fallback_timestamp: str,
) -> list[Transition]:
    """Add a gap-fill transition if the last history lane differs from current.

    Handles 4 cases:
    1. No history, current is planned: return empty (no transitions needed)
    2. No history, current is not planned: bootstrap planned -> current
    3. Last history matches current: return transitions unchanged
    4. Last history differs from current: append gap-fill transition

    Args:
        transitions: Existing transitions from history pairs.
        last_history_lane: Lane of the last collapsed history entry, or None.
        current_lane: Current frontmatter lane (alias-resolved).
        fallback_timestamp: Timestamp to use for the gap-fill transition.

    Returns:
        Updated list of transitions.
    """
    if last_history_lane is None:
        if current_lane == "planned":
            return []
        return [
            Transition(
                from_lane="planned",
                to_lane=current_lane,
                timestamp=fallback_timestamp,
                actor="migration",
            )
        ]

    if last_history_lane == current_lane:
        return transitions

    result = list(transitions)
    result.append(
        Transition(
            from_lane=last_history_lane,
            to_lane=current_lane,
            timestamp=fallback_timestamp,
            actor="migration",
        )
    )
    return result


def extract_done_evidence(frontmatter: dict[str, Any], wp_id: str) -> DoneEvidence | None:
    """Build DoneEvidence from frontmatter review fields.

    Only produces evidence when review_status is "approved" AND
    reviewed_by is non-empty.

    Args:
        frontmatter: Full WP frontmatter dict.
        wp_id: Work package ID for the reference field.

    Returns:
        DoneEvidence if review approval is present, None otherwise.
    """
    review_status = frontmatter.get("review_status")
    reviewed_by = frontmatter.get("reviewed_by")

    if review_status == "approved" and reviewed_by and str(reviewed_by).strip():
        return DoneEvidence(
            review=ReviewApproval(
                reviewer=str(reviewed_by).strip(),
                verdict="approved",
                reference=f"frontmatter-migration:{wp_id}",
            )
        )
    return None


def build_transition_chain(
    frontmatter: dict[str, Any],
    wp_id: str,
) -> TransitionChain:
    """Reconstruct a full transition chain from WP frontmatter.

    Main entry point that orchestrates: normalize -> collapse -> pair ->
    gap_fill -> attach evidence.

    Args:
        frontmatter: Full WP frontmatter dict.
        wp_id: Work package ID.

    Returns:
        TransitionChain with all reconstructed transitions.
    """
    history: list[dict[str, Any]] = frontmatter.get("history", [])
    if not isinstance(history, list):
        history = []

    raw_lane = str(frontmatter.get("lane", "planned")).strip() or "planned"
    current_lane = resolve_lane_alias(raw_lane)

    # Step 1: Normalize
    normalized = normalize_entries(history)

    # Step 2: Collapse consecutive duplicates
    collapsed = collapse_duplicates(normalized)

    # Step 3: Pair into transitions
    transitions = pair_transitions(collapsed)

    # Step 4: Gap-fill to current lane
    last_history_lane = collapsed[-1].lane if collapsed else None
    if collapsed:
        fallback_timestamp = collapsed[-1].timestamp
    else:
        fallback_timestamp = datetime.now(timezone.utc).isoformat()

    final_transitions = gap_fill(transitions, last_history_lane, current_lane, fallback_timestamp)

    # Step 5: Attach DoneEvidence to transitions targeting "done"
    evidence = extract_done_evidence(frontmatter, wp_id)
    has_evidence = False

    if evidence is not None:
        updated: list[Transition] = []
        for t in final_transitions:
            if t.to_lane == "done":
                updated.append(
                    Transition(
                        from_lane=t.from_lane,
                        to_lane=t.to_lane,
                        timestamp=t.timestamp,
                        actor=t.actor,
                        evidence=evidence,
                    )
                )
                has_evidence = True
            else:
                updated.append(t)
        final_transitions = updated

    return TransitionChain(
        transitions=final_transitions,
        history_entries=len(history),
        has_evidence=has_evidence,
    )

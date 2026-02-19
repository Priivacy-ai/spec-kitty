"""Conflict rendering with Rich (WP06/T025).

This module implements Rich-based rendering for semantic conflicts,
displaying ranked candidate senses with color-coded severity.
"""

import logging
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import Severity, SemanticConflict, SenseRef

logger = logging.getLogger(__name__)

SEVERITY_COLORS: dict[Severity, str] = {
    Severity.HIGH: "red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "blue",
}

SEVERITY_ICONS: dict[Severity, str] = {
    Severity.HIGH: "\U0001f534",
    Severity.MEDIUM: "\U0001f7e1",
    Severity.LOW: "\U0001f535",
}

# Scope precedence map: lower number = higher precedence (shown first)
SCOPE_PRECEDENCE: dict[str, int] = {
    "mission_local": 0,
    "team_domain": 1,
    "audience_domain": 2,
    "spec_kitty_core": 3,
}


def sort_candidates(candidates: List[SenseRef]) -> List[SenseRef]:
    """Sort candidate senses by scope precedence then descending confidence.

    Candidates with scope precedence mission_local (0) appear first,
    then team_domain (1), audience_domain (2), spec_kitty_core (3).
    Within the same scope, higher confidence appears first.
    Unknown scopes are sorted after all known scopes.

    Args:
        candidates: List of SenseRef candidates to sort

    Returns:
        New sorted list (does not mutate input)
    """
    return sorted(
        candidates,
        key=lambda s: (SCOPE_PRECEDENCE.get(s.scope, 99), -s.confidence),
    )


def _get_severity_color(severity: Severity) -> str:
    """Get color for severity, defaulting to white for unknown values."""
    color = SEVERITY_COLORS.get(severity)
    if color is None:
        logger.warning("Unknown severity level: %s, defaulting to white", severity)
        return "white"
    return color


def _get_severity_icon(severity: Severity) -> str:
    """Get icon for severity, defaulting to '?' for unknown values."""
    icon = SEVERITY_ICONS.get(severity)
    if icon is None:
        logger.warning("Unknown severity level: %s, defaulting to '?'", severity)
        return "?"
    return icon


def render_conflict(
    console: Console,
    conflict: SemanticConflict,
) -> None:
    """Render a single conflict with Rich formatting.

    Displays:
    - Severity icon and level (color-coded)
    - Term surface text
    - Context (usage location)
    - Ranked candidate senses (scope + definition + confidence)

    Args:
        console: Rich console instance
        conflict: Semantic conflict to render
    """
    severity_color = _get_severity_color(conflict.severity)
    severity_icon = _get_severity_icon(conflict.severity)

    # Create title with severity
    title = (
        f"[{severity_color}]{severity_icon}[/{severity_color}] "
        f'conflict: "{conflict.term.surface_text}"'
    )

    # Sort candidates by scope precedence then descending confidence
    ranked_candidates = sort_candidates(conflict.candidate_senses)

    # Create table for candidates
    if ranked_candidates:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Scope", style="green")
        table.add_column("Definition", style="white")
        table.add_column("Confidence", justify="right", style="yellow")

        # Add ranked candidates
        for idx, sense in enumerate(ranked_candidates, start=1):
            table.add_row(
                str(idx),
                sense.scope,
                sense.definition,
                f"{sense.confidence:.2f}",
            )

        body: Table | str = table
    else:
        body = "(No candidates available)"

    # Create metadata subtitle
    metadata = (
        f"[bold]Term:[/bold] {conflict.term.surface_text}  "
        f"[bold]Type:[/bold] {conflict.conflict_type.value}  "
        f"[bold]Context:[/bold] {conflict.context}"
    )

    panel = Panel(
        body,
        title=title,
        subtitle=metadata,
        border_style=severity_color,
    )

    console.print(panel)


def render_conflict_batch(
    console: Console,
    conflicts: List[SemanticConflict],
    max_questions: int = 3,
) -> List[SemanticConflict]:
    """Render conflicts prioritized by severity, capped at max_questions.

    Args:
        console: Rich console instance
        conflicts: All conflicts detected
        max_questions: Maximum conflicts to show (default 3)

    Returns:
        List of conflicts to prompt for (sorted by severity, capped)
    """
    # Sort by severity (high -> medium -> low), then by term text for determinism
    severity_order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    sorted_conflicts = sorted(
        conflicts,
        key=lambda c: (severity_order.get(c.severity, 99), c.term.surface_text),
    )

    # Cap to max_questions
    to_prompt = sorted_conflicts[:max_questions]

    # Render summary if truncated
    if len(sorted_conflicts) > max_questions:
        remaining = len(sorted_conflicts) - max_questions
        console.print(
            f"\n[yellow]Note:[/yellow] Showing {max_questions} of "
            f"{len(sorted_conflicts)} conflicts. "
            f"{remaining} lower-priority conflict(s) deferred to async resolution.\n"
        )

    # Render each conflict
    for conflict in to_prompt:
        render_conflict(console, conflict)
        console.print()  # Blank line between conflicts

    return to_prompt

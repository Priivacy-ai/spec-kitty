"""Scope resolution logic (WP04).

This module implements term resolution against the scope hierarchy.
Terms are resolved in precedence order: mission_local → team_domain → audience_domain → spec_kitty_core.
"""

from typing import List

from .models import TermSense
from .scope import GlossaryScope
from .store import GlossaryStore


def resolve_term(
    surface: str,
    scopes: List[GlossaryScope],
    store: GlossaryStore,
) -> List[TermSense]:
    """Resolve term against scope hierarchy.

    Args:
        surface: Term surface text (normalized)
        scopes: List of GlossaryScope in precedence order
        store: GlossaryStore to query

    Returns:
        List of matching TermSense objects across all scopes.
        Results maintain scope precedence order.

    Example:
        >>> scopes = [GlossaryScope.MISSION_LOCAL, GlossaryScope.TEAM_DOMAIN]
        >>> results = resolve_term("workspace", scopes, store)
        >>> # Returns matches from mission_local first, then team_domain
    """
    # Convert enum values to strings for store lookup
    scope_values = tuple(s.value for s in scopes)
    return store.lookup(surface, scope_values)

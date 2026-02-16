"""GlossaryScope enum and scope resolution utilities."""

from enum import Enum
from typing import List


class GlossaryScope(Enum):
    """Glossary scope levels in the hierarchy."""
    MISSION_LOCAL = "mission_local"
    TEAM_DOMAIN = "team_domain"
    AUDIENCE_DOMAIN = "audience_domain"
    SPEC_KITTY_CORE = "spec_kitty_core"


# Resolution order (highest to lowest precedence)
SCOPE_RESOLUTION_ORDER: List[GlossaryScope] = [
    GlossaryScope.MISSION_LOCAL,
    GlossaryScope.TEAM_DOMAIN,
    GlossaryScope.AUDIENCE_DOMAIN,
    GlossaryScope.SPEC_KITTY_CORE,
]


def get_scope_precedence(scope: GlossaryScope) -> int:
    """
    Get numeric precedence for a scope (lower number = higher precedence).

    Args:
        scope: GlossaryScope enum value

    Returns:
        Precedence integer (0 = highest precedence)
    """
    try:
        return SCOPE_RESOLUTION_ORDER.index(scope)
    except ValueError:
        # Unknown scope defaults to lowest precedence
        return len(SCOPE_RESOLUTION_ORDER)


def should_use_scope(scope: GlossaryScope, configured_scopes: List[GlossaryScope]) -> bool:
    """
    Check if a scope should be used in resolution.

    Args:
        scope: Scope to check
        configured_scopes: List of active scopes

    Returns:
        True if scope is configured and should be used
    """
    return scope in configured_scopes

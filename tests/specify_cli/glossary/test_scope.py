import pytest
from specify_cli.glossary.scope import (
    GlossaryScope,
    SCOPE_RESOLUTION_ORDER,
    get_scope_precedence,
    should_use_scope,
)

def test_scope_resolution_order():
    """SCOPE_RESOLUTION_ORDER is correct."""
    assert SCOPE_RESOLUTION_ORDER == [
        GlossaryScope.MISSION_LOCAL,
        GlossaryScope.TEAM_DOMAIN,
        GlossaryScope.AUDIENCE_DOMAIN,
        GlossaryScope.SPEC_KITTY_CORE,
    ]

def test_get_scope_precedence():
    """get_scope_precedence returns correct precedence."""
    assert get_scope_precedence(GlossaryScope.MISSION_LOCAL) == 0  # Highest
    assert get_scope_precedence(GlossaryScope.TEAM_DOMAIN) == 1
    assert get_scope_precedence(GlossaryScope.AUDIENCE_DOMAIN) == 2
    assert get_scope_precedence(GlossaryScope.SPEC_KITTY_CORE) == 3  # Lowest

def test_should_use_scope():
    """should_use_scope checks if scope is configured."""
    configured = [GlossaryScope.MISSION_LOCAL, GlossaryScope.SPEC_KITTY_CORE]

    assert should_use_scope(GlossaryScope.MISSION_LOCAL, configured) is True
    assert should_use_scope(GlossaryScope.SPEC_KITTY_CORE, configured) is True
    assert should_use_scope(GlossaryScope.TEAM_DOMAIN, configured) is False
    assert should_use_scope(GlossaryScope.AUDIENCE_DOMAIN, configured) is False

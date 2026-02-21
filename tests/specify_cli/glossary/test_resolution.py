"""Tests for term resolution logic (WP04 T016)."""

import pytest
from datetime import datetime
from pathlib import Path

from specify_cli.glossary.models import TermSurface, TermSense, Provenance, SenseStatus
from specify_cli.glossary.scope import GlossaryScope, SCOPE_RESOLUTION_ORDER
from specify_cli.glossary.store import GlossaryStore
from specify_cli.glossary.resolution import resolve_term


@pytest.fixture
def glossary_store(tmp_path: Path) -> GlossaryStore:
    """Create a GlossaryStore with sample data."""
    store = GlossaryStore(tmp_path / "events.log")

    # Add terms across different scopes
    provenance = Provenance(
        actor_id="user:alice",
        timestamp=datetime(2026, 2, 16, 12, 0, 0),
        source="user_clarification",
    )

    # mission_local: workspace (Git worktree)
    store.add_sense(
        TermSense(
            surface=TermSurface("workspace"),
            scope=GlossaryScope.MISSION_LOCAL.value,
            definition="Git worktree directory for a work package",
            provenance=provenance,
            confidence=1.0,
            status=SenseStatus.ACTIVE,
        )
    )

    # team_domain: workspace (VS Code workspace)
    store.add_sense(
        TermSense(
            surface=TermSurface("workspace"),
            scope=GlossaryScope.TEAM_DOMAIN.value,
            definition="VS Code workspace configuration file",
            provenance=provenance,
            confidence=0.9,
            status=SenseStatus.ACTIVE,
        )
    )

    # team_domain: mission (workflow machine)
    store.add_sense(
        TermSense(
            surface=TermSurface("mission"),
            scope=GlossaryScope.TEAM_DOMAIN.value,
            definition="Purpose-specific workflow machine",
            provenance=provenance,
            confidence=1.0,
            status=SenseStatus.ACTIVE,
        )
    )

    # audience_domain: mission (user-facing definition)
    store.add_sense(
        TermSense(
            surface=TermSurface("mission"),
            scope=GlossaryScope.AUDIENCE_DOMAIN.value,
            definition="A project goal or objective",
            provenance=provenance,
            confidence=0.8,
            status=SenseStatus.ACTIVE,
        )
    )

    # spec_kitty_core: feature (canonical definition)
    store.add_sense(
        TermSense(
            surface=TermSurface("feature"),
            scope=GlossaryScope.SPEC_KITTY_CORE.value,
            definition="A unit of work with specifications and work packages",
            provenance=provenance,
            confidence=1.0,
            status=SenseStatus.ACTIVE,
        )
    )

    return store


def test_resolve_term_single_match(glossary_store: GlossaryStore) -> None:
    """Test resolving a term with a single match."""
    results = resolve_term("feature", SCOPE_RESOLUTION_ORDER, glossary_store)

    assert len(results) == 1
    assert results[0].surface.surface_text == "feature"
    assert results[0].scope == GlossaryScope.SPEC_KITTY_CORE.value


def test_resolve_term_no_match(glossary_store: GlossaryStore) -> None:
    """Test resolving a term with no matches."""
    results = resolve_term("nonexistent", SCOPE_RESOLUTION_ORDER, glossary_store)

    assert len(results) == 0


def test_resolve_term_multiple_scopes(glossary_store: GlossaryStore) -> None:
    """Test resolving a term with matches in multiple scopes."""
    results = resolve_term("mission", SCOPE_RESOLUTION_ORDER, glossary_store)

    assert len(results) == 2
    # Results should be in scope precedence order
    assert results[0].scope == GlossaryScope.TEAM_DOMAIN.value
    assert results[1].scope == GlossaryScope.AUDIENCE_DOMAIN.value


def test_resolve_term_scope_precedence(glossary_store: GlossaryStore) -> None:
    """Test that resolution respects scope precedence order."""
    results = resolve_term("workspace", SCOPE_RESOLUTION_ORDER, glossary_store)

    assert len(results) == 2
    # mission_local (highest precedence) should come first
    assert results[0].scope == GlossaryScope.MISSION_LOCAL.value
    assert results[0].definition == "Git worktree directory for a work package"
    # team_domain should come second
    assert results[1].scope == GlossaryScope.TEAM_DOMAIN.value
    assert results[1].definition == "VS Code workspace configuration file"


def test_resolve_term_custom_scope_order(glossary_store: GlossaryStore) -> None:
    """Test resolving with a custom scope order."""
    custom_order = [GlossaryScope.AUDIENCE_DOMAIN, GlossaryScope.TEAM_DOMAIN]
    results = resolve_term("mission", custom_order, glossary_store)

    assert len(results) == 2
    # Custom order: audience_domain should come first
    assert results[0].scope == GlossaryScope.AUDIENCE_DOMAIN.value
    assert results[1].scope == GlossaryScope.TEAM_DOMAIN.value


def test_resolve_term_limited_scopes(glossary_store: GlossaryStore) -> None:
    """Test resolving with only specific scopes."""
    limited_scopes = [GlossaryScope.TEAM_DOMAIN]
    results = resolve_term("workspace", limited_scopes, glossary_store)

    # Should only find team_domain match, not mission_local
    assert len(results) == 1
    assert results[0].scope == GlossaryScope.TEAM_DOMAIN.value


def test_resolve_term_normalized_surface(glossary_store: GlossaryStore) -> None:
    """Test that resolution works with normalized surface text."""
    # Add a term with normalized surface
    provenance = Provenance(
        actor_id="user:alice",
        timestamp=datetime(2026, 2, 16, 12, 0, 0),
        source="user_clarification",
    )

    glossary_store.add_sense(
        TermSense(
            surface=TermSurface("worktree"),
            scope=GlossaryScope.TEAM_DOMAIN.value,
            definition="Git worktree",
            provenance=provenance,
            confidence=1.0,
            status=SenseStatus.ACTIVE,
        )
    )

    # Resolution should work with exact normalized surface
    results = resolve_term("worktree", SCOPE_RESOLUTION_ORDER, glossary_store)
    assert len(results) == 1
    assert results[0].surface.surface_text == "worktree"


def test_resolve_term_empty_scopes(glossary_store: GlossaryStore) -> None:
    """Test resolving with empty scope list."""
    results = resolve_term("workspace", [], glossary_store)

    # No scopes to search = no results
    assert len(results) == 0


def test_resolve_term_caching(glossary_store: GlossaryStore) -> None:
    """Test that repeated lookups use cache (performance)."""
    # First lookup
    results1 = resolve_term("workspace", SCOPE_RESOLUTION_ORDER, glossary_store)

    # Second lookup (should hit cache)
    results2 = resolve_term("workspace", SCOPE_RESOLUTION_ORDER, glossary_store)

    # Results should be identical
    assert len(results1) == len(results2)
    assert results1[0].surface.surface_text == results2[0].surface.surface_text

    # Cache should be used (same object references)
    # Note: This is an implementation detail, but validates caching works
    cache_info = glossary_store._lookup_cached.cache_info()
    assert cache_info.hits > 0

import pytest
from datetime import datetime
from specify_cli.glossary.store import GlossaryStore
from specify_cli.glossary.models import (
    TermSurface, TermSense, Provenance, SenseStatus,
)

def test_glossary_store_add_lookup(sample_term_sense, tmp_path):
    """Can add and look up senses."""
    store = GlossaryStore(tmp_path / "events")
    store.add_sense(sample_term_sense)

    results = store.lookup("workspace", ("team_domain",))
    assert len(results) == 1
    assert results[0].definition == "Git worktree directory for a work package"

def test_glossary_store_scope_order(tmp_path):
    """Lookup respects scope order."""
    store = GlossaryStore(tmp_path)

    # Add sense in team_domain
    sense1 = TermSense(
        surface=TermSurface("workspace"),
        scope="team_domain",
        definition="Team domain definition",
        provenance=Provenance("user:alice", datetime.now(), "user"),
        confidence=0.9,
    )
    store.add_sense(sense1)

    # Add sense in spec_kitty_core
    sense2 = TermSense(
        surface=TermSurface("workspace"),
        scope="spec_kitty_core",
        definition="Spec Kitty core definition",
        provenance=Provenance("system", datetime.now(), "system"),
        confidence=1.0,
    )
    store.add_sense(sense2)

    # Lookup with team_domain first (higher precedence)
    results = store.lookup("workspace", ("team_domain", "spec_kitty_core"))
    assert len(results) == 2
    assert results[0].scope == "team_domain"  # Higher precedence first

def test_glossary_store_empty_lookup(tmp_path):
    """Returns empty list if term not found."""
    store = GlossaryStore(tmp_path)
    results = store.lookup("nonexistent", ("team_domain",))
    assert results == []

def test_scope_resolution_hierarchy(tmp_path):
    """Resolution follows mission_local -> team_domain -> audience_domain -> spec_kitty_core."""
    store = GlossaryStore(tmp_path)

    # Add term in spec_kitty_core (lowest precedence)
    store.add_sense(TermSense(
        surface=TermSurface("workspace"),
        scope="spec_kitty_core",
        definition="Spec Kitty core definition",
        provenance=Provenance("system", datetime.now(), "system"),
        confidence=1.0,
    ))

    # Lookup with full hierarchy
    results = store.lookup("workspace", (
        "mission_local", "team_domain", "audience_domain", "spec_kitty_core"
    ))
    assert len(results) == 1
    assert results[0].scope == "spec_kitty_core"

    # Add term in team_domain (higher precedence)
    store.add_sense(TermSense(
        surface=TermSurface("workspace"),
        scope="team_domain",
        definition="Team domain definition",
        provenance=Provenance("user:alice", datetime.now(), "user"),
        confidence=0.9,
    ))

    # Now both are found, team_domain first
    results = store.lookup("workspace", (
        "mission_local", "team_domain", "audience_domain", "spec_kitty_core"
    ))
    assert len(results) == 2
    assert results[0].scope == "team_domain"
    assert results[1].scope == "spec_kitty_core"

def test_scope_resolution_skip_missing(tmp_path):
    """Skips scopes cleanly if not configured."""
    store = GlossaryStore(tmp_path)

    # Only add to spec_kitty_core
    store.add_sense(TermSense(
        surface=TermSurface("workspace"),
        scope="spec_kitty_core",
        definition="Definition",
        provenance=Provenance("system", datetime.now(), "system"),
        confidence=1.0,
    ))

    # Lookup with team_domain missing - should still find spec_kitty_core
    results = store.lookup("workspace", ("team_domain", "spec_kitty_core"))
    assert len(results) == 1


def test_lookup_cache_hit_and_invalidation(tmp_path):
    """Lookup uses LRU cache and invalidates on add_sense."""
    store = GlossaryStore(tmp_path)

    # Add initial sense
    sense1 = TermSense(
        surface=TermSurface("workspace"),
        scope="team_domain",
        definition="Initial definition",
        provenance=Provenance("user:alice", datetime.now(), "user"),
        confidence=0.9,
    )
    store.add_sense(sense1)

    # First lookup - cache miss
    results1 = store.lookup("workspace", ("team_domain",))
    assert len(results1) == 1
    assert results1[0].definition == "Initial definition"

    # Second lookup with same args - should hit cache
    results2 = store.lookup("workspace", ("team_domain",))
    assert len(results2) == 1
    assert results2[0].definition == "Initial definition"

    # Cache hit: verify cache_info exists
    cache_info = store._lookup_cached.cache_info()
    assert cache_info.hits > 0  # At least one cache hit
    assert cache_info.misses > 0  # At least one cache miss

    # Add new sense - should invalidate cache
    sense2 = TermSense(
        surface=TermSurface("workspace"),
        scope="team_domain",
        definition="Updated definition",
        provenance=Provenance("user:bob", datetime.now(), "user"),
        confidence=0.95,
    )
    store.add_sense(sense2)

    # Cache should be cleared - next lookup should be cache miss
    cache_info_after_add = store._lookup_cached.cache_info()
    assert cache_info_after_add.hits == 0  # Cache was cleared
    assert cache_info_after_add.misses == 0  # Cache was cleared

    # Lookup after invalidation - should see both senses
    results3 = store.lookup("workspace", ("team_domain",))
    assert len(results3) == 2  # Both senses returned
    assert results3[0].definition == "Initial definition"
    assert results3[1].definition == "Updated definition"

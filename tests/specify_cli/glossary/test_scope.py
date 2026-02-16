import pytest
from unittest.mock import MagicMock
from specify_cli.glossary.scope import (
    GlossaryScope,
    SCOPE_RESOLUTION_ORDER,
    get_scope_precedence,
    should_use_scope,
    load_seed_file,
    validate_seed_file,
    activate_scope,
)
from specify_cli.glossary.models import SenseStatus

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

def test_validate_seed_file():
    """validate_seed_file checks schema."""
    # Valid
    validate_seed_file({"terms": [{"surface": "foo", "definition": "bar"}]})

    # Missing terms key
    with pytest.raises(ValueError, match="must have 'terms' key"):
        validate_seed_file({})

    # Missing surface
    with pytest.raises(ValueError, match="must have 'surface' key"):
        validate_seed_file({"terms": [{"definition": "bar"}]})

    # Missing definition
    with pytest.raises(ValueError, match="must have 'definition' key"):
        validate_seed_file({"terms": [{"surface": "foo"}]})

def test_load_seed_file(sample_seed_file, tmp_path):
    """Can load seed file and parse terms."""
    senses = load_seed_file(GlossaryScope.TEAM_DOMAIN, tmp_path)

    assert len(senses) == 2
    assert senses[0].surface.surface_text == "workspace"
    assert senses[0].definition == "Git worktree directory for a work package"
    assert senses[0].confidence == 1.0
    assert senses[0].status == SenseStatus.ACTIVE

def test_load_seed_file_missing(tmp_path):
    """Returns empty list if seed file missing."""
    senses = load_seed_file(GlossaryScope.TEAM_DOMAIN, tmp_path)
    assert senses == []

def test_activate_scope():
    """Emits GlossaryScopeActivated event."""
    mock_emitter = MagicMock()

    activate_scope(
        GlossaryScope.TEAM_DOMAIN,
        version_id="v3",
        mission_id="041-mission",
        run_id="run-001",
        event_emitter=mock_emitter,
    )

    mock_emitter.emit.assert_called_once()
    call_args = mock_emitter.emit.call_args
    assert call_args[1]["event_type"] == "GlossaryScopeActivated"
    assert call_args[1]["payload"]["scope_id"] == "team_domain"

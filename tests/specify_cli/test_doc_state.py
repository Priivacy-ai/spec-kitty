"""Tests for documentation state management."""

import json
from datetime import datetime

import pytest

from specify_cli.doc_state import (
    set_iteration_mode,
    set_divio_types_selected,
    set_generators_configured,
    set_audit_metadata,
    read_documentation_state,
    initialize_documentation_state,
    update_documentation_state,
    ensure_documentation_state,
    get_state_version,
)


# Test state initialization
def test_initialize_documentation_state(tmp_path):
    """Test initialization creates valid state."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"feature_number": "001", "mission": "documentation"}))

    state = initialize_documentation_state(
        meta_file,
        iteration_mode="initial",
        divio_types=["tutorial", "reference"],
        generators=[{"name": "sphinx", "language": "python", "config_path": "docs/conf.py"}],
        target_audience="developers",
    )

    assert state["iteration_mode"] == "initial"
    assert state["divio_types_selected"] == ["tutorial", "reference"]
    assert len(state["generators_configured"]) == 1
    assert state["target_audience"] == "developers"
    assert state["last_audit_date"] is None
    assert state["coverage_percentage"] == 0.0

    # Verify written to file
    with open(meta_file) as f:
        meta = json.load(f)
    assert "documentation_state" in meta


# Test state reading
def test_read_documentation_state(tmp_path):
    """Test reading state from meta.json."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(
        json.dumps(
            {
                "mission": "documentation",
                "documentation_state": {
                    "iteration_mode": "gap_filling",
                    "divio_types_selected": ["tutorial"],
                    "generators_configured": [],
                    "target_audience": "end-users",
                    "last_audit_date": "2026-01-12T00:00:00Z",
                    "coverage_percentage": 0.5,
                },
            }
        )
    )

    state = read_documentation_state(meta_file)
    assert state is not None
    assert state["iteration_mode"] == "gap_filling"
    assert state["coverage_percentage"] == 0.5


# Test state updates
def test_update_documentation_state(tmp_path):
    """Test partial state updates."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"feature_number": "001", "mission": "documentation"}))

    # Initialize
    initialize_documentation_state(
        meta_file, iteration_mode="initial", divio_types=[], generators=[], target_audience="developers"
    )

    # Update
    updated = update_documentation_state(meta_file, iteration_mode="gap_filling", coverage_percentage=0.75)

    assert updated["iteration_mode"] == "gap_filling"
    assert updated["coverage_percentage"] == 0.75
    assert updated["target_audience"] == "developers"  # Unchanged


# Test backward compatibility
def test_ensure_state_for_old_feature(tmp_path):
    """Test migration adds state to old features."""
    # Old feature without documentation_state
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(
        json.dumps({"feature_number": "001", "mission": "documentation", "created_at": "2025-01-01T00:00:00Z"})
    )

    ensure_documentation_state(meta_file)

    # Verify state was added
    with open(meta_file) as f:
        meta = json.load(f)
    assert "documentation_state" in meta
    assert meta["documentation_state"]["iteration_mode"] == "initial"


# Test non-documentation missions unaffected
def test_read_state_for_non_doc_mission(tmp_path):
    """Test returns None for non-documentation missions."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "software-dev"}))

    state = read_documentation_state(meta_file)
    assert state is None


def test_ensure_state_ignores_non_doc_mission(tmp_path):
    """Test ensure_state ignores non-documentation missions."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "software-dev"}))

    ensure_documentation_state(meta_file)

    with open(meta_file) as f:
        meta = json.load(f)
    assert "documentation_state" not in meta


# Test individual setters
def test_set_iteration_mode(tmp_path):
    """Test set_iteration_mode updates state."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    set_iteration_mode(meta_file, "gap_filling")

    with open(meta_file) as f:
        meta = json.load(f)
    assert meta["documentation_state"]["iteration_mode"] == "gap_filling"


def test_set_divio_types_selected(tmp_path):
    """Test set_divio_types_selected updates state."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    set_divio_types_selected(meta_file, ["tutorial", "how-to"])

    with open(meta_file) as f:
        meta = json.load(f)
    assert meta["documentation_state"]["divio_types_selected"] == ["tutorial", "how-to"]


def test_set_generators_configured(tmp_path):
    """Test set_generators_configured updates state."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    generators = [{"name": "sphinx", "language": "python", "config_path": "docs/conf.py"}]
    set_generators_configured(meta_file, generators)

    with open(meta_file) as f:
        meta = json.load(f)
    assert len(meta["documentation_state"]["generators_configured"]) == 1
    assert meta["documentation_state"]["generators_configured"][0]["name"] == "sphinx"


def test_set_audit_metadata(tmp_path):
    """Test set_audit_metadata updates state."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    audit_date = datetime(2026, 1, 12, 10, 30, 0)
    set_audit_metadata(meta_file, audit_date, 0.75)

    with open(meta_file) as f:
        meta = json.load(f)
    assert meta["documentation_state"]["last_audit_date"] == "2026-01-12T10:30:00"
    assert meta["documentation_state"]["coverage_percentage"] == 0.75


# Test validation
def test_invalid_iteration_mode_rejected(tmp_path):
    """Test invalid iteration_mode raises ValueError."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    with pytest.raises(ValueError, match="Invalid iteration_mode"):
        set_iteration_mode(meta_file, "invalid_mode")


def test_invalid_divio_type_rejected(tmp_path):
    """Test invalid Divio type raises ValueError."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    with pytest.raises(ValueError, match="Invalid Divio types"):
        set_divio_types_selected(meta_file, ["tutorial", "invalid-type"])


def test_invalid_generator_config_rejected(tmp_path):
    """Test invalid generator config raises ValueError."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    # Missing 'name' field
    with pytest.raises(ValueError, match="missing 'name' field"):
        set_generators_configured(meta_file, [{"language": "python"}])

    # Invalid generator name
    with pytest.raises(ValueError, match="Invalid generator name"):
        set_generators_configured(meta_file, [{"name": "invalid", "language": "python", "config_path": "docs/conf.py"}])


def test_invalid_coverage_percentage_rejected(tmp_path):
    """Test invalid coverage_percentage raises ValueError."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    # Too high
    with pytest.raises(ValueError, match="must be 0.0-1.0"):
        set_audit_metadata(meta_file, None, 1.5)

    # Negative
    with pytest.raises(ValueError, match="must be 0.0-1.0"):
        set_audit_metadata(meta_file, None, -0.1)


# Test empty lists allowed
def test_empty_divio_types_allowed(tmp_path):
    """Test empty divio_types list is allowed."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    # Should not raise
    initialize_documentation_state(
        meta_file,
        iteration_mode="initial",
        divio_types=[],  # Empty
        generators=[],
        target_audience="developers",
    )

    state = read_documentation_state(meta_file)
    assert state["divio_types_selected"] == []


def test_empty_generators_allowed(tmp_path):
    """Test empty generators list is allowed."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    # Should not raise
    initialize_documentation_state(
        meta_file,
        iteration_mode="initial",
        divio_types=[],
        generators=[],  # Empty
        target_audience="developers",
    )

    state = read_documentation_state(meta_file)
    assert state["generators_configured"] == []


# Test update without initialization fails
def test_update_without_initialization_raises(tmp_path):
    """Test update raises error if state doesn't exist."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation"}))

    with pytest.raises(ValueError, match="No documentation state found"):
        update_documentation_state(meta_file, coverage_percentage=0.5)


# Test state version
def test_get_state_version():
    """Test get_state_version returns version number."""
    state = {
        "iteration_mode": "initial",
        "divio_types_selected": [],
        "generators_configured": [],
        "target_audience": "developers",
        "last_audit_date": None,
        "coverage_percentage": 0.0,
    }

    version = get_state_version(state)
    assert version == 1  # Default version


# Test JSON formatting
def test_state_persists_with_proper_json_formatting(tmp_path):
    """Test state is written with proper JSON formatting."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"mission": "documentation", "feature_number": "001"}))

    initialize_documentation_state(
        meta_file,
        iteration_mode="initial",
        divio_types=["tutorial"],
        generators=[{"name": "sphinx", "language": "python", "config_path": "docs/conf.py"}],
        target_audience="developers",
    )

    # Read raw JSON to verify formatting
    content = meta_file.read_text()

    # Should be valid JSON
    data = json.loads(content)
    assert "documentation_state" in data

    # Should be indented (not minified)
    assert "  " in content or "\t" in content


# Test original fields preserved
def test_original_fields_preserved_after_state_update(tmp_path):
    """Test original meta.json fields are preserved."""
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(
        json.dumps(
            {
                "feature_number": "012",
                "mission": "documentation",
                "created_at": "2026-01-13T00:00:00Z",
                "custom_field": "custom_value",
            }
        )
    )

    initialize_documentation_state(
        meta_file, iteration_mode="initial", divio_types=[], generators=[], target_audience="developers"
    )

    with open(meta_file) as f:
        meta = json.load(f)

    # Original fields should still exist
    assert meta["feature_number"] == "012"
    assert meta["mission"] == "documentation"
    assert meta["created_at"] == "2026-01-13T00:00:00Z"
    assert meta["custom_field"] == "custom_value"

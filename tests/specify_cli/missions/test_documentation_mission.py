"""Tests for documentation mission configuration."""

import pytest
from pathlib import Path

from specify_cli.mission_system import (
    Mission,
    MissionError,
    get_mission_by_name,
    list_available_missions
)


# Get source missions directory for testing
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_MISSIONS_DIR = REPO_ROOT / "src" / "specify_cli"


# T054: Test mission.yaml Loading
def test_documentation_mission_loads():
    """Test documentation mission loads from src/specify_cli/missions/."""
    mission_dir = SOURCE_MISSIONS_DIR / "missions" / "documentation"
    mission = Mission(mission_dir)

    assert mission.name == "Documentation Kitty"
    assert mission.domain == "other"
    assert mission.version == "1.0.0"


def test_documentation_mission_in_list():
    """Test documentation mission directory exists in source."""
    mission_dir = SOURCE_MISSIONS_DIR / "missions" / "documentation"

    assert mission_dir.exists()
    assert (mission_dir / "mission.yaml").exists()


def test_documentation_mission_config_valid():
    """Test mission.yaml passes pydantic validation."""
    mission_dir = SOURCE_MISSIONS_DIR / "missions" / "documentation"
    mission = Mission(mission_dir)

    # Access config to trigger validation
    config = mission.config

    assert config.name is not None
    assert config.version is not None
    assert len(config.workflow.phases) > 0


# T055: Test Workflow Phases
def test_documentation_mission_workflow_phases():
    """Test documentation mission has 6 workflow phases."""
    mission_dir = SOURCE_MISSIONS_DIR / "missions" / "documentation"
    mission = Mission(mission_dir)
    phases = mission.get_workflow_phases()

    assert len(phases) == 6

    # Check phase names in order
    phase_names = [p["name"] for p in phases]
    assert phase_names == [
        "discover",
        "audit",
        "design",
        "generate",
        "validate",
        "publish"
    ]


def test_documentation_mission_phase_descriptions():
    """Test each phase has description."""
    mission_dir = SOURCE_MISSIONS_DIR / "missions" / "documentation"
    mission = Mission(mission_dir)
    phases = mission.get_workflow_phases()

    for phase in phases:
        assert "description" in phase
        assert len(phase["description"]) > 0


# T056: Test Artifacts and Paths
def test_documentation_mission_required_artifacts():
    """Test documentation mission requires appropriate artifacts."""
    mission_dir = SOURCE_MISSIONS_DIR / "missions" / "documentation"
    mission = Mission(mission_dir)
    required = mission.get_required_artifacts()

    assert "spec.md" in required
    assert "plan.md" in required
    assert "tasks.md" in required
    assert "gap-analysis.md" in required


def test_documentation_mission_optional_artifacts():
    """Test documentation mission has optional artifacts."""
    mission_dir = SOURCE_MISSIONS_DIR / "missions" / "documentation"
    mission = Mission(mission_dir)
    optional = mission.get_optional_artifacts()

    # Should include divio-templates, generator-configs, etc.
    assert "divio-templates/" in optional or "research.md" in optional
    assert "release.md" in optional


def test_documentation_mission_path_conventions():
    """Test documentation mission defines path conventions."""
    mission_dir = SOURCE_MISSIONS_DIR / "missions" / "documentation"
    mission = Mission(mission_dir)
    paths = mission.get_path_conventions()

    assert "workspace" in paths
    assert paths["workspace"] == "docs/"
    assert "deliverables" in paths

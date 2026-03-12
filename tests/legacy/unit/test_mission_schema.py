#!/usr/bin/env python3
"""Legacy mission schema loading tests for the 1.x mission format."""

from __future__ import annotations

from specify_cli.mission import Mission
from tests.unit.test_mission_schema import MISSIONS_ROOT


def test_loads_software_dev_mission() -> None:
    """Existing software-dev mission.yaml remains valid."""
    mission_dir = MISSIONS_ROOT / "software-dev"
    mission = Mission(mission_dir)

    assert mission.name == "Software Dev Kitty"
    assert len(mission.get_workflow_phases()) >= 5
    assert "git_clean" in mission.get_validation_checks()
    assert mission.config.workflow.phases[0].name == "research"


def test_loads_research_mission() -> None:
    """Existing research mission.yaml remains valid."""
    mission_dir = MISSIONS_ROOT / "research"
    mission = Mission(mission_dir)

    assert mission.domain == "research"
    assert mission.get_required_artifacts()
    assert mission.config.validation.custom_validators is True

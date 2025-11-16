#!/usr/bin/env python3
"""Unit tests for mission schema validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from specify_cli.mission import Mission, MissionError


REPO_ROOT = Path(__file__).resolve().parents[2]
MISSIONS_ROOT = REPO_ROOT / ".kittify" / "missions"


def build_valid_config(**overrides: Any) -> Dict[str, Any]:
    """Return a baseline valid mission configuration for testing."""
    config: Dict[str, Any] = {
        "name": "Test Mission",
        "description": "Mission used for schema validation tests",
        "version": "1.0.0",
        "domain": "software",
        "workflow": {"phases": [{"name": "implement", "description": "Do the work"}]},
        "artifacts": {"required": ["spec.md"], "optional": ["plan.md"]},
        "paths": {"workspace": "src/"},
        "validation": {"checks": ["git_clean"], "custom_validators": False},
    }
    config.update(overrides)
    return config


def _write_mission(tmp_path: Path, config: Dict[str, Any]) -> Path:
    """Write YAML config to temp mission directory."""
    mission_dir = tmp_path / "mission"
    mission_dir.mkdir()
    (mission_dir / "mission.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return mission_dir


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


def test_missing_required_field_raises_error(tmp_path: Path) -> None:
    """Missing required fields should raise MissionError with helpful message."""
    config = build_valid_config()
    config.pop("name", None)
    mission_dir = _write_mission(tmp_path, config)

    with pytest.raises(MissionError) as excinfo:
        Mission(mission_dir)

    message = str(excinfo.value)
    assert "name" in message
    assert "Field required" in message


def test_typo_field_reports_extra_input(tmp_path: Path) -> None:
    """Typos such as 'validaton' should produce extra field errors."""
    config = build_valid_config()
    config["validaton"] = {"checks": ["git_clean"]}
    mission_dir = _write_mission(tmp_path, config)

    with pytest.raises(MissionError) as excinfo:
        Mission(mission_dir)

    message = str(excinfo.value)
    assert "validaton" in message
    assert "valid root fields" in message


def test_invalid_version_type_is_reported(tmp_path: Path) -> None:
    """Wrong types (int version) should be rejected."""
    config = build_valid_config(version=1)  # type: ignore[arg-type]
    mission_dir = _write_mission(tmp_path, config)

    with pytest.raises(MissionError) as excinfo:
        Mission(mission_dir)

    message = str(excinfo.value)
    assert "version" in message
    assert "valid string" in message

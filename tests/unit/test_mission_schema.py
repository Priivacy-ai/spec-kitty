#!/usr/bin/env python3
"""Unit tests for mission schema validation and per-feature mission functions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from specify_cli.mission_system import (
    Mission,
    MissionError,
    MissionNotFoundError,
    discover_missions,
    get_feature_mission_key,
    get_mission_for_feature,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MISSIONS_ROOT = REPO_ROOT / "src" / "specify_cli" / "missions"


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


# =============================================================================
# Per-Feature Mission Tests (T004, T005)
# =============================================================================


@pytest.fixture
def sample_kittify_dir(tmp_path: Path) -> Path:
    """Create a sample .kittify directory with software-dev and research missions."""
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions"

    # Create software-dev mission
    software_dev = missions_dir / "software-dev"
    software_dev.mkdir(parents=True)
    software_dev_config = {
        "name": "Software Dev Kitty",
        "description": "Build software",
        "version": "1.0.0",
        "domain": "software",
        "workflow": {"phases": [{"name": "implement", "description": "Code it"}]},
        "artifacts": {"required": ["spec.md"], "optional": []},
    }
    (software_dev / "mission.yaml").write_text(yaml.safe_dump(software_dev_config))

    # Create research mission
    research = missions_dir / "research"
    research.mkdir(parents=True)
    research_config = {
        "name": "Deep Research Kitty",
        "description": "Conduct research",
        "version": "1.0.0",
        "domain": "research",
        "workflow": {"phases": [{"name": "gather", "description": "Collect data"}]},
        "artifacts": {"required": ["findings.md"], "optional": []},
    }
    (research / "mission.yaml").write_text(yaml.safe_dump(research_config))

    return kittify_dir


@pytest.fixture
def feature_with_mission(tmp_path: Path, sample_kittify_dir: Path) -> Path:
    """Create a feature directory with mission field in meta.json."""
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    meta = {
        "feature_number": "001",
        "slug": "001-test-feature",
        "friendly_name": "Test Feature",
        "mission": "software-dev",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta))
    return feature_dir


@pytest.fixture
def feature_with_research_mission(tmp_path: Path, sample_kittify_dir: Path) -> Path:
    """Create a feature directory with research mission in meta.json."""
    feature_dir = tmp_path / "kitty-specs" / "002-research-feature"
    feature_dir.mkdir(parents=True)
    meta = {
        "feature_number": "002",
        "slug": "002-research-feature",
        "friendly_name": "Research Feature",
        "mission": "research",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta))
    return feature_dir


@pytest.fixture
def legacy_feature(tmp_path: Path, sample_kittify_dir: Path) -> Path:
    """Create a feature directory WITHOUT mission field (legacy)."""
    feature_dir = tmp_path / "kitty-specs" / "000-legacy"
    feature_dir.mkdir(parents=True)
    meta = {
        "feature_number": "000",
        "slug": "000-legacy",
        "friendly_name": "Legacy Feature",
        # NO mission field - simulates pre-v0.8.0 feature
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta))
    return feature_dir


@pytest.fixture
def feature_with_invalid_mission(tmp_path: Path, sample_kittify_dir: Path) -> Path:
    """Create a feature with a mission that doesn't exist."""
    feature_dir = tmp_path / "kitty-specs" / "003-invalid"
    feature_dir.mkdir(parents=True)
    meta = {
        "feature_number": "003",
        "slug": "003-invalid",
        "friendly_name": "Invalid Mission Feature",
        "mission": "nonexistent-mission",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta))
    return feature_dir


class TestGetFeatureMissionKey:
    """Tests for get_feature_mission_key() helper function."""

    def test_returns_mission_from_meta_json(self, feature_with_mission: Path) -> None:
        """Should extract mission key from meta.json."""
        assert get_feature_mission_key(feature_with_mission) == "software-dev"

    def test_returns_research_mission(self, feature_with_research_mission: Path) -> None:
        """Should extract research mission key."""
        assert get_feature_mission_key(feature_with_research_mission) == "research"

    def test_defaults_to_software_dev_when_no_mission_field(
        self, legacy_feature: Path
    ) -> None:
        """Should default to software-dev when mission field is missing."""
        assert get_feature_mission_key(legacy_feature) == "software-dev"

    def test_defaults_to_software_dev_when_no_meta_json(self, tmp_path: Path) -> None:
        """Should default to software-dev when meta.json doesn't exist."""
        empty_feature = tmp_path / "kitty-specs" / "empty"
        empty_feature.mkdir(parents=True)
        assert get_feature_mission_key(empty_feature) == "software-dev"

    def test_defaults_to_software_dev_on_invalid_json(self, tmp_path: Path) -> None:
        """Should default to software-dev when meta.json is invalid JSON."""
        feature_dir = tmp_path / "kitty-specs" / "bad-json"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text("{ invalid json }")
        assert get_feature_mission_key(feature_dir) == "software-dev"


class TestGetMissionForFeature:
    """Tests for get_mission_for_feature() function (T004)."""

    def test_returns_correct_mission(
        self, feature_with_mission: Path, sample_kittify_dir: Path
    ) -> None:
        """Should return the mission specified in meta.json."""
        mission = get_mission_for_feature(
            feature_with_mission, sample_kittify_dir.parent
        )
        assert mission.name == "Software Dev Kitty"
        assert mission.domain == "software"

    def test_returns_research_mission(
        self, feature_with_research_mission: Path, sample_kittify_dir: Path
    ) -> None:
        """Should return research mission when specified."""
        mission = get_mission_for_feature(
            feature_with_research_mission, sample_kittify_dir.parent
        )
        assert mission.name == "Deep Research Kitty"
        assert mission.domain == "research"

    def test_falls_back_on_invalid_mission(
        self, feature_with_invalid_mission: Path, sample_kittify_dir: Path
    ) -> None:
        """Should fall back to software-dev when mission doesn't exist."""
        with pytest.warns(UserWarning, match="not found"):
            mission = get_mission_for_feature(
                feature_with_invalid_mission, sample_kittify_dir.parent
            )
        assert mission.domain == "software"

    def test_raises_when_no_kittify_dir(self, tmp_path: Path) -> None:
        """Should raise MissionNotFoundError when .kittify not found."""
        feature_dir = tmp_path / "orphan-feature"
        feature_dir.mkdir(parents=True)
        meta = {"feature_number": "999", "slug": "orphan", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        with pytest.raises(MissionNotFoundError, match="Could not find .kittify"):
            get_mission_for_feature(feature_dir)


class TestGetMissionForFeatureLegacy:
    """Tests for backward compatibility with legacy features (T005)."""

    def test_legacy_feature_defaults_to_software_dev(
        self, legacy_feature: Path, sample_kittify_dir: Path
    ) -> None:
        """Features without mission field should use software-dev."""
        mission = get_mission_for_feature(legacy_feature, sample_kittify_dir.parent)
        assert mission.domain == "software"
        assert "software" in mission.name.lower()

    def test_legacy_feature_no_warning(
        self, legacy_feature: Path, sample_kittify_dir: Path
    ) -> None:
        """Legacy features should not produce warning (default is intentional)."""
        import warnings as w

        with w.catch_warnings(record=True) as caught:
            w.simplefilter("always")
            get_mission_for_feature(legacy_feature, sample_kittify_dir.parent)
            # Should not warn since software-dev exists and is the default
            mission_warnings = [
                c for c in caught if "mission" in str(c.message).lower()
            ]
            assert len(mission_warnings) == 0


class TestDiscoverMissions:
    """Tests for discover_missions() function."""

    def test_discovers_all_missions(self, sample_kittify_dir: Path) -> None:
        """Should find all valid missions in .kittify/missions/."""
        missions = discover_missions(sample_kittify_dir.parent)
        assert "software-dev" in missions
        assert "research" in missions
        assert len(missions) == 2

    def test_returns_mission_and_source_tuple(self, sample_kittify_dir: Path) -> None:
        """Should return (Mission, source) tuples."""
        missions = discover_missions(sample_kittify_dir.parent)
        mission, source = missions["software-dev"]
        assert isinstance(mission, Mission)
        assert source == "project"

    def test_returns_empty_dict_when_no_kittify(self, tmp_path: Path) -> None:
        """Should return empty dict when .kittify doesn't exist."""
        assert discover_missions(tmp_path) == {}

    def test_returns_empty_dict_when_no_missions_dir(self, tmp_path: Path) -> None:
        """Should return empty dict when missions/ doesn't exist."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        assert discover_missions(tmp_path) == {}

    def test_skips_invalid_missions(self, sample_kittify_dir: Path) -> None:
        """Should skip missions with invalid mission.yaml."""
        # Create invalid mission
        invalid_dir = sample_kittify_dir / "missions" / "broken"
        invalid_dir.mkdir()
        (invalid_dir / "mission.yaml").write_text("name: Missing Required Fields")

        with pytest.warns(UserWarning, match="Skipping invalid mission"):
            missions = discover_missions(sample_kittify_dir.parent)

        assert "broken" not in missions
        assert "software-dev" in missions

    def test_skips_directories_without_mission_yaml(
        self, sample_kittify_dir: Path
    ) -> None:
        """Should skip directories that don't have mission.yaml."""
        # Create directory without mission.yaml
        empty_dir = sample_kittify_dir / "missions" / "empty-dir"
        empty_dir.mkdir()

        missions = discover_missions(sample_kittify_dir.parent)
        assert "empty-dir" not in missions

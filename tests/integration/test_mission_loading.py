"""Integration tests for load_mission() dispatch.

Verifies that load_mission() and load_mission_by_name() correctly
auto-detect v0 vs v1 mission configs and return the appropriate type.

Covers:
- v1 config -> StateMachineMission
- v0 config -> PhaseMission
- Hybrid config (v1 + v0 keys) -> StateMachineMission
- Missing mission.yaml -> MissionNotFoundError
- Invalid v1 schema -> MissionValidationError
- Both types satisfy MissionProtocol
- load_mission_by_name convenience function
- Backward compat: Mission(path) still works for v0
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specify_cli.mission import Mission, MissionNotFoundError
from specify_cli.mission_v1 import (
    MissionProtocol,
    PhaseMission,
    StateMachineMission,
    load_mission,
    load_mission_by_name,
)
from specify_cli.mission_v1.schema import MissionValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> None:
    """Write a dict to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _minimal_v0_config(**overrides) -> dict:
    """Return a minimal valid v0 mission config."""
    config = {
        "name": "Test v0 Mission",
        "description": "A v0 test mission",
        "version": "1.0.0",
        "domain": "software",
        "workflow": {
            "phases": [
                {"name": "research", "description": "Research phase"},
                {"name": "implement", "description": "Implementation phase"},
            ],
        },
        "artifacts": {"required": [], "optional": []},
    }
    config.update(overrides)
    return config


def _minimal_v1_config(**overrides) -> dict:
    """Return a minimal valid v1 mission config."""
    config = {
        "mission": {
            "name": "Test v1 Mission",
            "version": "2.0.0",
            "description": "A v1 test mission",
        },
        "initial": "draft",
        "states": [
            {"name": "draft"},
            {"name": "active"},
            {"name": "done"},
        ],
        "transitions": [
            {"trigger": "activate", "source": "draft", "dest": "active"},
            {"trigger": "complete", "source": "active", "dest": "done"},
        ],
    }
    config.update(overrides)
    return config


def _hybrid_config() -> dict:
    """Return a config with both v1 AND v0 keys."""
    return {
        # v1 keys
        "mission": {
            "name": "Hybrid Mission",
            "version": "3.0.0",
            "description": "A hybrid v0+v1 mission",
        },
        "initial": "start",
        "states": [
            {"name": "start"},
            {"name": "finish"},
        ],
        "transitions": [
            {"trigger": "go", "source": "start", "dest": "finish"},
        ],
        # v0 keys (should be ignored by v1 loader, schema allows additionalProperties)
        "workflow": {
            "phases": [
                {"name": "plan", "description": "Plan"},
            ],
        },
        "artifacts": {"required": ["spec.md"], "optional": []},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def v0_mission_dir(tmp_path) -> Path:
    """Create a v0 mission directory."""
    mission_dir = tmp_path / "v0-mission"
    mission_dir.mkdir()
    _write_yaml(mission_dir / "mission.yaml", _minimal_v0_config())
    return mission_dir


@pytest.fixture()
def v1_mission_dir(tmp_path) -> Path:
    """Create a v1 mission directory."""
    mission_dir = tmp_path / "v1-mission"
    mission_dir.mkdir()
    _write_yaml(mission_dir / "mission.yaml", _minimal_v1_config())
    return mission_dir


@pytest.fixture()
def hybrid_mission_dir(tmp_path) -> Path:
    """Create a hybrid mission directory (v1 + v0 keys)."""
    mission_dir = tmp_path / "hybrid-mission"
    mission_dir.mkdir()
    _write_yaml(mission_dir / "mission.yaml", _hybrid_config())
    return mission_dir


@pytest.fixture()
def kittify_dir(tmp_path, v0_mission_dir, v1_mission_dir) -> Path:
    """Create a .kittify directory with both v0 and v1 missions."""
    kittify = tmp_path / ".kittify"
    missions = kittify / "missions"
    missions.mkdir(parents=True)

    # v0 mission at .kittify/missions/software-dev/
    sw_dir = missions / "software-dev"
    sw_dir.mkdir()
    _write_yaml(sw_dir / "mission.yaml", _minimal_v0_config(name="Software Dev Kitty"))

    # v1 mission at .kittify/missions/custom-v1/
    v1_dir = missions / "custom-v1"
    v1_dir.mkdir()
    _write_yaml(
        v1_dir / "mission.yaml",
        _minimal_v1_config(
            mission={"name": "Custom v1", "version": "1.0.0", "description": "Custom"},
        ),
    )

    return kittify


# ---------------------------------------------------------------------------
# T033 -- load_mission() dispatch
# ---------------------------------------------------------------------------


class TestLoadMissionDispatch:
    """Verify load_mission() auto-detects v0 vs v1 and returns correct type."""

    def test_v1_config_returns_state_machine_mission(self, v1_mission_dir):
        result = load_mission(v1_mission_dir)
        assert isinstance(result, StateMachineMission)

    def test_v0_config_returns_phase_mission(self, v0_mission_dir):
        result = load_mission(v0_mission_dir)
        assert isinstance(result, PhaseMission)

    def test_hybrid_config_returns_state_machine_mission(self, hybrid_mission_dir):
        """Hybrid YAML (v1 + v0 fields) routes to v1 path."""
        result = load_mission(hybrid_mission_dir)
        assert isinstance(result, StateMachineMission)

    def test_missing_mission_yaml_raises(self, tmp_path):
        """load_mission() with no mission.yaml raises MissionNotFoundError."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(MissionNotFoundError, match="Mission config not found"):
            load_mission(empty_dir)

    def test_missing_directory_raises(self, tmp_path):
        """load_mission() with nonexistent directory raises MissionNotFoundError."""
        nonexistent = tmp_path / "does-not-exist"

        with pytest.raises(MissionNotFoundError, match="Mission config not found"):
            load_mission(nonexistent)

    def test_invalid_v1_schema_raises(self, tmp_path):
        """load_mission() with invalid v1 schema raises MissionValidationError."""
        mission_dir = tmp_path / "bad-v1"
        mission_dir.mkdir()

        # Has states and transitions (detected as v1) but missing required "mission" key
        bad_config = {
            "states": [{"name": "alpha"}],
            "transitions": [{"trigger": "go", "source": "alpha", "dest": "alpha"}],
            # missing "initial" and "mission" -- schema requires them
        }
        _write_yaml(mission_dir / "mission.yaml", bad_config)

        with pytest.raises(MissionValidationError):
            load_mission(mission_dir)

    def test_v1_feature_dir_passed_through(self, v1_mission_dir, tmp_path):
        """feature_dir is forwarded to StateMachineMission."""
        feature = tmp_path / "kitty-specs" / "001-feature"
        feature.mkdir(parents=True)

        result = load_mission(v1_mission_dir, feature_dir=feature)
        assert isinstance(result, StateMachineMission)
        # The model should have the feature_dir set
        assert result.model.feature_dir == feature


# ---------------------------------------------------------------------------
# T034 -- MissionProtocol
# ---------------------------------------------------------------------------


class TestMissionProtocol:
    """Verify both types satisfy the MissionProtocol."""

    def test_state_machine_mission_satisfies_protocol(self, v1_mission_dir):
        result = load_mission(v1_mission_dir)
        assert isinstance(result, MissionProtocol)

    def test_phase_mission_satisfies_protocol(self, v0_mission_dir):
        result = load_mission(v0_mission_dir)
        assert isinstance(result, MissionProtocol)

    def test_v1_has_required_properties(self, v1_mission_dir):
        m = load_mission(v1_mission_dir)
        assert isinstance(m.name, str)
        assert isinstance(m.version, str)
        assert isinstance(m.state, str)

    def test_v0_has_required_properties(self, v0_mission_dir):
        m = load_mission(v0_mission_dir)
        assert isinstance(m.name, str)
        assert isinstance(m.version, str)
        assert isinstance(m.state, str)

    def test_v1_trigger_method(self, v1_mission_dir):
        m = load_mission(v1_mission_dir)
        assert m.state == "draft"
        m.trigger("activate")
        assert m.state == "active"

    def test_v0_trigger_method(self, v0_mission_dir):
        m = load_mission(v0_mission_dir)
        assert m.state == "research"
        m.trigger("advance")
        assert m.state == "implement"

    def test_v1_get_triggers(self, v1_mission_dir):
        m = load_mission(v1_mission_dir)
        triggers = m.get_triggers()
        assert "activate" in triggers

    def test_v0_get_triggers(self, v0_mission_dir):
        m = load_mission(v0_mission_dir)
        triggers = m.get_triggers()
        assert "advance" in triggers

    def test_v1_get_states(self, v1_mission_dir):
        m = load_mission(v1_mission_dir)
        states = m.get_states()
        assert "draft" in states
        assert "active" in states
        assert "done" in states

    def test_v0_get_states(self, v0_mission_dir):
        m = load_mission(v0_mission_dir)
        states = m.get_states()
        assert "research" in states
        assert "implement" in states
        assert "done" in states  # PhaseMission adds terminal "done"


# ---------------------------------------------------------------------------
# T035 -- load_mission_by_name()
# ---------------------------------------------------------------------------


class TestLoadMissionByName:
    """Verify load_mission_by_name() convenience function."""

    def test_loads_v0_by_name(self, kittify_dir):
        result = load_mission_by_name("software-dev", kittify_dir=kittify_dir)
        assert isinstance(result, PhaseMission)
        assert result.name == "Software Dev Kitty"

    def test_loads_v1_by_name(self, kittify_dir):
        result = load_mission_by_name("custom-v1", kittify_dir=kittify_dir)
        assert isinstance(result, StateMachineMission)
        assert result.name == "Custom v1"

    def test_missing_mission_name_raises(self, kittify_dir):
        with pytest.raises(MissionNotFoundError):
            load_mission_by_name("nonexistent", kittify_dir=kittify_dir)


# ---------------------------------------------------------------------------
# T036 -- Hybrid YAML handling
# ---------------------------------------------------------------------------


class TestHybridYAML:
    """Verify correct handling of YAML with both v1 and v0 keys."""

    def test_hybrid_routes_to_v1(self, hybrid_mission_dir):
        """Hybrid config is detected as v1 due to states+transitions keys."""
        result = load_mission(hybrid_mission_dir)
        assert isinstance(result, StateMachineMission)

    def test_hybrid_v1_state_machine_works(self, hybrid_mission_dir):
        """The v1 state machine from a hybrid config functions correctly."""
        m = load_mission(hybrid_mission_dir)
        assert m.state == "start"
        m.trigger("go")
        assert m.state == "finish"

    def test_hybrid_metadata_accessible(self, hybrid_mission_dir):
        """v1 mission metadata is accessible from hybrid config."""
        m = load_mission(hybrid_mission_dir)
        assert m.name == "Hybrid Mission"
        assert m.version == "3.0.0"


# ---------------------------------------------------------------------------
# T036 -- strip_v1_keys
# ---------------------------------------------------------------------------


class TestStripV1Keys:
    """Verify strip_v1_keys removes v1-only keys correctly."""

    def test_strip_removes_all_v1_keys(self):
        from specify_cli.mission_v1.schema import strip_v1_keys

        config = {
            "states": [{"name": "a"}],
            "transitions": [],
            "initial": "a",
            "guards": {},
            "inputs": [],
            "outputs": [],
            "mission": {"name": "test", "version": "1.0.0", "description": "t"},
            # v0 keys that should survive
            "name": "Test",
            "description": "A test",
            "version": "1.0.0",
            "domain": "software",
            "workflow": {"phases": [{"name": "plan", "description": "Plan"}]},
            "artifacts": {"required": [], "optional": []},
        }
        stripped = strip_v1_keys(config)

        # v1 keys removed
        assert "states" not in stripped
        assert "transitions" not in stripped
        assert "initial" not in stripped
        assert "guards" not in stripped
        assert "inputs" not in stripped
        assert "outputs" not in stripped
        assert "mission" not in stripped

        # v0 keys preserved
        assert stripped["name"] == "Test"
        assert stripped["domain"] == "software"
        assert "workflow" in stripped
        assert "artifacts" in stripped

    def test_strip_on_pure_v0_is_identity(self):
        from specify_cli.mission_v1.schema import strip_v1_keys

        config = _minimal_v0_config()
        stripped = strip_v1_keys(config)
        assert stripped == config

    def test_strip_does_not_mutate_original(self):
        from specify_cli.mission_v1.schema import strip_v1_keys

        config = {"states": [], "transitions": [], "name": "Test"}
        original_keys = set(config.keys())
        strip_v1_keys(config)
        assert set(config.keys()) == original_keys


# ---------------------------------------------------------------------------
# Backward compatibility: Mission(path) still works for v0
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Verify that the existing Mission class still works for v0 configs."""

    def test_mission_loads_v0_directly(self, v0_mission_dir):
        """Mission(path) continues to work for v0 configs."""
        m = Mission(v0_mission_dir)
        assert m.name == "Test v0 Mission"
        assert m.version == "1.0.0"

    def test_mission_get_workflow_phases(self, v0_mission_dir):
        """Mission.get_workflow_phases() still works."""
        m = Mission(v0_mission_dir)
        phases = m.get_workflow_phases()
        assert len(phases) == 2
        assert phases[0]["name"] == "research"

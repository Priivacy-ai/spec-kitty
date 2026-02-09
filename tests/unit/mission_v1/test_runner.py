"""Tests for MissionRunner / StateMachineMission.

Covers:
- Loading a minimal v1 config and verifying initial state
- Triggering valid transitions (forward and rollback)
- Invalid trigger raises MachineError, state unchanged
- get_triggers() returns correct triggers per state
- get_states() returns all state names
- name, version, description properties from config
- Invalid config raises MissionValidationError
- Fan-out transitions (multiple transitions from same source)
- auto_transitions=False (no to_<state> methods)
- MissionModel holds context (feature_dir, inputs, event_log_path)
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from transitions import MachineError

from specify_cli.mission_v1.runner import MissionModel, StateMachineMission
from specify_cli.mission_v1.schema import MissionValidationError


# ---------------------------------------------------------------------------
# Test configs
# ---------------------------------------------------------------------------

MINIMAL_V1_CONFIG: dict = {
    "mission": {
        "name": "test-mission",
        "version": "1.0.0",
        "description": "A test mission",
    },
    "initial": "alpha",
    "states": [
        {"name": "alpha"},
        {"name": "beta"},
        {"name": "done"},
    ],
    "transitions": [
        {"trigger": "advance", "source": "alpha", "dest": "beta"},
        {"trigger": "advance", "source": "beta", "dest": "done"},
        {"trigger": "rollback", "source": "beta", "dest": "alpha"},
    ],
}

FANOUT_CONFIG: dict = {
    "mission": {
        "name": "fanout-mission",
        "version": "2.0.0",
        "description": "Mission with fan-out transitions",
    },
    "initial": "start",
    "states": [
        {"name": "start"},
        {"name": "path_a"},
        {"name": "path_b"},
        {"name": "end"},
    ],
    "transitions": [
        {"trigger": "go_a", "source": "start", "dest": "path_a"},
        {"trigger": "go_b", "source": "start", "dest": "path_b"},
        {"trigger": "finish", "source": "path_a", "dest": "end"},
        {"trigger": "finish", "source": "path_b", "dest": "end"},
    ],
}

CONFIG_WITH_GUARDS: dict = {
    "mission": {
        "name": "guarded-mission",
        "version": "1.0.0",
        "description": "Mission with guard conditions (stripped by runner)",
    },
    "initial": "draft",
    "states": [
        {"name": "draft"},
        {"name": "reviewed"},
        {"name": "done"},
    ],
    "transitions": [
        {
            "trigger": "submit",
            "source": "draft",
            "dest": "reviewed",
            "conditions": ["artifact_exists('spec.md')"],
        },
        {
            "trigger": "accept",
            "source": "reviewed",
            "dest": "done",
            "unless": ["has_open_issues"],
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def minimal_config() -> dict:
    return copy.deepcopy(MINIMAL_V1_CONFIG)


@pytest.fixture()
def fanout_config() -> dict:
    return copy.deepcopy(FANOUT_CONFIG)


@pytest.fixture()
def guarded_config() -> dict:
    return copy.deepcopy(CONFIG_WITH_GUARDS)


# ---------------------------------------------------------------------------
# T009: StateMachineMission construction
# ---------------------------------------------------------------------------


class TestStateMachineMissionConstruction:
    """Verify that StateMachineMission loads configs correctly."""

    def test_initial_state(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert mission.state == "alpha"

    def test_name_property(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert mission.name == "test-mission"

    def test_version_property(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert mission.version == "1.0.0"

    def test_description_property(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert mission.description == "A test mission"

    def test_get_states(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        states = mission.get_states()
        assert set(states) == {"alpha", "beta", "done"}

    def test_get_triggers_current_state(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        triggers = mission.get_triggers()
        assert triggers == ["advance"]

    def test_get_triggers_specific_state(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        triggers = mission.get_triggers("beta")
        assert set(triggers) == {"advance", "rollback"}

    def test_get_triggers_terminal_state(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        triggers = mission.get_triggers("done")
        assert triggers == []

    def test_model_accessible(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert isinstance(mission.model, MissionModel)

    def test_feature_dir_passed_to_model(self, tmp_path: Path) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        mission = StateMachineMission(config, feature_dir=tmp_path)
        assert mission.model.feature_dir == tmp_path

    def test_inputs_passed_to_model(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        inputs = {"project_name": "acme", "language": "python"}
        mission = StateMachineMission(config, inputs=inputs)
        assert mission.model.inputs == inputs

    def test_event_log_path_passed_to_model(self, tmp_path: Path) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        log_path = tmp_path / "events.jsonl"
        mission = StateMachineMission(config, event_log_path=log_path)
        assert mission.model.event_log_path == log_path


# ---------------------------------------------------------------------------
# T009: State transitions
# ---------------------------------------------------------------------------


class TestStateTransitions:
    """Verify trigger/transition mechanics."""

    def test_valid_transition_forward(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        result = mission.trigger("advance")
        assert result is True
        assert mission.state == "beta"

    def test_chain_to_terminal(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        mission.trigger("advance")  # alpha -> beta
        mission.trigger("advance")  # beta -> done
        assert mission.state == "done"

    def test_rollback_transition(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        mission.trigger("advance")  # alpha -> beta
        assert mission.state == "beta"
        mission.trigger("rollback")  # beta -> alpha
        assert mission.state == "alpha"

    def test_invalid_trigger_raises_machine_error(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        mission.trigger("advance")  # alpha -> beta
        mission.trigger("advance")  # beta -> done
        with pytest.raises(MachineError, match="Can't trigger event"):
            mission.trigger("advance")  # done -> ??? (no transition)

    def test_state_unchanged_after_invalid_trigger(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        mission.trigger("advance")  # alpha -> beta
        mission.trigger("advance")  # beta -> done
        with pytest.raises(MachineError):
            mission.trigger("advance")
        assert mission.state == "done"

    def test_unknown_trigger_raises_attribute_error(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        with pytest.raises(AttributeError):
            mission.trigger("nonexistent_trigger")

    def test_rollback_not_available_from_alpha(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert mission.state == "alpha"
        with pytest.raises(MachineError):
            mission.trigger("rollback")


# ---------------------------------------------------------------------------
# T009: Fan-out transitions
# ---------------------------------------------------------------------------


class TestFanOutTransitions:
    """Verify multiple transitions from same source with different triggers."""

    def test_go_a_path(self, fanout_config: dict) -> None:
        mission = StateMachineMission(fanout_config)
        mission.trigger("go_a")
        assert mission.state == "path_a"
        mission.trigger("finish")
        assert mission.state == "end"

    def test_go_b_path(self, fanout_config: dict) -> None:
        mission = StateMachineMission(fanout_config)
        mission.trigger("go_b")
        assert mission.state == "path_b"
        mission.trigger("finish")
        assert mission.state == "end"

    def test_triggers_at_start(self, fanout_config: dict) -> None:
        mission = StateMachineMission(fanout_config)
        triggers = mission.get_triggers("start")
        assert set(triggers) == {"go_a", "go_b"}


# ---------------------------------------------------------------------------
# T009: auto_transitions=False
# ---------------------------------------------------------------------------


class TestAutoTransitionsDisabled:
    """Verify to_<state> methods are NOT created."""

    def test_no_to_alpha_method(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert not hasattr(mission.model, "to_alpha")

    def test_no_to_beta_method(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert not hasattr(mission.model, "to_beta")

    def test_no_to_done_method(self, minimal_config: dict) -> None:
        mission = StateMachineMission(minimal_config)
        assert not hasattr(mission.model, "to_done")


# ---------------------------------------------------------------------------
# T009: Guard stripping
# ---------------------------------------------------------------------------


class TestGuardStripping:
    """Verify configs with conditions/unless load without errors.

    Guards are stripped in this WP; compilation happens in WP03.
    """

    def test_config_with_conditions_loads(self, guarded_config: dict) -> None:
        mission = StateMachineMission(guarded_config)
        assert mission.state == "draft"

    def test_guarded_transitions_work_without_guards(self, guarded_config: dict) -> None:
        mission = StateMachineMission(guarded_config)
        mission.trigger("submit")  # conditions stripped, so transition fires
        assert mission.state == "reviewed"
        mission.trigger("accept")  # unless stripped, so transition fires
        assert mission.state == "done"


# ---------------------------------------------------------------------------
# T009: Schema validation at construction
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Verify invalid configs raise MissionValidationError."""

    def test_missing_mission_block(self) -> None:
        config = {
            "initial": "alpha",
            "states": [{"name": "alpha"}],
            "transitions": [{"trigger": "go", "source": "alpha", "dest": "alpha"}],
        }
        with pytest.raises(MissionValidationError, match="validation failed"):
            StateMachineMission(config)

    def test_missing_states(self) -> None:
        config = {
            "mission": {"name": "x", "version": "1", "description": "x"},
            "initial": "alpha",
            "transitions": [{"trigger": "go", "source": "alpha", "dest": "alpha"}],
        }
        with pytest.raises(MissionValidationError, match="validation failed"):
            StateMachineMission(config)

    def test_missing_transitions(self) -> None:
        config = {
            "mission": {"name": "x", "version": "1", "description": "x"},
            "initial": "alpha",
            "states": [{"name": "alpha"}],
        }
        with pytest.raises(MissionValidationError, match="validation failed"):
            StateMachineMission(config)

    def test_missing_initial(self) -> None:
        config = {
            "mission": {"name": "x", "version": "1", "description": "x"},
            "states": [{"name": "alpha"}],
            "transitions": [{"trigger": "go", "source": "alpha", "dest": "alpha"}],
        }
        with pytest.raises(MissionValidationError, match="validation failed"):
            StateMachineMission(config)

    def test_state_without_name(self) -> None:
        config = {
            "mission": {"name": "x", "version": "1", "description": "x"},
            "initial": "alpha",
            "states": [{"display_name": "Alpha"}],  # missing 'name'
            "transitions": [{"trigger": "go", "source": "alpha", "dest": "alpha"}],
        }
        with pytest.raises(MissionValidationError, match="validation failed"):
            StateMachineMission(config)


# ---------------------------------------------------------------------------
# T007: MissionModel
# ---------------------------------------------------------------------------


class TestMissionModel:
    """Verify MissionModel holds context correctly."""

    def test_default_state_empty_string(self) -> None:
        model = MissionModel()
        assert model.state == ""

    def test_feature_dir(self, tmp_path: Path) -> None:
        model = MissionModel(feature_dir=tmp_path)
        assert model.feature_dir == tmp_path

    def test_inputs_default_empty(self) -> None:
        model = MissionModel()
        assert model.inputs == {}

    def test_inputs_custom(self) -> None:
        model = MissionModel(inputs={"lang": "python"})
        assert model.inputs == {"lang": "python"}

    def test_event_log_path(self, tmp_path: Path) -> None:
        log = tmp_path / "events.jsonl"
        model = MissionModel(event_log_path=log)
        assert model.event_log_path == log

    def test_on_enter_state_callable(self) -> None:
        """Stub callback must be callable (MarkupMachine will call it)."""
        model = MissionModel()
        # Should not raise -- it's a no-op stub
        model.on_enter_state(event=None)

    def test_on_exit_state_callable(self) -> None:
        model = MissionModel()
        model.on_exit_state(event=None)

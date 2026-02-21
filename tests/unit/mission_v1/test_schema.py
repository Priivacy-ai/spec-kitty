"""Tests for mission_v1 JSON Schema validation.

Covers:
- Valid minimal and full v1 configs
- Missing required fields (initial, states, transitions, mission)
- Invalid nested structures (state without name, transition without trigger/dest)
- Invalid enum values (input type)
- v1 detection (is_v1_mission)
- Legacy v0 keys coexisting with v1 keys (additionalProperties: true at root)
"""

from __future__ import annotations

import copy

import pytest

from specify_cli.mission_v1.schema import (
    MissionValidationError,
    is_v1_mission,
    validate_mission_v1,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_V1_CONFIG: dict = {
    "mission": {
        "name": "software-dev",
        "version": "1.0.0",
        "description": "Software development mission",
    },
    "initial": "specify",
    "states": [
        {"name": "specify"},
        {"name": "plan"},
        {"name": "implement"},
        {"name": "review"},
        {"name": "done"},
    ],
    "transitions": [
        {"trigger": "start_planning", "source": "specify", "dest": "plan"},
        {"trigger": "start_impl", "source": "plan", "dest": "implement"},
        {"trigger": "submit_review", "source": "implement", "dest": "review"},
        {"trigger": "accept", "source": "review", "dest": "done"},
    ],
}


FULL_V1_CONFIG: dict = {
    **MINIMAL_V1_CONFIG,
    "inputs": [
        {
            "name": "project_name",
            "type": "string",
            "required": True,
            "description": "Name of the project",
        },
        {
            "name": "repo_path",
            "type": "path",
            "required": False,
            "description": "Path to the repository",
        },
    ],
    "outputs": [
        {
            "name": "spec_document",
            "type": "artifact",
            "path": "kitty-specs/{feature}/spec.md",
            "phase": "specify",
            "description": "Feature specification",
        },
        {
            "name": "test_report",
            "type": "report",
            "path": "reports/test.html",
            "description": "Test execution report",
        },
    ],
    "guards": {
        "spec_exists": {
            "description": "Spec document must exist before planning",
            "check": "check_spec_exists",
        },
        "tests_pass": {
            "description": "All tests must pass before review",
            "check": "check_tests_pass",
        },
    },
    "states": [
        {"name": "specify", "display_name": "Specify"},
        {"name": "plan", "display_name": "Plan", "on_enter": ["load_spec"]},
        {
            "name": "implement",
            "display_name": "Implement",
            "on_enter": ["setup_workspace"],
            "on_exit": ["run_tests"],
        },
        {"name": "review", "display_name": "Review"},
        {"name": "done", "display_name": "Done"},
    ],
    "transitions": [
        {
            "trigger": "start_planning",
            "source": "specify",
            "dest": "plan",
            "conditions": ["spec_exists"],
        },
        {"trigger": "start_impl", "source": "plan", "dest": "implement"},
        {
            "trigger": "submit_review",
            "source": "implement",
            "dest": "review",
            "conditions": ["tests_pass"],
            "before": ["run_linter"],
            "after": ["notify_reviewer"],
        },
        {"trigger": "accept", "source": "review", "dest": "done"},
        {
            "trigger": "request_changes",
            "source": "review",
            "dest": "implement",
            "unless": ["is_auto_approved"],
        },
    ],
}


V0_CONFIG: dict = {
    "name": "software-dev",
    "description": "Legacy v0 mission",
    "version": "0.1.0",
    "domain": "software",
    "workflow": {
        "phases": [
            {"name": "specify", "description": "Create specification"},
            {"name": "plan", "description": "Create plan"},
        ]
    },
    "artifacts": {"spec": "spec.md"},
}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidConfigs:
    """Valid configs must pass validation without error."""

    def test_minimal_v1_config(self) -> None:
        validate_mission_v1(MINIMAL_V1_CONFIG)

    def test_full_v1_config_with_guards_inputs_outputs(self) -> None:
        validate_mission_v1(FULL_V1_CONFIG)

    def test_v1_config_with_legacy_v0_keys(self) -> None:
        """additionalProperties: true at root allows v0 keys alongside v1."""
        config = {
            **MINIMAL_V1_CONFIG,
            "workflow": {"phases": [{"name": "legacy"}]},
            "artifacts": {"readme": "README.md"},
            "paths": {"output": "dist/"},
            "validation": {},
            "mcp_tools": [],
            "agent_context": {},
            "task_metadata": {},
            "commands": {},
        }
        validate_mission_v1(config)

    def test_transition_with_array_source(self) -> None:
        """source can be a list of state names (multi-source transition)."""
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"].append({"trigger": "reset", "source": ["plan", "implement"], "dest": "specify"})
        validate_mission_v1(config)


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------


class TestMissingRequiredFields:
    """Each required top-level key, when absent, must cause a validation error."""

    def test_missing_initial(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        del config["initial"]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("initial" in e for e in exc_info.value.errors)

    def test_missing_states(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        del config["states"]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("states" in e for e in exc_info.value.errors)

    def test_missing_transitions(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        del config["transitions"]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("transitions" in e for e in exc_info.value.errors)

    def test_missing_mission(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        del config["mission"]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("mission" in e for e in exc_info.value.errors)


# ---------------------------------------------------------------------------
# Invalid nested structures
# ---------------------------------------------------------------------------


class TestInvalidNestedStructures:
    """Schema must reject invalid items inside states/transitions/inputs."""

    def test_state_without_name(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["states"].append({"display_name": "Orphan"})
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("name" in e for e in exc_info.value.errors)

    def test_transition_without_trigger(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"].append({"source": "specify", "dest": "plan"})
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("trigger" in e for e in exc_info.value.errors)

    def test_transition_without_dest(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"].append({"trigger": "go", "source": "specify"})
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("dest" in e for e in exc_info.value.errors)

    def test_invalid_input_type_enum(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["inputs"] = [{"name": "bad_input", "type": "float", "required": True}]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("float" in e or "type" in e for e in exc_info.value.errors)

    def test_state_with_unknown_property(self) -> None:
        """States use additionalProperties: false, so unknown keys are rejected."""
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["states"][0]["bogus_key"] = "not allowed"
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("bogus_key" in e for e in exc_info.value.errors)

    def test_transition_with_unknown_property(self) -> None:
        """Transitions use additionalProperties: false, so unknown keys are rejected."""
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"][0]["bogus_key"] = "not allowed"
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("bogus_key" in e for e in exc_info.value.errors)

    def test_empty_states_array(self) -> None:
        """states must have at least one item."""
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["states"] = []
        with pytest.raises(MissionValidationError):
            validate_mission_v1(config)

    def test_empty_transitions_array(self) -> None:
        """transitions must have at least one item."""
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"] = []
        with pytest.raises(MissionValidationError):
            validate_mission_v1(config)


class TestTransitionGuardArrays:
    """conditions/unless/before/after must stay arrays of strings."""

    def test_conditions_reject_non_strings(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"][0]["conditions"] = ["ok", {"not": "string"}]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("conditions" in e for e in exc_info.value.errors)

    def test_unless_reject_non_strings(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"][0]["unless"] = [42]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("unless" in e for e in exc_info.value.errors)

    def test_before_after_reject_non_strings(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"][0]["before"] = ["ok", 123]
        config["transitions"][0]["after"] = [None]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        errors_text = " ".join(exc_info.value.errors)
        assert "before" in errors_text or "after" in errors_text

    def test_unknown_guard_reference_allowed(self) -> None:
        """Schema allows unresolved guards; guard compilation checks them later."""
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["transitions"][0]["conditions"] = ["unknown_guard"]
        validate_mission_v1(config)


# ---------------------------------------------------------------------------
# v1 detection
# ---------------------------------------------------------------------------


class TestIsV1Mission:
    """is_v1_mission() must reliably distinguish v0 from v1 configs."""

    def test_v1_config_detected(self) -> None:
        assert is_v1_mission(MINIMAL_V1_CONFIG) is True

    def test_full_v1_config_detected(self) -> None:
        assert is_v1_mission(FULL_V1_CONFIG) is True

    def test_v0_config_not_detected(self) -> None:
        assert is_v1_mission(V0_CONFIG) is False

    def test_empty_config_not_detected(self) -> None:
        assert is_v1_mission({}) is False

    def test_partial_v1_missing_transitions(self) -> None:
        """Having states but not transitions is NOT v1."""
        config = {"states": [{"name": "a"}]}
        assert is_v1_mission(config) is False

    def test_partial_v1_missing_states(self) -> None:
        """Having transitions but not states is NOT v1."""
        config = {"transitions": [{"trigger": "go", "dest": "b"}]}
        assert is_v1_mission(config) is False


# ---------------------------------------------------------------------------
# MissionValidationError
# ---------------------------------------------------------------------------


class TestMissionValidationError:
    """MissionValidationError must expose structured error details."""

    def test_error_has_errors_attribute(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        del config["initial"]
        del config["states"]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert len(exc_info.value.errors) >= 2

    def test_error_messages_contain_field_paths(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["states"].append({"display_name": "NoName"})
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        # Error path should reference the array index in states
        errors_text = " ".join(exc_info.value.errors)
        assert "states" in errors_text

    def test_error_str_contains_count(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        del config["initial"]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert "1 error" in str(exc_info.value)

    def test_error_default_empty_errors_list(self) -> None:
        err = MissionValidationError("test")
        assert err.errors == []


# ---------------------------------------------------------------------------
# Guards schema
# ---------------------------------------------------------------------------


class TestGuardsSchema:
    """Guards must follow the {description, check} structure."""

    def test_valid_guards(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["guards"] = {
            "my_guard": {
                "description": "Check something",
                "check": "check_something",
            }
        }
        validate_mission_v1(config)

    def test_guard_missing_description(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["guards"] = {"my_guard": {"check": "check_something"}}
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("description" in e for e in exc_info.value.errors)

    def test_guard_missing_check(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["guards"] = {"my_guard": {"description": "A guard without check"}}
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("check" in e for e in exc_info.value.errors)

    def test_guard_with_extra_properties_rejected(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["guards"] = {
            "my_guard": {
                "description": "desc",
                "check": "fn",
                "extra": "bad",
            }
        }
        with pytest.raises(MissionValidationError):
            validate_mission_v1(config)


# ---------------------------------------------------------------------------
# Outputs schema
# ---------------------------------------------------------------------------


class TestOutputsSchema:
    """Outputs must follow the required structure with valid type enum."""

    def test_valid_output_types(self) -> None:
        for output_type in ("artifact", "report", "data"):
            config = copy.deepcopy(MINIMAL_V1_CONFIG)
            config["outputs"] = [{"name": "out", "type": output_type}]
            validate_mission_v1(config)

    def test_invalid_output_type(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["outputs"] = [{"name": "out", "type": "binary"}]
        with pytest.raises(MissionValidationError):
            validate_mission_v1(config)


# ---------------------------------------------------------------------------
# Inputs schema
# ---------------------------------------------------------------------------


class TestInputsSchema:
    """Inputs must follow the required structure with valid type enum."""

    def test_all_valid_input_types(self) -> None:
        for input_type in ("string", "path", "url", "boolean", "integer"):
            config = copy.deepcopy(MINIMAL_V1_CONFIG)
            config["inputs"] = [{"name": "in", "type": input_type}]
            validate_mission_v1(config)

    def test_input_missing_name(self) -> None:
        config = copy.deepcopy(MINIMAL_V1_CONFIG)
        config["inputs"] = [{"type": "string", "required": True}]
        with pytest.raises(MissionValidationError) as exc_info:
            validate_mission_v1(config)
        assert any("name" in e for e in exc_info.value.errors)

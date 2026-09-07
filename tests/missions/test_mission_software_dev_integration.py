"""Integration tests for the built-in software-dev mission YAML.

Verifies:
- Loading the real mission.yaml from disk
- Named guards section documents the guard expressions
- v0 legacy keys coexist alongside the tolerated v1 keys
- Typed inputs and outputs present and correctly structured

The mission-DSL v1 runtime (schema validator, state machine, transition
graph) was retired in mission dead-port-disposition-01M1TZVN; the
``states:``/``transitions:`` blocks were deleted from the built-in packs at
the same time, so the structure/graph/reachability tests went with them.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from charter.offering.missions.repository import MissionTemplateRepository

import pytest

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MISSIONS_ROOT = MissionTemplateRepository.default_missions_root()
MISSION_YAML_PATH = MISSIONS_ROOT / "software-dev" / "mission.yaml"


@pytest.fixture()
def software_dev_config() -> dict:
    """Load the real software-dev mission.yaml."""
    with open(MISSION_YAML_PATH) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Presence
# ---------------------------------------------------------------------------


class TestMissionYamlPresence:
    """The built-in software-dev mission.yaml ships with the pack."""

    def test_file_exists(self) -> None:
        assert MISSION_YAML_PATH.exists(), f"Missing: {MISSION_YAML_PATH}"


# ---------------------------------------------------------------------------
# Guards section
# ---------------------------------------------------------------------------


class TestGuardsSection:
    """Named guards section provides documentation for guard expressions."""

    def test_guards_present(self, software_dev_config: dict) -> None:
        assert "guards" in software_dev_config

    def test_five_guards_defined(self, software_dev_config: dict) -> None:
        guards = software_dev_config["guards"]
        assert frozenset(guards.keys()) == frozenset(
            {"has_spec", "has_plan", "has_tasks", "all_wps_accepted", "review_passed"}
        )

    def test_guard_names(self, software_dev_config: dict) -> None:
        expected = {"has_spec", "has_plan", "has_tasks", "all_wps_accepted", "review_passed"}
        assert set(software_dev_config["guards"].keys()) == expected

    def test_each_guard_has_description_and_check(self, software_dev_config: dict) -> None:
        for name, guard in software_dev_config["guards"].items():
            assert "description" in guard, f"Guard '{name}' missing description"
            assert "check" in guard, f"Guard '{name}' missing check"
            assert isinstance(guard["description"], str)
            assert isinstance(guard["check"], str)


# ---------------------------------------------------------------------------
# Typed inputs and outputs
# ---------------------------------------------------------------------------


class TestInputsAndOutputs:
    """Mission declares typed input parameters and output artifacts."""

    def test_inputs_present(self, software_dev_config: dict) -> None:
        assert "inputs" in software_dev_config
        assert len(software_dev_config["inputs"]) >= 2

    def test_input_names(self, software_dev_config: dict) -> None:
        names = {i["name"] for i in software_dev_config["inputs"]}
        assert "feature_description" in names
        assert "project_root" in names

    def test_input_types_valid(self, software_dev_config: dict) -> None:
        valid_types = {"string", "path", "url", "boolean", "integer"}
        for inp in software_dev_config["inputs"]:
            assert inp["type"] in valid_types, f"Invalid input type: {inp['type']}"

    def test_outputs_present(self, software_dev_config: dict) -> None:
        assert "outputs" in software_dev_config
        assert len(software_dev_config["outputs"]) >= 3

    def test_output_names(self, software_dev_config: dict) -> None:
        names = {o["name"] for o in software_dev_config["outputs"]}
        assert "specification" in names
        assert "implementation_plan" in names
        assert "task_breakdown" in names
        assert "source_code" in names

    def test_output_types_valid(self, software_dev_config: dict) -> None:
        valid_types = {"artifact", "report", "data"}
        for out in software_dev_config["outputs"]:
            assert out["type"] in valid_types, f"Invalid output type: {out['type']}"

    def test_outputs_have_paths(self, software_dev_config: dict) -> None:
        for out in software_dev_config["outputs"]:
            assert "path" in out, f"Output '{out['name']}' missing path"


# ---------------------------------------------------------------------------
# v0 backward compatibility
# ---------------------------------------------------------------------------


class TestV0BackwardCompatibility:
    """v0 legacy keys must coexist with v1 fields."""

    def test_v0_name_preserved(self, software_dev_config: dict) -> None:
        assert software_dev_config["name"] == "Software Dev Kitty"

    def test_v0_workflow_preserved(self, software_dev_config: dict) -> None:
        assert "workflow" in software_dev_config
        phases = software_dev_config["workflow"]["phases"]
        assert frozenset(p["name"] for p in phases) == frozenset(
            {"research", "design", "implement", "test", "review"}
        )

    def test_v0_artifacts_preserved(self, software_dev_config: dict) -> None:
        assert "artifacts" in software_dev_config
        assert "spec.md" in software_dev_config["artifacts"]["required"]

    def test_v0_domain_preserved(self, software_dev_config: dict) -> None:
        assert software_dev_config["domain"] == "software"

    def test_v0_commands_preserved(self, software_dev_config: dict) -> None:
        assert "commands" in software_dev_config
        assert "specify" in software_dev_config["commands"]
        assert "implement" in software_dev_config["commands"]

    def test_v0_agent_context_preserved(self, software_dev_config: dict) -> None:
        assert "agent_context" in software_dev_config
        assert "TDD" in software_dev_config["agent_context"]


# ---------------------------------------------------------------------------
# Mission block
# ---------------------------------------------------------------------------


class TestMissionBlock:
    """The mission metadata block has correct v1 identity fields."""

    def test_mission_name(self, software_dev_config: dict) -> None:
        assert software_dev_config["mission"]["name"] == "software-dev"

    def test_mission_version(self, software_dev_config: dict) -> None:
        assert software_dev_config["mission"]["version"] == "2.0.0"

    def test_mission_description(self, software_dev_config: dict) -> None:
        desc = software_dev_config["mission"]["description"]
        assert "state machine" in desc.lower() or "software" in desc.lower()

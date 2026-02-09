"""Integration tests for the software-dev v1 mission YAML.

Verifies:
- Loading the real mission.yaml from disk and detecting it as v1
- Passing JSON Schema validation (validate_mission_v1)
- State machine structure: 6 states starting at 'discovery'
- Transition graph: 5 forward advances + 1 rework rollback
- Guard conditions on gated transitions
- Rollback transition (review -> implement) has no guards
- v0 legacy keys coexist alongside v1 keys
- Typed inputs and outputs present and correctly structured
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specify_cli.mission_v1.schema import (
    is_v1_mission,
    validate_mission_v1,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MISSION_YAML_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "specify_cli"
    / "missions"
    / "software-dev"
    / "mission.yaml"
)


@pytest.fixture()
def software_dev_config() -> dict:
    """Load the real software-dev mission.yaml."""
    with open(MISSION_YAML_PATH) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Detection & validation
# ---------------------------------------------------------------------------


class TestV1Detection:
    """The software-dev mission.yaml must be recognized as v1."""

    def test_file_exists(self) -> None:
        assert MISSION_YAML_PATH.exists(), f"Missing: {MISSION_YAML_PATH}"

    def test_is_v1_mission(self, software_dev_config: dict) -> None:
        assert is_v1_mission(software_dev_config) is True

    def test_passes_v1_schema_validation(self, software_dev_config: dict) -> None:
        # Should not raise
        validate_mission_v1(software_dev_config)


# ---------------------------------------------------------------------------
# State machine structure
# ---------------------------------------------------------------------------


class TestStateMachineStructure:
    """States, initial, and transitions match the expected graph."""

    def test_initial_state_is_discovery(self, software_dev_config: dict) -> None:
        assert software_dev_config["initial"] == "discovery"

    def test_six_states_defined(self, software_dev_config: dict) -> None:
        states = software_dev_config["states"]
        assert len(states) == 6

    def test_state_names(self, software_dev_config: dict) -> None:
        names = [s["name"] for s in software_dev_config["states"]]
        expected = ["discovery", "specify", "plan", "implement", "review", "done"]
        assert names == expected

    def test_all_states_have_display_name(self, software_dev_config: dict) -> None:
        for state in software_dev_config["states"]:
            assert "display_name" in state, f"State '{state['name']}' missing display_name"

    def test_all_states_have_on_enter(self, software_dev_config: dict) -> None:
        for state in software_dev_config["states"]:
            assert "on_enter" in state, f"State '{state['name']}' missing on_enter"
            assert isinstance(state["on_enter"], list)

    def test_six_transitions_defined(self, software_dev_config: dict) -> None:
        transitions = software_dev_config["transitions"]
        assert len(transitions) == 6

    def test_advance_transitions_count(self, software_dev_config: dict) -> None:
        advance_transitions = [
            t for t in software_dev_config["transitions"] if t["trigger"] == "advance"
        ]
        assert len(advance_transitions) == 5

    def test_rework_transition_exists(self, software_dev_config: dict) -> None:
        rework_transitions = [
            t for t in software_dev_config["transitions"] if t["trigger"] == "rework"
        ]
        assert len(rework_transitions) == 1
        rework = rework_transitions[0]
        assert rework["source"] == "review"
        assert rework["dest"] == "implement"


# ---------------------------------------------------------------------------
# Forward transition graph
# ---------------------------------------------------------------------------


class TestForwardTransitions:
    """Advance transitions form the correct forward path."""

    def _advance_map(self, config: dict) -> dict[str, str]:
        """Build source -> dest map for advance transitions."""
        result = {}
        for t in config["transitions"]:
            if t["trigger"] == "advance":
                result[t["source"]] = t["dest"]
        return result

    def test_discovery_to_specify(self, software_dev_config: dict) -> None:
        m = self._advance_map(software_dev_config)
        assert m["discovery"] == "specify"

    def test_specify_to_plan(self, software_dev_config: dict) -> None:
        m = self._advance_map(software_dev_config)
        assert m["specify"] == "plan"

    def test_plan_to_implement(self, software_dev_config: dict) -> None:
        m = self._advance_map(software_dev_config)
        assert m["plan"] == "implement"

    def test_implement_to_review(self, software_dev_config: dict) -> None:
        m = self._advance_map(software_dev_config)
        assert m["implement"] == "review"

    def test_review_to_done(self, software_dev_config: dict) -> None:
        m = self._advance_map(software_dev_config)
        assert m["review"] == "done"


# ---------------------------------------------------------------------------
# Guard conditions
# ---------------------------------------------------------------------------


class TestGuardConditions:
    """Gated transitions must have the expected guard expressions."""

    def _get_transition(self, config: dict, source: str, trigger: str) -> dict:
        for t in config["transitions"]:
            if t.get("source") == source and t["trigger"] == trigger:
                return t
        raise AssertionError(f"No transition: {trigger} from {source}")

    def test_discovery_to_specify_no_guard(self, software_dev_config: dict) -> None:
        t = self._get_transition(software_dev_config, "discovery", "advance")
        assert "conditions" not in t

    def test_specify_to_plan_requires_spec(self, software_dev_config: dict) -> None:
        t = self._get_transition(software_dev_config, "specify", "advance")
        assert 'artifact_exists("spec.md")' in t["conditions"]

    def test_plan_to_implement_requires_plan_and_tasks(
        self, software_dev_config: dict
    ) -> None:
        t = self._get_transition(software_dev_config, "plan", "advance")
        conditions = t["conditions"]
        assert 'artifact_exists("plan.md")' in conditions
        assert 'artifact_exists("tasks.md")' in conditions

    def test_implement_to_review_requires_all_wp_done(
        self, software_dev_config: dict
    ) -> None:
        t = self._get_transition(software_dev_config, "implement", "advance")
        assert 'all_wp_status("done")' in t["conditions"]

    def test_review_to_done_requires_review_approved(
        self, software_dev_config: dict
    ) -> None:
        t = self._get_transition(software_dev_config, "review", "advance")
        assert 'gate_passed("review_approved")' in t["conditions"]

    def test_rework_has_no_guards(self, software_dev_config: dict) -> None:
        t = self._get_transition(software_dev_config, "review", "rework")
        assert "conditions" not in t
        assert "unless" not in t


# ---------------------------------------------------------------------------
# Guards section
# ---------------------------------------------------------------------------


class TestGuardsSection:
    """Named guards section provides documentation for guard expressions."""

    def test_guards_present(self, software_dev_config: dict) -> None:
        assert "guards" in software_dev_config

    def test_five_guards_defined(self, software_dev_config: dict) -> None:
        guards = software_dev_config["guards"]
        assert len(guards) == 5

    def test_guard_names(self, software_dev_config: dict) -> None:
        expected = {"has_spec", "has_plan", "has_tasks", "all_wps_done", "review_passed"}
        assert set(software_dev_config["guards"].keys()) == expected

    def test_each_guard_has_description_and_check(
        self, software_dev_config: dict
    ) -> None:
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
        assert len(phases) == 5

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


# ---------------------------------------------------------------------------
# State reachability (graph integrity)
# ---------------------------------------------------------------------------


class TestStateReachability:
    """Every state is reachable from the initial state via transitions."""

    def test_all_states_reachable_from_initial(
        self, software_dev_config: dict
    ) -> None:
        initial = software_dev_config["initial"]
        state_names = {s["name"] for s in software_dev_config["states"]}
        transitions = software_dev_config["transitions"]

        # Build adjacency from transitions
        adj: dict[str, set[str]] = {s: set() for s in state_names}
        for t in transitions:
            source = t.get("source")
            dest = t["dest"]
            if isinstance(source, str):
                adj.setdefault(source, set()).add(dest)
            elif isinstance(source, list):
                for s in source:
                    adj.setdefault(s, set()).add(dest)

        # BFS from initial
        visited: set[str] = set()
        queue = [initial]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

        assert visited == state_names, (
            f"Unreachable states: {state_names - visited}"
        )

    def test_triggers_available_from_review(
        self, software_dev_config: dict
    ) -> None:
        """Review state should have both 'advance' and 'rework' triggers."""
        triggers = set()
        for t in software_dev_config["transitions"]:
            if t.get("source") == "review":
                triggers.add(t["trigger"])
        assert "advance" in triggers
        assert "rework" in triggers

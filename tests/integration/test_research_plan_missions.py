"""Integration tests for research and plan v1 mission YAML definitions.

Verifies:
- Both missions load from disk and are detected as v1
- Both missions pass JSON Schema validation
- Research mission has correct initial state, states, transitions, and guards
- Research mission evidence gate: event_count on gathering -> synthesis
- Research mission rollback: gather_more from synthesis -> gathering
- Plan mission has correct initial state, states, transitions, and guards
- Plan mission rollback: revise from draft -> structure and review -> draft
- Plan mission advance guard: gate_passed("plan_approved") on review -> done
- v0 compatibility fields preserved in research mission
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

MISSIONS_DIR = Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "missions"


def _load_yaml(mission_name: str) -> dict:
    """Load a mission.yaml from the missions directory."""
    path = MISSIONS_DIR / mission_name / "mission.yaml"
    assert path.exists(), f"Missing mission.yaml at {path}"
    with open(path) as f:
        return yaml.safe_load(f)


def _find_transitions(config: dict, trigger: str) -> list[dict]:
    """Return all transitions with the given trigger name."""
    return [t for t in config["transitions"] if t["trigger"] == trigger]


def _find_transition(config: dict, trigger: str, source: str) -> dict | None:
    """Return the first transition matching trigger and source."""
    for t in config["transitions"]:
        t_source = t.get("source")
        if t["trigger"] == trigger:
            if isinstance(t_source, list):
                if source in t_source:
                    return t
            elif t_source == source:
                return t
    return None


# ---------------------------------------------------------------------------
# Research Mission Tests
# ---------------------------------------------------------------------------


class TestResearchMissionV1:
    """Research mission v1 structure and schema validation."""

    @pytest.fixture()
    def config(self) -> dict:
        return _load_yaml("research")

    def test_is_detected_as_v1(self, config: dict) -> None:
        assert is_v1_mission(config) is True

    def test_passes_json_schema_validation(self, config: dict) -> None:
        validate_mission_v1(config)

    def test_mission_metadata(self, config: dict) -> None:
        assert config["mission"]["name"] == "research"
        assert config["mission"]["version"] == "2.0.0"

    def test_initial_state_is_scoping(self, config: dict) -> None:
        assert config["initial"] == "scoping"

    def test_states_count(self, config: dict) -> None:
        state_names = [s["name"] for s in config["states"]]
        assert state_names == [
            "scoping", "methodology", "gathering", "synthesis", "output", "done"
        ]

    def test_all_states_have_display_name(self, config: dict) -> None:
        for state in config["states"]:
            assert "display_name" in state, f"State {state['name']} missing display_name"

    def test_advance_transitions_form_linear_chain(self, config: dict) -> None:
        """Advance transitions should form: scoping -> methodology -> gathering
        -> synthesis -> output -> done."""
        expected_chain = [
            ("scoping", "methodology"),
            ("methodology", "gathering"),
            ("gathering", "synthesis"),
            ("synthesis", "output"),
            ("output", "done"),
        ]
        for source, dest in expected_chain:
            t = _find_transition(config, "advance", source)
            assert t is not None, f"Missing advance transition from {source}"
            assert t["dest"] == dest, (
                f"advance from {source} should go to {dest}, got {t['dest']}"
            )

    def test_evidence_gate_on_gathering_to_synthesis(self, config: dict) -> None:
        """The gathering -> synthesis transition must require event_count guard."""
        t = _find_transition(config, "advance", "gathering")
        assert t is not None
        assert "conditions" in t
        conditions = t["conditions"]
        assert any("event_count" in c and "source_documented" in c for c in conditions), (
            f"Expected event_count('source_documented', 3) guard, got {conditions}"
        )

    def test_artifact_gate_on_scoping_to_methodology(self, config: dict) -> None:
        t = _find_transition(config, "advance", "scoping")
        assert t is not None
        assert any("artifact_exists" in c and "spec.md" in c for c in t["conditions"])

    def test_artifact_gate_on_methodology_to_gathering(self, config: dict) -> None:
        t = _find_transition(config, "advance", "methodology")
        assert t is not None
        assert any("artifact_exists" in c and "plan.md" in c for c in t["conditions"])

    def test_artifact_gate_on_synthesis_to_output(self, config: dict) -> None:
        t = _find_transition(config, "advance", "synthesis")
        assert t is not None
        assert any("artifact_exists" in c and "findings.md" in c for c in t["conditions"])

    def test_gate_passed_on_output_to_done(self, config: dict) -> None:
        t = _find_transition(config, "advance", "output")
        assert t is not None
        assert any("gate_passed" in c and "publication_approved" in c for c in t["conditions"])

    def test_gather_more_rollback(self, config: dict) -> None:
        """gather_more should allow rolling back from synthesis to gathering."""
        t = _find_transition(config, "gather_more", "synthesis")
        assert t is not None
        assert t["dest"] == "gathering"
        # Rollback should have no conditions
        assert "conditions" not in t or t.get("conditions") is None

    def test_guards_section_present(self, config: dict) -> None:
        assert "guards" in config
        guard_names = set(config["guards"].keys())
        expected = {"has_scope", "has_methodology", "minimum_sources",
                    "has_findings", "publication_approved"}
        assert expected == guard_names

    def test_inputs_defined(self, config: dict) -> None:
        input_names = [i["name"] for i in config["inputs"]]
        assert "research_question" in input_names
        assert "project_root" in input_names
        assert "min_sources" in input_names

    def test_outputs_defined(self, config: dict) -> None:
        output_names = [o["name"] for o in config["outputs"]]
        assert "findings" in output_names
        assert "source_register" in output_names

    def test_v0_compatibility_fields_preserved(self, config: dict) -> None:
        """v0 fields must still be present for backward compatibility."""
        assert config["name"] == "Deep Research Kitty"
        assert config["domain"] == "research"
        assert "workflow" in config
        assert "phases" in config["workflow"]
        assert "artifacts" in config
        assert "paths" in config
        assert "agent_context" in config
        assert "commands" in config


# ---------------------------------------------------------------------------
# Plan Mission Tests
# ---------------------------------------------------------------------------


class TestPlanMissionV1:
    """Plan mission v1 structure and schema validation."""

    @pytest.fixture()
    def config(self) -> dict:
        return _load_yaml("plan")

    def test_is_detected_as_v1(self, config: dict) -> None:
        assert is_v1_mission(config) is True

    def test_passes_json_schema_validation(self, config: dict) -> None:
        validate_mission_v1(config)

    def test_mission_metadata(self, config: dict) -> None:
        assert config["mission"]["name"] == "plan"
        assert config["mission"]["version"] == "2.0.0"

    def test_initial_state_is_goals(self, config: dict) -> None:
        assert config["initial"] == "goals"

    def test_states_count(self, config: dict) -> None:
        state_names = [s["name"] for s in config["states"]]
        assert state_names == [
            "goals", "research", "structure", "draft", "review", "done"
        ]

    def test_all_states_have_display_name(self, config: dict) -> None:
        for state in config["states"]:
            assert "display_name" in state, f"State {state['name']} missing display_name"

    def test_advance_transitions_form_linear_chain(self, config: dict) -> None:
        """Advance transitions: goals -> research -> structure -> draft
        -> review -> done."""
        expected_chain = [
            ("goals", "research"),
            ("research", "structure"),
            ("structure", "draft"),
            ("draft", "review"),
            ("review", "done"),
        ]
        for source, dest in expected_chain:
            t = _find_transition(config, "advance", source)
            assert t is not None, f"Missing advance transition from {source}"
            assert t["dest"] == dest

    def test_artifact_gate_on_goals_to_research(self, config: dict) -> None:
        """goals -> research requires goals.md artifact."""
        t = _find_transition(config, "advance", "goals")
        assert t is not None
        assert any("artifact_exists" in c and "goals.md" in c for c in t["conditions"])

    def test_artifact_gate_on_research_to_structure(self, config: dict) -> None:
        t = _find_transition(config, "advance", "research")
        assert t is not None
        assert any("artifact_exists" in c and "research.md" in c for c in t["conditions"])

    def test_no_guard_on_structure_to_draft(self, config: dict) -> None:
        """structure -> draft should advance without conditions."""
        t = _find_transition(config, "advance", "structure")
        assert t is not None
        assert t.get("conditions") is None

    def test_artifact_gate_on_draft_to_review(self, config: dict) -> None:
        t = _find_transition(config, "advance", "draft")
        assert t is not None
        assert any("artifact_exists" in c and "plan.md" in c for c in t["conditions"])

    def test_gate_passed_on_review_to_done(self, config: dict) -> None:
        t = _find_transition(config, "advance", "review")
        assert t is not None
        assert any("gate_passed" in c and "plan_approved" in c for c in t["conditions"])

    def test_revise_rollback_from_draft_to_structure(self, config: dict) -> None:
        """revise trigger should roll back from draft to structure."""
        t = _find_transition(config, "revise", "draft")
        assert t is not None
        assert t["dest"] == "structure"
        assert "conditions" not in t or t.get("conditions") is None

    def test_revise_rollback_from_review_to_draft(self, config: dict) -> None:
        """revise trigger should roll back from review to draft."""
        t = _find_transition(config, "revise", "review")
        assert t is not None
        assert t["dest"] == "draft"
        assert "conditions" not in t or t.get("conditions") is None

    def test_guards_section_present(self, config: dict) -> None:
        assert "guards" in config
        guard_names = set(config["guards"].keys())
        expected = {"has_goals", "has_research", "has_plan", "plan_approved"}
        assert expected == guard_names

    def test_each_guard_has_description_and_check(self, config: dict) -> None:
        for name, guard in config["guards"].items():
            assert "description" in guard, f"Guard {name} missing description"
            assert "check" in guard, f"Guard {name} missing check"

    def test_inputs_defined(self, config: dict) -> None:
        input_names = [i["name"] for i in config["inputs"]]
        assert "planning_goal" in input_names
        assert "project_root" in input_names

    def test_outputs_defined(self, config: dict) -> None:
        output_names = [o["name"] for o in config["outputs"]]
        assert "plan" in output_names
        assert "research" in output_names

    def test_v0_compatibility_fields_present(self, config: dict) -> None:
        """Plan mission includes v0 fields for backward compatibility."""
        assert config["name"] == "Planning Kitty"
        assert config["domain"] == "other"
        assert "workflow" in config
        assert "artifacts" in config
        assert "commands" in config


# ---------------------------------------------------------------------------
# Directory structure tests
# ---------------------------------------------------------------------------


class TestPlanMissionDirectoryStructure:
    """Verify the plan mission directory has the expected layout."""

    def test_plan_directory_exists(self) -> None:
        assert (MISSIONS_DIR / "plan").is_dir()

    def test_plan_mission_yaml_exists(self) -> None:
        assert (MISSIONS_DIR / "plan" / "mission.yaml").is_file()

    def test_plan_command_templates_exists(self) -> None:
        assert (MISSIONS_DIR / "plan" / "command-templates").is_dir()

    def test_plan_templates_exists(self) -> None:
        assert (MISSIONS_DIR / "plan" / "templates").is_dir()


# ---------------------------------------------------------------------------
# Guard expression validation (both missions use the 6 supported primitives)
# ---------------------------------------------------------------------------


SUPPORTED_GUARD_PRIMITIVES = [
    "artifact_exists",
    "event_count",
    "gate_passed",
    "wp_status",
    "file_contains",
    "command_succeeds",
]


class TestGuardExpressionPrimitives:
    """All guard check expressions must use only supported primitives."""

    @pytest.mark.parametrize("mission_name", ["research", "plan"])
    def test_all_guards_use_supported_primitives(self, mission_name: str) -> None:
        config = _load_yaml(mission_name)
        for name, guard in config.get("guards", {}).items():
            check = guard["check"]
            matched = any(prim in check for prim in SUPPORTED_GUARD_PRIMITIVES)
            assert matched, (
                f"Guard '{name}' in {mission_name} uses unsupported expression: {check}"
            )

    @pytest.mark.parametrize("mission_name", ["research", "plan"])
    def test_all_transition_conditions_use_supported_primitives(
        self, mission_name: str
    ) -> None:
        config = _load_yaml(mission_name)
        for t in config["transitions"]:
            for cond in t.get("conditions", []):
                matched = any(prim in cond for prim in SUPPORTED_GUARD_PRIMITIVES)
                assert matched, (
                    f"Transition {t['trigger']} ({t.get('source')} -> {t['dest']}) "
                    f"in {mission_name} uses unsupported condition: {cond}"
                )

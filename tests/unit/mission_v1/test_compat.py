"""Tests for PhaseMission v0 compatibility wrapper.

Verifies that PhaseMission correctly wraps existing v0 Mission objects
as linear state machines with the same API surface as StateMachineMission.
"""

from __future__ import annotations

import pytest
import yaml

from specify_cli.mission import Mission
from specify_cli.mission_v1 import MissionProtocol, PhaseMission


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mission_yaml(phases: list[dict[str, str]], **overrides) -> dict:
    """Build a minimal v0 mission.yaml dict."""
    config = {
        "name": overrides.get("name", "Test Mission"),
        "description": overrides.get("description", "A test mission"),
        "version": overrides.get("version", "1.0.0"),
        "domain": overrides.get("domain", "software"),
        "workflow": {"phases": phases},
        "artifacts": {"required": [], "optional": []},
    }
    return config


@pytest.fixture()
def two_phase_mission(tmp_path):
    """A simple two-phase mission (alpha -> beta)."""
    mission_dir = tmp_path / "two-phase"
    mission_dir.mkdir()
    config = _make_mission_yaml(
        [
            {"name": "alpha", "description": "First phase"},
            {"name": "beta", "description": "Second phase"},
        ],
        name="Two Phase",
        version="0.1.0",
    )
    (mission_dir / "mission.yaml").write_text(yaml.dump(config))
    return Mission(mission_dir)


@pytest.fixture()
def software_dev_mission(tmp_path):
    """A software-dev-like mission with five phases."""
    mission_dir = tmp_path / "software-dev"
    mission_dir.mkdir()
    config = _make_mission_yaml(
        [
            {"name": "research", "description": "Research technologies"},
            {"name": "design", "description": "Define architecture"},
            {"name": "implement", "description": "Write code"},
            {"name": "test", "description": "Validate implementation"},
            {"name": "review", "description": "Code review"},
        ],
        name="Software Dev Kitty",
        version="1.0.0",
        description="Build software with structured workflows",
    )
    artifacts = {
        "required": ["spec.md", "plan.md", "tasks.md"],
        "optional": ["data-model.md"],
    }
    config["artifacts"] = artifacts
    (mission_dir / "mission.yaml").write_text(yaml.dump(config))
    return Mission(mission_dir)


@pytest.fixture()
def single_phase_mission(tmp_path):
    """A minimal single-phase mission."""
    mission_dir = tmp_path / "single"
    mission_dir.mkdir()
    config = _make_mission_yaml(
        [{"name": "execute", "description": "Do the thing"}],
        name="Single Phase",
    )
    (mission_dir / "mission.yaml").write_text(yaml.dump(config))
    return Mission(mission_dir)


# ---------------------------------------------------------------------------
# T015 -- PhaseMission creation
# ---------------------------------------------------------------------------


class TestPhaseMissionCreation:
    """Verify PhaseMission can be created from v0 Mission objects."""

    def test_initial_state_is_first_phase(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        assert pm.state == "alpha"

    def test_initial_state_software_dev(self, software_dev_mission):
        pm = PhaseMission(software_dev_mission)
        assert pm.state == "research"

    def test_single_phase_initial_state(self, single_phase_mission):
        pm = PhaseMission(single_phase_mission)
        assert pm.state == "execute"

    def test_repr_contains_state(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        r = repr(pm)
        assert "PhaseMission" in r
        assert "alpha" in r
        assert "Two Phase" in r


# ---------------------------------------------------------------------------
# T016 -- Linear state machine transitions
# ---------------------------------------------------------------------------


class TestLinearTransitions:
    """Verify the synthetic linear state machine works correctly."""

    def test_advance_moves_to_next_phase(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        assert pm.state == "alpha"
        pm.advance()
        assert pm.state == "beta"

    def test_advance_to_done(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        pm.advance()  # alpha -> beta
        pm.advance()  # beta -> done
        assert pm.state == "done"

    def test_full_software_dev_progression(self, software_dev_mission):
        """Walk through all five phases plus done."""
        pm = PhaseMission(software_dev_mission)
        expected = ["research", "design", "implement", "test", "review", "done"]

        for expected_state in expected:
            assert pm.state == expected_state
            if expected_state != "done":
                pm.advance()

    def test_done_is_terminal(self, two_phase_mission):
        """After reaching done, no further advance is possible."""
        pm = PhaseMission(two_phase_mission)
        pm.advance()  # alpha -> beta
        pm.advance()  # beta -> done

        # The transitions library raises MachineError when no valid transition
        from transitions.core import MachineError

        with pytest.raises(MachineError):
            pm.advance()

    def test_single_phase_advance_to_done(self, single_phase_mission):
        pm = PhaseMission(single_phase_mission)
        assert pm.state == "execute"
        pm.advance()
        assert pm.state == "done"


# ---------------------------------------------------------------------------
# T017 -- API compatibility with MissionProtocol
# ---------------------------------------------------------------------------


class TestAPICompatibility:
    """Verify PhaseMission satisfies the MissionProtocol."""

    def test_isinstance_mission_protocol(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        assert isinstance(pm, MissionProtocol)

    def test_name_property(self, software_dev_mission):
        pm = PhaseMission(software_dev_mission)
        assert pm.name == "Software Dev Kitty"

    def test_version_property(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        assert pm.version == "0.1.0"

    def test_description_property(self, software_dev_mission):
        pm = PhaseMission(software_dev_mission)
        assert pm.description == "Build software with structured workflows"

    def test_state_property(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        assert isinstance(pm.state, str)
        assert pm.state == "alpha"

    def test_trigger_method(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        pm.trigger("advance")
        assert pm.state == "beta"

    def test_get_triggers_current_state(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        triggers = pm.get_triggers()
        assert "advance" in triggers

    def test_get_triggers_explicit_state(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        triggers = pm.get_triggers("beta")
        assert "advance" in triggers

    def test_get_triggers_done_state(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        triggers = pm.get_triggers("done")
        assert triggers == []

    def test_get_states(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        states = pm.get_states()
        assert "alpha" in states
        assert "beta" in states
        assert "done" in states
        assert len(states) == 3

    def test_get_states_software_dev(self, software_dev_mission):
        pm = PhaseMission(software_dev_mission)
        states = pm.get_states()
        expected = {"research", "design", "implement", "test", "review", "done"}
        assert set(states) == expected


# ---------------------------------------------------------------------------
# T018 -- Legacy Mission delegation
# ---------------------------------------------------------------------------


class TestLegacyDelegation:
    """Verify PhaseMission delegates legacy methods to wrapped Mission."""

    def test_get_workflow_phases(self, software_dev_mission):
        pm = PhaseMission(software_dev_mission)
        phases = pm.get_workflow_phases()
        assert len(phases) == 5
        assert phases[0]["name"] == "research"
        assert phases[4]["name"] == "review"

    def test_get_required_artifacts(self, software_dev_mission):
        pm = PhaseMission(software_dev_mission)
        artifacts = pm.get_required_artifacts()
        assert "spec.md" in artifacts
        assert "plan.md" in artifacts
        assert "tasks.md" in artifacts

    def test_get_required_artifacts_empty(self, two_phase_mission):
        pm = PhaseMission(two_phase_mission)
        artifacts = pm.get_required_artifacts()
        assert artifacts == []

    def test_get_template_delegates(self, tmp_path):
        """Verify get_template delegates to the wrapped Mission."""
        mission_dir = tmp_path / "with-templates"
        mission_dir.mkdir()
        templates_dir = mission_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "spec-template.md").write_text("# Spec Template")

        config = _make_mission_yaml(
            [{"name": "plan", "description": "Plan things"}],
        )
        (mission_dir / "mission.yaml").write_text(yaml.dump(config))

        mission = Mission(mission_dir)
        pm = PhaseMission(mission)

        template_path = pm.get_template("spec-template.md")
        assert template_path.exists()
        assert template_path.name == "spec-template.md"

    def test_get_command_template_delegates(self, tmp_path):
        """Verify get_command_template delegates to the wrapped Mission."""
        mission_dir = tmp_path / "with-commands"
        mission_dir.mkdir()
        cmd_dir = mission_dir / "command-templates"
        cmd_dir.mkdir()
        (cmd_dir / "implement.md").write_text("# Implement")

        config = _make_mission_yaml(
            [{"name": "build", "description": "Build things"}],
        )
        (mission_dir / "mission.yaml").write_text(yaml.dump(config))

        mission = Mission(mission_dir)
        pm = PhaseMission(mission)

        cmd_path = pm.get_command_template("implement")
        assert cmd_path.exists()
        assert cmd_path.name == "implement.md"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and error conditions."""

    def test_advance_not_available_from_done(self, single_phase_mission):
        """Once in done, get_triggers returns empty."""
        pm = PhaseMission(single_phase_mission)
        pm.advance()  # execute -> done
        assert pm.get_triggers() == []

    def test_state_after_multiple_advances(self, software_dev_mission):
        """Verify state is correct after advancing multiple times."""
        pm = PhaseMission(software_dev_mission)
        pm.advance()
        pm.advance()
        pm.advance()
        assert pm.state == "test"

    def test_trigger_returns_truthy(self, two_phase_mission):
        """trigger() should return a truthy value on success."""
        pm = PhaseMission(two_phase_mission)
        result = pm.trigger("advance")
        assert result

    def test_many_phases(self, tmp_path):
        """Verify PhaseMission works with many phases."""
        mission_dir = tmp_path / "many-phases"
        mission_dir.mkdir()
        phases = [
            {"name": f"phase_{i}", "description": f"Phase {i}"}
            for i in range(20)
        ]
        config = _make_mission_yaml(phases, name="Many Phases")
        (mission_dir / "mission.yaml").write_text(yaml.dump(config))

        mission = Mission(mission_dir)
        pm = PhaseMission(mission)

        # Should have 21 states (20 phases + done)
        assert len(pm.get_states()) == 21
        assert pm.state == "phase_0"

        # Advance through all phases
        for i in range(20):
            pm.advance()

        assert pm.state == "done"

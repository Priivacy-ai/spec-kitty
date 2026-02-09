"""Tests for the guard expression compiler (mission_v1.guards).

Covers:
- T010: Guard expression parser
- T011: 6 guard primitives
- T012: Guard compilation (string -> bound callable)
- T013: Unknown guard rejection at load time
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.mission_v1.guards import (
    GUARD_REGISTRY,
    compile_guards,
    parse_guard_expression,
)
from specify_cli.mission_v1.schema import MissionValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(feature_dir: Path | None = None, inputs: dict | None = None) -> MagicMock:
    """Create a mock model with optional feature_dir and inputs."""
    model = MagicMock()
    model.feature_dir = feature_dir
    model.inputs = inputs or {}
    return model


def _make_event(model: MagicMock) -> MagicMock:
    """Create a mock EventData with .model attribute."""
    event = MagicMock()
    event.model = model
    return event


# ===================================================================
# T010 -- Guard expression parser
# ===================================================================


class TestParseGuardExpression:
    """Tests for parse_guard_expression()."""

    def test_single_string_arg(self) -> None:
        name, args = parse_guard_expression('artifact_exists("spec.md")')
        assert name == "artifact_exists"
        assert args == ["spec.md"]

    def test_single_string_arg_single_quotes(self) -> None:
        name, args = parse_guard_expression("artifact_exists('spec.md')")
        assert name == "artifact_exists"
        assert args == ["spec.md"]

    def test_string_and_int_args(self) -> None:
        name, args = parse_guard_expression('event_count("source_documented", 3)')
        assert name == "event_count"
        assert args == ["source_documented", 3]

    def test_single_input_arg(self) -> None:
        name, args = parse_guard_expression('input_provided("name")')
        assert name == "input_provided"
        assert args == ["name"]

    def test_no_args(self) -> None:
        name, args = parse_guard_expression("some_guard()")
        assert name == "some_guard"
        assert args == []

    def test_whitespace_handling(self) -> None:
        name, args = parse_guard_expression('  event_count( "type" , 5 )  ')
        assert name == "event_count"
        assert args == ["type", 5]

    def test_path_with_slashes(self) -> None:
        name, args = parse_guard_expression('artifact_exists("tasks/WP01.md")')
        assert name == "artifact_exists"
        assert args == ["tasks/WP01.md"]

    def test_invalid_no_parens(self) -> None:
        with pytest.raises(ValueError, match="Invalid guard expression syntax"):
            parse_guard_expression("just_a_name")

    def test_invalid_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid guard expression syntax"):
            parse_guard_expression("")

    def test_bare_identifier_arg(self) -> None:
        """Bare identifiers (no quotes) are kept as strings."""
        name, args = parse_guard_expression("gate_passed(my_gate)")
        assert name == "gate_passed"
        assert args == ["my_gate"]


# ===================================================================
# T011 -- Guard primitives
# ===================================================================


class TestArtifactExistsGuard:
    """Tests for artifact_exists guard primitive."""

    def test_file_exists(self, tmp_path: Path) -> None:
        (tmp_path / "spec.md").write_text("# Spec")
        factory = GUARD_REGISTRY["artifact_exists"]
        guard = factory(["spec.md"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True

    def test_file_missing(self, tmp_path: Path) -> None:
        factory = GUARD_REGISTRY["artifact_exists"]
        guard = factory(["spec.md"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False

    def test_no_feature_dir(self) -> None:
        factory = GUARD_REGISTRY["artifact_exists"]
        guard = factory(["spec.md"])
        model = _make_model(feature_dir=None)
        assert guard(_make_event(model)) is False

    def test_nested_path(self, tmp_path: Path) -> None:
        (tmp_path / "tasks").mkdir()
        (tmp_path / "tasks" / "WP01.md").write_text("---\nlane: done\n---\n")
        factory = GUARD_REGISTRY["artifact_exists"]
        guard = factory(["tasks/WP01.md"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True


class TestGatePassedGuard:
    """Tests for gate_passed guard primitive."""

    def test_gate_found(self, tmp_path: Path) -> None:
        log = tmp_path / "mission-events.jsonl"
        log.write_text(
            json.dumps({"type": "gate_passed", "name": "planning_complete"}) + "\n"
        )
        factory = GUARD_REGISTRY["gate_passed"]
        guard = factory(["planning_complete"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True

    def test_gate_not_found(self, tmp_path: Path) -> None:
        log = tmp_path / "mission-events.jsonl"
        log.write_text(
            json.dumps({"type": "gate_passed", "name": "other_gate"}) + "\n"
        )
        factory = GUARD_REGISTRY["gate_passed"]
        guard = factory(["planning_complete"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False

    def test_no_log_file(self, tmp_path: Path) -> None:
        factory = GUARD_REGISTRY["gate_passed"]
        guard = factory(["planning_complete"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False

    def test_no_feature_dir(self) -> None:
        factory = GUARD_REGISTRY["gate_passed"]
        guard = factory(["planning_complete"])
        model = _make_model(feature_dir=None)
        assert guard(_make_event(model)) is False

    def test_multiple_events_in_log(self, tmp_path: Path) -> None:
        log = tmp_path / "mission-events.jsonl"
        lines = [
            json.dumps({"type": "state_entered", "name": "specifying"}),
            json.dumps({"type": "gate_passed", "name": "spec_review"}),
            json.dumps({"type": "gate_passed", "name": "planning_complete"}),
        ]
        log.write_text("\n".join(lines) + "\n")
        factory = GUARD_REGISTRY["gate_passed"]
        guard = factory(["planning_complete"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True


class TestAllWpStatusGuard:
    """Tests for all_wp_status guard primitive."""

    def test_all_done(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "WP01.md").write_text("---\nlane: done\n---\n# WP01\n")
        (tasks_dir / "WP02.md").write_text("---\nlane: done\n---\n# WP02\n")
        factory = GUARD_REGISTRY["all_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True

    def test_some_not_done(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "WP01.md").write_text("---\nlane: done\n---\n# WP01\n")
        (tasks_dir / "WP02.md").write_text("---\nlane: doing\n---\n# WP02\n")
        factory = GUARD_REGISTRY["all_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False

    def test_no_tasks_dir(self, tmp_path: Path) -> None:
        factory = GUARD_REGISTRY["all_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False

    def test_no_feature_dir(self) -> None:
        factory = GUARD_REGISTRY["all_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=None)
        assert guard(_make_event(model)) is False

    def test_empty_tasks_dir(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        factory = GUARD_REGISTRY["all_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=tmp_path)
        # No WP files means False (nothing to check)
        assert guard(_make_event(model)) is False

    def test_quoted_lane_value(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "WP01.md").write_text('---\nlane: "done"\n---\n# WP01\n')
        factory = GUARD_REGISTRY["all_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True


class TestAnyWpStatusGuard:
    """Tests for any_wp_status guard primitive."""

    def test_one_matches(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "WP01.md").write_text("---\nlane: done\n---\n# WP01\n")
        (tasks_dir / "WP02.md").write_text("---\nlane: doing\n---\n# WP02\n")
        factory = GUARD_REGISTRY["any_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True

    def test_none_match(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "WP01.md").write_text("---\nlane: planned\n---\n# WP01\n")
        (tasks_dir / "WP02.md").write_text("---\nlane: doing\n---\n# WP02\n")
        factory = GUARD_REGISTRY["any_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False

    def test_no_feature_dir(self) -> None:
        factory = GUARD_REGISTRY["any_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=None)
        assert guard(_make_event(model)) is False

    def test_empty_tasks_dir(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        factory = GUARD_REGISTRY["any_wp_status"]
        guard = factory(["done"])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False


class TestInputProvidedGuard:
    """Tests for input_provided guard primitive."""

    def test_key_exists(self) -> None:
        factory = GUARD_REGISTRY["input_provided"]
        guard = factory(["project_url"])
        model = _make_model(inputs={"project_url": "https://example.com"})
        assert guard(_make_event(model)) is True

    def test_key_missing(self) -> None:
        factory = GUARD_REGISTRY["input_provided"]
        guard = factory(["project_url"])
        model = _make_model(inputs={"other_key": "value"})
        assert guard(_make_event(model)) is False

    def test_key_none_value(self) -> None:
        factory = GUARD_REGISTRY["input_provided"]
        guard = factory(["project_url"])
        model = _make_model(inputs={"project_url": None})
        assert guard(_make_event(model)) is False

    def test_no_inputs_attr(self) -> None:
        factory = GUARD_REGISTRY["input_provided"]
        guard = factory(["project_url"])
        model = MagicMock(spec=[])  # no attributes at all
        model.inputs = None
        event = _make_event(model)
        assert guard(event) is False

    def test_empty_string_value_is_truthy(self) -> None:
        """Empty string is not None, so it counts as 'provided'."""
        factory = GUARD_REGISTRY["input_provided"]
        guard = factory(["project_url"])
        model = _make_model(inputs={"project_url": ""})
        assert guard(_make_event(model)) is True


class TestEventCountGuard:
    """Tests for event_count guard primitive."""

    def test_enough_events(self, tmp_path: Path) -> None:
        log = tmp_path / "mission-events.jsonl"
        lines = [
            json.dumps({"type": "source_documented", "path": "a.py"}),
            json.dumps({"type": "source_documented", "path": "b.py"}),
            json.dumps({"type": "source_documented", "path": "c.py"}),
        ]
        log.write_text("\n".join(lines) + "\n")
        factory = GUARD_REGISTRY["event_count"]
        guard = factory(["source_documented", 3])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True

    def test_not_enough_events(self, tmp_path: Path) -> None:
        log = tmp_path / "mission-events.jsonl"
        lines = [
            json.dumps({"type": "source_documented", "path": "a.py"}),
        ]
        log.write_text("\n".join(lines) + "\n")
        factory = GUARD_REGISTRY["event_count"]
        guard = factory(["source_documented", 3])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False

    def test_no_log_file(self, tmp_path: Path) -> None:
        factory = GUARD_REGISTRY["event_count"]
        guard = factory(["source_documented", 1])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False

    def test_no_feature_dir(self) -> None:
        factory = GUARD_REGISTRY["event_count"]
        guard = factory(["source_documented", 1])
        model = _make_model(feature_dir=None)
        assert guard(_make_event(model)) is False

    def test_mixed_event_types(self, tmp_path: Path) -> None:
        log = tmp_path / "mission-events.jsonl"
        lines = [
            json.dumps({"type": "source_documented", "path": "a.py"}),
            json.dumps({"type": "other_event", "path": "b.py"}),
            json.dumps({"type": "source_documented", "path": "c.py"}),
        ]
        log.write_text("\n".join(lines) + "\n")
        factory = GUARD_REGISTRY["event_count"]
        guard = factory(["source_documented", 2])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True

    def test_exactly_min_count(self, tmp_path: Path) -> None:
        log = tmp_path / "mission-events.jsonl"
        log.write_text(json.dumps({"type": "reviewed"}) + "\n")
        factory = GUARD_REGISTRY["event_count"]
        guard = factory(["reviewed", 1])
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True


# ===================================================================
# T012 -- Guard compilation
# ===================================================================


class TestCompileGuards:
    """Tests for compile_guards()."""

    def test_compiles_conditions(self, tmp_path: Path) -> None:
        (tmp_path / "spec.md").write_text("# Spec")
        config = {
            "transitions": [
                {
                    "trigger": "start_planning",
                    "source": "specifying",
                    "dest": "planning",
                    "conditions": ['artifact_exists("spec.md")'],
                },
            ],
        }
        result = compile_guards(config, feature_dir=tmp_path)
        # The string should have been replaced with a callable
        entry = result["transitions"][0]["conditions"][0]
        assert callable(entry)

    def test_compiles_unless(self, tmp_path: Path) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "start_planning",
                    "source": "specifying",
                    "dest": "planning",
                    "unless": ['input_provided("skip_flag")'],
                },
            ],
        }
        result = compile_guards(config, feature_dir=tmp_path)
        entry = result["transitions"][0]["unless"][0]
        assert callable(entry)

    def test_non_expression_strings_left_alone(self) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "start",
                    "source": "idle",
                    "dest": "running",
                    "conditions": ["is_ready"],  # plain method name, no parens
                },
            ],
        }
        result = compile_guards(config)
        # Should remain as the original string
        assert result["transitions"][0]["conditions"][0] == "is_ready"

    def test_mutates_config_in_place(self) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "go",
                    "source": "a",
                    "dest": "b",
                    "conditions": ['artifact_exists("readme.md")'],
                },
            ],
        }
        result = compile_guards(config)
        assert result is config  # same object

    def test_multiple_guards_in_one_transition(self) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "go",
                    "source": "a",
                    "dest": "b",
                    "conditions": [
                        'artifact_exists("spec.md")',
                        'gate_passed("review")',
                    ],
                    "unless": [
                        'input_provided("skip")',
                    ],
                },
            ],
        }
        result = compile_guards(config)
        assert callable(result["transitions"][0]["conditions"][0])
        assert callable(result["transitions"][0]["conditions"][1])
        assert callable(result["transitions"][0]["unless"][0])

    def test_no_transitions_key(self) -> None:
        """Config without transitions should not raise."""
        config = {"states": [{"name": "idle"}]}
        result = compile_guards(config)
        assert result is config

    def test_transition_without_conditions(self) -> None:
        """Transitions without conditions/unless should not raise."""
        config = {
            "transitions": [
                {"trigger": "go", "source": "a", "dest": "b"},
            ],
        }
        result = compile_guards(config)
        assert result is config

    def test_compiled_guard_evaluates_correctly(self, tmp_path: Path) -> None:
        """End-to-end: compile then evaluate a guard."""
        (tmp_path / "plan.md").write_text("# Plan")
        config = {
            "transitions": [
                {
                    "trigger": "begin_tasks",
                    "source": "planning",
                    "dest": "tasking",
                    "conditions": ['artifact_exists("plan.md")'],
                },
            ],
        }
        compile_guards(config, feature_dir=tmp_path)
        guard = config["transitions"][0]["conditions"][0]
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is True

    def test_compiled_guard_returns_false_when_missing(self, tmp_path: Path) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "begin_tasks",
                    "source": "planning",
                    "dest": "tasking",
                    "conditions": ['artifact_exists("nonexistent.md")'],
                },
            ],
        }
        compile_guards(config, feature_dir=tmp_path)
        guard = config["transitions"][0]["conditions"][0]
        model = _make_model(feature_dir=tmp_path)
        assert guard(_make_event(model)) is False


# ===================================================================
# T013 -- Unknown guard rejection
# ===================================================================


class TestUnknownGuardRejection:
    """Tests for unknown guard expression rejection at compile time."""

    def test_unknown_guard_raises(self) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "go",
                    "source": "a",
                    "dest": "b",
                    "conditions": ['unknown_guard("arg")'],
                },
            ],
        }
        with pytest.raises(MissionValidationError, match="Unknown guard expression.*unknown_guard"):
            compile_guards(config)

    def test_unknown_guard_shows_supported(self) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "go",
                    "source": "a",
                    "dest": "b",
                    "conditions": ['artifcat_exists("spec.md")'],  # typo
                },
            ],
        }
        with pytest.raises(MissionValidationError, match="Supported guards:"):
            compile_guards(config)

    def test_unknown_guard_in_unless(self) -> None:
        config = {
            "transitions": [
                {
                    "trigger": "go",
                    "source": "a",
                    "dest": "b",
                    "unless": ['custom_check("x")'],
                },
            ],
        }
        with pytest.raises(MissionValidationError, match="Unknown guard expression.*custom_check"):
            compile_guards(config)


# ===================================================================
# Registry completeness
# ===================================================================


class TestGuardRegistry:
    """Verify the registry has exactly the 6 expected primitives."""

    EXPECTED_GUARDS = {
        "artifact_exists",
        "gate_passed",
        "all_wp_status",
        "any_wp_status",
        "input_provided",
        "event_count",
    }

    def test_registry_keys(self) -> None:
        assert set(GUARD_REGISTRY.keys()) == self.EXPECTED_GUARDS

    def test_all_values_are_callable(self) -> None:
        for name, factory in GUARD_REGISTRY.items():
            assert callable(factory), f"GUARD_REGISTRY['{name}'] is not callable"

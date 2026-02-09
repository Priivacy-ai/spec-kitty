"""MissionRunner -- v1 state machine mission backed by MarkupMachine.

Provides:
- MissionModel: Lightweight model object that MarkupMachine attaches state
  and trigger methods to. Holds context needed by guards and callbacks.
- StateMachineMission: Wrapper that loads a validated v1 config dict,
  constructs a MarkupMachine, and exposes a clean public API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transitions import MachineError
from transitions.extensions.markup import MarkupMachine

from specify_cli.mission_v1.events import emit_event
from specify_cli.mission_v1.guards import compile_guards
from specify_cli.mission_v1.schema import MissionValidationError, validate_mission_v1


__all__ = [
    "MissionModel",
    "StateMachineMission",
    "MachineError",
]


class MissionModel:
    """Model object for the mission state machine.

    MarkupMachine attaches a ``.state`` attribute and trigger methods
    (e.g. ``model.advance()``) to this object at construction time.

    It also holds context needed by guards and callbacks.

    Attributes:
        feature_dir: Optional path to the feature directory for guard context.
        inputs: Dict of user-supplied input values keyed by input name.
        event_log_path: Optional path to an event log file.
        mission_name: Name of the mission (used in emitted events).
        state: Current state name, managed by MarkupMachine.
    """

    def __init__(
        self,
        feature_dir: Path | None = None,
        inputs: dict[str, Any] | None = None,
        event_log_path: Path | None = None,
        mission_name: str = "",
    ) -> None:
        self.feature_dir = feature_dir
        self.inputs: dict[str, Any] = inputs or {}
        self.event_log_path = event_log_path
        self.mission_name = mission_name
        # MarkupMachine sets this to the initial state during construction.
        self.state: str = ""

    # ------------------------------------------------------------------
    # Callbacks -- emit events on state entry/exit.
    # ------------------------------------------------------------------

    def on_enter_state(self, event: Any) -> None:
        """Emit a ``phase_entered`` event when entering a state.

        Called as ``after_state_change`` by the MarkupMachine. The *event*
        parameter is a ``transitions.EventData`` instance whose
        ``transition.dest`` holds the destination state name.
        """
        dest = getattr(getattr(event, "transition", None), "dest", None)
        state_name = dest if dest else self.state
        emit_event(
            "phase_entered",
            {"state": state_name},
            mission_name=self.mission_name,
            feature_dir=self.feature_dir,
        )

    def on_exit_state(self, event: Any) -> None:
        """Emit a ``phase_exited`` event when leaving a state.

        Called as ``before_state_change`` by the MarkupMachine. The *event*
        parameter is a ``transitions.EventData`` instance whose
        ``transition.source`` holds the source state name.
        """
        source = getattr(getattr(event, "transition", None), "source", None)
        state_name = source if source else self.state
        emit_event(
            "phase_exited",
            {"state": state_name},
            mission_name=self.mission_name,
            feature_dir=self.feature_dir,
        )


def _strip_guard_references(transitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove ``conditions`` and ``unless`` from transitions.

    Guard expression strings (e.g. ``artifact_exists("spec.md")``) reference
    methods that won't exist on the model until WP03 compiles them. For this
    WP we strip them so MarkupMachine doesn't try to resolve missing methods.

    Returns a deep copy -- the original list is not mutated.
    """
    cleaned: list[dict[str, Any]] = []
    for t in transitions:
        entry = dict(t)  # shallow copy of this transition dict
        entry.pop("conditions", None)
        entry.pop("unless", None)
        cleaned.append(entry)
    return cleaned


def _transitions_have_callables(transitions: list[dict[str, Any]]) -> bool:
    """Return True if any transition contains callable guards."""
    for transition in transitions:
        for key in ("conditions", "unless"):
            entries = transition.get(key) or []
            if any(callable(e) for e in entries):
                return True
    return False

class StateMachineMission:
    """v1 state machine mission backed by ``transitions.MarkupMachine``.

    Wraps a validated config dict into a working state machine with a clean
    public API. Schema validation is performed at construction time.

    Args:
        config: Parsed YAML dict that must pass v1 schema validation.
        feature_dir: Optional feature directory for guard context.
        inputs: Optional dict of user-supplied input values.
        event_log_path: Optional path to an event log file.

    Raises:
        MissionValidationError: If the config fails schema validation.
    """

    def __init__(
        self,
        config: dict[str, Any],
        feature_dir: Path | None = None,
        inputs: dict[str, Any] | None = None,
        event_log_path: Path | None = None,
    ) -> None:
        if not _transitions_have_callables(config.get("transitions", [])):
            validate_mission_v1(config)

        self._config = config
        self._mission_info: dict[str, Any] = config.get("mission", {})

        self._model = MissionModel(
            feature_dir=feature_dir,
            inputs=inputs,
            event_log_path=event_log_path,
            mission_name=self._mission_info.get("name", ""),
        )

        # Compile guard expressions (no-op when already compiled to callables).
        compiled_config = compile_guards(config, feature_dir=feature_dir)

        states = []
        for state in compiled_config.get("states", []):
            if isinstance(state, dict):
                cleaned = {k: v for k, v in state.items() if k != "display_name"}
                states.append(cleaned)
            else:
                states.append(state)

        machine_config: dict[str, Any] = {
            "states": states,
            "transitions": compiled_config["transitions"],
            "initial": compiled_config["initial"],
            "auto_transitions": False,
            "send_event": True,
            "before_state_change": "on_exit_state",
            "after_state_change": "on_enter_state",
        }

        self._machine: MarkupMachine = MarkupMachine(
            model=self._model,
            **machine_config,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Mission name from the ``mission`` metadata block."""
        return self._mission_info.get("name", "")

    @property
    def version(self) -> str:
        """Mission version from the ``mission`` metadata block."""
        return self._mission_info.get("version", "")

    @property
    def description(self) -> str:
        """Mission description from the ``mission`` metadata block."""
        return self._mission_info.get("description", "")

    @property
    def state(self) -> str:
        """Current state of the mission state machine."""
        return self._model.state

    @property
    def model(self) -> MissionModel:
        """The underlying model object (for advanced / testing use)."""
        return self._model

    def trigger(self, trigger_name: str, **kwargs: Any) -> bool:
        """Fire a named trigger on the state machine.

        Args:
            trigger_name: The trigger event name (e.g. ``"advance"``).
            **kwargs: Extra keyword arguments forwarded to the trigger method.

        Returns:
            True if the transition was executed.

        Raises:
            MachineError: If the trigger is not valid from the current state.
            AttributeError: If ``trigger_name`` is not a known trigger at all.
        """
        method = getattr(self._model, trigger_name)
        return method(**kwargs)

    def get_triggers(self, state: str | None = None) -> list[str]:
        """Return the list of trigger names available from *state*.

        Args:
            state: State to query. Defaults to the current state.
        """
        if state is None:
            state = self.state
        return self._machine.get_triggers(state)

    def get_states(self) -> list[str]:
        """Return all state names defined in the mission."""
        return [s.name for s in self._machine.states.values()]

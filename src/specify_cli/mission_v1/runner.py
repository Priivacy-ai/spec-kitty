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


def _sanitize_transition_guards(transitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sanitize guard entries while preserving compiled/runtime-safe guards.

    - Keeps compiled callables.
    - Drops all string guards to avoid unresolved method lookups.
    - Drops non-callable, non-string entries.

    Returns a deep copy -- the original list is not mutated.
    """
    cleaned: list[dict[str, Any]] = []
    for t in transitions:
        entry = dict(t)  # shallow copy of this transition dict

        for key in ("conditions", "unless"):
            guards = entry.get(key)
            if not guards:
                continue

            if not isinstance(guards, list):
                guards = [guards]

            normalized: list[Any] = []
            for guard in guards:
                if callable(guard):
                    normalized.append(guard)

            if normalized:
                entry[key] = normalized
            else:
                entry.pop(key, None)

        cleaned.append(entry)
    return cleaned


def _sanitize_states(states: list[Any]) -> list[Any]:
    """Return states compatible with transitions.MarkupMachine.

    Mission YAML carries metadata like ``display_name`` for documentation.
    transitions only accepts state keys it understands, so we trim each state
    down to runtime keys.
    """
    cleaned: list[Any] = []
    for state in states:
        if not isinstance(state, dict):
            cleaned.append(state)
            continue

        cleaned_state: dict[str, Any] = {"name": state["name"]}
        if "on_enter" in state:
            cleaned_state["on_enter"] = state["on_enter"]
        if "on_exit" in state:
            cleaned_state["on_exit"] = state["on_exit"]
        cleaned.append(cleaned_state)
    return cleaned


class StateMachineMission:
    """v1 state machine mission backed by ``transitions.MarkupMachine``.

    Wraps a validated config dict into a working state machine with a clean
    public API. Schema validation is performed at construction time.

    Args:
        config: Parsed YAML dict that must pass v1 schema validation.
        feature_dir: Optional feature directory for guard context.
        inputs: Optional dict of user-supplied input values.
        event_log_path: Optional path to an event log file.
        validate_schema: When True, validate *config* against the v1 schema.
            Set False for prevalidated configs that contain compiled guard
            callables.

    Raises:
        MissionValidationError: If the config fails schema validation.
    """

    def __init__(
        self,
        config: dict[str, Any],
        feature_dir: Path | None = None,
        inputs: dict[str, Any] | None = None,
        event_log_path: Path | None = None,
        validate_schema: bool = True,
    ) -> None:
        if validate_schema:
            validate_mission_v1(config)

        self._config = config
        self._mission_info: dict[str, Any] = config.get("mission", {})

        self._model = MissionModel(
            feature_dir=feature_dir,
            inputs=inputs,
            event_log_path=event_log_path,
            mission_name=self._mission_info.get("name", ""),
        )

        sanitised_transitions = _sanitize_transition_guards(config["transitions"])
        sanitised_states = _sanitize_states(config["states"])

        machine_config: dict[str, Any] = {
            "states": sanitised_states,
            "transitions": sanitised_transitions,
            "initial": config["initial"],
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

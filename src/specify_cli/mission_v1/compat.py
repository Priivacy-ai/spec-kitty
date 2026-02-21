"""PhaseMission: v0 phase-list mission wrapped as a linear state machine.

Wraps existing v0 Mission objects (from specify_cli.mission) and exposes
the same API surface as StateMachineMission, so callers don't need to
distinguish between v0 and v1 missions.

Usage::

    from specify_cli.mission import Mission
    from specify_cli.mission_v1.compat import PhaseMission

    mission = Mission(mission_dir)
    pm = PhaseMission(mission)
    assert pm.state == "research"
    pm.advance()
    assert pm.state == "design"
"""

from __future__ import annotations

from typing import Any

from transitions import Machine

from specify_cli.mission import Mission


class PhaseMission:
    """v0 phase-list mission wrapped as a linear state machine.

    Provides API compatibility with StateMachineMission so callers
    don't need to distinguish between v0 and v1 missions.
    """

    def __init__(self, mission: Mission) -> None:
        """Wrap a v0 Mission as a linear state machine.

        Generates a synthetic linear state machine from the mission's
        ``workflow.phases`` list, adding a terminal ``done`` state.
        Each phase transitions to the next via an ``advance`` trigger.

        Args:
            mission: Existing Mission object (v0 phase-list format).

        Raises:
            ValueError: If the mission has no workflow phases.
        """
        self._mission = mission
        self._phases = [p["name"] for p in mission.get_workflow_phases()]

        if not self._phases:
            raise ValueError(f"Mission '{mission.name}' has no workflow phases; cannot create PhaseMission")

        # Generate linear state machine: [phase1, phase2, ..., phaseN, done]
        states = self._phases + ["done"]
        transitions = self._build_linear_transitions()

        self._machine = Machine(
            model=self,
            states=states,
            transitions=transitions,
            initial=self._phases[0],
            auto_transitions=False,
        )

    # -- Linear transition builder --

    def _build_linear_transitions(self) -> list[dict[str, Any]]:
        """Generate linear advance transitions from phase list.

        Returns a list of transition dicts, each moving from one phase
        to the next via the ``advance`` trigger. No rollback transitions
        are generated for v0 missions (they are advisory phases).
        """
        transitions: list[dict[str, Any]] = []
        all_states = self._phases + ["done"]

        for i in range(len(all_states) - 1):
            transitions.append(
                {
                    "trigger": "advance",
                    "source": all_states[i],
                    "dest": all_states[i + 1],
                }
            )

        return transitions

    # -- API surface (matches StateMachineMission) --

    @property
    def name(self) -> str:
        """Mission display name."""
        return self._mission.name

    @property
    def version(self) -> str:
        """Mission version string."""
        return self._mission.version

    @property
    def description(self) -> str:
        """Mission description."""
        return self._mission.description

    def trigger(self, trigger_name: str, **kwargs: Any) -> bool:
        """Fire a named trigger on the state machine.

        Args:
            trigger_name: Name of the trigger to fire (e.g. ``"advance"``).
            **kwargs: Additional keyword arguments passed to the trigger.

        Returns:
            True if the transition was executed successfully.
        """
        return getattr(self, trigger_name)(**kwargs)

    def get_triggers(self, state: str | None = None) -> list[str]:
        """Get available trigger names for a state.

        Args:
            state: State to query. Defaults to the current state.

        Returns:
            List of trigger names available from the given state.
        """
        if state is None:
            state = self.state
        return self._machine.get_triggers(state)

    def get_states(self) -> list[str]:
        """Get all state names in the machine.

        Returns:
            List of state name strings, including the terminal ``done`` state.
        """
        return [s.name for s in self._machine.states.values()]

    # -- Legacy Mission delegation --

    def get_workflow_phases(self) -> list[dict[str, str]]:
        """Delegate to the wrapped Mission's workflow phases."""
        return self._mission.get_workflow_phases()

    def get_required_artifacts(self) -> list[str]:
        """Delegate to the wrapped Mission's required artifacts list."""
        return self._mission.get_required_artifacts()

    def get_template(self, template_name: str):
        """Delegate to the wrapped Mission's template lookup."""
        return self._mission.get_template(template_name)

    def get_command_template(self, command_name: str, project_dir=None):
        """Delegate to the wrapped Mission's command template lookup."""
        return self._mission.get_command_template(command_name, project_dir)

    def __repr__(self) -> str:
        return f"PhaseMission(name={self.name!r}, version={self.version!r}, state={self.state!r})"

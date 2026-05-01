"""Runtime-to-sync emitter adapter for canonical mission events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specify_cli.mission_metadata import resolve_mission_identity

from .events import get_emitter


class SyncRuntimeEventEmitter:
    """Bridge runtime event callbacks onto the canonical sync EventEmitter."""

    def __init__(
        self,
        *,
        mission_slug: str,
        mission_type: str,
        mission_id: str | None,
    ) -> None:
        self._emitter = get_emitter()
        self._mission_slug = mission_slug
        self._mission_type = mission_type
        self._mission_id = mission_id
        self._started = False
        self._current_phase: str | None = None

    @classmethod
    def for_feature(
        cls,
        *,
        feature_dir: Path,
        mission_slug: str,
        mission_type: str,
    ) -> SyncRuntimeEventEmitter:
        try:
            mission_id = resolve_mission_identity(feature_dir).mission_id
        except Exception:
            mission_id = None
        return cls(
            mission_slug=mission_slug,
            mission_type=mission_type,
            mission_id=mission_id,
        )

    def seed_from_snapshot(self, snapshot: Any) -> None:
        """Initialize adapter state from a persisted runtime snapshot."""
        has_history = bool(
            getattr(snapshot, "issued_step_id", None)
            or getattr(snapshot, "completed_steps", None)
            or getattr(snapshot, "pending_decisions", None)
            or getattr(snapshot, "decisions", None)
            or getattr(snapshot, "blocked_reason", None)
        )
        if has_history:
            self._started = True

        phase = self._infer_phase_from_snapshot(snapshot)
        if phase is not None:
            self._current_phase = phase
        elif self._started and self._current_phase is None:
            self._current_phase = "not_started"

    def emit_mission_run_started(self, payload: Any) -> None:
        self._emitter.emit_mission_run_started(
            payload,
            mission_id=self._mission_id,
            mission_slug=self._mission_slug,
        )
        if not self._started and self._mission_id:
            actor_id = self._actor_id(payload)
            self._emitter.emit_mission_started(
                mission_id=self._mission_id,
                mission_type=self._mission_type,
                initial_phase="not_started",
                actor=actor_id,
                mission_slug=self._mission_slug,
            )
        self._started = True
        if self._current_phase is None:
            self._current_phase = "not_started"

    def emit_next_step_issued(self, payload: Any) -> None:
        self._enter_phase(getattr(payload, "step_id", None), self._actor_id(payload))
        self._emitter.emit_next_step_issued(
            payload,
            mission_id=self._mission_id,
            mission_slug=self._mission_slug,
        )

    def emit_next_step_auto_completed(self, payload: Any) -> None:
        self._emitter.emit_next_step_auto_completed(
            payload,
            mission_id=self._mission_id,
            mission_slug=self._mission_slug,
        )

    def emit_decision_input_requested(self, payload: Any) -> None:
        self._enter_phase(getattr(payload, "step_id", None), self._actor_id(payload))
        self._emitter.emit_decision_input_requested(
            payload,
            mission_id=self._mission_id,
            mission_slug=self._mission_slug,
        )

    def emit_decision_input_answered(self, payload: Any) -> None:
        self._emitter.emit_decision_input_answered(
            payload,
            mission_id=self._mission_id,
            mission_slug=self._mission_slug,
        )

    def emit_mission_run_completed(self, payload: Any) -> None:
        self._emitter.emit_mission_run_completed(
            payload,
            mission_id=self._mission_id,
            mission_slug=self._mission_slug,
        )
        if self._mission_id:
            self._emitter.emit_mission_completed(
                mission_id=self._mission_id,
                mission_type=self._mission_type,
                final_phase=self._current_phase or "unknown",
                actor=self._actor_id(payload),
                mission_slug=self._mission_slug,
            )

    def emit_significance_evaluated(self, payload: Any) -> None:
        del payload

    def emit_decision_timeout_expired(self, payload: Any) -> None:
        del payload

    def _enter_phase(self, step_id: str | None, actor_id: str) -> None:
        if not step_id:
            return
        if not self._started:
            if self._mission_id:
                self._emitter.emit_mission_started(
                    mission_id=self._mission_id,
                    mission_type=self._mission_type,
                    initial_phase="not_started",
                    actor=actor_id,
                    mission_slug=self._mission_slug,
                )
            self._started = True
            if self._current_phase is None:
                self._current_phase = "not_started"
        if self._mission_id and step_id != self._current_phase:
            self._emitter.emit_phase_entered(
                mission_id=self._mission_id,
                phase_name=step_id,
                previous_phase=self._current_phase,
                actor=actor_id,
                mission_slug=self._mission_slug,
            )
        self._current_phase = step_id

    @staticmethod
    def _actor_id(payload: Any) -> str:
        actor = getattr(payload, "actor", None)
        actor_id = getattr(actor, "actor_id", None)
        if isinstance(actor_id, str) and actor_id:
            return actor_id
        return "runtime"

    @staticmethod
    def _infer_phase_from_snapshot(snapshot: Any) -> str | None:
        issued_step_id = getattr(snapshot, "issued_step_id", None)
        if isinstance(issued_step_id, str) and issued_step_id:
            return issued_step_id

        pending_decisions = getattr(snapshot, "pending_decisions", None) or {}
        if isinstance(pending_decisions, dict):
            for decision in pending_decisions.values():
                if isinstance(decision, dict):
                    step_id = decision.get("step_id")
                    if isinstance(step_id, str) and step_id:
                        return step_id

        completed_steps = getattr(snapshot, "completed_steps", None) or []
        if isinstance(completed_steps, list) and completed_steps:
            last_step = completed_steps[-1]
            if isinstance(last_step, str) and last_step:
                return last_step

        if getattr(snapshot, "blocked_reason", None):
            return "blocked"

        return None

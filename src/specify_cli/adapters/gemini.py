"""Gemini adapter stub (S1/M1 baseline implementation)."""

import os
import re
from specify_cli.adapters.observe_decide import (
    ActorIdentity, ObservationSignal,
    DecisionRequestDraft, AdapterHealth
)
from specify_cli.events.ulid_utils import generate_event_id


class GeminiObserveDecideAdapter:
    """Gemini adapter stub (S1/M1 baseline implementation)."""

    def normalize_actor_identity(self, runtime_ctx: dict) -> ActorIdentity:
        """Extract actor identity from Gemini runtime context."""
        return ActorIdentity(
            agent_type="gemini",
            auth_principal=runtime_ctx.get("user_email", "unknown"),
            session_id=generate_event_id(),
        )

    def parse_observation(self, output: str | dict) -> list[ObservationSignal]:
        """Parse Gemini output (stub: basic text pattern matching)."""
        signals = []

        if isinstance(output, str):
            # Detect step_started
            if "Starting step" in output or "Begin execution" in output:
                step_match = re.search(r'step:(\d+)', output)
                if step_match:
                    signals.append(ObservationSignal(
                        signal_type="step_started",
                        entity_id=f"step:{step_match.group(1)}",
                        metadata={"source": "gemini_text_output"}
                    ))

            # Detect step_completed
            if "Completed step" in output or "Finished execution" in output:
                step_match = re.search(r'step:(\d+)', output)
                if step_match:
                    signals.append(ObservationSignal(
                        signal_type="step_completed",
                        entity_id=f"step:{step_match.group(1)}",
                        metadata={"source": "gemini_text_output"}
                    ))

        return signals

    def detect_decision_request(self, observation: ObservationSignal) -> DecisionRequestDraft | None:
        """Stub: Decision detection not implemented S1/M1."""
        return None

    def format_decision_answer(self, answer: str) -> str:
        """Format answer for Gemini (stub: JSON wrapper)."""
        import json
        return json.dumps({"decision": answer})

    def healthcheck(self) -> AdapterHealth:
        """Check Gemini API prerequisites."""
        api_key = os.getenv("GEMINI_API_KEY")

        if api_key:
            return AdapterHealth(status="ok", message="Gemini API key found")
        else:
            return AdapterHealth(status="unavailable", message="GEMINI_API_KEY not set")

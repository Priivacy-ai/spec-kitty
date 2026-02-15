"""Cursor adapter stub (S1/M1 baseline implementation)."""

import re
import shutil
from specify_cli.adapters.observe_decide import (
    ActorIdentity, ObservationSignal,
    DecisionRequestDraft, AdapterHealth
)
from specify_cli.events.ulid_utils import generate_event_id


class CursorObserveDecideAdapter:
    """Cursor adapter stub (S1/M1 baseline implementation)."""

    def normalize_actor_identity(self, runtime_ctx: dict) -> ActorIdentity:
        """Extract actor identity from Cursor runtime context."""
        return ActorIdentity(
            agent_type="cursor",
            auth_principal=runtime_ctx.get("user_email", "unknown"),
            session_id=generate_event_id(),
        )

    def parse_observation(self, output: str | dict) -> list[ObservationSignal]:
        """Parse Cursor markdown output (stub: basic text pattern matching)."""
        signals = []

        if isinstance(output, str):
            # Detect step_started (Cursor markdown format)
            if "## Starting" in output or "### Begin" in output:
                step_match = re.search(r'step:(\d+)', output)
                if step_match:
                    signals.append(ObservationSignal(
                        signal_type="step_started",
                        entity_id=f"step:{step_match.group(1)}",
                        metadata={"source": "cursor_markdown_output"}
                    ))

            # Detect step_completed
            if "## Completed" in output or "### Finished" in output:
                step_match = re.search(r'step:(\d+)', output)
                if step_match:
                    signals.append(ObservationSignal(
                        signal_type="step_completed",
                        entity_id=f"step:{step_match.group(1)}",
                        metadata={"source": "cursor_markdown_output"}
                    ))

        return signals

    def detect_decision_request(self, observation: ObservationSignal) -> DecisionRequestDraft | None:
        """Stub: Decision detection not implemented S1/M1."""
        return None

    def format_decision_answer(self, answer: str) -> str:
        """Format answer for Cursor (stub: markdown wrapper)."""
        return f"**Decision:** {answer}"

    def healthcheck(self) -> AdapterHealth:
        """Check Cursor CLI availability."""
        if shutil.which("cursor"):
            return AdapterHealth(status="ok", message="Cursor CLI found")
        else:
            return AdapterHealth(status="unavailable", message="Cursor CLI not in PATH")

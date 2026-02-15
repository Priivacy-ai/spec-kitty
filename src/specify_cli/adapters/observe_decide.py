"""ObserveDecideAdapter protocol for AI agent normalization."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ActorIdentity:
    """
    Adapter-normalized identity for agent/human actors.

    Used during join flow to normalize agent context. Not directly in events
    (events use SaaS-issued participant_id).
    """
    agent_type: str  # claude, gemini, cursor, human
    auth_principal: str  # User email or OAuth subject
    session_id: str  # CLI session ULID


@dataclass
class ObservationSignal:
    """
    Structured signal parsed from agent output.

    Signal types:
    - step_started: Agent began executing a step
    - step_completed: Agent finished executing a step
    - decision_requested: Agent asks for user decision
    - error_detected: Agent encountered error
    """
    signal_type: str  # step_started, step_completed, decision_requested, error_detected
    entity_id: str  # wp_id or step_id
    metadata: dict[str, Any]  # Provider-specific additional data


@dataclass
class DecisionRequestDraft:
    """
    Parsed decision request from agent output (optional for S1/M1).
    """
    question: str
    options: list[str]
    context: dict[str, Any]


@dataclass
class AdapterHealth:
    """
    Adapter health check result.
    """
    status: str  # ok, degraded, unavailable
    message: str


class ObserveDecideAdapter(Protocol):
    """
    Protocol for AI agent adapters (Gemini, Cursor, etc.).

    Adapters normalize agent-specific output into canonical collaboration events.

    S1/M1 Scope: Baseline stubs with tested parsing for common scenarios.
    Full production hardening continues post-S1/M1.

    Contract Ownership:
    - Feature 006: Event schemas/payloads
    - Feature 040: Adapter interface, implementations
    """

    def normalize_actor_identity(self, runtime_ctx: dict[str, Any]) -> ActorIdentity:
        """
        Extract actor identity from agent runtime context.

        Args:
            runtime_ctx: Provider-specific runtime context (e.g., user_email, session_token)

        Returns:
            ActorIdentity with agent_type, auth_principal, session_id
        """
        ...

    def parse_observation(self, output: str | dict[str, Any]) -> list[ObservationSignal]:
        """
        Parse agent output into structured observation signals.

        Args:
            output: Agent output (text or JSON)

        Returns:
            List of ObservationSignal (may be empty if no signals detected)
        """
        ...

    def detect_decision_request(self, observation: ObservationSignal) -> DecisionRequestDraft | None:
        """
        Check if observation contains decision request.

        Args:
            observation: Parsed observation signal

        Returns:
            DecisionRequestDraft if decision requested, else None
        """
        ...

    def format_decision_answer(self, answer: str) -> str:
        """
        Format decision answer for agent input (provider-specific formatting).

        Args:
            answer: Decision answer text

        Returns:
            Formatted string (e.g., Gemini JSON vs. Cursor markdown)
        """
        ...

    def healthcheck(self) -> AdapterHealth:
        """
        Check adapter prerequisites (API keys, network connectivity).

        Returns:
            AdapterHealth with status and message
        """
        ...

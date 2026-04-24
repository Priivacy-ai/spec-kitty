"""GitHub gate observability contracts for CI check_run events."""

import logging
from typing import Callable, Literal, Optional

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_serializer

from .models import SpecKittyEventsError

logger = logging.getLogger("spec_kitty_events.gates")


class GatePayloadBase(BaseModel):
    """Base payload for CI gate outcome events.

    Not intended to be instantiated directly — use GatePassedPayload
    or GateFailedPayload for type discrimination.
    """

    model_config = ConfigDict(frozen=True)

    gate_name: str = Field(
        ...,
        min_length=1,
        description="Name of the CI gate (e.g., 'ci/build', 'ci/lint')",
    )
    gate_type: Literal["ci"] = Field(
        ...,
        description="Type of gate. Currently only 'ci' is supported.",
    )
    conclusion: str = Field(
        ...,
        min_length=1,
        description="Raw conclusion string from the external provider",
    )
    external_provider: Literal["github"] = Field(
        ...,
        description="External CI provider. Currently only 'github' is supported.",
    )
    check_run_id: int = Field(
        ...,
        gt=0,
        strict=True,
        description="GitHub check run ID",
    )
    check_run_url: AnyHttpUrl = Field(
        ...,
        description="URL of the GitHub check run",
    )
    delivery_id: str = Field(
        ...,
        min_length=1,
        description="Webhook delivery ID used as idempotency key",
    )
    pr_number: Optional[int] = Field(
        None,
        gt=0,
        strict=True,
        description="Pull request number, if the gate is associated with a PR",
    )

    @field_serializer("check_run_url")
    @classmethod
    def serialize_url(cls, v: AnyHttpUrl) -> str:
        """Serialize AnyHttpUrl to plain string for round-trip compatibility."""
        return str(v)


class GatePassedPayload(GatePayloadBase):
    """Payload for a CI gate that concluded successfully.

    Attached to a generic Event with event_type='GatePassed'.
    """

    conclusion: Literal["success"] = Field(
        ...,
        description="Allowed GitHub check_run conclusion for passed gates.",
    )


class GateFailedPayload(GatePayloadBase):
    """Payload for a CI gate that concluded with a failure condition.

    Covers conclusions: failure, timed_out, cancelled, action_required.
    Attached to a generic Event with event_type='GateFailed'.
    """

    conclusion: Literal["failure", "timed_out", "cancelled", "action_required"] = Field(
        ...,
        description="Allowed GitHub check_run conclusions for failed gates.",
    )


class UnknownConclusionError(SpecKittyEventsError):
    """Raised when a check_run conclusion is not in the known set."""

    def __init__(self, conclusion: str) -> None:
        self.conclusion = conclusion
        super().__init__(
            f"Unknown check_run conclusion: {conclusion!r}. "
            f"Known values: success, failure, timed_out, cancelled, "
            f"action_required, neutral, skipped, stale"
        )


_GATE_PASSED = "GatePassed"
_GATE_FAILED = "GateFailed"

_CONCLUSION_MAP: dict[str, Optional[str]] = {
    "success": _GATE_PASSED,
    "failure": _GATE_FAILED,
    "timed_out": _GATE_FAILED,
    "cancelled": _GATE_FAILED,
    "action_required": _GATE_FAILED,
    "neutral": None,
    "skipped": None,
    "stale": None,
}

def map_check_run_conclusion(
    conclusion: str,
    on_ignored: Optional[Callable[[str, str], None]] = None,
) -> Optional[str]:
    """Map a GitHub check_run conclusion to an event type string.

    Args:
        conclusion: The raw conclusion string from GitHub's check_run API.
            Must be lowercase. GitHub always sends lowercase values;
            non-lowercase input is treated as unknown.
        on_ignored: Optional callback invoked when a conclusion is ignored.
            Receives (conclusion, reason) where reason is "non_blocking".

    Returns:
        "GatePassed" for success.
        "GateFailed" for failure, timed_out, cancelled, action_required.
        None for neutral, skipped, stale (ignored).

    Raises:
        UnknownConclusionError: If conclusion is not in the known set.
    """
    if conclusion not in _CONCLUSION_MAP:
        raise UnknownConclusionError(conclusion)

    event_type = _CONCLUSION_MAP[conclusion]

    if event_type is None:
        logger.info(
            "Ignored non-blocking check_run conclusion: %s", conclusion
        )
        if on_ignored is not None:
            on_ignored(conclusion, "non_blocking")

    return event_type

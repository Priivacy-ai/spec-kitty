"""Context contract and remediation payload structures."""

# Internalized from spec-kitty-runtime 0.4.3 as part of
# `shared-package-boundary-cutover-01KQ22DS` (mission). See
# `runtime-standalone-package-retirement-01KQ20Z8` for the upstream
# public-API inventory.
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RemediationPayload(BaseModel):
    """Structured error response for context resolution failures."""

    model_config = ConfigDict(frozen=True)

    error_code: Literal["CONTEXT_MISSING", "CONTEXT_AMBIGUOUS", "CONTEXT_INVALID"] = Field(
        ..., description="Type of context resolution failure"
    )
    context_name: str = Field(..., min_length=1, description="The context that failed")
    candidates: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Possible bindings, with sources and details"
    )
    remediation_hint: str = Field(
        ..., min_length=1,
        description="Exact suggested command/override to proceed"
    )
    resolver_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Debug info: resolver name, precedence position, validation rules"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When remediation was generated"
    )

    @staticmethod
    def missing(
        context_name: str,
        resolver_metadata: dict[str, Any] | None = None
    ) -> RemediationPayload:
        """Create a CONTEXT_MISSING remediation payload.

        Args:
            context_name: The context that could not be resolved
            resolver_metadata: Optional debug information
        """
        hint = f"Resolve missing context: --context={context_name} --source=<path-to-source>"
        return RemediationPayload(
            error_code="CONTEXT_MISSING",
            context_name=context_name,
            candidates=[],
            remediation_hint=hint,
            resolver_metadata=resolver_metadata or {}
        )

    @staticmethod
    def ambiguous(
        context_name: str,
        candidates: list[dict[str, Any]],
        resolver_metadata: dict[str, Any] | None = None
    ) -> RemediationPayload:
        """Create a CONTEXT_AMBIGUOUS remediation payload.

        Args:
            context_name: The context with multiple valid options
            candidates: List of equally valid binding options
            resolver_metadata: Optional debug information
        """
        # Build hint from available candidates
        if candidates:
            sources = [f"--context={context_name} --source={c.get('source', '?')}"
                       for c in candidates]
            hint = f"Select one: {' or '.join(sources)}"
        else:
            hint = f"Ambiguous context {context_name}: specify which source to use"

        return RemediationPayload(
            error_code="CONTEXT_AMBIGUOUS",
            context_name=context_name,
            candidates=candidates,
            remediation_hint=hint,
            resolver_metadata=resolver_metadata or {}
        )

    @staticmethod
    def invalid(
        context_name: str,
        candidates: list[dict[str, Any]],
        validation_failures: list[str] | None = None,
        resolver_metadata: dict[str, Any] | None = None
    ) -> RemediationPayload:
        """Create a CONTEXT_INVALID remediation payload.

        Args:
            context_name: The context that failed validation
            candidates: Binding options that all failed validation
            validation_failures: Human-readable validation error messages
            resolver_metadata: Optional debug information
        """
        failures = validation_failures or []
        if failures:
            hint = f"Context value must pass validation: {'; '.join(failures)}"
        else:
            hint = f"Context {context_name} failed validation against declared rules"

        return RemediationPayload(
            error_code="CONTEXT_INVALID",
            context_name=context_name,
            candidates=candidates,
            remediation_hint=hint,
            resolver_metadata=resolver_metadata or {}
        )

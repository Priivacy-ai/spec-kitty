"""Mission analytics event contracts.

Canonical analytics payloads used to build mission scorecards without
repo-local schema forks.
"""

from __future__ import annotations

from typing import FrozenSet, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .mission_next import RuntimeActorIdentity

TOKEN_USAGE_RECORDED: str = "TokenUsageRecorded"
DIFF_SUMMARY_RECORDED: str = "DiffSummaryRecorded"

ANALYTICS_EVENT_TYPES: FrozenSet[str] = frozenset({
    TOKEN_USAGE_RECORDED,
    DIFF_SUMMARY_RECORDED,
})


class TokenUsageRecordedPayload(BaseModel):
    """Canonical token and estimated-cost accounting payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1, description="Canonical mission identifier")
    run_id: Optional[str] = Field(None, min_length=1, description="Mission run identifier when available")
    step_id: Optional[str] = Field(None, min_length=1, description="Mission step identifier when available")
    wp_id: Optional[str] = Field(None, min_length=1, description="Work-package identifier when available")
    phase_name: Optional[str] = Field(None, min_length=1, description="Mission phase name when known")
    actor: Optional[RuntimeActorIdentity] = Field(
        None,
        description="Runtime actor identity when available",
    )
    provider: Optional[str] = Field(None, min_length=1, description="LLM provider when available")
    model: Optional[str] = Field(None, min_length=1, description="LLM model when available")
    input_tokens: int = Field(..., ge=0, description="Prompt/input token count")
    output_tokens: int = Field(..., ge=0, description="Completion/output token count")
    total_tokens: int = Field(..., ge=0, description="Total token count")
    estimated_cost_usd: float = Field(
        ...,
        ge=0,
        description="Estimated USD cost for the usage record",
    )
    source: str = Field(..., min_length=1, description="Usage data source identifier")

    @model_validator(mode="after")
    def _validate_totals(self) -> "TokenUsageRecordedPayload":
        expected_total = self.input_tokens + self.output_tokens
        if self.total_tokens != expected_total:
            raise ValueError(
                "total_tokens must equal input_tokens + output_tokens"
            )
        return self


class DiffSummaryRecordedPayload(BaseModel):
    """Canonical git diff summary payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1, description="Canonical mission identifier")
    run_id: Optional[str] = Field(None, min_length=1, description="Mission run identifier when available")
    step_id: Optional[str] = Field(None, min_length=1, description="Mission step identifier when available")
    wp_id: Optional[str] = Field(None, min_length=1, description="Work-package identifier when available")
    phase_name: Optional[str] = Field(None, min_length=1, description="Mission phase name when known")
    base_ref: str = Field(..., min_length=1, description="Diff base git ref or commit")
    head_ref: str = Field(..., min_length=1, description="Diff head git ref or commit")
    files_changed: int = Field(..., ge=0, description="Count of files changed in the diff")
    lines_added: int = Field(..., ge=0, description="Lines added in the diff")
    lines_deleted: int = Field(..., ge=0, description="Lines deleted in the diff")
    source: str = Field(..., min_length=1, description="Diff summary source identifier")

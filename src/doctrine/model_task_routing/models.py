"""Model-to-task_type schema models.

This module defines the Pydantic model that serves as the single source of
truth for ``model-to-task_type.schema.yaml``.  It describes a catalog of
LLM model capabilities, costs, and a routing policy for assigning models
to task types.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

TASK_TYPE_PATTERN = r"^[a-z][a-z0-9-]*$"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Sensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CostTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PREMIUM = "premium"


class LatencyTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RoutingObjective(StrEnum):
    QUALITY_FIRST = "quality_first"
    BALANCED = "balanced"
    COST_FIRST = "cost_first"


class OverrideMode(StrEnum):
    ADVISORY = "advisory"
    GATED = "gated"
    REQUIRED = "required"


class AccessMethod(StrEnum):
    API = "api"
    DATASET = "dataset"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class TaskType(BaseModel):
    """A task category that models can be scored against."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=TASK_TYPE_PATTERN)
    title: str
    description: str | None = None
    quality_sensitivity: Sensitivity | None = None
    cost_sensitivity: Sensitivity | None = None


class TaskFit(BaseModel):
    """How well a model fits a particular task type."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_type: str = Field(pattern=TASK_TYPE_PATTERN)
    score: float = Field(ge=0, le=1)
    confidence: Confidence | None = None
    rationale: str | None = None


class ModelCost(BaseModel):
    """Pricing information for a model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tier: CostTier
    input_per_1m_usd: float | None = Field(default=None, ge=0)
    output_per_1m_usd: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None)
    pricing_source_url: str | None = None


class ModelEntry(BaseModel):
    """A single model in the catalog."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    provider: str
    family: str | None = None
    tools: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    task_fit: list[TaskFit] = Field(min_length=1)
    cost: ModelCost
    latency_tier: LatencyTier | None = None


class RoutingWeights(BaseModel):
    """Weights for routing objective function."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    quality: float = Field(ge=0, le=1)
    cost: float = Field(ge=0, le=1)
    risk: float = Field(ge=0, le=1)
    latency: float = Field(ge=0, le=1)


class TierConstraint(BaseModel):
    """Maximum cost tier allowed for a task type."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_type: str = Field(pattern=TASK_TYPE_PATTERN)
    max_tier: CostTier


class OverridePolicy(BaseModel):
    """Policy for manual model overrides."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: OverrideMode
    require_reason: bool


class FreshnessPolicy(BaseModel):
    """How fresh the catalog must be."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_catalog_age_hours: int | None = Field(default=None, ge=1)


class RoutingPolicy(BaseModel):
    """Top-level routing configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    objective: RoutingObjective
    weights: RoutingWeights
    tier_constraints: list[TierConstraint] = Field(default_factory=list)
    override_policy: OverridePolicy
    freshness_policy: FreshnessPolicy | None = None


class DataSource(BaseModel):
    """A data source used to populate the catalog."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    url: str
    access_method: AccessMethod
    snapshot_at: str
    license_notes: str | None = None


# ---------------------------------------------------------------------------
# Top-level model
# ---------------------------------------------------------------------------


class ModelToTaskType(BaseModel):
    """Catalog of model capabilities, costs, and routing policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(pattern=r"^1\.0$")
    generated_at: str
    source_snapshot: str | None = None
    task_types: list[TaskType] = Field(min_length=1)
    models: list[ModelEntry] = Field(min_length=1)
    routing_policy: RoutingPolicy
    sources: list[DataSource] = Field(min_length=1)

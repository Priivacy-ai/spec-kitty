"""Shared Pydantic models used across multiple doctrine artifact types."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contradiction(BaseModel):
    """An anti-pattern or conflicting approach that opposes an artifact.

    Used by paradigms, directives, and tactics to declare explicit
    opposition to named anti-patterns or incompatible approaches.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["directive", "tactic", "paradigm"]
    id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


__all__ = ["Contradiction"]

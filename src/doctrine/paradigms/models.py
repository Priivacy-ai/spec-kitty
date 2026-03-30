"""Paradigm domain model."""

from pydantic import BaseModel, ConfigDict, Field

from doctrine.shared.models import Contradiction


class Paradigm(BaseModel):
    """A worldview-level framing that guides doctrine interpretation."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_version: str = Field(pattern=r"^1\.0$")
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    summary: str
    tactic_refs: list[str] = Field(default_factory=list)
    directive_refs: list[str] = Field(default_factory=list)
    opposed_by: list[Contradiction] = Field(default_factory=list)

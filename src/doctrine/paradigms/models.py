"""Paradigm domain model."""

from pydantic import BaseModel, ConfigDict, Field


class Paradigm(BaseModel):
    """A worldview-level framing that guides doctrine interpretation."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    schema_version: str = Field(pattern=r"^1\.0$")
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    summary: str


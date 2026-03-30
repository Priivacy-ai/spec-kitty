"""Toolguide domain model."""

from pydantic import BaseModel, ConfigDict, Field


class Toolguide(BaseModel):
    """A tool-specific governance guide."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    schema_version: str = Field(pattern=r"^1\.0$")
    tool: str
    title: str
    guide_path: str = Field(pattern=r"^src/doctrine/.+\.md$")
    summary: str
    commands: list[str] = Field(default_factory=list)

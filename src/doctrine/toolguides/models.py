"""Toolguide domain model."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _is_pack_relative_markdown_path(value: str) -> bool:
    if not value.endswith(".md"):
        return False
    if value.startswith(("/", "\\")):
        return False
    if "://" in value or re.match(r"^[A-Za-z]:", value):
        return False
    return ".." not in value.replace("\\", "/").split("/")


class Toolguide(BaseModel):
    """A tool-specific governance guide."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    schema_version: str = Field(pattern=r"^1\.0$")
    tool: str
    title: str
    guide_path: str
    summary: str
    commands: list[str] = Field(default_factory=list)
    applies_to_languages: list[str] = Field(default_factory=list)
    last_updated: str | None = None

    @field_validator("guide_path")
    @classmethod
    def validate_guide_path(cls, value: str) -> str:
        if not _is_pack_relative_markdown_path(value):
            raise ValueError("guide_path must be a pack-relative .md path")
        return value

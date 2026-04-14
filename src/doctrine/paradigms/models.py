"""Paradigm domain model.

Cross-artifact relationships (paradigm → tactic, paradigm → directive) live in
``src/doctrine/graph.yaml`` as of Phase 1 excision (mission
``excise-doctrine-curation-and-inline-references-01KP54J6`` WP02). Inline
``tactic_refs`` / ``paradigm_refs`` fields have been removed from this model.
"""

from pydantic import BaseModel, ConfigDict, Field

from doctrine.shared.models import Contradiction


class Paradigm(BaseModel):
    """A worldview-level framing that guides doctrine interpretation.

    Relationships to tactics and directives are expressed as typed edges in
    ``src/doctrine/graph.yaml`` rather than inline fields on this model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_version: str = Field(pattern=r"^1\.0$")
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    summary: str
    directive_refs: list[str] = Field(default_factory=list)
    opposed_by: list[Contradiction] = Field(default_factory=list)

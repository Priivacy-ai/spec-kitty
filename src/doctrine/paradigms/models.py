"""Paradigm domain model.

Cross-artifact relationships (paradigm → tactic, paradigm → directive) live in
``src/doctrine/graph.yaml`` as of Phase 1 excision (mission
``excise-doctrine-curation-and-inline-references-01KP54J6`` WP02). Inline
``tactic_refs`` / ``paradigm_refs`` fields have been removed from this model.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from doctrine.artifact_kinds import ArtifactKind
from doctrine.shared.models import Contradiction

_RETIRED_RELATIONSHIP_FIELDS = ("enhances", "overrides")


def _reject_retired_relationship_fields(kind: str, data: Any) -> Any:
    """Raise an actionable error if a retired relationship key is authored.

    The ``enhances``/``overrides`` fields were retired in the FR-028 hard
    cutover. Relationships are now authored exclusively as DRG fragment edges
    merged into ``src/doctrine/graph.yaml``, never as inline artifact fields.
    """
    if not isinstance(data, dict):
        return data
    present = [field for field in _RETIRED_RELATIONSHIP_FIELDS if field in data]
    if present:
        keys = ", ".join(repr(field) for field in present)
        raise ValueError(
            f"Retired relationship field(s) {keys} on {kind} are no longer "
            f"accepted (FR-028 hard cutover). Author the relationship as a DRG "
            f"fragment edge in a `drg/` fragment "
            f"(e.g. {{source: <kind>:<id>, target: <kind>:<id>, "
            f"relation: enhances|overrides}}) merged into "
            f"src/doctrine/graph.yaml — not as an inline artifact field."
        )
    return data


class ParadigmReference(BaseModel):
    """Typed cross-artifact reference from a paradigm.

    The sanctioned structured form (``{type, id}``) — distinct from the retired
    legacy ``tactic_refs`` / ``paradigm_refs`` inline-name fields excised in
    mission ``excise-doctrine-curation-and-inline-references-01KP54J6``. ``type``
    accepts the full :class:`ArtifactKind` vocabulary, so a paradigm may reference
    a tactic, procedure, agent profile, etc. The DRG extractor mints the
    corresponding ``paradigm -> <ref>`` edge at graph-generation time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: ArtifactKind
    id: str


class Paradigm(BaseModel):
    """A worldview-level framing that guides doctrine interpretation.

    Relationships to directives use the inline ``directive_refs`` list; richer
    cross-artifact relationships (paradigm -> tactic / procedure / agent_profile)
    use the structured ``references`` list. The retired legacy ``tactic_refs`` /
    ``paradigm_refs`` inline-name fields remain rejected (FR-028).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_version: str = Field(pattern=r"^1\.0$")
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    summary: str
    directive_refs: list[str] = Field(default_factory=list)
    references: list[ParadigmReference] = Field(default_factory=list)
    opposed_by: list[Contradiction] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _reject_retired_relationship_fields(cls, data: Any) -> Any:
        return _reject_retired_relationship_fields("paradigm", data)

"""Glossary pack domain model (FR-005, C-004).

Defines ``GlossaryTerm`` (a single canonical-term entity) and ``GlossaryPack``
(the aggregate root distributed as one ``*.glossary-pack.yaml`` file). The
term schema carries **every field the migration seed carries** — including
``see_also``, ``introduced_in_mission``, and ``synonyms_to_avoid`` beyond the
four obvious fields — so the Mission A migration off
``.kittify/glossaries/spec_kitty_core.yaml`` is provably zero-loss. The
``aliases`` / ``banned_synonyms`` enforcement fields are carried and
round-tripped for Mission B forward-compat but are inert (unwired) in
Mission A; see ``contracts/pack-schema.md`` §6.

No pack content and no gate wiring live here (WP03/WP04 own those).
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GlossaryTerm(BaseModel):
    """A single canonical-term entity within a :class:`GlossaryPack`.

    ``confidence`` is a float (seed values are 0.6/0.75/0.9/0.95/1.0) — never
    an enum or string. Optional list fields default to ``None`` (matching the
    runtime ``TermSense`` model), not ``[]``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    surface: str
    definition: str
    confidence: float
    status: str
    see_also: list[str] | None = None
    introduced_in_mission: str | None = None
    synonyms_to_avoid: list[str] | None = None
    aliases: list[str] | None = None
    banned_synonyms: list[str] | None = None


class GlossaryPack(BaseModel):
    """The aggregate root: a named, provenance-tagged collection of terms.

    Distributed as one ``*.glossary-pack.yaml`` file; loaded by
    ``GlossaryPackRepository``; addressable as a DRG node
    (``NodeKind.GLOSSARY_PACK``, URN ``glossary_pack:<id>``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    provenance: str
    terms: list[GlossaryTerm] = Field(min_length=1)
    description: str | None = None

    @model_validator(mode="after")
    def _validate_unique_surfaces(self) -> GlossaryPack:
        """Reject a pack whose terms do not have unique ``surface`` values.

        A pack with any invalid term (including a duplicate surface) is
        invalid as a whole (data-model.md invariant) — the doctor reports it
        unhealthy rather than silently loading a partial pack.
        """
        counts = Counter(term.surface for term in self.terms)
        duplicates = sorted(surface for surface, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(
                f"duplicate surface value(s) within glossary pack {self.id!r}: "
                f"{duplicates}. Each term's surface must be unique within the pack."
            )
        return self


__all__ = ["GlossaryPack", "GlossaryTerm"]

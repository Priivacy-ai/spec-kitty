"""Canonical enumeration of all doctrine artifact kinds.

Single source of truth for artifact type names, plural forms, and glob patterns.
Zero-dependency: no imports from specify_cli or other doctrine subpackages.

Canonical charter kind universe (R-009)
---------------------------------------
The charter command surfaces (``activate`` / ``deactivate`` / ``list`` /
``context --include``) operate over the *charter kind universe*, which is::

    the 9 activatable ``ArtifactKind`` kinds  +  ``mission-type``

``mission-type`` is **not** an :class:`ArtifactKind` member — it is a mission-tier
concept handled separately (see FR-032 / WP04). Callers route a mission-type
token explicitly; :meth:`ArtifactKind.from_operator_token` raises the distinct,
documented :class:`MissionTypeNotAnArtifactKind` for it rather than silently
mapping it to an artifact kind (R-009 / CL-1: no silent fallback).

``template`` *is* an :class:`ArtifactKind` member but is resolved specially
(mission-tier, empty glob — see :attr:`ArtifactKind.glob_pattern`); it is not one
of the 9 non-template artifact tokens enumerated in :data:`CHARTER_KIND_TOKENS`.

``anti_pattern`` *is* an :class:`ArtifactKind` member (mission
``doctrine-tension-edges-01KY1WPC``, D2) but is also excluded from the charter
kind universe via :data:`_NON_AUGMENTATION_ELIGIBLE_KINDS`: an anti-pattern
node is never activated as a live rule and is never hand-authored as a
standalone artifact file, so it is not one of the 9 charter-activatable
artifact tokens either.

Consumers must route every operator kind string through
:meth:`ArtifactKind.from_operator_token` (CC-4) — no second kind enumeration
may be re-declared elsewhere.
"""

from __future__ import annotations

from enum import StrEnum


class MissionTypeNotAnArtifactKind(ValueError):
    """Raised when ``mission-type`` is passed to :meth:`ArtifactKind.from_operator_token`.

    ``mission-type`` is part of the charter kind universe but is *not* an
    :class:`ArtifactKind` member. Callers must route it explicitly to the
    mission-tier handling path. This is a distinct, documented error (a
    :class:`ValueError` subclass) so callers can catch it specifically and
    branch, instead of treating mission-type as an unknown token.
    """

_PLURALS: dict[str, str] = {
    "directive": "directives",
    "tactic": "tactics",
    "styleguide": "styleguides",
    "toolguide": "toolguides",
    "paradigm": "paradigms",
    "procedure": "procedures",
    "agent_profile": "agent_profiles",
    "mission_step_contract": "mission_step_contracts",
    "template": "templates",
    "asset": "assets",
    "glossary_pack": "glossary_packs",
    "anti_pattern": "anti_patterns",
}

_PATTERNS: dict[str, str] = {
    "directive": "*.directive.yaml",
    "tactic": "*.tactic.yaml",
    "styleguide": "*.styleguide.yaml",
    "toolguide": "*.toolguide.yaml",
    "paradigm": "*.paradigm.yaml",
    "procedure": "*.procedure.yaml",
    "agent_profile": "*.agent.yaml",
    "mission_step_contract": "*.step-contract.yaml",
    "template": "",
    "asset": "*.asset.yaml",
    "glossary_pack": "*.glossary-pack.yaml",
    # anti_pattern nodes are hand-authored inside existing graph fragments
    # (re-kinded/tagged paradigm/tactic nodes, D2) -- there is no dedicated
    # `*.anti_pattern.yaml` artifact file convention. The pattern is declared
    # for consistency with every other ArtifactKind member (avoids a KeyError
    # in generic `for kind in ArtifactKind: kind.glob_pattern` consumers) but
    # is not expected to match any file on disk.
    "anti_pattern": "*.anti_pattern.yaml",
}

#: Operator token (hyphenated CLI surface) that callers must explicitly route to
#: the mission-tier path; it is part of the charter kind universe but not an
#: :class:`ArtifactKind` member. See :class:`MissionTypeNotAnArtifactKind`.
MISSION_TYPE_TOKEN = "mission-type"  # noqa: S105 - kind token, not a secret


class ArtifactKind(StrEnum):
    """All doctrine artifact types.

    String values are the canonical singular form stored in YAML ``type`` fields.
    Use :attr:`plural` for directory names and :attr:`glob_pattern` for file discovery.
    """

    DIRECTIVE = "directive"
    TACTIC = "tactic"
    STYLEGUIDE = "styleguide"
    TOOLGUIDE = "toolguide"
    PARADIGM = "paradigm"
    PROCEDURE = "procedure"
    AGENT_PROFILE = "agent_profile"
    MISSION_STEP_CONTRACT = "mission_step_contract"
    TEMPLATE = "template"
    ASSET = "asset"
    GLOSSARY_PACK = "glossary_pack"
    ANTI_PATTERN = "anti_pattern"

    @property
    def plural(self) -> str:
        """Plural directory name (e.g. ``"directives"``, ``"agent_profiles"``)."""
        return _PLURALS[self.value]

    @property
    def glob_pattern(self) -> str:
        """File glob pattern for this artifact type.

        Returns an empty string for ``TEMPLATE`` (no dedicated extension).
        """
        return _PATTERNS[self.value]

    @property
    def operator_token(self) -> str:
        """Hyphenated operator token for this kind (CLI surface, help text).

        Inverse of :meth:`from_operator_token`. The token is the canonical
        singular value with underscores replaced by hyphens
        (e.g. ``ArtifactKind.AGENT_PROFILE.operator_token == "agent-profile"``).
        """
        return self.value.replace("_", "-")

    @classmethod
    def from_plural(cls, plural: str) -> ArtifactKind:
        """Return the enum member matching a plural directory name.

        Raises :class:`KeyError` if *plural* is not a known plural form.
        """
        for member in cls:
            if member.plural == plural:
                return member
        raise KeyError(f"No ArtifactKind with plural {plural!r}")

    @classmethod
    def from_operator_token(cls, token: str) -> ArtifactKind:
        """Return the :class:`ArtifactKind` for a documented operator token.

        Normalizes the operator token (the hyphenated CLI surface form) to the
        canonical underscore singular and resolves it. Accepts both the
        hyphenated form (``agent-profile``) and the already-canonical underscore
        form (``agent_profile``); matching is case-insensitive.

        This is the **single** entry point charter surfaces use to turn a kind
        string into a canonical kind — no surface may re-declare the kind set
        (R-009 / CC-4).

        Args:
            token: Operator kind token, e.g. ``"agent-profile"``,
                ``"mission-step-contract"``, ``"directive"``.

        Returns:
            The matching :class:`ArtifactKind` member.

        Raises:
            MissionTypeNotAnArtifactKind: if *token* is ``"mission-type"``. This
                is part of the charter kind universe but is mission-tier, not an
                artifact kind — callers must route it explicitly.
            ValueError: if *token* is not a documented operator token. The error
                message lists the valid operator tokens (no silent fallback —
                R-009 / CL-1).
        """
        normalized = token.strip().lower().replace("-", "_")
        if normalized == MISSION_TYPE_TOKEN.replace("-", "_"):
            raise MissionTypeNotAnArtifactKind(
                "'mission-type' is part of the charter kind universe but is not "
                "an ArtifactKind; route it through the mission-tier handler."
            )
        for member in cls:
            if member.value == normalized:
                return member
        valid = ", ".join(member.operator_token for member in cls)
        raise ValueError(
            f"Unknown artifact kind token {token!r}. "
            f"Valid operator tokens: {valid}."
        )


#: Canonical set of :class:`ArtifactKind` members that are never eligible for
#: pack augmentation (``enhances``/``overrides``) or the charter kind universe.
#: ``TEMPLATE`` is mission-tier and resolves specially (empty glob); ``ASSET``
#: is a loose-contract kind excluded from the same surfaces (FR-005/FR-011).
#: ``ANTI_PATTERN`` (mission ``doctrine-tension-edges-01KY1WPC``, D2) is
#: excluded for the same reason: it is never activated as a live rule and is
#: never hand-authored as a standalone artifact file -- it is a re-kinded/
#: tagged node inside an existing graph fragment, referenced only via
#: ``rejects`` edges. This is the **single** canonical exclusion set —
#: downstream modules (``org_pack_loader.py``, the charter cascade) must
#: import this rather than re-declaring their own exclusion list.
_NON_AUGMENTATION_ELIGIBLE_KINDS: frozenset[ArtifactKind] = frozenset(
    {ArtifactKind.TEMPLATE, ArtifactKind.ASSET, ArtifactKind.ANTI_PATTERN}
)


#: Charter kind universe: the non-excluded artifact operator tokens + the
#: special ``mission-type`` token. Members of :data:`_NON_AUGMENTATION_ELIGIBLE_KINDS`
#: (``template``, ``asset``, ``anti_pattern``) resolve specially and are *not*
#: listed here.
CHARTER_KIND_TOKENS: tuple[str, ...] = tuple(
    member.operator_token
    for member in ArtifactKind
    if member not in _NON_AUGMENTATION_ELIGIBLE_KINDS
) + (MISSION_TYPE_TOKEN,)


__all__ = [
    "ArtifactKind",
    "CHARTER_KIND_TOKENS",
    "MISSION_TYPE_TOKEN",
    "MissionTypeNotAnArtifactKind",
]

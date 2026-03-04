"""Canonical enumeration of all doctrine artifact kinds.

Single source of truth for artifact type names, plural forms, and glob patterns.
Zero-dependency: no imports from specify_cli or other doctrine subpackages.
"""

from __future__ import annotations

from enum import StrEnum


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

    @property
    def plural(self) -> str:
        """Plural directory name (e.g. ``"directives"``, ``"agent_profiles"``)."""
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
        }
        return _PLURALS[self.value]

    @property
    def glob_pattern(self) -> str:
        """File glob pattern for this artifact type.

        Returns an empty string for ``TEMPLATE`` (no dedicated extension).
        """
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
        }
        return _PATTERNS[self.value]

    @classmethod
    def from_plural(cls, plural: str) -> ArtifactKind:
        """Return the enum member matching a plural directory name.

        Raises :class:`KeyError` if *plural* is not a known plural form.
        """
        for member in cls:
            if member.plural == plural:
                return member
        raise KeyError(f"No ArtifactKind with plural {plural!r}")


__all__ = ["ArtifactKind"]

"""Structured agent identity primitive for spec-kitty.

Provides the ``ActorIdentity`` frozen dataclass representing the 4-part
structured identity used across status events, frontmatter, and CLI flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import typer


_UNKNOWN = "unknown"
_FIELDS = ("tool", "model", "profile", "role")


@dataclass(frozen=True)
class ActorIdentity:
    """Structured 4-part agent identity.

    Format (compact): ``tool:model:profile:role``

    Fields default to ``"unknown"`` when not provided.  All four parts
    are always present in serialised form so readers never see missing keys.
    """

    tool: str
    model: str
    profile: str
    role: str

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serialisable dict with all four fields."""
        return {
            "tool": self.tool,
            "model": self.model,
            "profile": self.profile,
            "role": self.role,
        }

    def to_compact(self) -> str:
        """Return the compact ``tool:model:profile:role`` string."""
        return f"{self.tool}:{self.model}:{self.profile}:{self.role}"

    def __str__(self) -> str:
        """Return the tool name for backwards-compatible string contexts."""
        return self.tool

    # ------------------------------------------------------------------
    # Deserialisation
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActorIdentity:
        """Construct from a dict with any subset of the four fields."""
        return cls(
            tool=str(data.get("tool", _UNKNOWN)) or _UNKNOWN,
            model=str(data.get("model", _UNKNOWN)) or _UNKNOWN,
            profile=str(data.get("profile", _UNKNOWN)) or _UNKNOWN,
            role=str(data.get("role", _UNKNOWN)) or _UNKNOWN,
        )

    @classmethod
    def from_compact(cls, value: str) -> ActorIdentity:
        """Parse a colon-delimited compound string.

        Partial strings fill missing fields from the right with ``"unknown"``.
        Examples::

            from_compact("claude")           # tool=claude, rest=unknown
            from_compact("claude:opus")      # tool=claude, model=opus, rest=unknown
            from_compact("claude:opus:impl:impl")  # all four explicit
        """
        parts = value.split(":") if value else []
        # Pad to exactly 4 elements
        padded = parts[:4] + [_UNKNOWN] * max(0, 4 - len(parts))
        return cls(
            tool=padded[0] or _UNKNOWN,
            model=padded[1] or _UNKNOWN,
            profile=padded[2] or _UNKNOWN,
            role=padded[3] or _UNKNOWN,
        )

    @classmethod
    def from_legacy(cls, value: str) -> ActorIdentity:
        """Convert a bare legacy string (e.g. ``"claude"``) to ``ActorIdentity``.

        Delegates to :meth:`from_compact` so colon-delimited compound strings
        are also handled gracefully.
        """
        return cls.from_compact(value)


def parse_agent_identity(
    *,
    agent: str | None = None,
    tool: str | None = None,
    model: str | None = None,
    profile: str | None = None,
    role: str | None = None,
) -> ActorIdentity | None:
    """Parse agent identity from CLI flag combinations.

    Returns ``None`` when no identity flags are provided.

    Raises:
        typer.BadParameter: If both ``agent`` and any individual flag are provided.
    """
    individual = (tool, model, profile, role)
    has_individual = any(v is not None for v in individual)

    if agent is not None and has_individual:
        raise typer.BadParameter(
            "--agent is mutually exclusive with --tool / --model / --profile / --role"
        )

    if agent is not None:
        return ActorIdentity.from_compact(agent)

    if has_individual:
        return ActorIdentity(
            tool=tool or _UNKNOWN,
            model=model or _UNKNOWN,
            profile=profile or _UNKNOWN,
            role=role or _UNKNOWN,
        )

    return None


__all__ = [
    "ActorIdentity",
    "parse_agent_identity",
]

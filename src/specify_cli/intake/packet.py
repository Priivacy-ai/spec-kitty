"""Parse optional handoff-packet frontmatter from an intake brief.

A handoff packet is Markdown whose YAML frontmatter may declare
``handoff_packet: 1``. The prose body is always valid intake; structured
frontmatter is additive. Unknown or malformed packets degrade to prose
(return ``None``) instead of failing the command.

Contract: ``docs/contracts/handoff-packet-v1.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from specify_cli.intake.provenance import escape_for_comment

HANDOFF_PACKET_VERSION = 1

_FRONTMATTER_RE = re.compile(
    r"\A---\r?\n(?P<yaml>.*?)\r?\n---(?:\r?\n(?P<body>.*))?\Z",
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class HandoffPacket:
    """Validated v1 packet overlay. Body is the original Markdown including frontmatter."""

    source_tool: str | None
    source_mission: str | None
    source_ref: str | None
    requirement_count: int
    constraint_count: int
    requirement_ids: tuple[str, ...]
    body: str

    def sidecar_fields(self) -> dict[str, Any]:
        """Provenance fields for ``brief-source.yaml`` (already comment-escaped)."""
        fields: dict[str, Any] = {
            "packet_version": HANDOFF_PACKET_VERSION,
            "requirement_count": self.requirement_count,
            "constraint_count": self.constraint_count,
        }
        if self.source_tool:
            fields["source_tool"] = escape_for_comment(self.source_tool)
        if self.source_mission:
            fields["source_mission"] = escape_for_comment(self.source_mission)
        if self.source_ref:
            fields["source_ref"] = escape_for_comment(self.source_ref)
        if self.requirement_ids:
            fields["requirement_ids"] = [
                escape_for_comment(rid) for rid in self.requirement_ids
            ]
        return fields


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def parse_handoff_packet(content: str) -> HandoffPacket | None:
    """Return a v1 packet when frontmatter is valid; otherwise ``None`` (prose).

    Never raises for malformed YAML, unknown versions, or missing fields —
    those degrade to prose intake.
    """
    if not content:
        return None
    match = _FRONTMATTER_RE.match(content)
    if match is None:
        return None
    try:
        loaded = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError:
        return None
    if not isinstance(loaded, dict):
        return None
    version = loaded.get("handoff_packet")
    if version != HANDOFF_PACKET_VERSION:
        return None
    requirements = loaded.get("requirements")
    if not isinstance(requirements, list):
        return None
    ids: list[str] = []
    for item in requirements:
        if not isinstance(item, dict):
            return None
        req_id = item.get("id")
        statement = item.get("statement")
        if not isinstance(req_id, str) or not req_id.strip():
            return None
        if not isinstance(statement, str) or not statement.strip():
            return None
        ids.append(req_id.strip())
    constraints = loaded.get("constraints")
    if constraints is None:
        constraint_count = 0
    elif isinstance(constraints, list):
        constraint_count = len(constraints)
    else:
        return None
    return HandoffPacket(
        source_tool=_optional_str(loaded.get("source_tool")),
        source_mission=_optional_str(loaded.get("source_mission")),
        source_ref=_optional_str(loaded.get("source_ref")),
        requirement_count=len(ids),
        constraint_count=constraint_count,
        requirement_ids=tuple(ids),
        body=content,
    )


__all__ = [
    "HANDOFF_PACKET_VERSION",
    "HandoffPacket",
    "parse_handoff_packet",
]

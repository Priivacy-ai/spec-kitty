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

# This regex — not ``specify_cli.frontmatter.FrontmatterManager`` — does the
# frontmatter split here deliberately. ``FrontmatterManager`` operates on a
# file path and raises ``FrontmatterError`` on malformed input; this module
# operates on an in-memory string handed to us by the caller and must NEVER
# raise — every malformed shape degrades to prose (``return None``), per the
# module docstring. Consequently we also do not share ``FrontmatterManager``'s
# ``allow_duplicate_keys=False`` posture: a duplicate-key packet here simply
# fails ``yaml.safe_load``'s last-key-wins parse or trips a downstream
# validation check and degrades to prose, which is an acceptable outcome for
# an optional, best-effort overlay.
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


def _acceptance_criteria_valid(value: object) -> bool:
    """Return ``True`` when ``value`` is absent or a well-formed AC list.

    Absent ``acceptance_criteria`` is fine (it's optional). When present,
    each item must be a dict with a non-empty string ``id`` and a
    non-empty string ``statement`` — the contract's "adopted verbatim"
    promise (handoff-packet-v1.md degradation table, malformed-AC row)
    only holds if the ids are actually validated, not just counted.
    """
    if value is None:
        return True
    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, dict):
            return False
        ac_id = item.get("id")
        ac_statement = item.get("statement")
        if not isinstance(ac_id, str) or not ac_id.strip():
            return False
        if not isinstance(ac_statement, str) or not ac_statement.strip():
            return False
    return True


def _valid_constraint_count(value: object) -> int | None:
    """Return the count of well-formed constraints, or ``None`` if malformed.

    Absent ``constraints`` is fine (count 0). When present, every item
    must be a dict with a non-empty string ``id``; a malformed item
    degrades the whole packet to prose rather than silently inflating
    ``constraint_count`` via a bare ``len()``.
    """
    if value is None:
        return 0
    if not isinstance(value, list):
        return None
    for item in value:
        if not isinstance(item, dict):
            return None
        constraint_id = item.get("id")
        if not isinstance(constraint_id, str) or not constraint_id.strip():
            return None
    return len(value)


def parse_handoff_packet(content: str) -> HandoffPacket | None:
    """Return a v1 packet when frontmatter is valid; otherwise ``None`` (prose).

    Never raises for malformed YAML, unknown versions, or missing fields —
    those degrade to prose intake.
    """
    if not content:
        return None
    # A leading UTF-8 BOM defeats the ``\A---`` anchor below and would
    # silently degrade a real packet to prose. Strip a single leading BOM
    # from the parse view only; ``content`` itself (and thus the raw
    # SHA-256 brief hash computed by callers over the untouched string) is
    # never mutated.
    view = content.removeprefix("\ufeff")
    match = _FRONTMATTER_RE.match(view)
    if match is None:
        return None
    try:
        loaded = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError:
        return None
    if not isinstance(loaded, dict):
        return None
    version = loaded.get("handoff_packet")
    # ``True == 1`` and ``1.0 == 1`` in Python, so a bare ``!=`` check would
    # accept ``handoff_packet: true`` or ``handoff_packet: 1.0``. Only the
    # literal int ``1`` is a valid v1 packet.
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version != HANDOFF_PACKET_VERSION
    ):
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
        if not _acceptance_criteria_valid(item.get("acceptance_criteria")):
            return None
        ids.append(req_id.strip())
    constraint_count = _valid_constraint_count(loaded.get("constraints"))
    if constraint_count is None:
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

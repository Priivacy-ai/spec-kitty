"""ADR header converter (Mission B WP05 — IC-04a tooling slice).

Turns a legacy-header ADR into a bare-``status`` YAML-frontmatter ADR. Three
header dialects exist in the live tree (census: 70 bold-inline / 46 table /
1 dash-bullet = 117), so this module ships **three header parsers**:

* :func:`parse_table_header`      — ``| Status | Accepted |`` markdown-table rows
* :func:`parse_bold_inline_header` — ``**Status:** Accepted`` bold-inline fields
* :func:`parse_dash_bullet_header` — ``- Status: Accepted`` dash bullets

plus a frontmatter emitter (:func:`render_frontmatter`) and a **content-invariance
check** (:func:`invariant`) that proves the conversion changes only the *header
format*, never the decision body (C-002 / NFR-001).

The invariance check is **false-green-proof**: it strips the pre-image header via
the three parsers and the post-image frontmatter by *reusing*
:func:`scripts.docs._inventory.parse_frontmatter` (never a forked frontmatter
parser), then asserts **raw-byte** body identity — not a re-render, which would
silently pass on whitespace normalisation and miss a real edit.

This module is the *tool*. The execution over all 117 ADRs is WP06; this WP only
builds the tool and proves it on representative fixtures of all three dialects.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Final

from ruamel.yaml import YAML

# ``scripts.docs`` is a namespace-package module; when this file is imported as
# a bare script (``python scripts/docs/adr_converter.py``) the repo root is not
# on ``sys.path``. Anchor it so the shared frontmatter extractor resolves to the
# canonical inventory parser rather than a forked copy — mirrors the bootstrap
# used by ``scripts/docs/anti_sprawl_ratchet.py``.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs._inventory import (  # noqa: E402  (sys.path bootstrap above)
    parse_frontmatter,
)

__all__ = [
    "MADR_STATUSES",
    "AdrParseError",
    "ParsedHeader",
    "body_minus_frontmatter",
    "body_minus_header",
    "convert",
    "invariant",
    "parse_bold_inline_header",
    "parse_dash_bullet_header",
    "parse_header",
    "parse_table_header",
    "render_frontmatter",
]

#: MADR decision-status vocabulary. The frontmatter ``status`` key is the
#: *sanctioned* bare-``status`` exception (pages use ``doc_status``; ADRs use
#: bare ``status``). Lookup is case-insensitive; the emitted value is canonical.
MADR_STATUSES: Final[dict[str, str]] = {
    "proposed": "Proposed",
    "accepted": "Accepted",
    "deprecated": "Deprecated",
    "superseded": "Superseded",
}

_FRONTMATTER_FENCE: Final[str] = "---"
_TITLE_RE: Final[re.Pattern[str]] = re.compile(r"^#\s+(.+?)\s*$")
_TABLE_ROW_RE: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$"
)
_BOLD_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"^\*\*\s*([^*:]+?)\s*:\s*\*\*\s*(.*?)\s*$"
)
_DASH_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"^-\s+([^:]+?):\s*(.*?)\s*$"
)

# A field-line matcher returns ``(key, value)`` or ``None`` for a non-field line.
_FieldMatch = Callable[[str], "tuple[str, str] | None"]


class AdrParseError(ValueError):
    """Raised when an ADR header cannot be parsed into a complete schema.

    A status-less, date-less, or title-less header surfaces this error rather
    than emitting a silent status-less frontmatter block (which the anti-sprawl
    ratchet would then block on).
    """


@dataclass(frozen=True, slots=True)
class ParsedHeader:
    """A parsed ADR header plus the verbatim decision body that follows it.

    ``body`` is the raw byte-faithful remainder of the document with the title
    line and the entire (dialect-specific) header block removed. It is the unit
    the content-invariance check guards.
    """

    title: str
    status: str
    date: str
    body: str
    fields: dict[str, str] = field(default_factory=dict)


def _match_table_row(line: str) -> tuple[str, str] | None:
    match = _TABLE_ROW_RE.match(line)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _match_bold_field(line: str) -> tuple[str, str] | None:
    match = _BOLD_FIELD_RE.match(line)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _match_dash_field(line: str) -> tuple[str, str] | None:
    match = _DASH_FIELD_RE.match(line)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _find_title(lines: list[str]) -> tuple[str, int]:
    """Return ``(title, index)`` of the first ``# `` heading line."""
    for index, raw in enumerate(lines):
        match = _TITLE_RE.match(raw.rstrip("\n"))
        if match is not None:
            return match.group(1), index
    raise AdrParseError("ADR has no '# ' title heading line")


def _consume_header(
    lines: list[str], start: int, match_field: _FieldMatch
) -> tuple[dict[str, str], int]:
    """Collect header fields and return ``(fields, body_start_index)``.

    Consumes — as header decoration — blank lines, a lone ``---`` thematic
    break, and dialect field lines, stopping at the first content line. That
    stop point is the body boundary: for the dash-bullet dialect it is the first
    non-bullet, non-blank line after the top bullets (bullets *inside the body*,
    which follow a heading, are never reached).
    """
    fields: dict[str, str] = {}
    index = start
    while index < len(lines):
        stripped = lines[index].rstrip("\n").strip()
        if stripped == "" or stripped == _FRONTMATTER_FENCE:
            index += 1
            continue
        matched = match_field(lines[index].rstrip("\n"))
        if matched is None:
            break
        key, value = matched
        fields.setdefault(key.strip().lower(), value.strip())
        index += 1
    return fields, index


def _canonical_status(raw: str) -> str:
    canonical = MADR_STATUSES.get(raw.strip().lower())
    if canonical is None:
        raise AdrParseError(
            f"status {raw!r} is not MADR vocabulary "
            f"({'/'.join(MADR_STATUSES.values())})"
        )
    return canonical


def _build_header(
    lines: list[str], match_field: _FieldMatch
) -> ParsedHeader:
    """Shared parse driver: title → fields → body for any dialect."""
    title, title_index = _find_title(lines)
    fields, body_index = _consume_header(lines, title_index + 1, match_field)

    if "status" not in fields:
        raise AdrParseError("ADR header is missing a 'Status' field")
    if "date" not in fields:
        raise AdrParseError("ADR header is missing a 'Date' field")

    body = "".join(lines[body_index:]).lstrip("\n")
    return ParsedHeader(
        title=title,
        status=_canonical_status(fields["status"]),
        date=fields["date"],
        body=body,
        fields=fields,
    )


def parse_table_header(text: str) -> ParsedHeader:
    """Parse the markdown-table dialect (``| Status | Accepted |``). 46 ADRs."""
    return _build_header(text.splitlines(keepends=True), _match_table_row)


def parse_bold_inline_header(text: str) -> ParsedHeader:
    """Parse the bold-inline dialect (``**Status:** Accepted``). 70 ADRs."""
    return _build_header(text.splitlines(keepends=True), _match_bold_field)


def parse_dash_bullet_header(text: str) -> ParsedHeader:
    """Parse the dash-bullet dialect (``- Status: Accepted``). 1 ADR.

    This is the dialect the spec missed; without it that ADR converts
    status-less and the frontmatter ratchet blocks the whole conversion.
    """
    return _build_header(text.splitlines(keepends=True), _match_dash_field)


def _detect_parser(text: str) -> _FieldMatch:
    """Pick the dialect by how the ``Status`` line is written at the top."""
    for raw in text.splitlines():
        stripped = raw.strip()
        if _TABLE_ROW_RE.match(stripped) and "status" in stripped.lower():
            return _match_table_row
        if stripped.lower().startswith("**status"):
            return _match_bold_field
        if stripped.lower().startswith("- status"):
            return _match_dash_field
    raise AdrParseError("ADR has no recognisable 'Status' header line")


def parse_header(text: str) -> ParsedHeader:
    """Auto-detect the dialect and parse the header."""
    return _build_header(text.splitlines(keepends=True), _detect_parser(text))


def render_frontmatter(header: ParsedHeader) -> str:
    """Emit a bare-``status`` YAML frontmatter block (``title``/``status``/``date``).

    Uses ``ruamel.yaml`` (already vendored — no new dependency). Emits **bare**
    ``status`` carrying MADR vocabulary, never ``doc_status`` (that key is for
    pages). Key order is title → status → date.
    """
    yaml = YAML()
    yaml.default_flow_style = False
    payload = {
        "title": header.title,
        "status": header.status,
        "date": header.date,
    }
    buffer = StringIO()
    yaml.dump(payload, buffer)
    return f"{_FRONTMATTER_FENCE}\n{buffer.getvalue()}{_FRONTMATTER_FENCE}\n"


def convert(text: str) -> str:
    """Convert a legacy-header ADR to bare-``status`` frontmatter form.

    The decision body is preserved **verbatim** after the frontmatter block.
    """
    header = parse_header(text)
    return f"{render_frontmatter(header)}\n{header.body}"


def body_minus_header(text: str) -> str:
    """Pre-image body: strip the legacy header + title line (via the 3 parsers)."""
    return parse_header(text).body


def body_minus_frontmatter(text: str) -> str:
    """Post-image body: strip the YAML frontmatter, reusing the inventory parser.

    The *judgment* of what a frontmatter block is comes from
    :func:`scripts.docs._inventory.parse_frontmatter` (the canonical extractor
    every docs ruler shares). Only when that parser confirms a non-empty block
    do we slice the verbatim body off after the closing fence.
    """
    if not parse_frontmatter(text):
        raise AdrParseError("post-image has no parseable YAML frontmatter")

    lines = text.splitlines(keepends=True)
    for index in range(1, len(lines)):
        if lines[index].rstrip("\n").strip() == _FRONTMATTER_FENCE:
            return "".join(lines[index + 1 :]).lstrip("\n")
    raise AdrParseError("post-image frontmatter has no closing fence")


def invariant(pre: str, post: str) -> bool:
    """Return ``True`` iff the decision body is **byte-identical** pre/post.

    ``pre`` is the legacy-header ADR; ``post`` is its converted form. Any change
    to a single body byte — i.e. an actual decision-content mutation — makes this
    return ``False`` (the false-green-proof property).
    """
    return body_minus_header(pre) == body_minus_frontmatter(post)

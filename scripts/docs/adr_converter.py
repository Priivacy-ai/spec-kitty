"""ADR header converter (Mission B WP05 — IC-04a tooling slice).

Turns a legacy-header ADR into a bare-``status`` YAML-frontmatter ADR. **Five**
header dialects exist in the live 117-ADR tree (the cycle-2 census saw only
three; real-data execution — WP06 — surfaced two more), covered by the dialect
matchers:

* :func:`parse_table_header`      — ``| Status | Accepted |`` markdown-table rows
* :func:`parse_bold_inline_header` — ``**Status:** Accepted`` (colon INSIDE bold)
  **and** ``**Status**: Accepted`` (colon OUTSIDE bold — 26 real ADRs, cycle 3)
* :func:`parse_dash_bullet_header` — ``- Status: Accepted`` dash bullets **and**
  ``- **Status:** Accepted`` (dash+bold hybrid — 1 real ADR, cycle 3)

The two cycle-3 dialects are added as **extra branches inside the existing field
matchers** (``_match_bold_field`` / ``_match_dash_field``), so a single dialect
parser handles both spellings of its family.

On top of the dialects, cycle 3 adds two emitter-side resolution rules forced by
the live data:

* a **status-normalization alias table** (:data:`STATUS_ALIASES` +
  :func:`_status_root`) that maps qualified MADR values
  (``Accepted (amended …)``, ``Proposed — awaiting … review``) onto their MADR
  root, with two **operator-adjudicated** entries (``Amended — … superseded …``
  and ``Partially superseded`` → ``Superseded``). The alias only sets the
  frontmatter ``status``; the qualifier prose is preserved verbatim in the body
  (C-002). Anything neither MADR nor an explicit alias still hard-errors.
* a **Date-from-filename fallback** (:func:`_date_from_filename`) for the two
  era-less files whose ``**Date:**`` header sits after a revision-log block (so
  field consumption stops before reaching it) and the one file with no ``Date``
  header at all (a ``<DATE> (to be filled)`` body placeholder). A real ``Date``
  header always wins; the filename prefix is only the fallback.

plus a frontmatter emitter (:func:`render_frontmatter`) and a **content-invariance
check** (:func:`invariant`) that proves the conversion changes only the *header
format*, never the decision body (C-002 / NFR-001).

The invariance check is **false-green-proof**: it strips the pre-image header via
the dialect parsers and the post-image frontmatter by *reusing*
:func:`scripts.docs._inventory.parse_frontmatter` (never a forked frontmatter
parser), then asserts **raw-byte** body identity — not a re-render, which would
silently pass on whitespace normalisation and miss a real edit.

This module is the *tool*. The execution over all 117 ADRs is WP06; this WP only
builds the tool and proves it on representative fixtures of all five dialects.
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
    "STATUS_ALIASES",
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

#: Operator-adjudicated status aliases (Mission B WP05 cycle 3).
#:
#: Most non-canonical live status values are an MADR word qualified by an
#: editorial note — ``Accepted (amended 2026-02-18)``, ``Accepted (design) — …``,
#: ``Accepted (DELETE recommended; deferred…)``, ``Accepted — implemented by
#: mission …``, ``Proposed (mission …)``, ``Proposed — awaiting … review …``.
#: :func:`_status_root` strips the parenthetical / em-dash qualifier and recovers
#: the MADR root for those, so they need **no** entry here (the WP05 cycle-3
#: review sanctioned that derivation: the qualifier is editorial, the leading
#: MADR word is the decision).
#:
#: This table is ONLY for live values whose stripped root is *not* an MADR word
#: and therefore demands an EXPLICIT, reviewed decision — never a silent guess.
#: It is keyed by the lowercase stripped root. Anything covered by neither
#: :data:`MADR_STATUSES` nor this table still hard-errors (fail-closed).
#:
#: In every case the alias only sets the frontmatter ``status``; the original
#: qualifier prose ("amended", "partially") is preserved verbatim in the body
#: (C-002), so no nuance is lost.
STATUS_ALIASES: Final[dict[str, str]] = {
    # "Amended — the original <decision> is superseded by <new>": an amendment
    # that supersedes the prior decision → the MADR terminal state is Superseded.
    # (operator-adjudicated; the "amended" provenance stays verbatim in the body.)
    "amended": "Superseded",
    # "Partially superseded": MADR has no "partial" state. The decision IS
    # superseded; the partial-scope nuance stays verbatim in the body.
    # (operator-adjudicated.)
    "partially superseded": "Superseded",
}

_FRONTMATTER_FENCE: Final[str] = "---"
_TITLE_RE: Final[re.Pattern[str]] = re.compile(r"^#\s+(.+?)\s*$")
_TABLE_ROW_RE: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$"
)
# Bold-inline field, colon INSIDE the bold span: ``**Status:** Accepted``.
_BOLD_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"^\*\*\s*([^*:]+?)\s*:\s*\*\*\s*(.*?)\s*$"
)
# Bold field, colon OUTSIDE the bold span: ``**Status**: Accepted`` (26 ADRs).
_BOLD_OUTSIDE_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"^\*\*\s*([^*:]+?)\s*\*\*\s*:\s*(.*?)\s*$"
)
_DASH_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"^-\s+([^:]+?):\s*(.*?)\s*$"
)
# Dash+bold hybrid: ``- **Status:** Accepted`` (1 ADR — monorepo charter scope).
_DASH_BOLD_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"^-\s+\*\*\s*([^*:]+?)\s*:\s*\*\*\s*(.*?)\s*$"
)
# Leading ``YYYY-MM-DD`` date prefix of an ADR filename (the Date fallback).
_FILENAME_DATE_RE: Final[re.Pattern[str]] = re.compile(r"(\d{4}-\d{2}-\d{2})")

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
    """Match a bold field in either spelling: colon inside OR outside the bold.

    ``**Status:** Accepted`` (cycle-2) and ``**Status**: Accepted`` (cycle-3,
    26 real ADRs) are the same field family; both are header fields here.
    """
    match = _BOLD_FIELD_RE.match(line) or _BOLD_OUTSIDE_FIELD_RE.match(line)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _match_dash_field(line: str) -> tuple[str, str] | None:
    """Match a dash field in either spelling: plain OR dash+bold hybrid.

    ``- Status: Accepted`` (cycle-2) and ``- **Status:** Accepted`` (cycle-3,
    1 real ADR). The dash+bold regex is tried first because the plain regex
    would otherwise capture ``**Status`` as the key.
    """
    match = _DASH_BOLD_FIELD_RE.match(line) or _DASH_FIELD_RE.match(line)
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


def _status_root(raw: str) -> str:
    """Recover the MADR root by stripping editorial qualifiers.

    Removes a leading/trailing bold marker, an em-dash / en-dash qualifier tail
    (``Accepted — implemented by mission …`` → ``Accepted``), then a trailing
    parenthetical note (``Proposed (mission …)`` → ``Proposed``). The em-dash is
    split first so a parenthetical *inside* the qualifier
    (``Proposed — awaiting … (revision 2: …)``) does not leak in. The stripped
    qualifier text is preserved verbatim in the body (C-002); only the
    frontmatter ``status`` value is affected.
    """
    value = raw.strip().strip("*").strip()
    value = re.split(r"\s+[—–]\s+", value, maxsplit=1)[0]
    value = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()
    return value


def _canonical_status(raw: str) -> str:
    root = _status_root(raw)
    canonical = MADR_STATUSES.get(root.lower())
    if canonical is not None:
        return canonical
    aliased = STATUS_ALIASES.get(root.lower())
    if aliased is not None:
        return aliased
    raise AdrParseError(
        f"status {raw!r} (root {root!r}) is not MADR vocabulary "
        f"({'/'.join(MADR_STATUSES.values())}) nor a reviewed alias"
    )


def _date_from_filename(filename: str | None) -> str | None:
    """Derive an ISO date from an ADR filename's ``YYYY-MM-DD`` prefix.

    ADR files are named ``YYYY-MM-DD-<n>-<slug>.md``. Used ONLY as a fallback
    when the ``**Date:**`` header is broken (it sits after a revision-log block,
    so field consumption stops before reaching it) or absent (a
    ``<DATE> (to be filled)`` body placeholder). A real ``Date`` header always
    wins. Returns ``None`` when no filename is supplied or it carries no date
    prefix.
    """
    if filename is None:
        return None
    match = _FILENAME_DATE_RE.search(Path(filename).name)
    return match.group(1) if match else None


def _build_header(
    lines: list[str], match_field: _FieldMatch, filename: str | None = None
) -> ParsedHeader:
    """Shared parse driver: title → fields → body for any dialect.

    ``filename`` (when given) feeds the Date-from-filename fallback for headers
    whose ``Date`` field is broken or absent.
    """
    title, title_index = _find_title(lines)
    fields, body_index = _consume_header(lines, title_index + 1, match_field)

    if "status" not in fields:
        raise AdrParseError("ADR header is missing a 'Status' field")
    date = fields.get("date") or _date_from_filename(filename)
    if date is None:
        raise AdrParseError(
            "ADR header is missing a 'Date' field and no filename date prefix "
            "is available as a fallback"
        )

    body = "".join(lines[body_index:]).lstrip("\n")
    return ParsedHeader(
        title=title,
        status=_canonical_status(fields["status"]),
        date=date,
        body=body,
        fields=fields,
    )


def parse_table_header(text: str, filename: str | None = None) -> ParsedHeader:
    """Parse the markdown-table dialect (``| Status | Accepted |``). 46 ADRs."""
    return _build_header(text.splitlines(keepends=True), _match_table_row, filename)


def parse_bold_inline_header(text: str, filename: str | None = None) -> ParsedHeader:
    """Parse the bold dialect — colon inside (``**Status:**``) or outside
    (``**Status**:``) the bold span. 70 + 26 ADRs."""
    return _build_header(text.splitlines(keepends=True), _match_bold_field, filename)


def parse_dash_bullet_header(text: str, filename: str | None = None) -> ParsedHeader:
    """Parse the dash dialect — plain (``- Status: …``) or dash+bold hybrid
    (``- **Status:** …``). 1 + 1 ADRs.

    The plain form is the dialect the cycle-2 spec missed; the dash+bold hybrid
    is the cycle-3 addition. Without them those ADRs convert status-less and the
    frontmatter ratchet blocks the whole conversion.
    """
    return _build_header(text.splitlines(keepends=True), _match_dash_field, filename)


def _detect_parser(text: str) -> _FieldMatch:
    """Pick the dialect by how the ``Status`` line is written at the top."""
    for raw in text.splitlines():
        stripped = raw.strip()
        low = stripped.lower()
        if _TABLE_ROW_RE.match(stripped) and "status" in low:
            return _match_table_row
        if low.startswith("**status"):
            return _match_bold_field
        if low.startswith("- status") or low.startswith("- **status"):
            return _match_dash_field
    raise AdrParseError("ADR has no recognisable 'Status' header line")


def parse_header(text: str, filename: str | None = None) -> ParsedHeader:
    """Auto-detect the dialect and parse the header."""
    return _build_header(
        text.splitlines(keepends=True), _detect_parser(text), filename
    )


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


def convert(text: str, filename: str | None = None) -> str:
    """Convert a legacy-header ADR to bare-``status`` frontmatter form.

    The decision body is preserved **verbatim** after the frontmatter block.
    ``filename`` (when given) enables the Date-from-filename fallback for the
    few ADRs whose ``Date`` header is broken or absent.
    """
    header = parse_header(text, filename)
    return f"{render_frontmatter(header)}\n{header.body}"


def body_minus_header(text: str, filename: str | None = None) -> str:
    """Pre-image body: strip the legacy header + title line (via the parsers)."""
    return parse_header(text, filename).body


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


def invariant(pre: str, post: str, filename: str | None = None) -> bool:
    """Return ``True`` iff the decision body is **byte-identical** pre/post.

    ``pre`` is the legacy-header ADR; ``post`` is its converted form. Any change
    to a single body byte — i.e. an actual decision-content mutation — makes this
    return ``False`` (the false-green-proof property). ``filename`` is threaded to
    the pre-image parse so a broken/absent-Date ADR can still be stripped.
    """
    return body_minus_header(pre, filename) == body_minus_frontmatter(post)

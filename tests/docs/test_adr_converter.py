"""Tests for the ADR header converter (Mission B WP05).

Proves the three header parsers (markdown-table, bold-inline, dash-bullet) each
extract ``title``/``status``/``date`` and leave the decision body verbatim, that
the emitter writes **bare** ``status`` (MADR vocabulary, never ``doc_status``),
and that the content-invariance check is **false-green-proof**: a one-byte body
mutation drives it RED.

Fixtures are realistic ADR-shaped documents with real dated filenames and real
header bytes. The dash-bullet fixture is shaped from the canonical real file
``architecture/3.x/adr/2026-04-15-2-explicit-empty-charter-selections-remain-empty.md``
(the ``2.x/adr/`` path is a back-compat symlink into 3.x — never the fixture
source).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ``conftest.py`` puts the repo root on sys.path so ``scripts.docs`` imports.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs import _inventory  # noqa: E402
from scripts.docs.adr_converter import (  # noqa: E402
    AdrParseError,
    body_minus_frontmatter,
    convert,
    invariant,
    parse_bold_inline_header,
    parse_dash_bullet_header,
    parse_header,
    parse_table_header,
    render_frontmatter,
)

# ---------------------------------------------------------------------------
# Realistic ADR-shaped fixtures — one per dialect.
# ---------------------------------------------------------------------------

# 46 of 117 ADRs use the markdown-table dialect.
# Shaped from architecture/3.x/adr/2026-04-19-1-cli-auth-uses-...md
TABLE_ADR = """\
# CLI Auth Uses Browser-Mediated OAuth With Encrypted File-Only Session Storage

| Field | Value |
|---|---|
| Filename | `2026-04-19-1-cli-auth-uses-encrypted-file-only-session-storage.md` |
| Status | Accepted |
| Date | 2026-04-19 |
| Deciders | Spec Kitty Architecture Team |
| Supersedes | `2026-04-09-2-cli-saas-auth-is-browser-mediated-oauth-not-password.md` |

---

## Context and Problem Statement

The April 9 auth ADR made the correct high-level product call and the wrong
local persistence call.

## Decision

Encrypt the session file at rest; never persist tokens to the OS keyring.
"""

# 70 of 117 ADRs use the bold-inline dialect (the dominant format).
# Shaped from architecture/3.x/adr/2026-06-02-2-letta-agent-skill-only-support.md
BOLD_ADR = """\
# Letta agent is skill-only: no slash-command templates

**Filename:** `2026-06-02-2-letta-agent-skill-only-support.md`

**Status:** Accepted

**Date:** 2026-06-02

**Deciders:** Spec Kitty core team

**Technical Story:** [GitHub #1054](https://github.com/Priivacy-ai/spec-kitty/issues/1054)

---

## Context and Problem Statement

Letta Code (`letta`) is a memory-first coding agent supporting headless
automation. The design spike (#1054) raised two questions.

## Decision

Letta is skill-only; no `.letta/commands/` slash-command templates are shipped.
"""

# 1 of 117 ADRs uses the dash-bullet dialect — the dialect the spec missed.
# Verbatim bytes from the canonical real file
# architecture/3.x/adr/2026-04-15-2-explicit-empty-charter-selections-remain-empty.md
DASH_BULLET_ADR = """\
# ADR 2026-04-15-2: Explicit Empty Charter Selections Remain Empty

- Status: Accepted
- Date: 2026-04-15
- Decision Makers: Spec Kitty maintainers
- Supersedes: None
- Related: `/spec-kitty.charter`, charter interview/generation flow, doctrine selection

## Context

`spec-kitty charter generate` compiles a project charter from
`.kittify/charter/interview/answers.yaml`.

That interview schema includes explicit selection lists for:

- `selected_paradigms`
- `selected_directives`
- `available_tools`

## Decision

Explicit empty charter selections remain empty.
"""


# ---------------------------------------------------------------------------
# T027 — markdown-table parser.
# ---------------------------------------------------------------------------
def test_table_parser_extracts_fields_and_body() -> None:
    header = parse_table_header(TABLE_ADR)

    assert header.title == (
        "CLI Auth Uses Browser-Mediated OAuth With "
        "Encrypted File-Only Session Storage"
    )
    assert header.status == "Accepted"
    assert header.date == "2026-04-19"
    # The table rows, the `---` rule, and surrounding blanks are header, not body.
    assert header.body.startswith("## Context and Problem Statement")
    assert "| Status | Accepted |" not in header.body


# ---------------------------------------------------------------------------
# T028 — bold-inline parser.
# ---------------------------------------------------------------------------
def test_bold_inline_parser_extracts_fields_and_body() -> None:
    header = parse_bold_inline_header(BOLD_ADR)

    assert header.title == "Letta agent is skill-only: no slash-command templates"
    assert header.status == "Accepted"
    assert header.date == "2026-06-02"
    assert header.body.startswith("## Context and Problem Statement")
    assert "**Status:**" not in header.body


# ---------------------------------------------------------------------------
# T029 — dash-bullet parser (the missed dialect) + its boundary rule.
# ---------------------------------------------------------------------------
def test_dash_bullet_parser_extracts_fields_and_body() -> None:
    header = parse_dash_bullet_header(DASH_BULLET_ADR)

    assert header.title == (
        "ADR 2026-04-15-2: Explicit Empty Charter Selections Remain Empty"
    )
    assert header.status == "Accepted"
    assert header.date == "2026-04-15"
    # Boundary rule: top bullets are header; the body begins at `## Context`.
    assert header.body.startswith("## Context")
    assert "- Status: Accepted" not in header.body


def test_dash_bullet_body_bullets_are_body_not_header() -> None:
    # Bullets *inside* the body (after the heading) must survive in the body —
    # the boundary is the first non-bullet, non-blank line after the top block.
    header = parse_dash_bullet_header(DASH_BULLET_ADR)

    assert "- `selected_paradigms`" in header.body
    assert "- `available_tools`" in header.body


# ---------------------------------------------------------------------------
# T030 — frontmatter emitter (bare `status`, MADR vocabulary, never doc_status).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("adr", [TABLE_ADR, BOLD_ADR, DASH_BULLET_ADR])
def test_emitter_writes_bare_status_not_doc_status(adr: str) -> None:
    converted = convert(adr)

    assert converted.startswith("---\n")
    parsed = _inventory.parse_frontmatter(converted)
    # Bare `status` is the sanctioned ADR exception; `doc_status` is for pages.
    assert "status" in parsed
    assert "doc_status" not in parsed
    assert parsed["status"] == "Accepted"
    assert "title" in parsed
    assert "date" in parsed


def test_emitter_satisfies_ratchet_required_keys() -> None:
    # The anti-sprawl ratchet requires exactly these keys via the same parser.
    converted = convert(BOLD_ADR)
    parsed = _inventory.parse_frontmatter(converted)

    for key in ("title", "status", "date"):
        assert key in parsed


def test_render_frontmatter_emits_fenced_ordered_block() -> None:
    header = parse_bold_inline_header(BOLD_ADR)
    block = render_frontmatter(header)

    assert block.startswith("---\n")
    assert block.endswith("---\n")
    # title → status → date order, bare `status` key.
    assert block.index("title:") < block.index("status:") < block.index("date:")
    assert "doc_status" not in block


def test_emitter_canonicalises_madr_status_case() -> None:
    lowercase = BOLD_ADR.replace("**Status:** Accepted", "**Status:** accepted")
    parsed = _inventory.parse_frontmatter(convert(lowercase))

    assert parsed["status"] == "Accepted"


# ---------------------------------------------------------------------------
# T031 + T032 — content-invariance: green per dialect, RED on body mutation.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("name", "adr"),
    [("table", TABLE_ADR), ("bold", BOLD_ADR), ("dash-bullet", DASH_BULLET_ADR)],
)
def test_conversion_preserves_body_invariance(name: str, adr: str) -> None:
    converted = convert(adr)

    assert invariant(adr, converted), f"{name} dialect broke body invariance"


def test_mutation_fixture_drives_invariance_red() -> None:
    # Simulate a converter that altered one decision-body byte: invariance MUST
    # catch it. This is the false-green-proof — a re-render comparison would
    # pass on whitespace and miss this.
    converted = convert(BOLD_ADR)
    mutated = converted.replace(
        "Letta is skill-only", "Letta is slash-command-only"
    )

    assert mutated != converted  # the mutation actually landed
    assert not invariant(BOLD_ADR, mutated)


def test_whitespace_only_mutation_drives_invariance_red() -> None:
    # Locks the *raw-byte* (non-normalised) contract per NFR-001 / spec T031
    # ("A re-render comparison is a false-green — assert raw bytes"). A word-swap
    # mutation alone cannot distinguish a raw-byte ``==`` from a whitespace-
    # normalised compare. This fixture differs from the converted output by
    # whitespace ONLY (a doubled space in the Decision body), so it is caught by
    # raw-byte ``==`` (RED) but MISSED by a ``.split()``/normalised compare
    # (GREEN). It therefore fails if someone weakens ``invariant()`` to normalise.
    converted = convert(BOLD_ADR)
    mutated = converted.replace("skill-only; no", "skill-only;  no")

    assert mutated != converted  # the whitespace-only mutation actually landed
    # Same non-whitespace tokens — only the spacing differs. A normalised compare
    # would treat these as equal; raw-byte invariance must not.
    assert mutated.split() == converted.split()
    assert not invariant(BOLD_ADR, mutated)


def test_invariance_reuses_inventory_parse_frontmatter() -> None:
    # The post-image strip delegates the "is this frontmatter?" judgment to the
    # canonical inventory parser: a post-image whose frontmatter that parser
    # rejects (empty mapping) must raise, not silently treat the page as body.
    not_frontmatter = "## Context\n\nNo frontmatter fence here.\n"
    assert _inventory.parse_frontmatter(not_frontmatter) == {}

    with pytest.raises(AdrParseError):
        body_minus_frontmatter(not_frontmatter)


# ---------------------------------------------------------------------------
# T032 — malformed input surfaces a clear error (no silent status-less emit).
# ---------------------------------------------------------------------------
def test_status_less_header_raises_clear_error() -> None:
    status_less = """\
# Some ADR Without A Status

**Date:** 2026-06-02

## Context

Body text.
"""
    with pytest.raises(AdrParseError, match="Status"):
        parse_header(status_less)


def test_non_madr_status_raises_clear_error() -> None:
    bogus = BOLD_ADR.replace("**Status:** Accepted", "**Status:** Ratified")

    with pytest.raises(AdrParseError, match="MADR"):
        parse_header(bogus)


def test_titleless_input_raises_clear_error() -> None:
    titleless = "**Status:** Accepted\n\n**Date:** 2026-06-02\n\n## Context\n"

    with pytest.raises(AdrParseError, match="title"):
        parse_header(titleless)

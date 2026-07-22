"""Durable zero-readers guard for the WP07 (#2816, IC-06 / FR-011) inert-field
reduction.

FR-011 removes the now-inert ``wp_metadata`` field definitions that survive the
runtime-state corpus cutover with **zero live readers**. The removal's
precondition and its regression lock is a durable sweep proving that no live
code under ``src/`` references each removed field -- an attribute-access + AST
+ string-literal + keyword-arg sweep, NOT merely an ``extract_scalar(...)``
match (a field consumed via ``WPMetadata.<field>`` / ``read_wp_frontmatter().
<field>`` would be missed by a bare scalar-key match).

Two guarantees, mirroring WP06's SC-009 non-vacuity pattern:

1. **Zero live readers.** For every field in :data:`REMOVED_FIELDS`, the sweep
   over ``src/`` finds no reference (attribute / string-literal / keyword), and
   the field is genuinely gone from :class:`WPMetadata`'s schema.
2. **Durable non-vacuity (poison).** A co-located synthetic-source poison
   assertion feeds the SAME detector a source that DOES reference a removed
   field and asserts it flags RED, plus a clean mirror that stays GREEN -- so a
   detector bug that silently matches nothing cannot yield a permanent false
   green (DIR-041 "passes for the wrong reason").

Parse-safety (``extra="forbid"``): a removed field must ALSO be absent from
every real WP frontmatter in the corpus, otherwise its removal would turn a
tolerated legacy key into a hard ``ValidationError`` -- a behavioural
regression this optional WP forbids. That invariant is pinned here too.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from specify_cli.status.wp_metadata import WPMetadata

pytestmark = [pytest.mark.unit, pytest.mark.fast]


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
_WP_METADATA_REL = "specify_cli/status/wp_metadata.py"

#: The proven-inert ``wp_metadata`` field DEFINITIONS removed by T029. Each is
#: proven (a) reader-free across ``src/`` by :func:`_source_references_field`
#: below and (b) absent from every real WP frontmatter (parse-safe under
#: ``extra="forbid"``). ``branch_strategy_override`` was a speculative
#: "observed-in-practice" tolerance slot (added in a merge-test repair) that
#: never appears in any authored WP frontmatter and has no runtime reader.
REMOVED_FIELDS: tuple[str, ...] = ("branch_strategy_override",)

#: Snapshot-carrier runtime fields that MUST be retained -- they still carry the
#: reduced-snapshot values surfaced by ``_resolve_runtime_fields_from_snapshot``
#: (FR-005). Deleting any of these would be a real regression, not a reduction.
RETAINED_CARRIER_FIELDS: tuple[str, ...] = (
    "shell_pid",
    "shell_pid_created_at",
    "agent",
    "assignee",
)


def _source_references_field(field: str, source: str) -> bool:
    """Return True iff *source* (Python) references *field* as a live reader.

    A "reader" is any of:

    * an attribute access ``<expr>.<field>`` (e.g. ``meta.branch_strategy_override``),
    * a keyword argument ``<field>=`` (e.g. ``WPMetadata(branch_strategy_override=...)``
      / ``meta.update(branch_strategy_override=...)``),
    * a string literal ``"<field>"`` (e.g. ``getattr(meta, "branch_strategy_override")``
      / ``extract_scalar(fm, "branch_strategy_override")``).

    AST-based (robust to comments/formatting); this is the SINGLE detector the
    real sweep and the poison test both drive, so the zero-readers pass is
    meaningful rather than vacuous.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == field:
            return True
        if isinstance(node, ast.keyword) and node.arg == field:
            return True
        if isinstance(node, ast.Constant) and node.value == field:
            return True
    return False


def _iter_src_files() -> list[Path]:
    return sorted(
        p
        for p in _SRC_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
        and p.relative_to(_SRC_ROOT).as_posix() != _WP_METADATA_REL
    )


def _live_reader_sites(field: str) -> list[str]:
    """Every ``src/`` file (bar the definition module) that references *field*."""
    hits: list[str] = []
    for path in _iter_src_files():
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if field not in source:  # cheap pre-filter before AST parse
            continue
        if _source_references_field(field, source):
            hits.append(path.relative_to(_SRC_ROOT).as_posix())
    return hits


# ---------------------------------------------------------------------------
# Guarantee 1 — zero live readers + genuine removal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", REMOVED_FIELDS)
def test_removed_field_has_zero_live_readers(field: str) -> None:
    """No live ``src/`` code references the removed field (attribute / string /
    keyword sweep, not just ``extract_scalar``)."""
    sites = _live_reader_sites(field)
    assert sites == [], (
        f"{field!r} was removed from WPMetadata but is still referenced in "
        f"src/: {sites}. A field with a surviving reader is out of scope and "
        "must be kept (FR-011 'confirm zero live readers before removal')."
    )


@pytest.mark.parametrize("field", REMOVED_FIELDS)
def test_removed_field_is_gone_from_schema(field: str) -> None:
    """The removal actually happened -- the field is no longer a WPMetadata
    schema field (locks the reduction against silent re-introduction)."""
    assert field not in WPMetadata.model_fields


def _frontmatter_block(text: str) -> str:
    """Return the YAML frontmatter block (between the first two ``---`` fences).

    Only the leading frontmatter is parsed by ``WPMetadata``; body prose / code
    examples that merely mention a field name (e.g. mission 065's WP03, which
    *documents* the model) must NOT count as a real frontmatter key.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    block: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        block.append(line)
    return "\n".join(block)


@pytest.mark.parametrize("field", REMOVED_FIELDS)
def test_removed_field_absent_from_corpus_frontmatter(field: str) -> None:
    """Parse-safety under ``extra="forbid"``: a removed field must not appear
    as a **frontmatter** key in any real WP file, else its removal would turn a
    tolerated legacy key into a hard ValidationError (a regression). Only the
    leading ``---`` block counts -- a mention in body prose/code does not."""
    specs_root = _REPO_ROOT / "kitty-specs"
    if not specs_root.exists():
        pytest.skip("no kitty-specs corpus in this checkout")
    offenders = [
        wp.relative_to(_REPO_ROOT).as_posix()
        for wp in specs_root.glob("*/tasks/WP*.md")
        if any(
            line.strip().startswith(f"{field}:")
            for line in _frontmatter_block(
                wp.read_text(encoding="utf-8-sig", errors="replace")
            ).splitlines()
        )
    ]
    assert offenders == [], (
        f"{field!r} still appears as a frontmatter key in real WP files "
        f"{offenders}; removing it from WPMetadata (extra='forbid') would break "
        "parsing of those files."
    )


# ---------------------------------------------------------------------------
# Guarantee 2 — durable non-vacuity (poison), mirroring WP06 SC-009
# ---------------------------------------------------------------------------


def test_detector_flags_a_synthetic_reader_red() -> None:
    """Poison: the detector emits a POSITIVE for a synthetic source that reads a
    removed field via each supported reader shape -- so the zero-readers pass is
    non-vacuous (a match-nothing detector bug would fail here)."""
    field = REMOVED_FIELDS[0]
    attribute_reader = f"def f(meta):\n    return meta.{field}\n"
    keyword_reader = f"def f():\n    return WPMetadata({field}=None)\n"
    string_reader = f'def f(meta):\n    return getattr(meta, "{field}")\n'
    assert _source_references_field(field, attribute_reader)
    assert _source_references_field(field, keyword_reader)
    assert _source_references_field(field, string_reader)


def test_detector_stays_green_on_clean_source() -> None:
    """Mirror of the poison: a source that references only RETAINED fields does
    NOT trip the detector -- the positive above is discriminating, not blanket."""
    field = REMOVED_FIELDS[0]
    clean = "def f(meta):\n    return meta.work_package_id + meta.shell_pid\n"
    assert not _source_references_field(field, clean)


# ---------------------------------------------------------------------------
# Boundary guarantees — carriers retained; status_phase never a WPMetadata field
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", RETAINED_CARRIER_FIELDS)
def test_snapshot_carrier_fields_are_retained(field: str) -> None:
    """The reduced-snapshot carrier fields stay in the schema (they are NOT
    inert -- ``_resolve_runtime_fields_from_snapshot`` re-points them, FR-005)."""
    assert field in WPMetadata.model_fields


def test_status_phase_is_not_a_wp_metadata_field() -> None:
    """``status_phase`` is a ``meta.json`` marker read by the kept
    ``_legacy_lane_mirror_enabled`` (C-004) -- it is NOT a WPMetadata field and
    is entirely out of IC-06's bounds. This pins that it was never (re)introduced
    here as a field the reduction could tempt an out-of-scope retirement of."""
    assert "status_phase" not in WPMetadata.model_fields

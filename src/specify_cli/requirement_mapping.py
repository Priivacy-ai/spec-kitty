"""Structured requirement-to-WP mapping validation and frontmatter helpers.

The LLM registers mappings via ``spec-kitty agent tasks map-requirements``
which writes ``requirement_refs`` directly into each WP file's YAML
frontmatter.  ``finalize-tasks`` reads from frontmatter first (primary),
falling back to tasks.md text parsing for pre-API projects.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TypedDict

# Sonar S1192: the FR/NFR/C id alternation appears 5x below (table row,
# heading, bullet-lead, plus the standalone ref/find patterns) -- hoisted
# once here rather than repeated as a literal in every re.compile.
_ID_ALTERNATION = r"(?:FR|NFR|C)-\d+"
_REF_PATTERN = re.compile(rf"^{_ID_ALTERNATION}$", re.IGNORECASE)
_REF_FIND_PATTERN = re.compile(rf"\b{_ID_ALTERNATION}\b", re.IGNORECASE)

# --- #3394: declared-requirement scoping -----------------------------------
#
# A spec.md may legitimately CITE a foreign requirement id in prose (e.g.
# "...easy to miss, see FR-021's default-pack materialization") without that
# citation being a requirement THIS spec declares. ``_REF_FIND_PATTERN``
# alone can't distinguish a citation from a declaration -- it matches both,
# which is #3394: a WP-coverage-eligible spec's own three requirements pass,
# but a mid-sentence citation of another mission's already-shipped FR gets
# treated as an FR this spec must also route to a work package.
#
# A requirement is "declared" (not merely cited) when it opens the line as
# one of four canonical shapes seen across the spec-template corpus
# (kitty-specs/) and the test-fixture corpus alike: the id column of a
# markdown table row (``| FR-001 | ... |``), a heading naming the id
# (``### FR-001`` / ``### FR-001: Title``), a bulleted/numbered list item
# (``- FR-001: ...``, ``- **FR-001**: ...``, ``1. FR-001 ...``), or a bold id
# leading a bare paragraph (``**FR-001 — Title.** body...``). A prose sentence
# that merely *mentions* an id in passing -- not at the start of a table
# cell, heading, bullet, or bold span -- matches none of the four and is
# correctly excluded.
# The id cell itself is sometimes bold (``| **FR-001** | ... |``, common
# across kitty-specs/) or struck through to mark a retired requirement
# (``| ~~FR-006~~ | ...``, e.g. mission retrospective-durable-home-01KVYM1W) --
# optional leading/trailing ``**``/``~~`` around the id, either or both.
#
# Corpus-validation note (#3394 review F2): the four shapes above and the
# decision NOT to hard-fail when a document matches none of them were
# validated against the 366-spec ``kitty-specs/`` corpus during the #3394 Op
# (``01KZYBXE5G1Y8J4C5FAYV1FKN1``). A stricter, hard-failing prototype (refuse
# whenever raw ``FR``/``NFR``/``C`` tokens are present but none match a
# declared shape) was measured at roughly a 6% false-positive rate against
# that corpus and rejected for that reason; the prototype and its measurement
# were not preserved outside the Op transcript, so this sentence is the
# durable record of the number and the rationale. See
# :func:`find_undeclared_requirement_citations` below for the soft,
# non-blocking warning shipped instead of that rejected hard-fail layer.
_TABLE_ROW_ID_PATTERN = re.compile(rf"^\s*\|\s*(?:\*\*|~~){{0,2}}({_ID_ALTERNATION})(?:\*\*|~~){{0,2}}\s*\|", re.IGNORECASE)
_HEADING_ID_PATTERN = re.compile(rf"^#{{1,6}}\s*({_ID_ALTERNATION})\b", re.IGNORECASE)
# A leading ``-``, ``*``, or ``N.`` marker is itself the "this is a list
# item, not a sentence" signal that makes an id a declaration. The marker
# class includes ``*``, so a bold-led line (``**FR-001**: ...``) is
# recognized through this SAME pattern rather than a separate mechanism: the
# marker slot consumes the line's first ``*`` as the bullet marker, and the
# following ``\*{0,2}`` consumes the second ``*`` that opens the bold span --
# ``*`` is doubling as both "bullet" and "bold-open" here. That is why
# ``- FR-001: ...``, ``- **FR-001**: ...``, and a bold-led bare paragraph
# like ``**FR-001 — Title.** body text`` (common across kitty-specs/) all
# declare FR-001 through this one pattern; there is no distinct
# bold-paragraph mechanism to reach.
# A bare, un-marked line opening with an id and no leading ``-``/``*``/``N.``
# at all (``FR-001 must hold...``) matches no marker and is indistinguishable
# from a citation sentence, so it correctly does NOT count as declared
# (that's the #3394 bug).
_BULLET_LEAD_ID_PATTERN = re.compile(rf"^\s*(?:[-*]|\d+\.)\s*\*{{0,2}}({_ID_ALTERNATION})\b", re.IGNORECASE)
_DECLARED_ID_PATTERNS = (
    _TABLE_ROW_ID_PATTERN,
    _HEADING_ID_PATTERN,
    _BULLET_LEAD_ID_PATTERN,
)


def _declared_ids(spec_content: str) -> set[str]:
    """Ids written as a table row, an id-naming heading, or a bold-led definition.

    Doc-wide (not scoped to a ``Functional Requirements``-style heading):
    real specs also declare requirements with no enclosing section heading at
    all (e.g. a bare ``- **FR-001**: ...`` directly under the spec title), so
    scoping extraction to a heading boundary would silently drop those.
    """
    found: set[str] = set()
    for line in spec_content.splitlines():
        for pattern in _DECLARED_ID_PATTERNS:
            match = pattern.match(line)
            if match is not None:
                found.add(match.group(1).upper())
                break
    return found


def _raw_ref_tokens(text: str) -> set[str]:
    """Every ``FR-``/``NFR-``/``C-`` token anywhere in ``text`` (pre-#3394 scan)."""
    return {token.upper() for token in _REF_FIND_PATTERN.findall(text)}


def _is_requirement_heading(line: str) -> bool:
    """True for a markdown heading whose text mentions "requirement" (any case)."""
    stripped = line.lstrip()
    return stripped.startswith("#") and "requirement" in stripped.lower()


def _requirement_named_sections(spec_content: str) -> list[tuple[str, str]]:
    """``(heading_text, body)`` for every heading section naming "requirement".

    A section's body runs from immediately after its heading line to the next
    heading line (any level) or end of document -- mirrors how a human reader
    would scope "the Functional Requirements section".
    """
    lines = spec_content.splitlines()
    heading_idxs = [i for i, line in enumerate(lines) if line.lstrip().startswith("#")]
    sections: list[tuple[str, str]] = []
    for pos, idx in enumerate(heading_idxs):
        heading_line = lines[idx]
        if not _is_requirement_heading(heading_line):
            continue
        end = heading_idxs[pos + 1] if pos + 1 < len(heading_idxs) else len(lines)
        heading_text = heading_line.lstrip("#").strip()
        sections.append((heading_text, "\n".join(lines[idx + 1 : end])))
    return sections


def _undeclared_citation_warning(tokens: list[str], *, scope: str) -> str:
    joined = ", ".join(tokens)
    return (
        f"{scope} mentions requirement-shaped token(s) ({joined}) that matched none of the "
        "recognized declared shapes (table row / id-naming heading / bulleted item / bold-led "
        "paragraph) -- none of them count toward FR coverage. If these ARE this spec's own "
        "requirements, rewrite them in one of the recognized shapes; if they are citations of "
        "another mission's requirement, no action is needed."
    )


def find_undeclared_requirement_citations(spec_content: str) -> list[str]:
    """#3394 review F1: soft, non-blocking signal for the declared-shape-miss case.

    ``_declared_ids`` recognizes four declaration shapes (table row, heading,
    bullet, bold paragraph) and that scoping is deliberately NOT widened here
    (#3394 is settled). But a spec whose requirements are written in NONE of
    those shapes -- e.g. bare, unbulleted, unbolded sentences like "FR-001
    must hold. FR-002 too." -- now silently yields zero declared ids, and
    ``finalize-tasks``/``map-requirements`` then report full coverage with
    nothing to show for it (the same "reports success while measuring
    nothing" shape the project's ledger flags elsewhere).

    This detector does not change what counts as *declared*; it only flags,
    non-blockingly, when raw ref-shaped tokens (the pre-#3394
    ``_REF_FIND_PATTERN`` scan) are present but produced zero declared ids --
    either across the WHOLE document, or within a heading section whose title
    mentions "requirement" (e.g. "Functional Requirements", "Non-Functional
    Requirements").

    Returns:
        Human-readable warning message(s) -- empty when every raw token
        matched a declared shape, or when there were no raw tokens at all.
        Callers surface these as a non-blocking warning (console + a JSON
        field), never as a gate failure.
    """
    declared = _declared_ids(spec_content)
    doc_raw_tokens = _raw_ref_tokens(spec_content)
    if doc_raw_tokens and not declared:
        return [_undeclared_citation_warning(sorted(doc_raw_tokens), scope="spec.md")]

    warnings: list[str] = []
    for heading_text, section in _requirement_named_sections(spec_content):
        section_raw_tokens = _raw_ref_tokens(section)
        if section_raw_tokens and not _declared_ids(section):
            warnings.append(
                _undeclared_citation_warning(sorted(section_raw_tokens), scope=f"The {heading_text!r} section")
            )
    return warnings


class CoverageSummary(TypedDict):
    """Coverage summary returned by :func:`compute_coverage`."""

    total_functional: int
    mapped_functional: int
    unmapped_functional: list[str]


def validate_refs(refs: list[str], spec_requirement_ids: set[str]) -> tuple[list[str], list[str]]:
    """Validate refs against spec.

    Returns:
        (valid_refs, unknown_refs) — both lists are uppercased.
    """
    valid: list[str] = []
    unknown: list[str] = []
    for ref in refs:
        upper = ref.upper()
        if upper in spec_requirement_ids:
            valid.append(upper)
        else:
            unknown.append(upper)
    return valid, unknown


def validate_ref_format(refs: list[str]) -> tuple[list[str], list[str]]:
    """Check refs match FR|NFR|C-\\d+ format.

    Returns:
        (well_formed, malformed) — both lists are uppercased.
    """
    well_formed: list[str] = []
    malformed: list[str] = []
    for ref in refs:
        upper = ref.upper()
        if _REF_PATTERN.match(upper):
            well_formed.append(upper)
        else:
            malformed.append(upper)
    return well_formed, malformed


def classify_stale_refs(
    stale_refs: dict[str, list[str]],
    malformed: list[str],
) -> dict[str, dict[str, list[str]]]:
    """Split each WP's offending refs into format-malformed vs unknown-spec-id buckets.

    Lets diagnostics explain *why* a ref is stale: a ``malformed`` ref violates the
    ``FR-NNN`` / ``NFR-NNN`` / ``C-NNN`` shape (e.g. ``FR-003a`` or an unfilled
    ``<FR-XXX>`` placeholder), whereas an ``unknown_spec_id`` ref is well-formed but
    not declared in ``spec.md``.

    Args:
        stale_refs: per-WP offending raw tokens (case preserved).
        malformed: uppercased tokens that fail the format check (from
            :func:`validate_ref_format`).

    Returns:
        ``{wp_id: {"malformed": [...], "unknown_spec_id": [...]}}`` — raw tokens,
        sorted, each offending token in exactly one bucket.
    """
    malformed_set = set(malformed)
    reasons: dict[str, dict[str, list[str]]] = {}
    for wp_id, bad_refs in stale_refs.items():
        wp_malformed = sorted(r for r in bad_refs if r.startswith("<") or r.upper() in malformed_set)
        wp_unknown = sorted(r for r in bad_refs if not r.startswith("<") and r.upper() not in malformed_set)
        reasons[wp_id] = {"malformed": wp_malformed, "unknown_spec_id": wp_unknown}
    return reasons


def compute_coverage(mappings: dict[str, list[str]], functional_ids: set[str]) -> CoverageSummary:
    """Compute coverage summary: total, mapped, unmapped FRs."""
    mapped: set[str] = set()
    for refs in mappings.values():
        mapped.update(ref.upper() for ref in refs)
    mapped_functional = sorted(mapped & functional_ids)
    unmapped_functional = sorted(functional_ids - mapped)
    return {
        "total_functional": len(functional_ids),
        "mapped_functional": len(mapped_functional),
        "unmapped_functional": unmapped_functional,
    }


def parse_requirement_ids_from_spec_md(spec_content: str) -> dict[str, list[str]]:
    """Parse DECLARED requirement IDs from spec.md content.

    Shared between map-requirements and finalize-tasks.

    Scoped to ids the spec genuinely *declares* -- a markdown table row
    (``| FR-001 | ... |``), a heading naming the id (``### FR-001``), or a
    bold-led definition (``- **FR-001**: ...``) -- not every
    ``FR-NNN``/``NFR-NNN``/``C-NNN`` token anywhere in the document (#3394).
    A spec's prose may cite another mission's already-shipped requirement as
    background context (e.g. "...easy to miss, see FR-021's default-pack
    materialization"); that citation is not a requirement THIS spec's work
    packages must cover, so it is excluded from both keys below.

    Returns:
        {"all": [...], "functional": [...]} -- "all" is every declared FR/
        NFR/C id (used to check a WP-declared ref is *known*); "functional"
        is the FR-prefixed subset (used for FR coverage gating).
    """
    declared = _declared_ids(spec_content)
    functional_ids = {req_id for req_id in declared if req_id.startswith("FR-")}
    return {
        "all": sorted(declared),
        "functional": sorted(functional_ids),
    }


def normalize_requirement_refs_value(value: Any) -> list[str]:
    """Normalize frontmatter requirement_refs to list[str].

    Handles str, list (of str/int/mixed), None, and empty values.
    Extracts FR-NNN / NFR-NNN / C-NNN patterns and uppercases them.
    """
    refs: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                refs.extend(ref_id.upper() for ref_id in _REF_FIND_PATTERN.findall(item))
    elif isinstance(value, str):
        refs.extend(ref_id.upper() for ref_id in _REF_FIND_PATTERN.findall(value))
    return list(dict.fromkeys(refs))


def _read_all_wp_refs(
    tasks_dir: Path,
    extractor: Any,
) -> dict[str, list[str]]:
    """Read requirement_refs from all WP files' frontmatter.

    Args:
        tasks_dir: Directory containing WP*.md files.
        extractor: Callable(value) -> list[str] applied to the raw
            ``requirement_refs`` frontmatter value of each WP file.
    """
    from specify_cli.status import read_wp_frontmatter

    result: dict[str, list[str]] = {}
    if not tasks_dir.exists():
        return result
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        match = re.match(r"(WP\d{2})", wp_file.name)
        if not match:
            continue
        wp_id = match.group(1)
        try:
            wp_meta_dict, _ = read_wp_frontmatter(wp_file)
        except Exception:
            result[wp_id] = []
            continue
        result[wp_id] = extractor(wp_meta_dict.requirement_refs)
    return result


def read_all_wp_requirement_refs(tasks_dir: Path) -> dict[str, list[str]]:
    """Read requirement_refs from all WP files' frontmatter (normalized)."""
    return _read_all_wp_refs(tasks_dir, normalize_requirement_refs_value)


def read_all_wp_raw_requirement_refs(tasks_dir: Path) -> dict[str, list[str]]:
    """Read raw requirement_refs from all WP files' frontmatter.

    Uses the raw frontmatter dict (not the typed model) so that non-string
    items (e.g. integers) are preserved as ``<NON_STRING:...>`` tokens by
    :func:`_extract_raw_tokens`.
    """
    from specify_cli.frontmatter import FrontmatterManager

    result: dict[str, list[str]] = {}
    if not tasks_dir.exists():
        return result
    fm = FrontmatterManager()
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        match = re.match(r"(WP\d{2})", wp_file.name)
        if not match:
            continue
        wp_id = match.group(1)
        try:
            raw_dict, _ = fm.read(wp_file)
        except Exception:  # MIGRATION-ONLY: raw dict access is intentional here
            result[wp_id] = []
            continue
        result[wp_id] = _extract_raw_tokens(raw_dict.get("requirement_refs"))  # MIGRATION-ONLY: raw dict access is intentional here
    return result


def _extract_raw_tokens(value: Any) -> list[str]:
    """Extract individual tokens from a frontmatter value, preserving case.

    Case is preserved so that diagnostics can show exactly what was written
    (e.g. ``BOGUS`` vs ``bogus``).  Callers that need uppercased tokens for
    comparison should uppercase themselves.
    """
    tokens: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                tokens.extend(token for token in re.split(r"[,\s]+", item) if token.strip())
            else:
                tokens.append(f"<NON_STRING:{item}>")
    elif isinstance(value, str):
        tokens.extend(token for token in re.split(r"[,\s]+", value) if token.strip())
    return tokens

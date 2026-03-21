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

_REF_PATTERN = re.compile(r"^(?:FR|NFR|C)-\d+$", re.IGNORECASE)


class CoverageSummary(TypedDict):
    """Coverage summary returned by :func:`compute_coverage`."""

    total_functional: int
    mapped_functional: int
    unmapped_functional: list[str]


def validate_refs(
    refs: list[str], spec_requirement_ids: set[str]
) -> tuple[list[str], list[str]]:
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


def compute_coverage(
    mappings: dict[str, list[str]], functional_ids: set[str]
) -> CoverageSummary:
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
    """Parse requirement IDs from spec.md content.

    Shared between map-requirements and finalize-tasks.

    Returns:
        {"all": [...], "functional": [...]}
    """
    all_ids = {
        req_id.upper()
        for req_id in re.findall(r"\b(?:FR|NFR|C)-\d+\b", spec_content, re.IGNORECASE)
    }
    functional_ids = {req_id for req_id in all_ids if req_id.startswith("FR-")}
    return {
        "all": sorted(all_ids),
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
                refs.extend(
                    ref_id.upper()
                    for ref_id in re.findall(
                        r"\b(?:FR|NFR|C)-\d+\b", item, re.IGNORECASE
                    )
                )
    elif isinstance(value, str):
        refs.extend(
            ref_id.upper()
            for ref_id in re.findall(
                r"\b(?:FR|NFR|C)-\d+\b", value, re.IGNORECASE
            )
        )
    return list(dict.fromkeys(refs))


def _read_all_wp_refs(
    tasks_dir: Path,
    extractor: Any,
) -> dict[str, list[str]]:
    """Shared reader for WP frontmatter requirement_refs.

    Args:
        tasks_dir: Directory containing WP*.md files.
        extractor: Callable(value) -> list[str] applied to the raw
            ``requirement_refs`` frontmatter value of each WP file.
    """
    from specify_cli.frontmatter import read_frontmatter

    result: dict[str, list[str]] = {}
    if not tasks_dir.exists():
        return result
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        match = re.match(r"(WP\d{2})", wp_file.name)
        if not match:
            continue
        wp_id = match.group(1)
        try:
            frontmatter, _ = read_frontmatter(wp_file)
        except Exception:
            result[wp_id] = []
            continue
        result[wp_id] = extractor(frontmatter.get("requirement_refs"))
    return result


def read_all_wp_requirement_refs(tasks_dir: Path) -> dict[str, list[str]]:
    """Read requirement_refs from all WP files' frontmatter (normalized)."""
    return _read_all_wp_refs(tasks_dir, normalize_requirement_refs_value)


def read_all_wp_raw_requirement_refs(tasks_dir: Path) -> dict[str, list[str]]:
    """Read raw requirement_refs from all WP files' frontmatter."""
    return _read_all_wp_refs(tasks_dir, _extract_raw_tokens)


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
                tokens.extend(
                    token
                    for token in re.split(r"[,\s]+", item)
                    if token.strip()
                )
            else:
                tokens.append(f"<NON_STRING:{item}>")
    elif isinstance(value, str):
        tokens.extend(
            token
            for token in re.split(r"[,\s]+", value)
            if token.strip()
        )
    return tokens

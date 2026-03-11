"""Structured requirement-to-WP mapping validation and frontmatter helpers.

The LLM registers mappings via ``spec-kitty agent tasks map-requirements``
which writes ``requirement_refs`` directly into each WP file's YAML
frontmatter.  ``finalize-tasks`` reads from frontmatter (2-tier fallback:
tasks.md text → WP frontmatter).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Matches FR-001, NFR-002, C-003 etc.
_REF_PATTERN = re.compile(r"^(?:FR|NFR|C)-\d+$", re.IGNORECASE)


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
) -> dict:
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


def read_all_wp_requirement_refs(tasks_dir: Path) -> dict[str, list[str]]:
    """Read requirement_refs from all WP files' frontmatter.

    Returns:
        {wp_id: [refs]} for every WP file found.  Values are normalized
        (uppercased, pattern-matched FR/NFR/C-NNN only).
    """
    from specify_cli.frontmatter import read_frontmatter

    result: dict[str, list[str]] = {}
    if not tasks_dir.exists():
        return result
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        m = re.match(r"(WP\d{2})", wp_file.name)
        if not m:
            continue
        wp_id = m.group(1)
        try:
            fm, _ = read_frontmatter(wp_file)
        except Exception:
            result[wp_id] = []
            continue
        result[wp_id] = normalize_requirement_refs_value(
            fm.get("requirement_refs")
        )
    return result


def read_all_wp_raw_requirement_refs(tasks_dir: Path) -> dict[str, list[str]]:
    """Read raw requirement_refs strings from all WP files' frontmatter.

    Unlike ``read_all_wp_requirement_refs``, this does NOT pattern-filter
    entries.  Every string in the YAML list is returned as-is (uppercased),
    so callers can detect malformed values like ``BOGUS``.

    Returns:
        {wp_id: [raw_strings]} for every WP file found.
    """
    from specify_cli.frontmatter import read_frontmatter

    result: dict[str, list[str]] = {}
    if not tasks_dir.exists():
        return result
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        m = re.match(r"(WP\d{2})", wp_file.name)
        if not m:
            continue
        wp_id = m.group(1)
        try:
            fm, _ = read_frontmatter(wp_file)
        except Exception:
            result[wp_id] = []
            continue
        raw = fm.get("requirement_refs")
        if isinstance(raw, list):
            result[wp_id] = [
                str(item).upper() for item in raw if isinstance(item, str)
            ]
        elif isinstance(raw, str):
            result[wp_id] = [raw.upper()]
        else:
            result[wp_id] = []
    return result

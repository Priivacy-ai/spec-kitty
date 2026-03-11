"""Structured requirement-to-WP mapping storage and validation.

Provides a deterministic, JSON-based requirement mapping that replaces
fragile regex parsing of markdown text in tasks.md.  The LLM registers
mappings via ``spec-kitty agent tasks map-requirements`` and
``finalize-tasks`` reads them as the primary source.
"""

from __future__ import annotations

import json
import re
import datetime as _dt
from pathlib import Path

MAPPING_FILENAME = "requirement-mapping.json"

# Matches FR-001, NFR-002, C-003 etc.
_REF_PATTERN = re.compile(r"^(?:FR|NFR|C)-\d+$", re.IGNORECASE)


def load_requirement_mapping(feature_dir: Path) -> dict[str, list[str]]:
    """Load mappings from requirement-mapping.json.

    Returns:
        Dict of WP ID -> list of requirement ref strings.
        Empty dict if file is missing or malformed.
    """
    path = feature_dir / MAPPING_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        mappings = data.get("mappings", {})
        if not isinstance(mappings, dict):
            return {}
        # Normalize: uppercase all refs
        return {
            wp_id: [ref.upper() for ref in refs]
            for wp_id, refs in mappings.items()
            if isinstance(refs, list)
        }
    except (json.JSONDecodeError, OSError):
        return {}


def save_requirement_mapping(
    feature_dir: Path, mappings: dict[str, list[str]]
) -> None:
    """Save mappings to requirement-mapping.json with version + timestamp."""
    path = feature_dir / MAPPING_FILENAME
    data = {
        "version": 1,
        "mappings": {
            wp_id: sorted({ref.upper() for ref in refs})
            for wp_id, refs in mappings.items()
        },
        "updated_at": _dt.datetime.now(_dt.UTC).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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

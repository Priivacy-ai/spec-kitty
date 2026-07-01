"""AC-11 / C-010 / NFR-004: Slice F glossary terms are canonical.

covers: AC-11, FR-302, C-010 — expected GREEN at: WP12 final commit after T065 promotion

RED on planning base (and after WP08): the 10 Slice F terms land as
``Status: candidate`` per WP08. WP12/T065 promotes each to ``canonical``.

The glossary uses a Markdown table format:
    | **Status** | canonical |
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

SLICE_F_TERMS = [
    "Three-layer DRG",
    "Organisation Tier",
    "CharterScope",
    "Workflow Sequence",
    "Workflow ID",
    "Ratchet Baseline",
    "Cat-7 Grandfathered Orphan",
    "Symbol-level Dead Code",
    "Catalog Miss",
    "`__all__` Declaration Convention",
]


def test_all_slice_f_terms_are_canonical_in_doctrine_context() -> None:
    """All 10 Slice F terms must have Status: canonical in docs/context/doctrine.md."""
    repo_root = Path(__file__).resolve().parents[2]
    glossary_path = repo_root / "docs" / "context" / "doctrine.md"
    assert glossary_path.exists(), f"glossary not found: {glossary_path}"
    glossary = glossary_path.read_text()

    offenders: list[str] = []
    for term in SLICE_F_TERMS:
        # Escape the term for regex; handle backtick-quoted terms
        term_escaped = re.escape(term)
        # Find the section heading (### <term>) then look for the Status table row
        # within the next ~20 lines (the entry is short)
        pattern = re.compile(
            r"###\s+" + term_escaped + r"\s*\n"
            r".*?"
            r"\|\s*\*\*Status\*\*\s*\|\s*(\w+)\s*\|",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(glossary)
        if not match:
            offenders.append(f"{term}: missing entry or malformed Status row")
        elif match.group(1).lower() != "canonical":
            offenders.append(
                f"{term}: Status={match.group(1)!r} (expected 'canonical')"
            )

    assert not offenders, (
        "Glossary canonical-promotion failures (C-010 binding):\n  "
        + "\n  ".join(offenders)
    )

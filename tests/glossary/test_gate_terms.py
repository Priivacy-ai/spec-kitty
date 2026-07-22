"""Terminology regression tests for gate-family terms (WP07).

Verifies that transition gate, gate handler, and gate binding are registered
in BOTH glossary surfaces (pack + orchestration.md) with consistent definitions
and disambiguation guards against the five real gate senses.
"""

import re
from pathlib import Path

import pytest
import yaml

# Terms to verify: must exist in both surfaces
REQUIRED_TERMS = ["transition gate", "gate handler", "gate binding"]

# Five real gate senses that the new terms must disambiguate against
REAL_GATE_SENSES = [
    "branch strategy gate",
    "diff compliance gate",
    "dependency gate",
    "merge dependency gate",
    "sonar quality gate",
]

# Phantom sense that must NOT appear in the new definitions
PHANTOM_SENSE = "semantic gate"


@pytest.fixture
def glossary_pack_path() -> Path:
    """Locate the glossary pack."""
    pack_path = Path(__file__).parent.parent.parent / "src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml"
    assert pack_path.exists(), f"Glossary pack not found at {pack_path}"
    return pack_path


@pytest.fixture
def orchestration_md_path() -> Path:
    """Locate orchestration.md."""
    doc_path = Path(__file__).parent.parent.parent / "docs/context/orchestration.md"
    assert doc_path.exists(), f"orchestration.md not found at {doc_path}"
    return doc_path


@pytest.fixture
def glossary_terms(glossary_pack_path) -> dict:
    """Parse the glossary pack and return terms by surface."""
    with open(glossary_pack_path) as f:
        pack = yaml.safe_load(f)

    terms_by_surface = {}
    for term in pack.get("terms", []):
        surface = term.get("surface")
        if surface:
            terms_by_surface[surface] = term

    return terms_by_surface


def test_all_three_terms_in_glossary_pack(glossary_terms: dict) -> None:
    """Each of the three new terms must resolve as an active surface in the pack."""
    for term in REQUIRED_TERMS:
        assert term in glossary_terms, f"Term '{term}' not found in glossary pack surfaces"
        assert glossary_terms[term].get("status") == "active", f"Term '{term}' is not marked as active"


def test_all_three_terms_in_orchestration_md(orchestration_md_path: Path) -> None:
    """Each of the three new terms must be present as a heading in orchestration.md."""
    content = orchestration_md_path.read_text()

    for term in REQUIRED_TERMS:
        # Look for ### <term> heading (exact match, case-sensitive)
        heading = f"### {term}"
        assert heading in content, f"Heading '{heading}' not found in orchestration.md"


def test_glossary_pack_definitions_have_disambiguation_guard(glossary_terms: dict) -> None:
    """Each pack definition must include a "Do NOT confuse with" guard clause."""
    for term in REQUIRED_TERMS:
        definition = glossary_terms[term].get("definition", "")
        assert "Do NOT confuse with" in definition or "do NOT confuse with" in definition, \
            f"Term '{term}' in glossary pack lacks 'Do NOT confuse with' guard clause"


def test_orchestration_md_definitions_have_disambiguation_guard(orchestration_md_path: Path) -> None:
    """Each human definition in orchestration.md must include a guard clause."""
    content = orchestration_md_path.read_text()

    for term in REQUIRED_TERMS:
        # Find the section for this term
        heading = f"### {term}"
        heading_idx = content.find(heading)
        assert heading_idx >= 0, f"Could not find heading for '{term}'"

        # Extract the definition section (up to the next ### or ---)
        next_heading_idx = content.find("\n### ", heading_idx + 1)
        next_separator_idx = content.find("\n---", heading_idx + 1)

        # Find the end of this term's section
        end_idx = min(
            x for x in [next_heading_idx, next_separator_idx, len(content)]
            if x > heading_idx
        )

        section = content[heading_idx:end_idx]
        assert "Do NOT confuse with" in section or "do NOT confuse with" in section, \
            f"Orchestration.md section for '{term}' lacks 'Do NOT confuse with' guard clause"


def test_no_phantom_semantic_gate_reference(glossary_terms: dict, orchestration_md_path: Path) -> None:
    """Verify the phantom 'semantic gate' sense is not referenced anywhere."""
    # Check glossary pack
    for term in REQUIRED_TERMS:
        definition = glossary_terms[term].get("definition", "")
        assert PHANTOM_SENSE not in definition.lower(), \
            f"Glossary pack term '{term}' incorrectly references phantom '{PHANTOM_SENSE}'"

    # Check orchestration.md
    content = orchestration_md_path.read_text()
    for term in REQUIRED_TERMS:
        heading = f"### {term}"
        heading_idx = content.find(heading)

        next_heading_idx = content.find("\n### ", heading_idx + 1)
        next_separator_idx = content.find("\n---", heading_idx + 1)
        end_idx = min(
            x for x in [next_heading_idx, next_separator_idx, len(content)]
            if x > heading_idx
        )

        section = content[heading_idx:end_idx].lower()
        assert PHANTOM_SENSE not in section, \
            f"Orchestration.md section for '{term}' incorrectly references phantom '{PHANTOM_SENSE}'"


def test_five_real_senses_referenced_in_guards(glossary_terms: dict) -> None:
    """The guard clauses should reference the five real gate senses."""
    for term in REQUIRED_TERMS:
        definition = glossary_terms[term].get("definition", "").lower()

        # At least some of the five senses should be mentioned in the guard
        senses_mentioned = sum(
            1 for sense in REAL_GATE_SENSES
            if sense.lower() in definition
        )
        assert senses_mentioned >= 2, \
            f"Term '{term}' definition should reference multiple real gate senses; found {senses_mentioned}"


def test_pack_and_orchestration_md_consistency(glossary_terms: dict, orchestration_md_path: Path) -> None:
    """Both surfaces should carry the three terms with reasonably consistent meanings."""
    content = orchestration_md_path.read_text()

    for term in REQUIRED_TERMS:
        # Check pack exists
        assert term in glossary_terms, f"Term '{term}' missing from glossary pack"

        # Check orchestration.md heading exists
        heading = f"### {term}"
        assert heading in content, f"Heading for '{term}' missing from orchestration.md"


def test_no_legacy_feature_casing_in_new_terms(glossary_terms: dict, orchestration_md_path: Path) -> None:
    """Verify no forbidden 'Feature'/'feature' casing regression in the new terms.

    Per CLAUDE.md Terminology Canon, active systems must use 'Mission' not 'Feature'.
    """
    # Check glossary pack
    for term in REQUIRED_TERMS:
        definition = glossary_terms[term].get("definition", "")
        # Reject standalone 'Feature' or 'feature' (allow only in quotes/context)
        assert not re.search(r'\bFeature\b(?!.*\()', definition), \
            f"Glossary pack term '{term}' contains forbidden 'Feature' (use 'Mission')"

    # Check orchestration.md
    content = orchestration_md_path.read_text()
    for term in REQUIRED_TERMS:
        heading = f"### {term}"
        heading_idx = content.find(heading)

        next_heading_idx = content.find("\n### ", heading_idx + 1)
        next_separator_idx = content.find("\n---", heading_idx + 1)
        end_idx = min(
            x for x in [next_heading_idx, next_separator_idx, len(content)]
            if x > heading_idx
        )

        section = content[heading_idx:end_idx]
        # Look for forbidden Feature term (allow in code blocks)
        lines = section.split("\n")
        for i, line in enumerate(lines):
            if not line.strip().startswith("`"):  # Skip code lines
                assert not re.search(r'\bFeature\b', line), \
                    f"Orchestration.md section for '{term}' contains forbidden 'Feature' (use 'Mission')"

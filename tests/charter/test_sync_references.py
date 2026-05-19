"""WP02 — citation detection in charter-extracted directive bodies.

These tests pin the FR-006 contract: ``charter sync`` must lift catalog
citations (``DIRECTIVE_NNN`` and known tactic-id slugs) found inside a
directive body into the emitted ``Directive.references`` list. Membership
gating against ``DoctrineService.tactics`` is what prevents incidental
kebab-case words from being mis-classified as tactic citations.

See ``contracts/charter-sync-cross-link.md`` for the input/output
specification and ``kitty-specs/wp-prompt-governance-payload-01KRR8HS/
tasks/WP02-charter-sync-extensions.md`` for the WP-level Definition of
Done that these tests close.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.extractor import Extractor, _detect_catalog_references
from charter.sync import sync

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Direct unit tests for the citation detector helper.
# ---------------------------------------------------------------------------


class TestDetectCatalogReferences:
    """Unit-level behaviour of ``_detect_catalog_references``."""

    def test_body_with_DIRECTIVE_032_yields_reference(self) -> None:
        body = (
            "Terminology in code and docs aligns with the project glossary "
            "(DIRECTIVE_032 — Conceptual Alignment)."
        )
        result = _detect_catalog_references(body, tactic_registry=lambda _slug: False)
        assert result == ["DIRECTIVE_032"]

    def test_body_with_known_tactic_slug_yields_reference(self) -> None:
        body = "Reviewers MUST apply language-driven-design when reading the diff."
        known = {"language-driven-design"}
        result = _detect_catalog_references(body, tactic_registry=lambda slug: slug in known)
        assert result == ["language-driven-design"]

    def test_body_with_unknown_kebab_slug_yields_no_reference(self) -> None:
        # Risk R-5: pre-commit-hooks is not a tactic. Without registry
        # membership the slug MUST NOT bleed into references.
        body = "Run the pre-commit-hooks suite before pushing."
        result = _detect_catalog_references(body, tactic_registry=lambda _slug: False)
        assert result == []

    def test_body_with_multiple_citations_dedupes_and_preserves_order(self) -> None:
        body = (
            "See DIRECTIVE_010 for context. "
            "Cross-link to DIRECTIVE_032 too. "
            "And DIRECTIVE_010 again."
        )
        result = _detect_catalog_references(body, tactic_registry=lambda _slug: False)
        assert result == ["DIRECTIVE_010", "DIRECTIVE_032"]

    def test_body_without_citations_emits_empty_list(self) -> None:
        body = "Plain prose with no catalog identifiers whatsoever."
        result = _detect_catalog_references(body, tactic_registry=lambda _slug: False)
        assert result == []

    def test_malformed_citation_is_ignored(self) -> None:
        # Per contract §3 — DIRECTIVE_12 (only 2 digits) is NOT a valid
        # catalog citation and MUST NOT be lifted.
        body = "Compare DIRECTIVE_12 (not real) against DIRECTIVE_032 (real)."
        result = _detect_catalog_references(body, tactic_registry=lambda _slug: False)
        assert result == ["DIRECTIVE_032"]

    def test_mixed_directive_and_tactic_citations_preserve_first_seen_order(self) -> None:
        body = "Tactic acceptance-test-first plus DIRECTIVE_010 plus zombies-tdd."
        known = {"acceptance-test-first", "zombies-tdd"}
        result = _detect_catalog_references(body, tactic_registry=lambda slug: slug in known)
        assert result == ["acceptance-test-first", "DIRECTIVE_010", "zombies-tdd"]

    def test_registry_callable_failures_swallowed_for_directives(self) -> None:
        """A buggy registry MUST NOT break directive-id detection."""
        def bad_registry(_slug: str) -> bool:
            raise RuntimeError("registry crashed")

        body = "Citation DIRECTIVE_032 still survives a broken tactic registry."
        result = _detect_catalog_references(body, tactic_registry=bad_registry)
        assert result == ["DIRECTIVE_032"]


# ---------------------------------------------------------------------------
# End-to-end: Extractor + sync wire the references through into the
# emitted directives.yaml file.
# ---------------------------------------------------------------------------


_CHARTER_WITH_CITATION = """\
# Project Charter

## Code Review Checklist

- Terminology in code and docs aligns with the project glossary
  (DIRECTIVE_032 — Conceptual Alignment).
- The WP diff respects the agent profile's directive-references.
"""


def _load_directives(directives_yaml: Path) -> dict[str, object]:
    yaml = YAML()
    data = yaml.load(directives_yaml.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_sync_emits_references_field_for_DIRECTIVE_citation(tmp_path: Path) -> None:
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(_CHARTER_WITH_CITATION, encoding="utf-8")

    result = sync(charter_file, tmp_path)

    assert result.synced is True
    assert result.error is None
    directives_yaml = tmp_path / "directives.yaml"
    body = directives_yaml.read_text(encoding="utf-8")
    # DIRECTIVE_032 MUST appear somewhere in the emitted file — either in
    # the directive description or in the explicit references list — so
    # the ATDD test for cross-link emission goes green.
    assert "DIRECTIVE_032" in body, (
        "Cross-link contract violated: DIRECTIVE_032 cited in the body "
        "must be preserved in the emitted directives.yaml."
    )

    parsed = _load_directives(directives_yaml)
    directives_list = parsed.get("directives") or []
    assert isinstance(directives_list, list)
    assert directives_list, "Code Review Checklist bullets should produce directives"
    first = directives_list[0]
    assert isinstance(first, dict)
    refs = first.get("references")
    assert refs == ["DIRECTIVE_032"], (
        "First directive (which cites DIRECTIVE_032) must carry a "
        "references list with the catalog ID."
    )


def test_extractor_populates_references_from_body_via_registry() -> None:
    """End-to-end inside the Extractor: registry injection drives references."""
    charter = """\
# Charter

## Project Directives

1. Apply language-driven-design when reading the diff (see DIRECTIVE_010).
2. No bare references here.
"""
    extractor = Extractor(
        tactic_registry=lambda slug: slug == "language-driven-design",
    )
    result = extractor.extract(charter)
    assert len(result.directives.directives) == 2
    first = result.directives.directives[0]
    # Order is first-seen: tactic-slug appears before DIRECTIVE_010 in the body.
    assert first.references == ["language-driven-design", "DIRECTIVE_010"]
    assert result.directives.directives[1].references == []

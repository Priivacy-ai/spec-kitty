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


def test_sync_never_writes_directives_yaml_for_DIRECTIVE_citation(tmp_path: Path) -> None:
    """consolidate-charter-bundle (IC-04 / WP04): sync() no longer scrapes/emits anything.

    The prose->triad directive-body scrape (this test's original subject)
    is retired along with the rest of sync()'s write side. ``directives``
    are hand-authored directly in ``charter.yaml`` now
    (``charter.sync.load_directives_config``); ``directives.yaml`` is never
    materialised by ``sync()``, cited body or not.
    """
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(_CHARTER_WITH_CITATION, encoding="utf-8")

    result = sync(charter_file, tmp_path)

    assert result.synced is False
    assert result.error is None
    assert result.files_written == []
    assert not (tmp_path / "directives.yaml").exists()


def test_extractor_directive_body_extraction_is_retired() -> None:
    """The directive-body citation scraper is retired (IC-04 / WP04).

    ``Extractor``'s constructor no longer accepts ``tactic_registry`` --
    it existed only to thread a citation-detector predicate into the now-
    retired directive-body scraper. ``extract()`` always returns an EMPTY
    ``DirectivesConfig`` regardless of citations in the body (module
    docstring, ``src/charter/extractor.py``).
    """
    charter = """\
# Charter

## Project Directives

1. Apply language-driven-design when reading the diff (see DIRECTIVE_010).
2. No bare references here.
"""
    with pytest.raises(TypeError, match="tactic_registry"):
        Extractor(tactic_registry=lambda slug: slug == "language-driven-design")  # type: ignore[call-arg]

    result = Extractor().extract(charter)
    assert result.directives.directives == []

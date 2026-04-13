"""Tests for doctrine.drg.migration.id_normalizer."""

from __future__ import annotations

import pytest

from doctrine.drg.migration.id_normalizer import (
    artifact_to_urn,
    directive_to_urn,
    normalize_directive_id,
)


# ---------------------------------------------------------------------------
# normalize_directive_id
# ---------------------------------------------------------------------------


class TestNormalizeDirectiveId:
    """Covers the three branches: already-canonical, slug-with-digits, fallback."""

    def test_already_canonical(self) -> None:
        assert normalize_directive_id("DIRECTIVE_024") == "DIRECTIVE_024"

    def test_already_canonical_three_digit(self) -> None:
        assert normalize_directive_id("DIRECTIVE_001") == "DIRECTIVE_001"

    def test_slug_with_three_digits(self) -> None:
        assert normalize_directive_id("024-locality-of-change") == "DIRECTIVE_024"

    def test_slug_with_single_digit(self) -> None:
        assert normalize_directive_id("3-short") == "DIRECTIVE_003"

    def test_slug_with_two_digits(self) -> None:
        assert normalize_directive_id("10-specification-fidelity-requirement") == "DIRECTIVE_010"

    def test_slug_with_four_digits(self) -> None:
        """Four-digit numbers are preserved (no truncation)."""
        assert normalize_directive_id("1234-future") == "DIRECTIVE_1234"

    def test_fallback_uppercase(self) -> None:
        assert normalize_directive_id("unknown-format") == "UNKNOWN-FORMAT"

    def test_empty_string(self) -> None:
        assert normalize_directive_id("") == ""

    def test_digits_only(self) -> None:
        """A bare number is treated as a slug with no trailing slug part."""
        assert normalize_directive_id("42") == "DIRECTIVE_042"


# ---------------------------------------------------------------------------
# directive_to_urn
# ---------------------------------------------------------------------------


class TestDirectiveToUrn:
    def test_slug_input(self) -> None:
        assert directive_to_urn("024-locality-of-change") == "directive:DIRECTIVE_024"

    def test_canonical_input(self) -> None:
        assert directive_to_urn("DIRECTIVE_024") == "directive:DIRECTIVE_024"

    def test_single_digit(self) -> None:
        assert directive_to_urn("3-short") == "directive:DIRECTIVE_003"


# ---------------------------------------------------------------------------
# artifact_to_urn
# ---------------------------------------------------------------------------


class TestArtifactToUrn:
    def test_directive_kind_normalises(self) -> None:
        assert artifact_to_urn("directive", "024-locality-of-change") == "directive:DIRECTIVE_024"

    def test_tactic_kind_passthrough(self) -> None:
        assert artifact_to_urn("tactic", "tdd-red-green-refactor") == "tactic:tdd-red-green-refactor"

    def test_paradigm_kind_passthrough(self) -> None:
        assert artifact_to_urn("paradigm", "domain-driven-design") == "paradigm:domain-driven-design"

    def test_styleguide_kind_passthrough(self) -> None:
        assert artifact_to_urn("styleguide", "kitty-glossary-writing") == "styleguide:kitty-glossary-writing"

    def test_toolguide_kind_passthrough(self) -> None:
        assert artifact_to_urn("toolguide", "efficient-local-tooling") == "toolguide:efficient-local-tooling"

    def test_procedure_kind_passthrough(self) -> None:
        assert artifact_to_urn("procedure", "refactoring") == "procedure:refactoring"

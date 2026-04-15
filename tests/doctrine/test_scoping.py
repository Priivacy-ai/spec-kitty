"""Tests for doctrine language-scoping helpers."""

import pytest

from doctrine.shared.scoping import applies_to_languages_match, normalize_languages

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


def test_normalize_languages_none_returns_empty_tuple() -> None:
    assert normalize_languages(None) == ()


def test_normalize_languages_deduplicates_and_skips_blanks() -> None:
    assert normalize_languages([" Python ", "", "python", "TypeScript"]) == (
        "python",
        "typescript",
    )


def test_applies_to_languages_match_rejects_scoped_artifact_for_explicit_empty_scope() -> None:
    assert applies_to_languages_match(["python"], ()) is False

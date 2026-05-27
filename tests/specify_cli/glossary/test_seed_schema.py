"""Tests for glossary seed file Pydantic models and error types."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from specify_cli.glossary.exceptions import (
    GlossaryError,
    SeedFileValidationError,
    SeedValidationError,
)
from specify_cli.glossary.seed_schema import GlossarySeedFile, GlossarySeedTerm


# ---------------------------------------------------------------------------
# GlossarySeedTerm
# ---------------------------------------------------------------------------


class TestGlossarySeedTermValid:
    """Happy-path tests for GlossarySeedTerm."""

    def test_all_fields_explicit(self) -> None:
        term = GlossarySeedTerm(
            surface="workspace",
            definition="A directory for code",
            confidence=0.9,
            status="active",
        )
        assert term.surface == "workspace"
        assert term.definition == "A directory for code"
        assert term.confidence == 0.9
        assert term.status == "active"

    def test_defaults_applied(self) -> None:
        term = GlossarySeedTerm(surface="lane", definition="A WP grouping")
        assert term.confidence == 1.0
        assert term.status == "draft"

    def test_boundary_confidence_zero(self) -> None:
        term = GlossarySeedTerm(
            surface="edge", definition="A graph edge", confidence=0.0
        )
        assert term.confidence == 0.0

    def test_boundary_confidence_one(self) -> None:
        term = GlossarySeedTerm(
            surface="edge", definition="A graph edge", confidence=1.0
        )
        assert term.confidence == 1.0

    def test_all_status_values(self) -> None:
        for status in ("active", "draft", "deprecated"):
            term = GlossarySeedTerm(
                surface="term", definition="A term", status=status
            )
            assert term.status == status

    def test_frozen(self) -> None:
        term = GlossarySeedTerm(surface="frozen", definition="Cannot mutate")
        with pytest.raises(ValidationError):
            term.surface = "changed"  # type: ignore[misc]


class TestGlossarySeedTermSurfaceValidation:
    """Surface normalization validator tests."""

    def test_empty_surface_rejected(self) -> None:
        with pytest.raises(ValidationError, match="surface must not be empty"):
            GlossarySeedTerm(surface="", definition="A definition")

    def test_uppercase_surface_rejected(self) -> None:
        with pytest.raises(ValidationError, match="surface must be normalized"):
            GlossarySeedTerm(surface="Sonar quality gate", definition="A gate")

    def test_leading_space_rejected(self) -> None:
        with pytest.raises(ValidationError, match="surface must be normalized"):
            GlossarySeedTerm(surface=" workspace", definition="A workspace")

    def test_trailing_space_rejected(self) -> None:
        with pytest.raises(ValidationError, match="surface must be normalized"):
            GlossarySeedTerm(surface="workspace ", definition="A workspace")

    def test_mixed_case_rejected(self) -> None:
        with pytest.raises(ValidationError, match="surface must be normalized"):
            GlossarySeedTerm(surface="myTerm", definition="A term")


class TestGlossarySeedTermDefinitionValidation:
    """Definition non-empty validator tests."""

    def test_empty_definition_rejected(self) -> None:
        with pytest.raises(ValidationError, match="definition must not be empty"):
            GlossarySeedTerm(surface="term", definition="")

    def test_whitespace_only_definition_rejected(self) -> None:
        with pytest.raises(ValidationError, match="definition must not be empty"):
            GlossarySeedTerm(surface="term", definition="   ")


class TestGlossarySeedTermConfidenceValidation:
    """Confidence range validator tests."""

    def test_negative_confidence_rejected(self) -> None:
        with pytest.raises(ValidationError, match="confidence must be 0.0..1.0"):
            GlossarySeedTerm(surface="term", definition="Def", confidence=-0.1)

    def test_over_one_confidence_rejected(self) -> None:
        with pytest.raises(ValidationError, match="confidence must be 0.0..1.0"):
            GlossarySeedTerm(surface="term", definition="Def", confidence=1.01)


class TestGlossarySeedTermStatusValidation:
    """Status enum validator tests."""

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GlossarySeedTerm(
                surface="term", definition="Def", status="archived"  # type: ignore[arg-type]
            )


class TestGlossarySeedTermExtraForbid:
    """extra='forbid' tests."""

    def test_unknown_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_field"):
            GlossarySeedTerm(
                surface="term",
                definition="Def",
                extra_field="nope",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# GlossarySeedFile
# ---------------------------------------------------------------------------


class TestGlossarySeedFileValid:
    """Happy-path tests for GlossarySeedFile."""

    def test_valid_file_with_terms(self) -> None:
        seed = GlossarySeedFile(
            terms=[
                GlossarySeedTerm(surface="alpha", definition="First letter"),
                GlossarySeedTerm(
                    surface="beta",
                    definition="Second letter",
                    confidence=0.8,
                    status="active",
                ),
            ]
        )
        assert len(seed.terms) == 2
        assert seed.terms[0].surface == "alpha"

    def test_empty_terms_list_allowed(self) -> None:
        seed = GlossarySeedFile(terms=[])
        assert seed.terms == []


class TestGlossarySeedFileValidation:
    """Validation tests for GlossarySeedFile."""

    def test_missing_terms_key_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GlossarySeedFile()  # type: ignore[call-arg]

    def test_unknown_field_at_root_rejected(self) -> None:
        with pytest.raises(ValidationError, match="bogus"):
            GlossarySeedFile(
                terms=[], bogus="nope"  # type: ignore[call-arg]
            )

    def test_multiple_invalid_terms_collected(self) -> None:
        """Pydantic collects errors from all invalid terms."""
        with pytest.raises(ValidationError) as exc_info:
            GlossarySeedFile(
                terms=[
                    {"surface": "UPPER", "definition": "bad"},  # type: ignore[list-item]
                    {"surface": "ok", "definition": ""},  # type: ignore[list-item]
                ]
            )
        errors = exc_info.value.errors()
        assert len(errors) >= 2


# ---------------------------------------------------------------------------
# SeedValidationError (frozen dataclass)
# ---------------------------------------------------------------------------


class TestSeedValidationError:
    """Tests for the SeedValidationError dataclass."""

    def test_construction(self) -> None:
        err = SeedValidationError(
            file_path=Path("glossary.yaml"),
            term_index=3,
            term_surface="workspace",
            field="confidence",
            message="must be 0.0..1.0",
        )
        assert err.file_path == Path("glossary.yaml")
        assert err.term_index == 3
        assert err.term_surface == "workspace"
        assert err.field == "confidence"
        assert err.message == "must be 0.0..1.0"

    def test_frozen(self) -> None:
        err = SeedValidationError(
            file_path=Path("f.yaml"),
            term_index=0,
            term_surface=None,
            field=None,
            message="oops",
        )
        with pytest.raises(AttributeError):
            err.message = "changed"  # type: ignore[misc]

    def test_none_fields(self) -> None:
        err = SeedValidationError(
            file_path=Path("f.yaml"),
            term_index=None,
            term_surface=None,
            field=None,
            message="file-level error",
        )
        assert err.term_index is None
        assert err.term_surface is None
        assert err.field is None


# ---------------------------------------------------------------------------
# SeedFileValidationError (exception)
# ---------------------------------------------------------------------------


class TestSeedFileValidationError:
    """Tests for the SeedFileValidationError exception."""

    def test_extends_glossary_error(self) -> None:
        err = SeedFileValidationError(
            file_path=Path("seed.yaml"),
            errors=[
                SeedValidationError(
                    file_path=Path("seed.yaml"),
                    term_index=0,
                    term_surface="test",
                    field="confidence",
                    message="out of range",
                )
            ],
        )
        assert isinstance(err, GlossaryError)

    def test_message_single_error(self) -> None:
        err = SeedFileValidationError(
            file_path=Path("seed.yaml"),
            errors=[
                SeedValidationError(
                    file_path=Path("seed.yaml"),
                    term_index=2,
                    term_surface="lane",
                    field="confidence",
                    message="must be 0.0..1.0",
                )
            ],
        )
        msg = str(err)
        assert "1 validation error(s) in seed.yaml" in msg
        assert "term[2] 'lane'" in msg
        assert "confidence" in msg
        assert "must be 0.0..1.0" in msg

    def test_message_multi_error(self) -> None:
        errors = [
            SeedValidationError(
                file_path=Path("s.yaml"),
                term_index=0,
                term_surface="Alpha",
                field="surface",
                message="must be normalized",
            ),
            SeedValidationError(
                file_path=Path("s.yaml"),
                term_index=1,
                term_surface=None,
                field=None,
                message="unknown field 'bogus'",
            ),
        ]
        err = SeedFileValidationError(file_path=Path("s.yaml"), errors=errors)
        msg = str(err)
        assert "2 validation error(s)" in msg
        assert "term[0] 'Alpha'" in msg
        assert "surface" in msg
        assert "term[1]" in msg

    def test_file_level_error_formatting(self) -> None:
        err = SeedFileValidationError(
            file_path=Path("bad.yaml"),
            errors=[
                SeedValidationError(
                    file_path=Path("bad.yaml"),
                    term_index=None,
                    term_surface=None,
                    field=None,
                    message="YAML parse error",
                )
            ],
        )
        msg = str(err)
        assert "file: YAML parse error" in msg

    def test_errors_attribute_accessible(self) -> None:
        errors = [
            SeedValidationError(
                file_path=Path("x.yaml"),
                term_index=0,
                term_surface="t",
                field="f",
                message="m",
            )
        ]
        err = SeedFileValidationError(file_path=Path("x.yaml"), errors=errors)
        assert err.errors == errors
        assert err.file_path == Path("x.yaml")

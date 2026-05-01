"""Unit tests for styleguide schema validation."""

from doctrine.styleguides.validation import validate_styleguide
import pytest

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


class TestValidateStyleguide:
    def test_valid_minimal_styleguide(self, sample_styleguide_data: dict) -> None:
        errors = validate_styleguide(sample_styleguide_data)
        assert errors == []

    def test_valid_enriched_styleguide(self, enriched_styleguide_data: dict) -> None:
        errors = validate_styleguide(enriched_styleguide_data)
        assert errors == []

    def test_missing_required_field(self) -> None:
        data = {"schema_version": "1.0", "id": "test"}
        errors = validate_styleguide(data)
        assert len(errors) > 0

    def test_invalid_scope_value(self, sample_styleguide_data: dict) -> None:
        sample_styleguide_data["scope"] = "invalid"
        errors = validate_styleguide(sample_styleguide_data)
        assert any("scope" in e for e in errors)

    def test_empty_principles_invalid(self) -> None:
        data = {
            "schema_version": "1.0",
            "id": "test",
            "title": "Test",
            "scope": "code",
            "principles": [],
        }
        errors = validate_styleguide(data)
        assert any("principles" in e for e in errors)

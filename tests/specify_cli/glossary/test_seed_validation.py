"""Tests for glossary seed file validation orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.glossary.exceptions import SeedFileValidationError
from specify_cli.glossary.scope import GlossaryScope
from specify_cli.glossary.seed_schema import GlossarySeedFile
from specify_cli.glossary.seed_validation import (
    VALID_SCOPE_FILENAMES,
    _translate_pydantic_errors,
    validate_scope_filename,
    validate_seed_file_data,
)

SEED_PATH = Path("/fake/glossary/seed.yaml")


# ---- validate_seed_file_data: success cases --------------------------------


class TestValidateSeedFileDataSuccess:
    """validate_seed_file_data returns GlossarySeedFile on valid input."""

    def test_valid_single_term(self) -> None:
        data = {
            "terms": [
                {
                    "surface": "worktree",
                    "definition": "A linked working tree.",
                }
            ]
        }
        result = validate_seed_file_data(data, SEED_PATH)
        assert isinstance(result, GlossarySeedFile)
        assert len(result.terms) == 1
        assert result.terms[0].surface == "worktree"

    def test_valid_multiple_terms(self) -> None:
        data = {
            "terms": [
                {"surface": "alpha", "definition": "First letter."},
                {
                    "surface": "beta",
                    "definition": "Second letter.",
                    "confidence": 0.8,
                    "status": "active",
                },
            ]
        }
        result = validate_seed_file_data(data, SEED_PATH)
        assert len(result.terms) == 2

    def test_valid_empty_terms_list(self) -> None:
        data = {"terms": []}
        result = validate_seed_file_data(data, SEED_PATH)
        assert isinstance(result, GlossarySeedFile)
        assert result.terms == []

    def test_valid_with_all_optional_fields(self) -> None:
        data = {
            "terms": [
                {
                    "surface": "lane",
                    "definition": "An execution lane.",
                    "confidence": 0.95,
                    "status": "deprecated",
                }
            ]
        }
        result = validate_seed_file_data(data, SEED_PATH)
        assert result.terms[0].confidence == 0.95
        assert result.terms[0].status == "deprecated"


# ---- validate_seed_file_data: failure cases ---------------------------------


class TestValidateSeedFileDataFailure:
    """validate_seed_file_data raises SeedFileValidationError on bad input."""

    def test_non_normalized_surface(self) -> None:
        data = {
            "terms": [
                {"surface": "WorkTree", "definition": "A linked tree."}
            ]
        }
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        err = exc_info.value
        assert err.file_path == SEED_PATH
        assert len(err.errors) >= 1
        e = err.errors[0]
        assert e.term_index == 0
        assert e.term_surface == "WorkTree"
        assert e.field == "surface"
        assert "normalized" in e.message.lower() or "lowercase" in e.message.lower()

    def test_empty_surface(self) -> None:
        data = {
            "terms": [{"surface": "", "definition": "Something."}]
        }
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        assert any(
            e.field == "surface" and e.term_index == 0
            for e in exc_info.value.errors
        )

    def test_empty_definition(self) -> None:
        data = {
            "terms": [{"surface": "foo", "definition": "   "}]
        }
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        assert any(
            e.field == "definition" and e.term_index == 0
            for e in exc_info.value.errors
        )

    def test_missing_terms_key(self) -> None:
        data: dict[str, object] = {}
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        assert len(exc_info.value.errors) >= 1
        e = exc_info.value.errors[0]
        assert e.field == "terms"
        assert e.term_index is None

    def test_non_mapping_root(self) -> None:
        """A list instead of a dict at the root should raise."""
        data = [{"surface": "x", "definition": "y"}]
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        assert len(exc_info.value.errors) >= 1

    def test_invalid_confidence(self) -> None:
        data = {
            "terms": [
                {"surface": "foo", "definition": "bar", "confidence": 2.0}
            ]
        }
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        assert any(
            e.field == "confidence" and e.term_index == 0
            for e in exc_info.value.errors
        )

    def test_invalid_status(self) -> None:
        data = {
            "terms": [
                {"surface": "foo", "definition": "bar", "status": "unknown"}
            ]
        }
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        assert any(
            e.field == "status" and e.term_index == 0
            for e in exc_info.value.errors
        )

    def test_extra_field_at_term_level(self) -> None:
        data = {
            "terms": [
                {
                    "surface": "foo",
                    "definition": "bar",
                    "bogus": True,
                }
            ]
        }
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        assert any(
            e.term_index == 0 for e in exc_info.value.errors
        )

    def test_multiple_errors_collected(self) -> None:
        """Multiple invalid terms should produce multiple errors."""
        data = {
            "terms": [
                {"surface": "Good", "definition": "ok"},  # bad: uppercase
                {"surface": "also Bad", "definition": "ok"},  # bad: uppercase + space
            ]
        }
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        errors = exc_info.value.errors
        assert len(errors) >= 2
        indices = {e.term_index for e in errors}
        assert 0 in indices
        assert 1 in indices

    def test_error_message_includes_all_errors(self) -> None:
        data = {
            "terms": [
                {"surface": "BAD", "definition": ""},
            ]
        }
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, SEED_PATH)

        msg = str(exc_info.value)
        assert "validation error" in msg.lower()

    def test_file_path_propagated(self) -> None:
        custom_path = Path("/custom/path/to/seed.yaml")
        data = {"terms": [{"surface": "BAD", "definition": "x"}]}
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file_data(data, custom_path)

        assert exc_info.value.file_path == custom_path
        assert all(e.file_path == custom_path for e in exc_info.value.errors)


# ---- validate_scope_filename ------------------------------------------------


class TestValidateScopeFilename:
    """validate_scope_filename maps known filenames to GlossaryScope."""

    def test_mission_local(self) -> None:
        assert validate_scope_filename(Path("mission_local.yaml")) == GlossaryScope.MISSION_LOCAL

    def test_team_domain(self) -> None:
        assert validate_scope_filename(Path("team_domain.yaml")) == GlossaryScope.TEAM_DOMAIN

    def test_audience_domain(self) -> None:
        assert validate_scope_filename(Path("audience_domain.yaml")) == GlossaryScope.AUDIENCE_DOMAIN

    def test_spec_kitty_core(self) -> None:
        assert validate_scope_filename(Path("spec_kitty_core.yaml")) == GlossaryScope.SPEC_KITTY_CORE

    def test_unknown_yaml(self) -> None:
        assert validate_scope_filename(Path("unknown.yaml")) is None

    def test_non_yaml_file(self) -> None:
        assert validate_scope_filename(Path("readme.md")) is None

    def test_path_with_directory(self) -> None:
        """Only the filename matters, not the directory."""
        assert (
            validate_scope_filename(Path("/some/dir/mission_local.yaml"))
            == GlossaryScope.MISSION_LOCAL
        )

    def test_yml_extension_not_matched(self) -> None:
        """Only .yaml extension is valid, not .yml."""
        assert validate_scope_filename(Path("mission_local.yml")) is None


# ---- VALID_SCOPE_FILENAMES --------------------------------------------------


class TestValidScopeFilenames:
    """VALID_SCOPE_FILENAMES dict covers all GlossaryScope members."""

    def test_all_scopes_present(self) -> None:
        for scope in GlossaryScope:
            key = f"{scope.value}.yaml"
            assert key in VALID_SCOPE_FILENAMES
            assert VALID_SCOPE_FILENAMES[key] is scope

    def test_no_extra_entries(self) -> None:
        assert len(VALID_SCOPE_FILENAMES) == len(GlossaryScope)


# ---- _translate_pydantic_errors (internal) ----------------------------------


class TestTranslatePydanticErrors:
    """_translate_pydantic_errors handles all Pydantic loc shapes."""

    def _make_validation_error(self, data: dict[str, object]) -> tuple[Exception, dict[str, object]]:
        """Try to validate data and return (exc, data) on failure."""
        from pydantic import ValidationError as PydanticValidationError

        from specify_cli.glossary.seed_schema import GlossarySeedFile

        try:
            GlossarySeedFile.model_validate(data)
        except PydanticValidationError as exc:
            return exc, data
        pytest.fail("Expected ValidationError")

    def test_field_level_error(self) -> None:
        """loc=("terms", 0, "surface") -> term_index=0, field="surface"."""
        data = {
            "terms": [{"surface": "BAD", "definition": "ok"}]
        }
        exc, raw = self._make_validation_error(data)
        errors = _translate_pydantic_errors(exc, raw, SEED_PATH)  # type: ignore[arg-type]

        assert len(errors) >= 1
        e = errors[0]
        assert e.term_index == 0
        assert e.field == "surface"
        assert e.term_surface == "BAD"

    def test_file_level_error(self) -> None:
        """loc=("terms",) -> term_index=None, field="terms"."""
        data: dict[str, object] = {}
        exc, raw = self._make_validation_error(data)
        errors = _translate_pydantic_errors(exc, raw, SEED_PATH)  # type: ignore[arg-type]

        assert len(errors) >= 1
        e = errors[0]
        assert e.term_index is None
        assert e.field == "terms"

    def test_term_surface_extracted_from_data(self) -> None:
        """term_surface comes from input data, not error message."""
        data = {
            "terms": [{"surface": "My Term", "definition": "ok"}]
        }
        exc, raw = self._make_validation_error(data)
        errors = _translate_pydantic_errors(exc, raw, SEED_PATH)  # type: ignore[arg-type]

        e = errors[0]
        assert e.term_surface == "My Term"

    def test_term_surface_none_when_missing(self) -> None:
        """If the term dict lacks surface, term_surface should be None."""
        data = {
            "terms": [{"definition": "ok"}]  # missing surface
        }
        exc, raw = self._make_validation_error(data)
        errors = _translate_pydantic_errors(exc, raw, SEED_PATH)  # type: ignore[arg-type]

        surface_errors = [e for e in errors if e.field == "surface"]
        if surface_errors:
            assert surface_errors[0].term_surface is None

    def test_multiple_term_errors(self) -> None:
        """Multiple terms with errors produce distinct records."""
        data = {
            "terms": [
                {"surface": "BAD1", "definition": "ok"},
                {"surface": "BAD2", "definition": "ok"},
            ]
        }
        exc, raw = self._make_validation_error(data)
        errors = _translate_pydantic_errors(exc, raw, SEED_PATH)  # type: ignore[arg-type]

        assert len(errors) >= 2
        indices = {e.term_index for e in errors}
        assert 0 in indices
        assert 1 in indices

    def test_extra_field_error(self) -> None:
        """Extra fields at term level produce errors with term_index."""
        data = {
            "terms": [
                {"surface": "foo", "definition": "bar", "bogus": 1}
            ]
        }
        exc, raw = self._make_validation_error(data)
        errors = _translate_pydantic_errors(exc, raw, SEED_PATH)  # type: ignore[arg-type]

        assert len(errors) >= 1
        assert errors[0].term_index == 0

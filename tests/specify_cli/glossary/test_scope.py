"""Tests for scope.py — load_seed_file / save_seed_file with Pydantic validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.glossary.exceptions import (
    GlossaryError,
    SeedFileValidationError,
)
from specify_cli.glossary.models import SenseStatus, TermSense, TermSurface, Provenance
from specify_cli.glossary.scope import (
    GlossaryScope,
    load_seed_file,
    save_seed_file,
    validate_seed_file,
)

from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SEED_YAML = """\
# Spec Kitty glossary seed — scope: spec_kitty_core

terms:

  - surface: workspace
    definition: A user-owned container for projects
    confidence: 1.0
    status: active

  - surface: mission
    definition: A unit of planned work
    confidence: 0.9
    status: draft
"""

INVALID_SURFACE_YAML = """\
terms:

  - surface: Work Space
    definition: Something
    confidence: 1.0
    status: active
"""

MISSING_TERMS_YAML = """\
not_terms:
  - foo: bar
"""

EMPTY_DEFINITION_YAML = """\
terms:

  - surface: widget
    definition: "   "
    confidence: 1.0
    status: active
"""

BAD_CONFIDENCE_YAML = """\
terms:

  - surface: widget
    definition: A widget
    confidence: 5.0
    status: active
"""


def _write_seed(tmp_path: Path, scope: GlossaryScope, content: str) -> Path:
    seed_dir = tmp_path / ".kittify" / "glossaries"
    seed_dir.mkdir(parents=True, exist_ok=True)
    seed_path = seed_dir / f"{scope.value}.yaml"
    seed_path.write_text(content, encoding="utf-8")
    return seed_path


def _make_sense(
    surface: str = "workspace",
    definition: str = "A user-owned container",
    confidence: float = 1.0,
    status: SenseStatus = SenseStatus.ACTIVE,
) -> TermSense:
    return TermSense(
        surface=TermSurface(surface),
        scope=GlossaryScope.SPEC_KITTY_CORE.value,
        definition=definition,
        provenance=Provenance(
            actor_id="system:test",
            timestamp=datetime.now(),
            source="test",
        ),
        confidence=confidence,
        status=status,
    )


# ---------------------------------------------------------------------------
# validate_seed_file (T011)
# ---------------------------------------------------------------------------


class TestValidateSeedFile:
    """Test the updated validate_seed_file() delegation."""

    def test_valid_data_passes(self) -> None:
        data = {
            "terms": [
                {"surface": "workspace", "definition": "A container", "confidence": 1.0, "status": "active"},
            ]
        }
        # Should not raise
        validate_seed_file(data)

    def test_invalid_data_raises_seed_file_validation_error(self) -> None:
        data = {"terms": [{"surface": "Work Space", "definition": "A thing"}]}
        with pytest.raises(SeedFileValidationError):
            validate_seed_file(data)

    def test_missing_terms_raises_seed_file_validation_error(self) -> None:
        data = {"not_terms": []}
        with pytest.raises(SeedFileValidationError):
            validate_seed_file(data)

    def test_file_path_param_backward_compat(self) -> None:
        """Calling w/o file_path still works (uses placeholder)."""
        data = {"terms": [{"surface": "Bad Surface", "definition": "x"}]}
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file(data)
        assert "<unknown>" in str(exc_info.value.file_path)

    def test_file_path_param_forwarded(self) -> None:
        """Calling w/ file_path passes it through to error."""
        data = {"terms": [{"surface": "Bad Surface", "definition": "x"}]}
        p = Path("/my/seed.yaml")
        with pytest.raises(SeedFileValidationError) as exc_info:
            validate_seed_file(data, file_path=p)
        assert exc_info.value.file_path == p

    def test_is_glossary_error_subclass(self) -> None:
        """SeedFileValidationError caught by except GlossaryError."""
        data = {"terms": [{"surface": "Not Normalized", "definition": "x"}]}
        with pytest.raises(GlossaryError):
            validate_seed_file(data)


# ---------------------------------------------------------------------------
# load_seed_file (T012)
# ---------------------------------------------------------------------------


class TestLoadSeedFile:
    """Test load_seed_file with Pydantic validation."""

    def test_valid_file_loads_senses(self, tmp_path: Path) -> None:
        _write_seed(tmp_path, GlossaryScope.SPEC_KITTY_CORE, VALID_SEED_YAML)
        senses = load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)
        assert len(senses) == 2
        assert senses[0].surface.surface_text == "workspace"
        assert senses[0].definition == "A user-owned container for projects"
        assert senses[0].confidence == 1.0
        assert senses[0].status == SenseStatus.ACTIVE
        assert senses[1].surface.surface_text == "mission"
        assert senses[1].status == SenseStatus.DRAFT

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)
        assert result == []

    def test_non_normalized_surface_raises_seed_file_validation_error(
        self, tmp_path: Path
    ) -> None:
        """Previously raised ValueError; now raises SeedFileValidationError."""
        _write_seed(tmp_path, GlossaryScope.SPEC_KITTY_CORE, INVALID_SURFACE_YAML)
        with pytest.raises(SeedFileValidationError) as exc_info:
            load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)
        assert len(exc_info.value.errors) >= 1
        assert "normalized" in str(exc_info.value).lower()

    def test_missing_terms_key_raises_seed_file_validation_error(
        self, tmp_path: Path
    ) -> None:
        _write_seed(tmp_path, GlossaryScope.SPEC_KITTY_CORE, MISSING_TERMS_YAML)
        with pytest.raises(SeedFileValidationError):
            load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)

    def test_empty_definition_raises_seed_file_validation_error(
        self, tmp_path: Path
    ) -> None:
        _write_seed(tmp_path, GlossaryScope.SPEC_KITTY_CORE, EMPTY_DEFINITION_YAML)
        with pytest.raises(SeedFileValidationError):
            load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)

    def test_bad_confidence_raises_seed_file_validation_error(
        self, tmp_path: Path
    ) -> None:
        _write_seed(tmp_path, GlossaryScope.SPEC_KITTY_CORE, BAD_CONFIDENCE_YAML)
        with pytest.raises(SeedFileValidationError):
            load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)

    def test_error_includes_file_path(self, tmp_path: Path) -> None:
        _write_seed(tmp_path, GlossaryScope.SPEC_KITTY_CORE, INVALID_SURFACE_YAML)
        with pytest.raises(SeedFileValidationError) as exc_info:
            load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)
        assert "spec_kitty_core.yaml" in str(exc_info.value.file_path)

    def test_validation_before_term_surface_construction(
        self, tmp_path: Path
    ) -> None:
        """Pydantic validates BEFORE TermSurface() is constructed, so the
        error type is SeedFileValidationError, not ValueError."""
        _write_seed(tmp_path, GlossaryScope.SPEC_KITTY_CORE, INVALID_SURFACE_YAML)
        # Specifically check it's NOT a ValueError
        with pytest.raises(SeedFileValidationError):
            load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)

    def test_caught_by_glossary_error(self, tmp_path: Path) -> None:
        """Backward compat: code catching GlossaryError still catches validation errors."""
        _write_seed(tmp_path, GlossaryScope.SPEC_KITTY_CORE, INVALID_SURFACE_YAML)
        with pytest.raises(GlossaryError):
            load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)


# ---------------------------------------------------------------------------
# save_seed_file (T013)
# ---------------------------------------------------------------------------


class TestSaveSeedFile:
    """Test save_seed_file with Pydantic validation."""

    def test_valid_terms_written(self, tmp_path: Path) -> None:
        terms = [
            _make_sense("workspace", "A container", 1.0, SenseStatus.ACTIVE),
            _make_sense("mission", "A unit of work", 0.9, SenseStatus.DRAFT),
        ]
        save_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path, terms)
        seed_path = tmp_path / ".kittify" / "glossaries" / "spec_kitty_core.yaml"
        assert seed_path.exists()
        content = seed_path.read_text(encoding="utf-8")
        assert "workspace" in content
        assert "mission" in content

    def test_roundtrip(self, tmp_path: Path) -> None:
        """save then load returns equivalent data."""
        terms = [_make_sense("alpha", "First letter", 0.8, SenseStatus.DRAFT)]
        save_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path, terms)
        loaded = load_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path)
        assert len(loaded) == 1
        assert loaded[0].surface.surface_text == "alpha"
        assert loaded[0].definition == "First letter"
        assert loaded[0].confidence == 0.8
        assert loaded[0].status == SenseStatus.DRAFT

    def test_empty_list_written(self, tmp_path: Path) -> None:
        save_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path, [])
        seed_path = tmp_path / ".kittify" / "glossaries" / "spec_kitty_core.yaml"
        assert seed_path.exists()
        content = seed_path.read_text(encoding="utf-8")
        assert "terms: []" in content

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        terms = [_make_sense()]
        save_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path, terms)
        assert (tmp_path / ".kittify" / "glossaries" / "spec_kitty_core.yaml").exists()

    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        terms = [
            _make_sense("zebra", "Last letter animal"),
            _make_sense("alpha", "First letter"),
        ]
        save_seed_file(GlossaryScope.SPEC_KITTY_CORE, tmp_path, terms)
        content = (
            tmp_path / ".kittify" / "glossaries" / "spec_kitty_core.yaml"
        ).read_text(encoding="utf-8")
        alpha_pos = content.index("alpha")
        zebra_pos = content.index("zebra")
        assert alpha_pos < zebra_pos

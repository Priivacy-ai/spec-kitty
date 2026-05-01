"""Unit tests for doc_state.py — iteration mode and Divio type validation.

Covers set_iteration_mode() and set_divio_types_selected() with valid inputs,
invalid inputs, and missing-key initialisation of documentation_state.
All tests use tmp_path (no real project required).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.doc_state import set_divio_types_selected, set_iteration_mode

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_VALID_META_BASE: dict = {
    "feature_number": "001",
    "slug": "001-test",
    "mission_slug": "001-test",
    "friendly_name": "Test Feature",
    "mission": "documentation",
    "target_branch": "main",
    "created_at": "2026-01-01T00:00:00+00:00",
}


def _make_meta(path: Path, extra: dict | None = None) -> Path:
    """Write a valid meta.json to *path* and return the Path."""
    data: dict = {**_VALID_META_BASE}
    if extra:
        data.update(extra)
    meta = path / "meta.json"
    meta.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return meta


# ---------------------------------------------------------------------------
# set_iteration_mode
# ---------------------------------------------------------------------------


class TestSetIterationMode:
    """set_iteration_mode() stores valid modes and rejects invalid ones."""

    def test_sets_initial_mode(self, tmp_path: Path) -> None:
        """'initial' is written into documentation_state.iteration_mode."""
        # Arrange
        meta = _make_meta(tmp_path)

        # Assumption check
        assert "documentation_state" not in json.loads(meta.read_text())

        # Act
        set_iteration_mode(meta, "initial")

        # Assert
        stored = json.loads(meta.read_text())
        assert stored["documentation_state"]["iteration_mode"] == "initial"

    def test_sets_gap_filling_mode(self, tmp_path: Path) -> None:
        """'gap_filling' is accepted and stored correctly."""
        # Arrange
        meta = _make_meta(tmp_path)

        # Assumption check
        assert meta.exists()

        # Act
        set_iteration_mode(meta, "gap_filling")

        # Assert
        stored = json.loads(meta.read_text())
        assert stored["documentation_state"]["iteration_mode"] == "gap_filling"

    def test_sets_feature_specific_mode(self, tmp_path: Path) -> None:
        """'feature_specific' is accepted and stored correctly."""
        # Arrange
        meta = _make_meta(tmp_path)

        # Assumption check
        assert meta.exists()

        # Act
        set_iteration_mode(meta, "feature_specific")

        # Assert
        stored = json.loads(meta.read_text())
        assert stored["documentation_state"]["iteration_mode"] == "feature_specific"

    def test_overwrites_existing_mode(self, tmp_path: Path) -> None:
        """A second call overwrites the previously stored mode."""
        # Arrange
        meta = _make_meta(tmp_path)
        set_iteration_mode(meta, "initial")

        # Assumption check
        assert json.loads(meta.read_text())["documentation_state"]["iteration_mode"] == "initial"

        # Act
        set_iteration_mode(meta, "gap_filling")

        # Assert
        stored = json.loads(meta.read_text())
        assert stored["documentation_state"]["iteration_mode"] == "gap_filling"

    def test_initialises_documentation_state_key(self, tmp_path: Path) -> None:
        """documentation_state is auto-created when absent from meta.json."""
        # Arrange
        meta = _make_meta(tmp_path)

        # Assumption check
        assert "documentation_state" not in json.loads(meta.read_text())

        # Act
        set_iteration_mode(meta, "initial")

        # Assert
        stored = json.loads(meta.read_text())
        assert "documentation_state" in stored

    def test_rejects_invalid_mode(self, tmp_path: Path) -> None:
        """An invalid iteration_mode string raises ValueError."""
        # Arrange
        meta = _make_meta(tmp_path)

        # Assumption check
        assert meta.exists()

        # Act / Assert
        with pytest.raises(ValueError, match="Invalid iteration_mode"):
            set_iteration_mode(meta, "bogus")  # type: ignore[arg-type]

    def test_missing_meta_file_raises(self, tmp_path: Path) -> None:
        """FileNotFoundError is raised when meta.json does not exist."""
        # Arrange
        meta = tmp_path / "meta.json"

        # Assumption check
        assert not meta.exists()

        # Act / Assert
        with pytest.raises(FileNotFoundError):
            set_iteration_mode(meta, "initial")


# ---------------------------------------------------------------------------
# set_divio_types_selected
# ---------------------------------------------------------------------------


class TestSetDivioTypesSelected:
    """set_divio_types_selected() stores valid Divio types and rejects invalid ones."""

    def test_sets_all_four_types(self, tmp_path: Path) -> None:
        """All four Divio types are stored as a list."""
        # Arrange
        meta = _make_meta(tmp_path)
        all_types = ["tutorial", "how-to", "reference", "explanation"]

        # Assumption check
        assert meta.exists()

        # Act
        set_divio_types_selected(meta, all_types)

        # Assert
        stored = json.loads(meta.read_text())
        assert stored["documentation_state"]["divio_types_selected"] == all_types

    def test_sets_single_type(self, tmp_path: Path) -> None:
        """A list with one Divio type is stored correctly."""
        # Arrange
        meta = _make_meta(tmp_path)

        # Assumption check
        assert meta.exists()

        # Act
        set_divio_types_selected(meta, ["reference"])

        # Assert
        stored = json.loads(meta.read_text())
        assert stored["documentation_state"]["divio_types_selected"] == ["reference"]

    def test_rejects_invalid_type(self, tmp_path: Path) -> None:
        """An unrecognised Divio type raises ValueError."""
        # Arrange
        meta = _make_meta(tmp_path)

        # Assumption check
        assert meta.exists()

        # Act / Assert
        with pytest.raises(ValueError, match="Invalid Divio types"):
            set_divio_types_selected(meta, ["tutorial", "unknown-type"])

    def test_preserves_existing_meta_fields(self, tmp_path: Path) -> None:
        """Other meta.json fields are not clobbered when writing Divio types."""
        # Arrange
        meta = _make_meta(tmp_path, extra={"custom_field": "preserve-me"})

        # Assumption check
        assert json.loads(meta.read_text())["custom_field"] == "preserve-me"

        # Act
        set_divio_types_selected(meta, ["how-to"])

        # Assert
        stored = json.loads(meta.read_text())
        assert stored["custom_field"] == "preserve-me"
        assert stored["documentation_state"]["divio_types_selected"] == ["how-to"]

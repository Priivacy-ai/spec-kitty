"""Tests for doc_state formatting consistency after migration to feature_metadata I/O.

Verifies that all doc_state write functions produce the standard meta.json format:
- Sorted keys
- ensure_ascii=False (Unicode preserved)
- Trailing newline
- Unknown fields preserved
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.doc_state import (
    ensure_documentation_state,
    initialize_documentation_state,
    set_audit_metadata,
    set_divio_types_selected,
    set_generators_configured,
    set_iteration_mode,
    update_documentation_state,
    write_documentation_state,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_META_BASE: dict = {
    "feature_number": "001",
    "slug": "001-test",
    "mission_slug": "001-test",
    "friendly_name": "Test",
    "mission_type": "documentation",
    "target_branch": "main",
    "created_at": "2026-01-01T00:00:00+00:00",
}


def _write_meta(directory: Path, extra: dict | None = None) -> Path:
    """Write a valid meta.json with all required fields."""
    data = {**_VALID_META_BASE}
    if extra:
        data.update(extra)
    meta_file = directory / "meta.json"
    meta_file.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta_file


def _assert_standard_format(meta_file: Path) -> dict:
    """Assert meta.json matches the standard format and return parsed data."""
    content = meta_file.read_text(encoding="utf-8")

    # Trailing newline
    assert content.endswith("\n"), "meta.json must end with a trailing newline"

    # Valid JSON
    parsed = json.loads(content)

    # Sorted keys (top-level)
    keys = list(parsed.keys())
    assert keys == sorted(keys), f"Top-level keys not sorted: {keys}"

    # 2-space indentation (check for "  " prefix on second line)
    lines = content.strip().split("\n")
    if len(lines) > 1:
        assert lines[1].startswith("  "), "Expected 2-space indentation"

    # Re-serialize with standard format and compare
    expected = json.dumps(parsed, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    assert content == expected, "File content does not match standard serialization"

    return parsed


# ---------------------------------------------------------------------------
# Individual field setters produce standard format
# ---------------------------------------------------------------------------


class TestSetIterationModeFormat:
    """set_iteration_mode() produces standard meta.json format."""

    def test_sorted_keys_and_trailing_newline(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path)
        set_iteration_mode(meta_file, "gap_filling")
        parsed = _assert_standard_format(meta_file)
        assert parsed["documentation_state"]["iteration_mode"] == "gap_filling"

    def test_unicode_preserved(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path, extra={"friendly_name": "Dokumentation"})
        set_iteration_mode(meta_file, "initial")
        parsed = _assert_standard_format(meta_file)
        assert parsed["friendly_name"] == "Dokumentation"


class TestSetDivioTypesFormat:
    """set_divio_types_selected() produces standard meta.json format."""

    def test_sorted_keys_and_trailing_newline(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path)
        set_divio_types_selected(meta_file, ["tutorial", "how-to"])
        parsed = _assert_standard_format(meta_file)
        assert parsed["documentation_state"]["divio_types_selected"] == [
            "tutorial",
            "how-to",
        ]


class TestSetGeneratorsFormat:
    """set_generators_configured() produces standard meta.json format."""

    def test_sorted_keys_and_trailing_newline(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path)
        generators = [{"name": "sphinx", "language": "python", "config_path": "docs/conf.py"}]
        set_generators_configured(meta_file, generators)
        parsed = _assert_standard_format(meta_file)
        assert len(parsed["documentation_state"]["generators_configured"]) == 1


class TestSetAuditMetadataFormat:
    """set_audit_metadata() produces standard meta.json format."""

    def test_sorted_keys_and_trailing_newline(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path)
        audit_date = datetime(2026, 3, 15, 12, 0, 0)
        set_audit_metadata(meta_file, audit_date, 0.85)
        parsed = _assert_standard_format(meta_file)
        assert parsed["documentation_state"]["coverage_percentage"] == 0.85


# ---------------------------------------------------------------------------
# Composite writers produce standard format
# ---------------------------------------------------------------------------


class TestWriteDocumentationStateFormat:
    """write_documentation_state() produces standard meta.json format."""

    def test_sorted_keys_and_trailing_newline(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path)
        state = {
            "iteration_mode": "initial",
            "divio_types_selected": ["tutorial"],
            "generators_configured": [],
            "target_audience": "developers",
            "last_audit_date": None,
            "coverage_percentage": 0.0,
        }
        write_documentation_state(meta_file, state)
        _assert_standard_format(meta_file)


class TestInitializeDocumentationStateFormat:
    """initialize_documentation_state() produces standard meta.json format."""

    def test_sorted_keys_and_trailing_newline(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path)
        initialize_documentation_state(
            meta_file,
            iteration_mode="initial",
            divio_types=["reference"],
            generators=[],
            target_audience="developers",
        )
        _assert_standard_format(meta_file)


class TestUpdateDocumentationStateFormat:
    """update_documentation_state() produces standard meta.json format."""

    def test_sorted_keys_and_trailing_newline(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path)
        initialize_documentation_state(
            meta_file,
            iteration_mode="initial",
            divio_types=[],
            generators=[],
            target_audience="developers",
        )
        update_documentation_state(meta_file, iteration_mode="gap_filling")
        _assert_standard_format(meta_file)


class TestEnsureDocumentationStateFormat:
    """ensure_documentation_state() produces standard meta.json format."""

    def test_sorted_keys_and_trailing_newline(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path)
        ensure_documentation_state(meta_file)
        _assert_standard_format(meta_file)

    def test_skips_non_doc_mission(self, tmp_path: Path) -> None:
        """Non-documentation missions are not modified."""
        meta_file = _write_meta(tmp_path, extra={"mission_type": "software-dev"})
        content_before = meta_file.read_text()
        ensure_documentation_state(meta_file)
        content_after = meta_file.read_text()
        assert content_before == content_after


# ---------------------------------------------------------------------------
# Cross-cutting formatting guarantees
# ---------------------------------------------------------------------------


class TestAllSettersProduceSortedKeys:
    """Every doc_state write function produces sorted keys in meta.json."""

    def test_all_setters_sorted(self, tmp_path: Path) -> None:
        """Call each setter and verify sorted keys after each."""
        meta_file = _write_meta(tmp_path)

        # set_iteration_mode
        set_iteration_mode(meta_file, "initial")
        _assert_standard_format(meta_file)

        # set_divio_types_selected
        set_divio_types_selected(meta_file, ["tutorial"])
        _assert_standard_format(meta_file)

        # set_generators_configured
        set_generators_configured(
            meta_file,
            [{"name": "sphinx", "language": "python", "config_path": "docs/conf.py"}],
        )
        _assert_standard_format(meta_file)

        # set_audit_metadata
        set_audit_metadata(meta_file, datetime(2026, 1, 1), 0.5)
        _assert_standard_format(meta_file)

        # write_documentation_state (full state)
        state = {
            "iteration_mode": "gap_filling",
            "divio_types_selected": ["tutorial", "reference"],
            "generators_configured": [],
            "target_audience": "end-users",
            "last_audit_date": None,
            "coverage_percentage": 0.75,
        }
        write_documentation_state(meta_file, state)
        _assert_standard_format(meta_file)

        # ensure_documentation_state (already has state, no-op)
        ensure_documentation_state(meta_file)
        _assert_standard_format(meta_file)


class TestDocStatePreservesUnknownFields:
    """doc_state writes don't strip unknown meta.json fields."""

    def test_set_iteration_mode_preserves_custom(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path, extra={"custom_field": "preserved"})
        set_iteration_mode(meta_file, "initial")
        parsed = _assert_standard_format(meta_file)
        assert parsed["custom_field"] == "preserved"

    def test_write_documentation_state_preserves_custom(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path, extra={"extra_key": 42})
        state = {
            "iteration_mode": "initial",
            "divio_types_selected": [],
            "generators_configured": [],
            "target_audience": "developers",
            "last_audit_date": None,
            "coverage_percentage": 0.0,
        }
        write_documentation_state(meta_file, state)
        parsed = _assert_standard_format(meta_file)
        assert parsed["extra_key"] == 42

    def test_ensure_documentation_state_preserves_custom(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path, extra={"vendor_metadata": {"x": 1}})
        ensure_documentation_state(meta_file)
        parsed = _assert_standard_format(meta_file)
        assert parsed["vendor_metadata"] == {"x": 1}

    def test_initialize_preserves_custom(self, tmp_path: Path) -> None:
        meta_file = _write_meta(tmp_path, extra={"my_tag": "keep"})
        initialize_documentation_state(
            meta_file,
            iteration_mode="initial",
            divio_types=[],
            generators=[],
            target_audience="developers",
        )
        parsed = _assert_standard_format(meta_file)
        assert parsed["my_tag"] == "keep"


class TestTolerantWriteWithMinimalMeta:
    """doc_state writes must tolerate meta.json missing required top-level fields.

    During documentation mission setup, meta.json may only contain
    ``{"mission": "documentation"}`` without feature_number, slug, etc.
    The old code was tolerant of this; the new code must remain so.
    """

    def test_set_iteration_mode_minimal_meta(self, tmp_path: Path) -> None:
        """set_iteration_mode works with a meta.json lacking required top-level fields."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text(json.dumps({"mission_type": "documentation"}, indent=2) + "\n")
        set_iteration_mode(meta_file, "initial")
        parsed = json.loads(meta_file.read_text())
        assert parsed["documentation_state"]["iteration_mode"] == "initial"

    def test_write_documentation_state_minimal_meta(self, tmp_path: Path) -> None:
        """write_documentation_state works with a meta.json lacking top-level fields."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text(json.dumps({"mission_type": "documentation"}, indent=2) + "\n")
        state = {
            "iteration_mode": "initial",
            "divio_types_selected": [],
            "generators_configured": [],
            "target_audience": "developers",
            "last_audit_date": None,
            "coverage_percentage": 0.0,
        }
        write_documentation_state(meta_file, state)
        parsed = json.loads(meta_file.read_text())
        assert parsed["documentation_state"]["iteration_mode"] == "initial"

    def test_ensure_documentation_state_minimal_meta(self, tmp_path: Path) -> None:
        """ensure_documentation_state works with a meta.json lacking top-level fields."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text(json.dumps({"mission_type": "documentation"}, indent=2) + "\n")
        ensure_documentation_state(meta_file)
        parsed = json.loads(meta_file.read_text())
        assert "documentation_state" in parsed
        assert parsed["documentation_state"]["iteration_mode"] == "initial"


class TestNoDirectJsonDumpRemains:
    """Smoke test: verify doc_state module has no direct json.dump write calls."""

    def test_no_json_dump_calls(self) -> None:
        """doc_state.py should not use json.dump() for writes (uses write_meta).

        Note: json.load() is still used in read_documentation_state() -- that is
        intentional.  This WP only migrates the *write* path.
        """
        import inspect
        import specify_cli.doc_state as mod

        source = inspect.getsource(mod)
        # Write calls should go through write_meta(validate=False), not json.dump
        assert "json.dump(" not in source, "Found json.dump() call in doc_state.py"

    def test_no_private_atomic_write_import(self) -> None:
        """doc_state.py must not import private _atomic_write from feature_metadata."""
        import inspect
        import specify_cli.doc_state as mod

        source = inspect.getsource(mod)
        assert "_atomic_write" not in source, "Found _atomic_write reference in doc_state.py; use write_meta(validate=False) instead"

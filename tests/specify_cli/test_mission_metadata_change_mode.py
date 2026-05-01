"""Tests for the change_mode field in mission metadata."""

from __future__ import annotations


import pytest

from specify_cli.mission_metadata import (
    get_change_mode,
    load_meta,
    set_change_mode,
    validate_meta,
    write_meta,
)


def _minimal_meta() -> dict:
    """Return a minimal valid meta dict with all required fields."""
    return {
        "slug": "test-feature",
        "mission_slug": "test-feature",
        "friendly_name": "Test Feature",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-04-13T00:00:00+00:00",
    }


def _write_minimal_meta(feature_dir, extra=None):
    """Write a minimal valid meta.json, optionally merging *extra* keys."""
    meta = _minimal_meta()
    if extra:
        meta.update(extra)
    feature_dir.mkdir(parents=True, exist_ok=True)
    write_meta(feature_dir, meta)
    return meta


# ── validate_meta ────────────────────────────────────────────────────────


def test_validate_meta_without_change_mode_passes():
    meta = _minimal_meta()
    errors = validate_meta(meta)
    assert errors == []


def test_validate_meta_with_bulk_edit_passes():
    meta = _minimal_meta()
    meta["change_mode"] = "bulk_edit"
    errors = validate_meta(meta)
    assert errors == []


def test_validate_meta_with_invalid_change_mode_fails():
    meta = _minimal_meta()
    meta["change_mode"] = "yolo"
    errors = validate_meta(meta)
    assert len(errors) == 1
    assert "Invalid change_mode" in errors[0]
    assert "'yolo'" in errors[0]


# ── set_change_mode ──────────────────────────────────────────────────────


def test_set_change_mode_bulk_edit(tmp_path):
    _write_minimal_meta(tmp_path)
    result = set_change_mode(tmp_path, "bulk_edit")
    assert result["change_mode"] == "bulk_edit"
    # Round-trip: reload from disk
    reloaded = load_meta(tmp_path)
    assert reloaded["change_mode"] == "bulk_edit"


def test_set_change_mode_invalid_raises(tmp_path):
    _write_minimal_meta(tmp_path)
    with pytest.raises(ValueError, match="Invalid change_mode"):
        set_change_mode(tmp_path, "nope")


def test_set_change_mode_missing_meta_raises(tmp_path):
    # No meta.json on disk at all
    with pytest.raises(FileNotFoundError):
        set_change_mode(tmp_path, "bulk_edit")


# ── get_change_mode ──────────────────────────────────────────────────────


def test_get_change_mode_absent_returns_none(tmp_path):
    _write_minimal_meta(tmp_path)
    assert get_change_mode(tmp_path) is None


def test_get_change_mode_present_returns_value(tmp_path):
    _write_minimal_meta(tmp_path, extra={"change_mode": "bulk_edit"})
    assert get_change_mode(tmp_path) == "bulk_edit"


# ── round-trip preservation ──────────────────────────────────────────────


def test_change_mode_preserved_through_write_meta(tmp_path):
    """Ensure change_mode survives a write_meta round-trip without being dropped."""
    meta = _minimal_meta()
    meta["change_mode"] = "bulk_edit"
    tmp_path.mkdir(parents=True, exist_ok=True)
    write_meta(tmp_path, meta)

    reloaded = load_meta(tmp_path)
    assert reloaded["change_mode"] == "bulk_edit"

    # Write again (simulating another mutation) and verify persistence
    reloaded["target_branch"] = "develop"
    write_meta(tmp_path, reloaded)
    final = load_meta(tmp_path)
    assert final["change_mode"] == "bulk_edit"
    assert final["target_branch"] == "develop"

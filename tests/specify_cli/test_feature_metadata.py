"""Comprehensive unit tests for specify_cli.feature_metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from specify_cli.feature_metadata import (
    HISTORY_CAP,
    REQUIRED_FIELDS,
    _atomic_write,
    finalize_merge,
    load_meta,
    record_acceptance,
    record_merge,
    set_documentation_state,
    set_target_branch,
    set_vcs_lock,
    validate_meta,
    write_meta,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_meta() -> dict[str, Any]:
    """Return a minimal valid meta dict with all required fields."""
    return {
        "feature_number": "051",
        "slug": "051-canonical-state-authority",
        "feature_slug": "051-canonical-state-authority",
        "friendly_name": "Canonical State Authority",
        "mission": "software-dev",
        "target_branch": "main",
        "created_at": "2026-03-18T00:00:00+00:00",
    }


def _write_meta_file(feature_dir: Path, meta: dict[str, Any]) -> Path:
    """Write a meta.json file to *feature_dir* and return the path."""
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return meta_path


# ===================================================================
# load_meta tests
# ===================================================================


class TestLoadMeta:
    """Tests for load_meta()."""

    def test_load_valid(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        _write_meta_file(tmp_path, meta)
        result = load_meta(tmp_path)
        assert result == meta

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        result = load_meta(tmp_path)
        assert result is None

    def test_load_malformed_json_raises_valueerror(self, tmp_path: Path) -> None:
        meta_path = tmp_path / "meta.json"
        meta_path.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(ValueError, match="Malformed JSON"):
            load_meta(tmp_path)


# ===================================================================
# validate_meta tests
# ===================================================================


class TestValidateMeta:
    """Tests for validate_meta()."""

    def test_valid_meta_no_errors(self) -> None:
        errors = validate_meta(_minimal_meta())
        assert errors == []

    def test_missing_feature_number(self) -> None:
        meta = _minimal_meta()
        del meta["feature_number"]
        errors = validate_meta(meta)
        assert len(errors) == 1
        assert "feature_number" in errors[0]

    def test_empty_field_is_error(self) -> None:
        meta = _minimal_meta()
        meta["slug"] = ""
        errors = validate_meta(meta)
        assert any("slug" in e for e in errors)

    def test_missing_multiple_required_fields(self) -> None:
        meta = _minimal_meta()
        del meta["feature_number"]
        del meta["slug"]
        del meta["mission"]
        errors = validate_meta(meta)
        assert len(errors) == 3

    def test_unknown_fields_no_errors(self) -> None:
        meta = _minimal_meta()
        meta["custom_field"] = "hello"
        meta["another_unknown"] = 42
        errors = validate_meta(meta)
        assert errors == []

    def test_required_fields_constant(self) -> None:
        expected = {
            "feature_number",
            "slug",
            "feature_slug",
            "friendly_name",
            "mission",
            "target_branch",
            "created_at",
        }
        assert expected == REQUIRED_FIELDS


# ===================================================================
# write_meta tests
# ===================================================================


class TestWriteMeta:
    """Tests for write_meta()."""

    def test_writes_valid_meta(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        write_meta(tmp_path, meta)
        meta_path = tmp_path / "meta.json"
        assert meta_path.exists()
        loaded = json.loads(meta_path.read_text(encoding="utf-8"))
        assert loaded == meta

    def test_standard_format(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["zzz_extra"] = "last"
        meta["aaa_extra"] = "first"
        write_meta(tmp_path, meta)

        content = (tmp_path / "meta.json").read_text(encoding="utf-8")

        # Trailing newline
        assert content.endswith("\n")

        # 2-space indent
        assert "  " in content

        # Sorted keys: aaa_extra should come before created_at
        aaa_pos = content.index('"aaa_extra"')
        created_pos = content.index('"created_at"')
        assert aaa_pos < created_pos

        # ensure_ascii=False: Unicode preserved
        meta2 = _minimal_meta()
        meta2["friendly_name"] = "Ubersicht"
        write_meta(tmp_path, meta2)
        content2 = (tmp_path / "meta.json").read_text(encoding="utf-8")
        assert "Ubersicht" in content2

    def test_invalid_meta_raises_valueerror(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        del meta["feature_number"]

        # Pre-create a valid file to check it is preserved
        _write_meta_file(tmp_path, _minimal_meta())

        with pytest.raises(ValueError, match="Invalid meta.json"):
            write_meta(tmp_path, meta)

        # Original file should be unchanged
        original = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
        assert original["feature_number"] == "051"

    def test_atomic_write_cleanup_on_failure(self, tmp_path: Path) -> None:
        """If os.replace raises, no temp file is left and original is preserved."""
        _write_meta_file(tmp_path, _minimal_meta())

        with (
            patch("specify_cli.feature_metadata.os.replace", side_effect=OSError("boom")),
            pytest.raises(OSError, match="boom"),
        ):
            write_meta(tmp_path, _minimal_meta())

        # Original file unchanged
        original = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
        assert original == _minimal_meta()

        # No temp files left
        temp_files = list(tmp_path.glob(".meta-*.tmp"))
        assert temp_files == []


# ===================================================================
# _atomic_write tests
# ===================================================================


class TestAtomicWrite:
    """Tests for _atomic_write()."""

    def test_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        _atomic_write(target, '{"key": "value"}\n')
        assert target.read_text(encoding="utf-8") == '{"key": "value"}\n'

    def test_replaces_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        target.write_text("old content", encoding="utf-8")
        _atomic_write(target, "new content")
        assert target.read_text(encoding="utf-8") == "new content"

    def test_no_temp_file_on_success(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        _atomic_write(target, "content")
        temp_files = list(tmp_path.glob(".meta-*.tmp"))
        assert temp_files == []

    def test_cleanup_on_write_failure(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        target.write_text("original", encoding="utf-8")

        with (
            patch("specify_cli.feature_metadata.os.replace", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            _atomic_write(target, "new content")

        assert target.read_text(encoding="utf-8") == "original"
        temp_files = list(tmp_path.glob(".meta-*.tmp"))
        assert temp_files == []


# ===================================================================
# Mutation helper tests
# ===================================================================


class TestRecordAcceptance:
    """Tests for record_acceptance()."""

    def test_sets_fields_and_appends_history(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        result = record_acceptance(
            tmp_path,
            accepted_by="claude",
            mode="auto",
            from_commit="abc123",
            accept_commit="def456",
        )

        assert result["accepted_by"] == "claude"
        assert result["acceptance_mode"] == "auto"
        assert result["accepted_from_commit"] == "abc123"
        assert result["accept_commit"] == "def456"
        assert "accepted_at" in result

        history = result["acceptance_history"]
        assert len(history) == 1
        assert history[0]["accepted_by"] == "claude"
        assert history[0]["acceptance_mode"] == "auto"
        assert history[0]["accepted_from_commit"] == "abc123"
        assert history[0]["accept_commit"] == "def456"

    def test_optional_fields_omitted(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        result = record_acceptance(
            tmp_path,
            accepted_by="human",
            mode="manual",
        )

        assert "accepted_from_commit" not in result
        assert "accept_commit" not in result
        history = result["acceptance_history"]
        assert "accepted_from_commit" not in history[0]
        assert "accept_commit" not in history[0]

    def test_bounded_history_cap(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["acceptance_history"] = [
            {"accepted_at": f"2026-01-{i:02d}T00:00:00+00:00", "accepted_by": f"agent{i}", "acceptance_mode": "auto"}
            for i in range(1, HISTORY_CAP + 1)
        ]
        assert len(meta["acceptance_history"]) == HISTORY_CAP
        _write_meta_file(tmp_path, meta)

        result = record_acceptance(
            tmp_path,
            accepted_by="final_agent",
            mode="auto",
        )

        history = result["acceptance_history"]
        assert len(history) == HISTORY_CAP
        # Oldest entry dropped, newest is ours
        assert history[-1]["accepted_by"] == "final_agent"
        assert history[0]["accepted_by"] == "agent2"  # agent1 dropped

    def test_missing_meta_raises_filenotfound(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            record_acceptance(tmp_path, accepted_by="claude", mode="auto")


class TestRecordMerge:
    """Tests for record_merge()."""

    def test_sets_fields_and_appends_history(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        result = record_merge(
            tmp_path,
            merged_by="claude",
            merged_into="main",
            strategy="merge",
            push=True,
        )

        assert result["merged_by"] == "claude"
        assert result["merged_into"] == "main"
        assert result["merged_strategy"] == "merge"
        assert result["merged_push"] is True
        assert "merged_at" in result

        history = result["merge_history"]
        assert len(history) == 1
        assert history[0]["merged_by"] == "claude"
        assert history[0]["merged_commit"] is None

    def test_bounded_merge_history(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["merge_history"] = [
            {"merged_at": f"2026-01-{i:02d}T00:00:00+00:00", "merged_by": f"agent{i}"}
            for i in range(1, HISTORY_CAP + 1)
        ]
        _write_meta_file(tmp_path, meta)

        result = record_merge(
            tmp_path,
            merged_by="final",
            merged_into="main",
            strategy="squash",
            push=False,
        )

        assert len(result["merge_history"]) == HISTORY_CAP
        assert result["merge_history"][-1]["merged_by"] == "final"

    def test_missing_meta_raises_filenotfound(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            record_merge(tmp_path, merged_by="x", merged_into="main", strategy="merge", push=False)


class TestFinalizeMerge:
    """Tests for finalize_merge()."""

    def test_sets_commit_hash(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["merge_history"] = [
            {"merged_at": "2026-01-01T00:00:00+00:00", "merged_commit": None}
        ]
        _write_meta_file(tmp_path, meta)

        result = finalize_merge(tmp_path, merged_commit="abc123")

        assert result["merged_commit"] == "abc123"
        assert result["merge_history"][-1]["merged_commit"] == "abc123"

    def test_empty_history(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        _write_meta_file(tmp_path, meta)

        result = finalize_merge(tmp_path, merged_commit="abc123")

        assert result["merged_commit"] == "abc123"
        assert result["merge_history"] == []

    def test_missing_meta_raises_filenotfound(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            finalize_merge(tmp_path, merged_commit="abc123")


class TestSetVcsLock:
    """Tests for set_vcs_lock()."""

    def test_sets_vcs_and_locked_at(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        result = set_vcs_lock(
            tmp_path,
            vcs_type="git",
            locked_at="2026-03-18T00:00:00+00:00",
        )

        assert result["vcs"] == "git"
        assert result["vcs_locked_at"] == "2026-03-18T00:00:00+00:00"

    def test_locked_at_optional(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        result = set_vcs_lock(tmp_path, vcs_type="jj")

        assert result["vcs"] == "jj"
        assert "vcs_locked_at" not in result

    def test_missing_meta_raises_filenotfound(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            set_vcs_lock(tmp_path, vcs_type="git")


class TestSetDocumentationState:
    """Tests for set_documentation_state()."""

    def test_sets_state(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        doc_state = {
            "iteration_mode": "initial",
            "divio_types_selected": ["tutorial", "reference"],
            "coverage_percentage": 0.5,
        }
        result = set_documentation_state(tmp_path, doc_state)

        assert result["documentation_state"] == doc_state

    def test_replaces_existing_state(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["documentation_state"] = {"old": "state"}
        _write_meta_file(tmp_path, meta)

        new_state = {"new": "state"}
        result = set_documentation_state(tmp_path, new_state)

        assert result["documentation_state"] == new_state

    def test_missing_meta_raises_filenotfound(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            set_documentation_state(tmp_path, {"key": "value"})


class TestSetTargetBranch:
    """Tests for set_target_branch()."""

    def test_sets_branch(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        result = set_target_branch(tmp_path, "develop")

        assert result["target_branch"] == "develop"

    def test_persists_to_disk(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())
        set_target_branch(tmp_path, "release/1.0")

        reloaded = load_meta(tmp_path)
        assert reloaded is not None
        assert reloaded["target_branch"] == "release/1.0"

    def test_missing_meta_raises_filenotfound(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            set_target_branch(tmp_path, "main")


# ===================================================================
# Unknown field preservation (round-trip)
# ===================================================================


class TestUnknownFieldPreservation:
    """Unknown fields survive mutation round-trips."""

    def test_write_preserves_unknown_fields(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["custom_field"] = "hello"
        meta["extra_config"] = {"nested": True}
        write_meta(tmp_path, meta)

        loaded = load_meta(tmp_path)
        assert loaded is not None
        assert loaded["custom_field"] == "hello"
        assert loaded["extra_config"] == {"nested": True}

    def test_mutation_preserves_unknown_fields(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["custom_plugin_data"] = [1, 2, 3]
        _write_meta_file(tmp_path, meta)

        result = set_target_branch(tmp_path, "develop")

        assert result["custom_plugin_data"] == [1, 2, 3]

        # Also verify on disk
        on_disk = load_meta(tmp_path)
        assert on_disk is not None
        assert on_disk["custom_plugin_data"] == [1, 2, 3]

    def test_acceptance_preserves_unknown_fields(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["my_extension"] = "preserved"
        _write_meta_file(tmp_path, meta)

        result = record_acceptance(
            tmp_path, accepted_by="agent", mode="auto"
        )
        assert result["my_extension"] == "preserved"


# ===================================================================
# Unicode handling
# ===================================================================


class TestUnicodeHandling:
    """Verify ensure_ascii=False preserves Unicode."""

    def test_unicode_in_friendly_name(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["friendly_name"] = "Ubersicht der Anderungen"
        write_meta(tmp_path, meta)

        content = (tmp_path / "meta.json").read_text(encoding="utf-8")
        assert "Ubersicht" in content
        # Not escaped
        assert "\\u" not in content

    def test_unicode_round_trip(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["friendly_name"] = "Feature with emojis and accents: cafe"
        write_meta(tmp_path, meta)

        loaded = load_meta(tmp_path)
        assert loaded is not None
        assert loaded["friendly_name"] == "Feature with emojis and accents: cafe"

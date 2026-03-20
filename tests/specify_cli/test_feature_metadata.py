"""Comprehensive unit tests for specify_cli.feature_metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from specify_cli.core.atomic import atomic_write
from specify_cli.feature_metadata import (
    HISTORY_CAP,
    REQUIRED_FIELDS,
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

    def test_load_meta_non_dict_json(self, tmp_path: Path) -> None:
        """Regression: load_meta() must reject non-dict JSON (e.g. arrays)."""
        meta_path = tmp_path / "meta.json"
        meta_path.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="Expected JSON object.*got list"):
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

        # ensure_ascii=False: Unicode preserved (actual non-ASCII chars)
        meta2 = _minimal_meta()
        meta2["friendly_name"] = "\u00dcberblick caf\u00e9"
        write_meta(tmp_path, meta2)
        content2 = (tmp_path / "meta.json").read_text(encoding="utf-8")
        # Raw Unicode chars must appear, not \\uXXXX escapes
        assert "\u00dcberblick caf\u00e9" in content2
        assert "\\u00dc" not in content2

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

    def test_write_meta_validate_false_skips_validation(self, tmp_path: Path) -> None:
        """write_meta(validate=False) succeeds with minimal meta lacking required fields."""
        minimal = {"mission": "documentation"}
        write_meta(tmp_path, minimal, validate=False)

        meta_path = tmp_path / "meta.json"
        assert meta_path.exists()

        content = meta_path.read_text(encoding="utf-8")
        assert content.endswith("\n")

        loaded = json.loads(content)
        assert loaded == minimal

        # Sorted keys and standard format
        expected = json.dumps(minimal, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        assert content == expected

    def test_write_meta_validate_false_still_formats_correctly(self, tmp_path: Path) -> None:
        """write_meta(validate=False) produces sorted keys and trailing newline."""
        meta = {"zzz": "last", "aaa": "first", "mission": "documentation"}
        write_meta(tmp_path, meta, validate=False)

        content = (tmp_path / "meta.json").read_text(encoding="utf-8")
        keys = list(json.loads(content).keys())
        assert keys == sorted(keys)
        assert content.endswith("\n")

    def test_write_meta_validate_true_rejects_minimal(self, tmp_path: Path) -> None:
        """write_meta(validate=True) (default) rejects meta missing required fields."""
        minimal = {"mission": "documentation"}
        with pytest.raises(ValueError, match="Invalid meta.json"):
            write_meta(tmp_path, minimal)

    def test_atomic_write_cleanup_on_failure(self, tmp_path: Path) -> None:
        """If os.replace raises, no temp file is left and original is preserved."""
        _write_meta_file(tmp_path, _minimal_meta())

        with (
            patch("specify_cli.core.atomic.os.replace", side_effect=OSError("boom")),
            pytest.raises(OSError, match="boom"),
        ):
            write_meta(tmp_path, _minimal_meta())

        # Original file unchanged
        original = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
        assert original == _minimal_meta()

        # No temp files left
        temp_files = list(tmp_path.glob(".atomic-*.tmp"))
        assert temp_files == []


# ===================================================================
# atomic_write tests (shared utility, imported from specify_cli.core.atomic)
# ===================================================================


class TestAtomicWrite:
    """Tests for atomic_write()."""

    def test_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        atomic_write(target, '{"key": "value"}\n')
        assert target.read_text(encoding="utf-8") == '{"key": "value"}\n'

    def test_replaces_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        target.write_text("old content", encoding="utf-8")
        atomic_write(target, "new content")
        assert target.read_text(encoding="utf-8") == "new content"

    def test_no_temp_file_on_success(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        atomic_write(target, "content")
        temp_files = list(tmp_path.glob(".atomic-*.tmp"))
        assert temp_files == []

    def test_cleanup_on_write_failure(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        target.write_text("original", encoding="utf-8")

        with (
            patch("specify_cli.core.atomic.os.replace", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            atomic_write(target, "new content")

        assert target.read_text(encoding="utf-8") == "original"
        temp_files = list(tmp_path.glob(".atomic-*.tmp"))
        assert temp_files == []

    def test_write_is_complete_not_truncated(self, tmp_path: Path) -> None:
        """Verify the output file byte length matches the encoded input.

        This guards against short-write bugs where os.write() returns fewer
        bytes than requested and the caller ignores the return value.
        """
        # Use a payload large enough that a short write would be detectable
        content = '{"data": "' + "x" * 100_000 + '"}\n'
        target = tmp_path / "big.json"
        atomic_write(target, content)

        expected_bytes = content.encode("utf-8")
        actual_bytes = target.read_bytes()
        assert len(actual_bytes) == len(expected_bytes)
        assert actual_bytes == expected_bytes

    def test_write_complete_with_unicode(self, tmp_path: Path) -> None:
        """Verify multi-byte Unicode content is fully written (not truncated)."""
        # Multi-byte characters: each is 3+ bytes in UTF-8
        content = '{"name": "' + "\u00fc\u00e4\u00f6\u00df" * 5000 + '"}\n'
        target = tmp_path / "unicode.json"
        atomic_write(target, content)

        expected_bytes = content.encode("utf-8")
        actual_bytes = target.read_bytes()
        assert len(actual_bytes) == len(expected_bytes)
        assert actual_bytes == expected_bytes


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

    def test_record_acceptance_clears_stale_commit_fields(self, tmp_path: Path) -> None:
        """Regression: a second acceptance without commit args must not retain stale values."""
        _write_meta_file(tmp_path, _minimal_meta())

        # First acceptance WITH commit fields
        result1 = record_acceptance(
            tmp_path,
            accepted_by="agent1",
            mode="auto",
            from_commit="commit_aaa",
            accept_commit="commit_bbb",
        )
        assert result1["accepted_from_commit"] == "commit_aaa"
        assert result1["accept_commit"] == "commit_bbb"

        # Second acceptance WITHOUT commit fields — stale values must be gone
        result2 = record_acceptance(
            tmp_path,
            accepted_by="agent2",
            mode="manual",
        )
        assert "accepted_from_commit" not in result2
        assert "accept_commit" not in result2
        assert result2["accepted_by"] == "agent2"

        # Also verify on disk
        on_disk = load_meta(tmp_path)
        assert on_disk is not None
        assert "accepted_from_commit" not in on_disk
        assert "accept_commit" not in on_disk

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

    def test_record_merge_clears_stale_merged_commit(self, tmp_path: Path) -> None:
        """Regression: record_merge() after finalize_merge() must clear merged_commit."""
        _write_meta_file(tmp_path, _minimal_meta())

        # First merge + finalize
        record_merge(
            tmp_path,
            merged_by="agent1",
            merged_into="main",
            strategy="merge",
            push=True,
        )
        finalize_merge(tmp_path, merged_commit="sha_first")
        mid = load_meta(tmp_path)
        assert mid is not None
        assert mid["merged_commit"] == "sha_first"

        # Second merge (not yet finalized) — merged_commit must be gone
        result = record_merge(
            tmp_path,
            merged_by="agent2",
            merged_into="develop",
            strategy="squash",
            push=False,
        )
        assert "merged_commit" not in result
        assert result["merged_by"] == "agent2"

        # Verify on disk
        on_disk = load_meta(tmp_path)
        assert on_disk is not None
        assert "merged_commit" not in on_disk

    def test_missing_meta_raises_filenotfound(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            record_merge(tmp_path, merged_by="x", merged_into="main", strategy="merge", push=False)


class TestFinalizeMerge:
    """Tests for finalize_merge()."""

    def test_sets_commit_hash(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["merge_history"] = [{"merged_at": "2026-01-01T00:00:00+00:00", "merged_commit": None}]
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

        result = record_acceptance(tmp_path, accepted_by="agent", mode="auto")
        assert result["my_extension"] == "preserved"


# ===================================================================
# Unicode handling
# ===================================================================


class TestUnicodeHandling:
    """Verify ensure_ascii=False preserves Unicode."""

    def test_unicode_in_friendly_name(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["friendly_name"] = "\u00dcbersicht der \u00c4nderungen"
        write_meta(tmp_path, meta)

        content = (tmp_path / "meta.json").read_text(encoding="utf-8")
        # Raw Unicode chars must appear, not \uXXXX escapes
        assert "\u00dcbersicht" in content
        assert "\u00c4nderungen" in content
        assert "\\u00dc" not in content

    def test_unicode_round_trip(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["friendly_name"] = "Feature with emojis and accents: cafe"
        write_meta(tmp_path, meta)

        loaded = load_meta(tmp_path)
        assert loaded is not None
        assert loaded["friendly_name"] == "Feature with emojis and accents: cafe"


# ===================================================================
# WP03: Write-site migration verification tests
# ===================================================================


class TestVcsLockStandardFormat:
    """T018: Verify set_vcs_lock() produces correctly formatted meta.json."""

    def test_vcs_lock_produces_standard_format(self, tmp_path: Path) -> None:
        """set_vcs_lock() writes meta.json with standard formatting."""
        _write_meta_file(tmp_path, _minimal_meta())

        set_vcs_lock(tmp_path, vcs_type="git", locked_at="2026-03-18T12:00:00+00:00")

        content = (tmp_path / "meta.json").read_text(encoding="utf-8")
        # Trailing newline
        assert content.endswith("\n")
        # Valid JSON
        data = json.loads(content)
        # Sorted keys
        keys = list(data.keys())
        assert keys == sorted(keys)
        # Fields present
        assert data["vcs"] == "git"
        assert data["vcs_locked_at"] == "2026-03-18T12:00:00+00:00"

    def test_vcs_lock_without_locked_at(self, tmp_path: Path) -> None:
        """set_vcs_lock() without locked_at omits the field."""
        _write_meta_file(tmp_path, _minimal_meta())

        set_vcs_lock(tmp_path, vcs_type="git")

        content = (tmp_path / "meta.json").read_text(encoding="utf-8")
        assert content.endswith("\n")
        data = json.loads(content)
        assert data["vcs"] == "git"
        assert "vcs_locked_at" not in data

    def test_vcs_lock_preserves_existing_fields(self, tmp_path: Path) -> None:
        """set_vcs_lock() preserves all existing meta fields."""
        meta = _minimal_meta()
        meta["custom_field"] = "should survive"
        _write_meta_file(tmp_path, meta)

        set_vcs_lock(tmp_path, vcs_type="git", locked_at="2026-03-18T12:00:00+00:00")

        data = load_meta(tmp_path)
        assert data is not None
        assert data["custom_field"] == "should survive"
        assert data["feature_number"] == "051"


class TestRecordMergeBoundedHistory:
    """T018: Verify record_merge() caps merge_history at 20 entries."""

    def test_record_merge_bounded_history(self, tmp_path: Path) -> None:
        """record_merge() caps merge_history at 20 entries."""
        _write_meta_file(tmp_path, _minimal_meta())

        # Call record_merge() 25 times
        for i in range(25):
            record_merge(
                tmp_path,
                merged_by=f"agent{i}",
                merged_into="main",
                strategy="merge",
                push=False,
            )

        data = load_meta(tmp_path)
        assert data is not None
        assert len(data["merge_history"]) == HISTORY_CAP
        # Most recent entry is the last one we added
        assert data["merge_history"][-1]["merged_by"] == "agent24"
        # Oldest surviving is agent5 (agents 0-4 dropped)
        assert data["merge_history"][0]["merged_by"] == "agent5"

    def test_record_merge_standard_format(self, tmp_path: Path) -> None:
        """record_merge() writes meta.json with standard formatting."""
        _write_meta_file(tmp_path, _minimal_meta())

        record_merge(
            tmp_path,
            merged_by="claude",
            merged_into="main",
            strategy="squash",
            push=True,
        )

        content = (tmp_path / "meta.json").read_text(encoding="utf-8")
        assert content.endswith("\n")
        data = json.loads(content)
        keys = list(data.keys())
        assert keys == sorted(keys)
        assert data["merged_by"] == "claude"
        assert data["merged_into"] == "main"
        assert data["merged_strategy"] == "squash"
        assert data["merged_push"] is True


class TestFinalizeMergeUpdatesHistory:
    """T018: Verify finalize_merge() sets merged_commit on latest history entry."""

    def test_finalize_merge_updates_latest_history(self, tmp_path: Path) -> None:
        """finalize_merge() sets merged_commit on latest history entry."""
        _write_meta_file(tmp_path, _minimal_meta())

        record_merge(
            tmp_path,
            merged_by="agent",
            merged_into="main",
            strategy="merge",
            push=False,
        )

        finalize_merge(tmp_path, merged_commit="abc123def456")

        data = load_meta(tmp_path)
        assert data is not None
        assert data["merged_commit"] == "abc123def456"
        assert data["merge_history"][-1]["merged_commit"] == "abc123def456"

        # Standard format
        content = (tmp_path / "meta.json").read_text(encoding="utf-8")
        assert content.endswith("\n")
        keys = list(json.loads(content).keys())
        assert keys == sorted(keys)


class TestFeatureCreationTrailingNewline:
    """T018: Verify write_meta() on fresh creation includes trailing newline."""

    def test_feature_creation_has_trailing_newline(self, tmp_path: Path) -> None:
        """write_meta() on fresh creation includes trailing newline."""
        meta = _minimal_meta()
        write_meta(tmp_path, meta)

        content = (tmp_path / "meta.json").read_bytes()
        # Must end with newline byte
        assert content.endswith(b"\n")
        # Must be valid JSON
        parsed = json.loads(content)
        assert parsed["feature_number"] == "051"

    def test_feature_creation_with_documentation_state(self, tmp_path: Path) -> None:
        """set_documentation_state() after write_meta() keeps trailing newline."""
        meta = _minimal_meta()
        write_meta(tmp_path, meta)

        doc_state = {
            "iteration_mode": "initial",
            "divio_types_selected": [],
            "generators_configured": [],
            "target_audience": "developers",
            "last_audit_date": None,
            "coverage_percentage": 0.0,
        }
        set_documentation_state(tmp_path, doc_state)

        content = (tmp_path / "meta.json").read_bytes()
        # Must end with newline byte
        assert content.endswith(b"\n")
        # Must be valid JSON with documentation_state
        parsed = json.loads(content)
        assert parsed["documentation_state"] == doc_state
        # Keys should be sorted
        keys = list(parsed.keys())
        assert keys == sorted(keys)


# ===================================================================
# WP03 cycle 2: Merge tolerance for malformed meta.json
# ===================================================================


class TestMergeToleranceMalformedMeta:
    """Verify _prepare_merge_metadata and _finalize_merge_metadata tolerate
    malformed meta.json without raising, preserving the old error-tolerance
    that existed before the migration to feature_metadata.py.

    The merge operation itself must not fail due to metadata issues -- these
    functions are called AFTER git merge has already succeeded.
    """

    def test_prepare_merge_metadata_tolerates_malformed_json(self, tmp_path: Path) -> None:
        """_prepare_merge_metadata returns None (no crash) when meta.json is malformed."""
        import sys
        import os

        # Add the tasks scripts dir to sys.path so we can import tasks_cli
        tasks_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "specify_cli",
            "scripts",
            "tasks",
        )
        tasks_dir = os.path.normpath(tasks_dir)
        if tasks_dir not in sys.path:
            sys.path.insert(0, tasks_dir)

        from specify_cli.scripts.tasks.tasks_cli import _prepare_merge_metadata

        # Create feature dir with malformed meta.json
        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        meta_path = feature_dir / "meta.json"
        meta_path.write_text("{invalid json content", encoding="utf-8")

        # Should return None (not raise) because record_merge fails on malformed JSON
        result = _prepare_merge_metadata(
            repo_root=tmp_path,
            feature="test-feature",
            target="main",
            strategy="merge",
            pushed=False,
        )
        assert result is None

    def test_finalize_merge_metadata_tolerates_malformed_json(self, tmp_path: Path) -> None:
        """_finalize_merge_metadata does not raise when meta.json is malformed."""
        from specify_cli.scripts.tasks.tasks_cli import _finalize_merge_metadata

        # Create malformed meta.json
        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        meta_path = feature_dir / "meta.json"
        meta_path.write_text("{invalid json content", encoding="utf-8")

        # Should not raise -- just log a warning
        _finalize_merge_metadata(meta_path, merge_commit="abc123")

    def test_prepare_merge_metadata_works_with_valid_meta(self, tmp_path: Path) -> None:
        """_prepare_merge_metadata succeeds normally with valid meta.json."""
        from specify_cli.scripts.tasks.tasks_cli import _prepare_merge_metadata
        from unittest.mock import patch

        # Create valid meta.json
        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        meta = _minimal_meta()
        _write_meta_file(feature_dir, meta)

        # Mock _merge_actor to avoid git dependency
        with patch(
            "specify_cli.scripts.tasks.tasks_cli._merge_actor",
            return_value="test-user",
        ):
            result = _prepare_merge_metadata(
                repo_root=tmp_path,
                feature="test-feature",
                target="main",
                strategy="merge",
                pushed=False,
            )

        assert result is not None
        assert result == feature_dir / "meta.json"

        # Verify the metadata was written correctly
        data = load_meta(feature_dir)
        assert data is not None
        assert data["merged_by"] == "test-user"
        assert data["merged_into"] == "main"

    def test_finalize_merge_metadata_works_with_valid_meta(self, tmp_path: Path) -> None:
        """_finalize_merge_metadata succeeds normally with valid meta.json."""
        from specify_cli.scripts.tasks.tasks_cli import _finalize_merge_metadata

        # Create valid meta.json with merge history
        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        meta = _minimal_meta()
        meta["merge_history"] = [{"merged_at": "2026-03-18T00:00:00+00:00", "merged_commit": None}]
        _write_meta_file(feature_dir, meta)

        meta_path = feature_dir / "meta.json"
        _finalize_merge_metadata(meta_path, merge_commit="sha256abc")

        data = load_meta(feature_dir)
        assert data is not None
        assert data["merged_commit"] == "sha256abc"
        assert data["merge_history"][-1]["merged_commit"] == "sha256abc"


# ===================================================================
# WP05 T024: Compatibility wrapper tests
# ===================================================================


class TestCompatibilityWrappers:
    """Verify upgrade/feature_meta.py wrappers delegate to feature_metadata."""

    def test_write_feature_meta_delegates_to_write_meta(self, tmp_path: Path) -> None:
        """write_feature_meta() wrapper delegates to feature_metadata.write_meta()."""
        from specify_cli.upgrade.feature_meta import write_feature_meta

        feature_dir = tmp_path / "001-test"
        feature_dir.mkdir()
        meta = {
            "feature_number": "001",
            "slug": "001-test",
            "feature_slug": "001-test",
            "friendly_name": "Test",
            "mission": "software-dev",
            "target_branch": "main",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        write_feature_meta(feature_dir, meta)

        content = (feature_dir / "meta.json").read_text(encoding="utf-8")
        # Trailing newline (standard format)
        assert content.endswith("\n")
        # Sorted keys (new behaviour from write_meta)
        parsed = json.loads(content)
        assert list(parsed.keys()) == sorted(parsed.keys())
        # All fields present
        assert parsed["feature_number"] == "001"

    def test_load_feature_meta_delegates_to_load_meta(self, tmp_path: Path) -> None:
        """load_feature_meta() wrapper delegates to feature_metadata.load_meta()."""
        from specify_cli.upgrade.feature_meta import load_feature_meta

        feature_dir = tmp_path / "001-test"
        feature_dir.mkdir()
        (feature_dir / "meta.json").write_text('{"feature_number": "001"}', encoding="utf-8")

        result = load_feature_meta(feature_dir)
        assert result == {"feature_number": "001"}

    def test_load_feature_meta_returns_none_when_missing(self, tmp_path: Path) -> None:
        """load_feature_meta() returns None when meta.json does not exist."""
        from specify_cli.upgrade.feature_meta import load_feature_meta

        feature_dir = tmp_path / "001-test"
        feature_dir.mkdir()

        result = load_feature_meta(feature_dir)
        assert result is None

    def test_write_feature_meta_skips_validation(self, tmp_path: Path) -> None:
        """write_feature_meta() passes validate=False (matches old behaviour).

        Old code never validated required fields. The wrapper must not
        introduce validation failures for partial meta dicts used during
        upgrades.
        """
        from specify_cli.upgrade.feature_meta import write_feature_meta

        feature_dir = tmp_path / "partial"
        feature_dir.mkdir()
        # Partial meta missing many required fields -- old code accepted this
        partial_meta = {"mission": "software-dev"}
        write_feature_meta(feature_dir, partial_meta)

        content = (feature_dir / "meta.json").read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed == {"mission": "software-dev"}

    def test_migration_import_path_still_works(self) -> None:
        """The import path used by m_2_0_6_consistency_sweep.py still resolves."""
        from specify_cli.upgrade.feature_meta import (
            build_baseline_feature_meta,
            load_feature_meta,
            write_feature_meta,
        )

        # Just verify the symbols are importable -- migrations depend on this
        assert callable(load_feature_meta)
        assert callable(write_feature_meta)
        assert callable(build_baseline_feature_meta)

    def test_wrapper_round_trip_matches_canonical(self, tmp_path: Path) -> None:
        """Write via wrapper, read via canonical load_meta -- same data."""
        from specify_cli.upgrade.feature_meta import write_feature_meta

        feature_dir = tmp_path / "roundtrip"
        feature_dir.mkdir()
        meta = _minimal_meta()
        write_feature_meta(feature_dir, meta)

        canonical_result = load_meta(feature_dir)
        assert canonical_result == meta

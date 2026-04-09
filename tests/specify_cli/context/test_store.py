"""Tests for context/store.py -- persistence layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.context.errors import ContextCorruptedError, ContextNotFoundError
from specify_cli.context.models import ContextToken, MissionContext
from specify_cli.context.store import (
    delete_context,
    list_contexts,
    load_context,
    save_context,
)


def _make_context(**overrides: object) -> MissionContext:
    defaults: dict[str, object] = {
        "token": "ctx-01TESTSTORAGE00000000000AA",
        "project_uuid": "test-uuid-1234",
        "mission_id": "057-test-feature",
        "work_package_id": "WP01",
        "wp_code": "WP01",
        "mission_slug": "057-test-feature",
        "mission_number": "057",
        "mission_type": "software-dev",
        "target_branch": "main",
        "authoritative_repo": "/tmp/repo",
        "authoritative_ref": "kitty/mission-057-test-feature-lane-a",
        "owned_files": ("src/**",),
        "execution_mode": "code_change",
        "dependency_mode": "independent",
        "created_at": "2026-03-27T18:00:00+00:00",
        "created_by": "claude",
    }
    defaults.update(overrides)
    return MissionContext(**defaults)  # type: ignore[arg-type]


class TestSaveContext:
    """save_context writes atomic JSON files."""

    def test_creates_directory_and_file(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ct = save_context(ctx, tmp_path)

        assert isinstance(ct, ContextToken)
        assert ct.token == ctx.token
        assert ct.context_path.exists()
        assert ct.context_path.name == f"{ctx.token}.json"

    def test_file_content_is_valid_json(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ct = save_context(ctx, tmp_path)

        data = json.loads(ct.context_path.read_text(encoding="utf-8"))
        assert data["token"] == ctx.token
        assert data["wp_code"] == "WP01"

    def test_file_has_sorted_keys(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ct = save_context(ctx, tmp_path)

        data = json.loads(ct.context_path.read_text(encoding="utf-8"))
        keys = list(data.keys())
        assert keys == sorted(keys)

    def test_file_has_trailing_newline(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ct = save_context(ctx, tmp_path)

        raw = ct.context_path.read_text(encoding="utf-8")
        assert raw.endswith("\n")

    def test_overwrite_existing(self, tmp_path: Path) -> None:
        ctx1 = _make_context(created_by="agent1")
        ct1 = save_context(ctx1, tmp_path)

        ctx2 = _make_context(created_by="agent2")
        ct2 = save_context(ctx2, tmp_path)

        assert ct1.context_path == ct2.context_path
        data = json.loads(ct2.context_path.read_text(encoding="utf-8"))
        assert data["created_by"] == "agent2"


class TestLoadContext:
    """load_context reads a persisted MissionContext."""

    def test_round_trip(self, tmp_path: Path) -> None:
        original = _make_context()
        save_context(original, tmp_path)

        loaded = load_context(original.token, tmp_path)
        assert loaded == original

    def test_not_found_raises(self, tmp_path: Path) -> None:
        # Ensure the contexts directory exists but has no files
        (tmp_path / ".kittify" / "runtime" / "contexts").mkdir(parents=True)

        with pytest.raises(ContextNotFoundError, match="not found"):
            load_context("ctx-DOES-NOT-EXIST", tmp_path)

    def test_corrupted_json_raises(self, tmp_path: Path) -> None:
        contexts_dir = tmp_path / ".kittify" / "runtime" / "contexts"
        contexts_dir.mkdir(parents=True)
        (contexts_dir / "ctx-BROKEN.json").write_text("not valid json", encoding="utf-8")

        with pytest.raises(ContextCorruptedError, match="corrupted"):
            load_context("ctx-BROKEN", tmp_path)

    def test_missing_field_raises_corrupted(self, tmp_path: Path) -> None:
        contexts_dir = tmp_path / ".kittify" / "runtime" / "contexts"
        contexts_dir.mkdir(parents=True)
        # Valid JSON but missing required fields
        (contexts_dir / "ctx-INCOMPLETE.json").write_text(
            json.dumps({"token": "ctx-INCOMPLETE"}),
            encoding="utf-8",
        )

        with pytest.raises(ContextCorruptedError, match="missing required field"):
            load_context("ctx-INCOMPLETE", tmp_path)


class TestMissionFlagInErrorMessage:
    """Regression tests: error messages use --mission, not --feature (T027)."""

    def test_missing_token_error_uses_mission_flag(self, tmp_path: Path) -> None:
        """load_context not-found error must say --mission, not --feature."""
        (tmp_path / ".kittify" / "runtime" / "contexts").mkdir(parents=True)

        with pytest.raises(ContextNotFoundError) as exc_info:
            load_context("ctx-DOES-NOT-EXIST", tmp_path)

        error_msg = str(exc_info.value)
        assert "--mission" in error_msg
        assert "--feature" not in error_msg

    def test_missing_token_error_shows_resolve_command(self, tmp_path: Path) -> None:
        """load_context not-found error must include the context resolve command."""
        (tmp_path / ".kittify" / "runtime" / "contexts").mkdir(parents=True)

        with pytest.raises(ContextNotFoundError) as exc_info:
            load_context("ctx-DOES-NOT-EXIST", tmp_path)

        error_msg = str(exc_info.value)
        assert "context resolve" in error_msg


class TestListContexts:
    """list_contexts enumerates persisted tokens."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        result = list_contexts(tmp_path)
        assert result == []

    def test_lists_saved_contexts(self, tmp_path: Path) -> None:
        ctx1 = _make_context(token="ctx-01AAAA")
        ctx2 = _make_context(token="ctx-01BBBB")
        save_context(ctx1, tmp_path)
        save_context(ctx2, tmp_path)

        tokens = list_contexts(tmp_path)
        assert len(tokens) == 2
        token_ids = {t.token for t in tokens}
        assert token_ids == {"ctx-01AAAA", "ctx-01BBBB"}

    def test_returns_context_token_objects(self, tmp_path: Path) -> None:
        ctx = _make_context(token="ctx-01CHECK")
        save_context(ctx, tmp_path)

        tokens = list_contexts(tmp_path)
        assert len(tokens) == 1
        assert isinstance(tokens[0], ContextToken)
        assert tokens[0].token == "ctx-01CHECK"
        assert tokens[0].context_path.exists()

    def test_non_json_files_ignored(self, tmp_path: Path) -> None:
        contexts_dir = tmp_path / ".kittify" / "runtime" / "contexts"
        contexts_dir.mkdir(parents=True)
        (contexts_dir / "README.md").write_text("ignore me", encoding="utf-8")

        ctx = _make_context(token="ctx-01ONLY")
        save_context(ctx, tmp_path)

        tokens = list_contexts(tmp_path)
        assert len(tokens) == 1
        assert tokens[0].token == "ctx-01ONLY"


class TestDeleteContext:
    """delete_context removes the persisted file."""

    def test_delete_existing(self, tmp_path: Path) -> None:
        ctx = _make_context(token="ctx-01DELETE")
        ct = save_context(ctx, tmp_path)
        assert ct.context_path.exists()

        delete_context("ctx-01DELETE", tmp_path)
        assert not ct.context_path.exists()

    def test_delete_nonexistent_is_noop(self, tmp_path: Path) -> None:
        # Should not raise
        delete_context("ctx-GONE", tmp_path)

    def test_save_delete_list_cycle(self, tmp_path: Path) -> None:
        ctx = _make_context(token="ctx-01CYCLE")
        save_context(ctx, tmp_path)
        assert len(list_contexts(tmp_path)) == 1

        delete_context("ctx-01CYCLE", tmp_path)
        assert len(list_contexts(tmp_path)) == 0

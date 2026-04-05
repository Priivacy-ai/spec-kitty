"""Tests for context/models.py -- MissionContext and ContextToken."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from specify_cli.context.models import ContextToken, MissionContext


def _make_context(**overrides: object) -> MissionContext:
    """Helper to build a MissionContext with sensible defaults."""
    defaults: dict[str, object] = {
        "token": "ctx-01TEST000000000000000000AA",
        "project_uuid": "8a4a7da6-a97c-4bb4-893a-b31664abfee4",
        "mission_id": "057-canonical-context-architecture-cleanup",
        "work_package_id": "WP01",
        "wp_code": "WP01",
        "feature_slug": "057-canonical-context-architecture-cleanup",
        "target_branch": "main",
        "authoritative_repo": "/tmp/repo",
        "authoritative_ref": "kitty/mission-057-canonical-context-architecture-cleanup-lane-a",
        "owned_files": ("src/specify_cli/context/**",),
        "execution_mode": "code_change",
        "dependency_mode": "independent",
        "created_at": "2026-03-27T18:00:00+00:00",
        "created_by": "claude",
    }
    defaults.update(overrides)
    return MissionContext(**defaults)  # type: ignore[arg-type]


class TestMissionContextCreation:
    """MissionContext can be created with all fields."""

    def test_all_fields_present(self) -> None:
        ctx = _make_context()
        assert ctx.token == "ctx-01TEST000000000000000000AA"
        assert ctx.project_uuid == "8a4a7da6-a97c-4bb4-893a-b31664abfee4"
        assert ctx.mission_id == "057-canonical-context-architecture-cleanup"
        assert ctx.work_package_id == "WP01"
        assert ctx.wp_code == "WP01"
        assert ctx.feature_slug == "057-canonical-context-architecture-cleanup"
        assert ctx.target_branch == "main"
        assert ctx.authoritative_repo == "/tmp/repo"
        assert ctx.authoritative_ref == "kitty/mission-057-canonical-context-architecture-cleanup-lane-a"
        assert ctx.owned_files == ("src/specify_cli/context/**",)
        assert ctx.execution_mode == "code_change"
        assert ctx.dependency_mode == "independent"
        assert ctx.created_at == "2026-03-27T18:00:00+00:00"
        assert ctx.created_by == "claude"

    def test_authoritative_ref_none_for_planning_artifact(self) -> None:
        ctx = _make_context(
            execution_mode="planning_artifact",
            authoritative_ref=None,
        )
        assert ctx.authoritative_ref is None
        assert ctx.execution_mode == "planning_artifact"

    def test_owned_files_is_tuple(self) -> None:
        ctx = _make_context(owned_files=("a/**", "b/**"))
        assert isinstance(ctx.owned_files, tuple)
        assert len(ctx.owned_files) == 2

    def test_empty_owned_files(self) -> None:
        ctx = _make_context(owned_files=())
        assert ctx.owned_files == ()


class TestMissionContextFrozen:
    """MissionContext is immutable (frozen dataclass)."""

    def test_cannot_assign_token(self) -> None:
        ctx = _make_context()
        with pytest.raises(FrozenInstanceError):
            ctx.token = "ctx-MODIFIED"  # type: ignore[misc]

    def test_cannot_assign_wp_code(self) -> None:
        ctx = _make_context()
        with pytest.raises(FrozenInstanceError):
            ctx.wp_code = "WP99"  # type: ignore[misc]

    def test_cannot_assign_owned_files(self) -> None:
        ctx = _make_context()
        with pytest.raises(FrozenInstanceError):
            ctx.owned_files = ("modified/**",)  # type: ignore[misc]


class TestMissionContextSerialization:
    """to_dict / from_dict round-trip."""

    def test_round_trip(self) -> None:
        original = _make_context()
        data = original.to_dict()
        restored = MissionContext.from_dict(data)
        assert restored == original

    def test_to_dict_owned_files_is_list(self) -> None:
        """JSON representation uses list, not tuple, for owned_files."""
        ctx = _make_context(owned_files=("a/**", "b/**"))
        data = ctx.to_dict()
        assert isinstance(data["owned_files"], list)
        assert data["owned_files"] == ["a/**", "b/**"]

    def test_from_dict_converts_owned_files_to_tuple(self) -> None:
        data = _make_context().to_dict()
        data["owned_files"] = ["x/**", "y/**"]
        ctx = MissionContext.from_dict(data)
        assert isinstance(ctx.owned_files, tuple)
        assert ctx.owned_files == ("x/**", "y/**")

    def test_round_trip_with_null_authoritative_ref(self) -> None:
        original = _make_context(authoritative_ref=None)
        data = original.to_dict()
        assert data["authoritative_ref"] is None
        restored = MissionContext.from_dict(data)
        assert restored.authoritative_ref is None
        assert restored == original

    def test_to_dict_has_all_keys(self) -> None:
        data = _make_context().to_dict()
        expected_keys = {
            "token",
            "project_uuid",
            "mission_id",
            "work_package_id",
            "wp_code",
            "feature_slug",
            "target_branch",
            "authoritative_repo",
            "authoritative_ref",
            "owned_files",
            "execution_mode",
            "dependency_mode",
            "created_at",
            "created_by",
        }
        assert set(data.keys()) == expected_keys

    def test_from_dict_missing_key_raises(self) -> None:
        data = _make_context().to_dict()
        del data["token"]
        with pytest.raises(KeyError):
            MissionContext.from_dict(data)


class TestContextToken:
    """ContextToken is a lightweight frozen wrapper."""

    def test_creation(self, tmp_path: Path) -> None:
        ct = ContextToken(token="ctx-01ABCDEF", context_path=tmp_path / "ctx-01ABCDEF.json")
        assert ct.token == "ctx-01ABCDEF"
        assert ct.context_path == tmp_path / "ctx-01ABCDEF.json"

    def test_frozen(self, tmp_path: Path) -> None:
        ct = ContextToken(token="ctx-01ABCDEF", context_path=tmp_path / "ctx-01ABCDEF.json")
        with pytest.raises(FrozenInstanceError):
            ct.token = "modified"  # type: ignore[misc]

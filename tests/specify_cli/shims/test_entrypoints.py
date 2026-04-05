"""Tests for shims/entrypoints.py — shim dispatch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.shims.entrypoints import (
    _parse_raw_args,
    shim_dispatch,
)
from specify_cli.context.models import MissionContext
from specify_cli.context.errors import MissingArgumentError


# ---------------------------------------------------------------------------
# _parse_raw_args
# ---------------------------------------------------------------------------

class TestParseRawArgs:
    def test_extracts_wp_code(self) -> None:
        result = _parse_raw_args("WP03 --feature 057-cleanup")
        assert result["wp_code"] == "WP03"

    def test_extracts_feature_slug(self) -> None:
        result = _parse_raw_args("WP01 --feature 057-canonical-context")
        assert result["feature_slug"] == "057-canonical-context"

    def test_wp_code_case_normalised(self) -> None:
        result = _parse_raw_args("wp05")
        assert result["wp_code"] == "WP05"

    def test_missing_wp_returns_none(self) -> None:
        result = _parse_raw_args("--feature 057-cleanup")
        assert result["wp_code"] is None

    def test_missing_feature_returns_none(self) -> None:
        result = _parse_raw_args("WP01")
        assert result["feature_slug"] is None

    def test_empty_string(self) -> None:
        result = _parse_raw_args("")
        assert result["wp_code"] is None
        assert result["feature_slug"] is None

    def test_first_wp_wins(self) -> None:
        result = _parse_raw_args("WP01 WP02 WP03")
        assert result["wp_code"] == "WP01"

    def test_longer_wp_code(self) -> None:
        result = _parse_raw_args("WP123 --feature test")
        assert result["wp_code"] == "WP123"


# ---------------------------------------------------------------------------
# shim_dispatch
# ---------------------------------------------------------------------------

def _make_mock_context(**kwargs) -> MissionContext:
    """Build a minimal MissionContext for testing."""
    defaults: dict[str, object] = {
        "token": "ctx-01TEST",
        "project_uuid": "uuid-test",
        "mission_id": "057-test",
        "work_package_id": "WP01",
        "wp_code": "WP01",
        "feature_slug": "057-test",
        "target_branch": "main",
        "authoritative_repo": "/tmp/repo",
        "authoritative_ref": "kitty/mission-057-test-lane-a",
        "owned_files": (),
        "execution_mode": "code_change",
        "dependency_mode": "independent",
        "created_at": "2026-01-01T00:00:00+00:00",
        "created_by": "claude",
    }
    defaults.update(kwargs)
    return MissionContext(**defaults)  # type: ignore[arg-type]


class TestShimDispatch:
    def test_unknown_command_raises_value_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown shim command"):
            shim_dispatch(
                command="nonexistent-command",
                agent="claude",
                raw_args="WP01 --feature 057-test",
                context_token=None,
                repo_root=tmp_path,
            )

    def test_dispatches_with_context_token(self, tmp_path: Path) -> None:
        mock_ctx = _make_mock_context()
        with patch(
            "specify_cli.shims.entrypoints.resolve_or_load",
            return_value=mock_ctx,
        ) as mock_resolve:
            result = shim_dispatch(
                command="implement",
                agent="claude",
                raw_args="",
                context_token="ctx-01EXISTING",
                repo_root=tmp_path,
            )
            mock_resolve.assert_called_once_with(
                token="ctx-01EXISTING",
                wp_code=None,
                feature_slug=None,
                agent="claude",
                repo_root=tmp_path,
            )
            assert result is mock_ctx

    def test_dispatches_with_raw_args(self, tmp_path: Path) -> None:
        mock_ctx = _make_mock_context()
        with patch(
            "specify_cli.shims.entrypoints.resolve_or_load",
            return_value=mock_ctx,
        ) as mock_resolve:
            result = shim_dispatch(
                command="review",
                agent="codex",
                raw_args="WP03 --feature 057-canonical-context",
                context_token=None,
                repo_root=tmp_path,
            )
            mock_resolve.assert_called_once_with(
                token=None,
                wp_code="WP03",
                feature_slug="057-canonical-context",
                agent="codex",
                repo_root=tmp_path,
            )
            assert result is mock_ctx

    def test_missing_args_propagates_error(self, tmp_path: Path) -> None:
        with patch(
            "specify_cli.shims.entrypoints.resolve_or_load",
            side_effect=MissingArgumentError("Missing required argument(s)"),
        ), pytest.raises(MissingArgumentError):
            shim_dispatch(
                command="implement",
                agent="claude",
                raw_args="",
                context_token=None,
                repo_root=tmp_path,
            )

    @pytest.mark.parametrize(
        "command",
        [
            "implement",
            "review",
            "accept",
            "merge",
            "status",
            "dashboard",
            "tasks-finalize",
        ],
    )
    def test_cli_driven_commands_return_context(self, command: str, tmp_path: Path) -> None:
        """CLI-driven commands resolve and return a MissionContext."""
        mock_ctx = _make_mock_context(wp_code="WP01")
        with patch(
            "specify_cli.shims.entrypoints.resolve_or_load",
            return_value=mock_ctx,
        ):
            result = shim_dispatch(
                command=command,
                agent="claude",
                raw_args="WP01 --feature 057-test",
                context_token=None,
                repo_root=tmp_path,
            )
            assert result is mock_ctx

    @pytest.mark.parametrize(
        "command",
        [
            "specify",
            "plan",
            "tasks",
            "tasks-outline",
            "tasks-packages",
            "checklist",
            "analyze",
            "research",
            "charter",
        ],
    )
    def test_prompt_driven_commands_return_none(self, command: str, tmp_path: Path) -> None:
        """Prompt-driven commands return None without calling resolve_or_load."""
        with patch(
            "specify_cli.shims.entrypoints.resolve_or_load",
        ) as mock_resolve:
            result = shim_dispatch(
                command=command,
                agent="claude",
                raw_args="WP01 --feature 057-test",
                context_token=None,
                repo_root=tmp_path,
            )
            assert result is None
            mock_resolve.assert_not_called()

    @pytest.mark.parametrize("internal", ["doctor", "materialize", "debug"])
    def test_internal_commands_rejected(self, internal: str, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown shim command"):
            shim_dispatch(
                command=internal,
                agent="claude",
                raw_args="WP01 --feature 057-test",
                context_token=None,
                repo_root=tmp_path,
            )

"""Tests for `spec-kitty context info` display behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import context
from specify_cli.workspace.context import WorkspaceContext, save_context

pytestmark = [pytest.mark.fast]


def test_context_info_displays_unknown_when_base_commit_missing(
    tmp_path: Path, monkeypatch
) -> None:
    save_context(
        tmp_path,
        WorkspaceContext(
            wp_id="WP01",
            mission_slug="001-feature",
            worktree_path=".worktrees/001-feature-lane-a",
            branch_name="kitty/mission-001-feature-lane-a",
            base_branch="kitty/mission-001-feature",
            base_commit=None,
            dependencies=[],
            created_at="2026-01-25T12:00:00Z",
            created_by="recovery",
            vcs_backend="git",
            lane_id="lane-a",
            lane_wp_ids=["WP01"],
            current_wp="WP01",
        ),
    )
    monkeypatch.setattr(context, "find_repo_root", lambda: tmp_path)

    result = CliRunner().invoke(
        context.app,
        ["info", "--workspace", "001-feature-lane-a"],
    )

    assert result.exit_code == 0
    assert "Base Commit" in result.stdout
    assert "unknown" in result.stdout

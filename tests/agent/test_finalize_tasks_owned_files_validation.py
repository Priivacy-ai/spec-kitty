"""Agent-facing finalize-tasks ownership validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.mission import INVALID_WP_OWNED_FILES_KITTY_SPECS
from tests.tasks.test_finalize_tasks_owned_files_validation import (
    _build_feature,
    _invoke_finalize,
    _json_payload,
)

pytestmark = pytest.mark.fast


def test_agent_finalize_error_names_offending_wp_and_path(tmp_path: Path) -> None:
    feature_dir = _build_feature(
        tmp_path,
        owned_file="kitty-specs/077-invalid-owned-files/tasks.md",
    )

    result, _safe_commit = _invoke_finalize(tmp_path, feature_dir, ["--validate-only"])

    assert result.exit_code == 1
    payload = _json_payload(result.stdout)
    assert payload["error_code"] == INVALID_WP_OWNED_FILES_KITTY_SPECS
    assert payload["invalid_owned_files"] == [
        {
            "wp_id": "WP01",
            "path": "kitty-specs/077-invalid-owned-files/tasks.md",
        }
    ]

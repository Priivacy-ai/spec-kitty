"""
Unsafe Mission Slug Error-Surface Tests

The traversal guard (``core.paths.assert_safe_path_segment``) fails closed on an
unsafe ``--mission`` value, but the ``ValueError`` it raises used to escape the
handlers that only caught ``StatusReadPathNotFound``. The result was a raw
Python traceback: on ``orchestrator-api`` that broke the JSON machine contract
external orchestrators parse, and on ``next`` it broke the clean typed-error
contract every other malformed-input path already honoured.

These tests pin the error surface, not the guard itself — traversal is still
rejected either way.

Target:
- src/specify_cli/orchestrator_api/commands.py::_resolve_mission_dir_or_fail
- src/specify_cli/cli/commands/next_cmd.py::_emit_invalid_mission_error
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands.next_cmd import _emit_invalid_mission_error
from specify_cli.orchestrator_api.commands import _resolve_mission_dir_or_fail

pytestmark = [pytest.mark.adversarial, pytest.mark.fast]

UNSAFE_SLUGS = [
    ("../traversal", "Parent-directory traversal"),
    ("..", "Bare parent directory"),
    ("a/../b", "Embedded traversal"),
]


class TestOrchestratorApiEnvelope:
    """An unsafe slug must leave through the JSON envelope, never a traceback."""

    @pytest.mark.parametrize("slug,description", UNSAFE_SLUGS)
    def test_unsafe_slug_emits_valid_json_envelope(
        self, slug: str, description: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        with pytest.raises(typer.Exit) as exc_info:
            _resolve_mission_dir_or_fail("orchestrator-api.mission-state", tmp_path, slug)

        assert exc_info.value.exit_code != 0, f"Must exit non-zero ({description})"

        stdout = capsys.readouterr().out
        envelope = json.loads(stdout)  # raises if the contract was broken

        assert envelope["success"] is False
        assert envelope["error_code"] == "USAGE_ERROR"
        assert slug in envelope["data"]["mission_slug"]
        assert "safe path segment" in envelope["data"]["message"]

    def test_traceback_is_not_printed(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        """Regression guard: the ValueError must not reach the top level."""
        with pytest.raises(typer.Exit):
            _resolve_mission_dir_or_fail("orchestrator-api.list-ready", tmp_path, "../traversal")

        captured = capsys.readouterr()
        assert "Traceback" not in captured.out
        assert "Traceback" not in captured.err


class TestNextCommandTypedError:
    """``next`` must report an unsafe slug cleanly in both output modes."""

    def test_json_mode_emits_invalid_mission(self, capsys: pytest.CaptureFixture[str]):
        _emit_invalid_mission_error("Not a safe path segment: '../traversal'", json_output=True)

        payload = json.loads(capsys.readouterr().out)
        assert payload["result"] == "error"
        assert payload["error_code"] == "INVALID_MISSION"
        assert payload["next_step"]

    def test_human_mode_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]):
        _emit_invalid_mission_error("Not a safe path segment: '../traversal'", json_output=False)

        captured = capsys.readouterr()
        assert not captured.out, "Human-mode diagnostics belong on stderr"
        assert "Not a safe path segment" in captured.err
        assert "Next:" in captured.err

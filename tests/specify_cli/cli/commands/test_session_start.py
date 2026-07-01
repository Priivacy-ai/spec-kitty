"""T021 — Tests for the session-start CLI command.

Covers: project found/not-found, exit-0 guarantee, _find_project_root traversal,
exception swallowing, and NFR-001 performance (<200ms).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

# ---------------------------------------------------------------------------
# Ensure the worktree's src/ takes priority over the main-repo editable install
# so that specify_cli.session_presence resolves to the worktree package.
# ---------------------------------------------------------------------------
_WORKTREE_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_WORKTREE_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC))

from specify_cli.cli.commands.session_start import (  # noqa: E402
    _find_project_root,
    session_start,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Build a minimal typer app for testing the session_start command
_app = typer.Typer()
_app.command()(session_start)

runner = CliRunner()


@pytest.fixture
def spec_project(tmp_path: Path) -> Path:
    """A minimal spec-kitty project with .kittify/."""
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".claude").mkdir()
    return tmp_path


class TestSessionStartInsideProject:
    def test_exit_0_inside_project(
        self, spec_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(spec_project)
        with (
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch("importlib.metadata.version", return_value="3.2.0"),
            patch("specify_cli.compat.plan", side_effect=Exception("no compat")),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            result = runner.invoke(_app, [])
        assert result.exit_code == 0

    def test_outputs_render_result_inside_project(
        self, spec_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.session_presence.content import SECTION_OPEN

        monkeypatch.chdir(spec_project)
        with (
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch("importlib.metadata.version", return_value="3.2.0"),
            patch("specify_cli.compat.plan", side_effect=Exception("no compat")),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            result = runner.invoke(_app, [])
        assert SECTION_OPEN in result.output


class TestSessionStartOutsideProject:
    def test_exit_0_outside_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No .kittify/ present: exit 0, no output."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(_app, [])
        assert result.exit_code == 0

    def test_no_output_outside_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(_app, [])
        assert result.output.strip() == ""


class TestFindProjectRoot:
    def test_finds_kittify_in_cwd(self, spec_project: Path) -> None:
        original_cwd = os.getcwd()
        os.chdir(spec_project)
        try:
            root = _find_project_root()
            assert root == spec_project
        finally:
            os.chdir(original_cwd)

    def test_walks_up_from_nested_subdir(self, spec_project: Path) -> None:
        nested = spec_project / "a" / "b" / "c"
        nested.mkdir(parents=True)
        original_cwd = os.getcwd()
        os.chdir(nested)
        try:
            root = _find_project_root()
            assert root == spec_project
        finally:
            os.chdir(original_cwd)

    def test_returns_none_at_filesystem_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_find_project_root() returns None when no .kittify/ is found anywhere."""
        monkeypatch.chdir(tmp_path)
        # tmp_path has no .kittify/
        root = _find_project_root()
        assert root is None


class TestExitZeroGuarantee:
    def test_exit_0_on_build_content_exception(
        self, spec_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exception in _build_content(): exit 0, no traceback output."""
        monkeypatch.chdir(spec_project)
        with patch(
            "specify_cli.session_presence.manager.SessionPresenceManager._build_content",
            side_effect=RuntimeError("unexpected crash"),
        ):
            result = runner.invoke(_app, [])
        assert result.exit_code == 0
        assert "Traceback" not in result.output

    def test_exit_0_on_load_agent_config_exception(
        self, spec_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exception in load_agent_config(): exit 0, no output."""
        monkeypatch.chdir(spec_project)
        with patch(
            "specify_cli.core.agent_config.load_agent_config",
            side_effect=RuntimeError("config load failure"),
        ):
            result = runner.invoke(_app, [])
        assert result.exit_code == 0


class TestNFR001Performance:
    def test_session_start_completes_under_200ms(
        self, spec_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NFR-001: session-start must complete in <200ms on a warm filesystem.

        All I/O is mocked to eliminate variability and measure only the
        command dispatch overhead itself.
        """
        monkeypatch.chdir(spec_project)
        with (
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch("importlib.metadata.version", return_value="3.2.0"),
            patch("specify_cli.compat.plan", side_effect=Exception("no compat")),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            start = time.monotonic()
            result = runner.invoke(_app, [])
            elapsed_ms = (time.monotonic() - start) * 1000

        assert result.exit_code == 0
        assert elapsed_ms < 200, (
            f"session-start took {elapsed_ms:.1f}ms — exceeds NFR-001 200ms budget"
        )

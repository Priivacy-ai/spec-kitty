#!/usr/bin/env python3
"""
Test cases for the gitignore management and Codex security functionality.
"""

import tempfile
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

# Add the src directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from specify_cli import ensure_gitignore_entries, handle_codex_security  # noqa: E402


def test_ensure_gitignore_entries_new_file():
    """Test that ensure_gitignore_entries creates a new .gitignore file with entries."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        entries = [".codex/"]

        # Call the function
        result = ensure_gitignore_entries(project_path, entries)

        # Check that it returned True (file was modified)
        assert result

        # Check that .gitignore file was created
        gitignore_path = project_path / ".gitignore"
        assert gitignore_path.exists()

        # Check the content
        content = gitignore_path.read_text()
        assert "# Added by Spec Kitty CLI (auto-managed)" in content
        assert ".codex/" in content


def test_ensure_gitignore_entries_existing_file():
    """Test that ensure_gitignore_entries adds entries to existing .gitignore file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        gitignore_path = project_path / ".gitignore"

        # Create an existing .gitignore file
        existing_content = "node_modules/\n*.log\n"
        gitignore_path.write_text(existing_content)

        entries = [".codex/"]

        # Call the function
        result = ensure_gitignore_entries(project_path, entries)

        # Check that it returned True (file was modified)
        assert result

        # Check the content
        content = gitignore_path.read_text()
        assert existing_content in content
        assert "# Added by Spec Kitty CLI (auto-managed)" in content
        assert ".codex/" in content


def test_ensure_gitignore_entries_existing_entry():
    """Test that ensure_gitignore_entries doesn't duplicate existing entries."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        gitignore_path = project_path / ".gitignore"

        # Create an existing .gitignore file with .codex/ already present
        existing_content = "node_modules/\n*.log\n.codex/\n"
        gitignore_path.write_text(existing_content)

        entries = [".codex/"]

        # Call the function
        result = ensure_gitignore_entries(project_path, entries)

        # Check that it returned False (file was not modified)
        assert not result

        # Check that content is unchanged
        content = gitignore_path.read_text()
        assert content == existing_content


def test_ensure_gitignore_entries_multiple_entries():
    """Test that ensure_gitignore_entries handles multiple entries correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        gitignore_path = project_path / ".gitignore"

        # Create an existing .gitignore file
        existing_content = "node_modules/\n*.log\n"
        gitignore_path.write_text(existing_content)

        entries = [".codex/", ".env", "secrets.txt"]

        # Call the function
        result = ensure_gitignore_entries(project_path, entries)

        # Check that it returned True (file was modified)
        assert result

        # Check the content
        content = gitignore_path.read_text()
        assert existing_content in content
        assert "# Added by Spec Kitty CLI (auto-managed)" in content
        assert ".codex/" in content
        assert ".env" in content
        assert "secrets.txt" in content


def test_handle_codex_security_adds_gitignore_when_codex_selected(tmp_path, monkeypatch):
    """Test that handle_codex_security adds .codex/ to .gitignore when Codex is selected."""
    captured: list[str] = []
    mock_console = MagicMock()
    mock_console.print = lambda msg, *_, **__: captured.append(str(msg))

    handle_codex_security(tmp_path, ["codex"], mock_console)

    # Check that .gitignore was updated
    gitignore_path = tmp_path / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text()
    assert ".codex/" in content

    # Check that CODEX_HOME instructions were displayed
    assert any("CODEX_HOME" in msg for msg in captured)
    assert any("Updated .gitignore" in msg for msg in captured)


def test_handle_codex_security_adds_gitignore_when_codex_dir_exists(tmp_path, monkeypatch):
    """Test that handle_codex_security adds .codex/ to .gitignore when .codex directory exists."""
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()

    captured: list[str] = []
    mock_console = MagicMock()
    mock_console.print = lambda msg, *_, **__: captured.append(str(msg))

    handle_codex_security(tmp_path, [], mock_console)

    gitignore_path = tmp_path / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text()
    assert ".codex/" in content
    assert any("Updated .gitignore" in msg for msg in captured)


def test_handle_codex_security_warns_when_auth_tracked(tmp_path, monkeypatch):
    """Test that handle_codex_security warns when auth.json is tracked in git."""
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    auth_file = codex_dir / "auth.json"
    auth_file.write_text("{}", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    messages: list[str] = []
    mock_console = MagicMock()
    mock_console.print = lambda msg, *_, **__: messages.append(str(msg))

    def fake_run(*_, **__):
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr("specify_cli.subprocess.run", fake_run)

    handle_codex_security(tmp_path, ["codex"], mock_console)

    # Check for tracked file warning
    tracked_warning = "git rm --cached .codex/auth.json"
    assert any(tracked_warning in msg for msg in messages)
    assert any("auth.json" in msg and "tracked" in msg for msg in messages)


def test_handle_codex_security_no_action_when_not_needed(tmp_path):
    """Test that handle_codex_security does nothing when Codex is not selected and no .codex dir exists."""
    mock_console = MagicMock()
    captured: list[str] = []
    mock_console.print = lambda msg, *_, **__: captured.append(str(msg))

    handle_codex_security(tmp_path, ["claude", "gemini"], mock_console)

    # Check that no .gitignore was created
    gitignore_path = tmp_path / ".gitignore"
    assert not gitignore_path.exists()

    # Check that no messages were printed
    assert len(captured) == 0


def test_handle_codex_security_shows_codex_home_only_when_selected(tmp_path):
    """Test that CODEX_HOME instructions are only shown when Codex is selected, not just when dir exists."""
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()

    mock_console = MagicMock()
    captured: list[str] = []
    mock_console.print = lambda msg, *_, **__: captured.append(str(msg))

    # Test with .codex directory existing but Codex not selected
    handle_codex_security(tmp_path, [], mock_console)
    assert not any("CODEX_HOME" in msg for msg in captured)

    # Clear captured messages
    captured.clear()

    # Test with Codex selected
    handle_codex_security(tmp_path, ["codex"], mock_console)
    assert any("CODEX_HOME" in msg for msg in captured)
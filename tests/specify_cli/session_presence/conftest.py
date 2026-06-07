"""Shared fixtures for session_presence tests.

T017 — conftest.py + __init__.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure the worktree's src/ takes priority over the main-repo editable install
# so that specify_cli.session_presence resolves to the worktree package.
# ---------------------------------------------------------------------------
_WORKTREE_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_WORKTREE_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC))

from specify_cli.session_presence.content import SessionPresenceContent  # noqa: E402


@pytest.fixture
def healthy_content() -> SessionPresenceContent:
    """SessionPresenceContent in healthy state."""
    return SessionPresenceContent("3.2.0", "my-project", "healthy", None)


@pytest.fixture
def upgrade_content() -> SessionPresenceContent:
    """SessionPresenceContent with upgrade available."""
    return SessionPresenceContent("3.2.0", "my-project", "upgrade-available", "3.3.0")


@pytest.fixture
def migration_content() -> SessionPresenceContent:
    """SessionPresenceContent requiring migration."""
    return SessionPresenceContent("3.2.0", "my-project", "migration-required", None)


@pytest.fixture
def claude_project(tmp_path: Path) -> Path:
    """A minimal spec-kitty project directory with .kittify/ and .claude/."""
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".claude").mkdir()
    return tmp_path

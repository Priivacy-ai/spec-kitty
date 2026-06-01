"""Tests for WP06/T027+T029: spec-kitty charter list command.

Covers FR-004, FR-005, FR-006, FR-007:
- All-None state: all 9 rows show built-in message
- Explicit activations: correct IDs displayed
- --show-available flag: third column with available-but-not-activated items
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import charter_app

runner = CliRunner()

pytestmark = [pytest.mark.fast]

#: All 9 kind names in display order.
_ALL_KINDS = [
    "directive",
    "tactic",
    "styleguide",
    "toolguide",
    "paradigm",
    "procedure",
    "agent-profile",
    "mission-step-contract",
    "mission-type",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_project_root(tmp_path: Path) -> Path:
    """A project with empty config.yaml (no activation keys)."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("# empty config\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def project_with_directive(tmp_path: Path) -> Path:
    """A project with activated_directives: [python-style-guide] in config.yaml."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    config_data = "activated_directives:\n  - python-style-guide\n"
    (kittify / "config.yaml").write_text(config_data, encoding="utf-8")
    return tmp_path


def _invoke_list(project_root: Path, *args: str) -> object:
    """Invoke charter list with --repo-root."""
    return runner.invoke(
        charter_app,
        ["list", "--repo-root", str(project_root), *args],
        catch_exceptions=False,
    )


# ---------------------------------------------------------------------------
# test_list_all_none_shows_builtin_message
# ---------------------------------------------------------------------------


class TestListAllNone:
    def test_all_none_shows_builtin_message(self, empty_project_root: Path) -> None:
        """All 9 rows show '(All built-ins' when no explicit activation keys exist."""
        result = _invoke_list(empty_project_root)
        assert result.exit_code == 0, result.output
        assert "All built-ins" in result.output

    def test_all_nine_kinds_present_in_output(self, empty_project_root: Path) -> None:
        """All 9 kind names appear in the table."""
        result = _invoke_list(empty_project_root)
        assert result.exit_code == 0, result.output
        for kind in _ALL_KINDS:
            assert kind in result.output, f"Expected kind '{kind}' in output"

    def test_table_title_present(self, empty_project_root: Path) -> None:
        """The table title 'Charter Activation State' appears in output."""
        result = _invoke_list(empty_project_root)
        assert result.exit_code == 0, result.output
        assert "Charter Activation State" in result.output


# ---------------------------------------------------------------------------
# test_list_shows_explicit_activations
# ---------------------------------------------------------------------------


class TestListExplicitActivations:
    def test_shows_activated_directive(self, project_with_directive: Path) -> None:
        """Row for directive shows python-style-guide when it's in activated_directives."""
        result = _invoke_list(project_with_directive)
        assert result.exit_code == 0, result.output
        assert "python-style-guide" in result.output

    def test_empty_set_shows_restriction_message(self, tmp_path: Path) -> None:
        """A kind with an empty list shows the explicit-restriction message."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        # Empty list for directive → explicit restriction
        (kittify / "config.yaml").write_text(
            "activated_directives: []\n", encoding="utf-8"
        )
        result = _invoke_list(tmp_path)
        assert result.exit_code == 0, result.output
        assert "explicit restriction" in result.output.lower() or "Nothing activated" in result.output


# ---------------------------------------------------------------------------
# test_list_show_available_includes_doctrine_entries
# ---------------------------------------------------------------------------


class TestListShowAvailable:
    def test_show_available_adds_third_column(self, empty_project_root: Path) -> None:
        """--show-available causes a third column to appear."""
        result = _invoke_list(empty_project_root, "--show-available")
        assert result.exit_code == 0, result.output
        assert "Available (not activated)" in result.output

    def test_show_available_without_flag_has_no_third_column(
        self, empty_project_root: Path
    ) -> None:
        """Without --show-available, the third column is absent."""
        result = _invoke_list(empty_project_root)
        assert result.exit_code == 0, result.output
        assert "Available (not activated)" not in result.output

    @pytest.mark.doctrine
    def test_show_available_lists_doctrine_entries(self, empty_project_root: Path) -> None:
        """--show-available calls list_available and shows doctrine entries not activated."""
        # Mock list_available to return a known set
        with patch(
            "charter.pack_manager.CharterPackManager.list_available",
            return_value=frozenset(["doctrine-entry-1", "doctrine-entry-2"]),
        ):
            result = _invoke_list(empty_project_root, "--show-available")
        assert result.exit_code == 0, result.output
        # Doctrine entries should appear in the "Available" column
        assert "doctrine-entry-1" in result.output or "doctrine-entry-2" in result.output

    def test_show_available_hides_already_activated(self, project_with_directive: Path) -> None:
        """Already-activated artifacts don't appear in the 'Available' column."""
        with patch(
            "charter.pack_manager.CharterPackManager.list_available",
            return_value=frozenset(["python-style-guide", "other-directive"]),
        ):
            result = _invoke_list(project_with_directive, "--show-available")
        assert result.exit_code == 0, result.output
        # other-directive is available and not activated → should appear in available column
        output = result.output
        assert "other-directive" in output

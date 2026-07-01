"""Tests for m_0_9_4_roo_deprecation migration.

Covers:
- T031: roo absent from AI_CHOICES and AGENT_DIRS after migration
- T032: deprecation notice emitted when .roo/ detected (panel path)
- T032: .roo/ directory is NOT deleted
- T033: roo removed from .kittify/config.yaml when present
- T033: migration is idempotent when roo already absent from config
- detect() returns True when .roo/ exists or roo in config.yaml
- detect() returns False when neither condition is met
- can_apply() always returns (True, "")
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config_with_roo(project_root: Path) -> None:
    """Write a minimal .kittify/config.yaml that includes roo.

    Uses ``agents.available`` dict format (matching save_agent_config output).
    """
    kittify = project_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        "agents:\n  available:\n  - claude\n  - roo\n  - codex\n  auto_commit: true\n",
        encoding="utf-8",
    )


def _write_config_without_roo(project_root: Path) -> None:
    kittify = project_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        "agents:\n  available:\n  - claude\n  - codex\n  auto_commit: true\n",
        encoding="utf-8",
    )


def _create_roo_dir(project_root: Path) -> Path:
    roo = project_root / ".roo"
    roo.mkdir(parents=True, exist_ok=True)
    (roo / "commands").mkdir()
    return roo


# ---------------------------------------------------------------------------
# Import the migration class under test
# ---------------------------------------------------------------------------


def _get_migration() -> object:
    """Import RooDeprecationMigration avoiding cached module state."""
    from specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation import (
        RooDeprecationMigration,
    )

    return RooDeprecationMigration()


# ---------------------------------------------------------------------------
# T031 — roo absent from AI_CHOICES and AGENT_DIRS
# ---------------------------------------------------------------------------


class TestRooRemovedFromStaticConfig:
    def test_roo_not_in_ai_choices(self) -> None:
        from specify_cli.core.config import AI_CHOICES

        assert "roo" not in AI_CHOICES, (
            "'roo' must be removed from AI_CHOICES (Roo Code shut down 2026-05-15)"
        )

    def test_roo_not_in_agent_command_config(self) -> None:
        from specify_cli.core.config import AGENT_COMMAND_CONFIG

        assert "roo" not in AGENT_COMMAND_CONFIG

    def test_roo_not_in_agent_skill_config(self) -> None:
        from specify_cli.core.config import AGENT_SKILL_CONFIG

        assert "roo" not in AGENT_SKILL_CONFIG

    def test_roo_not_in_agent_dirs(self) -> None:
        from specify_cli.agent_utils.directories import AGENT_DIRS

        dirs = [d for d, _ in AGENT_DIRS]
        assert ".roo" not in dirs, "'roo' agent dir must be removed from AGENT_DIRS"

    def test_roo_not_in_agent_dir_to_key(self) -> None:
        from specify_cli.agent_utils.directories import AGENT_DIR_TO_KEY

        assert ".roo" not in AGENT_DIR_TO_KEY


# ---------------------------------------------------------------------------
# T032 — detect() logic
# ---------------------------------------------------------------------------


class TestRooDeprecationDetect:
    def test_detect_true_when_roo_dir_present(self, tmp_path: Path) -> None:
        _create_roo_dir(tmp_path)
        migration = _get_migration()
        assert migration.detect(tmp_path) is True  # type: ignore[union-attr]

    def test_detect_true_when_roo_in_config(self, tmp_path: Path) -> None:
        _write_config_with_roo(tmp_path)
        migration = _get_migration()
        assert migration.detect(tmp_path) is True  # type: ignore[union-attr]

    def test_detect_false_when_neither(self, tmp_path: Path) -> None:
        # No .roo/ dir, no roo in config
        _write_config_without_roo(tmp_path)
        migration = _get_migration()
        assert migration.detect(tmp_path) is False  # type: ignore[union-attr]

    def test_detect_false_when_no_kittify(self, tmp_path: Path) -> None:
        migration = _get_migration()
        assert migration.detect(tmp_path) is False  # type: ignore[union-attr]


class TestRooDeprecationCanApply:
    def test_can_apply_always_true(self, tmp_path: Path) -> None:
        migration = _get_migration()
        can, reason = migration.can_apply(tmp_path)  # type: ignore[union-attr]
        assert can is True
        assert reason == ""


# ---------------------------------------------------------------------------
# T032 — deprecation notice emitted; .roo/ preserved
# ---------------------------------------------------------------------------


class TestRooDeprecationNotice:
    def test_roo_dir_preserved_after_migration(self, tmp_path: Path) -> None:
        roo_dir = _create_roo_dir(tmp_path)
        migration = _get_migration()

        with patch("specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation._emit_deprecation_notice"):
            result = migration.apply(tmp_path, dry_run=False)  # type: ignore[union-attr]

        assert roo_dir.exists(), ".roo/ directory must NOT be deleted by migration"
        assert result.success is True

    def test_emit_notice_called_when_roo_dir_present(self, tmp_path: Path) -> None:
        _create_roo_dir(tmp_path)
        migration = _get_migration()

        with patch(
            "specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation._emit_deprecation_notice"
        ) as mock_emit:
            migration.apply(tmp_path, dry_run=False)  # type: ignore[union-attr]

        mock_emit.assert_called_once()

    def test_emit_notice_not_called_when_roo_dir_absent(self, tmp_path: Path) -> None:
        # Only roo in config — no .roo/ dir
        _write_config_with_roo(tmp_path)
        migration = _get_migration()

        with patch(
            "specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation._emit_deprecation_notice"
        ) as mock_emit:
            migration.apply(tmp_path, dry_run=False)  # type: ignore[union-attr]

        mock_emit.assert_not_called()

    def test_dry_run_does_not_modify_config(self, tmp_path: Path) -> None:
        _write_config_with_roo(tmp_path)
        migration = _get_migration()
        config_path = tmp_path / ".kittify" / "config.yaml"
        original = config_path.read_text()

        with patch("specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation._emit_deprecation_notice"):
            result = migration.apply(tmp_path, dry_run=True)  # type: ignore[union-attr]

        assert result.success is True
        assert config_path.read_text() == original, "dry_run must not mutate config.yaml"

    def test_emit_deprecation_notice_prints_rich_panel(self) -> None:
        """_emit_deprecation_notice calls Rich Console.print with a Panel."""
        from specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation import (
            _emit_deprecation_notice,
        )

        mock_console = MagicMock()
        # Console is imported inside the function, so patch at rich.console level
        with patch("rich.console.Console", return_value=mock_console):
            _emit_deprecation_notice()

        mock_console.print.assert_called_once()
        # Verify a Panel was passed to console.print
        from rich.panel import Panel

        args, _ = mock_console.print.call_args
        assert isinstance(args[0], Panel)

    def test_emit_deprecation_notice_falls_back_on_exception(self) -> None:
        """Notice failure must not raise — falls back to logging.warning."""
        from specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation import (
            _emit_deprecation_notice,
        )

        # Simulate Console.print raising an unexpected error
        mock_console = MagicMock()
        mock_console.print.side_effect = RuntimeError("unexpected")
        with patch("rich.console.Console", return_value=mock_console):
            # Must not raise — exception is caught by the broad BLE001 guard
            _emit_deprecation_notice()


# ---------------------------------------------------------------------------
# T033 — roo removed from config.yaml
# ---------------------------------------------------------------------------


class TestRemoveRooFromConfig:
    def test_removes_roo_from_config_yaml(self, tmp_path: Path) -> None:
        _write_config_with_roo(tmp_path)
        migration = _get_migration()

        with patch("specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation._emit_deprecation_notice"):
            result = migration.apply(tmp_path, dry_run=False)  # type: ignore[union-attr]

        assert result.success is True

        # Verify roo was removed from the config
        from specify_cli.core.agent_config import get_configured_agents

        agents = get_configured_agents(tmp_path)
        assert "roo" not in agents
        assert "claude" in agents  # other agents preserved
        assert "codex" in agents

    def test_idempotent_when_roo_already_absent(self, tmp_path: Path) -> None:
        _write_config_without_roo(tmp_path)
        migration = _get_migration()

        # detect() should return False (no .roo/ dir, roo not in config)
        assert migration.detect(tmp_path) is False  # type: ignore[union-attr]

        # apply() is still safe to call
        result = migration.apply(tmp_path, dry_run=False)  # type: ignore[union-attr]
        assert result.success is True
        assert result.changes_made == []

    def test_changes_listed_in_result(self, tmp_path: Path) -> None:
        _write_config_with_roo(tmp_path)
        migration = _get_migration()

        with patch("specify_cli.upgrade.migrations.m_0_9_4_roo_deprecation._emit_deprecation_notice"):
            result = migration.apply(tmp_path, dry_run=False)  # type: ignore[union-attr]

        assert any("roo" in c.lower() for c in result.changes_made)


# ---------------------------------------------------------------------------
# Migration registration
# ---------------------------------------------------------------------------


class TestMigrationRegistration:
    def test_migration_registered(self) -> None:
        """RooDeprecationMigration must be registered in MigrationRegistry."""
        from specify_cli.upgrade.migrations import auto_discover_migrations
        from specify_cli.upgrade.registry import MigrationRegistry

        auto_discover_migrations()
        assert "0_9_4_roo_deprecation" in MigrationRegistry._migrations

    def test_migration_id_correct(self) -> None:
        migration = _get_migration()
        assert migration.migration_id == "0_9_4_roo_deprecation"  # type: ignore[union-attr]

    def test_runs_on_worktrees_false(self) -> None:
        migration = _get_migration()
        assert migration.runs_on_worktrees is False  # type: ignore[union-attr]

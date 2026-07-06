"""T021 — Tests for SessionPresenceManager orchestration.

Covers install/update flows, dry-run, health determination, and exception handling.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.session_presence.manager import InstallResult, SessionPresenceManager

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _make_agent_config(available: list[str] | None = None) -> MagicMock:
    config = MagicMock()
    config.available = available or ["claude"]
    config.project_slug = "test-project"
    return config


def _make_manager(
    project_root: Path,
    available: list[str] | None = None,
) -> SessionPresenceManager:
    return SessionPresenceManager(
        project_root=project_root,
        agent_config=_make_agent_config(available),
    )


class TestInstall:
    def test_calls_write_when_can_write_and_no_presence(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        mock_writer = MagicMock()
        mock_writer.can_write.return_value = True
        mock_writer.has_presence.return_value = False

        with (
            patch(
                "specify_cli.session_presence.manager.get_writer",
                return_value=mock_writer,
            ),
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            result = manager.install()

        mock_writer.write.assert_called_once()
        assert len(result.changes) == 1

    def test_skips_when_has_presence_true(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        mock_writer = MagicMock()
        mock_writer.can_write.return_value = True
        mock_writer.has_presence.return_value = True

        with (
            patch(
                "specify_cli.session_presence.manager.get_writer",
                return_value=mock_writer,
            ),
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            result = manager.install()

        mock_writer.write.assert_not_called()
        assert len(result.changes) == 0

    def test_null_writer_skipped_silently(self, tmp_path: Path) -> None:
        """NullWriter (can_write=False) is skipped silently with no warnings."""
        manager = _make_manager(tmp_path)
        mock_writer = MagicMock()
        mock_writer.can_write.return_value = False

        with (
            patch(
                "specify_cli.session_presence.manager.get_writer",
                return_value=mock_writer,
            ),
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            result = manager.install()

        mock_writer.write.assert_not_called()
        assert len(result.warnings) == 0

    def test_returns_install_result_with_changes(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, available=["claude"])
        mock_writer = MagicMock()
        mock_writer.can_write.return_value = True
        mock_writer.has_presence.return_value = False

        with (
            patch(
                "specify_cli.session_presence.manager.get_writer",
                return_value=mock_writer,
            ),
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            result = manager.install()

        assert isinstance(result, InstallResult)
        assert isinstance(result.changes, list)

    def test_catches_writer_exceptions_adds_warnings(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        mock_writer = MagicMock()
        mock_writer.can_write.return_value = True
        mock_writer.has_presence.return_value = False
        mock_writer.write.side_effect = RuntimeError("disk error")

        with (
            patch(
                "specify_cli.session_presence.manager.get_writer",
                return_value=mock_writer,
            ),
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            result = manager.install()

        assert len(result.warnings) == 1
        assert "disk error" in result.warnings[0]


class TestUpdate:
    def test_update_calls_write_regardless_of_presence(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        mock_writer = MagicMock()
        mock_writer.can_write.return_value = True

        with (
            patch(
                "specify_cli.session_presence.manager.get_writer",
                return_value=mock_writer,
            ),
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            manager.update()

        mock_writer.write.assert_called_once()

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        mock_writer = MagicMock()
        mock_writer.can_write.return_value = True

        with (
            patch(
                "specify_cli.session_presence.manager.get_writer",
                return_value=mock_writer,
            ),
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            result = manager.update(dry_run=True)

        mock_writer.write.assert_not_called()
        assert any("Would write" in c for c in result.changes)


class TestBuildContent:
    def test_health_migration_required_when_compat_returns_block(
        self, tmp_path: Path
    ) -> None:
        from specify_cli.compat import Decision

        manager = _make_manager(tmp_path)
        mock_plan_result = MagicMock()
        mock_plan_result.decision = Decision.BLOCK_PROJECT_MIGRATION

        with (
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                return_value=mock_plan_result,
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            content = manager._build_content()

        assert content.health == "migration-required"

    def test_health_upgrade_available_when_newer_version(
        self, tmp_path: Path
    ) -> None:
        manager = _make_manager(tmp_path)

        with (
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = "3.3.0"
            content = manager._build_content()

        assert content.health == "upgrade-available"
        assert content.available_version == "3.3.0"

    def test_health_healthy_when_no_upgrade_no_migration(
        self, tmp_path: Path
    ) -> None:
        from specify_cli.compat import Decision

        manager = _make_manager(tmp_path)
        mock_plan_result = MagicMock()
        mock_plan_result.decision = Decision.ALLOW  # not BLOCK_PROJECT_MIGRATION

        with (
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.0",
            ),
            patch(
                "specify_cli.compat.plan",
                return_value=mock_plan_result,
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = None
            content = manager._build_content()

        assert content.health == "healthy"

    def test_health_healthy_when_cached_latest_is_older_than_installed(
        self, tmp_path: Path
    ) -> None:
        """#2413 regression: a stale PyPI cache (or an rc/dev install newer than
        the published latest) must not report an 'upgrade' to an older version."""
        from specify_cli.compat import Decision

        manager = _make_manager(tmp_path)
        mock_plan_result = MagicMock()
        mock_plan_result.decision = Decision.ALLOW

        with (
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.4",
            ),
            patch(
                "specify_cli.compat.plan",
                return_value=mock_plan_result,
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = "3.2.2"
            content = manager._build_content()

        assert content.health == "healthy"

    def test_health_healthy_when_older_latest_and_compat_raises(
        self, tmp_path: Path
    ) -> None:
        """#2413: the exception-fallback branch must use the same ordering."""
        manager = _make_manager(tmp_path)

        with (
            patch(
                "specify_cli.session_presence.manager.UpgradeChecker"
            ) as mock_checker_cls,
            patch(
                "importlib.metadata.version",
                return_value="3.2.4",
            ),
            patch(
                "specify_cli.compat.plan",
                side_effect=Exception("no compat"),
            ),
        ):
            mock_checker_cls.return_value.get_available_version.return_value = "3.2.2"
            content = manager._build_content()

        assert content.health == "healthy"


class TestUpgradeIsAvailable:
    """Matrix for the #2413 ordering helper."""

    def test_newer_available(self) -> None:
        from specify_cli.session_presence.manager import _upgrade_is_available

        assert _upgrade_is_available("3.3.0", "3.2.4") is True

    def test_equal_versions(self) -> None:
        from specify_cli.session_presence.manager import _upgrade_is_available

        assert _upgrade_is_available("3.2.4", "3.2.4") is False

    def test_older_available_the_2413_bug(self) -> None:
        from specify_cli.session_presence.manager import _upgrade_is_available

        assert _upgrade_is_available("3.2.2", "3.2.4") is False

    def test_prerelease_ordering(self) -> None:
        from specify_cli.session_presence.manager import _upgrade_is_available

        # An installed rc ahead of the published release is NOT upgradable to it.
        assert _upgrade_is_available("3.2.4", "3.2.5rc1") is False
        # A published release IS an upgrade over its own rc.
        assert _upgrade_is_available("3.2.4", "3.2.4rc39") is True

    def test_none_and_empty(self) -> None:
        from specify_cli.session_presence.manager import _upgrade_is_available

        assert _upgrade_is_available(None, "3.2.4") is False
        assert _upgrade_is_available("", "3.2.4") is False

    def test_unparseable_versions(self) -> None:
        from specify_cli.session_presence.manager import _upgrade_is_available

        assert _upgrade_is_available("not-a-version", "3.2.4") is False
        assert _upgrade_is_available("3.3.0", "not-a-version") is False

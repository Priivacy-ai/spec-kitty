"""Tests for specify_cli.runtime.bootstrap — ensure_runtime() and helpers.

Covers:
- T010: ensure_runtime() fast path, slow path, version matching, temp cleanup
- T012: Interrupted update recovery (F-Bootstrap-001, 1A-07)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.runtime.bootstrap import (
    _get_cli_version,
    _lock_exclusive,
    ensure_runtime,
    populate_from_package,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_VERSION = "99.0.0-test"


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set SPEC_KITTY_HOME to a temp dir and return the path."""
    home = tmp_path / "kittify"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    return home


@pytest.fixture()
def fake_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fake package asset root and override discovery.

    Returns the missions directory (what get_package_asset_root returns).
    """
    pkg_root = tmp_path / "package"
    missions = pkg_root / "missions"
    (missions / "software-dev").mkdir(parents=True)
    (missions / "software-dev" / "mission.yaml").write_text("test-mission")
    (missions / "research").mkdir(parents=True)
    (missions / "research" / "mission.yaml").write_text("test-research")

    # Scripts directory (sibling of missions)
    scripts = pkg_root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "validate.py").write_text("# validate")

    # AGENTS.md (sibling of missions)
    (pkg_root / "AGENTS.md").write_text("# Agents")

    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(missions))
    return missions


# ---------------------------------------------------------------------------
# T010: _get_cli_version() tests
# ---------------------------------------------------------------------------


class TestGetCliVersion:
    """_get_cli_version() returns the specify_cli.__version__ string."""

    def test_returns_string(self) -> None:
        version = _get_cli_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_matches_package_version(self) -> None:
        from specify_cli import __version__

        assert _get_cli_version() == __version__


# ---------------------------------------------------------------------------
# T010: _lock_exclusive() tests
# ---------------------------------------------------------------------------


class TestLockExclusive:
    """_lock_exclusive() acquires a file lock on Unix."""

    def test_lock_acquires_on_unix(self, tmp_path: Path) -> None:
        """Lock can be acquired on a new file."""
        lock_file = tmp_path / ".update.lock"
        fd = open(lock_file, "w")
        try:
            _lock_exclusive(fd)
            # No exception means success
        finally:
            fd.close()


# ---------------------------------------------------------------------------
# T010: populate_from_package() tests
# ---------------------------------------------------------------------------


class TestPopulateFromPackage:
    """populate_from_package() copies package assets to target."""

    def test_copies_missions(
        self, tmp_path: Path, fake_assets: Path
    ) -> None:
        target = tmp_path / "staging"
        populate_from_package(target)
        assert (target / "missions" / "software-dev" / "mission.yaml").exists()
        assert (target / "missions" / "research" / "mission.yaml").exists()

    def test_copies_scripts(
        self, tmp_path: Path, fake_assets: Path
    ) -> None:
        target = tmp_path / "staging"
        populate_from_package(target)
        assert (target / "scripts" / "validate.py").exists()

    def test_copies_agents_md(
        self, tmp_path: Path, fake_assets: Path
    ) -> None:
        target = tmp_path / "staging"
        populate_from_package(target)
        assert (target / "AGENTS.md").exists()
        assert (target / "AGENTS.md").read_text() == "# Agents"

    def test_creates_target_dir(
        self, tmp_path: Path, fake_assets: Path
    ) -> None:
        target = tmp_path / "nonexistent" / "staging"
        populate_from_package(target)
        assert target.is_dir()


# ---------------------------------------------------------------------------
# T010: ensure_runtime() unit tests
# ---------------------------------------------------------------------------


class TestEnsureRuntimeFastPath:
    """Fast path: version.lock matches CLI version -- return immediately."""

    def test_fast_path_version_matches(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When version.lock matches, no populate/merge occurs."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        # Pre-populate version.lock
        cache_dir = fake_home / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "version.lock").write_text(FAKE_VERSION)

        # Track whether populate_from_package is called
        with patch(
            "specify_cli.runtime.bootstrap.populate_from_package"
        ) as mock_pop:
            ensure_runtime()
            mock_pop.assert_not_called()

    def test_fast_path_no_lock_acquired(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fast path does not acquire the file lock."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        cache_dir = fake_home / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "version.lock").write_text(FAKE_VERSION)

        with patch(
            "specify_cli.runtime.bootstrap._lock_exclusive"
        ) as mock_lock:
            ensure_runtime()
            mock_lock.assert_not_called()


class TestEnsureRuntimeSlowPath:
    """Slow path: version.lock missing or stale -- full update occurs."""

    def test_slow_path_version_lock_missing(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing version.lock triggers full populate + merge."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        ensure_runtime()

        version_file = fake_home / "cache" / "version.lock"
        assert version_file.exists()
        assert version_file.read_text().strip() == FAKE_VERSION

    def test_slow_path_version_lock_stale(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Stale version.lock triggers update and writes new version."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        # Pre-populate with old version
        cache_dir = fake_home / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "version.lock").write_text("0.1.0-old")

        ensure_runtime()

        assert (cache_dir / "version.lock").read_text().strip() == FAKE_VERSION

    def test_slow_path_creates_home_dir(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Slow path creates ~/.kittify/ if it doesn't exist."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        assert not fake_home.exists()
        ensure_runtime()
        assert fake_home.is_dir()

    def test_slow_path_populates_managed_dirs(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Slow path copies managed directories into ~/.kittify/."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        ensure_runtime()

        assert (fake_home / "missions" / "software-dev" / "mission.yaml").exists()
        assert (fake_home / "missions" / "research" / "mission.yaml").exists()

    def test_slow_path_double_check_after_lock(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If another process wrote version.lock while we waited for lock,
        the double-check avoids redundant work."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        # Simulate: version.lock doesn't exist before lock but does after
        call_count = 0
        original_lock = _lock_exclusive

        def lock_that_creates_version(fd):
            nonlocal call_count
            original_lock(fd)
            call_count += 1
            # Simulate another process finishing while we waited
            cache_dir = fake_home / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / "version.lock").write_text(FAKE_VERSION)

        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._lock_exclusive",
            lock_that_creates_version,
        )

        with patch(
            "specify_cli.runtime.bootstrap.populate_from_package"
        ) as mock_pop:
            ensure_runtime()
            # populate_from_package should NOT be called -- double-check caught it
            mock_pop.assert_not_called()


class TestEnsureRuntimeTempDirCleanup:
    """Temp directory is cleaned up even if an error occurs."""

    def test_temp_dir_cleaned_on_success(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Temp directory is removed after successful update."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        ensure_runtime()

        # No .kittify_update_* directories should remain
        parent = fake_home.parent
        update_dirs = list(parent.glob(".kittify_update_*"))
        assert len(update_dirs) == 0

    def test_temp_dir_cleaned_on_exception(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Temp directory is removed even when populate raises."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        def exploding_populate(target: Path) -> None:
            target.mkdir(parents=True, exist_ok=True)
            (target / "partial-file.txt").write_text("partial")
            raise RuntimeError("Simulated failure during populate")

        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap.populate_from_package",
            exploding_populate,
        )

        with pytest.raises(RuntimeError, match="Simulated failure"):
            ensure_runtime()

        # Temp dir must be cleaned up
        parent = fake_home.parent
        update_dirs = list(parent.glob(".kittify_update_*"))
        assert len(update_dirs) == 0


class TestEnsureRuntimeVersionLockWrittenLast:
    """version.lock is the last file written during update."""

    def test_version_lock_written_after_merge(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """version.lock does not exist until merge completes."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        write_order: list[str] = []
        original_merge = __import__(
            "specify_cli.runtime.merge", fromlist=["merge_package_assets"]
        ).merge_package_assets

        def tracking_merge(source: Path, dest: Path) -> None:
            original_merge(source, dest)
            write_order.append("merge")
            # At this point version.lock should NOT exist yet
            version_file = fake_home / "cache" / "version.lock"
            assert not version_file.exists(), "version.lock written before merge completed"

        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap.merge_package_assets",
            tracking_merge,
        )

        ensure_runtime()

        assert "merge" in write_order
        # Now version.lock should exist
        assert (fake_home / "cache" / "version.lock").exists()


# ---------------------------------------------------------------------------
# T012: Interrupted update recovery (F-Bootstrap-001, 1A-07)
# ---------------------------------------------------------------------------


class TestInterruptedUpdateRecovery:
    """Interrupted update (no version.lock) triggers full bootstrap on next run."""

    def test_interrupted_update_recovery(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing version.lock after partial update triggers re-bootstrap (F-Bootstrap-001, 1A-07)."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        # Simulate interrupted update: ~/.kittify/ exists with some files
        # but no version.lock
        fake_home.mkdir(parents=True)
        (fake_home / "missions" / "software-dev").mkdir(parents=True)
        (fake_home / "missions" / "software-dev" / "stale.yaml").write_text("stale")
        # No version.lock -- simulates interrupted update

        ensure_runtime()

        # Recovery complete: version.lock written
        version_file = fake_home / "cache" / "version.lock"
        assert version_file.exists()
        assert version_file.read_text().strip() == FAKE_VERSION

    def test_interrupted_update_preserves_user_data(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Recovery from interrupted update preserves user-owned files."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        # Simulate partial state with user data
        fake_home.mkdir(parents=True)
        (fake_home / "config.yaml").write_text("user: settings")
        (fake_home / "missions" / "custom").mkdir(parents=True)
        (fake_home / "missions" / "custom" / "mine.yaml").write_text("my mission")

        ensure_runtime()

        # User data preserved
        assert (fake_home / "config.yaml").read_text() == "user: settings"
        assert (fake_home / "missions" / "custom" / "mine.yaml").read_text() == "my mission"

    def test_empty_kittify_treated_as_needing_bootstrap(
        self,
        fake_home: Path,
        fake_assets: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty ~/.kittify/ directory triggers full bootstrap."""
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap._get_cli_version",
            lambda: FAKE_VERSION,
        )

        fake_home.mkdir(parents=True)

        ensure_runtime()

        version_file = fake_home / "cache" / "version.lock"
        assert version_file.exists()
        assert version_file.read_text().strip() == FAKE_VERSION
        # Managed dirs should be populated
        assert (fake_home / "missions" / "software-dev").is_dir()

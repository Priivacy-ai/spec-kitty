"""T019 — Tests for UpgradeChecker TTL/cache/background behavior.

All tests use tmp_path and monkeypatch CACHE_PATH to avoid touching ~/.kittify/.
No network calls are made.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

import specify_cli.session_presence.upgrade_check as upgrade_check_module
from specify_cli.session_presence.upgrade_check import TTL_SECONDS, UpgradeChecker

pytestmark = [pytest.mark.unit]


@pytest.fixture
def patched_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monkeypatch CACHE_PATH to a tmp_path location."""
    cache_file = tmp_path / "last-cli-check.json"
    monkeypatch.setattr(upgrade_check_module, "CACHE_PATH", cache_file)
    monkeypatch.delenv(upgrade_check_module.OPT_OUT_ENV_VAR, raising=False)
    # Also patch the attribute in the module namespace for class usage
    return cache_file


def _write_cache(path: Path, version: str, age_seconds: int = 0) -> None:
    """Write a cache file with the given version and age."""
    checked_at = (
        datetime.now(UTC) - timedelta(seconds=age_seconds)
    ).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"checked_at": checked_at, "latest_version": version}),
        encoding="utf-8",
    )


class TestGetAvailableVersion:
    def test_opt_out_returns_none_even_when_cache_exists(
        self, patched_cache: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SPEC_KITTY_NO_UPGRADE_CHECK disables cached upgrade notices."""
        _write_cache(patched_cache, "9.9.9", age_seconds=60)
        monkeypatch.setenv("SPEC_KITTY_NO_UPGRADE_CHECK", "1")
        checker = UpgradeChecker()
        assert checker.get_available_version() is None

    def test_cache_miss_no_file_returns_none(self, patched_cache: Path) -> None:
        """Cache miss (no file): get_available_version() returns None."""
        checker = UpgradeChecker()
        assert checker.get_available_version() is None

    def test_cache_hit_within_ttl(
        self, patched_cache: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cache hit within TTL: returns cached version, check_in_background NOT called."""
        _write_cache(patched_cache, "3.3.0", age_seconds=60)  # fresh
        checker = UpgradeChecker()
        with patch.object(checker, "check_in_background") as mock_bg:
            result = checker.get_available_version()
        assert result == "3.3.0"
        mock_bg.assert_not_called()

    def test_cache_stale_returns_last_known(
        self, patched_cache: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cache stale (age > TTL): returns last known value."""
        _write_cache(patched_cache, "3.2.0", age_seconds=TTL_SECONDS + 100)
        checker = UpgradeChecker()
        result = checker.get_available_version()
        # Still returns the stale value
        assert result == "3.2.0"

    def test_cache_malformed_json_returns_none(self, patched_cache: Path) -> None:
        """Cache malformed JSON: returns None, no exception raised."""
        patched_cache.parent.mkdir(parents=True, exist_ok=True)
        patched_cache.write_text("NOT JSON {{{", encoding="utf-8")
        checker = UpgradeChecker()
        assert checker.get_available_version() is None

    def test_cache_missing_latest_version_key_returns_none(
        self, patched_cache: Path
    ) -> None:
        """Cache JSON without latest_version key returns None."""
        patched_cache.parent.mkdir(parents=True, exist_ok=True)
        patched_cache.write_text(
            json.dumps({"checked_at": datetime.now(UTC).isoformat()}),
            encoding="utf-8",
        )
        checker = UpgradeChecker()
        assert checker.get_available_version() is None

    def test_cache_malformed_timestamp_returns_none(self, patched_cache: Path) -> None:
        """Cache with malformed checked_at returns None."""
        patched_cache.parent.mkdir(parents=True, exist_ok=True)
        patched_cache.write_text(
            json.dumps({"checked_at": "not-a-date", "latest_version": "3.3.0"}),
            encoding="utf-8",
        )
        checker = UpgradeChecker()
        assert checker.get_available_version() is None


class TestCheckInBackground:
    def test_opt_out_does_not_spawn_subprocess(
        self, patched_cache: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SPEC_KITTY_NO_UPGRADE_CHECK disables background PyPI probes."""
        monkeypatch.setenv("SPEC_KITTY_NO_UPGRADE_CHECK", "1")
        with patch("subprocess.Popen") as mock_popen:
            checker = UpgradeChecker()
            checker.check_in_background()
        mock_popen.assert_not_called()

    def test_subprocess_oserror_does_not_raise(
        self, patched_cache: Path
    ) -> None:
        """check_in_background() with subprocess failure does not raise."""
        with patch("subprocess.Popen", side_effect=OSError("not found")):
            checker = UpgradeChecker()
            # Must not raise
            checker.check_in_background()

    def test_any_exception_does_not_raise(self, patched_cache: Path) -> None:
        """check_in_background() bare except catches any exception."""
        with patch("subprocess.Popen", side_effect=RuntimeError("unexpected")):
            checker = UpgradeChecker()
            result = checker.check_in_background()
        assert result is None

    def test_background_probe_uses_pypi_json_not_uv_pip_index(self, patched_cache: Path) -> None:
        calls: list[list[str]] = []

        with patch("subprocess.Popen", side_effect=lambda argv, **_: calls.append(argv)):
            UpgradeChecker().check_in_background()

        assert calls
        script = calls[0][2]
        assert "https://pypi.org/pypi/spec-kitty-cli/json" in script
        assert "uv pip index" not in script

    def test_mkdir_failure_does_not_raise(
        self, patched_cache: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_in_background() swallows mkdir failures."""
        with patch("subprocess.Popen", side_effect=PermissionError("no access")):
            checker = UpgradeChecker()
            checker.check_in_background()  # Must not raise

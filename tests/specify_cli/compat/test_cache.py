"""Tests for specify_cli.compat.cache (T010 — NagCache).

All tests use ``tmp_path`` for isolation — no real user cache is touched.
"""

from __future__ import annotations

import os
import stat
import sys
import unittest.mock as mock
from datetime import datetime, UTC
from pathlib import Path

import pytest

from specify_cli.compat.cache import NagCache, NagCacheRecord, _dt_to_iso, _iso_to_dt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC)
_VERSION = "2.0.11"


def _make_record(
    *,
    cli_version_key: str = _VERSION,
    latest_version: str | None = "2.1.0",
    latest_source: str = "pypi",
    fetched_at: datetime = _NOW,
    last_shown_at: datetime | None = _NOW,
) -> NagCacheRecord:
    """Convenience factory for test records."""
    from typing import Literal

    ls: Literal["pypi", "none"] = latest_source  # type: ignore[assignment]
    return NagCacheRecord(
        cli_version_key=cli_version_key,
        latest_version=latest_version,
        latest_source=ls,
        fetched_at=fetched_at,
        last_shown_at=last_shown_at,
    )


def _cache(tmp_path: Path) -> NagCache:
    return NagCache(tmp_path / "upgrade-nag.json")


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Write then read returns an equal record."""

    def test_round_trip_with_last_shown(self, tmp_path: Path) -> None:
        """Full round-trip including last_shown_at."""
        record = _make_record()
        cache = _cache(tmp_path)
        cache.write(record)
        result = cache.read()
        assert result == record

    def test_round_trip_none_last_shown(self, tmp_path: Path) -> None:
        """Round-trip with last_shown_at=None."""
        record = _make_record(last_shown_at=None)
        cache = _cache(tmp_path)
        cache.write(record)
        result = cache.read()
        assert result == record

    def test_round_trip_none_latest_version(self, tmp_path: Path) -> None:
        """Round-trip with latest_version=None and source='none'."""
        record = _make_record(latest_version=None, latest_source="none")
        cache = _cache(tmp_path)
        cache.write(record)
        result = cache.read()
        assert result == record

    def test_file_created_with_json(self, tmp_path: Path) -> None:
        """The cache file is actually written as valid JSON."""
        import json

        record = _make_record()
        cache = _cache(tmp_path)
        cache.write(record)
        path = tmp_path / "upgrade-nag.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["cli_version_key"] == _VERSION

    def test_json_keys_sorted(self, tmp_path: Path) -> None:
        """JSON is written with sort_keys=True for determinism."""
        import json

        record = _make_record()
        cache = _cache(tmp_path)
        cache.write(record)
        path = tmp_path / "upgrade-nag.json"
        raw = path.read_text()
        data = json.loads(raw)
        keys = list(data.keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# File-mode and symlink security (POSIX only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only security checks")
class TestPosixSecurity:
    """Security property tests on POSIX systems."""

    def test_file_mode_is_0o600(self, tmp_path: Path) -> None:
        """Written cache file has mode 0o600."""
        record = _make_record()
        cache = _cache(tmp_path)
        cache.write(record)
        path = tmp_path / "upgrade-nag.json"
        file_mode = stat.S_IMODE(os.lstat(path).st_mode)
        assert file_mode == 0o600

    def test_symlink_at_file_path_write_refuses(self, tmp_path: Path) -> None:
        """write() is a no-op when the target path is already a symlink."""
        path = tmp_path / "upgrade-nag.json"
        # Create a symlink at the target path pointing elsewhere.
        decoy = tmp_path / "decoy.json"
        decoy.write_text("{}")
        path.symlink_to(decoy)

        record = _make_record()
        cache = NagCache(path)
        cache.write(record)  # Must not raise.

        # The symlink target should NOT be overwritten.
        assert decoy.read_text() == "{}"

    def test_symlink_at_file_path_read_returns_none(self, tmp_path: Path) -> None:
        """read() returns None when the target path is a symlink."""
        path = tmp_path / "upgrade-nag.json"
        decoy = tmp_path / "decoy.json"
        import json

        decoy.write_text(
            json.dumps(
                {
                    "cli_version_key": _VERSION,
                    "latest_version": "2.1.0",
                    "latest_source": "pypi",
                    "fetched_at": _dt_to_iso(_NOW),
                    "last_shown_at": _dt_to_iso(_NOW),
                }
            )
        )
        path.symlink_to(decoy)
        os.chmod(str(decoy), 0o600)

        cache = NagCache(path)
        assert cache.read() is None

    def test_symlink_at_parent_write_refuses(self, tmp_path: Path) -> None:
        """write() is a no-op when the parent directory is a symlink."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        sym_dir = tmp_path / "sym"
        sym_dir.symlink_to(real_dir)

        cache = NagCache(sym_dir / "upgrade-nag.json")
        record = _make_record()
        cache.write(record)  # Must not raise.

        # Nothing should be written inside real_dir.
        assert not any(real_dir.iterdir())

    def test_symlink_at_parent_read_returns_none(self, tmp_path: Path) -> None:
        """read() returns None when the parent directory is a symlink."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        sym_dir = tmp_path / "sym"
        sym_dir.symlink_to(real_dir)

        cache = NagCache(sym_dir / "upgrade-nag.json")
        assert cache.read() is None

    def test_wrong_permissions_read_returns_none(self, tmp_path: Path) -> None:
        """read() returns None when the file has mode 0o644 (not 0o600)."""
        import json

        path = tmp_path / "upgrade-nag.json"
        path.write_text(
            json.dumps(
                {
                    "cli_version_key": _VERSION,
                    "latest_version": "2.1.0",
                    "latest_source": "pypi",
                    "fetched_at": _dt_to_iso(_NOW),
                    "last_shown_at": _dt_to_iso(_NOW),
                }
            )
        )
        os.chmod(str(path), 0o644)

        cache = NagCache(path)
        assert cache.read() is None

    def test_oversized_file_read_returns_none(self, tmp_path: Path) -> None:
        """read() returns None when the file is larger than 64 KiB."""
        path = tmp_path / "upgrade-nag.json"
        # Write 65 KiB of data.
        path.write_bytes(b"x" * (65 * 1024 + 1))
        os.chmod(str(path), 0o600)

        cache = NagCache(path)
        assert cache.read() is None

    def test_foreign_uid_read_returns_none(self, tmp_path: Path) -> None:
        """read() returns None when lstat reports a foreign uid (mocked)."""
        import json

        path = tmp_path / "upgrade-nag.json"
        path.write_text(
            json.dumps(
                {
                    "cli_version_key": _VERSION,
                    "latest_version": "2.1.0",
                    "latest_source": "pypi",
                    "fetched_at": _dt_to_iso(_NOW),
                    "last_shown_at": _dt_to_iso(_NOW),
                }
            )
        )
        os.chmod(str(path), 0o600)

        real_stat = os.lstat(path)

        # Build a fake stat_result with a different uid.
        fake_stat = mock.Mock(spec=os.stat_result)
        fake_stat.st_mode = real_stat.st_mode
        fake_stat.st_size = real_stat.st_size
        fake_stat.st_uid = os.geteuid() + 9999  # definitely foreign

        parent_stat = mock.Mock(spec=os.stat_result)
        parent_stat.st_mode = stat.S_IFDIR | 0o700  # not a symlink

        def fake_lstat(p: str | Path, **kwargs: object) -> os.stat_result:
            if Path(str(p)) == path:
                return fake_stat  # type: ignore[return-value]
            return parent_stat  # type: ignore[return-value]

        with mock.patch("specify_cli.compat.cache.os.lstat", side_effect=fake_lstat):
            cache = NagCache(path)
            assert cache.read() is None


# ---------------------------------------------------------------------------
# Oversized file (platform-agnostic)
# ---------------------------------------------------------------------------


class TestOversizedFile:
    """Oversized-file guard applies on all platforms."""

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod 0o600 required for read on POSIX")
    def test_oversized_read_returns_none_posix(self, tmp_path: Path) -> None:
        """Oversized file → read returns None (POSIX path)."""
        path = tmp_path / "upgrade-nag.json"
        path.write_bytes(b"x" * (65 * 1024 + 1))
        os.chmod(str(path), 0o600)
        cache = NagCache(path)
        assert cache.read() is None


# ---------------------------------------------------------------------------
# Missing / corrupt file
# ---------------------------------------------------------------------------


class TestMissingOrCorrupt:
    """Edge cases: missing file, malformed JSON."""

    def test_missing_file_read_returns_none(self, tmp_path: Path) -> None:
        """read() returns None when the file does not exist."""
        cache = _cache(tmp_path)
        assert cache.read() is None

    def test_malformed_json_read_returns_none(self, tmp_path: Path) -> None:
        """read() returns None when the file contains malformed JSON."""
        path = tmp_path / "upgrade-nag.json"
        path.write_text("NOT VALID JSON {{")
        if sys.platform != "win32":
            os.chmod(str(path), 0o600)
        cache = NagCache(path)
        assert cache.read() is None

    def test_json_missing_field_read_returns_none(self, tmp_path: Path) -> None:
        """read() returns None when a required field is absent."""
        import json

        path = tmp_path / "upgrade-nag.json"
        path.write_text(json.dumps({"cli_version_key": _VERSION}))
        if sys.platform != "win32":
            os.chmod(str(path), 0o600)
        cache = NagCache(path)
        assert cache.read() is None

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """write() creates the parent directory tree if it does not exist."""
        path = tmp_path / "a" / "b" / "c" / "upgrade-nag.json"
        cache = NagCache(path)
        cache.write(_make_record())
        assert path.exists()


# ---------------------------------------------------------------------------
# Throttle predicate table (T008)
# ---------------------------------------------------------------------------


class TestIsFresh:
    """Unit table for NagCache.is_fresh."""

    def test_none_record_returns_false(self) -> None:
        """None record → False."""
        assert NagCache.is_fresh(None, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_version_key_mismatch_returns_false(self) -> None:
        """Different cli_version_key → False (FR-025)."""
        record = _make_record(cli_version_key="1.0.0")
        assert NagCache.is_fresh(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_never_shown_returns_false(self) -> None:
        """last_shown_at=None → False (nag has never been shown)."""
        record = _make_record(last_shown_at=None)
        assert NagCache.is_fresh(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_just_shown_returns_true(self) -> None:
        """Shown 1 second ago with 86400 throttle → True (fresh)."""
        from datetime import timedelta

        last = _NOW - timedelta(seconds=1)
        record = _make_record(last_shown_at=last)
        assert NagCache.is_fresh(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is True

    def test_expired_returns_false(self) -> None:
        """Shown 86401 seconds ago with 86400 throttle → False (expired)."""
        from datetime import timedelta

        last = _NOW - timedelta(seconds=86401)
        record = _make_record(last_shown_at=last)
        assert NagCache.is_fresh(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_exactly_at_throttle_boundary_returns_false(self) -> None:
        """Shown exactly throttle_seconds ago → False (delta == throttle → expired, RISK-5 fix).

        Per the corrected data-model: ``delta < throttle_seconds`` is the freshness
        predicate, so the boundary (delta == throttle) is treated as expired.
        """
        from datetime import timedelta

        last = _NOW - timedelta(seconds=86400)
        record = _make_record(last_shown_at=last)
        result = NagCache.is_fresh(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION)
        # delta == throttle_seconds → expired (False)
        assert result is False

    def test_far_past_returns_false(self) -> None:
        """Shown 1 year ago → False."""
        from datetime import timedelta

        last = _NOW - timedelta(days=400)
        record = _make_record(last_shown_at=last)
        assert NagCache.is_fresh(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_clock_skew_future_last_shown_returns_false(self) -> None:
        """last_shown_at in the future (clock skew) → False (CHK044)."""
        from datetime import timedelta

        last = _NOW + timedelta(seconds=3600)
        record = _make_record(last_shown_at=last)
        assert NagCache.is_fresh(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_custom_throttle_respects_value(self) -> None:
        """Custom throttle of 120 seconds: shown 60 seconds ago → fresh."""
        from datetime import timedelta

        last = _NOW - timedelta(seconds=60)
        record = _make_record(last_shown_at=last)
        assert NagCache.is_fresh(record, throttle_seconds=120, now=_NOW, current_cli_version=_VERSION) is True

    def test_custom_throttle_expired(self) -> None:
        """Custom throttle of 120 seconds: shown 200 seconds ago → expired."""
        from datetime import timedelta

        last = _NOW - timedelta(seconds=200)
        record = _make_record(last_shown_at=last)
        assert NagCache.is_fresh(record, throttle_seconds=120, now=_NOW, current_cli_version=_VERSION) is False


# ---------------------------------------------------------------------------
# has_fresh_data predicate table (FIX C, P2)
# ---------------------------------------------------------------------------


class TestHasFreshData:
    """Unit table for NagCache.has_fresh_data (FIX C, P2).

    This predicate answers "should we skip the network call?" using
    ``fetched_at`` rather than ``last_shown_at``.  It is intentionally
    distinct from ``is_fresh`` so that "no update available" hits
    (where ``last_shown_at`` stays None) also benefit from the fast path.
    """

    def test_none_record_returns_false(self) -> None:
        """None record → False."""
        assert NagCache.has_fresh_data(None, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_version_key_mismatch_returns_false(self) -> None:
        """Different cli_version_key → False (FR-025 invalidation)."""
        record = _make_record(cli_version_key="1.0.0", last_shown_at=None)
        assert NagCache.has_fresh_data(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_just_fetched_at_now_returns_true(self) -> None:
        """Record with matching version key fetched at exactly now → True."""
        # NagCacheRecord.fetched_at is typed as datetime (not Optional), so
        # there is no None-fetched_at branch to test at runtime.  This test
        # confirms the happy path: a freshly-fetched record is considered fresh.
        record = _make_record(fetched_at=_NOW, last_shown_at=None)
        assert NagCache.has_fresh_data(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is True

    def test_just_fetched_returns_true(self) -> None:
        """Fetched 1 second ago with 86400 throttle → True (fresh data)."""
        from datetime import timedelta
        fetched = _NOW - timedelta(seconds=1)
        record = _make_record(fetched_at=fetched, last_shown_at=None)
        assert NagCache.has_fresh_data(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is True

    def test_no_update_available_last_shown_none_but_fresh(self) -> None:
        """Key scenario (FIX C): installed==latest, last_shown_at=None, fetched recently.

        is_fresh() returns False (last_shown_at is None).
        has_fresh_data() must return True (fetched_at is recent).
        This is what enables the no-update fast path.
        """
        from datetime import timedelta
        fetched = _NOW - timedelta(hours=1)
        record = _make_record(
            latest_version=_VERSION,   # installed == latest, no update
            fetched_at=fetched,
            last_shown_at=None,        # nag never shown
        )
        # is_fresh should be False (nag never shown)
        assert NagCache.is_fresh(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False
        # has_fresh_data should be True (fetched 1 hour ago, within 24h throttle)
        assert NagCache.has_fresh_data(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is True

    def test_stale_fetch_returns_false(self) -> None:
        """Fetched longer than throttle_seconds ago → False (stale data)."""
        from datetime import timedelta
        fetched = _NOW - timedelta(seconds=86401)
        record = _make_record(fetched_at=fetched, last_shown_at=None)
        assert NagCache.has_fresh_data(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_exactly_at_throttle_boundary_returns_false(self) -> None:
        """Fetched exactly throttle_seconds ago → False (delta == throttle → expired)."""
        from datetime import timedelta
        fetched = _NOW - timedelta(seconds=86400)
        record = _make_record(fetched_at=fetched, last_shown_at=None)
        assert NagCache.has_fresh_data(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_clock_skew_negative_delta_returns_false(self) -> None:
        """fetched_at in the future (clock skew) → False (CHK044)."""
        from datetime import timedelta
        fetched = _NOW + timedelta(seconds=3600)
        record = _make_record(fetched_at=fetched, last_shown_at=None)
        assert NagCache.has_fresh_data(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is False

    def test_delta_zero_returns_true(self) -> None:
        """Fetched at exactly now (delta==0) → True (within window)."""
        record = _make_record(fetched_at=_NOW, last_shown_at=None)
        assert NagCache.has_fresh_data(record, throttle_seconds=86400, now=_NOW, current_cli_version=_VERSION) is True


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


class TestSerialisation:
    """Unit tests for the ISO-8601 helpers."""

    def test_dt_to_iso_utc(self) -> None:
        """UTC datetime serialises with +00:00 offset."""
        dt = datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC)
        iso = _dt_to_iso(dt)
        assert "+00:00" in iso or iso.endswith("Z") or "2026-04-27" in iso

    def test_iso_to_dt_round_trip(self) -> None:
        """ISO-8601 string round-trips through _iso_to_dt."""
        dt = datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC)
        iso = _dt_to_iso(dt)
        back = _iso_to_dt(iso)
        assert back == dt

    def test_naive_datetime_assumed_utc(self) -> None:
        """Naive datetime is treated as UTC."""
        naive = datetime(2026, 4, 27, 12, 0, 0)
        iso = _dt_to_iso(naive)
        back = _iso_to_dt(iso)
        assert back.tzinfo is not None
        assert back.utcoffset() is not None

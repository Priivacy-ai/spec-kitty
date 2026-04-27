"""CI determinism tests (WP08 / T033).

Verifies that nag output is suppressed and the nag cache is NOT updated when
the CLI is invoked in CI-mode contexts:

  - CI=1 environment variable
  - stdout is not a TTY (piped output)
  - --no-nag flag present
  - SPEC_KITTY_NO_NAG=1 environment variable

Also verifies zero network calls in all suppressed contexts.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.helpers import _should_suppress_nag
from specify_cli.compat.cache import NagCache, NagCacheRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(tmp_path: Path, last_shown_at: datetime | None = None) -> NagCacheRecord:
    """Write a minimal NagCacheRecord to a tmp cache and return the path."""
    return NagCacheRecord(
        cli_version_key="2.0.0",
        latest_version="2.0.1",
        latest_source="pypi",
        fetched_at=datetime(2026, 4, 27, 0, 0, 0, tzinfo=UTC),
        last_shown_at=last_shown_at,
    )


def _nag_cache(tmp_path: Path) -> NagCache:
    return NagCache(tmp_path / "upgrade-nag.json")


# ---------------------------------------------------------------------------
# T032/T033-1: _should_suppress_nag() unit tests
# ---------------------------------------------------------------------------


class TestShouldSuppressNag:
    """Unit tests for the _should_suppress_nag() helper."""

    def test_no_suppress_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No suppression flags → returns False (nag allowed)."""
        # Ensure CI and SPEC_KITTY_NO_NAG are unset
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        # Pretend stdout is a TTY
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        result = _should_suppress_nag(argv=[])
        assert result is False

    def test_suppress_on_ci_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CI=1 → suppressed."""
        monkeypatch.setenv("CI", "1")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=[]) is True

    def test_suppress_on_ci_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CI=true → suppressed."""
        monkeypatch.setenv("CI", "true")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=[]) is True

    def test_no_suppress_on_ci_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CI=false → NOT suppressed by CI."""
        monkeypatch.setenv("CI", "false")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        result = _should_suppress_nag(argv=[])
        assert result is False

    def test_suppress_on_no_nag_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SPEC_KITTY_NO_NAG=1 → suppressed."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "1")
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=[]) is True

    def test_suppress_on_no_nag_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--no-nag in argv → suppressed."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=["status", "--no-nag"]) is True

    def test_suppress_on_json_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--json in argv → suppressed (belt-and-suspenders per T032)."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=["status", "--json"]) is True

    def test_suppress_on_quiet_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--quiet in argv → suppressed."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=["status", "--quiet"]) is True

    def test_suppress_on_help_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--help in argv → suppressed."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=["--help"]) is True

    def test_suppress_on_version_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--version in argv → suppressed."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=["--version"]) is True

    def test_suppress_when_stdout_not_tty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Piped stdout → suppressed."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: False))
        assert _should_suppress_nag(argv=[]) is True


# ---------------------------------------------------------------------------
# T033-5: cache last_shown_at is NOT updated after suppressed runs
# ---------------------------------------------------------------------------


class TestCacheNotUpdatedWhenSuppressed:
    """Verify that suppressed runs do not consume the throttle window."""

    def test_ci_run_does_not_update_last_shown_at(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        network_blocker: MagicMock,
    ) -> None:
        """CI=1 run must not write last_shown_at to the nag cache.

        Procedure:
        1. Write a record with last_shown_at=None.
        2. Invoke _render_nag_if_needed() with CI=1 (suppressed).
        3. Read the cache back — last_shown_at must still be None.
        """
        from specify_cli.cli.helpers import _render_nag_if_needed

        cache = _nag_cache(tmp_path)
        initial_record = _make_record(tmp_path, last_shown_at=None)
        cache.write(initial_record)

        monkeypatch.setenv("CI", "1")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)

        # NagCache is a deferred import inside _render_nag_if_needed.
        # Patch it at the compat.cache module level so the deferred import
        # picks up the patched class.
        monkeypatch.setattr(
            "specify_cli.compat.cache.NagCache.default",
            classmethod(lambda cls: cache),  # type: ignore[misc]
        )

        # We need a minimal context mock
        ctx = MagicMock()
        ctx.obj = None

        # _render_nag_if_needed will call _should_suppress_nag() which checks
        # os.environ (CI=1) and returns True → returns early before the planner.
        with patch("specify_cli.cli.helpers.sys") as mock_sys:
            mock_sys.argv = ["spec-kitty", "status"]
            mock_sys.stdout.isatty.return_value = True
            mock_sys.stderr.isatty.return_value = True
            _render_nag_if_needed(ctx)

        after_record = cache.read()
        assert after_record is not None
        assert after_record.last_shown_at is None, "last_shown_at must not be updated when nag is suppressed (CI=1)"

        # No network calls because _render_nag_if_needed returned early (CI=1)
        assert network_blocker.call_count == 0

    def test_no_nag_flag_does_not_update_last_shown_at(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--no-nag flag must not update last_shown_at in cache."""
        from specify_cli.cli.helpers import _render_nag_if_needed

        cache = _nag_cache(tmp_path)
        initial_record = _make_record(tmp_path, last_shown_at=None)
        cache.write(initial_record)

        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)

        ctx = MagicMock()
        ctx.obj = None

        with patch("specify_cli.cli.helpers.sys") as mock_sys:
            mock_sys.argv = ["spec-kitty", "status", "--no-nag"]
            mock_sys.stdout.isatty.return_value = True
            mock_sys.stderr.isatty.return_value = True
            _render_nag_if_needed(ctx)

        after_record = cache.read()
        assert after_record is not None
        assert after_record.last_shown_at is None, "last_shown_at must not be updated when --no-nag is present"

    def test_no_nag_env_does_not_update_last_shown_at(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SPEC_KITTY_NO_NAG=1 must not update last_shown_at in cache."""
        from specify_cli.cli.helpers import _render_nag_if_needed

        cache = _nag_cache(tmp_path)
        initial_record = _make_record(tmp_path, last_shown_at=None)
        cache.write(initial_record)

        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "1")

        ctx = MagicMock()
        ctx.obj = None

        with patch("specify_cli.cli.helpers.sys") as mock_sys:
            mock_sys.argv = ["spec-kitty", "status"]
            mock_sys.stdout.isatty.return_value = True
            mock_sys.stderr.isatty.return_value = True
            _render_nag_if_needed(ctx)

        after_record = cache.read()
        assert after_record is not None
        assert after_record.last_shown_at is None, "last_shown_at must not be updated when SPEC_KITTY_NO_NAG=1"


# ---------------------------------------------------------------------------
# T033-1/2/3/4: nag not in output under suppression conditions
# ---------------------------------------------------------------------------


class TestNagNotRenderedWhenSuppressed:
    """Verify that suppressed invocations do not produce nag output.

    These tests call _should_suppress_nag() directly rather than invoking the
    full CLI to keep them fast and avoid dealing with the Typer bootstrap.
    """

    def test_ci_env_suppresses_nag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CI=1 → _should_suppress_nag returns True."""
        monkeypatch.setenv("CI", "1")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=["status"]) is True

    def test_piped_stdout_suppresses_nag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Piped stdout (not a TTY) → _should_suppress_nag returns True."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: False))
        assert _should_suppress_nag(argv=["status"]) is True

    def test_no_nag_flag_suppresses_nag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--no-nag flag → _should_suppress_nag returns True."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=["status", "--no-nag"]) is True

    def test_no_nag_env_suppresses_nag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SPEC_KITTY_NO_NAG=1 → _should_suppress_nag returns True."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NO_NAG", "1")
        monkeypatch.setattr(sys, "stdout", MagicMock(isatty=lambda: True))
        assert _should_suppress_nag(argv=["status"]) is True


# ---------------------------------------------------------------------------
# Network blocker coverage: zero network calls in suppressed invocations
# ---------------------------------------------------------------------------


class TestNoNetworkUnderSuppression:
    """Verify no outbound network calls are made in suppressed CI contexts."""

    def test_no_network_calls_with_ci_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        network_blocker: MagicMock,
    ) -> None:
        """CI=1 invocation of _render_nag_if_needed must make 0 network calls."""
        from specify_cli.cli.helpers import _render_nag_if_needed

        monkeypatch.setenv("CI", "1")
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)

        ctx = MagicMock()
        ctx.obj = None

        with patch("specify_cli.cli.helpers.sys") as mock_sys:
            mock_sys.argv = ["spec-kitty", "status"]
            mock_sys.stdout.isatty.return_value = True
            mock_sys.stderr.isatty.return_value = True
            _render_nag_if_needed(ctx)

        assert network_blocker.call_count == 0, f"Expected 0 network calls with CI=1, got {network_blocker.call_count}"

    def test_no_network_calls_with_no_nag_flag(
        self,
        monkeypatch: pytest.MonkeyPatch,
        network_blocker: MagicMock,
    ) -> None:
        """--no-nag invocation of _render_nag_if_needed must make 0 network calls."""
        from specify_cli.cli.helpers import _render_nag_if_needed

        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)

        ctx = MagicMock()
        ctx.obj = None

        with patch("specify_cli.cli.helpers.sys") as mock_sys:
            mock_sys.argv = ["spec-kitty", "status", "--no-nag"]
            mock_sys.stdout.isatty.return_value = True
            mock_sys.stderr.isatty.return_value = True
            _render_nag_if_needed(ctx)

        assert network_blocker.call_count == 0, f"Expected 0 network calls with --no-nag, got {network_blocker.call_count}"

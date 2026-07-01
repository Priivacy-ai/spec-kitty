"""Nag passthrough behavioral tests for the readiness coordinator.

Asserts FR-006 (the coordinator wraps _render_nag_if_needed byte-for-byte)
and FR-010 (the coordinator never raises, even when the planner inside the
nag does).

Mission: cli-startup-readiness-coordinator-skeleton-01KS7JRV
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import typer

from specify_cli.readiness import ReadinessResult, evaluate_readiness


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _make_ctx() -> typer.Context:
    app = typer.Typer()

    @app.callback()
    def _root_cb(ctx: typer.Context) -> None:  # pragma: no cover
        pass

    cmd = typer.main.get_command(app)
    ctx = typer.Context(cmd)
    ctx.obj = None
    return ctx


def test_A_nag_renders_on_stderr_under_allow_with_nag(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When compat.plan returns ALLOW_WITH_NAG and conditions permit, the nag
    renders on stderr through the coordinator path."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)

    # Use a sentinel without digits/punctuation so Rich's auto-color does not
    # split the substring with ANSI escape codes (Rich highlights numbers).
    expected_nag = "SENTINEL-NAG-LINE-WP-upgrade-available"

    from specify_cli.compat import Decision

    class _FakeCLIStatus:
        installed_version = "3.0.0"
        latest_version = "99.0.0"
        latest_source = "test"

    class _FakeResult:
        decision = Decision.ALLOW_WITH_NAG
        rendered_human = expected_nag
        cli_status = _FakeCLIStatus()

    def _fake_plan(inv: Any) -> Any:
        return _FakeResult()

    # Patch the symbol where it is consumed inside _render_nag_if_needed.
    # The function imports `plan as compat_plan` lazily from specify_cli.compat.
    import specify_cli.compat as compat_mod

    monkeypatch.setattr(compat_mod, "plan", _fake_plan)

    # Avoid touching the real nag cache on disk.
    class _NoopCacheRecord:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    class _NoopCache:
        @staticmethod
        def default() -> _NoopCache:
            return _NoopCache()

        def read(self) -> Any:
            return None

        def write(self, record: Any) -> None:
            return None

    monkeypatch.setattr(compat_mod, "NagCache", _NoopCache)
    monkeypatch.setattr(compat_mod, "NagCacheRecord", _NoopCacheRecord)

    ctx = _make_ctx()
    result = evaluate_readiness(ctx)

    assert isinstance(result, ReadinessResult)
    captured = capsys.readouterr()
    assert expected_nag in captured.err, (
        f"expected nag on stderr, got stdout={captured.out!r} stderr={captured.err!r}"
    )


def test_B_nag_suppressed_when_json_in_argv(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When --json is in argv, the nag is suppressed even if compat.plan
    would have returned ALLOW_WITH_NAG."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status", "--json"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)

    sentinel = "SENTINEL-NAG-LINE-WP-should-not-appear"

    from specify_cli.compat import Decision

    class _FakeCLIStatus:
        installed_version = "3.0.0"
        latest_version = "99.0.0"
        latest_source = "test"

    class _FakeResult:
        decision = Decision.ALLOW_WITH_NAG
        rendered_human = sentinel
        cli_status = _FakeCLIStatus()

    import specify_cli.compat as compat_mod

    monkeypatch.setattr(compat_mod, "plan", lambda inv: _FakeResult())

    ctx = _make_ctx()
    evaluate_readiness(ctx)

    captured = capsys.readouterr()
    assert sentinel not in captured.out, f"nag leaked to stdout: {captured.out!r}"
    assert sentinel not in captured.err, f"nag leaked to stderr: {captured.err!r}"


def test_C_planner_exception_does_not_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A planner exception inside the wrapped nag is swallowed by
    _render_nag_if_needed's own try/except; the coordinator does not raise."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    def _raising_plan(inv: Any) -> Any:
        raise RuntimeError("simulated planner failure")

    import specify_cli.compat as compat_mod

    monkeypatch.setattr(compat_mod, "plan", _raising_plan)

    ctx = _make_ctx()
    # Must not raise.
    result = evaluate_readiness(ctx)
    assert isinstance(result, ReadinessResult)


def test_D_legacy_nag_cache_update_preserves_upgrade_readiness_preferences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy nag display must not erase WS3 snooze/auto-upgrade fields."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)

    from specify_cli.compat import Decision
    from specify_cli.compat.cache import NagCacheRecord

    now = datetime(2026, 1, 1, tzinfo=UTC)
    snoozed_until = now + timedelta(days=7)
    existing = NagCacheRecord(
        cli_version_key="3.0.0",
        latest_version="99.0.0",
        latest_source="pypi",
        fetched_at=now,
        last_shown_at=now,
        remote_version_seen="99.0.0",
        snooze_step="7d",
        snoozed_until=snoozed_until,
        always_upgrade=True,
        never_ask=True,
    )
    writes: list[NagCacheRecord] = []

    class _FakeCLIStatus:
        installed_version = "3.0.0"
        latest_version = "99.0.0"
        latest_source = "pypi"

    class _FakeResult:
        decision = Decision.ALLOW_WITH_NAG
        rendered_human = "SENTINEL-NAG-LINE"
        cli_status = _FakeCLIStatus()

    class _MemCache:
        @staticmethod
        def default() -> _MemCache:
            return _MemCache()

        def read(self) -> NagCacheRecord:
            return existing

        def write(self, record: NagCacheRecord) -> None:
            writes.append(record)

    import specify_cli.compat as compat_mod

    monkeypatch.setattr(compat_mod, "plan", lambda inv: _FakeResult())
    monkeypatch.setattr(compat_mod, "NagCache", _MemCache)

    evaluate_readiness(_make_ctx())

    assert writes, "nag display should refresh last_shown_at"
    written = writes[-1]
    assert written.remote_version_seen == "99.0.0"
    assert written.snooze_step == "7d"
    assert written.snoozed_until == snoozed_until
    assert written.always_upgrade is True
    assert written.never_ask is True

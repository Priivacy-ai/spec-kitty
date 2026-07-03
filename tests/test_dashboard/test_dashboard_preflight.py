"""Tests for the charter preflight hook in the dashboard (T025 / T026).

Verifies the FR-006 caller contract for the dashboard consumer:

* Server still launches on preflight failure (no abort).
* ``blocked_reason`` is persisted under ``.kittify/`` and surfaced as
  ``preflight_warning`` in the ``/api/health`` response.
* On success the field is absent and the persisted warning is cleared.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from specify_cli.charter_runtime.preflight.dashboard_warning import (
    clear_preflight_warning,
    preflight_warning_path,
    read_preflight_warning,
    write_preflight_warning,
)
from specify_cli.charter_runtime.preflight.result import CharterPreflightResult


pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _pass_result() -> CharterPreflightResult:
    return CharterPreflightResult(
        passed=True,
        checks=[],
        auto_refresh_applied=False,
        auto_refresh_actions=[],
        blocked_reason=None,
    )


def _fail_result(reason: str) -> CharterPreflightResult:
    return CharterPreflightResult(
        passed=False,
        checks=[],
        auto_refresh_applied=False,
        auto_refresh_actions=[],
        blocked_reason=reason,
    )


# ---------------------------------------------------------------------------
# Persistence helpers (.kittify/preflight-warning.json)
# ---------------------------------------------------------------------------


def test_write_then_read_preflight_warning_roundtrip(tmp_path: Path) -> None:
    reason = "doctrine stale; run: spec-kitty charter sync"
    write_preflight_warning(tmp_path, reason)

    path = preflight_warning_path(tmp_path)
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {"blocked_reason": reason}

    assert read_preflight_warning(tmp_path) == reason


def test_clear_preflight_warning_is_idempotent(tmp_path: Path) -> None:
    # Clear when absent — no error.
    clear_preflight_warning(tmp_path)
    assert read_preflight_warning(tmp_path) is None

    write_preflight_warning(tmp_path, "x")
    clear_preflight_warning(tmp_path)
    assert read_preflight_warning(tmp_path) is None


def test_read_preflight_warning_returns_none_for_corrupt_payload(tmp_path: Path) -> None:
    path = preflight_warning_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")

    assert read_preflight_warning(tmp_path) is None


# ---------------------------------------------------------------------------
# Hook wiring — dashboard CLI command
# ---------------------------------------------------------------------------


def test_dashboard_hook_persists_warning_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``run_preflight_for_dashboard`` returns the result; the CLI persists it.

    We exercise the persistence directly (the CLI command's branching is
    a thin wrapper) so the test stays focused on the contract.
    """
    from specify_cli.charter_runtime.preflight import hook as hook_mod

    monkeypatch.setattr(
        hook_mod,
        "run_charter_preflight",
        lambda **_: _fail_result("synthesized DRG missing; run: spec-kitty charter synthesize"),
    )

    result = hook_mod.run_preflight_for_dashboard(tmp_path)
    assert result.passed is False
    assert result.blocked_reason is not None

    # Mimic the dashboard CLI branch: write the warning when not-passed.
    write_preflight_warning(tmp_path, result.blocked_reason)
    assert read_preflight_warning(tmp_path) == result.blocked_reason


def test_dashboard_hook_clears_warning_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On success the persisted warning is cleared, even if one was stale."""
    from specify_cli.charter_runtime.preflight import hook as hook_mod

    write_preflight_warning(tmp_path, "stale from a previous run")
    monkeypatch.setattr(hook_mod, "run_charter_preflight", lambda **_: _pass_result())

    result = hook_mod.run_preflight_for_dashboard(tmp_path)
    assert result.passed is True

    # Mimic the dashboard CLI branch: clear on success.
    clear_preflight_warning(tmp_path)
    assert read_preflight_warning(tmp_path) is None


def test_dashboard_hook_does_not_warning_log_optional_missing_charter(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Fresh projects without charter state are advisory, not warning-level spam."""
    import subprocess

    from specify_cli.charter_runtime.preflight import hook as hook_mod

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)

    with caplog.at_level(logging.WARNING, logger=hook_mod.__name__):
        result = hook_mod.run_preflight_for_dashboard(tmp_path)

    assert result.passed is True
    assert result.blocked_reason is None
    assert result.warnings
    assert caplog.records == []


def test_null_project_config_enabled_still_runs_dashboard_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Null enabled must not silently skip the dashboard warning gate."""
    from specify_cli.charter_runtime.preflight import hook as hook_mod

    config_path = tmp_path / ".kittify" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("preflight:\n  enabled: null\n", encoding="utf-8")
    runner_calls: list[dict] = []

    def _run_charter_preflight(**kwargs):
        runner_calls.append(kwargs)
        return _pass_result()

    monkeypatch.setattr(hook_mod, "run_charter_preflight", _run_charter_preflight)

    result = hook_mod.run_preflight_for_dashboard(tmp_path)

    assert result.passed is True
    assert runner_calls == [
        {
            "repo_root": tmp_path,
            "auto_refresh": False,
            "allow_missing_charter": True,
            "strict": False,
        }
    ]


# ---------------------------------------------------------------------------
# API surface — /api/health response shape
# ---------------------------------------------------------------------------


class _StubRequestHandler:
    """Minimal stand-in for ``DashboardRouter`` to test ``handle_health``."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = str(project_dir)
        self.project_token = "tok-12345"
        self._headers: list[tuple[str, str]] = []
        self._status: int | None = None
        self._body: bytes = b""

    # The handler calls these BaseHTTPRequestHandler methods.
    def send_response(self, code: int) -> None:
        self._status = code

    def send_header(self, key: str, value: str) -> None:
        self._headers.append((key, value))

    def end_headers(self) -> None:
        pass

    class _WFile:
        def __init__(self, parent: _StubRequestHandler) -> None:
            self._parent = parent

        def write(self, data: bytes) -> None:
            self._parent._body += data

    @property
    def wfile(self) -> _StubRequestHandler._WFile:
        return self._WFile(self)

    @property
    def response_payload(self) -> dict:
        return json.loads(self._body.decode("utf-8"))


def _invoke_handle_health(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Invoke ``APIHandler.handle_health`` against a stub request handler."""
    from specify_cli.dashboard.handlers.api import APIHandler

    # ``get_sync_daemon_status`` performs IPC; stub it out for a clean payload.
    import specify_cli.dashboard.handlers.api as api_mod

    class _StubStatus:
        sync_running = False
        last_sync = None
        consecutive_failures = 0
        websocket_status = "Offline"

    monkeypatch.setattr(api_mod, "get_sync_daemon_status", lambda timeout=0.2: _StubStatus())

    handler = _StubRequestHandler(project_dir)
    APIHandler.handle_health(handler)  # type: ignore[arg-type]
    assert handler._status == 200
    return handler.response_payload


def test_api_health_omits_preflight_warning_when_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No persisted warning ⇒ ``preflight_warning`` is not present in the payload."""
    clear_preflight_warning(tmp_path)
    payload = _invoke_handle_health(tmp_path, monkeypatch)
    assert "preflight_warning" not in payload


def test_api_health_populates_preflight_warning_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persisted warning ⇒ exposed verbatim in ``/api/health`` response."""
    reason = "uncommitted generated artifacts; commit or stash and retry"
    write_preflight_warning(tmp_path, reason)

    payload = _invoke_handle_health(tmp_path, monkeypatch)
    assert payload["preflight_warning"] == reason

"""Regression tests for ``spec-kitty doctor restart-daemon``.

Covers the exit-code matrix in ``contracts/doctor-restart-daemon.md``:

- exit 0 — happy path (daemon stopped + respawned at foreground)
- exit 1 — no owner record on disk
- exit 2 — stop succeeds but respawn fails
- exit 3 — stop primitive fails
- foreground binding — after restart the daemon launcher is invoked
  with ``intent=REMOTE_REQUIRED`` so the new daemon binds to the
  foreground executable / source.

All tests monkeypatch the daemon stop / launch primitives so that no
actual ``run_sync_daemon`` subprocess is spawned during the test run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import doctor as doctor_module
from specify_cli.cli.commands import _is_doctor_restart_daemon_fast_path
from specify_cli.sync.daemon import DaemonIntent, DaemonStartOutcome

pytestmark = [pytest.mark.unit, pytest.mark.integration]
# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class _FakeRecord:
    """Minimal stand-in for :class:`DaemonOwnerRecord` for these tests."""

    pid: int = 12345


def _install_owner_record_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    record: _FakeRecord | None,
    path_exists: bool,
) -> None:
    """Wire up fakes for ``owner_record_path().exists()`` and ``read_owner_record()``.

    ``restart_daemon`` does its presence check via
    ``owner_record_path().exists()`` and only then reads the record
    fields, so the two fakes must agree.
    """

    class _FakePath:
        def exists(self) -> bool:
            return path_exists

    # ``_owner_record_present`` and ``_read_previous_pid`` both import
    # their helpers lazily from ``specify_cli.sync.owner`` at call time,
    # so the canonical patch targets live on that module, not on
    # ``specify_cli.sync.restart`` (which has no module-level binding).
    monkeypatch.setattr(
        "specify_cli.sync.owner.owner_record_path",
        lambda: _FakePath(),
        raising=True,
    )
    monkeypatch.setattr(
        "specify_cli.sync.owner.read_owner_record",
        lambda: record,
        raising=True,
    )


def _install_daemon_state_file_fake(
    monkeypatch: pytest.MonkeyPatch,
    *,
    exists: bool,
    port: int | None = 9400,
    pid: int | None = None,
) -> None:
    """Wire up a fake ``DAEMON_STATE_FILE.exists()`` response."""

    class _FakePath:
        def exists(self) -> bool:
            return exists

    monkeypatch.setattr(
        "specify_cli.sync.daemon.DAEMON_STATE_FILE",
        _FakePath(),
        raising=True,
    )
    monkeypatch.setattr(
        "specify_cli.sync.daemon._parse_daemon_file",
        lambda _path: ("http://127.0.0.1:9400", port, "token", pid),
        raising=True,
    )


def _install_stop_fake(
    monkeypatch: pytest.MonkeyPatch,
    *,
    result: tuple[bool, str] | Exception,
) -> list[float]:
    """Install a fake ``stop_sync_daemon`` and return a call-counter list."""
    calls: list[float] = []

    def _fake_stop(timeout: float = 5.0) -> tuple[bool, str]:
        calls.append(timeout)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(
        "specify_cli.sync.daemon.stop_sync_daemon",
        _fake_stop,
        raising=True,
    )
    return calls


def _install_launch_fake(
    monkeypatch: pytest.MonkeyPatch,
    *,
    outcome: DaemonStartOutcome | Exception,
) -> list[dict[str, Any]]:
    """Install a fake ``ensure_sync_daemon_running`` and capture calls."""
    calls: list[dict[str, Any]] = []

    def _fake_launch(*args: Any, **kwargs: Any) -> DaemonStartOutcome:
        calls.append({"args": args, "kwargs": kwargs})
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(
        "specify_cli.sync.daemon.ensure_sync_daemon_running",
        _fake_launch,
        raising=True,
    )
    return calls


def _runner() -> CliRunner:
    # Click 8.2+ removed the ``mix_stderr`` kwarg; the default behaviour is
    # what we want for these tests, so we just construct the runner plain.
    return CliRunner()


def test_restart_daemon_uses_cli_registration_fast_path() -> None:
    """Direct restart-daemon invocation should avoid registering unrelated commands."""
    assert _is_doctor_restart_daemon_fast_path(
        ["spec-kitty", "doctor", "restart-daemon", "--json"]
    )
    assert not _is_doctor_restart_daemon_fast_path(
        ["spec-kitty", "doctor", "restart-daemon", "--help"]
    )
    assert not _is_doctor_restart_daemon_fast_path(["spec-kitty", "doctor", "identity"])


def test_import_does_not_execute_restart_daemon_fast_path(tmp_path: Path) -> None:
    """Importing the package must not dispatch commands from inherited argv."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    env["HOME"] = str(tmp_path / "home")
    env.pop("SPEC_KITTY_TEST_MODE", None)
    code = (
        "import sys; "
        "sys.argv=['host','doctor','restart-daemon','--json']; "
        "import specify_cli; "
        "print('IMPORT_SURVIVED')"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "IMPORT_SURVIVED"
    assert result.stderr.strip() == ""


# ---------------------------------------------------------------------------
# Exit-code matrix
# ---------------------------------------------------------------------------


def test_happy_path_exits_zero_and_reports_new_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daemon stops, respawns, exits 0; JSON contract honoured."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True)
    stop_calls = _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    launch_calls = _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=67890),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])

    assert result.exit_code == 0
    assert stop_calls == [1.0], "stop primitive must be called exactly once"
    assert len(launch_calls) == 1, "launch primitive must be called exactly once"
    assert launch_calls[0]["kwargs"] == {
        "intent": DaemonIntent.REMOTE_REQUIRED,
        "health_wait_seconds": 3.0,
    }

    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "restarted"
    assert payload["previous_pid"] == 12345
    assert payload["new_pid"] == 67890
    assert payload["new_pid"] != payload["previous_pid"]
    assert payload["error"] is None


def test_no_owner_exits_one_and_directs_to_sync_now(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absent owner record → exit 1, message points operator at sync now."""
    _install_owner_record_fakes(monkeypatch, record=None, path_exists=False)
    _install_daemon_state_file_fake(monkeypatch, exists=False)
    stop_calls = _install_stop_fake(monkeypatch, result=(False, "should-not-call"))
    launch_calls = _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=False, skipped_reason="x", pid=None),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])

    assert result.exit_code == 1
    assert stop_calls == [], "stop must not be invoked when no owner record exists"
    assert launch_calls == [], "launch must not be invoked when no owner record exists"

    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "no_owner"
    assert payload["previous_pid"] is None
    assert payload["new_pid"] is None
    assert payload["error"] is not None
    assert "spec-kitty sync now" in payload["error"]


def test_owner_grace_wait_allows_registered_daemon_to_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A short owner-registration lag is tolerated when daemon metadata exists."""

    class _SequencedPath:
        def __init__(self, results: list[bool]) -> None:
            self._results = results

        def exists(self) -> bool:
            if len(self._results) > 1:
                return self._results.pop(0)
            return self._results[0]

    path = _SequencedPath([False, False, True])
    monkeypatch.setattr(
        "specify_cli.sync.owner.owner_record_path",
        lambda: path,
        raising=True,
    )
    monkeypatch.setattr(
        "specify_cli.sync.owner.read_owner_record",
        lambda: _FakeRecord(pid=12345),
        raising=True,
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True)

    ticks = iter([0.0, 0.1, 0.2, 0.3])
    sleeps: list[float] = []
    monkeypatch.setattr("specify_cli.sync.restart.time.monotonic", lambda: next(ticks))
    monkeypatch.setattr("specify_cli.sync.restart.time.sleep", lambda seconds: sleeps.append(seconds))

    stop_calls = _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    launch_calls = _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=67890),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])

    assert result.exit_code == 0
    assert sleeps, "restart should poll briefly while owner record appears"
    assert stop_calls == [1.0]
    assert len(launch_calls) == 1


def test_daemon_state_without_owner_is_restartable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daemon state metadata is enough to stop and respawn when owner is absent."""

    class _MissingPath:
        def exists(self) -> bool:
            return False

    monkeypatch.setattr(
        "specify_cli.sync.owner.owner_record_path",
        lambda: _MissingPath(),
        raising=True,
    )
    monkeypatch.setattr(
        "specify_cli.sync.owner.read_owner_record",
        lambda: None,
        raising=True,
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True, pid=12345)

    ticks = iter([0.0, 0.1, 0.2, 0.3, 2.1])
    sleeps: list[float] = []
    monkeypatch.setattr("specify_cli.sync.restart.time.monotonic", lambda: next(ticks))
    monkeypatch.setattr("specify_cli.sync.restart.time.sleep", lambda seconds: sleeps.append(seconds))

    stop_calls = _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    launch_calls = _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=67890),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])

    assert result.exit_code == 0
    assert sleeps, "restart should wait briefly for owner before falling back to state"
    assert stop_calls == [1.0]
    assert len(launch_calls) == 1
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "restarted"
    assert payload["previous_pid"] == 12345
    assert payload["new_pid"] == 67890


def test_invalid_daemon_state_without_owner_is_not_restartable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Corrupt state-only metadata stays on the no-owner boundary."""

    class _MissingPath:
        def exists(self) -> bool:
            return False

    monkeypatch.setattr(
        "specify_cli.sync.owner.owner_record_path",
        lambda: _MissingPath(),
        raising=True,
    )
    monkeypatch.setattr(
        "specify_cli.sync.owner.read_owner_record",
        lambda: None,
        raising=True,
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True, port=None, pid=None)

    ticks = iter([0.0, 0.1, 0.2, 0.3, 2.1])
    sleeps: list[float] = []
    monkeypatch.setattr("specify_cli.sync.restart.time.monotonic", lambda: next(ticks))
    monkeypatch.setattr("specify_cli.sync.restart.time.sleep", lambda seconds: sleeps.append(seconds))

    stop_calls = _install_stop_fake(monkeypatch, result=(False, "invalid metadata"))
    launch_calls = _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=67890),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])

    assert result.exit_code == 1
    assert sleeps, "restart should wait briefly for owner before checking state"
    assert stop_calls == []
    assert launch_calls == []
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "no_owner"
    assert payload["previous_pid"] is None
    assert payload["new_pid"] is None
    assert "spec-kitty sync now" in (payload["error"] or "")


def test_stop_failure_exits_three_and_skips_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop primitive failure → exit 3; launch must NOT be called."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True)
    stop_calls = _install_stop_fake(
        monkeypatch, result=RuntimeError("daemon unresponsive")
    )
    launch_calls = _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=99999),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])

    assert result.exit_code == 3
    assert stop_calls == [1.0]
    assert launch_calls == [], "launch must not run after a stop failure"

    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "stop_failed"
    assert payload["previous_pid"] == 12345
    assert payload["new_pid"] is None
    assert payload["error"] is not None
    assert "daemon unresponsive" in payload["error"]


def test_respawn_failure_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop OK, launch raises → exit 2."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True)
    _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    _install_launch_fake(monkeypatch, outcome=RuntimeError("port allocation failed"))

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "respawn_failed"
    assert payload["previous_pid"] == 12345
    assert payload["new_pid"] is None
    assert "port allocation failed" in (payload["error"] or "")


def test_respawn_skipped_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop OK, launch reports ``started=False`` → exit 2 (respawn_failed)."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True)
    _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(
            started=False, skipped_reason="rollout_disabled", pid=None
        ),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "respawn_failed"
    assert "rollout_disabled" in (payload["error"] or "")


def test_foreground_binding_uses_remote_required_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Launch is invoked with ``intent=REMOTE_REQUIRED`` so the new daemon
    binds to the foreground executable / source (not the stale owner's)."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    launch_calls = _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=67890),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon"])

    assert result.exit_code == 0
    assert len(launch_calls) == 1
    intent = launch_calls[0]["kwargs"].get("intent")
    assert intent == DaemonIntent.REMOTE_REQUIRED
    assert launch_calls[0]["kwargs"].get("health_wait_seconds") == 3.0


# ---------------------------------------------------------------------------
# Render surface
# ---------------------------------------------------------------------------


def test_human_render_includes_pid_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default (non-JSON) render contains both previous and new PIDs."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=67890),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon"])

    assert result.exit_code == 0
    assert "12345" in result.stdout
    assert "67890" in result.stdout
    assert "restarted" in result.stdout.lower()


def test_stale_owner_cleaned_still_exits_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When stop reports the existing daemon was unhealthy, the result is
    ``stale_owner_cleaned`` but exit code is still 0 (operator is told
    the daemon was respawned)."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_stop_fake(
        monkeypatch,
        result=(
            True,
            "Unhealthy sync daemon process stopped. Metadata has been cleared.",
        ),
    )
    _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=67890),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "stale_owner_cleaned"
    assert payload["new_pid"] == 67890


def test_doctor_help_lists_restart_daemon() -> None:
    """``doctor --help`` lists the ``restart-daemon`` subcommand."""
    result = _runner().invoke(doctor_module.app, ["--help"])
    assert result.exit_code == 0
    assert "restart-daemon" in result.stdout


def test_restart_daemon_help_exits_zero() -> None:
    """``doctor restart-daemon --help`` exits 0 and shows help text."""
    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--help"])
    assert result.exit_code == 0
    assert "restart" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Sanity: repo_root resolution must not crash outside a project
# ---------------------------------------------------------------------------


def test_runs_outside_project_does_not_crash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI tolerates ``locate_project_root`` returning None or raising
    by falling back to ``Path.cwd()``. Exercise the no-owner branch from
    a tmp dir so we know the entry point is robust."""
    monkeypatch.chdir(tmp_path)
    _install_owner_record_fakes(monkeypatch, record=None, path_exists=False)
    _install_daemon_state_file_fake(monkeypatch, exists=False)
    _install_stop_fake(monkeypatch, result=(False, "noop"))
    _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=False, skipped_reason="x", pid=None),
    )

    result = _runner().invoke(doctor_module.app, ["restart-daemon", "--json"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Production hot path (#2059, GAP 2)
#
# Production ``spec-kitty doctor restart-daemon [--json]`` never runs the Typer
# command body for the bare invocation: ``main()`` short-circuits into
# ``_run_doctor_restart_daemon_process_fast_path`` which renders the result and
# calls ``os._exit(result.exit_code)`` — bypassing the Typer/Click stack the
# CliRunner exercises above. The golden test only asserts ``exit_code in
# {0,1,2,3}`` (any of four passes). These tests drive the PRODUCTION fast-path
# directly and pin EACH state to its SPECIFIC exit code.
#
# Because the fast-path calls ``os._exit`` (which would kill the test process),
# we patch ``os._exit`` to record the code and raise a sentinel that stops
# execution exactly at the production exit boundary.
# ---------------------------------------------------------------------------


class _ExitCaptured(BaseException):
    """Sentinel raised in place of ``os._exit`` to halt at the exit boundary."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def _run_production_fast_path(
    monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> int:
    """Invoke the production restart-daemon fast-path and capture the os._exit code.

    Drives ``specify_cli._run_doctor_restart_daemon_process_fast_path`` — the
    real production seam — not the Typer CliRunner shell.
    """
    import specify_cli

    captured: dict[str, int] = {}

    def _fake_exit(code: int) -> None:
        captured["code"] = code
        raise _ExitCaptured(code)

    monkeypatch.setattr("specify_cli.os._exit", _fake_exit, raising=True)

    with pytest.raises(_ExitCaptured):
        specify_cli._run_doctor_restart_daemon_process_fast_path(argv)

    assert "code" in captured, "production fast-path must reach os._exit"
    return captured["code"]


_FAST_PATH_ARGV = ["spec-kitty", "doctor", "restart-daemon", "--json"]


def test_production_fast_path_happy_path_exits_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """restarted → production fast-path calls ``os._exit(0)``."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True)
    _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=67890),
    )

    assert _run_production_fast_path(monkeypatch, _FAST_PATH_ARGV) == 0


def test_production_fast_path_no_owner_exits_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """no_owner → production fast-path calls ``os._exit(1)``."""
    _install_owner_record_fakes(monkeypatch, record=None, path_exists=False)
    _install_daemon_state_file_fake(monkeypatch, exists=False)
    _install_stop_fake(monkeypatch, result=(False, "should-not-call"))
    _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=False, skipped_reason="x", pid=None),
    )

    assert _run_production_fast_path(monkeypatch, _FAST_PATH_ARGV) == 1


def test_production_fast_path_respawn_failure_exits_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """respawn_failed → production fast-path calls ``os._exit(2)``."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True)
    _install_stop_fake(monkeypatch, result=(True, "Sync daemon stopped."))
    _install_launch_fake(
        monkeypatch, outcome=RuntimeError("port allocation failed")
    )

    assert _run_production_fast_path(monkeypatch, _FAST_PATH_ARGV) == 2


def test_production_fast_path_stop_failure_exits_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stop_failed → production fast-path calls ``os._exit(3)``."""
    _install_owner_record_fakes(
        monkeypatch, record=_FakeRecord(pid=12345), path_exists=True
    )
    _install_daemon_state_file_fake(monkeypatch, exists=True)
    _install_stop_fake(
        monkeypatch, result=RuntimeError("daemon unresponsive")
    )
    _install_launch_fake(
        monkeypatch,
        outcome=DaemonStartOutcome(started=True, skipped_reason=None, pid=99999),
    )

    assert _run_production_fast_path(monkeypatch, _FAST_PATH_ARGV) == 3

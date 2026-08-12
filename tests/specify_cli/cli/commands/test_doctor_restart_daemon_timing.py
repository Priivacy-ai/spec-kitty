"""Functional regression gate for ``spec-kitty doctor restart-daemon``.

The command must stop the prior daemon, spawn a distinct process, and expose a
healthy control plane. Subprocess timeouts bound hangs; this module does not
claim a portable wall-clock performance budget for shared CI runners.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time
import urllib.request
from pathlib import Path

import psutil  # type: ignore[import-untyped]
import pytest


pytestmark = [
    pytest.mark.non_sandbox,
]

_RESTART_TIMEOUT_SECONDS = 15.0
_SETUP_TIMEOUT_SECONDS = 90.0
_CONTROL_PLANE_READY_TIMEOUT_SECONDS = 10.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _subprocess_env(home: Path) -> dict[str, str]:
    passthrough = (
        "PATH",
        "SYSTEMROOT",
        "TMP",
        "TMPDIR",
        "TEMP",
        "WINDIR",
    )
    env = {key: os.environ[key] for key in passthrough if key in os.environ}
    src_path = str(_repo_root() / "src")
    env["PYTHONPATH"] = src_path
    env["HOME"] = str(home)
    # This path exercises hosted-sync daemon startup. The temp HOME has no
    # credentials, so no authenticated remote sync is performed.
    env["SPEC_KITTY_ENABLE_SAAS_SYNC"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _restart_command() -> list[str]:
    # Exercise the current checkout through the active interpreter. macOS CI
    # can expose framework-level console shims that are slower and less
    # deterministic than the source tree under test.
    return [sys.executable, "-m", "specify_cli", "doctor", "restart-daemon", "--json"]


def _run_python(
    code: str,
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _daemon_state_file(home: Path) -> Path:
    return home / ".spec-kitty" / "sync-daemon"


def _read_daemon_record(home: Path) -> tuple[str, int, str, int]:
    lines = [
        line.strip()
        for line in _daemon_state_file(home).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return lines[0], int(lines[1]), lines[2], int(lines[3])


def _fetch_health(url: str, token: str) -> dict[str, object]:
    with urllib.request.urlopen(f"{url}/api/health", timeout=1.0) as response:  # nosec B310 — url is read from the temp-HOME localhost daemon record.
        assert response.status == 200
        payload = json.loads(response.read().decode("utf-8"))
    assert isinstance(payload, dict)
    assert payload.get("token") == token
    return payload


def _wait_for_control_plane_ready(home: Path, expected_pid: int, *, deadline: float) -> dict[str, object]:
    last_payload: dict[str, object] | None = None
    while time.perf_counter() < deadline:
        url, _port, token, pid = _read_daemon_record(home)
        assert pid == expected_pid
        try:
            payload = _fetch_health(url, token)
            last_payload = payload
            if payload.get("status") == "ok":
                return payload
        except Exception:  # noqa: BLE001 — daemon may be between fork and bind.
            pass
        time.sleep(0.1)
    raise AssertionError(f"sync control plane was not ready before NFR deadline: {last_payload}")


def _terminate_known_daemon_pids(pids: list[int]) -> None:
    for pid in pids:
        try:
            proc = psutil.Process(pid)
            cmdline = " ".join(proc.cmdline())
            if "run_sync_daemon" not in cmdline:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except psutil.TimeoutExpired:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def test_doctor_restart_daemon_restarts_and_becomes_healthy(
    tmp_path: Path,
) -> None:
    """A real stop + respawn publishes a distinct, healthy daemon."""

    home = tmp_path / "home"
    home.mkdir()
    env = _subprocess_env(home)
    repo_root = _repo_root()
    created_pids: list[int] = []

    try:
        setup = _run_python(
            """
            from specify_cli.sync.daemon import DaemonIntent, ensure_sync_daemon_running

            outcome = ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED)
            if not outcome.started:
                raise SystemExit(f"daemon did not start: {outcome.skipped_reason}")
            print(outcome.pid)
            """,
            cwd=repo_root,
            env=env,
            timeout=_SETUP_TIMEOUT_SECONDS,
        )
        assert setup.returncode == 0, setup.stderr or setup.stdout
        created_pids.append(int(setup.stdout.strip()))

        result = subprocess.run(
            _restart_command(),
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=_RESTART_TIMEOUT_SECONDS,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        payload = json.loads(result.stdout)
        assert payload["status"] == "restarted"
        assert payload["previous_pid"] != payload["new_pid"]
        created_pids.append(int(payload["new_pid"]))
        health_payload = _wait_for_control_plane_ready(
            home,
            int(payload["new_pid"]),
            deadline=time.perf_counter() + _CONTROL_PLANE_READY_TIMEOUT_SECONDS,
        )
        assert health_payload["status"] == "ok"
    finally:
        try:
            _run_python(
                """
                from specify_cli.sync.daemon import stop_sync_daemon

                stop_sync_daemon(timeout=1.0)
                """,
                cwd=repo_root,
                env=env,
                timeout=5.0,
            )
        except subprocess.TimeoutExpired:
            pass
        finally:
            _terminate_known_daemon_pids(created_pids)

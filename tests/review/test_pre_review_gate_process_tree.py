"""Real-process evidence for the pre-review gate interruption contract.

Catchable interruption owns and reaps the validation process group.  These
tests intentionally make no claim about orphan cleanup after the CLI parent is
uncatchably killed; that separate boundary remains tracked by #2762.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

import pytest

from specify_cli.review import pre_review_gate


_POSIX_ONLY = pytest.mark.skipif(os.name == "nt", reason="real POSIX process-group evidence")

_PROCESS_TEST = """\
import json
import os
import subprocess
import sys
import time


def test_owned_tree() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    with open(os.environ["OWNED_TREE_READY"], "w", encoding="utf-8") as stream:
        json.dump({"pytest": os.getpid(), "grandchild": child.pid}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    time.sleep(60)
"""


def _write_owned_tree_fixture(root: Path) -> None:
    (root / "test_owned_tree.py").write_text(_PROCESS_TEST, encoding="utf-8")


def _wait_for_ready(path: Path, *, deadline: float = 5.0) -> dict[str, int]:
    expires = time.monotonic() + deadline
    while time.monotonic() < expires:
        if path.exists() and path.stat().st_size:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return {str(key): int(value) for key, value in payload.items()}
        time.sleep(0.01)
    raise AssertionError("validation process tree did not publish readiness")


def _process_is_running(pid: int) -> bool:
    """Return false for absent and zombie POSIX processes."""
    result = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)],
        check=False,
        capture_output=True,
        text=True,
    )
    state = result.stdout.strip()
    return result.returncode == 0 and bool(state) and not state.startswith("Z")


def _assert_tree_stopped(pids: dict[str, int], *, deadline: float = 5.0) -> None:
    expires = time.monotonic() + deadline
    while time.monotonic() < expires:
        if not any(_process_is_running(pid) for pid in pids.values()):
            return
        time.sleep(0.02)
    live = {name: pid for name, pid in pids.items() if _process_is_running(pid)}
    raise AssertionError(f"command-owned process tree still running: {live}")


@pytest.mark.integration
@_POSIX_ONLY
def test_real_timeout_reaps_command_owned_process_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_path = tmp_path / "timeout-ready.json"
    _write_owned_tree_fixture(tmp_path)
    monkeypatch.setenv("OWNED_TREE_READY", str(ready_path))

    result = pre_review_gate.run_scoped_tests_at_head(
        ["test_owned_tree.py"],
        repo_root=tmp_path,
        timeout=1,
    )

    pids = _wait_for_ready(ready_path)
    assert result.ran is False
    assert result.state is pre_review_gate.HeadRunState.TIMED_OUT
    assert result.returncode is not None
    _assert_tree_stopped(pids)


@pytest.mark.integration
@_POSIX_ONLY
def test_real_cancellation_reaps_command_owned_process_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_path = tmp_path / "cancel-ready.json"
    _write_owned_tree_fixture(tmp_path)
    monkeypatch.setenv("OWNED_TREE_READY", str(ready_path))
    waits = 0

    def cancel_after_ready(
        process: subprocess.Popen[str],
        timeout: float,
    ) -> tuple[str, str]:
        nonlocal waits
        waits += 1
        if waits == 1:
            _wait_for_ready(ready_path, deadline=min(timeout, 5.0))
            raise KeyboardInterrupt
        return process.communicate(timeout=timeout)

    result = pre_review_gate.run_scoped_tests_at_head(
        ["test_owned_tree.py"],
        repo_root=tmp_path,
        wait=cancel_after_ready,
    )

    pids = _wait_for_ready(ready_path)
    assert result.ran is False
    assert result.state is pre_review_gate.HeadRunState.CANCELLED
    assert waits == 2
    _assert_tree_stopped(pids)


class _WindowsProcess:
    pid = 4242
    returncode: int | None = None
    terminated = False
    killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


@pytest.mark.windows_ci
def test_windows_taskkill_contract_uses_tree_then_force_escalation() -> None:
    """The existing ci-windows marker collector discovers this exact node."""
    process = _WindowsProcess()
    commands: list[tuple[str, ...]] = []

    def taskkill(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        commands.append(tuple(command))
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

    pre_review_gate._signal_owned_process_tree(
        process,
        force=False,
        platform="nt",
        windows_tree_kill=taskkill,
    )
    pre_review_gate._signal_owned_process_tree(
        process,
        force=True,
        platform="nt",
        windows_tree_kill=taskkill,
    )

    assert commands == [
        ("taskkill", "/PID", "4242", "/T"),
        ("taskkill", "/PID", "4242", "/T", "/F"),
    ]
    assert process.terminated is False
    assert process.killed is False


class _RaceProcess:
    pid = 5252
    returncode = 0


@pytest.mark.fast
def test_completion_observed_before_deadline_wins_race() -> None:
    clock = iter((0.0, 0.9))

    state, stdout, stderr = pre_review_gate._observe_process(
        _RaceProcess(),
        timeout=1.0,
        progress_callback=None,
        monotonic=lambda: next(clock),
        wait=lambda _process, _timeout: ("complete", ""),
    )

    assert (state, stdout, stderr) == (
        pre_review_gate.HeadRunState.COMPLETED,
        "complete",
        "",
    )


@pytest.mark.fast
def test_deadline_observed_first_yields_one_timeout_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter((0.0, 1.0))
    terminations: list[int] = []

    def terminate_once(process: _RaceProcess, *, wait: object) -> tuple[str, str]:
        del wait
        terminations.append(process.pid)
        return "", ""

    monkeypatch.setattr(
        pre_review_gate,
        "_terminate_and_reap",
        terminate_once,
    )

    state, _stdout, _stderr = pre_review_gate._observe_process(
        _RaceProcess(),
        timeout=1.0,
        progress_callback=None,
        monotonic=lambda: next(clock),
        wait=lambda _process, _timeout: ("too late", ""),
    )

    assert state is pre_review_gate.HeadRunState.TIMED_OUT
    assert terminations == [5252]

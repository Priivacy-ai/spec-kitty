"""Tests for the ``uv run`` interpreter resolver (#2570.3) and the scoped
subprocess contention lock (#2493) — mission ``loop-friction-quickwins-2``
WP03.

The unit-level branch tests below exercise
``specify_cli.review._interpreter.resolve_pytest_command`` directly (no
subprocess I/O). The remaining tests are real-subprocess integration cases:
they prove ``review.pre_review_gate.run_scoped_tests_at_head`` actually
routes through the resolved interpreter and the contention lock, rather than
just asserting on a monkeypatched ``subprocess.run`` — a mock-only proof
would not catch a regression back to the hardcoded ``sys.executable``
literal this WP removes.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

import pytest

from specify_cli.review import _interpreter, pre_review_gate

pytestmark = [pytest.mark.integration]

_PASSING_TEST_BODY = "def test_pass():\n    assert True\n"


def _write_tiny_pytest_project(base: Path) -> None:
    (base / "test_sample.py").write_text(_PASSING_TEST_BODY, encoding="utf-8")


# ---------------------------------------------------------------------------
# T010(i-iii) — resolve_pytest_command branch coverage
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_uv_present_and_pyproject_present_resolves_to_uv_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Branch (i): both legs of the AND hold -> route through ``uv run``."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    monkeypatch.setattr(_interpreter.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)

    command = _interpreter.resolve_pytest_command(["tests/foo"], repo_root=tmp_path)

    assert command == ["uv", "run", "--project", str(tmp_path), "python", "-m", "pytest", "tests/foo"]


@pytest.mark.fast
def test_uv_present_but_no_pyproject_falls_back_to_sys_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Branch (ii) — G2, the AND's second leg: no ``pyproject.toml`` at
    ``repo_root`` even though ``uv`` is on PATH -> fall back."""
    monkeypatch.setattr(_interpreter.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    assert not (tmp_path / "pyproject.toml").exists()

    command = _interpreter.resolve_pytest_command(["tests/foo"], repo_root=tmp_path)

    assert command == [sys.executable, "-m", "pytest", "tests/foo"]


@pytest.mark.fast
def test_uv_absent_falls_back_to_sys_executable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Branch (iii): no ``uv`` on PATH at all -> fall back regardless of pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    monkeypatch.setattr(_interpreter.shutil, "which", lambda _name: None)

    command = _interpreter.resolve_pytest_command(["tests/foo"], repo_root=tmp_path)

    assert command == [sys.executable, "-m", "pytest", "tests/foo"]


# ---------------------------------------------------------------------------
# T010 red-first — unmask #2570.3: a pytest-lacking sys.executable must not
# force a spurious no_coverage when uv can run the suite instead.
# ---------------------------------------------------------------------------


def _write_fake_uv(bin_dir: Path) -> None:
    """A stand-in ``uv`` on PATH: ignores its args except ``--junitxml=``,
    to which it writes a single passing ``<testcase>`` and exits 0."""
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "junit_path = next(a.split('=', 1)[1] for a in args if a.startswith('--junitxml='))\n"
        "with open(junit_path, 'w', encoding='utf-8') as fh:\n"
        "    fh.write('<testsuite><testcase classname=\"t\" name=\"test_pass\" /></testsuite>')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)


def _write_broken_python(bin_dir: Path) -> Path:
    """A stand-in for a ``sys.executable`` that lacks the ``pytest`` module:
    it always errors and never writes a JUnit file, mirroring the real
    ``No module named pytest`` failure mode (#2570.3)."""
    broken_python = bin_dir / "broken-python"
    broken_python.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write(\"ModuleNotFoundError: No module named 'pytest'\\n\")\n"
        "sys.exit(1)\n",
        encoding="utf-8",
    )
    broken_python.chmod(0o755)
    return broken_python


@pytest.mark.integration
def test_pytest_lacking_sys_executable_still_yields_real_verdict_via_uv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Red-first proof of #2570.3: bug-present code hardcodes ``sys.executable``
    unconditionally, so it would call ``broken-python -m pytest ...`` here,
    produce no JUnit output, and degrade to ``HeadRunResult(ran=False)`` (the
    caller then reports ``GateOutcome.NO_COVERAGE``). Fixed code detects
    ``uv`` + ``pyproject.toml`` and routes through the (working) fake ``uv``
    instead, never touching the broken interpreter at all."""
    project_dir = tmp_path
    (project_dir / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    _write_tiny_pytest_project(project_dir)

    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    broken_python = _write_broken_python(bin_dir)
    _write_fake_uv(bin_dir)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(pre_review_gate.sys, "executable", str(broken_python))

    result = pre_review_gate.run_scoped_tests_at_head(["test_sample.py"], repo_root=project_dir)

    assert result.ran is True
    assert result.current_failures == ()


# ---------------------------------------------------------------------------
# T011 — contention lock: serialization + decoupled timeout
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_scoped_run_lock_serializes_two_overlapping_holders() -> None:
    """Two overlapping ``_scoped_run_lock`` holders never run their critical
    section concurrently — whichever thread enters first must also exit
    before the second thread's entry is recorded."""
    events: list[str] = []
    lock_guard = threading.Lock()
    barrier = threading.Barrier(2)

    def hold(tag: str) -> None:
        barrier.wait(timeout=5)
        with pre_review_gate._scoped_run_lock(acquire_timeout=2.0):
            with lock_guard:
                events.append(f"{tag}-enter")
            time.sleep(0.05)
            with lock_guard:
                events.append(f"{tag}-exit")

    threads = [threading.Thread(target=hold, args=(tag,)) for tag in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert len(events) == 4
    first_tag = events[0].split("-")[0]
    assert events[1] == f"{first_tag}-exit", f"interleaved holders: {events}"


@pytest.mark.fast
def test_lock_acquire_timeout_falls_back_without_charging_run_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """K-9: under permanent lock contention the acquire loop gives up after
    its OWN short bound and the run proceeds anyway — the process observation
    ``timeout`` budget (and the wall-clock spent) must reflect only the SHORT
    lock-acquire bound, never the (much larger) run timeout."""
    monkeypatch.setattr(pre_review_gate, "_LOCK_ACQUIRE_TIMEOUT_DEFAULT", 0.05)

    import fcntl

    def _always_contended(_fd: int, _flags: int) -> None:
        raise OSError("simulated permanent contention")

    monkeypatch.setattr(fcntl, "flock", _always_contended)

    captured_command: list[str] = []
    captured_timeouts: list[float] = []

    class _FakeProcess:
        returncode = 0

    def _fake_launch(command: list[str], **_kwargs: object) -> _FakeProcess:
        captured_command.extend(command)
        return _FakeProcess()

    def _fake_wait(_process: object, timeout: float) -> tuple[str, str]:
        captured_timeouts.append(timeout)
        junit_arg = next(arg for arg in captured_command if arg.startswith("--junitxml="))
        junit_path = Path(junit_arg.split("=", 1)[1])
        junit_path.write_text(
            '<testsuite><testcase classname="t" name="ok" /></testsuite>', encoding="utf-8",
        )
        return "", ""

    monkeypatch.setattr(pre_review_gate, "_HEAD_RUN_HEARTBEAT_INTERVAL", 300.0)
    monkeypatch.setattr(pre_review_gate, "_launch_scoped_process", _fake_launch)
    observation_clock = iter((100.0, 100.0))

    start = time.monotonic()
    result = pre_review_gate.run_scoped_tests_at_head(
        ["tests/status"],
        repo_root=tmp_path,
        timeout=300,
        monotonic=lambda: next(observation_clock),
        wait=_fake_wait,
    )
    elapsed = time.monotonic() - start

    assert result.ran is True
    assert captured_timeouts == [300]  # process observation receives the full run budget
    assert elapsed < 2.0  # bounded by the short lock-acquire timeout, not the 300s run timeout

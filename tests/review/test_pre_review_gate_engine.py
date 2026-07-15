"""Tests for specify_cli.review.pre_review_gate — WP01: scope derivation +
head-side runner + verdict engine (mission review-regression-gate-01KWX6DF).

Scope-derivation cases below use INJECTED ``filter_groups``/``composite_routing``
fixtures (offline, no repo I/O) so they stay hermetic and fast — the proof that
the derivation reads the LIVE authorities lives in
``tests/architectural/test_pre_review_scope_singlesource.py`` (FR-006), not
here. The fixtures below deliberately mirror the real ci-quality.yml shapes
(status/core_misc/execution_context overlap; auth_audit_git/governance
composites) so the shape + exclusion assertions still pin the real-world
scenarios named in the spec (SC-003/SC-004/SC-007), just against a stable,
hand-built substrate instead of the live workflow file.
"""
from __future__ import annotations

import contextlib
import signal
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from specify_cli.review import pre_review_gate
from specify_cli.review.baseline import BaselineFailure, BaselineTestResult
from specify_cli.review.pre_review_gate import (
    GateOutcome,
    HeadRunResult,
    HeadRunState,
    ScopeResult,
)

# Module-level marker required by tests/architectural/test_pytest_marker_convention.py
# (WP01 landed this file without one — a pre-existing arch-gate red this WP02 sweep
# surfaced and Boy-Scout-fixes here). ``integration`` (not ``fast``) is the correct
# choice: the file's per-function markers stay authoritative and additive under it
# (the 18 ``@pytest.mark.fast`` cases remain selected by the fast-tests-review shard's
# ``-m "fast and not windows_ci"``), while ``integration`` keeps the 3 real-subprocess
# tests (``run_scoped_tests_at_head`` spawns real pytest) OUT of the fast lane — a
# module-level ``fast`` would have wrongly dragged them in.
pytestmark = [pytest.mark.integration]

# ---------------------------------------------------------------------------
# Synthetic filter-group / composite-routing fixtures (mirror the real
# ci-quality.yml shapes closely enough to pin SC-003/SC-004/SC-007 offline).
# ---------------------------------------------------------------------------

FAKE_GROUPS: dict[str, tuple[str, ...]] = {
    "status": (
        "src/specify_cli/status/**",
        "tests/status/**",
        "tests/specify_cli/status/**",
    ),
    "core_misc": (
        "src/specify_cli/status/**",
        "src/kernel/**",
        "tests/architectural/**",
        "tests/integration/**",
        "tests/contract/**",
    ),
    "execution_context": (
        "src/specify_cli/status/**",
        "tests/architectural/test_execution_context_parity.py",
    ),
    "any_src": ("src/**",),
    "e2e": ("tests/e2e/**",),
    "auth_audit_git": (
        "src/specify_cli/auth/**",
        "src/specify_cli/audit/**",
        "src/specify_cli/git/**",
    ),
    "governance": (
        "src/specify_cli/validators/**",
        "src/specify_cli/doctrine/**",
    ),
}

FAKE_ROUTING: dict[str, pre_review_gate._CompositeRoute] = {
    "git": (None, None, ("tests/git", "tests/git_ops")),
    "validators": (None, None, ()),
}

_DUMMY_ROOT = Path(".")


def _derive(changed_files: list[str]) -> ScopeResult:
    return pre_review_gate.derive_test_scope(
        changed_files,
        repo_root=_DUMMY_ROOT,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )


# ---------------------------------------------------------------------------
# Scope derivation: per-shard shape (FR-002/SC-003)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_per_shard_group_contributes_its_own_test_globs_and_excludes_core_misc() -> None:
    """status/emit.py-shaped file: member of status (focused, per-shard),
    core_misc (catch-all, excluded), and execution_context (focused,
    per-shard) — mirrors the spec's own grounding example."""
    scope = _derive(["src/specify_cli/status/emit.py"])
    assert set(scope.test_targets) == {
        "tests/status",
        "tests/specify_cli/status",
        "tests/architectural/test_execution_context_parity.py",
    }
    assert set(scope.matched_shard_groups) == {"status", "execution_context"}
    assert "core_misc" not in scope.matched_shard_groups
    assert not scope.is_empty


@pytest.mark.fast
def test_recall_over_precision_ambiguous_file_gets_every_focused_group() -> None:
    """An ambiguous file matching >=2 focused groups gets BOTH — no attempt
    to pick a single "best" group (recall > precision, spec edge case)."""
    scope = _derive(["src/specify_cli/status/emit.py"])
    assert {"status", "execution_context"} <= set(scope.matched_shard_groups)


# ---------------------------------------------------------------------------
# Scope derivation: composite shape (FR-002/SC-003/SC-007)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_composite_group_with_nonempty_cone_contributes_cone_roots() -> None:
    """A git/**-shaped change resolves via the composite dir's cone_roots,
    not any dorny test glob (auth_audit_git carries none)."""
    scope = _derive(["src/specify_cli/git/foo.py"])
    assert set(scope.test_targets) == {"tests/git", "tests/git_ops"}
    assert scope.matched_composite_dirs == ("git",)
    assert not scope.matched_shard_groups
    assert not scope.is_empty


@pytest.mark.fast
def test_composite_group_with_empty_cone_is_a_no_coverage_warn_not_clean() -> None:
    """SC-007: validators is a real composite dir with an EMPTY committed
    cone — the derivation must surface it as unverified, never silently
    "clean"."""
    scope = _derive(["src/specify_cli/validators/schema.py"])
    assert scope.is_empty
    assert scope.empty_cone_composite_dirs == ("validators",)
    assert "unmapped composite dir" in scope.describe_empty_reason()


# ---------------------------------------------------------------------------
# Scope derivation: catch-all / unmatched exclusion (FR-005)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_catch_all_only_file_is_excluded_and_scope_warns() -> None:
    """A file landing ONLY in a catch-all group (here: core_misc via
    src/kernel/**) contributes nothing — excluded, not a whole-tree run."""
    scope = _derive(["src/kernel/foo.py"])
    assert scope.is_empty
    assert scope.excluded_scope_files == ("src/kernel/foo.py",)
    assert "excluded scope" in scope.describe_empty_reason()


@pytest.mark.fast
def test_unmatched_file_is_excluded_and_scope_warns() -> None:
    """A file matching NO dorny group at all is excluded the same way."""
    scope = _derive(["README.md"])
    assert scope.is_empty
    assert scope.excluded_scope_files == ("README.md",)


@pytest.mark.fast
def test_describe_empty_reason_distinguishes_the_two_sc007_causes() -> None:
    empty_cone_scope = ScopeResult(
        test_targets=(),
        matched_shard_groups=(),
        matched_composite_dirs=("validators",),
        empty_cone_composite_dirs=("validators",),
        excluded_scope_files=(),
    )
    excluded_scope = ScopeResult(
        test_targets=(),
        matched_shard_groups=(),
        matched_composite_dirs=(),
        empty_cone_composite_dirs=(),
        excluded_scope_files=("README.md",),
    )
    assert "unmapped composite dir" in empty_cone_scope.describe_empty_reason()
    assert "excluded scope" in excluded_scope.describe_empty_reason()


# ---------------------------------------------------------------------------
# Head-side scoped runner (FR-001/FR-003, net-new)
# ---------------------------------------------------------------------------


_PASSING_TEST_BODY = "def test_pass():\n    assert True\n"
_FAILING_TEST_BODY = f"{_PASSING_TEST_BODY}\n\ndef test_break():\n    assert False, 'boom'\n"


def _write_tiny_pytest_project(base: Path, *, failing: bool) -> None:
    body = _FAILING_TEST_BODY if failing else _PASSING_TEST_BODY
    (base / "test_sample.py").write_text(body, encoding="utf-8")


class _FakeProcess:
    """Small ``Popen`` double for runner lifecycle tests."""

    def __init__(self, *, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.pid = 424242
        self.returncode = returncode
        self.stdout_text = stdout
        self.stderr_text = stderr
        self.terminated = False
        self.killed = False

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        del timeout
        return self.stdout_text, self.stderr_text

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def poll(self) -> int | None:
        return self.returncode


@pytest.mark.fast
def test_empty_test_targets_never_invokes_subprocess() -> None:
    result = pre_review_gate.run_scoped_tests_at_head([], repo_root=_DUMMY_ROOT)
    assert result.ran is False
    assert result.current_failures == ()
    assert "empty test scope" in (result.error or "")


@pytest.mark.fast
@pytest.mark.parametrize(
    ("platform", "expected_key"),
    [("posix", "start_new_session"), ("nt", "creationflags")],
)
def test_launch_uses_platform_process_group_isolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    platform: str,
    expected_key: str,
) -> None:
    calls: list[dict[str, object]] = []
    process = _FakeProcess()

    def _popen(command: list[str], **kwargs: object) -> _FakeProcess:
        del command
        calls.append(kwargs)
        return process

    monkeypatch.setattr(pre_review_gate.subprocess, "Popen", _popen)
    monkeypatch.setattr(
        pre_review_gate.subprocess,
        "CREATE_NEW_PROCESS_GROUP",
        512,
        raising=False,
    )

    launched = pre_review_gate._launch_scoped_process(
        ["pytest"],
        repo_root=tmp_path,
        env={},
        platform=platform,
    )

    assert launched is process
    assert len(calls) == 1
    assert calls[0][expected_key] == (True if platform == "posix" else 512)
    unexpected_key = "creationflags" if platform == "posix" else "start_new_session"
    assert unexpected_key not in calls[0]


@pytest.mark.fast
@pytest.mark.parametrize("force", [False, True])
def test_windows_signal_targets_owned_descendant_tree(
    force: bool,
) -> None:
    process = _FakeProcess()
    commands: list[tuple[str, ...]] = []

    def _taskkill(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        commands.append(tuple(command))
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

    pre_review_gate._signal_owned_process_tree(
        process,
        force=force,
        platform="nt",
        windows_tree_kill=_taskkill,
    )

    expected = ("taskkill", "/PID", str(process.pid), "/T")
    if force:
        expected += ("/F",)
    assert commands == [expected]
    assert process.terminated is False
    assert process.killed is False


@pytest.mark.fast
@pytest.mark.parametrize(
    ("force", "expected_signal"),
    [(False, signal.SIGTERM), (True, signal.SIGKILL)],
)
def test_posix_signal_targets_owned_process_group(
    monkeypatch: pytest.MonkeyPatch,
    force: bool,
    expected_signal: signal.Signals,
) -> None:
    process = _FakeProcess()
    calls: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(pre_review_gate.os, "killpg", lambda pid, sig: calls.append((pid, sig)))

    pre_review_gate._signal_owned_process_tree(
        process,
        force=force,
        platform="posix",
    )

    assert calls == [(process.pid, expected_signal)]


def _spy_on_resolve_pytest_command(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[tuple[str, ...], Path]]:
    """Wrap (not replace) ``resolve_pytest_command`` so the real command is
    still built and run, while recording every call.

    #2570.3 unmask: prior to WP03, these two real-subprocess tests only
    proved that *some* interpreter with pytest installed could run the
    scoped suite — the ambient ``sys.executable`` running this very test
    process necessarily has pytest, so a regression back to the hardcoded
    ``sys.executable`` literal (bypassing the interpreter-resolution seam
    entirely) would still pass every assertion below. Spying on the seam
    itself closes that gap: it fails loudly (``AttributeError`` on
    bug-present code, where the attribute does not exist; a call-count
    mismatch on a reintroduced hardcoded literal) instead of passing
    silently.
    """
    calls: list[tuple[tuple[str, ...], Path]] = []
    real_resolve = pre_review_gate.resolve_pytest_command

    def _spy(pytest_args: list[str], *, repo_root: Path) -> list[str]:
        calls.append((tuple(pytest_args), repo_root))
        return real_resolve(pytest_args, repo_root=repo_root)

    monkeypatch.setattr(pre_review_gate, "resolve_pytest_command", _spy)
    return calls


@pytest.mark.integration
def test_real_subprocess_run_parses_junit_and_captures_current_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _write_tiny_pytest_project(tmp_path, failing=True)
    calls = _spy_on_resolve_pytest_command(monkeypatch)

    result = pre_review_gate.run_scoped_tests_at_head(["test_sample.py"], repo_root=tmp_path)

    assert result.ran is True
    failing_names = {f.test for f in result.current_failures}
    assert any("test_break" in name for name in failing_names)
    assert not any("test_pass" in name for name in failing_names)
    assert len(calls) == 1
    assert calls[0][1] == tmp_path


@pytest.mark.integration
def test_real_subprocess_run_with_no_failures_yields_empty_current_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _write_tiny_pytest_project(tmp_path, failing=False)
    calls = _spy_on_resolve_pytest_command(monkeypatch)

    result = pre_review_gate.run_scoped_tests_at_head(["test_sample.py"], repo_root=tmp_path)

    assert result.ran is True
    assert result.current_failures == ()
    assert len(calls) == 1
    assert calls[0][1] == tmp_path


@pytest.mark.fast
def test_missing_junit_output_degrades_to_a_warn_not_a_crash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        pre_review_gate.subprocess,
        "Popen",
        lambda *args, **kwargs: _FakeProcess(returncode=1, stderr="boom"),
    )
    result = pre_review_gate.run_scoped_tests_at_head(["tests/status"], repo_root=tmp_path)
    assert result.ran is False
    assert result.returncode == 1
    assert result.state is HeadRunState.INCOMPLETE_OUTPUT
    assert "no JUnit XML produced" in (result.error or "")


@pytest.mark.fast
def test_timeout_degrades_to_a_warn_not_a_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    process = _FakeProcess()
    waits = 0

    def _wait(candidate: subprocess.Popen[str], timeout: float) -> tuple[str, str]:
        nonlocal waits
        del candidate
        waits += 1
        if waits == 1:
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=timeout)
        return "", "timed out"

    monkeypatch.setattr(pre_review_gate.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(pre_review_gate, "_signal_owned_process_tree", lambda *args, **kwargs: None)
    clock = iter((0.0, 1.0, 1.0))
    result = pre_review_gate.run_scoped_tests_at_head(
        ["tests/status"],
        repo_root=tmp_path,
        timeout=1,
        monotonic=lambda: next(clock),
        wait=_wait,
    )
    assert result.ran is False
    assert result.state is HeadRunState.TIMED_OUT
    assert "timed out" in (result.error or "")


@pytest.mark.fast
def test_launch_failure_degrades_to_a_warn_not_a_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _raise_oserror(command: list[str], **kwargs: object) -> _FakeProcess:
        raise OSError("no such file or directory")

    monkeypatch.setattr(pre_review_gate.subprocess, "Popen", _raise_oserror)
    result = pre_review_gate.run_scoped_tests_at_head(["tests/status"], repo_root=tmp_path)
    assert result.ran is False
    assert result.state is HeadRunState.LAUNCH_FAILED
    assert "failed to launch" in (result.error or "")


@pytest.mark.fast
def test_malformed_junit_degrades_to_a_warn_not_a_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
        junit_arg = next(arg for arg in command if arg.startswith("--junitxml="))
        junit_path = Path(junit_arg.split("=", 1)[1])
        junit_path.write_text("not valid xml <<<", encoding="utf-8")
        return _FakeProcess(returncode=1)

    monkeypatch.setattr(pre_review_gate.subprocess, "Popen", _fake_popen)
    result = pre_review_gate.run_scoped_tests_at_head(["tests/status"], repo_root=tmp_path)
    assert result.ran is False
    assert result.state is HeadRunState.INCOMPLETE_OUTPUT
    assert "failed to parse" in (result.error or "")


@pytest.mark.fast
def test_observer_emits_bounded_heartbeats_without_delaying_completion() -> None:
    process = _FakeProcess()
    now = 0.0
    wait_calls = 0
    heartbeats: list[float] = []

    def _wait(candidate: subprocess.Popen[str], timeout: float) -> tuple[str, str]:
        nonlocal now, wait_calls
        del candidate
        wait_calls += 1
        if wait_calls <= 2:
            now += timeout
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=timeout)
        return "done", ""

    state, stdout, stderr = pre_review_gate._observe_process(
        process,
        timeout=300,
        progress_callback=heartbeats.append,
        monotonic=lambda: now,
        wait=_wait,
    )

    assert state is HeadRunState.COMPLETED
    assert (stdout, stderr) == ("done", "")
    assert heartbeats == [30.0, 60.0]


@pytest.mark.fast
def test_observer_cancellation_terminates_and_reaps_owned_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess(stderr="cancelled")
    waits = 0
    signals: list[bool] = []

    def _wait(candidate: subprocess.Popen[str], timeout: float) -> tuple[str, str]:
        nonlocal waits
        del candidate, timeout
        waits += 1
        if waits == 1:
            raise KeyboardInterrupt
        return "", process.stderr_text

    monkeypatch.setattr(
        pre_review_gate,
        "_signal_owned_process_tree",
        lambda candidate, *, force: signals.append(force),
    )
    state, _stdout, stderr = pre_review_gate._observe_process(
        process,
        timeout=300,
        progress_callback=None,
        monotonic=lambda: 0.0,
        wait=_wait,
    )

    assert state is HeadRunState.CANCELLED
    assert stderr == "cancelled"
    assert signals == [False]
    assert waits == 2


@pytest.mark.fast
def test_termination_escalates_to_kill_and_reaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess(stdout="diagnostic")
    signals: list[bool] = []

    def _wait(candidate: subprocess.Popen[str], timeout: float) -> tuple[str, str]:
        del candidate
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=timeout)

    monkeypatch.setattr(
        pre_review_gate,
        "_signal_owned_process_tree",
        lambda candidate, *, force: signals.append(force),
    )
    output = pre_review_gate._terminate_and_reap(process, wait=_wait)

    assert signals == [False, True]
    assert output == ("diagnostic", "")


@pytest.mark.fast
def test_cancellation_releases_scoped_run_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    process = _FakeProcess()
    lock_events: list[str] = []
    waits = 0

    @contextlib.contextmanager
    def _recording_lock() -> Iterator[None]:
        lock_events.append("enter")
        try:
            yield
        finally:
            lock_events.append("exit")

    def _wait(candidate: subprocess.Popen[str], timeout: float) -> tuple[str, str]:
        nonlocal waits
        del candidate, timeout
        waits += 1
        if waits == 1:
            raise KeyboardInterrupt
        return "", ""

    monkeypatch.setattr(pre_review_gate, "_scoped_run_lock", _recording_lock)
    monkeypatch.setattr(pre_review_gate.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(pre_review_gate, "_signal_owned_process_tree", lambda *args, **kwargs: None)

    result = pre_review_gate.run_scoped_tests_at_head(
        ["tests/status"],
        repo_root=tmp_path,
        wait=_wait,
    )

    assert result.state is HeadRunState.CANCELLED
    assert lock_events == ["enter", "exit"]


# ---------------------------------------------------------------------------
# Verdict composition + diff_baseline reuse (FR-001/FR-003/SC-001/SC-002)
# ---------------------------------------------------------------------------


def _make_baseline(
    failures: tuple[BaselineFailure, ...] = (),
    *,
    failed: int = 0,
) -> BaselineTestResult:
    return BaselineTestResult(
        wp_id="WP01",
        captured_at="2026-07-07T00:00:00Z",
        base_branch="main",
        base_commit="abc1234",
        test_runner="pytest",
        total=10,
        passed=10 - failed,
        failed=failed,
        skipped=0,
        failures=failures,
    )


def _sentinel_baseline() -> BaselineTestResult:
    return BaselineTestResult(
        wp_id="WP01",
        captured_at="2026-07-07T00:00:00Z",
        base_branch="main",
        base_commit="",
        test_runner="pytest",
        total=0,
        passed=0,
        failed=-1,
        skipped=0,
        failures=(),
    )


@pytest.mark.fast
def test_empty_scope_short_circuits_before_running_or_diffing(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> HeadRunResult:
        raise AssertionError("run_scoped_tests_at_head must not be called for an empty scope")

    monkeypatch.setattr(pre_review_gate, "run_scoped_tests_at_head", _boom)
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/validators/schema.py"],
        repo_root=_DUMMY_ROOT,
        baseline=None,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.NO_COVERAGE


@pytest.mark.fast
def test_run_that_does_not_complete_degrades_to_no_coverage_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=False, error="boom"),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=None,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.NO_COVERAGE
    assert "scoped test run did not complete" in (verdict.reason or "")


@pytest.mark.fast
@pytest.mark.parametrize(
    ("state", "outcome"),
    [
        (HeadRunState.TIMED_OUT, GateOutcome.TIMED_OUT),
        (HeadRunState.CANCELLED, GateOutcome.CANCELLED),
    ],
)
def test_terminal_interruption_remains_typed_in_gate_verdict(
    monkeypatch: pytest.MonkeyPatch,
    state: HeadRunState,
    outcome: GateOutcome,
) -> None:
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *args, **kwargs: HeadRunResult(
            ran=False,
            error=state.value,
            state=state,
        ),
    )

    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=None,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )

    assert verdict.outcome is outcome
    assert verdict.run_state is state
    assert verdict.outcome is not GateOutcome.NO_COVERAGE


@pytest.mark.fast
def test_uncomputable_baseline_none_degrades_to_warn_and_surfaces_all_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_failure = BaselineFailure(test="tests.git.test_x", error="boom", file="tests/git/test_x.py:1")
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=True, current_failures=(fake_failure,)),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=None,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.UNVERIFIED_BASELINE
    assert verdict.new_failures == (fake_failure,)


@pytest.mark.fast
def test_sentinel_baseline_degrades_to_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_failure = BaselineFailure(test="tests.git.test_x", error="boom", file="tests/git/test_x.py:1")
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=True, current_failures=(fake_failure,)),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=_sentinel_baseline(),
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.UNVERIFIED_BASELINE


@pytest.mark.fast
def test_pre_existing_failure_does_not_block_no_new_failures_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SC-002: a base failure in the affected shard does NOT block the WP."""
    shared_failure = BaselineFailure(
        test="tests.git.test_known_red", error="pre-existing", file="tests/git/test_x.py:1",
    )
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=True, current_failures=(shared_failure,)),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=_make_baseline((shared_failure,), failed=1),
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert verdict.pre_existing_failures == (shared_failure,)
    assert verdict.new_failures == ()


@pytest.mark.fast
def test_new_failure_is_surfaced_via_the_real_diff_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-001: proves genuine ``diff_baseline`` reuse — the real function is
    spied on (still delegated to), not reimplemented."""
    calls: list[tuple[BaselineTestResult, list[BaselineFailure]]] = []
    real_diff_baseline = pre_review_gate.diff_baseline

    def _spy(
        baseline: BaselineTestResult, current_failures: list[BaselineFailure],
    ) -> tuple[list[BaselineFailure], list[BaselineFailure], list[str]]:
        calls.append((baseline, list(current_failures)))
        return real_diff_baseline(baseline, current_failures)

    monkeypatch.setattr(pre_review_gate, "diff_baseline", _spy)

    new_failure = BaselineFailure(
        test="tests.git.test_newly_broken", error="AssertionError", file="tests/git/test_x.py:5",
    )
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=True, current_failures=(new_failure,)),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=_make_baseline(),
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.NEW_FAILURES
    assert verdict.new_failures == (new_failure,)
    assert len(calls) == 1


@pytest.mark.integration
def test_end_to_end_new_failure_detected_via_real_subprocess_and_real_diff(tmp_path: Path) -> None:
    """Full composition with a REAL subprocess pytest run + the REAL
    diff_baseline — only the scope-derivation inputs are synthetic."""
    _write_tiny_pytest_project(tmp_path, failing=True)
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=tmp_path,
        baseline=_make_baseline(),  # base had no failures
        filter_groups={"auth_audit_git": ("src/specify_cli/git/**",)},
        composite_routing={"git": (None, None, ("test_sample.py",))},
    )
    assert verdict.outcome is GateOutcome.NEW_FAILURES
    assert any("test_break" in f.test for f in verdict.new_failures)

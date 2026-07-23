"""Auto-scoped pre-review regression gate: scope aggregation + head-side runner + verdict.

Mission ``review-regression-gate-01KWX6DF`` WP01 (closes #572 + the per-WP
review-blind-spot facet of #1979; part of #2283). ``move-task --to
for_review`` (``cli/commands/agent/tasks_move_task.py``) scopes review to a
WP's ``owned_files`` — a WP that breaks a *consumer* outside its owned set
would otherwise reach approval unnoticed. This module is the engine half of
the fix (the CLI hook + config/override wiring lives in ``tasks_move_task.py``):

1. **Build a :class:`ScopeResult`** (FR-002/FR-005/FR-006) from a WP's
   changed files via an injected
   :class:`~specify_cli.review.scope_source.ScopeSource` (see
   :func:`_scope_result_from_source`). The per-file derivation SHAPE — which
   dorny filter groups match, catch-all exclusion, composite-dir cone
   routing — is owned entirely by the port's implementations
   (``scope_source.py``); this module never re-derives it (mission
   ``scopesource-gate-followup-01KY6S9P`` WP04 retired the census tier this
   module used to own directly, FR-001). An EMPTY affected scope from a
   census-*narrowing* source is NEVER "verified clean" — always a
   ``no_coverage`` warn (SC-007), distinct from a green ``no_new_failures``
   verdict.

2. **Run the derived scope at head** (subprocess) — either the legacy
   hardcoded pytest/JUnit path (:func:`run_scoped_tests_at_head`, kept live
   via the FR-004 override tier) or the injected port's own
   ``test_command()``/``parse_results()`` (:func:`_evaluate_via_scope_source`)
   — and parse its output into per-failure identities.

3. **Compute the verdict** as ``head_failures - base_failures`` via
   ``review/baseline.py``'s existing ``diff_baseline`` (reused unchanged).
   An uncomputable baseline degrades to a warn, never a hard block (FR-003);
   a KNOWN baseline/head ``ScopeSource`` identity mismatch degrades to
   ``SOURCE_MISMATCH``, also a warn, never a hard block (FR-009/FR-011,
   mission ``scopesource-gate-followup-01KY6S9P`` WP04).
"""
from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from kernel.paths import to_posix
from specify_cli.paths import get_runtime_root
from specify_cli.review._interpreter import resolve_pytest_command
from specify_cli.review.baseline import (
    CAPTURE_BASELINE_TIMEOUT_SECONDS,
    BaselineFailure,
    BaselineTestResult,
    _extract_junit_output_path,
    _parse_junit_xml,
    diff_baseline,
)
from specify_cli.review.scope_source import (
    _JUNIT_ARTIFACT_FILENAME,
    RawRunResult,
    ScopeBreakdownSource,
    ScopeSource,
    empty_scope_is_coverage_gap,
    exposes_scope_breakdown,
    scope_source_identity,
)

# ---------------------------------------------------------------------------
# Composite-route shape (still referenced by the kept seam
# ``tasks_move_task._pre_review_gate_composite_routing`` and the KEPT
# ``_CompositeRoute`` type alias, C-002) — the census DERIVATION that used to
# live here (FR-001, mission scopesource-gate-followup-01KY6S9P WP04) is
# retired; the LIVE derivation now lives exclusively in
# ``scope_source.GateCoverageScopeSource`` (its own private copy).
# ---------------------------------------------------------------------------

# Mirrors _gate_coverage._CompositeRoute: (target_group, target_shard, cone_roots).
_CompositeRoute = tuple[str | None, str | None, tuple[str, ...]]

_DEFAULT_HEAD_RUN_TIMEOUT = CAPTURE_BASELINE_TIMEOUT_SECONDS  # shared with baseline.py's capture_baseline.
_HEAD_RUN_HEARTBEAT_INTERVAL = 30.0
_HEAD_RUN_TERMINATE_GRACE = 5.0

# How many trailing stderr chars a run-error message carries (bounded tail).
_STDERR_TAIL_CHARS = 500


def _gate_run_env() -> dict[str, str]:
    """Environment for an automated gate subprocess: inherit + force headless.

    Shared by the pytest/JUnit runner (:func:`run_scoped_tests_at_head`) and
    the raw-command runner (:func:`_run_raw_command`) so the ``PWHEADLESS``
    guard — never pop a browser window during an automated gate run — is set
    in ONE place rather than copied per call site.
    """
    env = dict(os.environ)
    env["PWHEADLESS"] = "1"
    return env


def _launch_failed_error(exc: OSError) -> str:
    """Shared ``OSError`` launch-failure message for the head-run subprocess."""
    return f"scoped test run failed to launch: {exc}"


def _timed_out_error(timeout: int, stderr: str) -> str:
    """Shared timeout message carrying a bounded stderr tail."""
    return f"scoped test run timed out after {timeout}s; stderr tail: {stderr[-_STDERR_TAIL_CHARS:]}"


def _cancelled_error(stderr: str) -> str:
    """Shared cancellation message carrying a bounded stderr tail."""
    return f"scoped test run cancelled; stderr tail: {stderr[-_STDERR_TAIL_CHARS:]}"


class GateAuthoritiesUnavailable(RuntimeError):
    """The live CI-topology authorities module could not be loaded for a repo.

    Raised by :class:`~specify_cli.review.scope_source.GateCoverageScopeSource`
    (the SOLE reachable importer of ``tests/architectural/_gate_coverage.py``
    as of mission ``doctrine-controlled-transition-gates-01KY51Z7`` WP03,
    FR-009) when that module is missing, fails to import, or resolves to a
    module living outside the requested ``repo_root`` (a stale cross-repo
    ``sys.modules`` cache hit). Callers treat this as an "unverified scope"
    signal (folded into a ``no_coverage`` warn by the caller), never as a hard
    failure — an inability to compute coverage must be surfaced, not silently
    swallowed or escalated to a crash.

    ``is_consumer_repo`` (#2534) distinguishes WHY the authority is missing:
    ``True`` when ``repo_root`` itself never carried
    ``tests/architectural/_gate_coverage.py`` (a legitimate ``spec-kitty
    init`` consumer checkout — this is the expected, common case), ``False``
    when the module SHOULD exist there (inside the spec-kitty source repo)
    but genuinely failed to load — a real signal worth the detailed,
    internal-audience message. Callers (the ``move-task --to for_review``
    CLI hook) use this flag to pick a calm consumer-facing message instead of
    naming this internal module to an operator who has never heard of it.

    This class stays here (not relocated to ``scope_source.py``) because
    WP09's ``tasks_move_task.py`` reader still depends on the
    ``is_consumer_repo`` field until that WP's hook-inversion lands — the
    field's cross-file retirement is a tracked fast-follow, not this WP's
    concern (post-task squad finding B3).
    """

    def __init__(self, message: str, *, is_consumer_repo: bool) -> None:
        super().__init__(message)
        self.is_consumer_repo = is_consumer_repo


# ---------------------------------------------------------------------------
# Scope derivation (FR-002/FR-005/FR-006)
#
# The census-narrowing DERIVATION that used to live here (``derive_test_scope``
# + its glob/path helpers) is retired (FR-001, mission
# scopesource-gate-followup-01KY6S9P WP04): the LIVE derivation now lives
# exclusively as a private copy inside
# :class:`~specify_cli.review.scope_source.GateCoverageScopeSource`
# (``scope_source.py``'s own ``_glob_matches_file`` / ``_glob_to_pytest_target``
# / ``_src_dir_segment`` / ``_resolve_excluded_catchall_groups``). This module
# only builds/consumes :class:`ScopeResult` from an injected
# :class:`~specify_cli.review.scope_source.ScopeSource` now (see
# :func:`_scope_result_from_source`, below).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopeResult:
    """The affected-test-set derivation outcome for a WP's changed files.

    ``test_targets`` unions every focused (non-catch-all) matched group's
    contribution: a per-shard group's own ``tests/**`` globs, or a composite
    group's dir-specific ``_COMPOSITE_ROUTING`` cone_roots.
    """

    test_targets: tuple[str, ...]
    matched_shard_groups: tuple[str, ...]
    matched_composite_dirs: tuple[str, ...]
    empty_cone_composite_dirs: tuple[str, ...]
    excluded_scope_files: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        """True iff no test target was derived — ALWAYS a no_coverage warn, never clean."""
        return not self.test_targets

    def describe_empty_reason(self) -> str:
        """Human-readable reason for an empty scope, distinguishing SC-007's two causes."""
        if self.empty_cone_composite_dirs:
            dirs = ", ".join(self.empty_cone_composite_dirs)
            return f"unmapped composite dir(s) with no test cone_roots — unverified (SC-007): {dirs}"
        return (
            "excluded scope — unverified: every changed file landed only in a catch-all "
            "group (core_misc/e2e/any_src) or matched no dorny group at all"
        )

    @classmethod
    def from_override(cls, targets: tuple[str, ...]) -> ScopeResult:
        """Build a ``ScopeResult`` for an explicit override scope (FR-004).

        An override IS the test scope, by definition — no shard-group or
        composite-dir matching runs for it, and no scope files are excluded.
        """
        return cls(
            test_targets=targets,
            matched_shard_groups=(),
            matched_composite_dirs=(),
            empty_cone_composite_dirs=(),
            excluded_scope_files=(),
        )


# ---------------------------------------------------------------------------
# Head-side scoped runner (FR-001/FR-003, net-new — C-001)
# ---------------------------------------------------------------------------


class HeadRunState(StrEnum):
    """Typed completion state for the runner-owned subprocess lifecycle."""

    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    LAUNCH_FAILED = "launch_failed"
    INCOMPLETE_OUTPUT = "incomplete_output"


@dataclass(frozen=True)
class HeadRunResult:
    """Outcome of invoking the derived test scope at head."""

    ran: bool
    current_failures: tuple[BaselineFailure, ...] = ()
    returncode: int | None = None
    error: str | None = None
    state: HeadRunState = HeadRunState.COMPLETED
    stdout: str = ""
    stderr: str = ""


_SCOPED_RUN_LOCK_FILENAME = "pre-review-gate-run.lock"

# K-9: the lock-acquire wait is bounded on ITS OWN short timeout, deliberately
# DECOUPLED from ``_DEFAULT_HEAD_RUN_TIMEOUT`` (300s) below. Charging a
# lock-wait against the subprocess run timeout would re-create the exact
# #2493 contention bug FR-004 removes: under N concurrent lanes a shard that
# is fast on its own could still see ``TimeoutExpired`` purely from queueing
# behind a sibling lane's run. A module-level (not a bound default-argument)
# constant so tests can monkeypatch it without needing to re-import the call
# site — a default argument value is frozen at function-definition time and
# a monkeypatch of the constant afterwards would not be observed.
_LOCK_ACQUIRE_TIMEOUT_DEFAULT: float = 5.0
_LOCK_RETRY_SLEEP_S: float = 0.05


@contextlib.contextmanager
def _scoped_run_lock(*, acquire_timeout: float | None = None) -> Iterator[None]:
    """Advisory lock serializing concurrent scoped subprocess runs (#2493).

    Uses a scoped ``fcntl.flock`` rather than the canonical
    :class:`specify_cli.core.file_lock.MachineFileLock`: that helper is an
    ``async`` context manager (built for the async OAuth-refresh call site),
    while this call site is a single synchronous ``subprocess.run``. Bridging
    one bounded, already-synchronous critical section through an event loop
    for a single advisory lock is materially more machinery than the problem
    needs — a scoped, function-local ``fcntl.flock`` (POSIX-only, imported
    lazily so importing this module never breaks on Windows) is the simpler
    sync-native fit and is self-contained to this one call site.

    Acquisition is a short, independently-timed, non-blocking retry loop
    bounded by ``acquire_timeout`` (default :data:`_LOCK_ACQUIRE_TIMEOUT_DEFAULT`)
    — never the caller's (much larger) subprocess run timeout. If the lock
    cannot be acquired within that bound, the caller proceeds WITHOUT it
    (fallback-to-run): losing the advisory serialization guarantee is
    preferable to a gate that blocks indefinitely or trips a false timeout.
    On Windows (no ``fcntl``) this is a no-op — advisory contention
    protection is a POSIX-only nicety here, not a correctness requirement.
    """
    if sys.platform == "win32":  # pragma: no cover - platform-specific, advisory-only nicety
        yield
        return

    import fcntl  # POSIX-only; local import keeps this module importable on Windows.

    timeout = _LOCK_ACQUIRE_TIMEOUT_DEFAULT if acquire_timeout is None else acquire_timeout
    # Lock lives under the canonical runtime root (FR-010: no hand-rolled
    # ``.spec-kitty`` home literal). One machine-wide lock is the right scope
    # for CPU contention: concurrent gate runs across lanes/worktrees on the
    # same machine serialize on it (a per-repo_root lock would not, since each
    # worktree has a distinct root).
    lock_path = get_runtime_root().base / "gate-locks" / _SCOPED_RUN_LOCK_FILENAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    acquired = False
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    break
                time.sleep(_LOCK_RETRY_SLEEP_S)
        yield
    finally:
        if acquired:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


_ProgressCallback = Callable[[float], None]
_ProcessWait = Callable[[subprocess.Popen[str], float], tuple[str, str]]


def _default_process_wait(process: subprocess.Popen[str], timeout: float) -> tuple[str, str]:
    """Drain both pipes while waiting for at most ``timeout`` seconds."""
    return process.communicate(timeout=timeout)


def _run_windows_taskkill(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Invoke Windows' tree-aware process terminator without a shell."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def _signal_owned_process_tree(
    process: subprocess.Popen[str],
    *,
    force: bool,
    platform: str | None = None,
    windows_tree_kill: Callable[[Sequence[str]], subprocess.CompletedProcess[str]] = (
        _run_windows_taskkill
    ),
) -> None:
    """Signal only the process group created for this runner-owned child."""
    platform = platform or os.name
    if platform == "nt":
        command = ["taskkill", "/PID", str(process.pid), "/T"]
        if force:
            command.append("/F")
        result = windows_tree_kill(command)
        if result.returncode != 0 and process.poll() is None:
            # The tree-aware authority can race a naturally exiting child. If
            # it genuinely fails while the parent is still alive, ensure at
            # least that direct child receives the requested signal; the
            # non-zero taskkill diagnostic remains captured by the caller's
            # process output rather than widening to unrelated host PIDs.
            (process.kill if force else process.terminate)()
        return
    try:
        os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
    except (OSError, ProcessLookupError):
        (process.kill if force else process.terminate)()


def _terminate_and_reap(
    process: subprocess.Popen[str],
    *,
    wait: _ProcessWait,
) -> tuple[str, str]:
    """Request termination, escalate after a bound, and reap the owned child."""
    _signal_owned_process_tree(process, force=False)
    try:
        return wait(process, _HEAD_RUN_TERMINATE_GRACE)
    except subprocess.TimeoutExpired:
        _signal_owned_process_tree(process, force=True)
        try:
            return process.communicate(timeout=_HEAD_RUN_TERMINATE_GRACE)
        except subprocess.TimeoutExpired:
            # The owned child is dead post-SIGKILL, but a grandchild that
            # escaped the process group (it called ``setsid`` itself) can
            # inherit and hold the stdout pipe, so the drain never sees EOF.
            # Reap the dead child by PID and return rather than wedging the
            # gate forever on a pipe the group-kill cannot reach. The escaped
            # orphan subtree is a separate, tracked reaping concern
            # (killpg/taskkill cannot cover a re-parented subtree) — it must
            # never turn the runner's own reap into an unbounded hang.
            with contextlib.suppress(Exception):
                process.wait(timeout=_HEAD_RUN_TERMINATE_GRACE)
            return "", ""


def _observe_process(
    process: subprocess.Popen[str],
    *,
    timeout: float,
    progress_callback: _ProgressCallback | None,
    monotonic: Callable[[], float],
    wait: _ProcessWait,
) -> tuple[HeadRunState, str, str]:
    """Drain, observe, and clean up one runner-owned process."""
    started_at = monotonic()
    deadline = started_at + timeout
    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            stdout, stderr = _terminate_and_reap(process, wait=wait)
            return HeadRunState.TIMED_OUT, stdout, stderr
        try:
            stdout, stderr = wait(process, min(_HEAD_RUN_HEARTBEAT_INTERVAL, remaining))
            return HeadRunState.COMPLETED, stdout, stderr
        except subprocess.TimeoutExpired:
            now = monotonic()
            if now >= deadline:
                stdout, stderr = _terminate_and_reap(process, wait=wait)
                return HeadRunState.TIMED_OUT, stdout, stderr
            if progress_callback is not None:
                progress_callback(now - started_at)
        except KeyboardInterrupt:
            stdout, stderr = _terminate_and_reap(process, wait=wait)
            return HeadRunState.CANCELLED, stdout, stderr
        except BaseException:
            _terminate_and_reap(process, wait=wait)
            raise


def _launch_scoped_process(
    command: Sequence[str],
    *,
    repo_root: Path,
    env: Mapping[str, str],
    platform: str | None = None,
) -> subprocess.Popen[str]:
    """Launch one isolated process group using platform-native flags."""
    platform = platform or os.name
    if platform == "nt":
        return subprocess.Popen(
            command,
            cwd=str(repo_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    return subprocess.Popen(
        command,
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def run_scoped_tests_at_head(
    test_targets: Sequence[str],
    *,
    repo_root: Path,
    timeout: int = _DEFAULT_HEAD_RUN_TIMEOUT,
    progress_callback: _ProgressCallback | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    wait: _ProcessWait = _default_process_wait,
) -> HeadRunResult:
    """Run ``test_targets`` at head and parse JUnit into ``current_failures``.

    The shard-scoped invocation itself is net-new (``baseline.py``'s
    ``capture_baseline`` runs one whole, un-scoped ``review.test_command``
    and has no head-side runner of its own) — but the JUnit parsing is
    ``baseline.py``'s existing ``_parse_junit_xml``, reused unchanged (C-001).

    The subprocess command is built via :func:`resolve_pytest_command`
    (#2570.3) so it runs under whichever interpreter actually has ``pytest``
    installed, and the subprocess itself is serialized against concurrent
    scoped runs via :func:`_scoped_run_lock` (#2493).
    """
    if not test_targets:
        return HeadRunResult(
            ran=False,
            error="empty test scope — nothing to run",
            state=HeadRunState.INCOMPLETE_OUTPUT,
        )

    env = _gate_run_env()

    with tempfile.TemporaryDirectory() as tmp_dir:
        junit_path = Path(tmp_dir) / _JUNIT_ARTIFACT_FILENAME
        command = resolve_pytest_command(
            [*test_targets, f"--junitxml={junit_path}", "-q"],
            repo_root=repo_root,
        )
        try:
            with _scoped_run_lock():
                process = _launch_scoped_process(
                    command,
                    repo_root=repo_root,
                    env=env,
                )
                state, stdout, stderr = _observe_process(
                    process,
                    timeout=timeout,
                    progress_callback=progress_callback,
                    monotonic=monotonic,
                    wait=wait,
                )
        except OSError as exc:
            return HeadRunResult(
                ran=False,
                error=_launch_failed_error(exc),
                state=HeadRunState.LAUNCH_FAILED,
            )

        if state is HeadRunState.TIMED_OUT:
            return HeadRunResult(
                ran=False,
                returncode=process.returncode,
                error=_timed_out_error(timeout, stderr),
                state=state,
                stdout=stdout,
                stderr=stderr,
            )
        if state is HeadRunState.CANCELLED:
            return HeadRunResult(
                ran=False,
                returncode=process.returncode,
                error=_cancelled_error(stderr),
                state=state,
                stdout=stdout,
                stderr=stderr,
            )

        if not junit_path.exists():
            return HeadRunResult(
                ran=False,
                returncode=process.returncode,
                error=(
                    f"no JUnit XML produced by the scoped run (exit={process.returncode}); "
                    f"stderr tail: {stderr[-_STDERR_TAIL_CHARS:]}"
                ),
                state=HeadRunState.INCOMPLETE_OUTPUT,
                stdout=stdout,
                stderr=stderr,
            )

        try:
            # Broad catch mirrors baseline.py's own handling around this exact parse
            # call: a malformed-XML runner bug degrades to a warn (error=...), never a crash.
            _total, _passed, _failed, _skipped, failures = _parse_junit_xml(junit_path)
        except Exception as exc:
            return HeadRunResult(
                ran=False,
                returncode=process.returncode,
                error=f"failed to parse scoped-run JUnit XML: {exc}",
                state=HeadRunState.INCOMPLETE_OUTPUT,
                stdout=stdout,
                stderr=stderr,
            )

    return HeadRunResult(
        ran=True,
        current_failures=tuple(failures),
        returncode=process.returncode,
        state=HeadRunState.COMPLETED,
        stdout=stdout,
        stderr=stderr,
    )


# ---------------------------------------------------------------------------
# Verdict (FR-001/FR-003)
# ---------------------------------------------------------------------------


class GateOutcome(StrEnum):
    """The verdict shapes a pre-review gate evaluation can produce."""

    NO_COVERAGE = "no_coverage"  # FR-001/SC-007: empty scope OR run didn't complete — warn, NEVER "clean"
    NO_NEW_FAILURES = "no_new_failures"  # non-empty run, no new failures vs. baseline
    NEW_FAILURES = "new_failures"  # non-empty run, >=1 new failure vs. baseline
    UNVERIFIED_BASELINE = "unverified_baseline"  # FR-003: baseline uncomputable -> warn
    SOURCE_MISMATCH = "source_mismatch"  # FR-009/FR-011: baseline/head ScopeSource identity differs -> warn
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class GateVerdict:
    """The end-to-end pre-review gate result: scope + head run + new-failure diff."""

    outcome: GateOutcome
    scope: ScopeResult
    reason: str | None = None
    new_failures: tuple[BaselineFailure, ...] = ()
    pre_existing_failures: tuple[BaselineFailure, ...] = ()
    run_state: HeadRunState = HeadRunState.COMPLETED


def _classify_current_failures(
    current_failures: tuple[BaselineFailure, ...],
    *,
    scope: ScopeResult,
    baseline: BaselineTestResult | None,
) -> GateVerdict:
    """The shared baseline-diff tail: classify a completed run's failures.

    Extracted (WP03, mission ``doctrine-controlled-transition-gates-01KY51Z7``)
    so BOTH the legacy ``run_scoped_tests_at_head`` path and the NEW
    injected-``ScopeSource`` path (:func:`_evaluate_via_scope_source`) share
    ONE tested verdict-classification body instead of duplicating the
    ``diff_baseline`` call and its outcome mapping.
    """
    if baseline is None or baseline.failed == -1:
        return GateVerdict(
            outcome=GateOutcome.UNVERIFIED_BASELINE,
            scope=scope,
            reason="baseline uncomputable — surfacing all current failures as unverified",
            new_failures=current_failures,
        )

    pre_existing, new_failures, _fixed = diff_baseline(baseline, list(current_failures))
    if new_failures:
        return GateVerdict(
            outcome=GateOutcome.NEW_FAILURES,
            scope=scope,
            new_failures=tuple(new_failures),
            pre_existing_failures=tuple(pre_existing),
        )
    return GateVerdict(
        outcome=GateOutcome.NO_NEW_FAILURES,
        scope=scope,
        pre_existing_failures=tuple(pre_existing),
    )


def _run_raw_command(
    command: Sequence[str],
    *,
    repo_root: Path,
    timeout: int,
    progress_callback: _ProgressCallback | None,
    monotonic: Callable[[], float],
    wait: _ProcessWait,
) -> tuple[HeadRunState, RawRunResult | None, str | None]:
    """Run ``command`` under the SAME process-lifecycle machinery
    :func:`run_scoped_tests_at_head` uses (launch/observe/lock/reap), but
    without baking in a pytest/JUnit-specific command shape — the
    injected-``ScopeSource`` counterpart (T011/FR-010). Returns the run
    state, an unparsed :class:`RawRunResult` (``None`` on a non-completion),
    and an error string (``None`` on success).

    A ``--junitxml=<relative path>`` embedded in a ``DeclaredCommandScopeSource``
    -resolved command resolves against the subprocess's ``cwd`` (``repo_root``,
    per :func:`_launch_scoped_process`) — mirroring the SAME B1 anchor
    ``baseline._run_command_for_baseline`` applies (data-model.md sec. 5),
    on the head side (mission scopesource-gate-followup-01KY6S9P WP04). Without
    this, a relative artifact path is checked against THIS process's own cwd
    (the gate's, not the subprocess's), silently missing a genuinely-produced
    artifact and mislabeling the run's ``scope_source_identity`` parse-mode —
    the exact false-``SOURCE_MISMATCH`` shape T024's parity suite exists to
    catch.
    """
    env = _gate_run_env()
    try:
        with _scoped_run_lock():
            process = _launch_scoped_process(list(command), repo_root=repo_root, env=env)
            state, stdout, stderr = _observe_process(
                process,
                timeout=timeout,
                progress_callback=progress_callback,
                monotonic=monotonic,
                wait=wait,
            )
    except OSError as exc:
        return HeadRunState.LAUNCH_FAILED, None, _launch_failed_error(exc)

    if state is HeadRunState.TIMED_OUT:
        return state, None, _timed_out_error(timeout, stderr)
    if state is HeadRunState.CANCELLED:
        return state, None, _cancelled_error(stderr)

    artifact_path = _extract_junit_output_path(command)
    if artifact_path is not None and not artifact_path.is_absolute():
        artifact_path = repo_root / artifact_path
    raw = RawRunResult(returncode=process.returncode, stdout=stdout, stderr=stderr, output_artifact_path=artifact_path)
    return state, raw, None


_NO_TEST_COMMAND_REASON = "no test command configured for the injected ScopeSource — review proceeds without it"


def _evaluate_via_scope_source(
    scope: ScopeResult,
    *,
    repo_root: Path,
    baseline: BaselineTestResult | None,
    timeout: int,
    progress_callback: _ProgressCallback | None,
    monotonic: Callable[[], float],
    wait: _ProcessWait,
    scope_source: ScopeSource,
) -> GateVerdict:
    """T011/FR-010/FR-011/FR-012: drive the head run + parse through the
    injected port instead of the hardcoded pytest/JUnit path
    (:func:`run_scoped_tests_at_head` / :func:`_parse_junit_xml`).

    Empty-scope handling is impl-shape-dependent (NFR-001):

    - A census-*narrowing* source (``GateCoverageScopeSource``, satisfying
      :class:`~specify_cli.review.scope_source.ScopeBreakdownSource`) treats an
      empty derived scope as a coverage gap — a ``no_coverage`` warn carrying the
      incumbent :meth:`ScopeResult.describe_empty_reason` wording — exactly as
      the now-retired census tier + the legacy branch of :func:`evaluate_with_scope`
      did. Restoring this keeps the empty-cone / all-excluded cases from silently
      running the whole suite through the inverted hook.
    - A non-narrowing implementation (``DeclaredCommandScopeSource``)
      legitimately reports an empty per-file scope while still running its whole
      declared suite (FR-003/FR-010) — that is not a no-coverage signal. For it,
      the ONLY no-coverage trigger here is ``test_command() -> None`` (FR-012),
      the port's own explicit no-config signal.

    **``SOURCE_MISMATCH`` (FR-009/FR-011, mission
    scopesource-gate-followup-01KY6S9P WP04).** After a completed run, the
    head-side identity (:func:`~specify_cli.review.scope_source.scope_source_identity`)
    is compared against the already-loaded ``baseline.source_identity`` (the
    baseline itself is loaded upstream, by ``tasks_move_task._mt_resolve_gate_baseline``
    — this function only COMPARES). A KNOWN (non-``"unknown"``) baseline
    identity that differs from the head's own -> ``SOURCE_MISMATCH`` (warn,
    fail-open by construction — see ``verdict_aggregation``'s member
    allowlists). ``baseline is None`` or its identity is ``"unknown"`` (legacy
    artifact / never captured) -> degrades to the existing
    ``UNVERIFIED_BASELINE`` path via :func:`_classify_current_failures`, never a
    mismatch.
    """
    if empty_scope_is_coverage_gap(scope_source) and scope.is_empty:
        return GateVerdict(outcome=GateOutcome.NO_COVERAGE, scope=scope, reason=scope.describe_empty_reason())

    command = scope_source.test_command()
    if command is None:
        return GateVerdict(outcome=GateOutcome.NO_COVERAGE, scope=scope, reason=_NO_TEST_COMMAND_REASON)

    state, raw, error = _run_raw_command(
        [*command, *scope.test_targets],
        repo_root=repo_root,
        timeout=timeout,
        progress_callback=progress_callback,
        monotonic=monotonic,
        wait=wait,
    )
    if state is HeadRunState.TIMED_OUT:
        return GateVerdict(outcome=GateOutcome.TIMED_OUT, scope=scope, reason=error, run_state=state)
    if state is HeadRunState.CANCELLED:
        return GateVerdict(outcome=GateOutcome.CANCELLED, scope=scope, reason=error, run_state=state)
    if raw is None:
        return GateVerdict(
            outcome=GateOutcome.NO_COVERAGE,
            scope=scope,
            reason=f"scoped test run did not complete: {error}",
            run_state=state,
        )

    failures = scope_source.parse_results(raw)
    head_identity = scope_source_identity(scope_source, raw)
    if baseline is not None and baseline.source_identity != "unknown" and baseline.source_identity != head_identity:
        return GateVerdict(
            outcome=GateOutcome.SOURCE_MISMATCH,
            scope=scope,
            reason=(
                f"baseline captured under {baseline.source_identity}; head ran under "
                f"{head_identity} — failure identities are not comparable"
            ),
        )
    return _classify_current_failures(failures, scope=scope, baseline=baseline)


def evaluate_with_scope(
    scope: ScopeResult,
    *,
    repo_root: Path,
    baseline: BaselineTestResult | None,
    timeout: int = _DEFAULT_HEAD_RUN_TIMEOUT,
    progress_callback: _ProgressCallback | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    wait: _ProcessWait = _default_process_wait,
    scope_source: ScopeSource | None = None,
) -> GateVerdict:
    """The shared verdict tail: run ``scope`` at head, diff vs. ``baseline``.

    Extracted (pre-merge finding, #572/#1979/#2283) so BOTH the
    injected-``ScopeSource`` tier (:func:`evaluate_pre_review_gate`, below —
    the census-derived auto-scope tier it used to also serve was retired by
    mission ``scopesource-gate-followup-01KY6S9P`` WP04, FR-001) AND the
    FR-004 explicit-override tier
    (``tasks_move_task._mt_pre_review_gate_with_override_scope``) drive the
    EXACT same warn/new-failure/unverified-baseline policy from ONE tested
    body — instead of the override tier hand-mirroring this tail as a
    divergence-prone copy (the pre-fix shape, which left its
    ``NEW_FAILURES``/block/force + ``UNVERIFIED_BASELINE`` branches with zero
    coverage).

    An empty ``scope`` still degrades to a ``no_coverage`` warn here, via
    :meth:`ScopeResult.describe_empty_reason` — the wording that fits
    :func:`evaluate_pre_review_gate`'s own auto-derived empty scope. A
    caller building a scope whose empty case needs DIFFERENT wording (e.g.
    the override tier's literal "override test scope is empty" — an
    explicit override list isn't a census exclusion, so
    ``describe_empty_reason()``'s catch-all/composite-dir phrasing would be
    misleading there) should check ``scope.is_empty`` itself and skip this
    function entirely for that branch, exactly as the override tier does.

    ``scope_source`` (T011, mission ``doctrine-controlled-transition-gates-01KY51Z7``
    WP03): when injected, the head run + parse route through the port
    (:func:`_evaluate_via_scope_source`) instead of the legacy hardcoded
    pytest/JUnit path — see that function's docstring for why its
    empty-scope handling differs. ``None`` (the default, C-002 KEPT LIVE) is
    the FR-004 explicit-override tier's own shape
    (``tasks_move_task._mt_pre_review_gate_with_override_scope``) — it never
    injects a ``scope_source``, by design, since an override IS the test
    scope.
    """
    if scope_source is None:
        if scope.is_empty:
            return GateVerdict(outcome=GateOutcome.NO_COVERAGE, scope=scope, reason=scope.describe_empty_reason())

        run_result = run_scoped_tests_at_head(
            scope.test_targets,
            repo_root=repo_root,
            timeout=timeout,
            progress_callback=progress_callback,
            monotonic=monotonic,
            wait=wait,
        )
        if run_result.state is HeadRunState.TIMED_OUT:
            return GateVerdict(
                outcome=GateOutcome.TIMED_OUT,
                scope=scope,
                reason=run_result.error,
                run_state=run_result.state,
            )
        if run_result.state is HeadRunState.CANCELLED:
            return GateVerdict(
                outcome=GateOutcome.CANCELLED,
                scope=scope,
                reason=run_result.error,
                run_state=run_result.state,
            )
        if not run_result.ran:
            return GateVerdict(
                outcome=GateOutcome.NO_COVERAGE,
                scope=scope,
                reason=f"scoped test run did not complete: {run_result.error}",
                run_state=run_result.state,
            )
        return _classify_current_failures(run_result.current_failures, scope=scope, baseline=baseline)

    return _evaluate_via_scope_source(
        scope,
        repo_root=repo_root,
        baseline=baseline,
        timeout=timeout,
        progress_callback=progress_callback,
        monotonic=monotonic,
        wait=wait,
        scope_source=scope_source,
    )


def _scope_result_from_source(scope_source: ScopeSource, changed_files: Sequence[str]) -> ScopeResult:
    """Build a :class:`ScopeResult` from the injected port's per-file scoping.

    A census-*narrowing* source (``GateCoverageScopeSource``, which satisfies the
    :class:`~specify_cli.review.scope_source.ScopeBreakdownSource` refinement)
    reconstructs the FULL breakdown — ``matched_shard_groups`` /
    ``matched_composite_dirs`` / ``empty_cone_composite_dirs`` /
    ``excluded_scope_files`` — so the inverted hook's transition metadata is
    byte-identical to the incumbent (now-retired) census tier (NFR-001).

    A non-narrowing source (``DeclaredCommandScopeSource`` or an arbitrary
    injected stub) has no shard groups by construction — the injected-port path
    only needs the flat union of ``file_to_scope`` targets, exactly as before.
    """
    if exposes_scope_breakdown(scope_source):
        return _scope_result_from_breakdown(scope_source, changed_files)
    targets: set[str] = set()
    for changed_file in changed_files:
        targets.update(scope_source.file_to_scope(changed_file))
    return ScopeResult(
        test_targets=tuple(sorted(targets)),
        matched_shard_groups=(),
        matched_composite_dirs=(),
        empty_cone_composite_dirs=(),
        excluded_scope_files=(),
    )


def _scope_result_from_breakdown(
    scope_source: ScopeBreakdownSource, changed_files: Sequence[str]
) -> ScopeResult:
    """Aggregate a narrowing source's per-file
    :class:`~specify_cli.review.scope_source.FileScopeBreakdown` contributions
    into a full :class:`ScopeResult`.

    Mirrors the retired census tier's own union/aggregation (recall >
    precision across focused groups; a file contributing no focused group
    lands in ``excluded_scope_files``) so the port-driven path reproduces the
    incumbent ``ScopeResult`` shape for the same changed set (NFR-001).
    """
    targets: set[str] = set()
    shard_groups: set[str] = set()
    composite_dirs: set[str] = set()
    empty_cone_dirs: set[str] = set()
    excluded_scope_files: list[str] = []
    for raw_file in changed_files:
        changed_file = to_posix(raw_file)
        breakdown = scope_source.scope_breakdown(changed_file)
        targets.update(breakdown.test_targets)
        shard_groups.update(breakdown.matched_shard_groups)
        composite_dirs.update(breakdown.matched_composite_dirs)
        empty_cone_dirs.update(breakdown.empty_cone_composite_dirs)
        if not breakdown.contributes_scope:
            excluded_scope_files.append(changed_file)
    return ScopeResult(
        test_targets=tuple(sorted(targets)),
        matched_shard_groups=tuple(sorted(shard_groups)),
        matched_composite_dirs=tuple(sorted(composite_dirs)),
        empty_cone_composite_dirs=tuple(sorted(empty_cone_dirs)),
        excluded_scope_files=tuple(sorted(set(excluded_scope_files))),
    )


def evaluate_pre_review_gate(
    changed_files: Sequence[str],
    *,
    repo_root: Path,
    baseline: BaselineTestResult | None,
    timeout: int = _DEFAULT_HEAD_RUN_TIMEOUT,
    progress_callback: _ProgressCallback | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    wait: _ProcessWait = _default_process_wait,
    scope_source: ScopeSource,
) -> GateVerdict:
    """Compose scope derivation + the shared head-run/verdict tail.

    Warn-shaped outcomes (``NO_COVERAGE`` / ``UNVERIFIED_BASELINE`` /
    ``SOURCE_MISMATCH``) are never escalated to a hard failure here — the
    warn-default/opt-in-block/``--force`` policy is layered on top of this
    verdict by the ``for_review`` hook, not this function's concern.

    ``scope_source`` (mission ``doctrine-controlled-transition-gates-01KY51Z7``
    WP03; required as of mission ``scopesource-gate-followup-01KY6S9P`` WP04,
    which retired the census-derived auto-scope tier this function used to
    fall back to when ``scope_source`` was omitted): scope/command/parse are
    sourced ENTIRELY from the injected port. The sole production caller
    (``gate_registry._spec_kitty_pre_review_handler``) always supplies a
    concrete, non-``None`` source resolved by activation.
    """
    scope = _scope_result_from_source(scope_source, changed_files)
    return evaluate_with_scope(
        scope,
        repo_root=repo_root,
        baseline=baseline,
        timeout=timeout,
        progress_callback=progress_callback,
        monotonic=monotonic,
        wait=wait,
        scope_source=scope_source,
    )

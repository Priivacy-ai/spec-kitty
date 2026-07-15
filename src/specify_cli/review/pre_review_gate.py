"""Auto-scoped pre-review regression gate: scope derivation + head-side runner + verdict.

Mission ``review-regression-gate-01KWX6DF`` WP01 (closes #572 + the per-WP
review-blind-spot facet of #1979; part of #2283). Today ``move-task --to
for_review`` (``cli/commands/agent/tasks_move_task.py``) runs no tests and
review is scoped to a WP's ``owned_files`` — a WP that breaks a *consumer*
outside its owned set reaches approval unnoticed. This module is the engine
half of the fix (the CLI hook + config/override wiring is WP02):

1. **Derive the affected test scope** (FR-002/FR-005/FR-006) from a WP's
   changed files, keyed on the dorny filter-group SHAPE parsed by
   ``tests/architectural/_gate_coverage.py`` (the live, single-source
   authority — never hand-declared here):

   - **per-shard groups** (``status``, ``cli``, ``merge``, ``review``, …) —
     their glob set already carries ``tests/**`` entries -> those globs ARE
     the affected test scope.
   - **composite groups** (``auth_audit_git``, ``lifecycle``,
     ``agent_surface``, ``closeout``, ``governance``, ``platform``) — their
     glob set is src-only -> the scope comes from the census
     ``_COMPOSITE_ROUTING`` cone_roots for the file's own worklist dir.
   - The catch-all groups (``core_misc``, ``e2e``, ``any_src``) are EXCLUDED
     regardless of shape — ``core_misc`` alone carries ~53 ``tests/**``
     globs (~17 min) and would defeat FR-005's bounded-cost goal.
   - An EMPTY affected scope is NEVER "verified clean" — always a
     ``no_coverage`` warn (SC-007), distinct from a green
     ``no_new_failures`` verdict.

2. **Run the derived scope at head** (subprocess) and parse its JUnit output
   with ``review/baseline.py``'s existing parser (``_parse_junit_xml``) —
   the shard-scoped invocation + this head-side run are net-new (C-001);
   ``baseline.py`` has neither today.

3. **Compute the new-failure verdict** as ``head_failures - base_failures``
   via ``review/baseline.py``'s existing ``diff_baseline`` (also reused
   unchanged). An uncomputable baseline degrades to a warn, never a hard
   block (FR-003).
"""
from __future__ import annotations

import contextlib
import fnmatch
import importlib
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
from types import ModuleType
from typing import cast

from specify_cli.paths import get_runtime_root
from specify_cli.review._interpreter import resolve_pytest_command
from specify_cli.review.baseline import (
    BaselineFailure,
    BaselineTestResult,
    _parse_junit_xml,
    diff_baseline,
)

# ---------------------------------------------------------------------------
# Catch-all exclusion (FR-002/FR-005)
# ---------------------------------------------------------------------------

# Dorny groups excluded from the review-time run regardless of shape (FR-002/
# FR-005) come from TWO signals, both consulted at call time (never a single
# fixed literal set) so a future whole-tree probe group doesn't silently slip
# through:
#
# 1. NAMED_CATCHALL_GROUPS — breadth that is a judgment call, not a structural
#    glob-shape property _gate_coverage.py exposes: core_misc alone carries
#    ~53 tests/** globs (~17 min); e2e's heavy full-CLI runs are excluded by
#    category. core_misc in particular DOES carry tests/** globs — it would
#    otherwise look "per-shard"-shaped — so it must be named, not inferred.
# 2. Any group whose glob set carries the literal ``src/**`` whole-tree probe
#    (``any_src``'s own glob) matches EVERY src file by construction — this is
#    a MECHANICAL signal, so it is derived per group map rather than named.
#    ci-windows.yml's ``windows_critical`` group is exactly this shape (it
#    globs plain ``src/**`` alongside ~20 specific windows-regression test
#    files) — aggregate_filter_groups() merges ci-windows.yml's groups into
#    the same namespace as ci-quality.yml's, so it must be excluded the same
#    way any_src is, or every src touch would unconditionally drag in those
#    ~20 unrelated files and mask an otherwise-empty (SC-007) scope.
NAMED_CATCHALL_GROUPS: frozenset[str] = frozenset({"core_misc", "e2e"})
_WHOLE_SRC_TREE_GLOB = "src/**"


def resolve_excluded_catchall_groups(filter_groups: Mapping[str, tuple[str, ...]]) -> frozenset[str]:
    """The full catch-all exclusion set for a given ``group -> globs`` map.

    = :data:`NAMED_CATCHALL_GROUPS` UNION every group whose glob set carries
    the literal ``src/**`` whole-tree probe (``any_src`` itself, plus any
    other group shaped the same way).
    """
    whole_tree_groups = {name for name, globs in filter_groups.items() if _WHOLE_SRC_TREE_GLOB in globs}
    return NAMED_CATCHALL_GROUPS | whole_tree_groups

_SRC_PACKAGE_PREFIX = "src/specify_cli/"
_TESTS_PREFIX = "tests/"
_GATE_COVERAGE_MODULE_NAME = "tests.architectural._gate_coverage"

# Mirrors _gate_coverage._CompositeRoute: (target_group, target_shard, cone_roots).
_CompositeRoute = tuple[str | None, str | None, tuple[str, ...]]
_EMPTY_COMPOSITE_ROUTE: _CompositeRoute = (None, None, ())

_LoadWorkflowModels = Callable[[], dict[str, object]]
_AggregateFilterGroups = Callable[[dict[str, object]], dict[str, tuple[str, ...]]]

_DEFAULT_HEAD_RUN_TIMEOUT = 300  # seconds; mirrors baseline.py's capture_baseline timeout.
_HEAD_RUN_HEARTBEAT_INTERVAL = 30.0
_HEAD_RUN_TERMINATE_GRACE = 5.0


class GateAuthoritiesUnavailable(RuntimeError):
    """The live CI-topology authorities module could not be loaded for a repo.

    Raised by :func:`_load_gate_coverage_module` when
    ``tests/architectural/_gate_coverage.py`` is missing, fails to import, or
    resolves to a module living outside the requested ``repo_root`` (a stale
    cross-repo ``sys.modules`` cache hit). Callers treat this as an
    "unverified scope" signal (folded into a ``no_coverage`` warn by
    :func:`derive_test_scope`'s caller), never as a hard failure — an
    inability to compute coverage must be surfaced, not silently swallowed
    or escalated to a crash.
    """


# ---------------------------------------------------------------------------
# Live-authority loading (FR-002/FR-006)
# ---------------------------------------------------------------------------


def _load_gate_coverage_module(repo_root: Path) -> ModuleType:
    """Import the live CI-topology model for ``repo_root``.

    ``tests/architectural/_gate_coverage.py`` is the single-source authority
    for both group shapes this module derives scope from:
    ``aggregate_filter_groups()`` (per-shard ``tests/**`` globs) and
    ``_COMPOSITE_ROUTING`` (composite cone_roots). It is test-tree code,
    imported lazily here (never at this module's own import time) so a
    consumer repo without a spec-kitty-shaped ``tests/`` tree degrades to
    :class:`GateAuthoritiesUnavailable` instead of breaking unrelated CLI
    imports.
    """
    resolved_root = repo_root.resolve()
    repo_str = str(resolved_root)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    try:
        module = importlib.import_module(_GATE_COVERAGE_MODULE_NAME)
    except ImportError as exc:
        raise GateAuthoritiesUnavailable(
            f"{_GATE_COVERAGE_MODULE_NAME} is not importable under {resolved_root}: {exc}",
        ) from exc
    module_file = getattr(module, "__file__", None)
    if module_file is None or resolved_root not in Path(module_file).resolve().parents:
        raise GateAuthoritiesUnavailable(
            f"{_GATE_COVERAGE_MODULE_NAME} resolved to {module_file!r}, outside "
            f"{resolved_root} — refusing a cross-repo authorities import.",
        )
    return module


def _default_filter_groups(repo_root: Path) -> dict[str, tuple[str, ...]]:
    """Live ``group -> globs`` map, straight from ``aggregate_filter_groups()``."""
    module = _load_gate_coverage_module(repo_root)
    load_workflow_models = cast("_LoadWorkflowModels", module.load_workflow_models)
    aggregate_filter_groups = cast("_AggregateFilterGroups", module.aggregate_filter_groups)
    return aggregate_filter_groups(load_workflow_models())


def _default_composite_routing(repo_root: Path) -> Mapping[str, _CompositeRoute]:
    """Live composite-dir -> ``(target_group, target_shard, cone_roots)`` routing plan.

    Reads ``_gate_coverage``'s own committed routing table directly (rather
    than mirroring a copy here) so this stays the single FR-006 authority.
    """
    module = _load_gate_coverage_module(repo_root)
    return cast("Mapping[str, _CompositeRoute]", module._COMPOSITE_ROUTING)


# ---------------------------------------------------------------------------
# Glob / path helpers
# ---------------------------------------------------------------------------


def _glob_matches_file(glob_pattern: str, file_path: str) -> bool:
    """True iff a dorny filter glob matches a specific changed-file path.

    Close enough to dorny/paths-filter's own semantics for our purposes: a
    ``<dir>/**`` glob matches the dir itself and everything under it; any
    other glob containing ``*`` falls back to shell-style matching;
    anything else is an exact-path match.
    """
    pattern = glob_pattern.replace("\\", "/")
    path = file_path.replace("\\", "/")
    if pattern.endswith("/**"):
        prefix = pattern[: -len("/**")]
        return path == prefix or path.startswith(f"{prefix}/")
    if "*" in pattern:
        return fnmatch.fnmatch(path, pattern)
    return path == pattern


def _glob_to_pytest_target(glob_pattern: str) -> str:
    """A ``tests/**`` dorny glob -> a runnable pytest path argument."""
    normalized = glob_pattern.replace("\\", "/")
    if normalized.endswith("/**"):
        return normalized[: -len("/**")]
    return normalized


def _src_dir_segment(file_path: str) -> str | None:
    """The direct ``src/specify_cli/<dir>`` child a file lives under, else ``None``.

    Same extraction rule as ``_gate_coverage._src_dir_of_glob`` — mirrored
    rather than imported, since it is applied to a concrete changed-file path
    rather than a glob. A top-level ``src/specify_cli/<file>.py`` has no
    owning worklist dir and returns ``None``.
    """
    if not file_path.startswith(_SRC_PACKAGE_PREFIX):
        return None
    segment = file_path[len(_SRC_PACKAGE_PREFIX) :].split("/", 1)[0]
    if not segment or segment.endswith(".py"):
        return None
    return segment


# ---------------------------------------------------------------------------
# Scope derivation (FR-002/FR-005/FR-006)
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


def derive_test_scope(
    changed_files: Sequence[str],
    *,
    repo_root: Path,
    filter_groups: Mapping[str, tuple[str, ...]] | None = None,
    composite_routing: Mapping[str, _CompositeRoute] | None = None,
) -> ScopeResult:
    """Derive the affected pytest targets for ``changed_files``.

    Reads BOTH live authorities from ``tests.architectural._gate_coverage``
    unless overridden — the ``filter_groups``/``composite_routing`` override
    seam exists for ``test_pre_review_scope_singlesource.py``'s mutation-bite
    proofs and offline unit tests, never for production callers.

    Recall > precision applies only within the focused (non-catch-all)
    groups: every matching focused group contributes its scope (no attempt
    to pick a single "best" group for an ambiguous file); this never
    re-admits the excluded catch-alls.
    """
    groups = filter_groups if filter_groups is not None else _default_filter_groups(repo_root)
    routing = composite_routing if composite_routing is not None else _default_composite_routing(repo_root)
    excluded_groups = resolve_excluded_catchall_groups(groups)

    test_targets: set[str] = set()
    matched_shard_groups: set[str] = set()
    matched_composite_dirs: set[str] = set()
    empty_cone_dirs: set[str] = set()
    excluded_scope_files: list[str] = []

    for raw_file in changed_files:
        changed_file = raw_file.replace("\\", "/")
        matched_group_names = {
            name for name, globs in groups.items() if any(_glob_matches_file(g, changed_file) for g in globs)
        }
        focused_group_names = matched_group_names - excluded_groups
        if not focused_group_names:
            excluded_scope_files.append(changed_file)
            continue

        for group_name in focused_group_names:
            test_globs = [g for g in groups[group_name] if g.startswith(_TESTS_PREFIX)]
            if test_globs:
                matched_shard_groups.add(group_name)
                test_targets.update(_glob_to_pytest_target(g) for g in test_globs)
                continue

            dir_name = _src_dir_segment(changed_file)
            if dir_name is None:
                continue
            _, _, cone_roots = routing.get(dir_name, _EMPTY_COMPOSITE_ROUTE)
            matched_composite_dirs.add(dir_name)
            if cone_roots:
                test_targets.update(cone_roots)
            else:
                empty_cone_dirs.add(dir_name)

    return ScopeResult(
        test_targets=tuple(sorted(test_targets)),
        matched_shard_groups=tuple(sorted(matched_shard_groups)),
        matched_composite_dirs=tuple(sorted(matched_composite_dirs)),
        empty_cone_composite_dirs=tuple(sorted(empty_cone_dirs)),
        excluded_scope_files=tuple(sorted(set(excluded_scope_files))),
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
        return process.communicate()


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

    env = dict(os.environ)
    env["PWHEADLESS"] = "1"  # never pop a browser window during an automated gate run

    with tempfile.TemporaryDirectory() as tmp_dir:
        junit_path = Path(tmp_dir) / "pre-review-junit.xml"
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
                error=f"scoped test run failed to launch: {exc}",
                state=HeadRunState.LAUNCH_FAILED,
            )

        if state is HeadRunState.TIMED_OUT:
            return HeadRunResult(
                ran=False,
                returncode=process.returncode,
                error=f"scoped test run timed out after {timeout}s; stderr tail: {stderr[-500:]}",
                state=state,
                stdout=stdout,
                stderr=stderr,
            )
        if state is HeadRunState.CANCELLED:
            return HeadRunResult(
                ran=False,
                returncode=process.returncode,
                error=f"scoped test run cancelled; stderr tail: {stderr[-500:]}",
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
                    f"stderr tail: {stderr[-500:]}"
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


def evaluate_with_scope(
    scope: ScopeResult,
    *,
    repo_root: Path,
    baseline: BaselineTestResult | None,
    timeout: int = _DEFAULT_HEAD_RUN_TIMEOUT,
    progress_callback: _ProgressCallback | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    wait: _ProcessWait = _default_process_wait,
) -> GateVerdict:
    """The shared verdict tail: run ``scope`` at head, diff vs. ``baseline``.

    Extracted (pre-merge finding, #572/#1979/#2283) so BOTH the
    census-derived auto-scope tier (:func:`evaluate_pre_review_gate`, below)
    AND the FR-004 explicit-override tier
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
    """
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

    if baseline is None or baseline.failed == -1:
        return GateVerdict(
            outcome=GateOutcome.UNVERIFIED_BASELINE,
            scope=scope,
            reason="baseline uncomputable — surfacing all current failures as unverified",
            new_failures=run_result.current_failures,
        )

    pre_existing, new_failures, _fixed = diff_baseline(baseline, list(run_result.current_failures))
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


def evaluate_pre_review_gate(
    changed_files: Sequence[str],
    *,
    repo_root: Path,
    baseline: BaselineTestResult | None,
    timeout: int = _DEFAULT_HEAD_RUN_TIMEOUT,
    filter_groups: Mapping[str, tuple[str, ...]] | None = None,
    composite_routing: Mapping[str, _CompositeRoute] | None = None,
    progress_callback: _ProgressCallback | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    wait: _ProcessWait = _default_process_wait,
) -> GateVerdict:
    """Compose scope derivation + the shared head-run/verdict tail.

    Warn-shaped outcomes (``NO_COVERAGE`` / ``UNVERIFIED_BASELINE``) are
    never escalated to a hard failure here — the warn-default/opt-in-block/
    ``--force`` policy is layered on top of this verdict by WP02's
    ``for_review`` hook, not this function's concern.
    """
    scope = derive_test_scope(
        changed_files,
        repo_root=repo_root,
        filter_groups=filter_groups,
        composite_routing=composite_routing,
    )
    return evaluate_with_scope(
        scope,
        repo_root=repo_root,
        baseline=baseline,
        timeout=timeout,
        progress_callback=progress_callback,
        monotonic=monotonic,
        wait=wait,
    )

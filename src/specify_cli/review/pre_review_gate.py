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

import fnmatch
import importlib
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import cast

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


@dataclass(frozen=True)
class HeadRunResult:
    """Outcome of invoking the derived test scope at head."""

    ran: bool
    current_failures: tuple[BaselineFailure, ...] = ()
    returncode: int | None = None
    error: str | None = None


def run_scoped_tests_at_head(
    test_targets: Sequence[str],
    *,
    repo_root: Path,
    timeout: int = _DEFAULT_HEAD_RUN_TIMEOUT,
) -> HeadRunResult:
    """Run ``test_targets`` at head and parse JUnit into ``current_failures``.

    The shard-scoped invocation itself is net-new (``baseline.py``'s
    ``capture_baseline`` runs one whole, un-scoped ``review.test_command``
    and has no head-side runner of its own) — but the JUnit parsing is
    ``baseline.py``'s existing ``_parse_junit_xml``, reused unchanged (C-001).
    """
    if not test_targets:
        return HeadRunResult(ran=False, error="empty test scope — nothing to run")

    env = dict(os.environ)
    env["PWHEADLESS"] = "1"  # never pop a browser window during an automated gate run

    with tempfile.TemporaryDirectory() as tmp_dir:
        junit_path = Path(tmp_dir) / "pre-review-junit.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            *test_targets,
            f"--junitxml={junit_path}",
            "-q",
        ]
        try:
            result = subprocess.run(
                command,
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return HeadRunResult(ran=False, error=f"scoped test run timed out after {timeout}s: {exc}")
        except OSError as exc:
            return HeadRunResult(ran=False, error=f"scoped test run failed to launch: {exc}")

        if not junit_path.exists():
            return HeadRunResult(
                ran=False,
                returncode=result.returncode,
                error=(
                    f"no JUnit XML produced by the scoped run (exit={result.returncode}); "
                    f"stderr tail: {result.stderr[-500:]}"
                ),
            )

        try:
            # Broad catch mirrors baseline.py's own handling around this exact parse
            # call: a malformed-XML runner bug degrades to a warn (error=...), never a crash.
            _total, _passed, _failed, _skipped, failures = _parse_junit_xml(junit_path)
        except Exception as exc:
            return HeadRunResult(
                ran=False,
                returncode=result.returncode,
                error=f"failed to parse scoped-run JUnit XML: {exc}",
            )

    return HeadRunResult(ran=True, current_failures=tuple(failures), returncode=result.returncode)


# ---------------------------------------------------------------------------
# Verdict (FR-001/FR-003)
# ---------------------------------------------------------------------------


class GateOutcome(StrEnum):
    """The verdict shapes a pre-review gate evaluation can produce."""

    NO_COVERAGE = "no_coverage"  # FR-001/SC-007: empty scope OR run didn't complete — warn, NEVER "clean"
    NO_NEW_FAILURES = "no_new_failures"  # non-empty run, no new failures vs. baseline
    NEW_FAILURES = "new_failures"  # non-empty run, >=1 new failure vs. baseline
    UNVERIFIED_BASELINE = "unverified_baseline"  # FR-003: baseline uncomputable -> warn


@dataclass(frozen=True)
class GateVerdict:
    """The end-to-end pre-review gate result: scope + head run + new-failure diff."""

    outcome: GateOutcome
    scope: ScopeResult
    reason: str | None = None
    new_failures: tuple[BaselineFailure, ...] = ()
    pre_existing_failures: tuple[BaselineFailure, ...] = ()


def evaluate_with_scope(
    scope: ScopeResult,
    *,
    repo_root: Path,
    baseline: BaselineTestResult | None,
    timeout: int = _DEFAULT_HEAD_RUN_TIMEOUT,
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

    run_result = run_scoped_tests_at_head(scope.test_targets, repo_root=repo_root, timeout=timeout)
    if not run_result.ran:
        return GateVerdict(
            outcome=GateOutcome.NO_COVERAGE,
            scope=scope,
            reason=f"scoped test run did not complete: {run_result.error}",
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
    return evaluate_with_scope(scope, repo_root=repo_root, baseline=baseline, timeout=timeout)

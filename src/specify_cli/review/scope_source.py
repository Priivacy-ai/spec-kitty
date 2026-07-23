"""``ScopeSource`` port + its two implementations (WP02, mission
``doctrine-controlled-transition-gates-01KY51Z7``, epic #2535 half A).

``ScopeSource`` is the injectable seam that lets the pre-review gate become
layout-agnostic: everything that varies with a repo's *shape* — how to run
its tests, how a changed file maps to a test target, how a completed run's
output is parsed into per-failure identities — lives behind this
``typing.Protocol``, mirroring ``OrgDoctrineSource``
(:mod:`specify_cli.doctrine.sources.protocol`): ``@runtime_checkable``, and
methods that never raise for environmental problems (surfaced via return
value instead).

**``changed_files`` is deliberately absent from the port** (FR-001). It is
the shared canonical merge-base+diff SSOT
(``core.vcs.git.merge_base_changed_files``, surfaced via
``tasks_move_task.py``), passed *into* the gate rather than re-derived per
implementation, so the two implementations below cannot diverge on "which
files changed". Do not "helpfully" add a ``changed_files`` method here — that
is the exact drift this port design forbids.

**Import-cycle guard.** WP03 makes ``pre_review_gate.py`` and ``baseline.py``
import ``ScopeSource`` back from this module — a two-way cycle if this
module imports them at module scope. ``BaselineFailure`` is therefore
referenced only under ``TYPE_CHECKING`` (annotations are lazy strings via
``from __future__ import annotations``, so this costs nothing at runtime and
never executes at import time); ``_parse_junit_xml``, ``_get_test_command``,
and ``GateAuthoritiesUnavailable`` are imported LAZILY inside the method
bodies that need them, never at module top. Those types stay in their
current home (``baseline.py`` / ``pre_review_gate.py``) — they are not
duplicated here.
"""
from __future__ import annotations

import fnmatch
import importlib
import shlex
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from kernel.paths import to_posix
from specify_cli.review._interpreter import resolve_pytest_command

if TYPE_CHECKING:
    from specify_cli.review.baseline import BaselineFailure

# ``DeclaredCommandScopeSource`` (the portable, layout-agnostic impl) and
# ``FileScopeBreakdown`` (the per-file breakdown dataclass) are not yet consumed
# cross-module in half A: the activation-resolved wiring that would select the
# portable source lands with #2873, and the breakdown is an internal detail of
# the census path. Both stay importable by their unit tests; they are re-added
# to ``__all__`` when a runtime caller wires them.
__all__ = [
    "GateCoverageScopeSource",
    "RawRunResult",
    "ScopeBreakdownSource",
    "ScopeSource",
]


@dataclass(frozen=True)
class RawRunResult:
    """The UNPARSED product of running :meth:`ScopeSource.test_command`.

    This is deliberately NOT ``pre_review_gate.HeadRunResult`` — that type is
    already-**parsed** (it carries ``current_failures`` and has no raw-output
    field), so feeding it to :meth:`ScopeSource.parse_results` would leave the
    portable implementation nothing to parse and it would collapse to
    ``NO_COVERAGE`` (the exact decorative-gate regression this mission
    kills). The engine builds a parsed result FROM ``parse_results(raw)``'s
    output, never the other way round.
    """

    returncode: int
    stdout: str
    stderr: str
    output_artifact_path: Path | None = None


@runtime_checkable
class ScopeSource(Protocol):
    """The repo-shape-varying concerns behind the pre-review gate.

    Covers ONLY what varies by repo shape. "Which files changed" is NOT on
    the port (FR-001) — see the module docstring.

    Port-wide invariant: implementations never raise for environmental
    problems — they surface them via return value (the ``OrgDoctrineSource``
    discipline). ``test_command() -> None`` is the no-config signal, not an
    exception.
    """

    def test_command(self) -> list[str] | None:
        """The runnable argv the gate executes at head.

        ``None`` means the repo declares no test command -> the gate is a
        visible ``NO_COVERAGE`` warn (FR-012), never a crash and never a
        silent green.
        """
        ...

    def file_to_scope(self, path: str) -> tuple[str, ...]:
        """Map ONE changed file to zero-or-more test targets.

        ``()`` means "contributes no scope" — not an error. Called once per
        element of the shared ``changed_files`` input (never invented here).
        """
        ...

    def parse_results(self, raw: RawRunResult) -> tuple[BaselineFailure, ...]:
        """Turn a completed (unparsed) head run into per-failure identities.

        Exit code alone is insufficient identity for a baseline diff — the
        parser MUST yield per-failure identities so the caller can classify
        pre-existing vs. new failures. A non-zero exit with unparseable
        output counts the whole run as failing (surfaced, never swallowed).
        """
        ...


@dataclass(frozen=True)
class FileScopeBreakdown:
    """One changed file's FULL census contribution, not just its flat targets.

    ``file_to_scope`` collapses this to ``test_targets`` alone; a
    census-narrowing source additionally exposes WHICH dorny shard groups /
    composite dirs a file landed in, so the inverted transition-gate hook can
    rebuild a :class:`~specify_cli.review.pre_review_gate.ScopeResult` whose
    ``matched_shard_groups`` / ``matched_composite_dirs`` /
    ``empty_cone_composite_dirs`` metadata is byte-identical to the incumbent
    ``derive_test_scope`` (NFR-001). ``contributes_scope`` is ``False`` when the
    file matched no *focused* (non-catch-all) group at all — the signal the
    engine folds into ``ScopeResult.excluded_scope_files``.
    """

    test_targets: tuple[str, ...] = ()
    matched_shard_groups: tuple[str, ...] = ()
    matched_composite_dirs: tuple[str, ...] = ()
    empty_cone_composite_dirs: tuple[str, ...] = ()
    contributes_scope: bool = True


@runtime_checkable
class ScopeBreakdownSource(Protocol):
    """Optional :class:`ScopeSource` refinement for census-*narrowing* impls.

    A source that satisfies this protocol (only :class:`GateCoverageScopeSource`
    in half A) both (a) exposes the per-file shard/composite breakdown via
    :meth:`scope_breakdown`, and (b) declares — by satisfying the protocol at
    all — that an EMPTY derived scope is a coverage gap (a ``no_coverage`` warn),
    exactly as the incumbent ``derive_test_scope`` + ``evaluate_with_scope``
    treated it. A plain :class:`ScopeSource` (``DeclaredCommandScopeSource`` or an
    arbitrary injected stub) does NOT narrow by file: its empty per-file scope is
    not a gap — it runs its whole declared suite — so it deliberately does not
    implement this refinement.
    """

    def scope_breakdown(self, path: str) -> FileScopeBreakdown:
        """Map ONE changed file to its full census breakdown (never raises)."""
        ...


# ---------------------------------------------------------------------------
# GateCoverageScopeSource — internal, behaviour-preserving (FR-002/FR-009)
# ---------------------------------------------------------------------------

# Mirrors pre_review_gate.py's own constants/helpers. Deliberately
# duplicated (not imported) — this module owns a PRIVATE copy of the census
# derivation so it never has to import pre_review_gate.py at module scope
# (that would recreate the exact cycle the guard above avoids). WP03 retires
# the pre_review_gate.py originals once that module is rewired onto this
# port; until then the two copies coexist (relocation, not redesign).
_SRC_PACKAGE_PREFIX = "src/specify_cli/"
_TESTS_PREFIX = "tests/"
_GATE_COVERAGE_MODULE_NAME = "tests.architectural._gate_coverage"

# Mirrors _gate_coverage._CompositeRoute: (target_group, target_shard, cone_roots).
_CompositeRoute = tuple[str | None, str | None, tuple[str, ...]]
_EMPTY_COMPOSITE_ROUTE: _CompositeRoute = (None, None, ())

_NAMED_CATCHALL_GROUPS: frozenset[str] = frozenset({"core_misc", "e2e"})
_WHOLE_SRC_TREE_GLOB = "src/**"

_JUNIT_ARTIFACT_FILENAME = "pre-review-junit.xml"

_LoadWorkflowModels = Callable[[], dict[str, object]]
_AggregateFilterGroups = Callable[[dict[str, object]], dict[str, tuple[str, ...]]]


def _resolve_excluded_catchall_groups(filter_groups: Mapping[str, tuple[str, ...]]) -> frozenset[str]:
    """Private copy of ``pre_review_gate.resolve_excluded_catchall_groups`` (FR-009)."""
    whole_tree_groups = {name for name, globs in filter_groups.items() if _WHOLE_SRC_TREE_GLOB in globs}
    return _NAMED_CATCHALL_GROUPS | whole_tree_groups


def _glob_matches_file(glob_pattern: str, file_path: str) -> bool:
    """Private copy of ``pre_review_gate._glob_matches_file`` (FR-009)."""
    pattern = to_posix(glob_pattern)
    path = to_posix(file_path)
    if pattern.endswith("/**"):
        prefix = pattern[: -len("/**")]
        return path == prefix or path.startswith(f"{prefix}/")
    if "*" in pattern:
        return fnmatch.fnmatch(path, pattern)
    return path == pattern


def _glob_to_pytest_target(glob_pattern: str) -> str:
    """Private copy of ``pre_review_gate._glob_to_pytest_target`` (FR-009)."""
    normalized = to_posix(glob_pattern)
    if normalized.endswith("/**"):
        return normalized[: -len("/**")]
    return normalized


def _src_dir_segment(file_path: str) -> str | None:
    """Private copy of ``pre_review_gate._src_dir_segment`` (FR-009)."""
    if not file_path.startswith(_SRC_PACKAGE_PREFIX):
        return None
    segment = file_path[len(_SRC_PACKAGE_PREFIX) :].split("/", 1)[0]
    if not segment or segment.endswith(".py"):
        return None
    return segment


def _is_spec_kitty_source_repo(repo_root: Path) -> bool:
    """Private internal filesystem probe (FR-009).

    MUST NOT gate impl selection — activation (WP09), not this probe,
    decides which ``ScopeSource`` runs. Used only to fill
    ``GateAuthoritiesUnavailable.is_consumer_repo`` with the same signal
    ``pre_review_gate.py`` uses today.
    """
    return (repo_root / "tests" / "architectural" / "_gate_coverage.py").is_file()


def _load_gate_coverage_module(repo_root: Path) -> ModuleType:
    """Import the live CI-topology model for ``repo_root`` (private, FR-009).

    A PRIVATE copy of the runtime ``_gate_coverage`` import: unreachable
    unless :class:`GateCoverageScopeSource` is selected by activation.
    ``GateAuthoritiesUnavailable`` is imported lazily from its current home
    (``pre_review_gate.py``) to avoid a module-top import cycle.
    """
    from specify_cli.review.pre_review_gate import GateAuthoritiesUnavailable

    resolved_root = repo_root.resolve()
    repo_str = str(resolved_root)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    is_consumer_repo = not _is_spec_kitty_source_repo(resolved_root)
    try:
        module = importlib.import_module(_GATE_COVERAGE_MODULE_NAME)
    except ImportError as exc:
        raise GateAuthoritiesUnavailable(
            f"{_GATE_COVERAGE_MODULE_NAME} is not importable under {resolved_root}: {exc}",
            is_consumer_repo=is_consumer_repo,
        ) from exc
    module_file = getattr(module, "__file__", None)
    if module_file is None or resolved_root not in Path(module_file).resolve().parents:
        raise GateAuthoritiesUnavailable(
            f"{_GATE_COVERAGE_MODULE_NAME} resolved to {module_file!r}, outside "
            f"{resolved_root} — refusing a cross-repo authorities import.",
            is_consumer_repo=is_consumer_repo,
        )
    return module


def _default_filter_groups(repo_root: Path) -> dict[str, tuple[str, ...]]:
    """Live ``group -> globs`` map, straight from ``aggregate_filter_groups()``."""
    module = _load_gate_coverage_module(repo_root)
    load_workflow_models = cast("_LoadWorkflowModels", module.load_workflow_models)
    aggregate_filter_groups = cast("_AggregateFilterGroups", module.aggregate_filter_groups)
    return aggregate_filter_groups(load_workflow_models())


def _default_composite_routing(repo_root: Path) -> Mapping[str, _CompositeRoute]:
    """Live composite-dir -> ``(target_group, target_shard, cone_roots)`` routing plan."""
    module = _load_gate_coverage_module(repo_root)
    return cast("Mapping[str, _CompositeRoute]", module._COMPOSITE_ROUTING)


@dataclass
class GateCoverageScopeSource:
    """Reproduces today's exact Spec-Kitty pre-review behaviour (FR-002).

    Zero behaviour change (NFR-001): the ``_gate_coverage`` census-narrowing
    scope derivation, the pytest ``--junitxml``/``-q`` injection, and the
    JUnit parse are all encapsulated *inside* this implementation.

    ``filter_groups_override``/``composite_routing_override`` exist ONLY for
    hermetic, offline unit tests (mirroring ``derive_test_scope``'s own
    test-only override seam) — production callers must leave them ``None``
    so the live ``tests.architectural._gate_coverage`` authorities apply.
    """

    repo_root: Path
    filter_groups_override: Mapping[str, tuple[str, ...]] | None = None
    composite_routing_override: Mapping[str, _CompositeRoute] | None = None
    _junit_dir: Path | None = field(default=None, init=False, repr=False)

    @cached_property
    def _filter_groups(self) -> Mapping[str, tuple[str, ...]]:
        if self.filter_groups_override is not None:
            return self.filter_groups_override
        return _default_filter_groups(self.repo_root)

    @cached_property
    def _composite_routing(self) -> Mapping[str, _CompositeRoute]:
        if self.composite_routing_override is not None:
            return self.composite_routing_override
        return _default_composite_routing(self.repo_root)

    @property
    def filter_groups(self) -> Mapping[str, tuple[str, ...]]:
        """Public read-only view of the resolved live ``group -> globs`` map.

        The census authority ``derive_test_scope`` needs when it runs without
        an explicit override — exposed so callers read it through the port
        instead of reaching into the private ``_filter_groups`` cache.
        """
        return self._filter_groups

    @property
    def composite_routing(self) -> Mapping[str, _CompositeRoute]:
        """Public read-only view of the resolved composite-dir routing plan.

        Companion to :attr:`filter_groups` — the second live authority
        ``derive_test_scope`` consumes, exposed as a public accessor.
        """
        return self._composite_routing

    def test_command(self) -> list[str] | None:
        """The incumbent pytest argv, injecting ``--junitxml``/``-q`` here.

        Moved off the shared runner (``pre_review_gate.py``'s
        ``run_scoped_tests_at_head``) into this implementation — the port's
        sole authority for "what command proves the change" (FR-011).
        """
        junit_path = self._junit_output_path()
        # Explicit annotation (not a bare return): this repo's mypy config skips
        # ``specify_cli.*`` imports when a narrow single-file path is checked
        # (`[[tool.mypy.overrides]] module = ["specify_cli.*"]` ->
        # `follow_imports = "skip"`), which otherwise resolves
        # ``resolve_pytest_command``'s return as ``Any`` and trips
        # ``--warn-return-any`` under ``mypy --strict scope_source.py`` alone.
        command: list[str] = resolve_pytest_command([f"--junitxml={junit_path}", "-q"], repo_root=self.repo_root)
        return command

    def file_to_scope(self, path: str) -> tuple[str, ...]:
        """The flat ``test_targets`` projection of :meth:`scope_breakdown`.

        Behaviour-preserving: identical to the pre-inversion narrowing — the
        breakdown's shard/composite bookkeeping is simply discarded here for
        callers that only need the runnable targets.
        """
        return self.scope_breakdown(path).test_targets

    def scope_breakdown(self, path: str) -> FileScopeBreakdown:
        """Today's ``_gate_coverage`` census narrowing for ONE changed file, WITH breakdown.

        Mirrors ``derive_test_scope``'s own per-file classification so the
        inverted hook can rebuild the incumbent ``ScopeResult`` metadata
        byte-for-byte (NFR-001): a focused per-shard group contributes its own
        ``tests/**`` globs (recorded in ``matched_shard_groups``); a focused
        composite group contributes its dir's ``_COMPOSITE_ROUTING`` cone_roots
        (recorded in ``matched_composite_dirs``, with an empty cone recorded in
        ``empty_cone_composite_dirs``). A file matching only catch-all groups (or
        no group) contributes nothing and reports ``contributes_scope=False``.
        """
        changed_file = to_posix(path)
        excluded_groups = _resolve_excluded_catchall_groups(self._filter_groups)
        focused_group_names = {
            name
            for name, globs in self._filter_groups.items()
            if any(_glob_matches_file(g, changed_file) for g in globs)
        } - excluded_groups
        if not focused_group_names:
            return FileScopeBreakdown(contributes_scope=False)

        targets: set[str] = set()
        shard_groups: set[str] = set()
        composite_dirs: set[str] = set()
        empty_cone_dirs: set[str] = set()
        for group_name in focused_group_names:
            test_globs = [g for g in self._filter_groups[group_name] if g.startswith(_TESTS_PREFIX)]
            if test_globs:
                shard_groups.add(group_name)
                targets.update(_glob_to_pytest_target(g) for g in test_globs)
                continue
            dir_name = _src_dir_segment(changed_file)
            if dir_name is None:
                continue
            _, _, cone_roots = self._composite_routing.get(dir_name, _EMPTY_COMPOSITE_ROUTE)
            composite_dirs.add(dir_name)
            if cone_roots:
                targets.update(cone_roots)
            else:
                empty_cone_dirs.add(dir_name)
        return FileScopeBreakdown(
            test_targets=tuple(sorted(targets)),
            matched_shard_groups=tuple(sorted(shard_groups)),
            matched_composite_dirs=tuple(sorted(composite_dirs)),
            empty_cone_composite_dirs=tuple(sorted(empty_cone_dirs)),
            contributes_scope=True,
        )

    def parse_results(self, raw: RawRunResult) -> tuple[BaselineFailure, ...]:
        """Parse JUnit XML from ``raw.output_artifact_path`` (``_parse_junit_xml`` semantics)."""
        from specify_cli.review.baseline import BaselineFailure, _parse_junit_xml

        artifact = raw.output_artifact_path
        if artifact is None or not artifact.exists():
            return (
                BaselineFailure(
                    test="<gate-coverage-junit>",
                    error="no JUnit XML artifact produced by the scoped run",
                    file="unknown",
                ),
            )
        _total, _passed, _failed, _skipped, failures = _parse_junit_xml(artifact)
        return tuple(failures)

    def _junit_output_path(self) -> Path:
        """A stable-for-this-instance JUnit output path, allocated lazily."""
        if self._junit_dir is None:
            self._junit_dir = Path(tempfile.mkdtemp(prefix="spec-kitty-gate-coverage-"))
        return self._junit_dir / _JUNIT_ARTIFACT_FILENAME


# ---------------------------------------------------------------------------
# DeclaredCommandScopeSource — portable, baseline-relative (FR-003/FR-010)
# ---------------------------------------------------------------------------

_FAILURE_LINE_PREFIX = "FAIL "
_UNPARSEABLE_FAILURE_TEST_ID = "<declared-command>"
_FAILURE_MESSAGE_MAX_CHARS = 200


def _parse_declared_command_failure_lines(text: str) -> tuple[BaselineFailure, ...]:
    """Extract per-failure identities from a ``FAIL <test>[: <message>]``-shaped stream.

    A small, non-pytest, non-JUnit output convention: any line starting with
    ``FAIL `` is one failing test identity. This is the "genuinely
    non-pytest-shaped" parser NFR-004 requires — it never assumes pytest or
    JUnit.
    """
    from specify_cli.review.baseline import BaselineFailure

    failures: list[BaselineFailure] = []
    for line in text.splitlines():
        if not line.startswith(_FAILURE_LINE_PREFIX):
            continue
        remainder = line[len(_FAILURE_LINE_PREFIX) :]
        test_name, _, message = remainder.partition(":")
        error = (message.strip() or "failed")[:_FAILURE_MESSAGE_MAX_CHARS]
        failures.append(BaselineFailure(test=test_name.strip(), error=error, file="unknown"))
    return tuple(failures)


def _whole_run_failure(raw: RawRunResult) -> BaselineFailure:
    """A single synthetic identity representing "the whole run failed, unparseably".

    Exit code alone is insufficient identity for a baseline diff, but a
    non-zero exit with no parseable per-test failures must still be
    surfaced as failing — never silently swallowed into ``()``.
    """
    from specify_cli.review.baseline import BaselineFailure

    tail_source = raw.stderr or raw.stdout
    tail_lines = tail_source.strip().splitlines()
    summary = tail_lines[-1][:_FAILURE_MESSAGE_MAX_CHARS] if tail_lines else f"exit code {raw.returncode}"
    return BaselineFailure(test=_UNPARSEABLE_FAILURE_TEST_ID, error=summary, file="unknown")


@dataclass(frozen=True)
class DeclaredCommandScopeSource:
    """Gates a non-pytest / non-``src/specify_cli/`` repo by its own declared command.

    ``file_to_scope`` always returns ``()`` — no per-file narrowing; the
    declared command runs the whole suite (layout-agnostic). ``parse_results``
    yields per-failure identities so a failing suite is a blocking-capable
    ``NEW_FAILURES`` verdict, never a false ``ANY_FAILURES``-shaped collapse
    (forbidden by NFR-004): a ``returncode != 0`` alone is never treated as
    the verdict — pre-existing baseline failures must not block.
    """

    repo_root: Path

    def test_command(self) -> list[str] | None:
        """``shlex.split(review.test_command)``, or ``None`` when unset (FR-012).

        Reads the same config surface ``baseline._get_test_command`` reads
        (FR-011) — no new config key is invented.
        """
        from specify_cli.review.baseline import _get_test_command

        command_template, _output_format = _get_test_command(self.repo_root)
        if not command_template:
            return None
        return shlex.split(command_template)

    def file_to_scope(self, _path: str) -> tuple[str, ...]:
        """Always ``()`` — no per-file narrowing (deliberately not #2330).

        The argument is unused by design: this implementation never narrows
        by file (the declared command runs the whole suite), so the
        parameter is intentionally underscore-prefixed rather than dropped —
        positional calls through the ``ScopeSource`` port are unaffected.
        """
        return ()

    def parse_results(self, raw: RawRunResult) -> tuple[BaselineFailure, ...]:
        """Parse the declared command's own output into per-failure identities.

        Prefers a JUnit artifact when the declared command happens to
        produce one (``test_output_format: junit_xml`` consumers); otherwise
        parses ``stdout``/``stderr`` via the ``FAIL <test>`` convention. A
        non-zero exit with nothing parseable still counts as failing
        (surfaced via :func:`_whole_run_failure`, never swallowed).
        """
        if raw.output_artifact_path is not None and raw.output_artifact_path.exists():
            from specify_cli.review.baseline import _parse_junit_xml

            _total, _passed, _failed, _skipped, failures = _parse_junit_xml(raw.output_artifact_path)
            return tuple(failures)

        text_failures = _parse_declared_command_failure_lines(raw.stdout) + _parse_declared_command_failure_lines(
            raw.stderr
        )
        if text_failures:
            return text_failures
        if raw.returncode != 0:
            return (_whole_run_failure(raw),)
        return ()

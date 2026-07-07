"""Static model of the CI test-selection matrix (Issue #2034 / #1933).

CI selects tests **by marker** (``fast`` / ``integration`` / ``git_repo`` /
``slow`` / ``architectural`` / ``windows_ci`` / ``quarantine`` / ``timing`` /
``distribution``) combined with **path** arguments, sharded across many jobs.
The authoring taxonomy (``pytest.ini`` documents ``unit`` as "the category
default for module-scoped tests"; ``contract`` for contract tests) diverges
from that *selection* taxonomy: **no gate selects ``-m unit`` or
``-m contract``**, and several test directories are touched by no gate at all.
The result is that a large fraction of the suite is selected by **zero** gates —
"untested-but-green": those tests never run in CI, so a regression in them is
invisible (no red), only a silent coverage hole.

This module is the *enforcement substrate* for that gap. It does not re-tier or
re-shard CI (that is the maintainer's migration, against this guardrail). It
statically:

1. Parses every ``pytest`` invocation across the five workflow files that run
   the suite (``ci-quality`` / ``ci-windows`` / ``drift-detector`` /
   ``release`` / ``ui-e2e``), expanding the ``integration-tests-core-misc``
   shard matrix.
2. Models each invocation as a :class:`Gate` = ``(paths, ignores, marker_expr)``.
3. Evaluates every collected test against every gate, using pytest's own
   marker-expression evaluator, to count how many gates select it.

A test selected by **0** gates is an *orphan* (coverage hole); a test selected
by **>=2** gates is a *duplicate* (intentional overlap is allowed — reported,
not enforced).

The companion ratchet (``test_gate_coverage.py`` +
``_gate_coverage_baseline.json``) freezes today's orphan surface as a visible
worklist and fails only on a **new** ungated file — so no *new* test can leak
into zero gates by construction, without blocking on the existing backlog.

Run directly to refresh the baseline or check drift::

    uv run python -m tests.architectural._gate_coverage --update-baseline
    uv run python -m tests.architectural._gate_coverage --check
"""

from __future__ import annotations

import ast
import configparser
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Sequence

# pytest's own marker-expression evaluator — guarantees identical semantics to a
# real ``-m`` selection. This is a *private* pytest API and ``pytest`` is floored
# (``>=9.0.3``), NOT upper-pinned, so a breaking move of this import fails loudly
# at import time rather than silently mis-modelling selection. The import contract
# is pinned by ``test_pytest_marker_expression_import_contract`` in the companion
# test module; ``uv.lock`` pins the exact resolved version for reproducible runs.
from _pytest.mark.expression import Expression

# One collected test: its nodeid, repo-relative path, and applied marker names.
TestRecord = dict[str, Any]

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# The five workflows that actually run the pytest suite (the others lint, build,
# or sync and select no tests). ``ui-e2e.yml`` is the scoped Playwright
# dashboard e2e gate (issue #1008): a standalone, drift-detector-shaped
# workflow (own trigger, single job, no dorny filter, no quality-gate
# aggregator) whose ``pytest tests/ui/`` invocation must be MODELED here so
# ``discover_pytest_workflows`` (FR-008 fail-closed) stays equal to this
# allowlist and the ``tests/ui/`` e2e carrier is a covered — not orphan —
# surface (so the ``e2e`` marker keeps its ROUTED-BY-PATH home).
WORKFLOW_FILES: tuple[str, ...] = (
    "ci-quality.yml",
    "ci-windows.yml",
    "drift-detector.yml",
    "release.yml",
    "ui-e2e.yml",
)

BASELINE_PATH = Path(__file__).with_name("_gate_coverage_baseline.json")
_COLLECT_PLUGIN = "tests.architectural._gate_collect_plugin"
_TESTS_ROOT = "tests"

# A healthy collect-only run with the marker-dump plugin clears every item, so
# pytest reports NO_TESTS_COLLECTED (5). A collection-time error in a test file
# (bad import / syntax) instead increments testsfailed and yields a failure code.
# Trusting the partial dump in that case would silently DROP the broken file's
# tests — exactly the new tests the ratchet must scrutinize — so any other exit
# code must fail loudly (Issue #2034 Codex review: P2).
_COLLECT_OK_CODES: frozenset[int] = frozenset(
    {int(pytest.ExitCode.OK), int(pytest.ExitCode.NO_TESTS_COLLECTED)},
)

# Reported (not enforced) selection-overlap threshold: >=2 gates = duplicate.
_DUPLICATE_GATE_THRESHOLD = 2

# Quoted ``-m 'a and b'`` OR unquoted single-token ``-m windows_ci``.
_MARKER_Q_RE = re.compile(r"-m\s+(?P<q>['\"])(?P<expr>.*?)(?P=q)")
_MARKER_U_RE = re.compile(r"-m\s+(?P<expr>[A-Za-z_]\w*)")
_IGNORE_RE = re.compile(r"--ignore=(\S+)")
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_]\w*=(?:'[^']*'|\"[^\"]*\"|\S+)\s+")
_PYTEST_HEAD_RE = re.compile(r"^pytest\b")
_GHA_EXPR_RE = re.compile(r"\$\{\{(.*?)\}\}")
_SEGMENT_SPLIT_RE = re.compile(r"&&|;|\|\|?|\bthen\b|\bdo\b")

# Runner prefixes that may precede the literal ``pytest`` command token. After
# stripping leading env-assignments and these, a real pytest *command* segment
# begins with ``pytest`` — so ``pipx inject ... pytest`` and ``git grep ...
# pytest`` (where pytest is an argument, not the command) are correctly skipped.
_PREFIX_RE = re.compile(
    r"^(?:"
    r"uv\s+run(?:\s+--\S+(?:\s+'[^']*'|\s+\"[^\"]*\"|\s+\S+)?)*"  # uv run [--with '...']
    r"|python\d?(?:\s+-m)?"
    r"|\"?\$?\{?[A-Za-z_]\w*\}?\"?\s+-m"  # "$VENV_PYTHON" -m / $VAR -m
    r"|pipx\s+run"
    r"|-m"
    r")\s+",
)


@dataclass
class Gate:
    """One CI test-selection: positional ``paths``, ``--ignore`` globs, ``-m`` expr."""

    workflow: str
    job: str
    shard: str | None
    paths: list[str] = field(default_factory=list)
    ignores: list[str] = field(default_factory=list)
    marker_expr: str | None = None

    def label(self) -> str:
        suffix = f" ({self.shard})" if self.shard else ""
        return f"{self.workflow}::{self.job}{suffix}"


# ---------------------------------------------------------------------------
# Workflow parsing
# ---------------------------------------------------------------------------


def _iter_run_steps(
    data: dict[str, Any],
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Return ``(job_name, job, step)`` for every step carrying a ``run`` script."""
    steps: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for job_name, job in (data.get("jobs") or {}).items():
        for step in job.get("steps") or []:
            if isinstance(step, dict) and "run" in step:
                steps.append((job_name, job, step))
    return steps


def _matrix_includes(job: dict[str, Any]) -> list[dict[str, Any]] | None:
    matrix = (job.get("strategy") or {}).get("matrix") or {}
    include = matrix.get("include")
    return include if isinstance(include, list) else None


def substitute_matrix(text: str, mvars: dict[str, Any]) -> str:
    """Expand ``${{ matrix.X }}`` (blanking other ``${{ ... }}`` expressions)."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key.startswith("matrix."):
            return str(mvars.get(key.split(".", 1)[1], ""))
        return ""

    return _GHA_EXPR_RE.sub(repl, text)


def join_continuations(script: str) -> list[str]:
    """Join backslash-continued shell lines into single logical lines."""
    out: list[str] = []
    buf = ""
    for raw in script.splitlines():
        line = raw.rstrip()
        if line.endswith("\\"):
            buf += line[:-1] + " "
        else:
            out.append(buf + line)
            buf = ""
    if buf:
        out.append(buf)
    return out


def strip_to_command(segment: str) -> str:
    """Strip env-assignments and runner prefixes; stop at the ``pytest`` token."""
    s = segment.strip()
    while True:
        m = _ENV_ASSIGN_RE.match(s)
        if not m:
            break
        s = s[m.end() :]
    while not _PYTEST_HEAD_RE.match(s):
        m = _PREFIX_RE.match(s)
        if not m:
            break
        s = s[m.end() :]
    return s


def _extract_marker(tail: str) -> str | None:
    mq = _MARKER_Q_RE.search(tail)
    if mq:
        return mq.group("expr").strip()
    mu = _MARKER_U_RE.search(tail)
    return mu.group("expr").strip() if mu else None


def _extract_paths(tail: str) -> list[str]:
    cleaned = _MARKER_U_RE.sub(" ", _MARKER_Q_RE.sub(" ", tail))
    paths: list[str] = []
    for token in cleaned.split():
        candidate = token.strip("'\"").replace("\\", "/")
        if candidate == _TESTS_ROOT or candidate.startswith(f"{_TESTS_ROOT}/"):
            paths.append(candidate)
    return paths


def parse_pytest_invocation(
    logical_line: str,
) -> tuple[list[str], list[str], str | None] | None:
    """Return ``(paths, ignores, marker)`` for a real pytest command, else None."""
    if logical_line.lstrip().startswith("#"):
        return None
    for segment in _SEGMENT_SPLIT_RE.split(logical_line):
        command = strip_to_command(segment)
        if not command.startswith("pytest"):
            continue
        tail = command[len("pytest") :]
        return _extract_paths(tail), _IGNORE_RE.findall(tail), _extract_marker(tail)
    return None


def parse_workflow(path: Path) -> list[Gate]:
    """Parse one workflow file into the gates it defines."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    gates: list[Gate] = []
    for job_name, job, step in _iter_run_steps(data):
        includes = _matrix_includes(job)
        variants: Sequence[dict[str, Any] | None] = includes or (None,)
        for mvars in variants:
            script = substitute_matrix(step["run"], mvars or {})
            for logical in join_continuations(script):
                parsed = parse_pytest_invocation(logical)
                if parsed is None:
                    continue
                paths, ignores, marker = parsed
                gates.append(
                    Gate(
                        workflow=path.name,
                        job=job_name,
                        shard=(mvars or {}).get("shard") if mvars else None,
                        paths=paths,
                        ignores=ignores,
                        marker_expr=marker,
                    ),
                )
    return gates


def load_gates() -> list[Gate]:
    """Parse all five suite-running workflows into the full gate list."""
    gates: list[Gate] = []
    for name in WORKFLOW_FILES:
        gates.extend(parse_workflow(WORKFLOWS_DIR / name))
    return gates


# ---------------------------------------------------------------------------
# Workflow relation model (mission ci-suite-map-bind WP01 — additive substrate
# for the FR-001/FR-003/FR-005/FR-008/FR-010..FR-013 invariant suites).
# Pure parsing only: the invariants over these relations live in the consumer
# test modules, never here.
# ---------------------------------------------------------------------------

_PYTEST_INI_PATH = REPO_ROOT / "pytest.ini"
_DORNY_FILTER_ACTION = "dorny/paths-filter"

# ``needs.<job>.result`` reads inside run scripts (FR-003a / FR-003d).
_NEEDS_RESULT_RE = re.compile(r"needs\.([A-Za-z0-9_-]+)\.result")
# ``needs.<job>.outputs.<group>`` references inside job-level ``if:`` gates
# (FR-003b / FR-010 / FR-011 job→group gating map).
_FILTER_OUTPUT_RE = re.compile(r"needs\.[A-Za-z0-9_-]+\.outputs\.([A-Za-z0-9_]+)")
# ``--cov=<target>`` emitters inside run scripts (FR-005).
_COV_TARGET_RE = re.compile(r"--cov=([^\s\\'\"]+)")
# The diff-coverage job's ``critical_paths=( ... )`` shell array (FR-005).
_CRITICAL_PATHS_RE = re.compile(r"critical_paths=\((.*?)\)", re.DOTALL)
_SHELL_QUOTED_RE = re.compile(r"'([^']*)'|\"([^\"]*)\"")
# Leading identifier of one ``markers =`` registry line in pytest.ini.
_MARKER_NAME_RE = re.compile(r"[A-Za-z_]\w*")


def positive_marker_tokens(marker_expr: str | None) -> frozenset[str]:
    """Marker names *positively* referenced by a ``-m`` expression (FR-001 (i)).

    Negation-aware: ``not windows_ci`` does NOT reference ``windows_ci``
    positively (the spec's pinned edge case — every Linux gate negates it),
    while ``not not fast`` does reference ``fast``. A name is positive iff it
    occurs under an even number of ``not`` operators.

    The expression is first compiled with pytest's own
    :class:`~_pytest.mark.expression.Expression` (identical grammar/semantics
    to a real ``-m`` selection — an invalid expression fails loudly there,
    and a breaking move of the private API fails at import time, see the
    module-top import note). The sign walk itself uses the stdlib ``ast``
    parse of the same text: for the identifier-and-boolean-operator
    expressions the workflows use, pytest's expression grammar is a strict
    subset of Python's.
    """
    if not marker_expr:
        return frozenset()
    Expression.compile(marker_expr)  # loud fail on an invalid expression
    try:
        tree = ast.parse(marker_expr, mode="eval")
    except SyntaxError as exc:  # pragma: no cover — Expression accepts a superset
        raise RuntimeError(
            f"marker expression {marker_expr!r} compiles under pytest's grammar "
            "but not under stdlib ast — a gate started using a marker name that "
            "is not a Python identifier; extend positive_marker_tokens' walker.",
        ) from exc
    positive: set[str] = set()
    _walk_marker_ast(tree.body, negated=False, positive=positive)
    return frozenset(positive)


def _walk_marker_ast(node: ast.expr, *, negated: bool, positive: set[str]) -> None:
    """Recursive sign-tracking walk backing :func:`positive_marker_tokens`."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        _walk_marker_ast(node.operand, negated=not negated, positive=positive)
    elif isinstance(node, ast.BoolOp):
        for value in node.values:
            _walk_marker_ast(value, negated=negated, positive=positive)
    elif isinstance(node, ast.Name):
        if not negated:
            positive.add(node.id)
    else:
        raise RuntimeError(
            f"unsupported marker-expression node {ast.dump(node)} — a gate "
            "started using pytest kwarg selection (mark(arg=...)); extend "
            "positive_marker_tokens before trusting its output.",
        )


def routed_marker_names(gates: Sequence[Gate]) -> frozenset[str]:
    """Union of positively-referenced marker names across ``gates`` (FR-001 (i)).

    This is the live ROUTED-BY-MARKER set the marker-completeness invariant
    classifies against.
    """
    routed: set[str] = set()
    for gate in gates:
        routed |= positive_marker_tokens(gate.marker_expr)
    return frozenset(routed)


@dataclass(frozen=True)
class WorkflowModel:
    """Parsed relation surfaces of one workflow file (WP01 substrate).

    Every field is a *parsed source relation* (Adjudicated Decision 8: the
    dorny filter block and the job ``if:`` gates are the only two path-topology
    authorities; consumers assert against these, never against hand-maintained
    copies).

    - ``job_needs``: job → declared ``needs:`` list (FR-003a/d).
    - ``needs_result_reads``: job → job names read via ``needs.<job>.result``
      in that job's run scripts (FR-003a). The quality-gate aggregator's
      result-loop membership (FR-003d) is ``needs_result_reads["quality-gate"]``.
    - ``job_gating_groups``: job → dorny filter outputs referenced in the
      job-level ``if:`` expression (FR-003b; FR-011's job→group gating map).
    - ``filter_groups``: dorny filter group → glob list (FR-003c / FR-010).
    - ``cov_targets``: job → ``--cov=`` targets emitted in run scripts (FR-005).
    - ``diff_cover_critical_paths``: the diff-coverage job's shell
      ``critical_paths`` array entries, in declaration order (FR-005).
    - ``pull_request_types`` / ``pull_request_paths`` / ``push_paths``: outer
      ``on:`` trigger types and paths lists (FR-013 / FR-012 two-layer reads).
    """

    path: Path
    job_needs: dict[str, tuple[str, ...]]
    needs_result_reads: dict[str, frozenset[str]]
    job_gating_groups: dict[str, frozenset[str]]
    filter_groups: dict[str, tuple[str, ...]]
    cov_targets: dict[str, frozenset[str]]
    diff_cover_critical_paths: tuple[str, ...]
    pull_request_types: tuple[str, ...]
    pull_request_paths: tuple[str, ...]
    push_paths: tuple[str, ...]


def _job_needs_tuple(job: dict[str, Any]) -> tuple[str, ...]:
    """A job's declared ``needs:`` as a tuple (GitHub allows str or list)."""
    needs = job.get("needs")
    if needs is None:
        return ()
    if isinstance(needs, str):
        return (needs,)
    return tuple(str(entry) for entry in needs)


def _job_run_text(job: dict[str, Any]) -> str:
    """All raw ``run:`` script text of a job.

    Un-substituted: ``${{ }}`` expressions are kept, because the relation
    reads (``needs.<job>.result``, ...) live inside them.
    """
    return "\n".join(
        str(step["run"])
        for step in job.get("steps") or []
        if isinstance(step, dict) and "run" in step
    )


def _parse_filter_groups(jobs: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Dorny paths-filter group → glob tuple.

    Read from any ``dorny/paths-filter`` step's inline ``filters:`` YAML
    (FR-003c / FR-010 source authority).
    """
    groups: dict[str, tuple[str, ...]] = {}
    for job in jobs.values():
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            if not str(step.get("uses", "")).startswith(_DORNY_FILTER_ACTION):
                continue
            filters_raw = (step.get("with") or {}).get("filters")
            if not isinstance(filters_raw, str):
                continue
            parsed = yaml.safe_load(filters_raw) or {}
            for name, globs in parsed.items():
                groups[str(name)] = tuple(str(g) for g in globs or [])
    return groups


def _diff_cover_critical_paths(run_text: str) -> tuple[str, ...]:
    """Quoted entries of every ``critical_paths=( ... )`` shell array.

    Declaration order preserved, de-duplicated (FR-005).
    """
    entries: list[str] = []
    for block in _CRITICAL_PATHS_RE.findall(run_text):
        for single, double in _SHELL_QUOTED_RE.findall(block):
            entry = single or double
            if entry and entry not in entries:
                entries.append(entry)
    return tuple(entries)


def _on_section(data: dict[Any, Any]) -> dict[str, Any]:
    """The workflow's ``on:`` mapping (``{}`` for shorthand ``on: push``).

    Typed ``dict[Any, Any]`` because the key is genuinely non-str in the
    common case: YAML 1.1 parses the bare ``on`` key as boolean ``True``.
    """
    section = data.get("on", data.get(True))
    return section if isinstance(section, dict) else {}


def _trigger_tuple(on_section: dict[str, Any], event: str, key: str) -> tuple[str, ...]:
    """``on.<event>.<key>`` as a string tuple; ``()`` when absent."""
    event_section = on_section.get(event)
    if not isinstance(event_section, dict):
        return ()
    return tuple(str(value) for value in event_section.get(key) or [])


def load_workflow_model(path: Path) -> WorkflowModel:
    """Parse one workflow file into its :class:`WorkflowModel` relations."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs: dict[str, Any] = data.get("jobs") or {}
    run_texts = {name: _job_run_text(job) for name, job in jobs.items()}
    on_section = _on_section(data)
    return WorkflowModel(
        path=path,
        job_needs={name: _job_needs_tuple(job) for name, job in jobs.items()},
        needs_result_reads={
            name: frozenset(_NEEDS_RESULT_RE.findall(text))
            for name, text in run_texts.items()
        },
        job_gating_groups={
            name: frozenset(_FILTER_OUTPUT_RE.findall(str(job.get("if") or "")))
            for name, job in jobs.items()
        },
        filter_groups=_parse_filter_groups(jobs),
        cov_targets={
            name: frozenset(_COV_TARGET_RE.findall(text))
            for name, text in run_texts.items()
        },
        diff_cover_critical_paths=_diff_cover_critical_paths(
            "\n".join(run_texts.values()),
        ),
        pull_request_types=_trigger_tuple(on_section, "pull_request", "types"),
        pull_request_paths=_trigger_tuple(on_section, "pull_request", "paths"),
        push_paths=_trigger_tuple(on_section, "push", "paths"),
    )


def discover_pytest_workflows(workflows_dir: Path | None = None) -> frozenset[str]:
    """Workflow file names under ``workflows_dir`` that invoke pytest (FR-008).

    Content probe with the *same* detection semantics as the gate model
    (:func:`parse_workflow`), so the probe and :data:`WORKFLOW_FILES` cannot
    diverge in what "runs the suite" means. The consumer invariant asserts
    this set equals the allowlist, failing closed when a fifth suite-running
    workflow appears without entering the model.
    """
    directory = workflows_dir or WORKFLOWS_DIR
    candidates = sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml"))
    return frozenset(path.name for path in candidates if parse_workflow(path))


def registered_markers(pytest_ini: Path | None = None) -> tuple[str, ...]:
    """Marker names registered in pytest.ini's ``markers =`` block.

    ``pytest.ini`` is the single marker-registry authority (C-006, guarded by
    ``test_marker_registry_single_source.py``) — this READS it, adding no
    second surface. pytest's own ini handling is line-based (each non-empty
    block line registers one marker, its name the leading identifier before
    the ``:`` description), mirrored here without importing pytest's config
    machinery.
    """
    path = pytest_ini or _PYTEST_INI_PATH
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for line in parser.get("pytest", "markers", fallback="").splitlines():
        match = _MARKER_NAME_RE.match(line.strip())
        if match:
            names.append(match.group())
    return tuple(names)


# ---------------------------------------------------------------------------
# Selection model
# ---------------------------------------------------------------------------


def _is_file_entry(entry: str) -> bool:
    return entry.endswith(".py") or ".py::" in entry


def path_matches(relpath: str, nodeid: str, entry: str) -> bool:
    entry = entry.replace("\\", "/")
    if "::" in entry:
        return nodeid == entry or nodeid.startswith(entry)
    if _is_file_entry(entry):
        return relpath == entry
    prefix = entry if entry.endswith("/") else entry + "/"
    return relpath.startswith(prefix)


class CompiledGate:
    """A :class:`Gate` with its marker expression pre-compiled for evaluation."""

    def __init__(self, gate: Gate) -> None:
        self.gate = gate
        # A gate whose positional paths could not be parsed (e.g. ci-windows.yml
        # builds its test list dynamically via ``git grep``) falls back to the
        # whole tree. That fallback is coverage-SAFE only when a marker expression
        # narrows it: ci-windows runs ``-m windows_ci``, so it claims coverage of
        # exactly the windows-only tests, not the whole suite. A whole-tree gate
        # with NO marker would over-claim — guarded by
        # ``test_windows_gate_models_windows_ci_marker``.
        self.paths = gate.paths or [_TESTS_ROOT]
        self.expr = Expression.compile(gate.marker_expr) if gate.marker_expr else None

    def selects(self, relpath: str, nodeid: str, markers: set[str]) -> bool:
        if not any(path_matches(relpath, nodeid, p) for p in self.paths):
            return False
        if any(path_matches(relpath, nodeid, ig) for ig in self.gate.ignores):
            return False
        if self.expr is None:
            return True
        # pytest's matcher protocol is callable(name, /, **kw) -> bool; a plain
        # membership test is structurally compatible (cast silences the Protocol).
        matcher = cast("Any", lambda name: name in markers)
        return bool(self.expr.evaluate(matcher))


@dataclass
class CoverageReport:
    total: int
    orphan_nodeids: list[str]
    orphan_files: list[str]
    duplicate_nodeids: list[str]

    @property
    def orphan_count(self) -> int:
        return len(self.orphan_nodeids)


def analyze(gates: list[Gate], universe: list[TestRecord]) -> CoverageReport:
    """Count gate selections per test; collect orphans (0) and duplicates (>=2)."""
    compiled = [CompiledGate(g) for g in gates]
    orphan_nodeids: list[str] = []
    orphan_files: set[str] = set()
    duplicate_nodeids: list[str] = []
    for test in universe:
        relpath, nodeid = test["relpath"], test["nodeid"]
        markers = set(test["markers"])
        hits = sum(1 for cg in compiled if cg.selects(relpath, nodeid, markers))
        if hits == 0:
            orphan_nodeids.append(nodeid)
            orphan_files.add(relpath)
        elif hits >= _DUPLICATE_GATE_THRESHOLD:
            duplicate_nodeids.append(nodeid)
    return CoverageReport(
        total=len(universe),
        orphan_nodeids=sorted(orphan_nodeids),
        orphan_files=sorted(orphan_files),
        duplicate_nodeids=sorted(duplicate_nodeids),
    )


# ---------------------------------------------------------------------------
# Collection (subprocess --collect-only with the marker-dumping plugin)
# ---------------------------------------------------------------------------


def collect_universe(repo_root: Path | None = None) -> list[TestRecord]:
    """Collect every test with its marker set via a one-pass ``--collect-only``.

    Runs pytest in a subprocess with an isolated ``HOME`` (WP04 home isolation)
    and the :data:`_COLLECT_PLUGIN` plugin, which dumps
    ``{nodeid, relpath, markers}`` for each item and suppresses execution.
    """
    repo = repo_root or REPO_ROOT
    with tempfile.TemporaryDirectory() as tmp:
        dump = Path(tmp) / "universe.json"
        env = dict(os.environ)
        env.update(
            HOME=tempfile.mkdtemp(prefix="sk-gatecov-home-"),
            SK_GATE_DUMP=str(dump),
            SK_GATE_REPO=str(repo),
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-p",
                "no:cacheprovider",
                "-p",
                _COLLECT_PLUGIN,
                "-o",
                "addopts=",
                _TESTS_ROOT,
            ],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        if result.returncode not in _COLLECT_OK_CODES or not dump.exists():
            raise RuntimeError(
                "gate-coverage collection did not complete cleanly — refusing to "
                "trust a partial/empty test universe. A collection-time import or "
                "syntax error in a test file would otherwise be silently dropped, "
                "letting the orphan ratchet pass against an incomplete suite.\n"
                f"pytest exit={result.returncode} "
                f"(expected one of {sorted(_COLLECT_OK_CODES)}); "
                f"dump_present={dump.exists()}\n"
                f"--- stdout (tail) ---\n{result.stdout[-2000:]}\n"
                f"--- stderr (tail) ---\n{result.stderr[-2000:]}",
            )
        universe: list[TestRecord] = json.loads(dump.read_text(encoding="utf-8"))
        return universe


# ---------------------------------------------------------------------------
# CI-topology census + architectural-completeness relations
# (mission ci-topology-shrink-01KWQAVX WP01 — additive substrate for the
# NFR-002/NFR-003/NFR-006 invariant suites authored in WP02/WP03. PURE
# parsing/derivation only: the invariants over these relations live in the
# consumer test modules, never here. C-001 additive; NFR-007 — no existing
# surface's behavior is changed.)
# ---------------------------------------------------------------------------

# Single-literal census path (Sonar S1192): the committed construction-derived
# worklist authority WP02's SC-001 test iterates.
CENSUS_PATH = Path(__file__).with_name("ci_topology_census.json")

# Committed LOC floor for worklist membership (NFR-006). This is the plan-time
# constant; it lives in the census artifact and is NEVER inlined into a test —
# the SC-001 test reads it from the census so the metric measures coverage, not
# the implementer's constant.
T_LOC = 500

_SRC_PACKAGE_PREFIX = "src/specify_cli/"
_WHOLE_DIR_SUFFIX = "/**"
# The catch-all group (``src/**``) is src-backed but maps no *specific* dir: a
# touch matching only it still trips ``unmatched`` (data-model: "Src-backed
# groups (minus any_src)"), so it never removes a dir from the worklist.
_ANY_SRC_GROUP = "any_src"
# Marker name whose positive presence identifies an architectural-suite gate.
_ARCH_MARKER = "architectural"
# Gate-tier prefixes for the same-tier uniqueness relation (NFR-003).
_FAST_TIER_PREFIX = "fast-tests"
_INTEGRATION_TIER_PREFIX = "integration-tests"

# NFR-001 wallclock baseline (live CI run 28705381819, research §2.2). Probe
# measurements, not tree-derivable — committed so the SC-003/NFR-001 ceiling is
# anchored to a cited run rather than re-measured per invocation.
_TIMINGS_BASELINE: dict[str, float] = {
    "fast_core_misc_min": 17.0,
    "arch_shard_min": 12.3,
    "critical_path_min": 29.4,
    "next_lane_min": 13.6,
    "source_run_id": 28705381819,
}

_WORKLIST_RULE = (
    "D in worklist iff D is a direct child directory of src/specify_cli/ AND "
    "sum(LOC of *.py under D) >= t_loc AND no src-backed dorny filter group "
    "(excluding any_src) globs src/specify_cli/<D>/."
)

# Frozen pre-mission mapped baseline (NFR-006; review cycle 1). The FR-001
# worklist is the set of hot dirs the mission is chartered to *shrink to zero*
# by mapping them into src-backed dorny groups. Deriving the worklist against
# the LIVE ``mapped_src_dirs`` would make the mission's own success empty the
# worklist (worklist would shrink to nothing the moment WP03 globs the dirs),
# making WP02's routing / non-empty / freshness assertions mutually
# unsatisfiable. So membership subtracts this *committed snapshot* of the dirs
# already mapped before the mission began — identical to the census
# ``mapped_dirs`` field, disjoint from the 32-dir worklist. It is frozen: it
# does NOT re-read the live model (nor the census JSON it validates), so
# post-WP03 mapping leaves it at these 23 dirs, keeping the worklist stable at
# 32. Teeth are preserved and strengthened — a hand-trim of the census still
# reds, a dir crossing the LOC floor changes membership, and a *new* hot dir
# (>= t_loc, not in this baseline) grows the live derivation beyond the
# committed census and reds.
_PRE_MISSION_MAPPED_SRC_DIRS: frozenset[str] = frozenset(
    {
        "acceptance",
        "agent_utils",
        "charter_runtime",
        "cli",
        "coordination",
        "core",
        "dashboard",
        "delivery",
        "doctrine_synthesizer",
        "event_journal",
        "lanes",
        "merge",
        "missions",
        "post_merge",
        "release",
        "review",
        "runtime",
        "saas",
        "state",
        "status",
        "sync",
        "tool_surface",
        "upgrade",
    },
)

# One committed composite-routing plan entry: (target_group, target_shard,
# cone_roots). ``target_shard`` is the existing integration shard family the dir
# already lands in (research §1.4A/§3), the stable anchor SC-001 checks.
_CompositeRoute = tuple[str | None, str | None, tuple[str, ...]]
_EMPTY_ROUTING: _CompositeRoute = (None, None, ())

# Committed composite-routing plan (FR-001 / FR-010, research §3): the named
# group + focused integration shard family each worklist dir must map to, plus
# its test cone roots. This is the *design overlay* joined onto the tree-derived
# ``{dir, loc}`` membership — tree membership + LOC are re-derived live
# (:func:`live_derived_worklist`); this table is the committed plan authority
# SC-001 (WP03) asserts the live workflow conforms to, not a derived fact.
_COMPOSITE_ROUTING: dict[str, _CompositeRoute] = {
    # auth_audit_git -> existing ``auth-audit-git`` integration shard.
    "auth": ("auth_audit_git", "auth-audit-git", ("tests/auth",)),
    "audit": (
        "auth_audit_git", "auth-audit-git",
        ("tests/audit", "tests/specify_cli/audit"),
    ),
    "git": (
        "auth_audit_git", "auth-audit-git",
        ("tests/git", "tests/git_ops", "tests/specify_cli/git"),
    ),
    # lifecycle -> ``specify-cli-heavy`` (heavy marker adds ``and not slow``).
    "migration": (
        "lifecycle", "specify-cli-heavy",
        ("tests/migration", "tests/specify_cli/migration"),
    ),
    "invocation": (
        "lifecycle", "specify-cli-heavy",
        ("tests/invocation", "tests/specify_cli/invocation"),
    ),
    "compat": ("lifecycle", "specify-cli-heavy", ("tests/specify_cli/compat",)),
    "template": ("lifecycle", "specify-cli-heavy", ("tests/test_template",)),
    # agent_surface -> ``specify-cli-rest``.
    "orchestrator_api": (
        "agent_surface", "specify-cli-rest", ("tests/specify_cli/orchestrator_api",),
    ),
    "tracker": ("agent_surface", "specify-cli-rest", ("tests/tracker",)),
    "dossier": (
        "agent_surface", "specify-cli-rest",
        ("tests/dossier", "tests/specify_cli/dossier"),
    ),
    "bulk_edit": ("agent_surface", "specify-cli-rest", ("tests/specify_cli/bulk_edit",)),
    "skills": ("agent_surface", "specify-cli-rest", ("tests/specify_cli/skills",)),
    # closeout -> ``misc``.
    "retrospective": (
        "closeout", "misc",
        (
            "tests/retrospective",
            "tests/specify_cli/retrospect",
            "tests/specify_cli/retrospective",
        ),
    ),
    "readiness": (
        "closeout", "misc", ("tests/readiness", "tests/specify_cli/readiness"),
    ),
    "decisions": ("closeout", "misc", ("tests/specify_cli/decisions",)),
    "doc_analysis": ("closeout", "misc", ()),
    "widen": ("closeout", "misc", ("tests/specify_cli/widen",)),
    # governance -> ``misc``.
    "doctrine": ("governance", "misc", ("tests/specify_cli/doctrine",)),
    "policy": ("governance", "misc", ("tests/policy",)),
    "ownership": ("governance", "misc", ("tests/specify_cli/ownership",)),
    "validators": ("governance", "misc", ()),
    "calibration": ("governance", "misc", ("tests/calibration",)),
    "context": ("governance", "misc", ("tests/context", "tests/specify_cli/context")),
    # platform -> ``specify-cli-rest``.
    "workspace": ("platform", "specify-cli-rest", ("tests/specify_cli/workspace",)),
    "session_presence": (
        "platform", "specify-cli-rest", ("tests/specify_cli/session_presence",),
    ),
    "mission_v1": ("platform", "specify-cli-rest", ("tests/specify_cli/mission_v1",)),
    "mission_loader": ("platform", "specify-cli-rest", ("tests/unit/mission_loader",)),
    "events": ("platform", "specify-cli-rest", ("tests/specify_cli/events",)),
    "paths": ("platform", "specify-cli-rest", ("tests/paths",)),
    "saas_client": ("platform", "specify-cli-rest", ("tests/specify_cli/saas_client",)),
    "task_utils": ("platform", "specify-cli-rest", ()),
    "intake": ("platform", "specify-cli-rest", ()),
}


def load_workflow_models() -> dict[str, WorkflowModel]:
    """Parse all five suite-running workflows into ``name -> WorkflowModel``."""
    return {
        name: load_workflow_model(WORKFLOWS_DIR / name) for name in WORKFLOW_FILES
    }


def _group_is_src_backed(globs: Sequence[str]) -> bool:
    """A filter group is src-backed iff >=1 glob targets ``src/`` (data-model)."""
    return any(str(g).startswith("src/") for g in globs)


def aggregate_filter_groups(
    models: dict[str, WorkflowModel],
) -> dict[str, tuple[str, ...]]:
    """Union of every workflow's dorny filter groups: ``group -> sorted globs``."""
    merged: dict[str, set[str]] = {}
    for model in models.values():
        for name, globs in model.filter_groups.items():
            merged.setdefault(name, set()).update(globs)
    return {name: tuple(sorted(globs)) for name, globs in merged.items()}


def _src_dir_of_glob(glob: str) -> str | None:
    """First ``src/specify_cli/<dir>`` segment a glob targets, else ``None``.

    ``src/**`` (the ``any_src`` catch-all), non-package globs, and top-level
    ``src/specify_cli/<file>.py`` globs return ``None`` — they map no *specific*
    package dir.
    """
    normalized = glob.replace("\\", "/")
    if not normalized.startswith(_SRC_PACKAGE_PREFIX):
        return None
    segment = normalized[len(_SRC_PACKAGE_PREFIX) :].split("/", 1)[0].split("*", 1)[0]
    if not segment or segment.endswith(".py"):
        return None
    return segment


def mapped_src_dirs(models: dict[str, WorkflowModel]) -> frozenset[str]:
    """``src/specify_cli`` dirs claimed by >=1 src-backed named group != any_src.

    A dir here does NOT fall to ``unmatched->run_all`` on a confined touch
    (research §1.2 mapping oracle); the FR-001 worklist is exactly the
    complement (``>= t_loc`` LOC, unmapped).
    """
    mapped: set[str] = set()
    for name, globs in aggregate_filter_groups(models).items():
        if name == _ANY_SRC_GROUP or not _group_is_src_backed(globs):
            continue
        for glob in globs:
            dir_name = _src_dir_of_glob(glob)
            if dir_name is not None:
                mapped.add(dir_name)
    return frozenset(mapped)


def _newline_count(path: Path) -> int:
    """``wc -l`` semantics: the number of newline bytes in a file."""
    return path.read_bytes().count(b"\n")


def src_package_loc(repo_root: Path = REPO_ROOT) -> dict[str, int]:
    """Direct-child dir of ``src/specify_cli/`` -> recursive ``*.py`` line count.

    Mirrors the research §1.1 shell census (``find <d> -name '*.py' | xargs
    wc -l``): the count is the total number of newline characters across every
    ``*.py`` file under the dir, so a construction-derived worklist matches a
    hand-run census exactly.
    """
    package_dir = repo_root / "src" / "specify_cli"
    loc_by_dir: dict[str, int] = {}
    for child in sorted(package_dir.iterdir()):
        if not child.is_dir():
            continue
        loc_by_dir[child.name] = sum(_newline_count(py) for py in child.rglob("*.py"))
    return loc_by_dir


def live_derived_worklist(
    t_loc: int = T_LOC,
    repo_root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    """Re-derive the FR-001 worklist from the LIVE tree (NFR-006 freshness guard).

    Pure and side-effect-free: reads only the source tree, never writes. A dir
    qualifies iff it is a direct child of ``src/specify_cli/``, its recursive
    ``*.py`` LOC ``>= t_loc``, and it is NOT in the frozen pre-mission mapped
    baseline :data:`_PRE_MISSION_MAPPED_SRC_DIRS` — the committed
    :data:`_WORKLIST_RULE`. The subtraction is against the *frozen* baseline,
    not the live ``mapped_src_dirs``, so the mission's own success (WP03 mapping
    the worklist dirs) does not empty the worklist: the derivation stays at the
    32 hot-but-unmapped-at-mission-start dirs (review cycle 1 fix). Each
    qualifying dir is annotated with its committed :data:`_COMPOSITE_ROUTING`
    plan (group / focused shard / cone roots); tree membership + LOC are the
    *derived* facts, the annotation is the committed plan overlay (an unrouted
    qualifying dir carries ``None`` group/shard).

    WP02's ``test_ci_topology_worklist.py`` asserts census/live agreement on
    membership + routing via :func:`worklist_routing_index` — so a stale or
    hand-trimmed census still reds in CI (NFR-006). Exact per-dir ``loc`` is NOT
    emitted (issue #2416): it was a noisy freshness proxy that red unrelated PRs on
    any line-count churn, while every anti-tamper tooth (hand-trim, floor-crossing,
    new hot dir) is a *membership* change the routing index already captures.
    ``loc`` is still read internally to gate membership on the floor. The drop is
    applied here at the single shared derivation, so the ``--verify-census`` CLI
    (which consumes this function) is LOC-insensitive by construction too. Entries
    are sorted by ``dir`` name (LOC-independent) for a stable, diff-friendly order.
    """
    worklist: list[dict[str, Any]] = []
    for dir_name, loc in src_package_loc(repo_root).items():
        if loc < t_loc or dir_name in _PRE_MISSION_MAPPED_SRC_DIRS:
            continue
        group, shard, cones = _COMPOSITE_ROUTING.get(dir_name, _EMPTY_ROUTING)
        worklist.append(
            {
                "dir": dir_name,
                "cone_roots": list(cones),
                "target_group": group,
                "target_shard": shard,
            },
        )
    worklist.sort(key=lambda entry: str(entry["dir"]))
    return worklist


def worklist_routing_index(
    entries: Sequence[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Dir-keyed routing index for the freshness guard (order/LOC-insensitive, #2416).

    Only membership (the dir keys) and the committed routing plan (cone roots /
    target group / target shard) participate, so a pure line-count change or a LOC
    rank-swap between two members does not red the freshness gate. Exact LOC and list
    order are deliberately excluded — every anti-tamper tooth is a membership or
    routing change, which this index still captures.
    """
    return {
        str(entry["dir"]): {
            "cone_roots": list(entry.get("cone_roots", [])),
            "target_group": entry.get("target_group"),
            "target_shard": entry.get("target_shard"),
        }
        for entry in entries
    }


# --- Differential arch-completeness matrix (NFR-002) -----------------------


def _gate_is_arch(gate: Gate) -> bool:
    """True iff the gate positively selects the ``architectural`` marker family."""
    return _ARCH_MARKER in positive_marker_tokens(gate.marker_expr)


def _job_gating_index(models: dict[str, WorkflowModel]) -> dict[str, frozenset[str]]:
    """Merged ``job -> filter groups referenced in its ``if:`` across workflows."""
    gating: dict[str, frozenset[str]] = {}
    for model in models.values():
        gating.update(model.job_gating_groups)
    return gating


def group_less_suite_jobs(
    gates: Sequence[Gate],
    models: dict[str, WorkflowModel],
) -> frozenset[str]:
    """Suite-running jobs with NO dorny filter-group ``if:`` gate (always-on).

    Such a job (``lint``, ``slow-tests``, ``unit-contract-residual`` today; the
    future always-on ``arch-adversarial``) references no filter output, so it is
    legitimately absent from ``JOB_GROUPS`` / ``src_backed_groups`` and does not
    perturb the FR-010/FR-011 relations (research §4.2). Recognizing it lets the
    differential matrix credit an always-on arch pole that carries no filter
    gate.
    """
    gating = _job_gating_index(models)
    return frozenset(gate.job for gate in gates if not gating.get(gate.job))


def always_on_arch_present(
    gates: Sequence[Gate],
    models: dict[str, WorkflowModel],
) -> bool:
    """True iff an always-on (group-less) job runs the architectural suite.

    When present, the arch suite fires on every PR regardless of which src dir
    changed, so every dir is arch-selected by construction (NFR-002 target
    state). Today no group-less job runs arch -> ``False`` -> 13 arch-blind dirs.
    """
    group_less = group_less_suite_jobs(gates, models)
    return any(_gate_is_arch(gate) and gate.job in group_less for gate in gates)


def arch_trigger_groups(
    gates: Sequence[Gate],
    models: dict[str, WorkflowModel],
) -> frozenset[str]:
    """Filter groups whose touch fires the (group-gated) architectural suite.

    Union of the ``if:`` filter outputs of every group-gated arch-running job
    (today ``integration-tests-core-misc`` -> ``{acceptance, core_misc,
    execution_context}``). A dir whole-dir covered by one of these is
    arch-covered even without an always-on pole.
    """
    group_less = group_less_suite_jobs(gates, models)
    gating = _job_gating_index(models)
    triggers: set[str] = set()
    for gate in gates:
        if _gate_is_arch(gate) and gate.job not in group_less:
            triggers |= set(gating.get(gate.job, frozenset()))
    return frozenset(triggers)


def _whole_dir_glob(dir_name: str) -> str:
    """The dorny glob that covers the whole of ``src/specify_cli/<dir_name>``."""
    return f"{_SRC_PACKAGE_PREFIX}{dir_name}{_WHOLE_DIR_SUFFIX}"


def _arch_covered_src_dirs(
    gates: Sequence[Gate],
    models: dict[str, WorkflowModel],
) -> frozenset[str]:
    """Dirs whole-dir covered by an arch-trigger group (every touch fires arch).

    Only a whole-dir glob (``src/specify_cli/<D>/**``) counts: a deeper glob
    like ``execution_context``'s ``src/specify_cli/cli/commands/agent/**`` leaves
    a confined ``cli`` touch arch-blind, so ``cli`` is NOT arch-covered.
    """
    triggers = arch_trigger_groups(gates, models)
    groups = aggregate_filter_groups(models)
    covered: set[str] = set()
    for group in triggers:
        for glob in groups.get(group, ()):
            dir_name = _src_dir_of_glob(glob)
            if dir_name is not None and _whole_dir_glob(dir_name) == glob:
                covered.add(dir_name)
    return frozenset(covered)


def arch_selected_for_dir(
    dir_name: str,
    *,
    mapped: frozenset[str],
    arch_covered: frozenset[str],
    always_on_arch: bool,
) -> bool:
    """Pure predicate: does a touch confined to ``dir_name`` run the arch suite?

    ``True`` iff (a) an always-on arch job exists (fires unconditionally), or
    (b) the dir is unmapped (a confined touch trips ``unmatched->run_all``,
    which runs everything incl. arch), or (c) the dir is whole-dir covered by an
    arch-trigger filter group. ``False`` (arch-blind) only for a mapped dir no
    arch-trigger group covers (Mode B) — the un-blind target.
    """
    if always_on_arch:
        return True
    if dir_name not in mapped:
        return True
    return dir_name in arch_covered


def differential_arch_matrix(
    gates: Sequence[Gate] | None = None,
    models: dict[str, WorkflowModel] | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, bool]:
    """``src/specify_cli/*`` dir -> arch-selected bool (NFR-002 differential matrix).

    The mechanized proof that the architectural + adversarial guards execute on
    100% of src dirs. Today 13 dirs are arch-blind (the pre-WP03 red baseline);
    WP03's always-on arch job flips every dir to ``True`` by construction, and a
    regression re-adding a filter-group gate to that job reds this relation.
    """
    resolved_models = models if models is not None else load_workflow_models()
    resolved_gates = list(gates) if gates is not None else load_gates()
    mapped = mapped_src_dirs(resolved_models)
    arch_covered = _arch_covered_src_dirs(resolved_gates, resolved_models)
    always_on = always_on_arch_present(resolved_gates, resolved_models)
    return {
        dir_name: arch_selected_for_dir(
            dir_name,
            mapped=mapped,
            arch_covered=arch_covered,
            always_on_arch=always_on,
        )
        for dir_name in src_package_loc(repo_root)
    }


def arch_blind_src_dirs(
    gates: Sequence[Gate] | None = None,
    models: dict[str, WorkflowModel] | None = None,
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    """Sorted ``src/specify_cli/*`` dirs the arch suite never fires on (Mode B)."""
    matrix = differential_arch_matrix(gates, models, repo_root)
    return tuple(sorted(d for d, selected in matrix.items() if not selected))


# --- Same-tier shard-uniqueness relation (NFR-003) -------------------------


def _gate_tier(gate: Gate) -> str | None:
    """Tier of a gate for same-tier uniqueness: ``fast`` / ``integration`` / None."""
    if gate.job.startswith(_FAST_TIER_PREFIX):
        return "fast"
    if gate.job.startswith(_INTEGRATION_TIER_PREFIX):
        return "integration"
    return None


def shard_counts_for_test(
    test: TestRecord,
    tiered_gates: Sequence[tuple[CompiledGate, str]],
) -> dict[str, int]:
    """Count fast-tier / integration-tier shards that select one test (NFR-003).

    ``tiered_gates`` is a pre-built ``[(CompiledGate, tier), ...]``. Same-tier
    uniqueness means each count should be ``<= 1``; a test selected by two fast
    shards (or two integration shards) is a same-tier double-run.
    """
    relpath, nodeid, markers = test["relpath"], test["nodeid"], set(test["markers"])
    fast = integration = 0
    for compiled, tier in tiered_gates:
        if not compiled.selects(relpath, nodeid, markers):
            continue
        if tier == "fast":
            fast += 1
        else:
            integration += 1
    return {"count_fast_shards": fast, "count_integration_shards": integration}


def same_tier_shard_counts(
    gates: Sequence[Gate],
    universe: Sequence[TestRecord],
) -> dict[str, dict[str, int]]:
    """``nodeid -> {count_fast_shards, count_integration_shards}`` (NFR-003).

    Pure over its inputs (the caller supplies the collected ``universe`` via
    :func:`collect_universe`), so this module performs no collection side effect.
    Distinct from the report-only cross-tier duplicate count in :func:`analyze`:
    this counts *within* a tier, where the invariant is uniqueness (``<= 1``),
    not intentional overlap.
    """
    tiered_gates: list[tuple[CompiledGate, str]] = [
        (CompiledGate(gate), tier)
        for gate in gates
        if (tier := _gate_tier(gate)) is not None
    ]
    return {
        test["nodeid"]: shard_counts_for_test(test, tiered_gates)
        for test in universe
    }


# --- Census assembly + regeneration CLI (NFR-006) --------------------------


def _primary_group_for_dir(
    dir_name: str,
    groups: dict[str, tuple[str, ...]],
) -> str | None:
    """The named group whose whole-dir glob claims ``dir_name`` (skip any_src)."""
    whole = _whole_dir_glob(dir_name)
    for name, globs in sorted(groups.items()):
        if name != _ANY_SRC_GROUP and whole in globs:
            return name
    return None


def _arch_blind_group_rows(
    gates: Sequence[Gate],
    models: dict[str, WorkflowModel],
    loc_by_dir: dict[str, int],
) -> list[dict[str, Any]]:
    """The 13 Mode-B arch-blind groups as ``{group, dir, loc}`` rows (data-model)."""
    groups = aggregate_filter_groups(models)
    rows: list[dict[str, Any]] = [
        {
            "group": _primary_group_for_dir(dir_name, groups),
            "dir": dir_name,
            "loc": loc_by_dir.get(dir_name, 0),
        }
        for dir_name in arch_blind_src_dirs(gates, models)
    ]
    rows.sort(key=lambda row: (-int(row["loc"]), str(row["dir"])))
    return rows


_CENSUS_COMMENT = (
    "Construction-derived CI-topology census (mission ci-topology-shrink, "
    "NFR-006). 'worklist' is the FR-001 authority: every src/specify_cli/* dir "
    "with >= t_loc LOC that no src-backed dorny filter group claims. Re-derived "
    "live by tests.architectural._gate_coverage.live_derived_worklist(); WP02's "
    "test_ci_topology_worklist.py asserts census.worklist == "
    "live_derived_worklist(), so a stale/hand-trimmed census reds. Regenerate "
    "with: uv run python -m tests.architectural._gate_coverage --emit-census"
)


def build_census(t_loc: int = T_LOC, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Assemble the full census dict from the LIVE tree + parsed model (NFR-006)."""
    models = load_workflow_models()
    gates = load_gates()
    loc_by_dir = src_package_loc(repo_root)
    return {
        "_comment": _CENSUS_COMMENT,
        "t_loc": t_loc,
        "rule": _WORKLIST_RULE,
        "worklist": live_derived_worklist(t_loc, repo_root),
        "mapped_dirs": sorted(mapped_src_dirs(models)),
        "arch_blind_groups": _arch_blind_group_rows(gates, models, loc_by_dir),
        "timings_baseline": dict(_TIMINGS_BASELINE),
    }


def _emit_census() -> int:
    census = build_census()
    CENSUS_PATH.write_text(
        json.dumps(census, indent=2) + "\n", encoding="utf-8",
    )
    print(
        f"census written: {len(census['worklist'])} worklist dirs, "
        f"{len(census['arch_blind_groups'])} arch-blind groups -> {CENSUS_PATH}",
    )
    return 0


_CENSUS_DERIVED_FIELDS = ("worklist", "mapped_dirs", "arch_blind_groups")


def _verify_census() -> int:
    census: dict[str, Any] = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    live = build_census()
    stale = [f for f in _CENSUS_DERIVED_FIELDS if census.get(f) != live[f]]
    if stale:
        print(f"census is STALE in {stale} — re-run --emit-census")
        return 1
    print(
        f"census fresh: {len(live['worklist'])} worklist dirs, "
        f"{len(live['mapped_dirs'])} mapped dirs, "
        f"{len(live['arch_blind_groups'])} arch-blind groups",
    )
    return 0


# ---------------------------------------------------------------------------
# Baseline I/O + CLI
# ---------------------------------------------------------------------------


def load_baseline() -> dict[str, Any]:
    baseline: dict[str, Any] = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return baseline


def _baseline_payload(report: CoverageReport) -> dict[str, Any]:
    return {
        "_comment": (
            "Gate-coverage ratchet baseline (Issue #2034 / #1933). Frozen set of "
            "test FILES that contain >=1 test selected by zero CI gates — the "
            "visible #1931 worklist. The ratchet (test_gate_coverage.py) fails on "
            "any NEW orphan file not listed here. Regenerate with: "
            "uv run python -m tests.architectural._gate_coverage --update-baseline"
        ),
        "total_tests": report.total,
        "orphan_test_count": report.orphan_count,
        "duplicate_test_count": len(report.duplicate_nodeids),
        "orphan_files": report.orphan_files,
    }


def update_baseline() -> CoverageReport:
    report = analyze(load_gates(), collect_universe())
    BASELINE_PATH.write_text(
        json.dumps(_baseline_payload(report), indent=2) + "\n", encoding="utf-8",
    )
    return report


def _print_check(report: CoverageReport, new_files: list[str]) -> None:
    pct = 100 * report.orphan_count / report.total if report.total else 0.0
    print(f"total tests          : {report.total}")
    print(f"orphans (0 gates)    : {report.orphan_count} ({pct:.1f}%)")
    print(f"duplicates (>=2)     : {len(report.duplicate_nodeids)}")
    print(f"orphan files         : {len(report.orphan_files)}")
    if new_files:
        print(f"\nNEW ungated files ({len(new_files)}):")
        for f in new_files:
            print(f"  {f}")


def check() -> int:
    """Recompute coverage and fail (1) if a new orphan file appeared."""
    report = analyze(load_gates(), collect_universe())
    baseline_files = set(load_baseline().get("orphan_files", []))
    new_files = sorted(set(report.orphan_files) - baseline_files)
    _print_check(report, new_files)
    return 1 if new_files else 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if "--emit-census" in args:
        return _emit_census()
    if "--verify-census" in args:
        return _verify_census()
    if "--update-baseline" in args:
        report = update_baseline()
        print(f"baseline updated: {report.orphan_count} orphans across "
              f"{len(report.orphan_files)} files -> {BASELINE_PATH}")
        return 0
    if "--check" in args:
        return check()
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

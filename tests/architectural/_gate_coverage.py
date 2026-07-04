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

1. Parses every ``pytest`` invocation across the four workflow files that run
   the suite (``ci-quality`` / ``ci-windows`` / ``drift-detector`` /
   ``release``), expanding the ``integration-tests-core-misc`` shard matrix.
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

# The four workflows that actually run the pytest suite (the others lint, build,
# or sync and select no tests).
WORKFLOW_FILES: tuple[str, ...] = (
    "ci-quality.yml",
    "ci-windows.yml",
    "drift-detector.yml",
    "release.yml",
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
    """Parse all four suite-running workflows into the full gate list."""
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

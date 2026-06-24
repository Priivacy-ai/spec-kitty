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

import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from pytest import ExitCode

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
    {int(ExitCode.OK), int(ExitCode.NO_TESTS_COLLECTED)}
)

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


def _substitute_matrix(text: str, mvars: dict[str, Any]) -> str:
    """Expand ``${{ matrix.X }}`` (blanking other ``${{ ... }}`` expressions)."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key.startswith("matrix."):
            return str(mvars.get(key.split(".", 1)[1], ""))
        return ""

    return _GHA_EXPR_RE.sub(repl, text)


def _join_continuations(script: str) -> list[str]:
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


def _strip_to_command(segment: str) -> str:
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


def _parse_pytest_invocation(
    logical_line: str,
) -> tuple[list[str], list[str], str | None] | None:
    """Return ``(paths, ignores, marker)`` for a real pytest command, else None."""
    if logical_line.lstrip().startswith("#"):
        return None
    for segment in _SEGMENT_SPLIT_RE.split(logical_line):
        command = _strip_to_command(segment)
        if not command.startswith("pytest"):
            continue
        tail = command[len("pytest") :]
        return _extract_paths(tail), _IGNORE_RE.findall(tail), _extract_marker(tail)
    return None


def parse_workflow(path: Path) -> list[Gate]:
    """Parse one workflow file into the gates it defines."""
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    gates: list[Gate] = []
    for job_name, job, step in _iter_run_steps(data):
        includes = _matrix_includes(job)
        variants: Sequence[dict[str, Any] | None] = includes if includes else [None]
        for mvars in variants:
            script = _substitute_matrix(step["run"], mvars or {})
            for logical in _join_continuations(script):
                parsed = _parse_pytest_invocation(logical)
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
                    )
                )
    return gates


def load_gates() -> list[Gate]:
    """Parse all four suite-running workflows into the full gate list."""
    gates: list[Gate] = []
    for name in WORKFLOW_FILES:
        gates.extend(parse_workflow(WORKFLOWS_DIR / name))
    return gates


# ---------------------------------------------------------------------------
# Selection model
# ---------------------------------------------------------------------------


def _is_file_entry(entry: str) -> bool:
    return entry.endswith(".py") or ".py::" in entry


def _path_matches(relpath: str, nodeid: str, entry: str) -> bool:
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
        if not any(_path_matches(relpath, nodeid, p) for p in self.paths):
            return False
        if any(_path_matches(relpath, nodeid, ig) for ig in self.gate.ignores):
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
        elif hits >= 2:
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
                f"--- stderr (tail) ---\n{result.stderr[-2000:]}"
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
        json.dumps(_baseline_payload(report), indent=2) + "\n", encoding="utf-8"
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

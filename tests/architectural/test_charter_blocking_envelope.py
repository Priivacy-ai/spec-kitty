"""NFR-003/FR-006/NFR-004 regression envelope (WP06).

Binding contract: ``kitty-specs/charter-preflight-remediation-01KYG9WK/``
``spec.md`` (FR-006, NFR-003, NFR-004) and ``data-model.md``'s F1..F4 fixture
matrix. This mission changes a gate that blocks people from working (the
charter preflight gate, ``specify_cli.charter_runtime.preflight``). The
failure mode this module guards against is fixing one blocking state while
introducing another -- a project that worked before and refuses to
implement afterwards is a worse outcome than the bug the mission set out to
fix.

------------------------------------------------------------------------
THE MEASUREMENT TRAP (T027): a single post-change measurement only proves
what blocks *now*, not what changed. The "before" column below is not
reasoned about -- it was *measured*, by checking out the mission's true
pre-mission commit into a scratch worktree and running the exact same
production call sequence this module runs against the mission tip.
------------------------------------------------------------------------

Baseline provenance (T027 step 1/5, Reviewer Guidance 1)
=========================================================

The pre-mission commit is **not** ``fix/charter-preflight-remediation``'s
current tip -- that branch is this repository's stand-in for a protected
``main`` (see this project's own git-workflow doctrine) and, at WP06
measurement time, it already carries in-mission WP merges (WP03/WP05
approval commits etc.) landed while earlier WPs were reviewed. Naively
diffing against that branch's tip would measure "before WP06" rather than
"before the mission" -- silently laundering WP01-WP05's own changes out of
the regression envelope. The correct baseline is the merge-base with
``main`` itself::

    git merge-base main kitty/mission-charter-preflight-remediation-01KYG9WK
    # == git merge-base fix/charter-preflight-remediation HEAD   (from any lane)
    # == 1aed89411b50203c8dbd9b284d70cc8fefbf32fa

...confirmed identical to local ``main``'s own tip at measurement time
(2026-07-27): this mission had not yet merged anything into ``main``.

``_MERGE_BASE_COMMIT`` below is that SHA. ``test_baseline_commit_is_recorded_
with_provenance`` re-derives and checks it is a real ancestor of ``HEAD``
whenever local git history permits (skips gracefully on a shallow clone --
never fails hard on an environment fact this module cannot control).

Committed evidence, not a live checkout (T027 step 5)
=======================================================

The ``_BASELINE`` table below is **frozen, reviewed data measured once**,
not a live ``git worktree``/``git show`` shell-out performed at every test
run. This was a deliberate choice over the alternative (checking out the
baseline commit inside the test and re-running the production call chain
there):

* A live checkout needs the baseline commit to exist locally, in full (not
  just as a tree object) -- a shallow CI clone or a `git gc`'d object store
  breaks the test through no fault of the code under test.
* It is slow (a second worktree, a second interpreter environment) for
  something that should run as part of the fast/architectural suite.
* The frozen values were derived exactly once, by hand, using a real
  ``git worktree add --detach <sha>`` checkout and the *same* fixture
  primitives (``init_git_repo`` / ``seed_charter_yaml`` / ``seed_bundle_
  files`` / ``make_fresh_repo`` -- all already present at the baseline
  commit) feeding the *same* ``run_charter_preflight`` call this module
  makes against the tip. That is the honest, reviewable derivation the
  Reviewer Guidance asks for; freezing it as data is what keeps the result
  stable and fast on every subsequent run instead of re-deriving (and
  risking silently mis-deriving) it every time.

A genuine finding surfaced along the way (documented, not "fixed" here --
out of this WP's owned-file scope)
====================================================================

``run_charter_preflight`` takes an ``allow_missing_charter`` flag
(``charter_runtime/preflight/runner.py``). With it left at its default
(``False``) -- the parameterisation ``spec-kitty implement``, ``spec-kitty
next --result ...``, and the standalone ``spec-kitty charter preflight``
CLI all use -- a never-initialised project (F1) **fails closed**, by
existing, reviewed, pre-mission design (see ``tests/specify_cli/
charter_preflight/test_runner.py::test_missing_charter_blocks_mutation_
gates_by_default``, unmodified by this mission). Only a read-only/dashboard
caller that opts in via ``allow_missing_charter=True`` (``spec-kitty
next`` in query mode, the dashboard) gets the advisory, non-blocking
treatment (``test_missing_charter_in_fresh_project_is_advisory_not_
blocking``, likewise unmodified).

So "F1 is advisory, non-blocking" (data-model.md) is true of the read-only
gate path, not the mutation gate -- and this module measures *both*,
per shape, rather than picking the one that makes the aspirational table
in data-model.md look right. Both are proven unchanged between baseline
and tip below (T028); T029 exercises the one surface where "F1 stays
advisory" is actually, presently true (the real ``run_preflight_for_
dashboard`` hook, not a hand-picked kwarg on the bare runner).

A second, adjacent finding, also unchanged baseline-to-tip and out of
scope here: under ``allow_missing_charter=True`` the runner's fresh-project
carve-out (``_is_optional_missing_charter_fresh_project``) matches on
``state`` values only, so F2 (legacy bundle, no ``charter.yaml``) presents
the identical all-``missing`` state triple as F1 and is *also* waved
through as advisory by that specific parameterisation. This is pre-existing
(the function is byte-identical at the baseline commit) and orthogonal to
every WP01-WP05 change; recorded here for the mission review, not chased.

A third finding, surfaced by review cycle 1's demand that T030's surface
list actually be complete: ``charter bundle validate`` (R-003 site 7)
crashes uncaught on F4, both plain and ``--json`` --
``ruamel.yaml.parser.ParserError`` out of ``get_bundle_schema_version``
(``src/doctrine/versioning.py``), called via ``_bundle_compatibility_error``
from ``validate()`` (``cli/commands/charter_bundle.py``), which -- unlike
``status`` and ``resynthesize``, both of which call the same primitive on
the same input without incident -- has no catch-all around the call. Also
confirmed pre-existing by independent baseline reproduction (see
``_KNOWN_PRE_EXISTING_CRASH_CELLS`` below for the full chain and the
correction to review-cycle-1.md's function-level attribution). Recorded
for the mission review, not fixed here -- out of this WP's owned-file
scope, and now `xfail(strict=True)`-pinned in T030 rather than silently
absent from the tested surface list.

Subtasks
========

* T027/T028 -- ``test_blocking_count_same_or_lower_per_shape``: the
  four-shape matrix, both call parameterisations, baseline vs tip, with a
  per-shape (not aggregate) same-or-lower assertion naming the offending
  shape on failure.
* T029 -- ``test_greenfield_stays_advisory_through_real_gate_path``: F1
  through the real, production ``run_preflight_for_dashboard`` hook.
* T030 -- ``test_diagnostic_surface_reports_rather_than_raises``: every
  WP04-converged operator-facing diagnostic, over all four shapes, via
  CLI subprocess (the only vantage point from which "raised a traceback at
  the operator" is actually observable), including ``--json``,
  ``charter context --include section:<id>``, ``charter bundle validate``,
  ``charter sync``, and ``charter resynthesize`` explicitly (cycle 2: all
  nine of WP04's R-003 sites are now covered by a CLI invocation in this
  list -- see the comment above ``_DIAGNOSTIC_CLI_INVOCATIONS`` for the
  site-by-site mapping).
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from specify_cli.charter_runtime.preflight.hook import run_preflight_for_dashboard
from specify_cli.charter_runtime.preflight.runner import run_charter_preflight

from tests.specify_cli.charter_preflight._fixtures import (
    build_f1_no_charter,
    build_f2_legacy_bundle_no_charter_yaml,
    build_f3_valid_charter,
    build_f4_invalid_charter_yaml,
)

# Whole-suite CLI subprocess invocations (T030) -- same shape as
# test_remediation_effectiveness.py, structurally incompatible with mutmut's
# forked sandbox (ADR 2026-04-20-1).
pytestmark = [pytest.mark.architectural, pytest.mark.git_repo, pytest.mark.non_sandbox]


# ---------------------------------------------------------------------------
# Baseline provenance (T027)
# ---------------------------------------------------------------------------

#: The mission's true pre-mission commit -- see the module docstring for how
#: this was derived and why it is NOT ``fix/charter-preflight-remediation``'s
#: current tip.
_MERGE_BASE_COMMIT = "1aed89411b50203c8dbd9b284d70cc8fefbf32fa"


def _find_repo_root() -> Path:
    candidate = Path(__file__).resolve().parent
    while candidate != candidate.parent:
        if (candidate / "pyproject.toml").exists():
            return candidate
        candidate = candidate.parent
    raise RuntimeError("Could not find repo root (no pyproject.toml found in any parent directory)")


def test_baseline_commit_is_recorded_with_provenance() -> None:
    """T027 step 1/5, Reviewer Guidance 1: the baseline is identified and real.

    Re-derives the ancestry relationship whenever local git history permits
    it, so a reviewer does not have to trust the recorded SHA on faith --
    but skips (never fails) on a shallow clone or a gc'd object, which are
    environment facts this module cannot control and must not be graded on.
    """
    assert re.fullmatch(r"[0-9a-f]{40}", _MERGE_BASE_COMMIT), (
        f"baseline commit must be a full 40-hex SHA, got {_MERGE_BASE_COMMIT!r}"
    )
    repo_root = _find_repo_root()
    # A shallow clone cannot answer an ancestry question that crosses its graft
    # boundary, and it does NOT report that as an error: `merge-base
    # --is-ancestor` simply returns 1 ("not an ancestor"), indistinguishable
    # from a genuinely stale SHA. The 128-class guard below therefore never
    # fires for the case that actually occurs, which is how this test failed on
    # CI (fetch-depth-limited checkout) while passing on every full clone.
    # Detect shallowness up front instead of inferring it from an exit code.
    try:
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git unavailable in this environment; baseline provenance recorded but not re-verified")
    is_shallow = shallow.returncode == 0 and shallow.stdout.strip() == "true"
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", _MERGE_BASE_COMMIT, "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git unavailable in this environment; baseline provenance recorded but not re-verified")
    if result.returncode not in (0, 1):
        # 128-class exit: commit unknown locally (shallow clone) -- an
        # environment limitation, not evidence the recorded SHA is wrong.
        pytest.skip(
            f"baseline commit {_MERGE_BASE_COMMIT} not resolvable locally "
            f"(git exit {result.returncode}: {result.stderr.strip()}); "
            "provenance recorded but not re-verified in this environment"
        )
    # A POSITIVE answer is always trustworthy -- git found the ancestry path, so
    # shallowness is irrelevant and the assertion below simply passes. Only a
    # NEGATIVE answer is unreliable in a truncated clone, because git cannot
    # distinguish "no such path" from "the path runs past my graft boundary".
    # Skipping on shallowness alone would make this vacuous everywhere (this very
    # checkout is shallow yet answers correctly); narrowing the skip to the
    # negative case keeps the check as sensitive as the environment permits.
    if result.returncode == 1 and is_shallow:
        pytest.skip(
            "shallow clone reported 'not an ancestor', which it cannot distinguish "
            "from an answer beyond its graft boundary; provenance recorded but not "
            "re-verified in this environment"
        )
    assert result.returncode == 0, (
        f"recorded baseline commit {_MERGE_BASE_COMMIT} is not an ancestor of HEAD -- "
        "provenance is stale; re-derive via `git merge-base main <mission-branch>`"
    )


# ---------------------------------------------------------------------------
# The four-shape matrix (T027/T028)
# ---------------------------------------------------------------------------

#: Reused verbatim from WP01 (DIRECTIVE_044: no third fixture mechanism).
_SHAPE_BUILDERS: tuple[tuple[str, Callable[[Path], Path]], ...] = (
    ("F1", build_f1_no_charter),
    ("F2", build_f2_legacy_bundle_no_charter_yaml),
    ("F3", build_f3_valid_charter),
    ("F4", build_f4_invalid_charter_yaml),
)


@dataclass(frozen=True)
class _ShapeBaseline:
    """One shape's measured pre-mission blocking status, both call shapes.

    ``mutation_gate_blocked``: ``run_charter_preflight(repo, auto_refresh=
    False)`` -- the parameterisation ``implement``/``next --result``/the
    standalone ``charter preflight`` CLI use.

    ``advisory_blocked``: the same call with ``allow_missing_charter=True``
    -- the parameterisation ``run_preflight_for_dashboard`` (dashboard,
    ``next`` query mode) uses.
    """

    shape: str
    mutation_gate_blocked: bool
    advisory_blocked: bool


#: Measured once (2026-07-27) against a scratch ``git worktree add --detach
#: 1aed89411b50203c8dbd9b284d70cc8fefbf32fa`` checkout, using that commit's
#: own ``init_git_repo``/``seed_charter_yaml``/``seed_bundle_files``/
#: ``make_fresh_repo`` primitives (``build_f1_no_charter``..``build_f4_
#: invalid_charter_yaml`` did not exist yet at the baseline commit -- they
#: are WP01's own addition -- so the baseline was reconstructed from the
#: lower-level primitives WP01 built them from, which *do* predate this
#: mission). See the module docstring for the exact commands.
_BASELINE: tuple[_ShapeBaseline, ...] = (
    _ShapeBaseline("F1", mutation_gate_blocked=True, advisory_blocked=False),
    _ShapeBaseline("F2", mutation_gate_blocked=True, advisory_blocked=False),
    _ShapeBaseline("F3", mutation_gate_blocked=False, advisory_blocked=False),
    _ShapeBaseline("F4", mutation_gate_blocked=True, advisory_blocked=True),
)

_BASELINE_BY_SHAPE: dict[str, _ShapeBaseline] = {b.shape: b for b in _BASELINE}


def _measure_shape(repo_root: Path) -> tuple[bool, bool]:
    """Return ``(mutation_gate_blocked, advisory_blocked)`` for ``repo_root``.

    Both calls go through ``run_charter_preflight`` -- the real preflight
    runner, not ``compute_freshness`` alone -- matching how every real
    consumer (``implement``, ``next``, ``charter preflight``, the
    dashboard) actually invokes it.
    """
    mutation = run_charter_preflight(repo_root, auto_refresh=False)
    advisory = run_charter_preflight(repo_root, auto_refresh=False, allow_missing_charter=True)
    return (not mutation.passed, not advisory.passed)


@contextmanager
def _tmp_repo() -> Iterator[Path]:
    with TemporaryDirectory() as raw:
        yield Path(raw)


def render_four_shape_comparison_table() -> str:
    """Build the T027 deliverable: baseline vs tip, both gate parameterisations.

    Exercised by :func:`test_four_shape_comparison_table_is_well_formed`
    below so this is not dead code -- it is also what the mission review and
    the PR description quote directly.
    """
    header = (
        "| Shape | Mutation-gate before | Mutation-gate after | "
        "Advisory-gate before | Advisory-gate after |\n"
        "|---|---|---|---|---|"
    )
    rows = []
    for shape_name, build_fixture in _SHAPE_BUILDERS:
        baseline = _BASELINE_BY_SHAPE[shape_name]
        with _tmp_repo() as repo_root:
            build_fixture(repo_root)
            after_mutation, after_advisory = _measure_shape(repo_root)
        rows.append(
            f"| {shape_name} | "
            f"{'blocking' if baseline.mutation_gate_blocked else 'not blocking'} | "
            f"{'blocking' if after_mutation else 'not blocking'} | "
            f"{'blocking' if baseline.advisory_blocked else 'not blocking'} | "
            f"{'blocking' if after_advisory else 'not blocking'} |"
        )
    return "\n".join([header, *rows])


def test_four_shape_comparison_table_is_well_formed() -> None:
    """T027: the comparison table covers all four shapes on both arms."""
    table = render_four_shape_comparison_table()
    for shape_name, _ in _SHAPE_BUILDERS:
        assert shape_name in table, f"comparison table is missing shape {shape_name!r}: {table}"
    lines = table.splitlines()
    # header title row + markdown separator row + one row per shape.
    assert len(lines) == 2 + len(_SHAPE_BUILDERS), (
        f"expected a title row + separator row + {len(_SHAPE_BUILDERS)} shape rows, got:\n{table}"
    )


@pytest.mark.parametrize("shape_name, build_fixture", _SHAPE_BUILDERS, ids=[s for s, _ in _SHAPE_BUILDERS])
def test_blocking_count_same_or_lower_per_shape(
    shape_name: str,
    build_fixture: Callable[[Path], Path],
    tmp_path: Path,
) -> None:
    """T028: same-or-lower, asserted PER SHAPE, naming the offending shape.

    An aggregate blocking count could stay level while one shape silently
    swapped its blocking status with another -- this asserts each shape
    independently, on both real call parameterisations (mutation-gate and
    advisory), so a regression on either surface is caught and named.
    """
    repo_root = build_fixture(tmp_path)
    baseline = _BASELINE_BY_SHAPE[shape_name]
    after_mutation, after_advisory = _measure_shape(repo_root)

    assert int(after_mutation) <= int(baseline.mutation_gate_blocked), (
        f"NFR-003 regression: shape {shape_name!r} newly blocks the MUTATION gate "
        "(spec-kitty implement / next --result / charter preflight) -- "
        f"before={baseline.mutation_gate_blocked} after={after_mutation}"
    )
    assert int(after_advisory) <= int(baseline.advisory_blocked), (
        f"NFR-003 regression: shape {shape_name!r} newly blocks the ADVISORY gate "
        "(dashboard / next query mode, run_preflight_for_dashboard) -- "
        f"before={baseline.advisory_blocked} after={after_advisory}"
    )


def test_total_blocking_count_same_or_lower_aggregate() -> None:
    """T028 supplementary: the aggregate total, kept in lockstep with the
    per-shape assertions above -- never a substitute for them (a per-shape
    swap could hide behind an unchanged aggregate; the parametrized test
    above is what actually catches that)."""
    before_total = sum(b.mutation_gate_blocked for b in _BASELINE)
    after_total = 0
    for _shape_name, build_fixture in _SHAPE_BUILDERS:
        with _tmp_repo() as repo_root:
            build_fixture(repo_root)
            after_mutation, _after_advisory = _measure_shape(repo_root)
            after_total += int(after_mutation)
    assert after_total <= before_total, (
        f"NFR-003 regression: total mutation-gate blocking count rose from "
        f"{before_total} to {after_total}"
    )


# ---------------------------------------------------------------------------
# T029 -- greenfield stays advisory, through the real gate path
# ---------------------------------------------------------------------------


def test_greenfield_stays_advisory_through_real_gate_path(tmp_path: Path) -> None:
    """FR-006: F1 (no charter at all) stays advisory, non-blocking.

    Calls the actual production hook (``run_preflight_for_dashboard``,
    ``charter_runtime/preflight/hook.py``) unmodified -- the same function
    ``spec-kitty next`` (query mode) and the dashboard call -- rather than a
    unit-level check on ``compute_freshness`` that would bypass the runner
    entirely. This is the one real caller for which "F1 does not block" is
    actually, presently true (see the module docstring for why the mutation
    gate, a separate real caller, is a different and unchanged story).
    """
    repo_root = build_f1_no_charter(tmp_path)

    result = run_preflight_for_dashboard(repo_root)

    assert result.passed is True, (
        f"FR-006 regression: greenfield (F1) newly blocks the advisory gate path; "
        f"blocked_reason={result.blocked_reason!r}"
    )
    assert result.blocked_reason is None, (
        f"FR-006 regression: greenfield (F1) produced a blocked_reason: {result.blocked_reason!r}"
    )


# ---------------------------------------------------------------------------
# T030 -- zero new uncaught exception paths, every diagnostic, every shape
# ---------------------------------------------------------------------------

#: Uncaught-traceback marker. A CLI subprocess is the only vantage point
#: from which "a diagnostic raised at the operator" is directly observable
#: (an in-process call catches nothing the CLI boundary itself wouldn't);
#: this is why T030 runs through ``run_cli`` rather than importing the
#: underlying functions.
#:
#: Deliberately WITHOUT the trailing colon (cycle 2 fix, found while adding
#: the ``bundle validate`` coverage below). Typer's default exception
#: rendering (rich's "pretty exceptions", on by default whenever ``rich`` is
#: installed and not explicitly disabled) prints the header as
#: ``"Traceback (most recent call last) ─...─╮"`` inside a box -- no colon,
#: box-drawing characters instead. The colon-terminated form only matches a
#: *raw* CPython traceback, which this CLI never actually emits (typer's
#: rich rendering is always active here). Verified directly: reproducing the
#: F4/``bundle validate`` crash below with the colon-terminated marker
#: produced a false negative (plain invocation: no colon in rich's boxed
#: header, so the substring check silently missed a genuine, confirmed
#: uncaught exception) while the ``--json`` sibling still failed via the
#: JSON-parseability branch below. Dropping the colon is a superset match --
#: still matches a raw CPython traceback (which contains this substring as
#: a prefix of the line) -- so this is strictly more sensitive, not a
#: behaviour change for any case that previously failed correctly.
_TRACEBACK_MARKER = "Traceback (most recent call last)"

#: WP04-converged operator-facing diagnostics (R-003), covering:
#: * the bootstrap ``--action`` render, plain and ``--json`` (T030 step 4);
#: * ``--include section:<id>`` specifically (T030 step 5) -- before WP04
#:   this raised ``ValueError("No charter.md found for section selector.")``
#:   uncaught, on exactly the command the compact-mode renderer tells
#:   operators to run next (research.md R-003 site 10);
#: * the preflight gate's own ``--json`` surface;
#: * ``charter status --json`` (R-003 site 4/5, also exercises site 3 --
#:   ``_resolve_charter_path`` -- since ``status`` is one of its two callers);
#: * ``charter bundle validate``, plain and ``--json`` (R-003 site 7 --
#:   the completeness gap review cycle 1 found: this module tested six of
#:   WP04's nine converged sites and silently never invoked this one);
#: * ``charter sync`` (R-003 site 3's other caller, and site 6 --
#:   ``src/charter/sync.py``, the staleness reporter WP04 T019 explicitly
#:   deferred a routing decision on -- this at least proves it degrades
#:   rather than raising);
#: * ``charter resynthesize`` with no ``--topic`` (R-003 site 8) -- exercises
#:   the same presence-and-compatibility preamble as ``bundle validate`` and
#:   ``status`` (``_assert_bundle_compatible``) without running the (slow,
#:   mutating) synthesis pipeline itself, which needs a resolvable topic and
#:   is out of scope for a presence/crash regression check.
#:
#: Site 1 (``charter_runtime/freshness/computer.py`` -- the gate) is the
#: convergence target, not one of the nine, and is exercised directly via
#: ``run_charter_preflight`` throughout T027-T029 above plus its own CLI
#: surface here (``preflight_json``). Sites 2, 9, 10 all live behind the one
#: ``charter context`` command and its ``--action``/``--include``/``--json``
#: flag combinations already covered above.
_DIAGNOSTIC_CLI_INVOCATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("context_action", ("charter", "context", "--action", "implement")),
    ("context_action_json", ("charter", "context", "--action", "implement", "--json")),
    ("context_include_section", ("charter", "context", "--include", "section:regression-vigilance")),
    (
        "context_include_section_json",
        ("charter", "context", "--include", "section:regression-vigilance", "--json"),
    ),
    ("preflight_json", ("charter", "preflight", "--json")),
    ("status_json", ("charter", "status", "--json")),
    ("bundle_validate", ("charter", "bundle", "validate")),
    ("bundle_validate_json", ("charter", "bundle", "validate", "--json")),
    ("sync_json", ("charter", "sync", "--json")),
    ("resynthesize_json", ("charter", "resynthesize", "--json")),
)

#: T030 documented exclusion (cycle 2 review finding, not fixed here --
#: out of this WP's owned-file scope; production code lives in
#: ``src/specify_cli/cli/commands/charter_bundle.py`` and
#: ``src/doctrine/versioning.py``, neither owned by WP06).
#:
#: ``charter bundle validate`` crashes uncaught on F4 (unparseable
#: ``charter.yaml``), both plain and ``--json``. The exact chain (traced
#: directly, not inherited from the review doc's guess -- see below):
#: ``validate()`` (``cli/commands/charter_bundle.py:367``) calls
#: ``_bundle_compatibility_error`` (``:261``), which calls
#: ``get_bundle_schema_version`` (``src/doctrine/versioning.py:194``),
#: which does ``YAML().load(charter_yaml_path)`` with no ``try``/``except``
#: around the parse -- an unparseable ``charter.yaml`` raises
#: ``ruamel.yaml.parser.ParserError`` straight through ``validate()``,
#: which (unlike ``status`` and ``resynthesize``, both of which wrap their
#: entire body in ``except Exception: _emit_error(..., unexpected=True)``)
#: has no catch-all around this call -- only its own initial
#: ``resolve_canonical_repo_root`` call is guarded. ``status`` and
#: ``resynthesize`` call the exact same crash-prone primitive
#: (``_assert_bundle_compatible`` -> ``get_bundle_schema_version``) on the
#: same F4 input and do NOT crash, because their catch-all converts the
#: same ``ParserError`` into a reported error -- confirming the gap is
#: `validate()`'s missing catch-all, not a defect in the shared primitive.
#:
#: (Correction to review-cycle-1.md's finding, which attributed this to
#: ``validate_synthesis_state`` in ``src/charter/bundle.py``: reproducing
#: and reading the actual traceback shows ``validate_synthesis_state`` is
#: never reached -- the crash happens earlier, in the compatibility check
#: above it. ``validate_synthesis_state`` itself was independently exercised
#: against this fixture and does not crash.)
#:
#: Verified pre-existing, independently, not inherited: reproduced the
#: identical crash (same file/line, same ``ParserError``) at the baseline
#: commit (``1aed89411b50203c8dbd9b284d70cc8fefbf32fa``) via a detached
#: ``git worktree add --detach``, using that commit's own
#: ``init_git_repo``/``seed_charter_yaml(valid=False)`` primitives feeding
#: the same ``charter bundle validate`` CLI invocation. ``git diff`` of
#: ``src/doctrine/versioning.py`` baseline-to-tip is empty (byte-identical);
#: ``charter_bundle.py``'s only change in this region is WP04/T019's
#: intended ``.exists()`` -> ``charter_yaml_present()`` swap, which does not
#: touch the crash path (both resolve truthy for an existing-but-invalid
#: ``charter.yaml``, so the crash fires identically either way). Not a
#: WP01-WP05 regression.
_KNOWN_PRE_EXISTING_CRASH_CELLS: frozenset[tuple[str, str]] = frozenset(
    {
        ("bundle_validate", "F4"),
        ("bundle_validate_json", "F4"),
    }
)


#: Rich styles its traceback header, so on any stream it considers styleable the
#: marker arrives as ``\x1b[1mTraceback \x1b[0m\x1b[1;2m(most recent call last)\x1b[0m``
#: and a plain substring test silently misses it. That is exactly how this guard
#: went blind on CI while passing on every local run: the ``bundle_validate``
#: cell "passed" against a genuine uncaught traceback and tripped its own
#: ``xfail(strict=True)`` as an unexpected pass. A guard whose sensitivity
#: depends on whether the runner allocated a TTY is not a guard, so normalise
#: before matching. This is the same class of false negative the colon note
#: above records, one layer further down.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _contains_traceback(stream: str) -> bool:
    """Return whether a traceback header is present, ignoring styling and wrapping."""
    normalized = " ".join(_ANSI_ESCAPE_RE.sub("", stream).split())
    return _TRACEBACK_MARKER in normalized


def _assert_reports_rather_than_raises(result: subprocess.CompletedProcess[str], *, json_mode: bool) -> None:
    """NFR-004: the surface degraded to a reported state, never a raw traceback."""
    assert not _contains_traceback(result.stderr), (
        f"NFR-004 violation: an uncaught traceback reached the operator: {result.stderr!r}"
    )
    assert not _contains_traceback(result.stdout), (
        f"NFR-004 violation: an uncaught traceback leaked onto stdout: {result.stdout!r}"
    )
    assert result.returncode in (0, 1), (
        f"unexpected exit code {result.returncode} (a reported diagnostic exits 0 or 1, "
        f"never a crash); stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    if json_mode:
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(
                "NFR-004 violation: the --json surface did not emit parseable JSON "
                f"({exc}); stdout={result.stdout!r} stderr={result.stderr!r}"
            )


@pytest.mark.parametrize("shape_name, build_fixture", _SHAPE_BUILDERS, ids=[s for s, _ in _SHAPE_BUILDERS])
@pytest.mark.parametrize(
    "label, args",
    _DIAGNOSTIC_CLI_INVOCATIONS,
    ids=[label for label, _ in _DIAGNOSTIC_CLI_INVOCATIONS],
)
def test_diagnostic_surface_reports_rather_than_raises(
    label: str,
    args: tuple[str, ...],
    shape_name: str,
    build_fixture: Callable[[Path], Path],
    tmp_path: Path,
    run_cli: Callable[..., subprocess.CompletedProcess[str]],
    request: pytest.FixtureRequest,
) -> None:
    """T030: every WP04-converged diagnostic reports, never raises, on every shape.

    F4 (unparseable ``charter.yaml``) is the shape most likely to throw --
    malformed input is exactly where a resolver's parse step is weakest --
    and it is exercised here on every listed surface, same as F1-F3.

    Note: WP04's own parity test (``tests/charter/test_charter_presence_
    seam.py::test_all_surfaces_agree_on_presence``) excludes F4 from ONE
    assertion (``build_charter_context`` via direct call with a companion
    ``charter.md`` present) because of a pre-existing, unrelated crash in
    ``doctrine.spdd_reasons.activation``. That exact companion-``charter.md``
    shape is NOT reachable from this module: the canonical WP01
    ``build_f4_invalid_charter_yaml`` fixture this WP is required to reuse
    (DIRECTIVE_044) seeds only ``charter.yaml``, no ``charter.md`` -- verified
    directly that ``build_charter_context`` does not crash against it. No
    exclusion is needed here; if a future caller seeds ``charter.md``
    alongside this fixture, it inherits WP04's already-documented, already-
    excluded pre-existing defect, not a new one.

    ``charter bundle validate`` on F4 is a second, distinct pre-existing
    NFR-004 gap (cycle 2 review finding) -- see
    ``_KNOWN_PRE_EXISTING_CRASH_CELLS`` above for the full chain and the
    baseline reproduction. Unlike site 2 above, this one IS reachable from
    this module's own fixture, so it cannot be argued away in a docstring --
    it is marked ``xfail(strict=True)`` below: the assertion still runs, so
    if `validate()` ever grows the same catch-all `status`/`resynthesize`
    already have, this flips to an unexpected pass and fails the suite,
    forcing the exclusion to be removed rather than silently going stale.
    """
    if (label, shape_name) in _KNOWN_PRE_EXISTING_CRASH_CELLS:
        request.node.add_marker(
            pytest.mark.xfail(
                reason=(
                    f"{label!r} on shape {shape_name!r}: documented pre-existing NFR-004 "
                    "gap in charter_bundle.py's validate() (see _KNOWN_PRE_EXISTING_CRASH_"
                    "CELLS docstring) -- production fix is out of this WP's owned-file scope"
                ),
                strict=True,
                # NOT narrowed to AssertionError: the --json branch reports via
                # `pytest.fail`, which raises `Failed`, so an `AssertionError`-only
                # xfail left that cell failing outright on CI instead of xfailing.
                # Any failure of this cell is the documented pre-existing gap;
                # `strict=True` still forces removal the moment it starts passing.
            )
        )
    repo_root = build_fixture(tmp_path)
    result = run_cli(repo_root, *args)
    _assert_reports_rather_than_raises(result, json_mode="--json" in args)

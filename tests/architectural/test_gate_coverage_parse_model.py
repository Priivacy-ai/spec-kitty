"""Unit guards for the WP01 parse-model extensions of :mod:`_gate_coverage`.

Mission ci-suite-map-bind (Wave 0, #2297/#2296/#2333): WP01 extends the
gate-coverage module ADDITIVELY with the parsed relation surfaces the
downstream invariant suites (FR-001, FR-003, FR-005, FR-008, FR-010..FR-013)
consume. These tests pin each new parse surface directly — fixture-first for
determinism, plus live smoke checks against the real workflows that assert
only relations the mission's later work packages will not remove (they add
jobs/groups/markers; they never drop the ones pinned here).

The INVARIANTS over these surfaces (phantom-needs, filter-consumption,
marker-completeness, ...) live in WP04's test files, not here — this file
guards only that the parsing itself is faithful.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]


# ---------------------------------------------------------------------------
# positive_marker_tokens (FR-001 state-(i) primitive)
# ---------------------------------------------------------------------------


def test_positive_marker_tokens_is_negation_aware() -> None:
    """`not windows_ci` must NOT count windows_ci as positively referenced.

    This is the spec's pinned edge case: every Linux gate negates
    ``windows_ci``; a sign-blind token grab would falsely satisfy the
    marker-completeness invariant for it.
    """
    assert gc.positive_marker_tokens(
        "not windows_ci and (git_repo or integration or architectural)"
    ) == frozenset({"git_repo", "integration", "architectural"})
    assert gc.positive_marker_tokens("windows_ci") == frozenset({"windows_ci"})
    # Negation distributes over a parenthesised group.
    assert gc.positive_marker_tokens("not (fast or slow)") == frozenset()
    # Double negation flips back to positive.
    assert gc.positive_marker_tokens("not not fast") == frozenset({"fast"})
    # Gates without a marker expression reference nothing.
    assert gc.positive_marker_tokens(None) == frozenset()
    assert gc.positive_marker_tokens("") == frozenset()


def test_positive_marker_tokens_fails_loudly_on_invalid_expression() -> None:
    """An expression pytest's own evaluator rejects must raise, not return junk.

    pytest 9's ``Expression.compile`` raises a plain ``SyntaxError`` subclass
    for an unparsable expression (ParseError was folded into it).
    """
    with pytest.raises(SyntaxError):
        gc.positive_marker_tokens("and and")


def test_routed_marker_names_live_floor() -> None:
    """The live routed-by-marker set contains the 8 known positive tokens.

    Containment (not equality) so later mission WPs that route new markers
    (``unit``/``contract`` via the residual job) do not red this parse guard.
    """
    routed = gc.routed_marker_names(gc.load_gates())
    assert routed >= {
        "fast",
        "integration",
        "git_repo",
        "architectural",
        "slow",
        "timing",
        "quarantine",
        "windows_ci",
    }
    # Negation-awareness on live data: ci-quality.yml only ever NEGATES
    # windows_ci; its positive reference lives in ci-windows.yml alone.
    ci_quality_gates = [g for g in gc.load_gates() if g.workflow == "ci-quality.yml"]
    assert "windows_ci" not in gc.routed_marker_names(ci_quality_gates)


# ---------------------------------------------------------------------------
# WorkflowModel: needs / needs.<job>.result reads (FR-003a / FR-003d)
# ---------------------------------------------------------------------------


def _write_workflow(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "wf.yml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_workflow_model_parses_needs_and_result_reads(tmp_path: Path) -> None:
    """`needs:` lists (str or list form) and run-script result reads are parsed.

    Parsing is sign-blind on purpose: a ``needs.ghost.result`` read WITHOUT a
    declaration must still surface here — WP04's invariant is what rejects it.
    """
    path = _write_workflow(
        tmp_path,
        """\
        name: fixture
        on: push
        jobs:
          a:
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
          b:
            needs: a
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
          agg:
            needs: [a, b]
            if: always()
            runs-on: ubuntu-latest
            steps:
              - run: |
                  echo "${{ needs.a.result }}"
                  echo "${{ needs.ghost.result }}"
        """,
    )
    model = gc.load_workflow_model(path)
    assert model.job_needs == {"a": (), "b": ("a",), "agg": ("a", "b")}
    assert model.needs_result_reads["agg"] == frozenset({"a", "ghost"})
    assert model.needs_result_reads["a"] == frozenset()


# ---------------------------------------------------------------------------
# WorkflowModel: dorny filter groups + job→group gating (FR-003b / FR-010 / FR-011)
# ---------------------------------------------------------------------------


def test_workflow_model_parses_filter_groups_and_job_gating(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """\
        name: fixture
        on: pull_request
        jobs:
          changes:
            runs-on: ubuntu-latest
            steps:
              - uses: dorny/paths-filter@v4
                id: filter
                with:
                  filters: |
                    grp1:
                      - 'src/x/**'
                      - 'tests/x/**'
                    grp2:
                      - 'src/y/**'
          job2:
            needs: [changes]
            if: always() && needs.changes.outputs.grp1 == 'true'
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
          ungated:
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
        """,
    )
    model = gc.load_workflow_model(path)
    assert model.filter_groups == {
        "grp1": ("src/x/**", "tests/x/**"),
        "grp2": ("src/y/**",),
    }
    assert model.job_gating_groups["job2"] == frozenset({"grp1"})
    assert model.job_gating_groups["ungated"] == frozenset()


# ---------------------------------------------------------------------------
# WorkflowModel: --cov emitters + diff-cover critical paths (FR-005)
# ---------------------------------------------------------------------------


def test_workflow_model_parses_cov_targets_and_critical_paths(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """\
        name: fixture
        on: push
        jobs:
          tests:
            runs-on: ubuntu-latest
            steps:
              - run: |
                  uv run pytest tests/a \\
                    --cov=src/a --cov=src/b \\
                    --cov-report=xml
          diff-coverage:
            runs-on: ubuntu-latest
            steps:
              - run: |
                  critical_paths=(
                    'src/a/*'
                    'src/b/critical.py'
                  )
                  uv run diff-cover --include "${critical_paths[@]}"
        """,
    )
    model = gc.load_workflow_model(path)
    assert model.cov_targets["tests"] == frozenset({"src/a", "src/b"})
    assert model.cov_targets["diff-coverage"] == frozenset()
    assert model.diff_cover_critical_paths == ("src/a/*", "src/b/critical.py")


# ---------------------------------------------------------------------------
# WorkflowModel: on: triggers — pull_request types + outer paths (FR-012 / FR-013)
# ---------------------------------------------------------------------------


def test_workflow_model_parses_trigger_types_and_paths(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """\
        name: fixture
        on:
          pull_request:
            types: [opened, synchronize, ready_for_review]
            paths:
              - 'src/**'
              - 'tests/**'
          push:
            paths:
              - 'src/**'
        jobs:
          a:
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
        """,
    )
    model = gc.load_workflow_model(path)
    assert model.pull_request_types == ("opened", "synchronize", "ready_for_review")
    assert model.pull_request_paths == ("src/**", "tests/**")
    assert model.push_paths == ("src/**",)


def test_workflow_model_handles_absent_trigger_sections(tmp_path: Path) -> None:
    """Bare ``on: push`` (no pull_request, no paths) parses to empty tuples."""
    path = _write_workflow(
        tmp_path,
        """\
        name: fixture
        on: push
        jobs:
          a:
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
        """,
    )
    model = gc.load_workflow_model(path)
    assert model.pull_request_types == ()
    assert model.pull_request_paths == ()
    assert model.push_paths == ()


# ---------------------------------------------------------------------------
# Live smoke: the parsed relations exist on the real ci-quality.yml
# ---------------------------------------------------------------------------


def test_workflow_model_live_ci_quality_relations() -> None:
    """Each parsed surface is non-trivially populated on the live workflow.

    Only relations that are stable across this mission's own later edits are
    pinned (existing jobs/groups are never removed by the mission; they are
    added to).
    """
    model = gc.load_workflow_model(gc.WORKFLOWS_DIR / "ci-quality.yml")
    # needs + result-loop reads (FR-003a/d substrate). Post-FR-011 (WP03
    # surgery) the quality-gate verdict consumes the FULL needs context via
    # ``toJSON(needs)`` — there is no literal ``needs.<job>.result`` loop left
    # to read, so the parsed read-set is EMPTY by construction: a phantom
    # result-read (the FR-003a failure class) can no longer be written for the
    # aggregator. A non-empty set reappearing here means someone reintroduced
    # a hand-enumerated result list — the exact drift the rewrite removed.
    assert "e2e-cross-cutting" in model.job_needs["quality-gate"]
    assert model.needs_result_reads["quality-gate"] == frozenset()
    # dorny groups + job gating (FR-003b / FR-011 substrate).
    assert ".github/workflows/ci-quality.yml" in model.filter_groups["core_misc"]
    assert "lanes" in model.job_gating_groups["fast-tests-lanes"]
    # --cov emitters + diff-cover critical paths (FR-005 substrate).
    assert "src/kernel" in model.cov_targets["kernel-tests"]
    assert "src/runtime/next/*" in model.diff_cover_critical_paths
    # Outer trigger paths (FR-012 substrate).
    assert "src/**" in model.pull_request_paths
    assert "src/**" in model.push_paths


# ---------------------------------------------------------------------------
# discover_pytest_workflows (FR-008)
# ---------------------------------------------------------------------------


def test_discover_pytest_workflows_matches_module_allowlist() -> None:
    """The content probe over .github/workflows/ finds exactly WORKFLOW_FILES.

    This is FR-008's ground-truth relation: a fifth pytest-running workflow
    must enter the model (WP04 binds the fail-closed invariant; this guard
    pins that the probe and the allowlist agree today).
    """
    assert gc.discover_pytest_workflows() == frozenset(gc.WORKFLOW_FILES)


def test_discover_pytest_workflows_detects_fixture_workflow(tmp_path: Path) -> None:
    """A workflow invoking pytest in a run script is discovered by content probe."""
    (tmp_path / "sneaky.yml").write_text(
        textwrap.dedent(
            """\
            name: sneaky
            on: push
            jobs:
              hidden-suite:
                runs-on: ubuntu-latest
                steps:
                  - run: uv run pytest tests/hidden -m fast
            """
        ),
        encoding="utf-8",
    )
    (tmp_path / "innocent.yml").write_text(
        textwrap.dedent(
            """\
            name: innocent
            on: push
            jobs:
              lint:
                runs-on: ubuntu-latest
                steps:
                  - run: ruff check .
            """
        ),
        encoding="utf-8",
    )
    assert gc.discover_pytest_workflows(tmp_path) == frozenset({"sneaky.yml"})


# ---------------------------------------------------------------------------
# registered_markers (pytest.ini registry read — C-006 read-only authority)
# ---------------------------------------------------------------------------


def test_registered_markers_parses_fixture_ini(tmp_path: Path) -> None:
    ini = tmp_path / "pytest.ini"
    ini.write_text(
        textwrap.dedent(
            """\
            [pytest]
            markers =
                alpha: first marker
                beta_two: second marker (with parens: and colon)
                gamma
            """
        ),
        encoding="utf-8",
    )
    assert gc.registered_markers(ini) == ("alpha", "beta_two", "gamma")


def test_registered_markers_live_registry() -> None:
    """The live pytest.ini registry parses, is duplicate-free, and contains the
    mission-critical marker names."""
    markers = gc.registered_markers()
    assert len(markers) == len(set(markers)), "duplicate marker registrations"
    assert {
        "unit",
        "contract",
        "fast",
        "integration",
        "architectural",
        "windows_ci",
        "quarantine",
    } <= set(markers)

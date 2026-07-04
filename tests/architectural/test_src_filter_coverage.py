"""Path-topology invariants (FR-010c/d, FR-012, FR-013, WP04).

The delivery-topology half of the mission: a ``src/`` change can never silently
skip its suites, and the two hand-mirrored catch-all ``--ignore`` lists cannot
drift from the filter topology. Every check is the PARSED RELATION over the two
path-topology authorities (Decision 8: the dorny filter block and the job
``if:`` gates) — never a literal copy of either mapping (C-002):

  FR-010c  the catch-all ``unmatched`` step's group-reference set == the parsed
           filter-group set (minus the ``any_src`` probe): a group added/removed
           without catch-all wiring reds. AND every named group gates >=1
           test-running job.
  FR-010   NON-VACUOUS boolean guard (the positive arm is live-unprovable
           pre-merge — a self-mapping mechanism PR matches core_misc — so THIS
           fixture assertion IS the permanent guard): ``unmatched = any_src AND
           NOT any(named group)``; a mapped-only change yields ``unmatched=false``
           (NFR-006).
  FR-010d  refactor-stability red-negative: reordering/renaming groups without
           changing the parsed relation stays GREEN (discriminates the parsed
           relation from a literal ordered mirror).
  FR-012   each catch-all ``--ignore`` root is owned (as a positional path) by a
           dedicated shard in the same workflow — no spurious ignore drills a
           coverage hole; reorder red-negative included.
  FR-013   ``on.pull_request.types`` includes ``ready_for_review`` (parsed, not
           line-pinned) so a draft->ready flip re-runs the draft-skipped suites.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
import yaml

from tests.architectural import _gate_coverage as gc
from tests.architectural._workflow_fixtures import filter_workflow, write_workflow

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.architectural

_CI_QUALITY = gc.WORKFLOWS_DIR / "ci-quality.yml"
_ANY_SRC = "any_src"
_FILTER_OUTPUT_RE = re.compile(r"steps\.filter\.outputs\.(\w+)")
_TESTS_ROOT = "tests"
# The catch-all ``--ignore`` roots are DIRECTORY roots; file / node-id positional
# args of dedicated jobs are not ignore-able roots.
_MIN_CATCHALL_IGNORES = 2


# ---------------------------------------------------------------------------
# Pure relation primitives.
# ---------------------------------------------------------------------------


def unmatched_group_refs(workflow_path: Path) -> set[str]:
    """Group names the catch-all ``unmatched`` step enumerates (minus ``any_src``).

    Parsed from the step's ``run`` + ``env`` text so the enumeration is read
    from the workflow's OWN wiring — never a hand-maintained copy.
    """
    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    changes_steps = (data.get("jobs") or {}).get("changes", {}).get("steps") or []
    step = next((s for s in changes_steps if s.get("id") == "unmatched"), None)
    if step is None:
        return set()
    text = str(step.get("run", "")) + " " + str(step.get("env", ""))
    return set(_FILTER_OUTPUT_RE.findall(text)) - {_ANY_SRC}


def compute_unmatched(any_src_hit: bool, group_hits: list[bool]) -> bool:
    """The catch-all boolean: fire ONLY when a src change matched NO named group."""
    return any_src_hit and not any(group_hits)


def _group_is_src_backed(globs: tuple[str, ...]) -> bool:
    """A filter group is SRC-BACKED iff >=1 of its globs targets ``src/``."""
    return any(glob.startswith("src/") for glob in globs)


def src_backed_groups(model: gc.WorkflowModel) -> set[str]:
    """Named filter groups (minus the ``any_src`` probe) that back >=1 ``src/`` glob.

    The catch-all's purpose is "a ``src/**`` change matched by no SRC-BACKED named
    group". Non-src groups (``docs``, ``e2e``) must be excluded from the union so a
    docs- or e2e-only change bundled with an UNMAPPED src change cannot set
    matched=true and mask the src hole (aggregate-squad debbie). Computed from the
    parsed per-group globs the model already exposes — never a hand-maintained list.
    """
    return {
        name
        for name, globs in model.filter_groups.items()
        if name != _ANY_SRC and _group_is_src_backed(globs)
    }


def _is_whole_tree(gate: gc.Gate) -> bool:
    return not gate.paths or all(path.rstrip("/") == _TESTS_ROOT for path in gate.paths)


def _is_dir_root(path: str) -> bool:
    return "::" not in path and not path.endswith(".py")


def catch_all_gates(gates: list[gc.Gate]) -> list[gc.Gate]:
    """Whole-tree gates that defer to dedicated shards via a multi-entry ``--ignore``."""
    return [g for g in gates if _is_whole_tree(g) and len(g.ignores) >= _MIN_CATCHALL_IGNORES]


def dedicated_owned_dirs(gates: list[gc.Gate], *, exclude_job: str) -> set[str]:
    """Directory roots owned as positional paths by dedicated (non-whole-tree) shards."""
    owned: set[str] = set()
    for gate in gates:
        if gate.job == exclude_job or _is_whole_tree(gate):
            continue
        owned |= {p.rstrip("/") for p in gate.paths if _is_dir_root(p)}
    return owned


def catch_all_ignore_violations(gates: list[gc.Gate]) -> list[str]:
    """FR-012: catch-all ``--ignore`` roots not owned by any dedicated shard."""
    out: list[str] = []
    for gate in catch_all_gates(gates):
        ignored = {i.rstrip("/") for i in gate.ignores if _is_dir_root(i)}
        owned = dedicated_owned_dirs(gates, exclude_job=gate.job)
        spurious = ignored - owned
        if spurious:
            out.append(
                f"catch-all {gate.label()} --ignores root(s) {sorted(spurious)} "
                "owned by NO dedicated shard — a coverage hole (nothing runs them)"
            )
    return out


# ---------------------------------------------------------------------------
# Live fixtures.
# ---------------------------------------------------------------------------


def _ci_quality_model() -> gc.WorkflowModel:
    return gc.load_workflow_model(_CI_QUALITY)


def _ci_quality_gates() -> list[gc.Gate]:
    return [g for g in gc.load_gates() if g.workflow == "ci-quality.yml"]


# ---------------------------------------------------------------------------
# FR-010c live: unmatched group-ref set == parsed filter-group set + group->job.
# ---------------------------------------------------------------------------


def test_unmatched_refs_equal_parsed_filter_groups_live() -> None:
    """FR-010c: the catch-all enumerates EXACTLY the SRC-BACKED filter groups.

    A src-backed group added/removed without wiring the catch-all reds — this is
    the parsed-relation binding that makes the fail-closed catch-all NON-vacuous
    (paula CRITICAL: not "every package matched-or-caught"). The expected set is
    the SRC-BACKED groups only: the catch-all fires on "a src change matched by
    no src-backed named group", so non-src groups (``docs``, ``e2e``) are
    excluded — otherwise a docs/e2e change bundled with an unmapped-src change
    sets matched=true and masks the src hole (aggregate-squad debbie).
    """
    model = _ci_quality_model()
    expected = src_backed_groups(model)
    refs = unmatched_group_refs(_CI_QUALITY)
    assert refs == expected, (
        "catch-all unmatched enumeration drifted from the src-backed filter set. "
        f"only-in-catchall={sorted(refs - expected)}, "
        f"only-in-src-backed={sorted(expected - refs)}"
    )
    # Regression naming the exact hole (aggregate-squad debbie): ``docs`` and
    # ``e2e`` are non-src groups; if either re-enters the union, a docs/e2e change
    # riding along with an unmapped-src change would mask the src hole.
    assert "docs" not in refs and "e2e" not in refs


def test_every_named_group_gates_a_test_running_job_live() -> None:
    """FR-010c second arm: each filter group's output gates >=1 test-running job."""
    model = _ci_quality_model()
    filter_names = set(model.filter_groups) - {_ANY_SRC}
    test_jobs = {g.job for g in _ci_quality_gates()}
    ungated = [
        group
        for group in sorted(filter_names)
        if not any(
            group in model.job_gating_groups.get(job, frozenset()) for job in test_jobs
        )
    ]
    assert not ungated, f"filter groups gating no test-running job: {ungated}"


# ---------------------------------------------------------------------------
# FR-010 boolean guard (the permanent fixture proof for the live-unprovable arm).
# ---------------------------------------------------------------------------


def test_unmatched_boolean_semantics() -> None:
    """The catch-all boolean fires ONLY on an unmatched src change."""
    # Positive arm (live-unprovable pre-merge): a src change no named group caught.
    assert compute_unmatched(any_src_hit=True, group_hits=[False, False, False]) is True
    # NFR-006: a change touching ONLY mapped paths => unmatched is false.
    assert compute_unmatched(any_src_hit=True, group_hits=[False, True, False]) is False
    # No src change at all => never fires.
    assert compute_unmatched(any_src_hit=False, group_hits=[False]) is False


def test_docs_e2e_do_not_mask_unmapped_src_live() -> None:
    """aggregate-squad debbie: a docs/e2e hit must NOT mask an unmapped-src change.

    Before the src-backed restriction the catch-all enumerated ``docs`` + ``e2e``,
    so an unmapped ``src/**`` dir bundled with a docs (or e2e) change set
    matched=true and the fail-closed catch-all never fired. Two proofs the hole
    is closed: (1) the live enumeration excludes the two non-src groups, and
    (2) with only src-backed group hits feeding the boolean, an unmapped src
    change (all src-backed groups miss) fires the catch-all even when a docs/e2e
    change rides along.
    """
    refs = unmatched_group_refs(_CI_QUALITY)
    assert "docs" not in refs and "e2e" not in refs
    # The boolean's group_hits are now the SRC-BACKED outputs only; an unmapped
    # src change misses them all => unmatched=true regardless of any docs/e2e hit.
    assert compute_unmatched(any_src_hit=True, group_hits=[False, False]) is True


# ---------------------------------------------------------------------------
# FR-012 live: catch-all --ignore lists mirror the dedicated-shard-owned roots.
# ---------------------------------------------------------------------------


def test_catch_all_ignore_lists_mirror_owned_roots_live() -> None:
    """FR-012: every catch-all ``--ignore`` root is owned by a dedicated shard.

    The ⊇/⊆ shape is deliberate and load-bearing: the whole-tree fast catch-all
    ignores exactly the roots dedicated fast shards own; it does NOT ignore
    integration-owned roots (it legitimately re-selects them under its own
    ``fast`` marker). The coverage-hole direction (an ignore that no shard runs)
    is the real drift this guards.
    """
    violations = catch_all_ignore_violations(_ci_quality_gates())
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# FR-013 live: ready_for_review trigger type.
# ---------------------------------------------------------------------------


def test_ready_for_review_trigger_present_live() -> None:
    """FR-013: a draft->ready flip re-runs the draft-skipped suites (parsed types)."""
    assert "ready_for_review" in _ci_quality_model().pull_request_types


# ---------------------------------------------------------------------------
# Fault-injection + refactor-stability red-negatives.
# ---------------------------------------------------------------------------


def _reorderable_groups() -> dict[str, list[str]]:
    return {
        "sync": ["src/specify_cli/sync/**"],
        "merge": ["src/specify_cli/merge/**"],
        "cli": ["src/specify_cli/cli/**"],
        _ANY_SRC: ["src/**"],
    }


def test_faultinjection_group_missing_from_catchall_reds(tmp_path: Path) -> None:
    """FR-010c: a filter group the catch-all forgot to enumerate reds."""
    groups = _reorderable_groups()
    # ``cli`` is a real group but the unmatched step omits it (drift).
    wf = write_workflow(
        tmp_path,
        filter_workflow(
            groups,
            unmatched_refs=["sync", "merge"],
            gated_jobs={"j": ["sync"]},
        ),
    )
    model = gc.load_workflow_model(wf)
    # Fixture groups are all src-backed (``src/...`` globs), so the expected set
    # is the same relation the live test asserts.
    expected = src_backed_groups(model)
    assert unmatched_group_refs(wf) != expected
    assert (expected - unmatched_group_refs(wf)) == {"cli"}


def test_rednegative_group_reorder_stays_green(tmp_path: Path) -> None:
    """FR-010d: reordering groups (unchanged membership) keeps the invariant green."""
    groups = _reorderable_groups()
    refs = ["sync", "merge", "cli"]
    wf_a = write_workflow(
        tmp_path,
        filter_workflow(groups, unmatched_refs=refs, gated_jobs={"j": ["sync"]}),
        name="a.yml",
    )
    reordered = {"cli": groups["cli"], _ANY_SRC: groups[_ANY_SRC], "sync": groups["sync"], "merge": groups["merge"]}
    wf_b = write_workflow(
        tmp_path,
        filter_workflow(reordered, unmatched_refs=list(reversed(refs)), gated_jobs={"j": ["sync"]}),
        name="b.yml",
    )
    for wf in (wf_a, wf_b):
        model = gc.load_workflow_model(wf)
        assert unmatched_group_refs(wf) == src_backed_groups(model)


def test_faultinjection_spurious_catchall_ignore_reds(tmp_path: Path) -> None:
    """FR-012: a catch-all ignoring a root no dedicated shard owns reds."""
    wf = write_workflow(
        tmp_path,
        """\
        name: fixture
        on: pull_request
        jobs:
          fast-sync:
            runs-on: ubuntu-latest
            steps:
              - run: uv run pytest tests/sync -m fast
          fast-core-misc:
            runs-on: ubuntu-latest
            steps:
              - run: |
                  uv run pytest \\
                    --ignore=tests/sync \\
                    --ignore=tests/ghost_suite \\
                    -m fast
        """,
    )
    violations = catch_all_ignore_violations(gc.parse_workflow(wf))
    assert any("tests/ghost_suite" in v for v in violations), violations


def test_rednegative_ignore_reorder_stays_green(tmp_path: Path) -> None:
    """FR-012 red-negative: reordering ``--ignore`` entries keeps the mirror green."""
    body = """\
        name: fixture
        on: pull_request
        jobs:
          fast-sync:
            runs-on: ubuntu-latest
            steps:
              - run: uv run pytest tests/sync -m fast
          fast-merge:
            runs-on: ubuntu-latest
            steps:
              - run: uv run pytest tests/merge -m fast
          fast-core-misc:
            runs-on: ubuntu-latest
            steps:
              - run: |
                  uv run pytest \\
                    {order} \\
                    -m fast
        """
    wf_a = write_workflow(
        tmp_path,
        body.format(order="--ignore=tests/sync \\\n                    --ignore=tests/merge"),
        name="a.yml",
    )
    wf_b = write_workflow(
        tmp_path,
        body.format(order="--ignore=tests/merge \\\n                    --ignore=tests/sync"),
        name="b.yml",
    )
    assert catch_all_ignore_violations(gc.parse_workflow(wf_a)) == []
    assert catch_all_ignore_violations(gc.parse_workflow(wf_b)) == []


def test_faultinjection_missing_ready_for_review_reds(tmp_path: Path) -> None:
    """FR-013: a workflow whose pull_request types omit ready_for_review reds."""
    wf = write_workflow(
        tmp_path,
        """\
        name: fixture
        on:
          pull_request:
            types: [opened, synchronize]
        jobs:
          j:
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
        """,
    )
    assert "ready_for_review" not in gc.load_workflow_model(wf).pull_request_types

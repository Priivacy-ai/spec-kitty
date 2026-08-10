"""Architectural guards for CI path-filter ownership."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architectural import _gate_coverage as gc

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"
_COLLECT_TIMEOUT_SECONDS = 240


def _load_workflow() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return data


def _path_filters(data: dict[str, Any]) -> dict[str, list[str]]:
    filter_step = next(step for step in data["jobs"]["changes"]["steps"] if step.get("id") == "filter")
    parsed: dict[str, list[str]] = yaml.safe_load(filter_step["with"]["filters"])
    return parsed


def _job_run_script(data: dict[str, Any], job_name: str, step_name: str) -> str:
    step = next(step for step in data["jobs"][job_name]["steps"] if step.get("name") == step_name)
    return str(step["run"])


def _job(data: dict[str, Any], job_name: str) -> dict[str, Any]:
    return dict(data["jobs"][job_name])


# T021 (mission review-cycle-verdict-seam-rebuild-01KZ2W7W, WP05): a shard job
# must not condition its own execution on a predecessor's `.result` — it
# should still run and report its own outcome regardless of whether the
# predecessor passed or failed. This regex catches both classes of gate this
# WP removed: `needs.<job>.result != 'failure'` (Class 1, e.g. a coverage
# shard gated on kernel-tests/fast-tests-status) and `needs.<job>.result ==
# 'success'` (Class 2, an integration-tests-* job gated on its fast-tests-*
# counterpart).
_RESULT_GATE_PATTERN = re.compile(r"needs\.[\w-]+\.result\s*(?:!=\s*'failure'|==\s*'success')")

# Single named, justified exception (see the DoD in
# kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/tasks/WP05-ci-shard-independence.md):
# ``consumer-compatibility``'s ``needs.build-wheel.result == 'success'`` gate
# is a release-packaging aggregator dependency (a wheel it consumes), not a
# coverage-shard result-gate the way the removed edges were — build-wheel
# produces the artifact consumer-compatibility installs, so gating on its
# result is a genuine "don't bother installing a wheel that was never built"
# check, not the redundant "predecessor's test outcome shouldn't block my own
# report" coupling this test exists to forbid. This is a single named
# constant, not a general allowlist: any job matching the pattern that is NOT
# named here fails the test below, and adding a name here requires the same
# explicit justification as this comment.
_NON_SHARD_AGGREGATOR_EXCEPTIONS = frozenset({"consumer-compatibility"})


def _find_result_gated_jobs(jobs: dict[str, Any]) -> dict[str, str]:
    """Return ``{job_name: if_expr}`` for jobs gating on a predecessor's ``.result``.

    A job's ``if:`` arrives here, post-PyYAML-parse, as one of three shapes: a
    plain string, a folded ``>-`` block scalar (also just a ``str`` once
    parsed), or absent (key missing, defaults to always-run) — all three are
    handled uniformly by coercing to ``str`` and skipping ``None``.
    """
    offending: dict[str, str] = {}
    for job_name, job in jobs.items():
        if job_name in _NON_SHARD_AGGREGATOR_EXCEPTIONS:
            continue
        if_expr = job.get("if") if isinstance(job, dict) else None
        if if_expr is None:
            continue
        if _RESULT_GATE_PATTERN.search(str(if_expr)):
            offending[job_name] = str(if_expr)
    return offending


# Marker selector shared by the legacy catch-all universe and every shard
# collection in test_core_misc_shards_plus_e2e_owner_cover_legacy_selection.
_MARKER_EXPR = "not windows_ci and (git_repo or integration or architectural)"

# The legacy catch-all core-misc selection (the pre-shard universe): every
# ``--ignore`` it carried plus its marker selector. Hoisted to a module
# constant so the ~117-line test body reads as intent, not literal data.
#
# ``--ignore=tests/docs`` added 2026-08-05 (PR #3204, operator decision): the
# #2359 docs over-coverage fail-safe was retired, so the `misc` shard no
# longer runs tests/docs and this "intended selection" baseline must not
# expect it either -- tests/docs runs ONLY in the dedicated `fast-tests-docs`
# job now (see the ci-quality.yml fast-tests-docs job header for the
# accepted tradeoff).
_LEGACY_CORE_MISC_ARGS: list[str] = [
    "--ignore=tests/doctrine",
    "--ignore=tests/kernel",
    "--ignore=tests/status",
    "--ignore=tests/specify_cli/status",
    "--ignore=tests/sync",
    "--ignore=tests/merge",
    "--ignore=tests/missions",
    "--ignore=tests/post_merge",
    "--ignore=tests/release",
    "--ignore=tests/review",
    "--ignore=tests/next",
    "--ignore=tests/specify_cli/next",
    "--ignore=tests/lanes",
    "--ignore=tests/test_dashboard",
    "--ignore=tests/upgrade",
    "--ignore=tests/cli",
    "--ignore=tests/runtime",
    "--ignore=tests/charter",
    "--ignore=tests/agent",
    "--ignore=tests/docs",
    "-m",
    _MARKER_EXPR,
]

# The per-shard path/ignore universes whose union must cover the legacy
# selection. Each entry is collected with the same marker selector appended.
_SHARD_COMMANDS: list[list[str]] = [
    ["tests/adversarial", "tests/architectural", "tests/architecture", "tests/lint"],
    ["tests/integration"],
    [
        "tests/specify_cli/migration",
        "tests/specify_cli/invocation",
        "tests/specify_cli/test_charter_activate_cli.py",
    ],
    [
        "tests/specify_cli",
        "--ignore=tests/specify_cli/migration",
        "--ignore=tests/specify_cli/invocation",
        "--ignore=tests/specify_cli/test_charter_activate_cli.py",
        "--ignore=tests/specify_cli/status",
        "--ignore=tests/specify_cli/next",
    ],
    ["tests/auth", "tests/audit", "tests/git_ops", "tests/git", "tests/cli_gate"],
    [
        "tests/calibration",
        "tests/ci",
        "tests/concurrency",
        "tests/contract",
        "tests/core",
        "tests/cross_branch",
        # tests/docs REMOVED 2026-08-05 (PR #3204, operator decision): the
        # #2359 docs over-coverage fail-safe was retired from the `misc`
        # shard, so it must not appear in the "new" (post-shard) universe
        # either -- see the matching --ignore=tests/docs added to
        # _LEGACY_CORE_MISC_ARGS above, which keeps this comparison coherent
        # (shards ∪ e2e == the intended selection, and the intended selection
        # no longer includes docs in core-misc).
        "tests/doctor",
        "tests/init",
        "tests/migration",
        "tests/mission_runtime",
        "tests/packaging",
        "tests/policy",
        "tests/readiness",
        "tests/regression",
        "tests/regressions",
        "tests/research",
        "tests/retrospective",
        "tests/saas",
        "tests/stress",
        "tests/tasks",
        "tests/unit",
    ],
]


def _collect_nodes(args: list[str]) -> set[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-qq", *args],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        # Generous wall-clock (_COLLECT_TIMEOUT_SECONDS): these `--collect-only`
        # subprocesses run several at a time (see the worker-capped
        # ThreadPoolExecutor below), so on a CPU-constrained CI runner a single
        # collection's wall-clock can stretch well past a tight cap even though
        # it is fast in isolation.
        timeout=_COLLECT_TIMEOUT_SECONDS,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line}


def test_missions_filter_includes_missions_package_and_tests() -> None:
    """Mission package tests must both trigger and run the mission test slice."""
    data = _load_workflow()
    missions_filter = set(_path_filters(data)["missions"])
    assert "src/specify_cli/missions/**" in missions_filter
    assert "tests/fixtures/missions/**" in missions_filter
    assert "tests/specify_cli/missions/**" in missions_filter

    fast_run = _job_run_script(data, "fast-tests-missions", "Run fast tests — missions")
    integration_run = _job_run_script(
        data,
        "integration-tests-missions",
        "Run integration tests — missions",
    )
    assert "tests/specify_cli/missions/" in fast_run
    assert "tests/specify_cli/missions/" in integration_run


def test_lanes_filter_and_jobs_include_lanes_package_tests() -> None:
    """Lane package tests must both trigger and run the lane test slice."""
    data = _load_workflow()
    lanes_filter = set(_path_filters(data)["lanes"])
    assert "tests/specify_cli/lanes/**" in lanes_filter

    fast_run = _job_run_script(data, "fast-tests-lanes", "Run fast tests — lanes")
    integration_run = _job_run_script(
        data,
        "integration-tests-lanes",
        "Run integration tests — lanes",
    )
    assert "tests/specify_cli/lanes/" in fast_run
    assert "tests/specify_cli/lanes/" in integration_run


def _glob_matches(pattern: str, path: str) -> bool:
    """Approximate GitHub Actions / dorny ``on.paths``-style glob matching.

    ``**`` matches any sequence of characters including path separators (zero
    or more intervening segments); a single ``*`` matches within one segment
    (never crosses ``/``). Sufficient for asserting concrete example paths
    against the corpus glob set below -- not a general-purpose glob engine.
    """
    escaped = re.escape(pattern)
    escaped = escaped.replace(r"\*\*", "\x00DOUBLESTAR\x00")
    escaped = escaped.replace(r"\*", "[^/]*")
    escaped = escaped.replace("\x00DOUBLESTAR\x00", ".*")
    return re.fullmatch(escaped, path) is not None


def test_corpus_filter_claims_the_discrete_glob_set() -> None:
    """The `corpus` dorny filter must claim the exact T001/T002 glob set.

    Mirrors the `on.paths` trigger allowlists (Gate 0, checked separately by
    test_ci_corpus_trigger_completeness.py) -- discrete globs only, never
    bare `kitty-specs/**` or `status.events.jsonl` (C-001).
    """
    data = _load_workflow()
    corpus_filter = set(_path_filters(data)["corpus"])
    assert corpus_filter == {
        "packs/**",
        "kitty-specs/**/spec.md",
        "kitty-specs/**/plan.md",
        "kitty-specs/**/tasks/**",
        "kitty-specs/**/contracts/**",
        "kitty-specs/**/acceptance-matrix.json",
        ".kittify/charter/**",
        ".kittify/glossaries/**",
        ".kittify/doctrine/**",
        ".kittify/release/downstream-verified.json",
    }


def test_corpus_filter_selects_a_packs_built_in_only_diff() -> None:
    """SC-001: a packs/built-in/**-only diff must select the corpus group."""
    data = _load_workflow()
    corpus_filter = _path_filters(data)["corpus"]
    changed_path = "packs/built-in/agent_profiles/implementer-ivan.agent.yaml"
    assert any(_glob_matches(g, changed_path) for g in corpus_filter)


def test_corpus_filter_selects_a_narrow_kitty_specs_spec_leaf() -> None:
    """SC-001: a narrow kitty-specs/<mission>/spec.md diff selects corpus."""
    data = _load_workflow()
    corpus_filter = _path_filters(data)["corpus"]
    changed_path = "kitty-specs/example-mission-01ABCDEF/spec.md"
    assert any(_glob_matches(g, changed_path) for g in corpus_filter)


def test_corpus_filter_does_not_select_status_events_churn() -> None:
    """SC-002: routine WP status-event churn must NOT select the corpus group.

    Guards C-001 -- a bare `kitty-specs/**` or `status.events.jsonl` glob
    would fire on every WP status transition, defeating the point of a
    narrow corpus trigger.
    """
    data = _load_workflow()
    corpus_filter = _path_filters(data)["corpus"]
    changed_path = "kitty-specs/example-mission-01ABCDEF/status.events.jsonl"
    assert not any(_glob_matches(g, changed_path) for g in corpus_filter)


def test_corpus_filter_globs_are_all_non_src() -> None:
    """M2: every corpus glob must stay non-src so ci_topology_census.json and
    the `unmatched` catch-all loop (both src/specify_cli-scoped) never need to
    change for this non-src data group."""
    data = _load_workflow()
    corpus_filter = _path_filters(data)["corpus"]
    assert all(not g.startswith("src/") for g in corpus_filter)


def test_next_filter_includes_canonical_runtime_packages() -> None:
    """The next trigger must watch the canonical runtime, not just the shim.

    src/specify_cli/next/ is a deprecation shim (removed in 3.3.0); the
    canonical runtime lives in src/runtime/next/ and depends on
    src/mission_runtime/. Both must trigger the next test suites.
    """
    data = _load_workflow()
    next_filter = set(_path_filters(data)["next"])
    assert "src/runtime/next/**" in next_filter
    assert "src/mission_runtime/**" in next_filter


def test_next_jobs_measure_canonical_runtime_coverage() -> None:
    """Both next suites must measure src/runtime/next, not only the shim."""
    data = _load_workflow()
    fast_run = _job_run_script(data, "fast-tests-next", "Run fast tests — next")
    integration_run = _job_run_script(
        data,
        "integration-tests-next",
        "Run integration tests — next",
    )
    assert "--cov=src/runtime/next" in fast_run
    assert "--cov=src/runtime/next" in integration_run


def test_diff_coverage_critical_paths_include_canonical_runtime() -> None:
    """The enforced diff-coverage gate must include the canonical runtime."""
    run_script = _job_run_script(
        _load_workflow(),
        "diff-coverage",
        "diff-coverage (critical-path, enforced)",
    )
    assert "'src/runtime/next/*'" in run_script
    assert "'src/mission_runtime/*'" in run_script


def test_diff_coverage_critical_paths_all_resolve_to_existing_files() -> None:
    """Every diff-coverage ``--include`` critical-path entry must resolve to a real file.

    Guards #2443: a critical-path allowlist entry that names no existing file
    silently contributes nothing to the enforced gate, so a moved/renamed/phantom
    module drops coverage enforcement with no signal. ``mission_detection.py`` was
    exactly this — a phantom that never existed in git history yet sat in the
    allowlist looking enforced.

    Reuses the canonical allowlist parser
    (``_gate_coverage._diff_cover_critical_paths``) — deliberately NOT a second
    hand-rolled shell-array parser (charter: single canonical authority). Per entry:
    a **glob** (contains ``*``) is expanded with ``Path.glob`` and must match >=1
    file (this also catches a vacuous glob that expands to zero files — the retired
    ``src/specify_cli/next/*`` rot precedent); a **literal** must ``.exists()``.
    """
    run_script = _job_run_script(
        _load_workflow(),
        "diff-coverage",
        "diff-coverage (critical-path, enforced)",
    )
    entries = gc._diff_cover_critical_paths(run_script)
    assert entries, "no critical_paths=( ... ) entries parsed from the enforced diff-coverage step — the canonical parser found nothing (workflow shape drifted?)"

    unresolved: list[str] = []
    for entry in entries:
        if "*" in entry:
            if not any(_REPO_ROOT.glob(entry)):
                unresolved.append(entry)
        elif not (_REPO_ROOT / entry).exists():
            unresolved.append(entry)

    assert not unresolved, (
        f"diff-coverage --include critical-path entries resolve to no file on disk (stale/phantom allowlist -> silent coverage-enforcement rot): {unresolved}"
    )


def test_execution_context_parity_ratchet_runs_unconditionally() -> None:
    """The CWD parity ratchet must still run — now unconditionally, in the pole.

    Re-pinned for mission ci-topology-shrink (FR-005/FR-013), then re-pinned
    again for mission ci-health-charter-path-and-arch-shard-01KWRTB2 (#2397)
    when the single ``architectural`` shard was split into three
    marker-routed shards (``arch_shard_1/2/3``). WP03 (ci-topology-shrink)
    removed the exec-context special-path block that used to run
    ``test_execution_context_parity.py`` inside ``integration-tests-core-misc``
    only when ``core_misc != 'true' AND execution_context == 'true'``. The
    parity gate now lives in the standalone, always-on ``arch-adversarial``
    pole: every one of its three legs collects ``tests/architectural`` (where
    the parity file lives, per ``paths`` staying identical across all three
    shards) under the ``git_repo``/``architectural`` marker the parity tests
    carry, and the job is ``if: always()`` with no filter gate — so an
    execution-context change (indeed ANY change) still runs the ratchet, more
    strongly than the old conditional path. Behavioral intent preserved: the
    parity ratchet is never skippable, regardless of which shard collects it.
    """
    data = _load_workflow()
    arch_job = _job(data, "arch-adversarial")

    # Always-on: no result-gated or path/status-gated skip can drop the ratchet.
    # The only permitted guards are the pr:deferred / pr:skip-ci full-CI-block
    # labels (ddac71ebc), which block ALL PR workflows but cannot mask this pole
    # via a change filter.
    assert gc.gate_is_always_on_modulo_full_ci_block(str(arch_job["if"]), require_always=True), (
        f"arch-adversarial pole gained a masking filter: if={arch_job['if']!r}"
    )

    # Every matrix leg collects the tests/architectural tree, which owns
    # test_execution_context_parity.py — so the parity ratchet is in-scope no
    # matter which arch_shard_N marker ends up selecting it.
    arch_legs = arch_job["strategy"]["matrix"]["include"]
    assert arch_legs, "arch-adversarial matrix must not be empty"
    for entry in arch_legs:
        assert "tests/architectural" in str(entry["paths"]), (
            f"matrix leg {entry.get('shard')!r} dropped tests/architectural from its paths — the parity ratchet could fall out of scope"
        )
    parity_file = _REPO_ROOT / "tests" / "architectural" / "test_execution_context_parity.py"
    assert parity_file.exists(), "the CWD parity ratchet file moved out of tests/architectural — update this guard so the arch-adversarial pole still collects it"

    # The pole runs under a marker that positively selects the parity tests'
    # architectural/git_repo markers, so collection is not silently empty.
    run_script = _job_run_script(
        data,
        "arch-adversarial",
        "Run architectural + adversarial suite (always-on pole)",
    )
    assert "git_repo or integration or architectural" in run_script


def test_core_misc_integration_is_sharded_and_parallelized() -> None:
    """The slow core-misc integration bucket must stay split and parallel.

    Re-pinned for mission ci-topology-shrink (FR-005/FR-013): the
    ``architectural`` shard was EXTRACTED from this matrix into the standalone
    always-on ``arch-adversarial`` pole (de-serialized), so it is no longer an
    ``integration-tests-core-misc`` shard. The remaining five shards must stay
    split and parallel, and the extracted arch pole must still run.

    Re-pinned again for mission ci-health-charter-path-and-arch-shard-01KWRTB2
    (#2397): the extracted pole itself is now a 3-shard matrix
    (``arch_shard_1/2/3``) rather than the single ``architectural`` shard, so
    this asserts the pole's matrix is non-empty and marker-routed instead of
    hard-pinning the retired single shard name.
    """
    data = _load_workflow()
    job = _job(data, "integration-tests-core-misc")
    matrix = job["strategy"]["matrix"]["include"]
    shard_names = {entry["shard"] for entry in matrix}

    assert shard_names == {
        "integration",
        "specify-cli-heavy",
        "specify-cli-rest",
        "auth-audit-git",
        "misc",
    }
    # The extracted architectural pole must not have vanished — it lives in the
    # always-on ``arch-adversarial`` job now (its de-serialization is pinned by
    # test_arch_pole_deserialized.py; here we pin that the pole still exists
    # and is the 3-way marker-routed split mission 01KWRTB2 introduced).
    arch_shards = {entry["shard"] for entry in _job(data, "arch-adversarial")["strategy"]["matrix"]["include"]}
    assert arch_shards == {"arch_shard_1", "arch_shard_2", "arch_shard_3"}

    run_script = _job_run_script(
        data,
        "integration-tests-core-misc",
        "Run integration tests — core misc",
    )
    assert "-n auto --dist loadfile" in run_script
    assert "--durations=50" in run_script


def test_ci_quality_guards_trigger_core_misc_validation() -> None:
    """CI workflow and architectural guard edits must run the validating shard."""
    core_misc_filter = set(_path_filters(_load_workflow())["core_misc"])
    assert ".github/workflows/ci-quality.yml" in core_misc_filter
    assert "tests/architectural/**" in core_misc_filter


def test_core_misc_shards_plus_e2e_owner_cover_legacy_selection() -> None:
    """The shard split must not drop tests covered by the legacy catch-all job.

    This compares the legacy catch-all node universe against the union of the
    new shard universes; the invariant is ``legacy_nodes - new_nodes == {}``
    over IDENTICAL path/marker universes. The 8 distinct ``--collect-only``
    subprocesses are launched concurrently (each is I/O-bound, waiting on a
    child pytest process) instead of serially. De-duplicating/parallelizing the
    distinct collections this way leaves node→selector attribution unchanged:
    every collection runs with the exact same args it ran with serially, and is
    bucketed back to ``legacy`` vs ``new`` by an explicit key — concurrency only
    overlaps the waits, it never merges or reattributes node sets.
    """
    marker_args = ["-m", _MARKER_EXPR]
    e2e_args = [
        "tests/e2e",
        "tests/cross_cutting",
        "-m",
        "not distribution and not windows_ci",
    ]

    # (bucket, args) for each distinct collection. "legacy" feeds the catch-all
    # universe; "new" feeds the union of shard universes. Attribution is fixed
    # here, before any concurrency, so parallel execution cannot change it.
    collections: list[tuple[str, list[str]]] = [("legacy", _LEGACY_CORE_MISC_ARGS)]
    collections.extend(("new", [*command, *marker_args]) for command in _SHARD_COMMANDS)
    collections.append(("new", e2e_args))

    # Each _collect_nodes call spawns a child pytest process and blocks on it;
    # run them concurrently so the wall-clock is bounded by the slowest single
    # collection instead of their serial sum. Cap concurrency at the CPU count
    # (min 2): launching all of them at once oversubscribes a 2-core CI runner,
    # which inflates each child's wall-clock and made a single collection blow
    # its per-subprocess timeout. Pacing to the available cores keeps each
    # collection fast without serialising the whole set.
    max_workers = min(len(collections), max(2, os.cpu_count() or 2))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(
            executor.map(lambda item: (item[0], _collect_nodes(item[1])), collections),
        )

    legacy_nodes: set[str] = set()
    new_nodes: set[str] = set()
    for bucket, nodes in results:
        (legacy_nodes if bucket == "legacy" else new_nodes).update(nodes)

    missing = sorted(legacy_nodes - new_nodes)
    assert not missing, "Shard split dropped legacy core-misc tests:\n" + "\n".join(
        missing[:20],
    )


def test_core_misc_excludes_e2e_and_cross_cutting_suites() -> None:
    """E2E and cross-cutting suites belong to e2e-cross-cutting, not core-misc."""
    data = _load_workflow()
    path_filters = _path_filters(data)
    assert "tests/e2e/**" not in path_filters["core_misc"]
    assert "tests/cross_cutting/**" not in path_filters["core_misc"]
    assert "tests/e2e/**" in path_filters["e2e"]
    assert "tests/cross_cutting/**" in path_filters["e2e"]

    # Re-pinned for mission ci-topology-shrink (FR-003): the fast core-misc job
    # was split into a shard matrix and its per-run ``--ignore`` list moved from
    # a literal in the run step into each shard's ``matrix.ignore_args``. The
    # behavioral intent is unchanged — the whole-tree residual ``core-misc``
    # shard must still exclude e2e/cross_cutting — just asserted at the new
    # structural location. The run step now interpolates ``${{ matrix.ignore_args }}``.
    fast_run = _job_run_script(data, "fast-tests-core-misc", "Run fast tests — core misc")
    assert "${{ matrix.ignore_args }}" in fast_run
    fast_job = _job(data, "fast-tests-core-misc")
    fast_core_misc_shard = next(entry for entry in fast_job["strategy"]["matrix"]["include"] if entry["shard"] == "core-misc")
    fast_ignores = str(fast_core_misc_shard["ignore_args"])
    assert "--ignore=tests/e2e" in fast_ignores
    assert "--ignore=tests/cross_cutting" in fast_ignores

    job = _job(data, "integration-tests-core-misc")
    matrix = job["strategy"]["matrix"]["include"]
    matrix_text = "\n".join(f"{entry.get('paths', '')}\n{entry.get('ignore_args', '')}" for entry in matrix)
    assert "tests/e2e" not in matrix_text
    assert "tests/cross_cutting" not in matrix_text


def test_e2e_cross_cutting_runs_independently_of_fast_fanout() -> None:
    """The dedicated e2e job should not wait on unrelated fast-test shards."""
    data = _load_workflow()
    job = _job(data, "e2e-cross-cutting")
    assert job["needs"] == ["changes"]

    condition = str(job["if"])
    assert "needs.changes.outputs.e2e == 'true'" in condition
    assert "needs.changes.outputs.core_misc == 'true'" in condition
    assert "needs.changes.outputs.execution_context == 'true'" in condition

    path_filters = _path_filters(data)
    assert ".github/workflows/ci-quality.yml" in path_filters["e2e"]

    run_script = _job_run_script(
        data,
        "e2e-cross-cutting",
        "[ENFORCED] Run e2e and cross_cutting tests with coverage",
    )
    assert "tests/e2e/ tests/cross_cutting/" in run_script
    assert "--durations=50" in run_script


def test_e2e_cross_cutting_failures_are_quality_gated() -> None:
    """The owner job for e2e/cross-cutting coverage must block merges on failure.

    Post-FR-011 (mission ci-suite-map-bind WP03) the quality-gate verdict is
    computed by ``scripts/ci/quality_gate_decision.py`` over the FULL needs
    context (``toJSON(needs)``): membership in ``needs:`` IS the blocking
    relation (a failed/cancelled needs job always fails the gate), so the old
    literal per-job ``needs.<job>.result`` read this test used to pin cannot
    silently omit a job anymore.
    """
    quality_gate = _job(_load_workflow(), "quality-gate")
    assert "e2e-cross-cutting" in quality_gate["needs"]

    decision_step = next(step for step in quality_gate["steps"] if step.get("name") == "Evaluate quality-gate decision")
    assert decision_step["env"]["NEEDS_JSON"] == "${{ toJSON(needs) }}"
    assert "scripts/ci/quality_gate_decision.py" in decision_step["run"]
    # The decision script pipes into ``tee -a "$GITHUB_STEP_SUMMARY"``. Under
    # GitHub's default ``bash -e {0}`` (no pipefail) the pipe returns tee's
    # always-zero exit, SWALLOWING the script's blocking (exit 1) / contract
    # (exit 2) verdict — the gate would be vacuous. ``shell: bash`` makes
    # GitHub run ``bash --noprofile --norc -eo pipefail {0}`` so the script's
    # non-zero propagates through the pipe. Pin it so the mask cannot return.
    assert decision_step.get("shell") == "bash", (
        "quality-gate decision step must set ``shell: bash`` so pipefail is enabled and the script's non-zero exit is not swallowed by ``| tee``"
    )


@pytest.mark.parametrize("step_id", ["bandit", "pip_audit"])
def test_security_scan_steps_set_pipefail(step_id: str) -> None:
    """Bandit and pip-audit must ``set -o pipefail`` so the security gate isn't vacuous.

    Both scans pipe into ``| tee out/reports/...``. Under GitHub's default
    ``bash -e {0}`` (no pipefail) the pipe returns tee's always-zero exit, so
    ``steps.<id>.outcome`` is ``success`` even when the scan finds issues — and
    the downstream ``[ENFORCED] Fail job if security checks failed`` arm (which
    tests ``steps.bandit.outcome != 'success'``) never fires. ``set -o pipefail``
    makes each step's exit reflect the scan's real exit (tee still writes the
    report). Same swallowed-exit class the mission fixed for its own
    quality-gate decision step (aggregate-squad alphonso). Parse-only guard.
    """
    step = next(step for step in _job(_load_workflow(), "lint")["steps"] if step.get("id") == step_id)
    assert "set -o pipefail" in str(step["run"]), (
        f"security scan step '{step_id}' must ``set -o pipefail`` so its ``| tee`` pipeline does not swallow a non-zero scan exit (vacuous security gate)"
    )


def test_no_shard_gates_execution_on_a_predecessor_result() -> None:
    """No shard job may condition its own execution on a predecessor's ``.result``.

    T021 (mission review-cycle-verdict-seam-rebuild-01KZ2W7W, WP05): guards
    against silently reintroducing the coupling this WP removed — e.g. a new
    shard added by copy-pasting an existing job's ``if:`` block with its
    ``.result`` gate left intact. A job may still declare a real ``needs:``
    artifact dependency (checkout/cache/coverage-XML handoff); what it must
    NOT do is skip its own execution — and therefore its own reported result —
    because a predecessor failed or didn't succeed. See
    kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/tasks/WP05-ci-shard-independence.md.
    """
    data = _load_workflow()
    offending = _find_result_gated_jobs(data["jobs"])
    assert not offending, (
        "job(s) still gate their own execution on a predecessor's .result "
        "(a shard must run and report its own outcome regardless of whether "
        f"an upstream shard passed or failed): {offending}"
    )


def test_result_gate_checker_catches_a_reintroduced_gate() -> None:
    """Synthetic-poison proof that ``_find_result_gated_jobs`` reds on a new gate.

    Permanent regression proof for T021: constructs a minimal synthetic
    ``jobs`` mapping containing a deliberately (re)introduced Class 1 style
    gate (``!= 'failure'``, folded ``if: >-`` block shape) and a Class 2 style
    gate (``== 'success'``), alongside an ungated job and a job with no ``if:``
    key at all, and confirms the checker flags exactly the two poisoned jobs.
    This is what proves the checker actually catches the regression it exists
    to prevent — not merely that it currently passes against an
    already-fixed workflow.
    """
    poisoned_jobs = {
        "fast-tests-example": {
            "if": ("always()\n&& (needs.changes.outputs.example == 'true' || github.event_name == 'push')\n&& needs.fast-tests-status.result != 'failure'\n"),
        },
        "integration-tests-example": {
            "if": ("always()\n&& (needs.changes.outputs.example == 'true' || github.event_name == 'push')\n&& needs.fast-tests-example.result == 'success'\n"),
        },
        "clean-job": {
            "if": "always() && (needs.changes.outputs.example == 'true' || github.event_name == 'push')",
        },
        "no-if-job": {},
        "consumer-compatibility": {
            "if": "always() && needs.changes.outputs.release == 'true' && needs.build-wheel.result == 'success'",
        },
    }
    offending = _find_result_gated_jobs(poisoned_jobs)
    assert set(offending) == {"fast-tests-example", "integration-tests-example"}

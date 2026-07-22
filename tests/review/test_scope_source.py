"""Tests for ``specify_cli.review.scope_source`` — WP02 of mission
``doctrine-controlled-transition-gates-01KY51Z7`` (epic #2535 half A).

Covers T008 (port contract + both impls + no-config), T009 (portable-verdict
baseline-relative fidelity fixtures), and T010 (behaviour-parity micro-golden
for the internal scope derivation). ATDD red-first: authored against the
not-yet-written ``scope_source`` module.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.review import pre_review_gate, scope_source
from specify_cli.review.baseline import BaselineTestResult, diff_baseline
from specify_cli.review.scope_source import (
    DeclaredCommandScopeSource,
    GateCoverageScopeSource,
    RawRunResult,
    ScopeSource,
)

pytestmark = [pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Port contract (T008)
# ---------------------------------------------------------------------------


def test_gate_coverage_scope_source_satisfies_the_port(tmp_path: Path) -> None:
    impl = GateCoverageScopeSource(repo_root=tmp_path)
    assert isinstance(impl, ScopeSource)


def test_declared_command_scope_source_satisfies_the_port(tmp_path: Path) -> None:
    impl = DeclaredCommandScopeSource(repo_root=tmp_path)
    assert isinstance(impl, ScopeSource)


@pytest.mark.parametrize(
    "impl",
    [GateCoverageScopeSource(repo_root=Path(".")), DeclaredCommandScopeSource(repo_root=Path("."))],
)
def test_neither_impl_exposes_a_changed_files_method(impl: ScopeSource) -> None:
    """SSOT-off-port guard (FR-001): ``changed_files`` is the shared
    merge-base+diff input passed to the gate, never a per-impl method — a
    future contributor "helpfully" adding it back would re-introduce the
    exact divergence risk this port design forbids."""
    assert not hasattr(impl, "changed_files")


def test_port_declares_exactly_the_three_repo_shape_methods() -> None:
    port_methods = {
        name for name in vars(ScopeSource) if not name.startswith("_")
    } & {"test_command", "file_to_scope", "parse_results", "changed_files"}
    assert port_methods == {"test_command", "file_to_scope", "parse_results"}


# ---------------------------------------------------------------------------
# GateCoverageScopeSource (T008)
# ---------------------------------------------------------------------------


def test_gate_coverage_test_command_includes_junitxml_and_q(tmp_path: Path) -> None:
    command = GateCoverageScopeSource(repo_root=tmp_path).test_command()

    assert command is not None
    assert command[-1] == "-q"
    assert any(arg.startswith("--junitxml=") for arg in command)


_MICRO_GOLDEN_GROUPS: dict[str, tuple[str, ...]] = {
    "status": ("src/specify_cli/status/**", "tests/status/**"),
    "git": ("src/specify_cli/git/**",),
    "governance": ("src/specify_cli/governance_file.py",),
    "core_misc": ("src/**",),
}
_MICRO_GOLDEN_ROUTING: dict[str, pre_review_gate._CompositeRoute] = {
    "git": (None, None, ("tests/git", "tests/git_ops")),
}


def _gate_coverage_impl(repo_root: Path) -> GateCoverageScopeSource:
    return GateCoverageScopeSource(
        repo_root=repo_root,
        filter_groups_override=_MICRO_GOLDEN_GROUPS,
        composite_routing_override=_MICRO_GOLDEN_ROUTING,
    )


def test_gate_coverage_file_to_scope_reproduces_per_shard_census_narrowing(tmp_path: Path) -> None:
    """A ``status``-shaped file: per-shard ``tests/**`` glob contributes its
    own test target directly (mirrors the spec's own grounding example)."""
    impl = _gate_coverage_impl(tmp_path)

    targets = impl.file_to_scope("src/specify_cli/status/emit.py")

    assert set(targets) == {"tests/status"}


def test_gate_coverage_file_to_scope_reproduces_composite_cone_narrowing(tmp_path: Path) -> None:
    """A composite-shaped file resolves via the composite dir's committed
    cone_roots, not a dorny test glob (``git`` carries none)."""
    impl = _gate_coverage_impl(tmp_path)

    targets = impl.file_to_scope("src/specify_cli/git/foo.py")

    assert set(targets) == {"tests/git", "tests/git_ops"}


# ---------------------------------------------------------------------------
# scope_breakdown — the census breakdown behind file_to_scope (metadata fidelity,
# mission ``doctrine-controlled-transition-gates-01KY51Z7`` WP09 remediation)
# ---------------------------------------------------------------------------


def test_gate_coverage_satisfies_the_scope_breakdown_refinement(tmp_path: Path) -> None:
    """Only the census-narrowing impl exposes the breakdown refinement — that
    membership is exactly what tells the engine an empty scope is a coverage
    gap (vs. a whole-suite ``DeclaredCommandScopeSource`` run)."""
    from specify_cli.review.scope_source import ScopeBreakdownSource

    assert isinstance(GateCoverageScopeSource(repo_root=tmp_path), ScopeBreakdownSource)
    assert not isinstance(DeclaredCommandScopeSource(repo_root=tmp_path), ScopeBreakdownSource)


def test_gate_coverage_scope_breakdown_records_per_shard_group(tmp_path: Path) -> None:
    """A per-shard file records its group in ``matched_shard_groups`` (the
    metadata the inverted hook must preserve byte-for-byte, NFR-001)."""
    breakdown = _gate_coverage_impl(tmp_path).scope_breakdown("src/specify_cli/status/emit.py")

    assert breakdown.test_targets == ("tests/status",)
    assert breakdown.matched_shard_groups == ("status",)
    assert breakdown.matched_composite_dirs == ()
    assert breakdown.contributes_scope is True


def test_gate_coverage_scope_breakdown_records_composite_dir(tmp_path: Path) -> None:
    """A composite file records its dir in ``matched_composite_dirs`` with the
    committed cone as targets (no dorny test glob)."""
    breakdown = _gate_coverage_impl(tmp_path).scope_breakdown("src/specify_cli/git/foo.py")

    assert set(breakdown.test_targets) == {"tests/git", "tests/git_ops"}
    assert breakdown.matched_composite_dirs == ("git",)
    assert breakdown.matched_shard_groups == ()
    assert breakdown.empty_cone_composite_dirs == ()


def test_gate_coverage_scope_breakdown_flags_empty_cone_composite_dir(tmp_path: Path) -> None:
    """A composite dir with an EMPTY committed cone is recorded in
    ``empty_cone_composite_dirs`` and contributes no target (SC-007)."""
    routing: dict[str, pre_review_gate._CompositeRoute] = {"git": (None, None, ())}
    impl = GateCoverageScopeSource(
        repo_root=tmp_path,
        filter_groups_override={"git": ("src/specify_cli/git/**",)},
        composite_routing_override=routing,
    )

    breakdown = impl.scope_breakdown("src/specify_cli/git/foo.py")

    assert breakdown.test_targets == ()
    assert breakdown.matched_composite_dirs == ("git",)
    assert breakdown.empty_cone_composite_dirs == ("git",)


def test_gate_coverage_scope_breakdown_marks_catch_all_only_file_as_no_contribution(tmp_path: Path) -> None:
    """A file landing ONLY in a catch-all group (``core_misc`` via ``src/**``)
    contributes nothing and reports ``contributes_scope=False`` — the signal the
    engine folds into ``ScopeResult.excluded_scope_files``."""
    breakdown = _gate_coverage_impl(tmp_path).scope_breakdown("src/kernel/foo.py")

    assert breakdown.contributes_scope is False
    assert breakdown.test_targets == ()
    assert breakdown.matched_shard_groups == ()


def test_gate_coverage_file_to_scope_is_the_breakdown_targets_projection(tmp_path: Path) -> None:
    """``file_to_scope`` stays the flat projection of ``scope_breakdown`` — the
    behaviour-preserving contract that keeps the flat callers unchanged."""
    impl = _gate_coverage_impl(tmp_path)
    for path in ("src/specify_cli/status/emit.py", "src/specify_cli/git/foo.py", "src/kernel/foo.py"):
        assert impl.file_to_scope(path) == impl.scope_breakdown(path).test_targets


def test_gate_coverage_parse_results_parses_sample_junit_xml_into_failures(tmp_path: Path) -> None:
    junit_path = tmp_path / "sample-junit.xml"
    junit_path.write_text(
        '<testsuite>'
        '<testcase classname="tests.foo" name="test_ok" />'
        '<testcase classname="tests.foo" name="test_broken">'
        '<failure message="AssertionError: boom">traceback</failure>'
        "</testcase>"
        "</testsuite>",
        encoding="utf-8",
    )
    impl = GateCoverageScopeSource(repo_root=tmp_path)
    raw = RawRunResult(returncode=1, stdout="", stderr="", output_artifact_path=junit_path)

    failures = impl.parse_results(raw)

    assert len(failures) == 1
    assert failures[0].test == "tests.foo.test_broken"
    assert "boom" in failures[0].error


def test_glob_matches_file_fnmatch_branch_for_a_wildcard_mid_pattern() -> None:
    """A glob that contains ``*`` but does not end in ``/**`` falls back to
    shell-style ``fnmatch`` (private copy of ``pre_review_gate``'s helper)."""
    assert scope_source._glob_matches_file("tests/status/test_*.py", "tests/status/test_emit.py") is True
    assert scope_source._glob_matches_file("tests/status/test_*.py", "tests/status/other.py") is False


def test_glob_to_pytest_target_returns_a_non_star_glob_unchanged() -> None:
    assert scope_source._glob_to_pytest_target("tests/status/test_emit.py") == "tests/status/test_emit.py"


def test_src_dir_segment_returns_none_outside_the_src_package_prefix() -> None:
    assert scope_source._src_dir_segment("README.md") is None


def test_is_spec_kitty_source_repo_true_when_gate_coverage_module_present(tmp_path: Path) -> None:
    gate_coverage = tmp_path / "tests" / "architectural" / "_gate_coverage.py"
    gate_coverage.parent.mkdir(parents=True)
    gate_coverage.write_text("", encoding="utf-8")

    assert scope_source._is_spec_kitty_source_repo(tmp_path) is True


def test_is_spec_kitty_source_repo_false_for_a_bare_consumer_checkout(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()

    assert scope_source._is_spec_kitty_source_repo(tmp_path) is False


def test_load_gate_coverage_module_marks_consumer_repo_when_unavailable(tmp_path: Path) -> None:
    """A bare consumer repo (no ``tests/architectural/_gate_coverage.py`` of
    its own) raises ``GateAuthoritiesUnavailable`` with ``is_consumer_repo=True``
    — mirrors ``pre_review_gate``'s own #2534 calm-degrade guard, now proven
    against this module's PRIVATE copy of the loader (FR-009)."""
    with pytest.raises(pre_review_gate.GateAuthoritiesUnavailable) as excinfo:
        scope_source._load_gate_coverage_module(tmp_path)

    assert excinfo.value.is_consumer_repo is True


def test_gate_coverage_uses_the_live_authorities_against_the_real_repo() -> None:
    """No override -> the live ``tests.architectural._gate_coverage``
    authorities load for real against THIS repo — the "unreachable unless
    selected" claim (FR-009) only holds if the live path genuinely works."""
    impl = GateCoverageScopeSource(repo_root=_REPO_ROOT)

    targets = impl.file_to_scope("src/specify_cli/review/scope_source.py")

    assert isinstance(targets, tuple)


def test_gate_coverage_parse_results_missing_artifact_is_surfaced_not_swallowed(tmp_path: Path) -> None:
    """A run that produced no JUnit artifact at all must never silently
    collapse to an empty (clean-looking) failure set."""
    impl = GateCoverageScopeSource(repo_root=tmp_path)
    raw = RawRunResult(returncode=1, stdout="", stderr="", output_artifact_path=None)

    failures = impl.parse_results(raw)

    assert len(failures) == 1


# ---------------------------------------------------------------------------
# DeclaredCommandScopeSource (T008)
# ---------------------------------------------------------------------------


def _write_config(repo_root: Path, *, test_command: str | None) -> None:
    kittify_dir = repo_root / ".kittify"
    kittify_dir.mkdir(parents=True, exist_ok=True)
    if test_command is None:
        (kittify_dir / "config.yaml").write_text("review: {}\n", encoding="utf-8")
        return
    (kittify_dir / "config.yaml").write_text(
        f"review:\n  test_command: {test_command!r}\n",
        encoding="utf-8",
    )


def test_declared_command_test_command_returns_shlex_split_of_configured_command(tmp_path: Path) -> None:
    _write_config(tmp_path, test_command="./run-tests.sh --ci")

    command = DeclaredCommandScopeSource(repo_root=tmp_path).test_command()

    assert command == ["./run-tests.sh", "--ci"]


def test_declared_command_no_config_yields_none_test_command(tmp_path: Path) -> None:
    """Named mission guard: no-config -> ``test_command() -> None`` -> the
    gate surfaces a visible ``NO_COVERAGE`` warn, never a silent green."""
    _write_config(tmp_path, test_command=None)

    command = DeclaredCommandScopeSource(repo_root=tmp_path).test_command()

    assert command is None


def test_declared_command_file_to_scope_is_always_empty(tmp_path: Path) -> None:
    impl = DeclaredCommandScopeSource(repo_root=tmp_path)

    assert impl.file_to_scope("any/file/at/all.rb") == ()
    assert impl.file_to_scope("src/specify_cli/status/emit.py") == ()


def test_declared_command_parse_results_prefers_a_junit_artifact_when_present(tmp_path: Path) -> None:
    """A declared command configured with ``test_output_format: junit_xml``
    that happens to produce a JUnit artifact is parsed via the same
    ``_parse_junit_xml`` authority as the internal impl (FR-011 consistency)."""
    junit_path = tmp_path / "declared-junit.xml"
    junit_path.write_text(
        '<testsuite><testcase classname="t" name="test_ok" />'
        '<testcase classname="t" name="test_broken">'
        '<failure message="boom">trace</failure></testcase></testsuite>',
        encoding="utf-8",
    )
    impl = DeclaredCommandScopeSource(repo_root=tmp_path)
    raw = RawRunResult(returncode=1, stdout="", stderr="", output_artifact_path=junit_path)

    failures = impl.parse_results(raw)

    assert [f.test for f in failures] == ["t.test_broken"]


def test_declared_command_parse_results_yields_per_failure_identities(tmp_path: Path) -> None:
    impl = DeclaredCommandScopeSource(repo_root=tmp_path)
    raw = RawRunResult(
        returncode=1,
        stdout="ok test_alpha\nFAIL test_beta: boom\nFAIL test_gamma: kaboom\n",
        stderr="",
    )

    failures = impl.parse_results(raw)

    assert {f.test for f in failures} == {"test_beta", "test_gamma"}


def test_declared_command_parse_results_forbids_any_failures_style_collapse(tmp_path: Path) -> None:
    """A passing run (returncode 0, no FAIL lines) must parse to zero
    failures — proves ``parse_results`` is not a bare ``returncode != 0``
    (ANY_FAILURES) check, which the contract explicitly forbids."""
    impl = DeclaredCommandScopeSource(repo_root=tmp_path)
    raw = RawRunResult(returncode=0, stdout="ok test_alpha\nok test_beta\n", stderr="")

    assert impl.parse_results(raw) == ()


def test_declared_command_unparseable_nonzero_exit_counts_as_whole_run_failing(tmp_path: Path) -> None:
    """A non-zero exit with no parseable per-test failure lines must still
    be surfaced as failing (never swallowed) — but as ONE identity, since
    exit code alone carries no per-test identity."""
    impl = DeclaredCommandScopeSource(repo_root=tmp_path)
    raw = RawRunResult(returncode=2, stdout="", stderr="panic: segmentation fault\n")

    failures = impl.parse_results(raw)

    assert len(failures) == 1
    assert "segmentation fault" in failures[0].error


# ---------------------------------------------------------------------------
# T009 — portable-verdict baseline-relative fidelity fixtures (NFR-004)
# ---------------------------------------------------------------------------
#
# Both fixtures run a genuinely non-pytest-shaped ``FAIL <test>: <message>``
# declared command through DeclaredCommandScopeSource — proving the
# layout-agnostic path, not an accidentally-pytest one. The head<->baseline
# diff/classification itself is ``baseline.diff_baseline`` (existing,
# reused unchanged, owned by WP03's engine wiring) — exercised here only to
# prove the two fixtures' *data* (newly-failing vs pre-existing) originates
# from this port's ``parse_results``.


def test_newly_failing_fixture_is_blocking_capable_new_failures(tmp_path: Path) -> None:
    """A non-pytest consumer whose declared command has a test absent at
    baseline but failing at head -> a blocking-capable NEW_FAILURES
    identity, proving results are *parsed*, not that the process merely
    ran."""
    impl = DeclaredCommandScopeSource(repo_root=tmp_path)
    baseline_raw = RawRunResult(returncode=0, stdout="ok test_alpha\n", stderr="")
    head_raw = RawRunResult(returncode=1, stdout="ok test_alpha\nFAIL test_new_thing: boom\n", stderr="")

    baseline_failures = impl.parse_results(baseline_raw)
    head_failures = impl.parse_results(head_raw)
    baseline = BaselineTestResult(
        wp_id="WP02", captured_at="2026-01-01T00:00:00Z", base_branch="main",
        base_commit="abc1234", test_runner="custom", total=1, passed=1, failed=0,
        skipped=0, failures=tuple(baseline_failures),
    )

    pre_existing, new_failures, _fixed = diff_baseline(baseline, list(head_failures))

    assert [f.test for f in new_failures] == ["test_new_thing"]
    assert pre_existing == []


def test_pre_existing_failure_fixture_is_not_blocked(tmp_path: Path) -> None:
    """A consumer whose suite is already red at baseline -> the same red at
    head is classified pre-existing -> NOT blocked (no false-positive gate
    for a consumer with a pre-existing red suite)."""
    impl = DeclaredCommandScopeSource(repo_root=tmp_path)
    baseline_raw = RawRunResult(returncode=1, stdout="FAIL test_flaky: known issue\n", stderr="")
    head_raw = RawRunResult(returncode=1, stdout="FAIL test_flaky: known issue\n", stderr="")

    baseline_failures = impl.parse_results(baseline_raw)
    head_failures = impl.parse_results(head_raw)
    baseline = BaselineTestResult(
        wp_id="WP02", captured_at="2026-01-01T00:00:00Z", base_branch="main",
        base_commit="abc1234", test_runner="custom", total=1, passed=0, failed=1,
        skipped=0, failures=tuple(baseline_failures),
    )

    pre_existing, new_failures, _fixed = diff_baseline(baseline, list(head_failures))

    assert new_failures == []
    assert [f.test for f in pre_existing] == ["test_flaky"]


# ---------------------------------------------------------------------------
# T010 — behaviour-parity micro-golden for the internal scope derivation
# ---------------------------------------------------------------------------
#
# Snapshot the OLD ``pre_review_gate.derive_test_scope`` behaviour (the
# actual, unmodified function — not a hand-computed expectation, to avoid a
# self-referential oracle) and assert the NEW ``GateCoverageScopeSource``
# reproduces it for each representative shape.


@pytest.mark.parametrize(
    "changed_file",
    [
        "src/specify_cli/status/emit.py",  # per-shard tests/** direct target
        "src/specify_cli/git/foo.py",  # composite routing, non-empty cone
        "src/specify_cli/governance_file.py",  # top-level file, no owning dir -> ()
        "src/kernel/foo.py",  # catch-all only -> excluded, empty
    ],
)
def test_internal_scope_derivation_micro_parity_with_old_derive_test_scope(
    tmp_path: Path, changed_file: str,
) -> None:
    old_scope = pre_review_gate.derive_test_scope(
        [changed_file],
        repo_root=tmp_path,
        filter_groups=_MICRO_GOLDEN_GROUPS,
        composite_routing=_MICRO_GOLDEN_ROUTING,
    )

    new_targets = _gate_coverage_impl(tmp_path).file_to_scope(changed_file)

    assert set(new_targets) == set(old_scope.test_targets)

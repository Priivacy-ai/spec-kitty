"""Tests for specify_cli.review.pre_review_gate — WP01: scope derivation +
head-side runner + verdict engine (mission review-regression-gate-01KWX6DF).

Scope-derivation cases below use INJECTED ``filter_groups``/``composite_routing``
fixtures (offline, no repo I/O) so they stay hermetic and fast — the proof that
the derivation reads the LIVE authorities lives in
``tests/architectural/test_pre_review_scope_singlesource.py`` (FR-006), not
here. The fixtures below deliberately mirror the real ci-quality.yml shapes
(status/core_misc/execution_context overlap; auth_audit_git/governance
composites) so the shape + exclusion assertions still pin the real-world
scenarios named in the spec (SC-003/SC-004/SC-007), just against a stable,
hand-built substrate instead of the live workflow file.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.review import pre_review_gate
from specify_cli.review.baseline import BaselineFailure, BaselineTestResult
from specify_cli.review.pre_review_gate import GateOutcome, HeadRunResult, ScopeResult

# Module-level marker required by tests/architectural/test_pytest_marker_convention.py
# (WP01 landed this file without one — a pre-existing arch-gate red this WP02 sweep
# surfaced and Boy-Scout-fixes here). ``integration`` (not ``fast``) is the correct
# choice: the file's per-function markers stay authoritative and additive under it
# (the 18 ``@pytest.mark.fast`` cases remain selected by the fast-tests-review shard's
# ``-m "fast and not windows_ci"``), while ``integration`` keeps the 3 real-subprocess
# tests (``run_scoped_tests_at_head`` spawns real pytest) OUT of the fast lane — a
# module-level ``fast`` would have wrongly dragged them in.
pytestmark = [pytest.mark.integration]

# ---------------------------------------------------------------------------
# Synthetic filter-group / composite-routing fixtures (mirror the real
# ci-quality.yml shapes closely enough to pin SC-003/SC-004/SC-007 offline).
# ---------------------------------------------------------------------------

FAKE_GROUPS: dict[str, tuple[str, ...]] = {
    "status": (
        "src/specify_cli/status/**",
        "tests/status/**",
        "tests/specify_cli/status/**",
    ),
    "core_misc": (
        "src/specify_cli/status/**",
        "src/kernel/**",
        "tests/architectural/**",
        "tests/integration/**",
        "tests/contract/**",
    ),
    "execution_context": (
        "src/specify_cli/status/**",
        "tests/architectural/test_execution_context_parity.py",
    ),
    "any_src": ("src/**",),
    "e2e": ("tests/e2e/**",),
    "auth_audit_git": (
        "src/specify_cli/auth/**",
        "src/specify_cli/audit/**",
        "src/specify_cli/git/**",
    ),
    "governance": (
        "src/specify_cli/validators/**",
        "src/specify_cli/doctrine/**",
    ),
}

FAKE_ROUTING: dict[str, pre_review_gate._CompositeRoute] = {
    "git": (None, None, ("tests/git", "tests/git_ops")),
    "validators": (None, None, ()),
}

_DUMMY_ROOT = Path(".")


def _derive(changed_files: list[str]) -> ScopeResult:
    return pre_review_gate.derive_test_scope(
        changed_files,
        repo_root=_DUMMY_ROOT,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )


# ---------------------------------------------------------------------------
# Scope derivation: per-shard shape (FR-002/SC-003)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_per_shard_group_contributes_its_own_test_globs_and_excludes_core_misc() -> None:
    """status/emit.py-shaped file: member of status (focused, per-shard),
    core_misc (catch-all, excluded), and execution_context (focused,
    per-shard) — mirrors the spec's own grounding example."""
    scope = _derive(["src/specify_cli/status/emit.py"])
    assert set(scope.test_targets) == {
        "tests/status",
        "tests/specify_cli/status",
        "tests/architectural/test_execution_context_parity.py",
    }
    assert set(scope.matched_shard_groups) == {"status", "execution_context"}
    assert "core_misc" not in scope.matched_shard_groups
    assert not scope.is_empty


@pytest.mark.fast
def test_recall_over_precision_ambiguous_file_gets_every_focused_group() -> None:
    """An ambiguous file matching >=2 focused groups gets BOTH — no attempt
    to pick a single "best" group (recall > precision, spec edge case)."""
    scope = _derive(["src/specify_cli/status/emit.py"])
    assert {"status", "execution_context"} <= set(scope.matched_shard_groups)


# ---------------------------------------------------------------------------
# Scope derivation: composite shape (FR-002/SC-003/SC-007)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_composite_group_with_nonempty_cone_contributes_cone_roots() -> None:
    """A git/**-shaped change resolves via the composite dir's cone_roots,
    not any dorny test glob (auth_audit_git carries none)."""
    scope = _derive(["src/specify_cli/git/foo.py"])
    assert set(scope.test_targets) == {"tests/git", "tests/git_ops"}
    assert scope.matched_composite_dirs == ("git",)
    assert not scope.matched_shard_groups
    assert not scope.is_empty


@pytest.mark.fast
def test_composite_group_with_empty_cone_is_a_no_coverage_warn_not_clean() -> None:
    """SC-007: validators is a real composite dir with an EMPTY committed
    cone — the derivation must surface it as unverified, never silently
    "clean"."""
    scope = _derive(["src/specify_cli/validators/schema.py"])
    assert scope.is_empty
    assert scope.empty_cone_composite_dirs == ("validators",)
    assert "unmapped composite dir" in scope.describe_empty_reason()


# ---------------------------------------------------------------------------
# Scope derivation: catch-all / unmatched exclusion (FR-005)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_catch_all_only_file_is_excluded_and_scope_warns() -> None:
    """A file landing ONLY in a catch-all group (here: core_misc via
    src/kernel/**) contributes nothing — excluded, not a whole-tree run."""
    scope = _derive(["src/kernel/foo.py"])
    assert scope.is_empty
    assert scope.excluded_scope_files == ("src/kernel/foo.py",)
    assert "excluded scope" in scope.describe_empty_reason()


@pytest.mark.fast
def test_unmatched_file_is_excluded_and_scope_warns() -> None:
    """A file matching NO dorny group at all is excluded the same way."""
    scope = _derive(["README.md"])
    assert scope.is_empty
    assert scope.excluded_scope_files == ("README.md",)


@pytest.mark.fast
def test_describe_empty_reason_distinguishes_the_two_sc007_causes() -> None:
    empty_cone_scope = ScopeResult(
        test_targets=(),
        matched_shard_groups=(),
        matched_composite_dirs=("validators",),
        empty_cone_composite_dirs=("validators",),
        excluded_scope_files=(),
    )
    excluded_scope = ScopeResult(
        test_targets=(),
        matched_shard_groups=(),
        matched_composite_dirs=(),
        empty_cone_composite_dirs=(),
        excluded_scope_files=("README.md",),
    )
    assert "unmapped composite dir" in empty_cone_scope.describe_empty_reason()
    assert "excluded scope" in excluded_scope.describe_empty_reason()


# ---------------------------------------------------------------------------
# Head-side scoped runner (FR-001/FR-003, net-new)
# ---------------------------------------------------------------------------


_PASSING_TEST_BODY = "def test_pass():\n    assert True\n"
_FAILING_TEST_BODY = f"{_PASSING_TEST_BODY}\n\ndef test_break():\n    assert False, 'boom'\n"


def _write_tiny_pytest_project(base: Path, *, failing: bool) -> None:
    body = _FAILING_TEST_BODY if failing else _PASSING_TEST_BODY
    (base / "test_sample.py").write_text(body, encoding="utf-8")


@pytest.mark.fast
def test_empty_test_targets_never_invokes_subprocess() -> None:
    result = pre_review_gate.run_scoped_tests_at_head([], repo_root=_DUMMY_ROOT)
    assert result.ran is False
    assert result.current_failures == ()
    assert "empty test scope" in (result.error or "")


@pytest.mark.integration
def test_real_subprocess_run_parses_junit_and_captures_current_failures(tmp_path: Path) -> None:
    _write_tiny_pytest_project(tmp_path, failing=True)
    result = pre_review_gate.run_scoped_tests_at_head(["test_sample.py"], repo_root=tmp_path)
    assert result.ran is True
    failing_names = {f.test for f in result.current_failures}
    assert any("test_break" in name for name in failing_names)
    assert not any("test_pass" in name for name in failing_names)


@pytest.mark.integration
def test_real_subprocess_run_with_no_failures_yields_empty_current_failures(tmp_path: Path) -> None:
    _write_tiny_pytest_project(tmp_path, failing=False)
    result = pre_review_gate.run_scoped_tests_at_head(["test_sample.py"], repo_root=tmp_path)
    assert result.ran is True
    assert result.current_failures == ()


@pytest.mark.fast
def test_missing_junit_output_degrades_to_a_warn_not_a_crash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    def _fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(pre_review_gate.subprocess, "run", _fake_run)
    result = pre_review_gate.run_scoped_tests_at_head(["tests/status"], repo_root=tmp_path)
    assert result.ran is False
    assert result.returncode == 1
    assert "no JUnit XML produced" in (result.error or "")


@pytest.mark.fast
def test_timeout_degrades_to_a_warn_not_a_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _raise_timeout(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=1)

    monkeypatch.setattr(pre_review_gate.subprocess, "run", _raise_timeout)
    result = pre_review_gate.run_scoped_tests_at_head(["tests/status"], repo_root=tmp_path, timeout=1)
    assert result.ran is False
    assert "timed out" in (result.error or "")


@pytest.mark.fast
def test_launch_failure_degrades_to_a_warn_not_a_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _raise_oserror(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("no such file or directory")

    monkeypatch.setattr(pre_review_gate.subprocess, "run", _raise_oserror)
    result = pre_review_gate.run_scoped_tests_at_head(["tests/status"], repo_root=tmp_path)
    assert result.ran is False
    assert "failed to launch" in (result.error or "")


@pytest.mark.fast
def test_malformed_junit_degrades_to_a_warn_not_a_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        junit_arg = next(arg for arg in command if arg.startswith("--junitxml="))
        junit_path = Path(junit_arg.split("=", 1)[1])
        junit_path.write_text("not valid xml <<<", encoding="utf-8")
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(pre_review_gate.subprocess, "run", _fake_run)
    result = pre_review_gate.run_scoped_tests_at_head(["tests/status"], repo_root=tmp_path)
    assert result.ran is False
    assert "failed to parse" in (result.error or "")


# ---------------------------------------------------------------------------
# Verdict composition + diff_baseline reuse (FR-001/FR-003/SC-001/SC-002)
# ---------------------------------------------------------------------------


def _make_baseline(
    failures: tuple[BaselineFailure, ...] = (),
    *,
    failed: int = 0,
) -> BaselineTestResult:
    return BaselineTestResult(
        wp_id="WP01",
        captured_at="2026-07-07T00:00:00Z",
        base_branch="main",
        base_commit="abc1234",
        test_runner="pytest",
        total=10,
        passed=10 - failed,
        failed=failed,
        skipped=0,
        failures=failures,
    )


def _sentinel_baseline() -> BaselineTestResult:
    return BaselineTestResult(
        wp_id="WP01",
        captured_at="2026-07-07T00:00:00Z",
        base_branch="main",
        base_commit="",
        test_runner="pytest",
        total=0,
        passed=0,
        failed=-1,
        skipped=0,
        failures=(),
    )


@pytest.mark.fast
def test_empty_scope_short_circuits_before_running_or_diffing(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> HeadRunResult:
        raise AssertionError("run_scoped_tests_at_head must not be called for an empty scope")

    monkeypatch.setattr(pre_review_gate, "run_scoped_tests_at_head", _boom)
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/validators/schema.py"],
        repo_root=_DUMMY_ROOT,
        baseline=None,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.NO_COVERAGE


@pytest.mark.fast
def test_run_that_does_not_complete_degrades_to_no_coverage_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=False, error="boom"),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=None,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.NO_COVERAGE
    assert "scoped test run did not complete" in (verdict.reason or "")


@pytest.mark.fast
def test_uncomputable_baseline_none_degrades_to_warn_and_surfaces_all_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_failure = BaselineFailure(test="tests.git.test_x", error="boom", file="tests/git/test_x.py:1")
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=True, current_failures=(fake_failure,)),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=None,
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.UNVERIFIED_BASELINE
    assert verdict.new_failures == (fake_failure,)


@pytest.mark.fast
def test_sentinel_baseline_degrades_to_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_failure = BaselineFailure(test="tests.git.test_x", error="boom", file="tests/git/test_x.py:1")
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=True, current_failures=(fake_failure,)),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=_sentinel_baseline(),
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.UNVERIFIED_BASELINE


@pytest.mark.fast
def test_pre_existing_failure_does_not_block_no_new_failures_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SC-002: a base failure in the affected shard does NOT block the WP."""
    shared_failure = BaselineFailure(
        test="tests.git.test_known_red", error="pre-existing", file="tests/git/test_x.py:1",
    )
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=True, current_failures=(shared_failure,)),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=_make_baseline((shared_failure,), failed=1),
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert verdict.pre_existing_failures == (shared_failure,)
    assert verdict.new_failures == ()


@pytest.mark.fast
def test_new_failure_is_surfaced_via_the_real_diff_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-001: proves genuine ``diff_baseline`` reuse — the real function is
    spied on (still delegated to), not reimplemented."""
    calls: list[tuple[BaselineTestResult, list[BaselineFailure]]] = []
    real_diff_baseline = pre_review_gate.diff_baseline

    def _spy(
        baseline: BaselineTestResult, current_failures: list[BaselineFailure],
    ) -> tuple[list[BaselineFailure], list[BaselineFailure], list[str]]:
        calls.append((baseline, list(current_failures)))
        return real_diff_baseline(baseline, current_failures)

    monkeypatch.setattr(pre_review_gate, "diff_baseline", _spy)

    new_failure = BaselineFailure(
        test="tests.git.test_newly_broken", error="AssertionError", file="tests/git/test_x.py:5",
    )
    monkeypatch.setattr(
        pre_review_gate,
        "run_scoped_tests_at_head",
        lambda *a, **k: HeadRunResult(ran=True, current_failures=(new_failure,)),
    )
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=_DUMMY_ROOT,
        baseline=_make_baseline(),
        filter_groups=FAKE_GROUPS,
        composite_routing=FAKE_ROUTING,
    )
    assert verdict.outcome is GateOutcome.NEW_FAILURES
    assert verdict.new_failures == (new_failure,)
    assert len(calls) == 1


@pytest.mark.integration
def test_end_to_end_new_failure_detected_via_real_subprocess_and_real_diff(tmp_path: Path) -> None:
    """Full composition with a REAL subprocess pytest run + the REAL
    diff_baseline — only the scope-derivation inputs are synthetic."""
    _write_tiny_pytest_project(tmp_path, failing=True)
    verdict = pre_review_gate.evaluate_pre_review_gate(
        ["src/specify_cli/git/foo.py"],
        repo_root=tmp_path,
        baseline=_make_baseline(),  # base had no failures
        filter_groups={"auth_audit_git": ("src/specify_cli/git/**",)},
        composite_routing={"git": (None, None, ("test_sample.py",))},
    )
    assert verdict.outcome is GateOutcome.NEW_FAILURES
    assert any("test_break" in f.test for f in verdict.new_failures)

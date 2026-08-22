"""Unit tests for the flake-report pure core (mission ci-flake-report-workflow, WP01).

Pins, red-first, the behaviors from ``kitty-specs/ci-flake-report-workflow-01M0M9D8``:

- FR-001 conclusion taxonomy: `cancelled`/`action_required` excluded from both
  numerator and denominator; `tally()` denominators.
- FR-002 classifier signature contract (data-model.md §5): mixed run -> `real`;
  all-timing -> `perf_timing_flake`; infra-only -> `infra_flake`; gate signal ->
  `real`; unmatched -> `needs_review`. `false_red_rate` reproduces the squad's
  0.586 on the data-model's own synthetic counts.
- FR-003 duration aggregation: median/mean/max + the `median > 2.0` long-pole
  threshold (boundary exactly at 2.0 is NOT a long pole).
- FR-004/FR-005 delta cursor: half-open boundary (`>` not `>=`); a straddling
  in-progress run is enumerated exactly once when it completes; a re-run/new
  attempt is re-picked by completion time, not blocked by a stale run-id seen
  before; `completed_through` never regresses.
- FR-015/NFR-004: `classifier_coverage`, deterministic ordering, and the
  enumerated run-id set recorded on `ReportState`.

``scripts/ci`` is not an importable package (mirrors
``tests/ci/test_sonar_project_version.py`` / ``tests/scripts/test_quality_gate_decision.py``),
so the module is loaded by file path.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "ci" / "flake_report.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("flake_report", _SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build an import spec for {_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FR: Any = _load_module()

_UTC = UTC


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=_UTC)


def _run(
    run_id: int,
    conclusion: str | None,
    *,
    attempt: int = 1,
    status: str = "completed",
    created_at: str = "2026-08-15T09:00:00",
    completed_at: str | None = "2026-08-15T09:10:00",
    pr_number: int | None = 3596,
    head_branch: str | None = "kitty/mission-ci-flake-report-workflow-01M0M9D8-lane-1",
) -> Any:
    return FR.Run(
        run_id=run_id,
        attempt=attempt,
        conclusion=conclusion,
        status=status,
        event="pull_request",
        draft=False,
        created_at=_dt(created_at),
        completed_at=_dt(completed_at) if completed_at else None,
        pr_number=pr_number,
        head_branch=head_branch,
    )


# ---------------------------------------------------------------------------
# FR-001: conclusion taxonomy + tally
# ---------------------------------------------------------------------------


class TestConclusionTaxonomy:
    @pytest.mark.parametrize("conclusion", ["success", "failure", "timed_out", "startup_failure"])
    def test_completed_set(self, conclusion: str) -> None:
        assert FR.is_completed(conclusion) is True
        assert FR.is_excluded(conclusion) is False

    @pytest.mark.parametrize("conclusion", ["cancelled", "action_required", "skipped", "neutral", "stale"])
    def test_excluded_set(self, conclusion: str) -> None:
        assert FR.is_excluded(conclusion) is True
        assert FR.is_completed(conclusion) is False

    def test_none_conclusion_is_neither(self) -> None:
        # In-progress runs report conclusion=None; not completed, not excluded.
        assert FR.is_completed(None) is False
        assert FR.is_excluded(None) is False

    def test_cancelled_and_action_required_excluded_from_tally_numerator_and_denominator(self) -> None:
        runs = [
            _run(32554963001, "success", pr_number=3596),
            _run(32554963002, "failure", pr_number=3596),
            _run(32554963003, "cancelled", pr_number=3597),
            _run(32554963004, "action_required", pr_number=3598),
        ]
        result = FR.tally(runs)
        # completed_runs counts only success/failure (2), not cancelled/action_required.
        assert result.completed_runs == 2
        assert result.total_runs == 4

    def test_distinct_prs_deduped_by_pr_number_with_head_branch_fallback(self) -> None:
        runs = [
            _run(1, "success", pr_number=3407, head_branch="kitty/mission-a-lane-1"),
            _run(2, "failure", pr_number=3407, head_branch="kitty/mission-a-lane-2"),  # same PR, dedup
            _run(3, "success", pr_number=None, head_branch="main"),  # push event, headBranch fallback
            _run(4, "failure", pr_number=None, head_branch="main"),  # same push branch, dedup
        ]
        result = FR.tally(runs)
        assert result.distinct_prs == 2  # {pr:3407, branch:main}

    def test_prs_with_failure_counts_completed_failure_conclusion_only(self) -> None:
        runs = [
            _run(1, "failure", pr_number=100),
            _run(2, "success", pr_number=101),
            _run(3, "cancelled", pr_number=102),  # excluded conclusion, not a "failure"
        ]
        result = FR.tally(runs)
        assert result.prs_with_failure == 1

    def test_distinct_prs_excludes_non_completed_conclusions(self) -> None:
        # renata S2/paula 8: a cancelled/action_required run's PR must not
        # inflate distinct_prs -- it never produced a completed verdict.
        runs = [
            _run(1, "success", pr_number=100),
            _run(2, "cancelled", pr_number=200),  # excluded: must not count
            _run(3, "action_required", pr_number=300),  # excluded: must not count
        ]
        result = FR.tally(runs)
        assert result.distinct_prs == 1

    def test_prs_with_failure_counts_failure_like_conclusions_not_just_bare_failure(self) -> None:
        # renata S2/paula 8: timed_out/startup_failure are FAILURE_LIKE too,
        # not just the bare "failure" conclusion.
        runs = [
            _run(1, "timed_out", pr_number=400),
            _run(2, "startup_failure", pr_number=500),
            _run(3, "success", pr_number=600),
        ]
        result = FR.tally(runs)
        assert result.prs_with_failure == 2


# ---------------------------------------------------------------------------
# FR-002: classifier + false-red rate
# ---------------------------------------------------------------------------


_TIMING_NODEID_1 = "tests/perf/test_tasks_status_baseline.py::test_tasks_status_p95_within_nfr005_budget"
_TIMING_NODEID_2 = "tests/architectural/test_startup_budget.py::test_the_guard_completes_inside_the_budget_on_three_warm_runs"
_REAL_NODEID = "tests/status/test_transitions.py::test_reject_blocked_to_done_without_force"


class TestClassifyOne:
    def test_all_timing_nodeids_is_perf_timing_flake(self) -> None:
        bucket, reason = FR.classify_one(
            failed_nodeids=[_TIMING_NODEID_1, _TIMING_NODEID_2],
            log_text="FAILED " + _TIMING_NODEID_1 + "\nFAILED " + _TIMING_NODEID_2,
            job_names=["fast-tests-perf"],
            infra_signals=[],
            gate_signals=[],
        )
        assert bucket == FR.BUCKET_PERF_TIMING_FLAKE
        assert _TIMING_NODEID_1 in reason

    def test_mixed_timing_and_real_nodeids_is_real(self) -> None:
        bucket, _reason = FR.classify_one(
            failed_nodeids=[_TIMING_NODEID_1, _REAL_NODEID],
            log_text="",
            job_names=["fast-tests-status"],
            infra_signals=[],
            gate_signals=[],
        )
        assert bucket == FR.BUCKET_REAL

    def test_infra_signal_with_no_failed_nodeids_is_infra_flake(self) -> None:
        bucket, reason = FR.classify_one(
            failed_nodeids=[],
            log_text="ERROR: logged_out_on_connected_teamspace during setup",
            job_names=["fast-tests-sync"],
            infra_signals=["logged_out_on_connected_teamspace"],
            gate_signals=[],
        )
        assert bucket == FR.BUCKET_INFRA_FLAKE
        assert "logged_out_on_connected_teamspace" in reason

    def test_infra_signal_plus_failed_nodeid_is_not_infra_flake(self) -> None:
        # infra_signals present but a real nodeid also failed -> real wins (actionable).
        bucket, _reason = FR.classify_one(
            failed_nodeids=[_REAL_NODEID],
            log_text="INTERNALERROR: an unexpected error occurred",
            job_names=["fast-tests-status"],
            infra_signals=["INTERNALERROR"],
            gate_signals=[],
        )
        assert bucket == FR.BUCKET_REAL

    def test_gate_signal_with_no_failed_nodeids_is_real(self) -> None:
        bucket, reason = FR.classify_one(
            failed_nodeids=[],
            log_text="",
            job_names=["mypy-strict-gate"],
            infra_signals=[],
            gate_signals=["mypy-strict-gate"],
        )
        assert bucket == FR.BUCKET_REAL
        assert "mypy-strict-gate" in reason

    def test_unmatched_failure_is_needs_review(self) -> None:
        bucket, reason = FR.classify_one(
            failed_nodeids=[],
            log_text="some unrecognized failure output",
            job_names=["fast-tests-unknown-shard"],
            infra_signals=[],
            gate_signals=[],
        )
        assert bucket == FR.BUCKET_NEEDS_REVIEW
        assert "1 job(s)" in reason

    def test_is_timing_matches_seed_set_and_regex_fallback(self) -> None:
        assert FR.is_timing(_TIMING_NODEID_1) is True
        assert FR.is_timing("tests/perf/test_x.py::test_nfr_003_completes_in_under_5s") is True
        assert FR.is_timing(_REAL_NODEID) is False

    def test_extract_failed_nodeids_greps_failed_lines(self) -> None:
        log = f"FAILED {_TIMING_NODEID_1} - assert False\nFAILED {_REAL_NODEID} - AssertionError\n"
        assert FR.extract_failed_nodeids(log) == [_TIMING_NODEID_1, _REAL_NODEID]

    def test_extract_infra_signals_finds_known_keywords(self) -> None:
        assert FR.extract_infra_signals("boom: digest-mismatch detected") == frozenset({"digest-mismatch"})
        assert FR.extract_infra_signals("all clear") == frozenset()

    def test_extract_gate_signals_matches_job_name_substrings(self) -> None:
        result = FR.extract_gate_signals(["mypy-strict-gate", "fast-tests-status", "ruff-lint"])
        assert result == frozenset({"mypy-strict-gate", "ruff-lint"})

    def test_classify_one_rejects_unknown_bucket_in_bucket_counts(self) -> None:
        with pytest.raises(ValueError, match="unknown classification bucket"):
            FR.bucket_counts(["not_a_real_bucket"])


class TestTimingRegexConservativeness:
    """B1 (BLOCKER): bare ``_under_``/``nfr_00\\d`` over-matched 245+ real,
    non-timing repo tests -- a real regression in one of those would
    misclassify as ``perf_timing_flake`` and corrupt the headline false-red
    rate. The fallback regex must require a genuine timing co-signal.
    """

    def test_bare_under_nodeid_is_not_timing(self) -> None:
        # Real repo test: tests/charter/synthesizer/test_path_guard.py -- a
        # forbidden-path guard, nothing to do with timing budgets.
        nodeid = "tests/charter/synthesizer/test_path_guard.py::test_mkdir_under_forbidden_path_raises"
        assert FR.is_timing(nodeid) is False

    def test_bare_under_contention_nodeid_is_not_timing(self) -> None:
        nodeid = "tests/status/test_claim_contention.py::test_claim_under_contention"
        assert FR.is_timing(nodeid) is False

    def test_bare_nfr_nodeid_without_timing_cotoken_is_not_timing(self) -> None:
        # A real nfr_00N-named test that is about determinism, not timing.
        nodeid = "tests/doctor/test_identity_audit.py::test_nfr_004_deterministic_output"
        assert FR.is_timing(nodeid) is False

    def test_bare_under_nodeid_with_no_timing_signal_classifies_as_real_not_perf_timing_flake(self) -> None:
        nodeid = "tests/charter/synthesizer/test_path_guard.py::test_mkdir_under_forbidden_path_raises"
        bucket, _reason = FR.classify_one(
            failed_nodeids=[nodeid],
            log_text=f"FAILED {nodeid} - AssertionError",
            job_names=["fast-tests-charter"],
            infra_signals=[],
            gate_signals=[],
        )
        # A false needs_review would be honest; silently bucketing a real
        # regression as perf_timing_flake would corrupt the headline metric.
        assert bucket == FR.BUCKET_REAL

    def test_under_with_seconds_bound_is_timing(self) -> None:
        # A real repo timing test: tests/specify_cli/invocation/test_doctor_ops.py
        nodeid = "tests/specify_cli/invocation/test_doctor_ops.py::test_sweep_nfr_002_10k_files_under_5s"
        assert FR.is_timing(nodeid) is True

    def test_nfr_with_timing_cotoken_is_timing(self) -> None:
        # Real repo timing tests named test_nfr_00N_timing_*.
        assert FR.is_timing("tests/doctor/test_identity_audit.py::test_nfr_002_timing_200_missions") is True
        nodeid = "tests/specify_cli/cli/commands/test_doctor_mission_type.py::test_nfr_004_timing_200_missions"
        assert FR.is_timing(nodeid) is True

    def test_seed_set_and_narrow_fallback_alternatives_still_match(self) -> None:
        # Every non-seed-set alternative kept in the narrowed regex.
        assert FR.is_timing("tests/x.py::test_something_p95_latency") is True
        assert FR.is_timing("tests/x.py::test_stays_within_the_5s_budget") is True
        assert FR.is_timing("tests/x.py::test_completes_in_under_10_calls") is True


class TestConclusionThreadedClassification:
    """Thread ``run.conclusion`` into classification (renata N1/paula 4):
    ``startup_failure``/``timed_out`` runs commonly have no fetchable
    ``--log-failed`` body, so absent that evidence the run's own conclusion
    is a decisive infra signal rather than degrading to ``needs_review``.
    """

    def test_startup_failure_conclusion_with_no_other_signal_is_infra_flake(self) -> None:
        bucket, reason = FR.classify_one(
            failed_nodeids=[],
            log_text="",
            job_names=[],
            infra_signals=[],
            gate_signals=[],
            conclusion="startup_failure",
        )
        assert bucket == FR.BUCKET_INFRA_FLAKE
        assert "startup_failure" in reason

    def test_timed_out_conclusion_with_no_other_signal_is_infra_flake(self) -> None:
        bucket, reason = FR.classify_one(
            failed_nodeids=[],
            log_text="",
            job_names=[],
            infra_signals=[],
            gate_signals=[],
            conclusion="timed_out",
        )
        assert bucket == FR.BUCKET_INFRA_FLAKE
        assert "timed_out" in reason

    def test_no_conclusion_with_no_other_signal_still_needs_review(self) -> None:
        # Backward-compat default (conclusion=None): unchanged honest fallback.
        bucket, _reason = FR.classify_one(
            failed_nodeids=[], log_text="", job_names=[], infra_signals=[], gate_signals=[]
        )
        assert bucket == FR.BUCKET_NEEDS_REVIEW

    def test_failed_nodeid_takes_precedence_over_infra_like_conclusion(self) -> None:
        # Nodeid-keyed precedence retained: an actual failing test wins even
        # when the run's conclusion is timed_out.
        bucket, _reason = FR.classify_one(
            failed_nodeids=[_REAL_NODEID],
            log_text=f"FAILED {_REAL_NODEID}",
            job_names=[],
            infra_signals=[],
            gate_signals=[],
            conclusion="timed_out",
        )
        assert bucket == FR.BUCKET_REAL

    def test_gate_signal_takes_precedence_over_infra_like_conclusion(self) -> None:
        bucket, _reason = FR.classify_one(
            failed_nodeids=[],
            log_text="",
            job_names=["mypy-strict-gate"],
            infra_signals=[],
            gate_signals=["mypy-strict-gate"],
            conclusion="startup_failure",
        )
        assert bucket == FR.BUCKET_REAL


class TestFalseRedRate:
    def test_reproduces_the_squads_reference_rate(self) -> None:
        # data-model.md §1 headline example: 14 perf_timing_flake, 3 infra_flake,
        # 12 real, 0 needs_review -> 17/29 = 0.586 (rounded to 3dp for comparison).
        counts = {
            FR.BUCKET_PERF_TIMING_FLAKE: 14,
            FR.BUCKET_INFRA_FLAKE: 3,
            FR.BUCKET_REAL: 12,
            FR.BUCKET_NEEDS_REVIEW: 0,
        }
        assert round(FR.false_red_rate(counts), 3) == 0.586

    def test_needs_review_excluded_from_denominator(self) -> None:
        counts = {FR.BUCKET_PERF_TIMING_FLAKE: 1, FR.BUCKET_INFRA_FLAKE: 0, FR.BUCKET_REAL: 1, FR.BUCKET_NEEDS_REVIEW: 100}
        assert FR.false_red_rate(counts) == 0.5

    def test_empty_denominator_guards_divide_by_zero(self) -> None:
        counts = {FR.BUCKET_PERF_TIMING_FLAKE: 0, FR.BUCKET_INFRA_FLAKE: 0, FR.BUCKET_REAL: 0, FR.BUCKET_NEEDS_REVIEW: 3}
        assert FR.false_red_rate(counts) == 0.0

    def test_bucket_counts_builds_the_mapping_false_red_rate_consumes(self) -> None:
        buckets = [FR.BUCKET_PERF_TIMING_FLAKE] * 14 + [FR.BUCKET_INFRA_FLAKE] * 3 + [FR.BUCKET_REAL] * 12
        counts = FR.bucket_counts(buckets)
        assert counts.total == 29
        assert round(FR.false_red_rate(counts.as_mapping()), 3) == 0.586


class TestClassifierCoverage:
    def test_full_coverage_when_no_needs_review(self) -> None:
        counts = {FR.BUCKET_PERF_TIMING_FLAKE: 14, FR.BUCKET_INFRA_FLAKE: 3, FR.BUCKET_REAL: 12, FR.BUCKET_NEEDS_REVIEW: 0}
        assert FR.classifier_coverage(counts) == 1.0

    def test_partial_coverage_with_needs_review(self) -> None:
        counts = {FR.BUCKET_PERF_TIMING_FLAKE: 0, FR.BUCKET_INFRA_FLAKE: 0, FR.BUCKET_REAL: 8, FR.BUCKET_NEEDS_REVIEW: 2}
        assert FR.classifier_coverage(counts) == 0.8

    def test_zero_failures_guards_divide_by_zero(self) -> None:
        counts = {FR.BUCKET_PERF_TIMING_FLAKE: 0, FR.BUCKET_INFRA_FLAKE: 0, FR.BUCKET_REAL: 0, FR.BUCKET_NEEDS_REVIEW: 0}
        assert FR.classifier_coverage(counts) == 1.0


# ---------------------------------------------------------------------------
# FR-003: duration aggregation
# ---------------------------------------------------------------------------


class TestAggregateDurations:
    def test_aggregates_n_median_mean_max_per_nodeid(self) -> None:
        samples = [
            FR.DurationSample(nodeid=_TIMING_NODEID_1, duration_s=28.10),
            FR.DurationSample(nodeid=_TIMING_NODEID_1, duration_s=30.35),
            FR.DurationSample(nodeid=_TIMING_NODEID_1, duration_s=39.95),
        ]
        aggs = FR.aggregate_durations(samples)
        assert len(aggs) == 1
        agg = aggs[0]
        assert agg.nodeid == _TIMING_NODEID_1
        assert agg.n == 3
        assert agg.median_s == 30.35
        assert agg.max_s == 39.95
        assert agg.long_pole is True

    def test_long_pole_threshold_is_strictly_greater_than_2_seconds(self) -> None:
        at_boundary = FR.aggregate_durations([FR.DurationSample(nodeid="tests/x.py::test_a", duration_s=2.0)])
        above_boundary = FR.aggregate_durations([FR.DurationSample(nodeid="tests/x.py::test_b", duration_s=2.01)])
        assert at_boundary[0].long_pole is False
        assert above_boundary[0].long_pole is True

    def test_stable_ordering_by_nodeid(self) -> None:
        samples = [
            FR.DurationSample(nodeid="tests/z.py::test_z", duration_s=1.0),
            FR.DurationSample(nodeid="tests/a.py::test_a", duration_s=1.0),
        ]
        aggs = FR.aggregate_durations(samples)
        assert [agg.nodeid for agg in aggs] == ["tests/a.py::test_a", "tests/z.py::test_z"]

    def test_empty_samples_yields_empty_aggregates(self) -> None:
        assert FR.aggregate_durations([]) == []


# ---------------------------------------------------------------------------
# FR-004/FR-005: delta cursor
# ---------------------------------------------------------------------------


class TestResolveWindow:
    def test_no_prior_cursor_is_first_run_with_30_day_lookback(self) -> None:
        now = _dt("2026-08-22T05:00:00")
        window = FR.resolve_window(None, now)
        assert window.lineage == FR.LINEAGE_FIRST_RUN
        assert window.start == now - timedelta(days=30)
        assert window.end == now

    def test_invalid_baseline_is_lost_baseline_with_30_day_lookback(self) -> None:
        now = _dt("2026-08-22T05:00:00")
        prior = FR.Cursor(completed_through=_dt("2026-08-21T23:14:07"), in_progress_low_water=None)
        window = FR.resolve_window(prior, now, baseline_valid=False)
        assert window.lineage == FR.LINEAGE_LOST_BASELINE
        assert window.start == now - timedelta(days=30)

    def test_valid_baseline_starts_at_prior_completed_through(self) -> None:
        now = _dt("2026-08-22T05:00:00")
        prior = FR.Cursor(completed_through=_dt("2026-08-21T23:14:07"), in_progress_low_water=None)
        window = FR.resolve_window(prior, now)
        assert window.lineage == FR.LINEAGE_OK
        assert window.start == _dt("2026-08-21T23:14:07")


class TestRunsCompletedInWindow:
    def test_half_open_boundary_excludes_run_completed_exactly_at_start(self) -> None:
        window = FR.Window(start=_dt("2026-08-21T23:14:07"), end=_dt("2026-08-22T05:00:00"), lineage=FR.LINEAGE_OK)
        exactly_at_start = _run(1, "success", completed_at="2026-08-21T23:14:07")
        one_second_after = _run(2, "success", completed_at="2026-08-21T23:14:08")
        result = FR.runs_completed_in_window([exactly_at_start, one_second_after], window)
        assert [run.run_id for run in result] == [2]

    def test_in_progress_runs_with_no_completed_at_are_excluded(self) -> None:
        window = FR.Window(start=_dt("2026-08-21T00:00:00"), end=_dt("2026-08-22T00:00:00"), lineage=FR.LINEAGE_OK)
        in_progress = _run(1, None, status="in_progress", completed_at=None)
        result = FR.runs_completed_in_window([in_progress], window)
        assert result == []


class TestAdvanceCursor:
    def test_completed_through_advances_to_max_completed_time(self) -> None:
        previous = FR.Cursor(completed_through=_dt("2026-08-21T00:00:00"), in_progress_low_water=None)
        runs = [
            _run(1, "success", completed_at="2026-08-21T10:00:00"),
            _run(2, "failure", completed_at="2026-08-21T12:30:00"),
        ]
        cursor = FR.advance_cursor(runs, previous)
        assert cursor.completed_through == _dt("2026-08-21T12:30:00")

    def test_completed_through_never_regresses_on_backfilled_older_run(self) -> None:
        previous = FR.Cursor(completed_through=_dt("2026-08-21T12:30:00"), in_progress_low_water=None)
        backfilled_older_run = _run(99, "success", completed_at="2026-08-10T09:00:00")
        cursor = FR.advance_cursor([backfilled_older_run], previous)
        assert cursor.completed_through == _dt("2026-08-21T12:30:00")

    def test_straddling_run_low_water_mark_then_counted_once_on_completion(self) -> None:
        previous = FR.Cursor(completed_through=_dt("2026-08-14T23:14:07"), in_progress_low_water=None)

        # Pass 1: run 32549865287 is still in progress at report time.
        straddler_in_progress = _run(
            32549865287, None, status="in_progress", created_at="2026-08-21T20:00:00", completed_at=None
        )
        cursor_after_pass1 = FR.advance_cursor([straddler_in_progress], previous)
        assert cursor_after_pass1.completed_through == _dt("2026-08-14T23:14:07")  # unchanged, not completed yet
        assert cursor_after_pass1.in_progress_low_water == _dt("2026-08-21T20:00:00")

        window1 = FR.resolve_window(previous, _dt("2026-08-21T23:14:07"))
        enumerated_pass1 = FR.runs_completed_in_window([straddler_in_progress], window1)
        assert enumerated_pass1 == []  # not counted while in progress

        # Pass 2 (a week later): the same run has now completed, after cursor1.
        straddler_completed = _run(
            32549865287, "success", status="completed", created_at="2026-08-21T20:00:00", completed_at="2026-08-21T23:20:00"
        )
        window2 = FR.resolve_window(cursor_after_pass1, _dt("2026-08-28T23:14:07"))
        enumerated_pass2 = FR.runs_completed_in_window([straddler_completed], window2)
        assert [run.run_id for run in enumerated_pass2] == [32549865287]  # counted exactly once, in pass 2

    def test_rerun_new_attempt_repicked_by_completion_time_not_blocked_by_prior_attempt(self) -> None:
        previous_report_cursor = FR.Cursor(completed_through=_dt("2026-08-14T23:14:07"), in_progress_low_water=None)
        original_attempt = _run(
            42_000_001, "failure", attempt=1, completed_at="2026-08-13T10:00:00"
        )  # already before the cursor, from a prior window
        rerun_attempt = _run(
            42_000_001, "success", attempt=2, completed_at="2026-08-21T09:00:00"
        )  # same run_id, new attempt, completes after the cursor

        assert original_attempt.enumeration_key != rerun_attempt.enumeration_key

        window = FR.resolve_window(previous_report_cursor, _dt("2026-08-21T23:14:07"))
        enumerated = FR.runs_completed_in_window([original_attempt, rerun_attempt], window)
        assert [run.attempt for run in enumerated] == [2]  # only the new attempt falls in the window

    def test_in_progress_low_water_carried_forward_when_batch_has_no_in_progress_runs(self) -> None:
        previous = FR.Cursor(completed_through=_dt("2026-08-14T00:00:00"), in_progress_low_water=_dt("2026-08-13T22:00:00"))
        all_completed = [_run(1, "success", completed_at="2026-08-14T05:00:00")]
        cursor = FR.advance_cursor(all_completed, previous)
        assert cursor.in_progress_low_water == _dt("2026-08-13T22:00:00")


class TestInProgressLowWaterWiring:
    """renata S1: ``in_progress_low_water`` was computed and serialized but
    never read back -- FR-004's re-enumeration was unimplemented. Wired via
    :func:`resolve_window` (widen ``window.start``) paired with
    :func:`runs_completed_in_window`'s ``already_enumerated`` dedup so the
    widened window never double-counts a run already reported once.
    """

    def test_resolve_window_starts_at_low_water_when_earlier_than_completed_through(self) -> None:
        now = _dt("2026-08-22T05:00:00")
        prior = FR.Cursor(
            completed_through=_dt("2026-08-21T12:00:00"), in_progress_low_water=_dt("2026-08-21T09:00:00")
        )
        window = FR.resolve_window(prior, now)
        assert window.start == _dt("2026-08-21T09:00:00")

    def test_resolve_window_keeps_completed_through_when_low_water_is_later(self) -> None:
        # in_progress_low_water can legitimately be *after* completed_through
        # (a fresh in-progress run that started after the last cursor
        # advance) -- the window must not be narrowed by it.
        now = _dt("2026-08-22T05:00:00")
        prior = FR.Cursor(
            completed_through=_dt("2026-08-14T23:14:07"), in_progress_low_water=_dt("2026-08-21T20:00:00")
        )
        window = FR.resolve_window(prior, now)
        assert window.start == _dt("2026-08-14T23:14:07")

    def test_straddling_run_re_enumerated_while_already_counted_run_is_deduped(self) -> None:
        # This test's pass/fail depends on the low-water wiring: without it,
        # window.start stays at completed_through (12:00) and the straddler
        # would still be caught by the plain completed_at boundary -- but
        # WITH the widened window, the already-counted run at 11:00 would be
        # wrongly re-admitted unless already_enumerated dedups it.
        previous = FR.Cursor(
            completed_through=_dt("2026-08-21T12:00:00"), in_progress_low_water=_dt("2026-08-21T09:00:00")
        )
        now = _dt("2026-08-22T05:00:00")
        window = FR.resolve_window(previous, now)
        assert window.start == _dt("2026-08-21T09:00:00")

        already_counted = _run(100, "success", completed_at="2026-08-21T11:00:00")  # counted last report
        straddler = _run(200, "success", completed_at="2026-08-21T13:30:00")  # was in-progress last time

        deduped = FR.runs_completed_in_window(
            [already_counted, straddler], window, already_enumerated=frozenset({100})
        )
        assert [run.run_id for run in deduped] == [200]

        # Without the dedup, the widened window would double-count run 100.
        not_deduped = FR.runs_completed_in_window([already_counted, straddler], window)
        assert {run.run_id for run in not_deduped} == {100, 200}


# ---------------------------------------------------------------------------
# FR-015/NFR-004: coverage + deterministic state
# ---------------------------------------------------------------------------


class TestDeterministicOrdering:
    def test_sorted_run_ids_dedupes_and_orders_ascending(self) -> None:
        runs = [_run(3, "success"), _run(1, "success"), _run(2, "success"), _run(1, "failure", attempt=2)]
        assert FR.sorted_run_ids(runs) == [1, 2, 3]

    def test_stable_sorted_nodeids_dedupes_and_orders(self) -> None:
        result = FR.stable_sorted_nodeids([_REAL_NODEID, _TIMING_NODEID_1, _REAL_NODEID])
        assert result == sorted({_REAL_NODEID, _TIMING_NODEID_1})


class TestBuildReportState:
    def test_captures_enumerated_run_ids_and_headline_from_window_and_counts(self) -> None:
        previous = FR.Cursor(completed_through=_dt("2026-08-14T23:14:07"), in_progress_low_water=None)
        now = _dt("2026-08-21T23:14:07")
        window = FR.resolve_window(previous, now)
        runs = [
            _run(32554963783, "failure", completed_at="2026-08-21T22:00:00"),
            _run(32549865287, "success", completed_at="2026-08-21T22:30:00"),
            _run(32549865286, "cancelled", completed_at="2026-08-21T22:45:00"),  # excluded taxonomy, not enumerated
            _run(32549865285, "failure", completed_at="2026-08-14T23:14:07"),  # exactly at boundary, excluded
        ]
        counts = FR.bucket_counts([FR.BUCKET_REAL])

        state = FR.build_report_state(
            generated_at=now,
            target_workflow="ci-quality.yml",
            cursor=FR.advance_cursor(runs, previous),
            runs=runs,
            window=window,
            counts=counts,
        )

        assert state.lineage == FR.LINEAGE_OK
        assert state.enumerated_run_ids == (32549865287, 32554963783)  # cancelled + boundary run excluded
        assert state.headline.completed_runs == 2
        assert state.headline.failures == 1
        assert state.headline.classifier_coverage == 1.0
        # cancelled run's completed_at (22:45) does not advance the cursor
        # (excluded taxonomy); the boundary run (exactly at window.start)
        # doesn't either. Max of the two completed runs' times wins.
        assert state.cursor.completed_through == _dt("2026-08-21T22:30:00")

"""Fidelity + CLI-layer tests for the CI flake-report workflow (WP02).

Drives the golden fixture (``tests/ci/fixtures/flake_report/``) through the
WP01 pure core + WP02 IO shell/render layer with NO live ``gh`` call, per
FR-017/NFR-003:

- Classification against ``runs.json`` + ``logs/*.log`` reproduces
  ``expected.json``'s buckets and ``false_red_rate`` within ±2pp, and
  per-test medians within ±10%.
- An unmatched failure signature routes to ``needs_review`` (never silent
  mis-bucketing).
- ``render_markdown`` is deterministic (NFR-004): the same logical model,
  rebuilt with a different internal iteration order (simulating Python's
  per-process hash-randomized set/dict ordering), renders byte-identically
  once the single varying field (``generated_at``) is stripped.

Plus targeted unit coverage for the IO-shell/parsing/bundle helpers that
``flake_report_cli.py`` adds around the WP01 core (T006-T008): log-prefix
stripping, CALL-only duration extraction, ``gh`` JSON parsing, caps/drop
accounting, ``load_state`` lineage classification, ``write_bundle`` end to
end, and ``run_gh``'s failure/timeout handling.

``scripts/ci`` is not an importable package (mirrors
``tests/ci/test_flake_report_core.py`` / ``test_sonar_project_version.py``),
so ``flake_report_cli.py`` is loaded by file path; ``CLI.FR`` is used for the
WP01 core rather than loading ``flake_report.py`` a second time under a
different module identity (pytest.ini deliberately excludes the repo root
from ``pythonpath`` to avoid exactly that dual-module-identity hazard).
"""

from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLI_SCRIPT_PATH = _REPO_ROOT / "scripts" / "ci" / "flake_report_cli.py"
_FIXTURE_DIR = _REPO_ROOT / "tests" / "ci" / "fixtures" / "flake_report"

_RATE_TOLERANCE_PP = 0.02  # NFR-003: false-red rate within +/-2 percentage points
_MEDIAN_RELATIVE_TOLERANCE = 0.10  # NFR-003: per-test median within +/-10%


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build an import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CLI: Any = _load_module(_CLI_SCRIPT_PATH, "flake_report_cli")
FR: Any = CLI.FR  # the exact flake_report module object CLI itself imports


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def _fixture_runs_json_text() -> str:
    return (_FIXTURE_DIR / "runs.json").read_text(encoding="utf-8")


def _fixture_expected() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((_FIXTURE_DIR / "expected.json").read_text(encoding="utf-8")))


def _fixture_logs_by_run_id(failure_runs: list[Any]) -> dict[int, str]:
    return {run.run_id: (_FIXTURE_DIR / "logs" / f"{run.run_id}.log").read_text(encoding="utf-8") for run in failure_runs}


def _failure_like_runs(runs: list[Any]) -> list[Any]:
    """Runs matching FAILURE_LIKE_CONCLUSIONS (failure/timed_out/startup_failure), not bare "failure"."""
    return [run for run in runs if run.conclusion in CLI.FAILURE_LIKE_CONCLUSIONS]


def _classify_fixture() -> tuple[list[tuple[Any, str, str]], dict[str, Any]]:
    """Run the fixture through parse -> classify, returning (classified, expected)."""
    raw = _fixture_runs_json_text()
    runs = CLI.parse_runs_json(raw)
    job_names_by_run_id = CLI.parse_failed_job_names(raw)
    failure_runs = _failure_like_runs(runs)
    logs_by_run_id = _fixture_logs_by_run_id(failure_runs)
    classified = CLI.classify_all(failure_runs, logs_by_run_id, job_names_by_run_id)
    return classified, _fixture_expected()


# ---------------------------------------------------------------------------
# FR-017/NFR-003: golden fixture fidelity
# ---------------------------------------------------------------------------


class TestGoldenFixtureFidelity:
    def test_reproduces_expected_buckets_exactly(self) -> None:
        classified, expected = _classify_fixture()
        counts = FR.bucket_counts(bucket for _, bucket, _ in classified)
        assert counts.as_mapping() == expected["buckets"]

    def test_reproduces_false_red_rate_within_two_percentage_points(self) -> None:
        classified, expected = _classify_fixture()
        counts = FR.bucket_counts(bucket for _, bucket, _ in classified)
        rate = FR.false_red_rate(counts.as_mapping())
        assert abs(rate - expected["false_red_rate"]) <= _RATE_TOLERANCE_PP

    def test_reproduces_per_test_medians_within_ten_percent(self) -> None:
        raw = _fixture_runs_json_text()
        runs = CLI.parse_runs_json(raw)
        failure_runs = _failure_like_runs(runs)
        logs_by_run_id = _fixture_logs_by_run_id(failure_runs)
        job_names_by_run_id = CLI.parse_failed_job_names(raw)

        aggs, _disclosed = CLI.mine_durations(failure_runs, logs_by_run_id, job_names_by_run_id)
        actual_medians = {agg.nodeid: agg.median_s for agg in aggs}

        expected = _fixture_expected()
        assert expected["duration_medians"], "fixture must pin at least one per-test median expectation"
        for nodeid, expected_median in expected["duration_medians"].items():
            actual = actual_medians[nodeid]
            assert math.isclose(actual, expected_median, rel_tol=_MEDIAN_RELATIVE_TOLERANCE), (
                f"{nodeid}: actual median {actual}s vs expected {expected_median}s "
                f"exceeds the +/-{_MEDIAN_RELATIVE_TOLERANCE:.0%} tolerance"
            )

    def test_tally_honours_conclusion_taxonomy_over_the_full_fixture(self) -> None:
        raw = _fixture_runs_json_text()
        runs = CLI.parse_runs_json(raw)
        tally = FR.tally(runs)
        expected = _fixture_expected()
        assert tally.total_runs == expected["total_runs"]
        assert tally.completed_runs == expected["completed_runs"]

    def test_tally_reproduces_distinct_prs_and_prs_with_failure_excluding_non_completed(self) -> None:
        # renata S2/paula 8: the fixture's cancelled/action_required runs
        # (PRs 3613/3614 + two forked-branch pushes) carry PR identities that
        # must NOT inflate distinct_prs now that tally() scopes to completed
        # runs only.
        raw = _fixture_runs_json_text()
        runs = CLI.parse_runs_json(raw)
        tally = FR.tally(runs)
        expected = _fixture_expected()
        assert tally.distinct_prs == expected["distinct_prs"]
        assert tally.prs_with_failure == expected["prs_with_failure"]

    def test_excluded_conclusions_present_in_fixture_are_excluded_from_tally(self) -> None:
        raw = _fixture_runs_json_text()
        runs = CLI.parse_runs_json(raw)
        excluded_conclusions = {run.conclusion for run in runs if FR.is_excluded(run.conclusion)}
        # The fixture must actually exercise the exclusion set (cancelled/action_required/skipped),
        # not merely assert an accidental absence.
        assert excluded_conclusions >= {"cancelled", "action_required", "skipped"}
        completed = FR.tally(runs).completed_runs
        assert completed == len(runs) - sum(1 for run in runs if FR.is_excluded(run.conclusion))

    def test_unmatched_failure_signature_routes_to_needs_review(self) -> None:
        # A failure log with no FAILED nodeid, no infra keyword, and no gate job name --
        # the honest fallback per FR-002, never silent mis-bucketing.
        bucket, reason = CLI.classify_failure_run(
            "some unrecognized tooling crash with no known signature", job_names=["fast-tests-unknown-shard"]
        )
        assert bucket == FR.BUCKET_NEEDS_REVIEW


class TestClassifyFailureRunThreadsConclusion:
    """renata N1/paula 4, at the CLI layer: :func:`CLI.classify_failure_run`
    and :func:`CLI.classify_all` must thread a run's ``conclusion`` through
    to ``FR.classify_one`` so a startup_failure/timed_out run with an
    unfetchable log (empty string, no signal) still lands on ``infra_flake``.
    """

    def test_classify_failure_run_threads_startup_failure_conclusion(self) -> None:
        bucket, reason = CLI.classify_failure_run("", job_names=[], conclusion="startup_failure")
        assert bucket == FR.BUCKET_INFRA_FLAKE
        assert "startup_failure" in reason

    def test_classify_failure_run_defaults_conclusion_to_none(self) -> None:
        bucket, _reason = CLI.classify_failure_run("", job_names=[])
        assert bucket == FR.BUCKET_NEEDS_REVIEW

    def test_classify_all_passes_each_runs_own_conclusion(self) -> None:
        timed_out_run = FR.Run(
            run_id=9001,
            attempt=1,
            conclusion="timed_out",
            status="completed",
            event="pull_request",
            draft=False,
            created_at=_dt("2026-08-19T23:55:00+00:00"),
            completed_at=_dt("2026-08-20T00:00:00+00:00"),
            pr_number=1,
            head_branch="main",
        )
        results = CLI.classify_all([timed_out_run], {timed_out_run.run_id: ""}, {timed_out_run.run_id: []})
        assert len(results) == 1
        _run_obj, bucket, reason = results[0]
        assert bucket == FR.BUCKET_INFRA_FLAKE
        assert "timed_out" in reason


# ---------------------------------------------------------------------------
# NFR-004: markdown determinism
# ---------------------------------------------------------------------------


def _sample_report_model(*, reordered: bool) -> dict[str, Any]:
    buckets_ordered = {
        FR.BUCKET_PERF_TIMING_FLAKE: 14,
        FR.BUCKET_INFRA_FLAKE: 3,
        FR.BUCKET_REAL: 12,
        FR.BUCKET_NEEDS_REVIEW: 0,
    }
    buckets = dict(reversed(buckets_ordered.items())) if reordered else buckets_ordered

    suites = ["fast-tests-sync-daemon", "mypy-strict-gate", "ruff-lint"]
    suites_without = list(reversed(suites)) if reordered else suites

    tests = [
        {
            "nodeid": "tests/perf/test_tasks_status_baseline.py::test_tasks_status_p95_within_nfr005_budget",
            "n": 2,
            "median_s": 30.35,
            "mean_s": 30.35,
            "max_s": 32.6,
            "long_pole": True,
        },
        {
            "nodeid": "tests/status/test_transitions.py::test_reject_blocked_to_done_without_force",
            "n": 1,
            "median_s": 0.42,
            "mean_s": 0.42,
            "max_s": 0.42,
            "long_pole": False,
        },
    ]
    tests_ordered = list(reversed(tests)) if reordered else tests

    metrics = {
        "window": {"start": "2026-08-14T23:14:07+00:00", "end": "2026-08-21T23:14:07+00:00", "target_workflow": "ci-quality.yml"},
        "denominators": {"total_runs": 63, "completed_runs": 57, "distinct_prs": 13, "prs_with_failure": 8},
        "false_red_rate": 0.5862,
        "classifier_coverage": 1.0,
        "failures": {"total": 29, "buckets": buckets},
        "delta_vs_prev": {"false_red_rate": -0.02, "failures": -4, "needs_review": 0},
        "caps_applied": {"classified_failures_cap": 200, "duration_runs_cap": 50, "dropped": 0},
    }
    durations = {"runs_sampled": 29, "suites_without_durations": sorted(suites_without), "tests": tests_ordered}
    return {"metrics": metrics, "durations": durations, "lineage": "ok", "generated_at": "2026-08-22T05:00:00+00:00"}


def _strip_generated_at(rendered: str) -> str:
    return "\n".join(line for line in rendered.splitlines() if not line.startswith("Generated:"))


class TestMarkdownDeterminism:
    def test_render_markdown_is_byte_identical_across_reordered_equivalent_input(self) -> None:
        canonical = CLI.render_markdown(_sample_report_model(reordered=False))
        reordered = CLI.render_markdown(_sample_report_model(reordered=True))
        assert _strip_generated_at(canonical) == _strip_generated_at(reordered)
        # Sanity: the models really were logically identical (not accidentally
        # identical because "reordered" didn't change anything).
        assert list(_sample_report_model(reordered=False)["metrics"]["failures"]["buckets"].keys()) != list(
            _sample_report_model(reordered=True)["metrics"]["failures"]["buckets"].keys()
        )

    def test_render_markdown_reports_headline_figures(self) -> None:
        rendered = CLI.render_markdown(_sample_report_model(reordered=False))
        assert "58.6%" in rendered
        assert "| perf_timing_flake | 14 |" in rendered
        assert "test_tasks_status_p95_within_nfr005_budget" in rendered

    def test_render_markdown_discloses_suites_without_durations(self) -> None:
        rendered = CLI.render_markdown(_sample_report_model(reordered=False))
        assert "mypy-strict-gate" in rendered
        assert "absence" in rendered.lower()

    def test_render_markdown_no_previous_report_states_so_explicitly(self) -> None:
        model = _sample_report_model(reordered=False)
        model["metrics"]["delta_vs_prev"] = None
        rendered = CLI.render_markdown(model)
        assert "first run or lost baseline" in rendered


# ---------------------------------------------------------------------------
# T006: IO-shell parsing helpers
# ---------------------------------------------------------------------------


class TestStripGhLogPrefix:
    def test_strips_job_and_step_tsv_columns(self) -> None:
        raw = "fast-tests-status\tRun pytest\tFAILED tests/status/test_x.py::test_y - AssertionError"
        assert CLI._strip_gh_log_prefix(raw) == "FAILED tests/status/test_x.py::test_y - AssertionError"

    def test_bare_lines_without_tabs_pass_through_unchanged(self) -> None:
        raw = "FAILED tests/status/test_x.py::test_y - AssertionError\n30.35s call tests/x.py::test_y"
        assert CLI._strip_gh_log_prefix(raw) == raw


class TestExtractDurations:
    def test_keeps_only_call_phase_not_setup_or_teardown(self) -> None:
        log = (
            "30.35s call     tests/perf/test_x.py::test_y\n"
            "0.02s setup    tests/perf/test_x.py::test_y\n"
            "0.01s teardown tests/perf/test_x.py::test_y\n"
        )
        samples = CLI.extract_durations(log)
        assert len(samples) == 1
        assert samples[0].nodeid == "tests/perf/test_x.py::test_y"
        assert samples[0].duration_s == 30.35

    def test_no_duration_lines_yields_empty_list(self) -> None:
        assert CLI.extract_durations("FAILED tests/x.py::test_y - boom\n") == []


class TestParseRunsJson:
    def test_sorts_by_created_at_then_run_id(self) -> None:
        raw = json.dumps(
            [
                {
                    "databaseId": 2,
                    "attempt": 1,
                    "conclusion": "success",
                    "status": "completed",
                    "event": "push",
                    "headBranch": "main",
                    "createdAt": "2026-08-15T09:00:00Z",
                    "updatedAt": "2026-08-15T09:10:00Z",
                    "isDraft": False,
                    "pullRequests": [],
                },
                {
                    "databaseId": 1,
                    "attempt": 1,
                    "conclusion": "success",
                    "status": "completed",
                    "event": "push",
                    "headBranch": "main",
                    "createdAt": "2026-08-14T09:00:00Z",
                    "updatedAt": "2026-08-14T09:10:00Z",
                    "isDraft": False,
                    "pullRequests": [],
                },
            ]
        )
        runs = CLI.parse_runs_json(raw)
        assert [run.run_id for run in runs] == [1, 2]

    def test_maps_pull_request_number_and_push_head_branch_fallback(self) -> None:
        raw = json.dumps(
            [
                {
                    "databaseId": 42,
                    "attempt": 1,
                    "conclusion": "failure",
                    "status": "completed",
                    "event": "pull_request",
                    "headBranch": "kitty/mission-x-lane-1",
                    "createdAt": "2026-08-15T09:00:00Z",
                    "updatedAt": "2026-08-15T09:10:00Z",
                    "isDraft": False,
                    "pullRequests": [{"number": 3596}],
                },
                {
                    "databaseId": 43,
                    "attempt": 1,
                    "conclusion": "success",
                    "status": "completed",
                    "event": "push",
                    "headBranch": "main",
                    "createdAt": "2026-08-15T10:00:00Z",
                    "updatedAt": "2026-08-15T10:10:00Z",
                    "isDraft": False,
                    "pullRequests": [],
                },
            ]
        )
        runs = CLI.parse_runs_json(raw)
        by_id = {run.run_id: run for run in runs}
        assert by_id[42].pr_number == 3596
        assert by_id[43].pr_number is None
        assert by_id[43].head_branch == "main"

    def test_completed_at_only_set_when_status_is_completed(self) -> None:
        raw = json.dumps(
            [
                {
                    "databaseId": 7,
                    "attempt": 1,
                    "conclusion": None,
                    "status": "in_progress",
                    "event": "push",
                    "headBranch": "main",
                    "createdAt": "2026-08-15T09:00:00Z",
                    "updatedAt": "2026-08-15T09:05:00Z",
                    "isDraft": False,
                    "pullRequests": [],
                }
            ]
        )
        runs = CLI.parse_runs_json(raw)
        assert runs[0].completed_at is None
        assert runs[0].conclusion is None

    def test_rejects_non_array_payload(self) -> None:
        with pytest.raises(ValueError, match="JSON array"):
            CLI.parse_runs_json(json.dumps({"not": "a list"}))


class TestParseFailedJobNames:
    def test_extracts_side_channel_field_only_when_present(self) -> None:
        raw = json.dumps(
            [
                {"databaseId": 1, "failedJobNames": ["mypy-strict-gate"]},
                {"databaseId": 2},
            ]
        )
        result = CLI.parse_failed_job_names(raw)
        assert result == {1: ["mypy-strict-gate"]}


# ---------------------------------------------------------------------------
# T007: caps + drop accounting
# ---------------------------------------------------------------------------


def _fake_run(run_id: int, completed_at: str) -> Any:
    return FR.Run(
        run_id=run_id,
        attempt=1,
        conclusion="failure",
        status="completed",
        event="pull_request",
        draft=False,
        created_at=_dt(completed_at) - timedelta(minutes=5),
        completed_at=_dt(completed_at),
        pr_number=1,
        head_branch="main",
    )


class TestCaps:
    def test_apply_classified_cap_drops_the_oldest_beyond_the_cap(self) -> None:
        runs = [_fake_run(i, f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00") for i in range(1, 251)]
        selected, dropped = CLI.apply_classified_cap(runs, cap=200)
        assert len(selected) == 200
        assert dropped == 50

    def test_apply_classified_cap_under_cap_drops_nothing(self) -> None:
        runs = [_fake_run(i, "2026-08-15T00:00:00+00:00") for i in range(1, 5)]
        selected, dropped = CLI.apply_classified_cap(runs, cap=200)
        assert len(selected) == 4
        assert dropped == 0

    def test_apply_duration_cap_selects_most_recent_n(self) -> None:
        runs = [
            _fake_run(1, "2026-08-10T00:00:00+00:00"),
            _fake_run(2, "2026-08-20T00:00:00+00:00"),
            _fake_run(3, "2026-08-15T00:00:00+00:00"),
        ]
        selected = CLI.apply_duration_cap(runs, cap=2)
        assert [run.run_id for run in selected] == [2, 3]


# ---------------------------------------------------------------------------
# T008: load_state lineage classification
# ---------------------------------------------------------------------------


class TestLoadState:
    def test_missing_path_is_true_first_run(self, tmp_path: Path) -> None:
        loaded = CLI.load_state(tmp_path / "does-not-exist.json")
        assert loaded.cursor is None
        assert loaded.baseline_valid is True
        assert loaded.previous_headline is None

    def test_none_path_is_true_first_run(self) -> None:
        loaded = CLI.load_state(None)
        assert loaded.cursor is None
        assert loaded.baseline_valid is True

    def test_corrupt_json_is_lost_baseline(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text("{not valid json", encoding="utf-8")
        loaded = CLI.load_state(state_path)
        assert loaded.cursor is not None  # sentinel, not None -> lost_baseline (not first_run)
        assert loaded.baseline_valid is False

    def test_wrong_schema_is_lost_baseline(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"schema": 999, "cursor": {}}), encoding="utf-8")
        loaded = CLI.load_state(state_path)
        assert loaded.baseline_valid is False

    def test_valid_state_round_trips_cursor_and_headline(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "cursor": {
                        "completed_through": "2026-08-21T23:14:07+00:00",
                        "in_progress_low_water": "2026-08-21T22:50:00+00:00",
                    },
                    "headline": {"false_red_rate": 0.6, "failures": 30, "buckets": {"needs_review": 1}},
                }
            ),
            encoding="utf-8",
        )
        loaded = CLI.load_state(state_path)
        assert loaded.baseline_valid is True
        assert loaded.cursor.completed_through == _dt("2026-08-21T23:14:07+00:00")
        assert loaded.cursor.in_progress_low_water == _dt("2026-08-21T22:50:00+00:00")
        assert loaded.previous_headline["failures"] == 30

    def test_resolve_window_treats_corrupt_state_as_lost_baseline_not_first_run(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text("garbage", encoding="utf-8")
        loaded = CLI.load_state(state_path)
        now = _dt("2026-08-22T05:00:00+00:00")
        window = FR.resolve_window(loaded.cursor, now, baseline_valid=loaded.baseline_valid)
        assert window.lineage == FR.LINEAGE_LOST_BASELINE


class TestComputeDelta:
    def test_none_previous_headline_yields_none_delta(self) -> None:
        headline = FR.Headline(
            window_start=_dt("2026-08-14T00:00:00+00:00"),
            window_end=_dt("2026-08-21T00:00:00+00:00"),
            completed_runs=57,
            failures=29,
            false_red_rate=0.586,
            buckets=FR.BucketCounts(perf_timing_flake=14, infra_flake=3, real=12, needs_review=0),
            classifier_coverage=1.0,
        )
        assert CLI.compute_delta(headline, None) is None

    def test_malformed_previous_headline_yields_none_delta(self) -> None:
        headline = FR.Headline(
            window_start=_dt("2026-08-14T00:00:00+00:00"),
            window_end=_dt("2026-08-21T00:00:00+00:00"),
            completed_runs=57,
            failures=29,
            false_red_rate=0.586,
            buckets=FR.BucketCounts(perf_timing_flake=14, infra_flake=3, real=12, needs_review=0),
            classifier_coverage=1.0,
        )
        assert CLI.compute_delta(headline, {"missing": "fields"}) is None

    def test_happy_path_computes_false_red_rate_failures_and_needs_review_deltas(self) -> None:
        # paula 2: two well-formed headlines -> correct arithmetic, not just
        # the None-guard paths already covered above.
        headline = FR.Headline(
            window_start=_dt("2026-08-14T00:00:00+00:00"),
            window_end=_dt("2026-08-21T00:00:00+00:00"),
            completed_runs=60,
            failures=25,
            false_red_rate=0.55,
            buckets=FR.BucketCounts(perf_timing_flake=10, infra_flake=3, real=10, needs_review=2),
            classifier_coverage=0.92,
        )
        previous_headline = {
            "false_red_rate": 0.60,
            "failures": 29,
            "buckets": {FR.BUCKET_NEEDS_REVIEW: 4},
        }
        delta = CLI.compute_delta(headline, previous_headline)
        assert delta == {
            "false_red_rate": round(0.55 - 0.60, 4),
            "failures": 25 - 29,
            "needs_review": 2 - 4,
        }


# ---------------------------------------------------------------------------
# T008: write_bundle end to end
# ---------------------------------------------------------------------------


class TestWriteBundleEndToEnd:
    def test_writes_all_four_artifacts_with_consistent_headline_figures(self, tmp_path: Path) -> None:
        raw = _fixture_runs_json_text()
        runs = CLI.parse_runs_json(raw)
        job_names_by_run_id = CLI.parse_failed_job_names(raw)
        failure_runs = _failure_like_runs(runs)
        logs_by_run_id = _fixture_logs_by_run_id(failure_runs)

        classified = CLI.classify_all(failure_runs, logs_by_run_id, job_names_by_run_id)
        counts = FR.bucket_counts(bucket for _, bucket, _ in classified)
        duration_aggs, suites_without = CLI.mine_durations(failure_runs, logs_by_run_id, job_names_by_run_id)

        now = _dt("2026-08-22T05:00:00+00:00")
        cursor = FR.Cursor(completed_through=_dt("2026-08-14T23:14:07+00:00"), in_progress_low_water=None)
        window = FR.Window(
            start=_dt("2026-08-14T23:14:07+00:00"), end=now, lineage=FR.LINEAGE_OK
        )
        state = FR.build_report_state(
            generated_at=now, target_workflow="ci-quality.yml", cursor=cursor, runs=runs, window=window, counts=counts
        )
        tally = FR.tally(runs)
        out_dir = tmp_path / "out"

        CLI.write_bundle(
            out_dir,
            state=state,
            tally=tally,
            duration_aggs=duration_aggs,
            duration_runs_sampled=len(failure_runs),
            suites_without_durations=suites_without,
            caps_applied={"classified_failures_cap": 200, "duration_runs_cap": 50, "dropped": 0},
            previous_headline=None,
        )

        assert {p.name for p in out_dir.iterdir()} == {
            CLI.METRICS_FILENAME,
            CLI.DURATIONS_FILENAME,
            CLI.REPORT_FILENAME,
            CLI.STATE_FILENAME,
        }
        metrics = json.loads((out_dir / CLI.METRICS_FILENAME).read_text(encoding="utf-8"))
        assert metrics["failures"]["buckets"] == counts.as_mapping()
        assert abs(metrics["false_red_rate"] - 0.586) <= _RATE_TOLERANCE_PP
        assert metrics["delta_vs_prev"] is None
        assert metrics["caps_applied"]["dropped"] == 0

        durations = json.loads((out_dir / CLI.DURATIONS_FILENAME).read_text(encoding="utf-8"))
        assert durations["tests"] == sorted(durations["tests"], key=lambda t: t["nodeid"])

        state_json = json.loads((out_dir / CLI.STATE_FILENAME).read_text(encoding="utf-8"))
        assert state_json["lineage"] == FR.LINEAGE_OK
        assert state_json["schema"] == CLI.STATE_SCHEMA_VERSION

        report_text = (out_dir / CLI.REPORT_FILENAME).read_text(encoding="utf-8")
        assert "CI Flake Report" in report_text
        assert "58.6%" in report_text or "58.5%" in report_text or "58.7%" in report_text


# ---------------------------------------------------------------------------
# T006: run_gh error handling + live-fetch wrappers (monkeypatched, no real gh)
# ---------------------------------------------------------------------------


class TestRunGh:
    def test_raises_gh_command_error_on_nonzero_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=["gh"], returncode=1, stdout="", stderr="not authenticated")

        monkeypatch.setattr(CLI.subprocess, "run", _fake_run)
        with pytest.raises(CLI.GhCommandError, match="not authenticated"):
            CLI.run_gh(["run", "list"])

    def test_raises_gh_command_error_on_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fake_run(*_args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd="gh", timeout=kwargs.get("timeout", 30.0))

        monkeypatch.setattr(CLI.subprocess, "run", _fake_run)
        with pytest.raises(CLI.GhCommandError, match="timed out"):
            CLI.run_gh(["run", "list"], timeout=1.0)

    def test_raises_gh_command_error_when_gh_not_on_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError("gh")

        monkeypatch.setattr(CLI.subprocess, "run", _fake_run)
        with pytest.raises(CLI.GhCommandError, match="not found"):
            CLI.run_gh(["run", "list"])

    def test_returns_stdout_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=["gh"], returncode=0, stdout="[]", stderr="")

        monkeypatch.setattr(CLI.subprocess, "run", _fake_run)
        assert CLI.run_gh(["run", "list"]) == "[]"


class TestFetchLogsAndJobs:
    def test_delegates_to_failed_log_and_run_job_names_per_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def _fake_failed_log(run_id: int, **_kwargs: Any) -> str:
            calls.append(run_id)
            return f"log-for-{run_id}"

        def _fake_run_job_names(run_id: int, **_kwargs: Any) -> list[str]:
            return [f"job-for-{run_id}"]

        monkeypatch.setattr(CLI, "failed_log", _fake_failed_log)
        monkeypatch.setattr(CLI, "run_job_names", _fake_run_job_names)

        runs = [_fake_run(1, "2026-08-15T00:00:00+00:00"), _fake_run(2, "2026-08-16T00:00:00+00:00")]
        logs, jobs = CLI.fetch_logs_and_jobs(runs)

        assert calls == [1, 2]
        assert logs == {1: "log-for-1", 2: "log-for-2"}
        assert jobs == {1: ["job-for-1"], 2: ["job-for-2"]}

    def test_isolates_gh_command_error_per_run_and_continues(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # paula 5: one run's expired/404 log/jobs fetch must not abort the
        # whole report -- it degrades to an unfetchable (empty) entry and the
        # batch continues for every other run.
        def _fake_failed_log(run_id: int, **_kwargs: Any) -> str:
            if run_id == 1:
                raise CLI.GhCommandError("log expired")
            return f"log-for-{run_id}"

        def _fake_run_job_names(run_id: int, **_kwargs: Any) -> list[str]:
            if run_id == 2:
                raise CLI.GhCommandError("404 not found")
            return [f"job-for-{run_id}"]

        monkeypatch.setattr(CLI, "failed_log", _fake_failed_log)
        monkeypatch.setattr(CLI, "run_job_names", _fake_run_job_names)

        runs = [_fake_run(1, "2026-08-15T00:00:00+00:00"), _fake_run(2, "2026-08-16T00:00:00+00:00")]
        logs, jobs = CLI.fetch_logs_and_jobs(runs)

        assert logs == {1: "", 2: "log-for-2"}
        assert jobs == {1: ["job-for-1"], 2: []}

        # An unfetchable run (empty log, no other signal) still classifies
        # honestly instead of crashing the report.
        bucket, _reason = CLI.classify_failure_run(logs[1], jobs[1])
        assert bucket == FR.BUCKET_NEEDS_REVIEW


# ---------------------------------------------------------------------------
# main() / argparse wiring
# ---------------------------------------------------------------------------


class TestArgParser:
    def test_defaults(self) -> None:
        parser = CLI._build_arg_parser()
        args = parser.parse_args([])
        assert args.workflow == CLI.DEFAULT_WORKFLOW
        assert args.since is None
        assert args.state is None
        assert args.out == Path(CLI.DEFAULT_OUT_DIR)

    def test_overrides(self) -> None:
        parser = CLI._build_arg_parser()
        args = parser.parse_args(
            ["--workflow", "custom.yml", "--since", "2026-08-01T00:00:00", "--state", "prior.json", "--out", "out-dir"]
        )
        assert args.workflow == "custom.yml"
        assert args.since == "2026-08-01T00:00:00"
        assert args.state == Path("prior.json")
        assert args.out == Path("out-dir")

    def test_main_invokes_run_report_and_returns_zero(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        captured: dict[str, Any] = {}

        def _fake_run_report(**kwargs: Any) -> Any:
            captured.update(kwargs)
            return FR.ReportState(
                schema=1,
                generated_at=datetime.now(UTC),
                target_workflow=kwargs["workflow"],
                cursor=FR.Cursor(completed_through=datetime.now(UTC), in_progress_low_water=None),
                enumerated_run_ids=(),
                lineage=FR.LINEAGE_FIRST_RUN,
                headline=FR.Headline(
                    window_start=datetime.now(UTC),
                    window_end=datetime.now(UTC),
                    completed_runs=0,
                    failures=0,
                    false_red_rate=0.0,
                    buckets=FR.BucketCounts(),
                    classifier_coverage=1.0,
                ),
            )

        monkeypatch.setattr(CLI, "run_report", _fake_run_report)
        exit_code = CLI.main(["--workflow", "ci-quality.yml", "--out", str(tmp_path / "out")])
        assert exit_code == 0
        assert captured["workflow"] == "ci-quality.yml"
        assert captured["out_dir"] == tmp_path / "out"


# ---------------------------------------------------------------------------
# paula 2/3: run_report end-to-end (monkeypatched list_runs/fetch_logs_and_jobs)
# ---------------------------------------------------------------------------


class TestRunReportIntegration:
    """Drive :func:`CLI.run_report` end to end with monkeypatched IO so
    metrics.json/state.json stay consistent and FAILURE_LIKE_CONCLUSIONS
    selection -- including the timed_out/startup_failure runs added for
    renata N1/paula 4 -- flows all the way through the pipeline, not just
    through ``classify_one``/``classify_failure_run`` in isolation.
    """

    def test_run_report_end_to_end_with_timed_out_and_startup_failure_runs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        now = datetime.now(UTC)

        def _mk_run(run_id: int, conclusion: str, days_ago: int) -> Any:
            completed = now - timedelta(days=days_ago)
            return FR.Run(
                run_id=run_id,
                attempt=1,
                conclusion=conclusion,
                status="completed",
                event="pull_request",
                draft=False,
                created_at=completed - timedelta(minutes=10),
                completed_at=completed,
                pr_number=100 + run_id,
                head_branch=f"kitty/mission-x-lane-{run_id}",
            )

        success_run = _mk_run(1, "success", 2)
        real_failure_run = _mk_run(2, "failure", 2)
        timed_out_run = _mk_run(3, "timed_out", 1)
        startup_failure_run = _mk_run(4, "startup_failure", 1)
        cancelled_run = _mk_run(5, "cancelled", 3)
        all_runs = [success_run, real_failure_run, timed_out_run, startup_failure_run, cancelled_run]

        real_nodeid = "tests/status/test_transitions.py::test_reject_blocked_to_done_without_force"
        logs = {
            real_failure_run.run_id: f"FAILED {real_nodeid} - AssertionError",
            timed_out_run.run_id: "",  # unfetchable/empty log (renata N1/paula 4)
            startup_failure_run.run_id: "",
        }
        jobs = {real_failure_run.run_id: [], timed_out_run.run_id: [], startup_failure_run.run_id: []}

        monkeypatch.setattr(CLI, "list_runs", lambda *_args, **_kwargs: all_runs)
        monkeypatch.setattr(
            CLI,
            "fetch_logs_and_jobs",
            lambda selected: (
                {run.run_id: logs[run.run_id] for run in selected},
                {run.run_id: jobs[run.run_id] for run in selected},
            ),
        )

        out_dir = tmp_path / "out"
        state = CLI.run_report(workflow="ci-quality.yml", since=None, state_path=None, out_dir=out_dir)

        # FAILURE_LIKE_CONCLUSIONS selection flowed through end to end: 3
        # failures counted (real + timed_out + startup_failure), not just the
        # bare "failure" conclusion.
        assert state.headline.failures == 3
        assert state.headline.buckets.real == 1
        assert state.headline.buckets.infra_flake == 2
        assert state.headline.buckets.perf_timing_flake == 0
        assert state.headline.buckets.needs_review == 0

        metrics = json.loads((out_dir / CLI.METRICS_FILENAME).read_text(encoding="utf-8"))
        state_json = json.loads((out_dir / CLI.STATE_FILENAME).read_text(encoding="utf-8"))

        # metrics.json <-> state.json consistency (paula 2/3): identical
        # headline figures on both artifacts.
        assert metrics["failures"]["total"] == state_json["headline"]["failures"] == 3
        assert metrics["failures"]["buckets"] == state_json["headline"]["buckets"]
        assert metrics["false_red_rate"] == state_json["headline"]["false_red_rate"]
        assert metrics["denominators"]["total_runs"] == 5
        assert metrics["denominators"]["completed_runs"] == 4  # cancelled excluded from FR-001 taxonomy

        # enumerated_run_ids: success/failure/timed_out/startup_failure in;
        # cancelled (excluded taxonomy) never enumerated.
        assert state_json["enumerated_run_ids"] == [1, 2, 3, 4]

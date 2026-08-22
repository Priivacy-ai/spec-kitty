#!/usr/bin/env python3
"""IO shell + CLI + markdown render for the CI flake-report workflow (WP02).

``scripts/ci/flake_report.py`` (WP01) is the pure core: deterministic,
stdlib-only, IO-free classification/aggregation/cursor arithmetic. Everything
in *this* module is the opposite half of that seam — the parts that touch the
outside world (``gh`` subprocess calls, the filesystem, argv) plus the
markdown renderer, which is deterministic but consumes the core's output
rather than producing it.

Layering, so the fidelity test (T009) can drive the classifier/aggregator
against the golden fixture without a live ``gh``:

- **IO shell** (:func:`run_gh`, :func:`list_runs`, :func:`failed_log`,
  :func:`run_job_names`, :func:`run_log_durations`, :func:`fetch_logs_and_jobs`)
  — the only functions that shell out. Never called by tests directly; tests
  drive the layers below with fixture data instead.
- **Parsing** (:func:`parse_runs_json`, :func:`parse_failed_job_names`,
  :func:`extract_durations`) — pure, JSON/text in, dataclasses out. Reused by
  both the live IO shell and the fidelity test.
- **Pipeline** (:func:`classify_failure_run`, :func:`classify_all`,
  :func:`apply_classified_cap`, :func:`apply_duration_cap`,
  :func:`mine_durations`) — pure, wires already-fetched data through the WP01
  core (:mod:`scripts.ci.flake_report`).
- **Bundle + render** (:func:`load_state`, :func:`write_bundle`,
  :func:`render_markdown`) — writes ``metrics.json``/``durations.json``/
  ``report.md``/``state.json`` (C-001: findings only, never a repo commit,
  never a docs edit).
- **CLI** (:func:`main`) — argparse wiring + the live end-to-end run.

Duration mining reuses the SAME ``--log-failed`` fetch used for
classification (:func:`run_log_durations` calls :func:`failed_log`) rather
than a second full-log round-trip, per NFR-002/the mission notes ("prefer
``--log-failed``/selective ``gh api`` over full-run-log zips"). The
consequence: duration samples are drawn only from failure-run logs, not the
full completed-run population — sufficient for this mission's signal (how
much a *flaky* test's timing costs), not a general-purpose duration profiler.

Auth: ``gh`` is invoked with the ambient environment untouched, so it picks
up ``GITHUB_TOKEN`` the normal way; this module never unsets or mutates it.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.clock import UTC, datetime, now_utc, parse_iso  # noqa: E402
from scripts.ci import flake_report as FR  # noqa: E402

# ---------------------------------------------------------------------------
# Constants (S1192: literals repeated >=3x hoisted here)
# ---------------------------------------------------------------------------

ENCODING = "utf-8"
DEFAULT_WORKFLOW = "ci-quality.yml"
DEFAULT_OUT_DIR = "flake-report-out"
METRICS_FILENAME = "metrics.json"
DURATIONS_FILENAME = "durations.json"
REPORT_FILENAME = "report.md"
STATE_FILENAME = "state.json"

#: Single-sourced from WP01 (nit): this constant and ``build_report_state``'s
#: ``schema`` default must never drift onto different values.
STATE_SCHEMA_VERSION = FR.SCHEMA_VERSION
DEFAULT_FETCH_TIMEOUT_S = 30.0
CLASSIFIED_FAILURES_CAP = 200
DURATION_RUNS_CAP = 50
LIST_RUNS_LIMIT = 500

#: Conclusions this tool attempts to classify. A strict subset of WP01's
#: ``COMPLETED_CONCLUSIONS`` -- ``success`` is completed but never a
#: candidate for classification. Single-sourced from WP01 so ``tally()``'s
#: own failure-like scoping can never drift from this module's selection.
FAILURE_LIKE_CONCLUSIONS: frozenset[str] = FR.FAILURE_LIKE_CONCLUSIONS

#: Fields requested from ``gh run list --json``. NOTE: ``gh run list`` does NOT
#: expose ``pullRequests`` or ``isDraft`` (those live on ``gh run view`` / ``gh
#: pr``); requesting them makes ``gh`` exit non-zero with "Unknown JSON field".
#: ``pr_number`` therefore stays ``None`` on the live path and ``pr_identity``
#: falls back to ``headBranch`` by design; ``draft`` is unused. The recorded
#: golden fixture may still carry these keys -- ``_run_from_entry`` reads them
#: tolerantly via ``.get()`` -- so fixture-driven tests are unaffected.
RUN_LIST_JSON_FIELDS = "databaseId,attempt,conclusion,status,event,headBranch,createdAt,updatedAt"

#: Matches all three pytest ``--durations`` phase lines so setup/teardown
#: lines are correctly recognized and skipped rather than accidentally
#: mistaken for something else; FR-003 measures CALL duration specifically
#: (setup/teardown is fixture overhead, not the test's own cost), so
#: :func:`extract_durations` keeps only ``phase == "call"`` matches.
_DURATION_LINE_PATTERN = re.compile(r"(\d+\.\d+)s\s+(call|setup|teardown)\s+(\S+)")

_RENDER_BUCKET_ORDER: tuple[str, ...] = (
    FR.BUCKET_PERF_TIMING_FLAKE,
    FR.BUCKET_INFRA_FLAKE,
    FR.BUCKET_REAL,
    FR.BUCKET_NEEDS_REVIEW,
)

#: JSON wire-format keys shared across metrics.json/state.json/round-trip
#: reads (data-model.md schemas) -- hoisted since each appears >=3x (S1192).
_KEY_SCHEMA = "schema"
_KEY_FALSE_RED_RATE = "false_red_rate"
_KEY_FAILURES = "failures"
_KEY_BUCKETS = "buckets"
_KEY_IN_PROGRESS_LOW_WATER = "in_progress_low_water"

#: Placeholder cursor for the "prior state.json exists but is invalid" case.
#: Its VALUES are never read: ``resolve_window(..., baseline_valid=False)``
#: unconditionally falls back to a 30-day window and only tests
#: ``prev_cursor is not None`` to pick the ``lost_baseline`` (vs
#: ``first_run``) lineage label.
_INVALID_STATE_CURSOR = FR.Cursor(completed_through=datetime(1970, 1, 1, tzinfo=UTC), in_progress_low_water=None)


class GhCommandError(RuntimeError):
    """``gh`` exited non-zero, timed out, or was not found on PATH."""


# ---------------------------------------------------------------------------
# IO shell (T006) -- the only functions that shell out to `gh`
# ---------------------------------------------------------------------------


def run_gh(args: Sequence[str], *, timeout: float = DEFAULT_FETCH_TIMEOUT_S) -> str:
    """Run ``gh <args>`` and return stdout; raise :class:`GhCommandError` on failure/timeout."""
    try:
        result = subprocess.run(  # noqa: S603 -- fixed executable name, args are our own construction
            ["gh", *args], capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise GhCommandError(f"gh {' '.join(args)} timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise GhCommandError("gh CLI not found on PATH") from exc
    if result.returncode != 0:
        raise GhCommandError(f"gh {' '.join(args)} failed (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout


def list_runs(workflow: str, since: datetime | None, limit: int) -> list[FR.Run]:
    """Enumerate ``workflow``'s runs (pinned ``--limit``, sorted in-script -- C-… gh pagination note)."""
    raw = run_gh(["run", "list", "--workflow", workflow, "--limit", str(limit), "--json", RUN_LIST_JSON_FIELDS])
    runs = parse_runs_json(raw)
    if since is None:
        return runs
    return [run for run in runs if run.created_at > since or (run.completed_at is not None and run.completed_at > since)]


def failed_log(run_id: int, *, timeout: float = DEFAULT_FETCH_TIMEOUT_S) -> str:
    """Fetch ``gh run view <run_id> --log-failed``, stripped of gh's ``job\\tstep\\t`` TSV prefix."""
    raw = run_gh(["run", "view", str(run_id), "--log-failed"], timeout=timeout)
    return _strip_gh_log_prefix(raw)


def run_job_names(run_id: int, *, timeout: float = DEFAULT_FETCH_TIMEOUT_S) -> list[str]:
    """Failed job names for one run, via ``gh run view --json jobs`` (feeds ``extract_gate_signals``)."""
    raw = run_gh(["run", "view", str(run_id), "--json", "jobs"], timeout=timeout)
    payload = json.loads(raw)
    jobs = payload.get("jobs", [])
    return [str(job["name"]) for job in jobs if job.get("conclusion") == "failure"]


def run_log_durations(run_id: int, *, timeout: float = DEFAULT_FETCH_TIMEOUT_S) -> list[FR.DurationSample]:
    """Duration samples mined from the same ``--log-failed`` fetch used for classification."""
    return extract_durations(failed_log(run_id, timeout=timeout))


def fetch_logs_and_jobs(selected: Sequence[FR.Run]) -> tuple[dict[int, str], dict[int, list[str]]]:
    """Live IO: fetch failed-log text + failed-job names for each of ``selected``.

    Per-run error isolation (paula 5): an expired/404 ``--log-failed`` or
    ``--json jobs`` fetch previously raised :class:`GhCommandError` and
    aborted the *entire* report over one bad run. Now each run's log/jobs
    fetch is isolated -- on :class:`GhCommandError` the run is recorded as
    unfetchable (empty log / empty job list) and the batch continues; an
    unfetchable run still classifies honestly (``needs_review`` absent any
    other signal, or ``infra_flake`` via the conclusion-threaded rule) rather
    than crashing the whole run.
    """
    logs: dict[int, str] = {}
    jobs: dict[int, list[str]] = {}
    for run in selected:
        try:
            logs[run.run_id] = failed_log(run.run_id)
        except GhCommandError:
            logs[run.run_id] = ""
        try:
            jobs[run.run_id] = run_job_names(run.run_id)
        except GhCommandError:
            jobs[run.run_id] = []
    return logs, jobs


def _strip_gh_log_prefix(raw_log: str) -> str:
    """Strip gh's ``<job>\\t<step>\\t`` TSV prefix so WP01's ``^FAILED``-anchored patterns match.

    Lines without the two-tab prefix (e.g. already-bare fixture text) pass
    through unchanged, so this is safe to apply unconditionally.
    """
    lines = []
    for line in raw_log.splitlines():
        parts = line.split("\t", 2)
        lines.append(parts[2] if len(parts) == 3 else line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parsing (pure: JSON/text in, dataclasses out)
# ---------------------------------------------------------------------------


def parse_runs_json(raw_json: str) -> list[FR.Run]:
    """Parse ``gh run list --json ...`` output into sorted :class:`FR.Run` objects."""
    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("gh run list --json output must be a JSON array")
    runs = [_run_from_entry(entry) for entry in payload]
    return sorted(runs, key=lambda run: (run.created_at, run.run_id))


def _run_from_entry(entry: Mapping[str, Any]) -> FR.Run:
    status = str(entry["status"])
    conclusion = entry.get("conclusion") or None
    created_at = _parse_timestamp(str(entry["createdAt"]))
    updated_raw = entry.get("updatedAt")
    updated_at = _parse_timestamp(str(updated_raw)) if updated_raw else None
    completed_at = updated_at if status == "completed" else None
    pull_requests = entry.get("pullRequests") or []
    pr_number = int(pull_requests[0]["number"]) if pull_requests else None
    return FR.Run(
        run_id=int(entry["databaseId"]),
        attempt=int(entry.get("attempt", 1)),
        conclusion=str(conclusion) if conclusion else None,
        status=status,
        event=str(entry.get("event", "")),
        draft=bool(entry.get("isDraft", False)),
        created_at=created_at,
        completed_at=completed_at,
        updated_at=updated_at,
        pr_number=pr_number,
        head_branch=entry.get("headBranch"),
    )


def _parse_timestamp(value: str) -> datetime:
    return parse_iso(value)


def parse_failed_job_names(raw_json: str) -> dict[int, list[str]]:
    """Extract ``{run_id: [failed job names]}`` from the fixture's ``runs.json`` side-channel field.

    Live runs source this via :func:`run_job_names` instead (a real
    ``gh run view --json jobs`` call); this reads a pre-recorded
    ``failedJobNames`` field so the golden fixture's ``runs.json`` alone is
    enough to reproduce classification without live logs for the gate-only
    cases.
    """
    payload = json.loads(raw_json)
    result: dict[int, list[str]] = {}
    for entry in payload:
        names = entry.get("failedJobNames")
        if names:
            result[int(entry["databaseId"])] = [str(name) for name in names]
    return result


def extract_durations(log_text: str) -> list[FR.DurationSample]:
    """Pull CALL-phase duration samples from ``pytest --durations``-style log lines (FR-003).

    Recognizes ``call``/``setup``/``teardown`` phase lines but only emits a
    sample for ``call`` -- FR-003 measures the test's own CALL duration, not
    fixture setup/teardown overhead.
    """
    return [
        FR.DurationSample(nodeid=match.group(3), duration_s=float(match.group(1)))
        for match in _DURATION_LINE_PATTERN.finditer(log_text)
        if match.group(2) == "call"
    ]


# ---------------------------------------------------------------------------
# Pipeline (pure: wires already-fetched data through the WP01 core)
# ---------------------------------------------------------------------------


def classify_failure_run(log_text: str, job_names: Sequence[str], conclusion: str | None = None) -> tuple[str, str]:
    """One failure run's (bucket, reason), extracting signals then delegating to ``FR.classify_one``.

    ``conclusion`` (renata N1/paula 4) threads the run's own conclusion
    through so a ``startup_failure``/``timed_out`` run with an unfetchable or
    signal-free log still classifies deterministically as ``infra_flake``
    rather than degrading to ``needs_review``.
    """
    failed_nodeids = FR.extract_failed_nodeids(log_text)
    infra_signals = FR.extract_infra_signals(log_text)
    gate_signals = FR.extract_gate_signals(job_names)
    return FR.classify_one(failed_nodeids, log_text, job_names, infra_signals, gate_signals, conclusion)


def classify_all(
    selected: Sequence[FR.Run],
    logs_by_run_id: Mapping[int, str],
    job_names_by_run_id: Mapping[int, Sequence[str]],
) -> list[tuple[FR.Run, str, str]]:
    """Classify every run in ``selected`` against its pre-fetched log + job names."""
    results: list[tuple[FR.Run, str, str]] = []
    for run in selected:
        log_text = logs_by_run_id.get(run.run_id, "")
        job_names = job_names_by_run_id.get(run.run_id, ())
        bucket, reason = classify_failure_run(log_text, job_names, conclusion=run.conclusion)
        results.append((run, bucket, reason))
    return results


def _completion_sort_key(run: FR.Run) -> datetime:
    return run.completed_at or run.created_at


def apply_classified_cap(
    failure_runs: Sequence[FR.Run], cap: int = CLASSIFIED_FAILURES_CAP
) -> tuple[list[FR.Run], int]:
    """Most-recent-first selection up to ``cap`` (FR-008); returns ``(selected, dropped_count)``."""
    ordered = sorted(failure_runs, key=_completion_sort_key, reverse=True)
    selected = ordered[:cap]
    dropped = max(0, len(ordered) - cap)
    return selected, dropped


def apply_duration_cap(runs: Sequence[FR.Run], cap: int = DURATION_RUNS_CAP) -> list[FR.Run]:
    """Most-recent-first selection up to ``cap`` most-recent runs for duration mining (FR-008)."""
    ordered = sorted(runs, key=_completion_sort_key, reverse=True)
    return ordered[:cap]


def mine_durations(
    sampled: Sequence[FR.Run],
    logs_by_run_id: Mapping[int, str],
    job_names_by_run_id: Mapping[int, Sequence[str]],
) -> tuple[list[FR.DurationAgg], list[str]]:
    """Aggregate durations over ``sampled``; disclose job names whose log yielded zero samples (C-005)."""
    all_samples: list[FR.DurationSample] = []
    suites_with: set[str] = set()
    suites_without: set[str] = set()
    for run in sampled:
        log_text = logs_by_run_id.get(run.run_id)
        if log_text is None:
            continue
        samples = extract_durations(log_text)
        all_samples.extend(samples)
        job_names = job_names_by_run_id.get(run.run_id, ())
        target = suites_with if samples else suites_without
        target.update(job_names)
    aggs = FR.aggregate_durations(all_samples)
    disclosed = sorted(suites_without - suites_with)
    return aggs, disclosed


# ---------------------------------------------------------------------------
# Bundle + render (T008)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoadedState:
    """Result of :func:`load_state`: what the prior ``state.json`` (if any) told us."""

    cursor: FR.Cursor | None
    baseline_valid: bool
    previous_headline: Mapping[str, Any] | None
    previous_enumerated_run_ids: tuple[int, ...] = ()


def load_state(path: Path | None) -> LoadedState:
    """Load a prior ``state.json``; schema-validate; missing/corrupt degrade gracefully (FR-005).

    - ``path`` is ``None`` or does not exist -> true first run (empty enumerated set).
    - exists but unparsable/schema-invalid -> lost baseline (sentinel cursor, empty enumerated set).
    - exists and valid -> ``(cursor, True, previous_headline, previous_enumerated_run_ids)``.

    ``previous_enumerated_run_ids`` (FR-004) is threaded back out so
    :func:`run_report` can dedup against it when :func:`FR.resolve_window`
    widens the window to a prior in-progress low-water mark -- otherwise a
    run already counted once would be re-admitted and double-counted.
    """
    if path is None or not path.exists():
        return LoadedState(cursor=None, baseline_valid=True, previous_headline=None, previous_enumerated_run_ids=())
    try:
        raw = json.loads(path.read_text(encoding=ENCODING))
        if raw.get(_KEY_SCHEMA) != STATE_SCHEMA_VERSION:
            raise ValueError(f"unsupported state schema: {raw.get(_KEY_SCHEMA)!r}")
        cursor_raw = raw["cursor"]
        cursor = FR.Cursor(
            completed_through=_parse_timestamp(cursor_raw["completed_through"]),
            in_progress_low_water=(
                _parse_timestamp(cursor_raw[_KEY_IN_PROGRESS_LOW_WATER])
                if cursor_raw.get(_KEY_IN_PROGRESS_LOW_WATER)
                else None
            ),
        )
        enumerated_run_ids = tuple(int(run_id) for run_id in raw.get("enumerated_run_ids", []))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return LoadedState(
            cursor=_INVALID_STATE_CURSOR, baseline_valid=False, previous_headline=None, previous_enumerated_run_ids=()
        )
    return LoadedState(
        cursor=cursor,
        baseline_valid=True,
        previous_headline=raw.get("headline"),
        previous_enumerated_run_ids=enumerated_run_ids,
    )


def compute_delta(
    headline: FR.Headline, previous_headline: Mapping[str, Any] | None
) -> dict[str, float | int] | None:
    """``headline`` vs the prior report's headline; ``None`` when there is nothing comparable."""
    if previous_headline is None:
        return None
    try:
        prev_rate = float(previous_headline[_KEY_FALSE_RED_RATE])
        prev_failures = int(previous_headline[_KEY_FAILURES])
        prev_needs_review = int(previous_headline[_KEY_BUCKETS][FR.BUCKET_NEEDS_REVIEW])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        _KEY_FALSE_RED_RATE: round(headline.false_red_rate - prev_rate, 4),
        _KEY_FAILURES: headline.failures - prev_failures,
        "needs_review": headline.buckets.needs_review - prev_needs_review,
    }


def _serialize_cursor(cursor: FR.Cursor) -> dict[str, str | None]:
    return {
        "completed_through": cursor.completed_through.isoformat(),
        _KEY_IN_PROGRESS_LOW_WATER: cursor.in_progress_low_water.isoformat() if cursor.in_progress_low_water else None,
    }


def _serialize_headline(headline: FR.Headline) -> dict[str, Any]:
    return {
        "window_start": headline.window_start.isoformat(),
        "window_end": headline.window_end.isoformat(),
        "completed_runs": headline.completed_runs,
        _KEY_FAILURES: headline.failures,
        _KEY_FALSE_RED_RATE: round(headline.false_red_rate, 4),
        _KEY_BUCKETS: headline.buckets.as_mapping(),
        "classifier_coverage": round(headline.classifier_coverage, 4),
    }


def serialize_state(state: FR.ReportState) -> dict[str, Any]:
    """``state.json`` schema (data-model.md §1) from a WP01 :class:`FR.ReportState`."""
    return {
        _KEY_SCHEMA: state.schema,
        "generated_at": state.generated_at.isoformat(),
        "target_workflow": state.target_workflow,
        "cursor": _serialize_cursor(state.cursor),
        "enumerated_run_ids": list(state.enumerated_run_ids),
        "lineage": state.lineage,
        "headline": _serialize_headline(state.headline),
    }


def build_metrics_model(
    state: FR.ReportState,
    tally: FR.Tally,
    delta: Mapping[str, float | int] | None,
    caps_applied: Mapping[str, int],
) -> dict[str, Any]:
    """``metrics.json`` schema (data-model.md §2)."""
    headline = state.headline
    return {
        _KEY_SCHEMA: state.schema,
        "window": {
            "start": headline.window_start.isoformat(),
            "end": headline.window_end.isoformat(),
            "target_workflow": state.target_workflow,
        },
        "denominators": {
            "total_runs": tally.total_runs,
            "completed_runs": tally.completed_runs,
            "distinct_prs": tally.distinct_prs,
            "prs_with_failure": tally.prs_with_failure,
        },
        _KEY_FAILURES: {"total": headline.failures, _KEY_BUCKETS: headline.buckets.as_mapping()},
        _KEY_FALSE_RED_RATE: round(headline.false_red_rate, 4),
        "classifier_coverage": round(headline.classifier_coverage, 4),
        "delta_vs_prev": delta,
        "caps_applied": dict(caps_applied),
    }


def build_durations_model(
    runs_sampled: int, suites_without_durations: Sequence[str], aggs: Sequence[FR.DurationAgg]
) -> dict[str, Any]:
    """``durations.json`` schema (data-model.md §3)."""
    return {
        _KEY_SCHEMA: STATE_SCHEMA_VERSION,
        "runs_sampled": runs_sampled,
        "suites_without_durations": sorted(suites_without_durations),
        "tests": [
            {
                "nodeid": agg.nodeid,
                "n": agg.n,
                "median_s": agg.median_s,
                "mean_s": agg.mean_s,
                "max_s": agg.max_s,
                "long_pole": agg.long_pole,
            }
            for agg in aggs
        ],
    }


def _write_json(path: Path, model: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(model, indent=2) + "\n", encoding=ENCODING)


def write_bundle(
    out_dir: Path,
    *,
    state: FR.ReportState,
    tally: FR.Tally,
    duration_aggs: Sequence[FR.DurationAgg],
    duration_runs_sampled: int,
    suites_without_durations: Sequence[str],
    caps_applied: Mapping[str, int],
    previous_headline: Mapping[str, Any] | None,
) -> None:
    """Write the four findings artifacts (metrics/durations/report/state) to ``out_dir``.

    Artifacts only (C-001): this never touches the repo tree outside
    ``out_dir``, never writes docs, and performs no git operation.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    delta = compute_delta(state.headline, previous_headline)
    metrics_model = build_metrics_model(state, tally, delta, caps_applied)
    durations_model = build_durations_model(duration_runs_sampled, suites_without_durations, duration_aggs)
    state_model = serialize_state(state)

    _write_json(out_dir / METRICS_FILENAME, metrics_model)
    _write_json(out_dir / DURATIONS_FILENAME, durations_model)
    _write_json(out_dir / STATE_FILENAME, state_model)

    report_model = {
        "metrics": metrics_model,
        "durations": durations_model,
        "lineage": state.lineage,
        "generated_at": state.generated_at.isoformat(),
    }
    (out_dir / REPORT_FILENAME).write_text(render_markdown(report_model), encoding=ENCODING)


def render_markdown(model: Mapping[str, Any]) -> str:
    """Deterministic markdown render (NFR-004): fixed key order, sorted collections throughout.

    ``model`` is the ``{"metrics": ..., "durations": ..., "lineage": ..., "generated_at": ...}``
    shape produced by :func:`write_bundle`. Only ``generated_at`` varies across
    otherwise-identical runs; every other field is rendered via a fixed
    iteration order (:data:`_RENDER_BUCKET_ORDER`, pre-sorted lists) so two
    calls with logically-identical-but-differently-ordered inputs (e.g. a
    dict/set rebuilt in a different iteration order after hash randomization)
    still byte-match.
    """
    metrics = model["metrics"]
    durations = model["durations"]
    lines: list[str] = [
        f"# CI Flake Report — {metrics['window']['target_workflow']}",
        "",
        f"Generated: {model['generated_at']}  |  Lineage: `{model['lineage']}`",
        f"Window: {metrics['window']['start']} → {metrics['window']['end']}",
        "",
        "## Headline",
        "",
        f"- False-red rate: **{metrics[_KEY_FALSE_RED_RATE]:.1%}**",
        f"- Classifier coverage: {metrics['classifier_coverage']:.1%}",
        f"- Completed runs: {metrics['denominators']['completed_runs']} "
        f"(total fetched: {metrics['denominators']['total_runs']})",
        f"- Distinct PRs: {metrics['denominators']['distinct_prs']} "
        f"({metrics['denominators']['prs_with_failure']} with a failure)",
        "",
        "## Buckets",
        "",
        "| Bucket | Count |",
        "| --- | --- |",
    ]
    for bucket_name in _RENDER_BUCKET_ORDER:
        lines.append(f"| {bucket_name} | {metrics[_KEY_FAILURES][_KEY_BUCKETS].get(bucket_name, 0)} |")
    lines.extend(["", "## Delta vs previous", ""])
    lines.extend(_render_delta_lines(metrics.get("delta_vs_prev")))
    lines.extend(["", "## Duration long-poles", ""])
    lines.extend(_render_long_pole_lines(durations["tests"]))
    lines.extend(["", "## Coverage & caveats", ""])
    lines.extend(_render_caveat_lines(durations, metrics["caps_applied"]))
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_delta_lines(delta: Mapping[str, float | int] | None) -> list[str]:
    if delta is None:
        return ["_No comparable previous report (first run or lost baseline)._"]
    return [
        f"- False-red rate: {delta[_KEY_FALSE_RED_RATE]:+.4f}",
        f"- Failures: {delta[_KEY_FAILURES]:+d}",
        f"- Needs review: {delta['needs_review']:+d}",
    ]


def _render_long_pole_lines(tests: Sequence[Mapping[str, Any]]) -> list[str]:
    long_poles = [test for test in tests if test["long_pole"]]
    if not long_poles:
        return ["_No long-poles (median > 2.0s) in this window._"]
    lines = ["| Test | n | median_s | mean_s | max_s |", "| --- | --- | --- | --- | --- |"]
    lines.extend(
        f"| {test['nodeid']} | {test['n']} | {test['median_s']} | {test['mean_s']} | {test['max_s']} |"
        for test in long_poles
    )
    return lines


def _render_caveat_lines(durations: Mapping[str, Any], caps_applied: Mapping[str, int]) -> list[str]:
    lines = [f"- Runs sampled for durations: {durations['runs_sampled']}"]
    suites_without = durations["suites_without_durations"]
    if suites_without:
        lines.append(
            f"- Suites without `--durations` output (absence ≠ zero cost): {', '.join(suites_without)}"
        )
    lines.append(
        f"- Caps applied: {caps_applied['classified_failures_cap']} classified failures / "
        f"{caps_applied['duration_runs_cap']} duration-mined runs (dropped: {caps_applied['dropped']})"
    )
    return lines


# ---------------------------------------------------------------------------
# CLI (T006/T008)
# ---------------------------------------------------------------------------


def run_report(*, workflow: str, since: datetime | None, state_path: Path | None, out_dir: Path) -> FR.ReportState:
    """End-to-end live run: fetch via ``gh``, classify, mine durations, write the bundle."""
    now = now_utc()
    loaded = load_state(state_path)
    window = FR.resolve_window(loaded.cursor, now, baseline_valid=loaded.baseline_valid)
    if since is not None:
        window = replace(window, start=since)

    # FR-004: dedup against runs already enumerated by the prior report, since
    # resolve_window may have widened window.start back to a prior
    # in-progress low-water mark.
    already_enumerated = frozenset(loaded.previous_enumerated_run_ids)

    runs = list_runs(workflow, since=window.start, limit=LIST_RUNS_LIMIT)
    tally = FR.tally(runs)

    in_window = FR.runs_completed_in_window(runs, window, already_enumerated=already_enumerated)
    failure_runs = [run for run in in_window if run.conclusion in FAILURE_LIKE_CONCLUSIONS]

    classify_selected, dropped = apply_classified_cap(failure_runs)
    duration_selected = apply_duration_cap(failure_runs)
    logs_by_run_id, jobs_by_run_id = fetch_logs_and_jobs(classify_selected)

    classified = classify_all(classify_selected, logs_by_run_id, jobs_by_run_id)
    duration_aggs, suites_without_durations = mine_durations(duration_selected, logs_by_run_id, jobs_by_run_id)

    counts = FR.bucket_counts(bucket for _, bucket, _ in classified)
    previous_cursor = loaded.cursor or FR.Cursor(completed_through=window.start, in_progress_low_water=None)
    cursor = FR.advance_cursor(runs, previous_cursor)
    state = FR.build_report_state(
        generated_at=now,
        target_workflow=workflow,
        cursor=cursor,
        runs=runs,
        window=window,
        counts=counts,
        already_enumerated=already_enumerated,
    )

    caps_applied = {
        "classified_failures_cap": CLASSIFIED_FAILURES_CAP,
        "duration_runs_cap": DURATION_RUNS_CAP,
        "dropped": dropped,
    }
    write_bundle(
        out_dir,
        state=state,
        tally=tally,
        duration_aggs=duration_aggs,
        duration_runs_sampled=len(duration_selected),
        suites_without_durations=suites_without_durations,
        caps_applied=caps_applied,
        previous_headline=loaded.previous_headline,
    )
    return state


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flake_report_cli.py",
        description=(
            "Measure the CI false-red rate and per-test timing cost for a target GitHub Actions "
            "workflow, incrementally since the previous report. Writes findings as artifacts only "
            "(metrics.json, durations.json, report.md, state.json) -- never a repo commit, never a "
            "docs edit (C-001)."
        ),
    )
    parser.add_argument(
        "--workflow", default=DEFAULT_WORKFLOW, help=f"Target workflow file (default: {DEFAULT_WORKFLOW})."
    )
    parser.add_argument(
        "--since",
        default=None,
        help="ISO8601 timestamp overriding the window start (default: prior state cursor, or a 30-day lookback).",
    )
    parser.add_argument(
        "--state", default=None, type=Path, help="Path to a prior state.json (default: none => first run)."
    )
    parser.add_argument(
        "--out",
        default=Path(DEFAULT_OUT_DIR),
        type=Path,
        help=f"Directory to write the findings bundle into (default: {DEFAULT_OUT_DIR}).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    since = parse_iso(args.since) if args.since else None
    state = run_report(workflow=args.workflow, since=since, state_path=args.state, out_dir=args.out)
    print(
        f"flake-report: {state.headline.failures} failure(s), "
        f"false_red_rate={state.headline.false_red_rate:.3f}, lineage={state.lineage} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

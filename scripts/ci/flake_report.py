#!/usr/bin/env python3
"""Pure core for the CI flake-report workflow (mission ci-flake-report-workflow, WP01).

Everything in this module is deterministic, stdlib-only, and IO-free: no
``gh`` calls, no network, no filesystem access. The IO shell (fetching runs
and logs via ``gh``, reading/writing ``state.json``/``metrics.json``/
``durations.json``/``report.md``) is WP02's concern; this module only knows
how to turn already-fetched, in-memory data into classifications, tallies,
aggregates, and cursor/window arithmetic.

Covers:

- **FR-001** conclusion taxonomy + run tally (:func:`is_completed`,
  :func:`is_excluded`, :func:`tally`).
- **FR-002** failure classification + pinned false-red-rate formula
  (:func:`classify_one`, :func:`false_red_rate`), per the signature
  contract in ``data-model.md`` §5.
- **FR-003** per-test duration aggregation (:func:`aggregate_durations`).
- **FR-004/FR-005** delta cursor: half-open window resolution and monotonic
  cursor advancement (:func:`resolve_window`, :func:`advance_cursor`,
  :func:`runs_completed_in_window`).
- **FR-015/NFR-004** classifier coverage + deterministic, reproducible state
  (:func:`classifier_coverage`, :func:`build_report_state`).

NFR-001: standard library only; ``ruff``/``mypy --strict`` clean; every
function kept at cyclomatic complexity <= 15.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from kernel.clock import datetime, timedelta

# ---------------------------------------------------------------------------
# FR-001: conclusion taxonomy
# ---------------------------------------------------------------------------

COMPLETED_CONCLUSIONS: frozenset[str] = frozenset({"success", "failure", "timed_out", "startup_failure"})
EXCLUDED_CONCLUSIONS: frozenset[str] = frozenset({"cancelled", "action_required", "skipped", "neutral", "stale"})

#: Conclusions this tool attempts to classify -- a strict subset of
#: ``COMPLETED_CONCLUSIONS`` (``success`` is completed but never a failure
#: candidate). Single-sourced here so WP02's CLI and this module's own
#: ``tally()`` never drift on what counts as "a failure" (renata S2/paula 8).
FAILURE_LIKE_CONCLUSIONS: frozenset[str] = frozenset({"failure", "timed_out", "startup_failure"})

#: Conclusions that, absent any other signal (no failed nodeid, no gate job
#: failure), deterministically classify as infra trouble rather than
#: degrading to ``needs_review``. Runs with these conclusions typically have
#: no fetchable ``--log-failed`` body to begin with -- they ARE the infra
#: problem (renata N1/paula 4).
CONCLUSION_INFRA_LIKE: frozenset[str] = frozenset({"startup_failure", "timed_out"})

#: ``state.json``/``metrics.json``/``durations.json`` schema version.
#: Single-sourced: WP02's ``flake_report_cli.STATE_SCHEMA_VERSION`` and this
#: module's ``build_report_state`` default both point here so the four
#: artifacts can never silently drift onto different schema numbers (nit).
SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# FR-002: classifier signature contract (data-model.md §5)
# ---------------------------------------------------------------------------

#: Seed set of bare test-function names known to be timing/perf-budget tests
#: (pinned, versioned in the golden fixture per FR-017).
TIMING_NODEIDS: frozenset[str] = frozenset(
    {
        "test_tasks_status_p95_within_nfr005_budget",
        "test_the_guard_completes_inside_the_budget_on_three_warm_runs",
        "test_200_missions_under_5s",
        "test_nfr_002_timing_200_missions",
        "test_sweep_enumeration_perf_1k_files",
        "test_run_consistency_check_completes_within_budget",
        # Retained as a benign classifier hint after #3787 retired the
        # check_nfr_003_latency gate: no test by this node-id exists any more,
        # but the flake-report golden fixture pins this TIMING set, so removing
        # the string would destabilise that (separate mission's) fixture for no
        # runtime gain — it never matches a live node again.
        "check_nfr_003_latency",
    }
)

#: Regex fallback for timing tests not (yet) in the pinned seed set.
#:
#: DELIBERATELY CONSERVATIVE (B1, BLOCKER): a bare ``_under_`` or bare
#: ``nfr_00\d`` matched the whole nodeid against 245+ real, non-timing repo
#: tests (e.g. ``test_mkdir_under_forbidden_path_raises``,
#: ``test_claim_under_contention``, ``test_nfr_004_deterministic_output``) --
#: a real regression in one of those would misclassify as
#: ``perf_timing_flake`` and silently corrupt the headline false-red rate.
#: A false ``needs_review`` is honest; a false ``perf_timing_flake`` is not,
#: so every alternative below requires a genuine timing co-signal:
#: ``_p95_``, ``within...budget``, ``three_warm_runs``,
#: ``completes_in_under``, a number-of-seconds ``under_<N>...s`` bound, or
#: ``nfr_00<N>`` co-occurring with ``timing`` in the name. Tests not covered
#: by these signatures rely on the pinned :data:`TIMING_NODEIDS` seed set
#: instead of this fallback.
_TIMING_PATTERN = re.compile(
    r"(_p95_|within.*budget|three_warm_runs|completes_in_under|under_\d+\w*s"
    r"|nfr_00\d\w*timing|timing\w*nfr_00\d)"
)

#: Substrings that, if present anywhere in the failure log, indicate
#: infrastructure trouble rather than a test defect.
INFRA_SIGNAL_KEYWORDS: frozenset[str] = frozenset(
    {"logged_out_on_connected_teamspace", "digest-mismatch", "INTERNALERROR", "SystemError", "startup_failure"}
)

#: Job-name substrings that mark a CI gate (mypy/ruff/golden-count/arch/docs
#: step) as opposed to a test-suite job.
GATE_JOB_KEYWORDS: frozenset[str] = frozenset({"mypy", "ruff", "golden-count", "arch", "docs"})

_FAILED_NODEID_PATTERN = re.compile(r"^FAILED (\S+)", re.MULTILINE)

BUCKET_PERF_TIMING_FLAKE = "perf_timing_flake"
BUCKET_INFRA_FLAKE = "infra_flake"
BUCKET_REAL = "real"
BUCKET_NEEDS_REVIEW = "needs_review"
_ALL_BUCKETS: tuple[str, ...] = (BUCKET_PERF_TIMING_FLAKE, BUCKET_INFRA_FLAKE, BUCKET_REAL, BUCKET_NEEDS_REVIEW)

LONG_POLE_THRESHOLD_S = 2.0

LINEAGE_FIRST_RUN = "first_run"
LINEAGE_LOST_BASELINE = "lost_baseline"
LINEAGE_OK = "ok"
LOST_BASELINE_WINDOW_DAYS = 30


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Run:
    """One CI run of the target workflow (spec Key Entities: CI Run)."""

    run_id: int
    attempt: int
    conclusion: str | None
    status: str
    event: str
    draft: bool
    created_at: datetime
    completed_at: datetime | None = None
    updated_at: datetime | None = None
    pr_number: int | None = None
    head_branch: str | None = None

    @property
    def enumeration_key(self) -> tuple[int, int]:
        """Re-run/new-attempt identity: keyed on run-id+attempt, never bare run-id."""
        return (self.run_id, self.attempt)

    @property
    def pr_identity(self) -> tuple[str, int] | tuple[str, str]:
        """Distinct-PR key: PR number when present, else headBranch (push events)."""
        if self.pr_number is not None:
            return ("pr", self.pr_number)
        return ("branch", self.head_branch or "")


@dataclass(frozen=True)
class Tally:
    """FR-001 denominators."""

    total_runs: int
    completed_runs: int
    distinct_prs: int
    prs_with_failure: int


@dataclass(frozen=True)
class DurationSample:
    """One raw CALL-duration observation for a test nodeid (FR-003 input)."""

    nodeid: str
    duration_s: float


@dataclass(frozen=True)
class DurationAgg:
    """Per-nodeid duration aggregate (FR-003 output)."""

    nodeid: str
    n: int
    median_s: float
    mean_s: float
    max_s: float
    long_pole: bool


@dataclass(frozen=True)
class Cursor:
    """FR-004/FR-005 delta cursor."""

    completed_through: datetime
    in_progress_low_water: datetime | None


@dataclass(frozen=True)
class Window:
    """A resolved analysis window plus the lineage that produced it."""

    start: datetime
    end: datetime
    lineage: str


@dataclass(frozen=True)
class BucketCounts:
    """FR-002 classification bucket counts."""

    perf_timing_flake: int = 0
    infra_flake: int = 0
    real: int = 0
    needs_review: int = 0

    def as_mapping(self) -> dict[str, int]:
        return {
            BUCKET_PERF_TIMING_FLAKE: self.perf_timing_flake,
            BUCKET_INFRA_FLAKE: self.infra_flake,
            BUCKET_REAL: self.real,
            BUCKET_NEEDS_REVIEW: self.needs_review,
        }

    @property
    def total(self) -> int:
        return self.perf_timing_flake + self.infra_flake + self.real + self.needs_review


@dataclass(frozen=True)
class Headline:
    """FR-002/FR-015 headline metrics for one report."""

    window_start: datetime
    window_end: datetime
    completed_runs: int
    failures: int
    false_red_rate: float
    buckets: BucketCounts
    classifier_coverage: float


@dataclass(frozen=True)
class ReportState:
    """The lineage-critical delta baseline (data-model.md §1 ``state.json``)."""

    schema: int
    generated_at: datetime
    target_workflow: str
    cursor: Cursor
    enumerated_run_ids: tuple[int, ...]
    lineage: str
    headline: Headline


# ---------------------------------------------------------------------------
# FR-001: taxonomy + tally
# ---------------------------------------------------------------------------


def is_completed(conclusion: str | None) -> bool:
    """True iff ``conclusion`` is in the completed set counted by every metric."""
    return conclusion in COMPLETED_CONCLUSIONS


def is_excluded(conclusion: str | None) -> bool:
    """True iff ``conclusion`` is excluded from both numerator and denominator."""
    return conclusion in EXCLUDED_CONCLUSIONS


def tally(runs: Sequence[Run]) -> Tally:
    """FR-001 denominators: total/completed runs, distinct PRs, PRs with a failure.

    ``distinct_prs`` and ``prs_with_failure`` are both scoped to completed
    runs (renata S2/paula 8): a cancelled/action_required run never produced
    a verdict, so it must not inflate either denominator.
    ``prs_with_failure`` counts :data:`FAILURE_LIKE_CONCLUSIONS`
    (failure/timed_out/startup_failure), not bare ``"failure"`` alone.
    """
    completed = [run for run in runs if is_completed(run.conclusion)]
    distinct_prs = {run.pr_identity for run in completed if run.pr_number is not None or run.head_branch}
    failing_prs = {run.pr_identity for run in completed if run.conclusion in FAILURE_LIKE_CONCLUSIONS}
    return Tally(
        total_runs=len(runs),
        completed_runs=len(completed),
        distinct_prs=len(distinct_prs),
        prs_with_failure=len(failing_prs),
    )


# ---------------------------------------------------------------------------
# FR-002: classifier
# ---------------------------------------------------------------------------


def is_timing(nodeid: str) -> bool:
    """True iff a failed nodeid is a known/likely timing-budget test."""
    test_name = nodeid.rsplit("::", 1)[-1]
    return test_name in TIMING_NODEIDS or bool(_TIMING_PATTERN.search(nodeid))


def extract_failed_nodeids(log_text: str) -> list[str]:
    """Pull ``FAILED <nodeid>`` lines from a ``--log-failed`` excerpt."""
    return _FAILED_NODEID_PATTERN.findall(log_text)


def extract_infra_signals(log_text: str) -> frozenset[str]:
    """Which infra-trouble keywords (if any) appear in the failure log."""
    return frozenset(keyword for keyword in INFRA_SIGNAL_KEYWORDS if keyword in log_text)


def extract_gate_signals(job_names: Sequence[str]) -> frozenset[str]:
    """Which failed job names look like a CI gate step rather than a test suite."""
    return frozenset(job for job in job_names if any(keyword in job for keyword in GATE_JOB_KEYWORDS))


def classify_one(
    failed_nodeids: Sequence[str],
    log_text: str,
    job_names: Sequence[str],
    infra_signals: Iterable[str],
    gate_signals: Iterable[str],
    conclusion: str | None = None,
) -> tuple[str, str]:
    """Classify one completed failure run per data-model.md §5.

    Ordered evaluation, first decisive rule wins:

    1. infra signal(s) with no failed nodeids and no gate signals -> ``infra_flake``
    2. any failed nodeid:
       - a non-timing failed nodeid present -> ``real`` (mixed => actionable)
       - all failed nodeids are timing -> ``perf_timing_flake``
    3. gate signal(s) -> ``real``
    4. ``conclusion`` in :data:`CONCLUSION_INFRA_LIKE` (``startup_failure``/
       ``timed_out``) with no failed nodeids and no gate signal ->
       ``infra_flake`` (renata N1/paula 4): these runs commonly have no
       fetchable ``--log-failed`` body, so absent that evidence the *run's
       own conclusion* is still a decisive, honest signal -- deterministic
       infra_flake beats a blind ``needs_review``.
    5. otherwise -> ``needs_review`` (honest fallback, never silent)

    Classification is driven solely by ``failed_nodeids``/``infra_signals``/
    ``gate_signals``/``conclusion`` (nodeid- and conclusion-keyed,
    drift-resistant per FR-002) — never by matching substrings in
    ``log_text``. ``log_text`` and ``job_names`` are threaded through only so
    a ``needs_review`` reason points back at the raw evidence a human should
    look at.
    """
    nodeids = list(failed_nodeids)
    infra = frozenset(infra_signals)
    gate = frozenset(gate_signals)

    if infra and not nodeids and not gate:
        return BUCKET_INFRA_FLAKE, f"infra signal(s) matched with no failing nodeids: {sorted(infra)}"

    if nodeids:
        non_timing = sorted(nodeid for nodeid in nodeids if not is_timing(nodeid))
        if non_timing:
            return BUCKET_REAL, f"non-timing failing nodeid(s): {non_timing}"
        return BUCKET_PERF_TIMING_FLAKE, f"all failing nodeids match the timing signature: {sorted(nodeids)}"

    if gate:
        return BUCKET_REAL, f"gate job failure(s): {sorted(gate)}"

    if conclusion in CONCLUSION_INFRA_LIKE:
        return BUCKET_INFRA_FLAKE, f"run conclusion={conclusion!r} with no failing nodeid or gate signal (log unavailable)"

    evidence = f"{len(job_names)} job(s), {len(log_text)} log byte(s) inspected"
    return BUCKET_NEEDS_REVIEW, f"no failed nodeids, infra signal, or gate signal matched ({evidence})"


def bucket_counts(buckets: Iterable[str]) -> BucketCounts:
    """Aggregate a stream of :func:`classify_one` bucket labels into counts."""
    counts = dict.fromkeys(_ALL_BUCKETS, 0)
    for bucket in buckets:
        if bucket not in counts:
            raise ValueError(f"unknown classification bucket: {bucket!r}")
        counts[bucket] += 1
    return BucketCounts(**counts)


def false_red_rate(counts: Mapping[str, int]) -> float:
    """FR-002 pinned formula; ``needs_review`` excluded; 0.0 on an empty denominator."""
    perf = counts.get(BUCKET_PERF_TIMING_FLAKE, 0)
    infra = counts.get(BUCKET_INFRA_FLAKE, 0)
    real = counts.get(BUCKET_REAL, 0)
    denominator = perf + infra + real
    if denominator == 0:
        return 0.0
    return (perf + infra) / denominator


def classifier_coverage(counts: Mapping[str, int]) -> float:
    """FR-015: ``1 - needs_review/failures``; 1.0 (fully covered) with zero failures."""
    needs_review = counts.get(BUCKET_NEEDS_REVIEW, 0)
    failures = sum(counts.get(bucket, 0) for bucket in _ALL_BUCKETS)
    if failures == 0:
        return 1.0
    return 1.0 - (needs_review / failures)


# ---------------------------------------------------------------------------
# FR-003: duration aggregation
# ---------------------------------------------------------------------------


def aggregate_durations(samples: Sequence[DurationSample]) -> list[DurationAgg]:
    """Per-nodeid n/median/mean/max, stably ordered by nodeid (NFR-004)."""
    grouped: dict[str, list[float]] = {}
    for sample in samples:
        grouped.setdefault(sample.nodeid, []).append(sample.duration_s)

    aggregates: list[DurationAgg] = []
    for nodeid in sorted(grouped):
        values = grouped[nodeid]
        median = statistics.median(values)
        aggregates.append(
            DurationAgg(
                nodeid=nodeid,
                n=len(values),
                median_s=round(median, 2),
                mean_s=round(statistics.mean(values), 2),
                max_s=round(max(values), 2),
                long_pole=median > LONG_POLE_THRESHOLD_S,
            )
        )
    return aggregates


# ---------------------------------------------------------------------------
# FR-004/FR-005: delta cursor
# ---------------------------------------------------------------------------


def resolve_window(prev_cursor: Cursor | None, now: datetime, *, baseline_valid: bool = True) -> Window:
    """Resolve the analysis window: prior cursor, or a 30-day trailing fallback.

    - ``prev_cursor is None`` -> ``first_run`` (true first run).
    - ``prev_cursor`` present but ``baseline_valid=False`` -> ``lost_baseline``
      (schema-invalid/corrupt/missing prior artifact, FR-005).
    - otherwise -> ``ok``, half-open on
      ``min(prev_cursor.completed_through, prev_cursor.in_progress_low_water)``
      when a prior low-water mark exists (FR-004: a run still in-progress at
      the last report must remain reachable until it completes), else on
      ``prev_cursor.completed_through`` alone. Pair with
      :func:`runs_completed_in_window`'s ``already_enumerated`` so widening
      the window this way never double-counts a run already reported once.
    """
    if prev_cursor is not None and baseline_valid:
        start = prev_cursor.completed_through
        if prev_cursor.in_progress_low_water is not None:
            start = min(start, prev_cursor.in_progress_low_water)
        return Window(start=start, end=now, lineage=LINEAGE_OK)
    lineage = LINEAGE_FIRST_RUN if prev_cursor is None else LINEAGE_LOST_BASELINE
    start = now - timedelta(days=LOST_BASELINE_WINDOW_DAYS)
    return Window(start=start, end=now, lineage=lineage)


def runs_completed_in_window(
    runs: Sequence[Run], window: Window, *, already_enumerated: frozenset[int] = frozenset()
) -> list[Run]:
    """Runs whose completion falls in the half-open window ``(start, end]``.

    ``>`` not ``>=`` at the lower bound: a run completed exactly at
    ``window.start`` was already counted by the report that advanced the
    cursor to that value.

    ``already_enumerated`` (FR-004): run ids already recorded on a prior
    report's ``enumerated_run_ids``. Needed because :func:`resolve_window`
    can widen ``window.start`` back to a prior in-progress low-water mark,
    which would otherwise re-admit runs that fell between the low-water mark
    and ``completed_through`` and were already counted once.
    """
    return [
        run
        for run in runs
        if run.completed_at is not None
        and window.start < run.completed_at <= window.end
        and run.run_id not in already_enumerated
    ]


def advance_cursor(runs: Sequence[Run], previous: Cursor) -> Cursor:
    """Advance the cursor from a freshly-fetched run batch; never regresses.

    - ``completed_through``: the max completed-run completion time seen,
      starting from (never below) ``previous.completed_through``.
    - ``in_progress_low_water``: the earliest still-in-progress run's start
      time in this batch, so the next report re-enumerates from there and a
      straddling run is counted exactly once when it completes. Carried
      forward unchanged when this batch has no in-progress runs.
    """
    completed_through = previous.completed_through
    for run in runs:
        if is_completed(run.conclusion) and run.completed_at is not None and run.completed_at > completed_through:
            completed_through = run.completed_at

    in_progress = [run for run in runs if run.status != "completed"]
    low_water = min((run.created_at for run in in_progress), default=previous.in_progress_low_water)

    return Cursor(completed_through=completed_through, in_progress_low_water=low_water)


# ---------------------------------------------------------------------------
# FR-015/NFR-004: coverage + deterministic state
# ---------------------------------------------------------------------------


def sorted_run_ids(runs: Iterable[Run]) -> list[int]:
    """Stable, deduped, ascending run-id ordering (NFR-004 determinism)."""
    return sorted({run.run_id for run in runs})


def stable_sorted_nodeids(nodeids: Iterable[str]) -> list[str]:
    """Stable, deduped, ascending nodeid ordering (NFR-004 determinism)."""
    return sorted(set(nodeids))


def build_report_state(
    *,
    generated_at: datetime,
    target_workflow: str,
    cursor: Cursor,
    runs: Sequence[Run],
    window: Window,
    counts: BucketCounts,
    schema: int = SCHEMA_VERSION,
    already_enumerated: frozenset[int] = frozenset(),
) -> ReportState:
    """Compose the FR-015 state model: enumerated run-id set + headline metrics.

    ``runs`` is the full fetched batch; a run is enumerated/counted only when
    all true: its completion falls within ``window`` (half-open, per
    :func:`runs_completed_in_window`), its conclusion is in the FR-001
    completed taxonomy (excluded conclusions never enter a metric), and its
    run id is not already in ``already_enumerated`` (FR-004 dedup for a
    low-water-widened window; see :func:`runs_completed_in_window`).
    """
    completed = [
        run
        for run in runs_completed_in_window(runs, window, already_enumerated=already_enumerated)
        if is_completed(run.conclusion)
    ]
    counts_mapping = counts.as_mapping()
    headline = Headline(
        window_start=window.start,
        window_end=window.end,
        completed_runs=len(completed),
        failures=counts.total,
        false_red_rate=false_red_rate(counts_mapping),
        buckets=counts,
        classifier_coverage=classifier_coverage(counts_mapping),
    )
    return ReportState(
        schema=schema,
        generated_at=generated_at,
        target_workflow=target_workflow,
        cursor=cursor,
        enumerated_run_ids=tuple(sorted_run_ids(completed)),
        lineage=window.lineage,
        headline=headline,
    )

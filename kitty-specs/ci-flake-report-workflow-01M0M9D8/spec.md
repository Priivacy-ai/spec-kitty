# Mission Specification: CI Flake-Report Workflow

**Mission Branch**: `kitty/mission-ci-flake-report-workflow-01M0M9D8`
**Created**: 2026-08-22
**Status**: Draft (post-spec squad revision v2)
**Input**: Turn the manual squad flake-analysis into a repeatable, scheduled measurement; plus a draft-vs-ready CI execution mode (fail-fast for drafts, full-*relevant*-signal for ready PRs).

## Overview

CI red on this repository is dominated by inactionable false-reds. A one-off squad measurement over a ~2.4-day window found **58.6% of CI failures were false-red** (flake, not defect), **48.3%** of them the wall-clock/timing class, and **~92% false-red on main-branch runs**. That analysis was produced by hand across six agent lenses; nothing re-runs it, so the trend is invisible between manual audits.

This mission delivers two capabilities that share one north star — *make the CI signal trustworthy and cheap* — partitioned into separately-landable work streams:

- **Capability A — Flake-Report measurement (core, shippable alone):** a script plus a scheduled/on-demand CI workflow that quantifies the false-red rate and per-test timing cost **incrementally each week**, storing findings as artifacts only.
- **Capability B — Draft/ready CI execution mode (separate WP; touches merge-gating `ci-quality.yml`):** **draft** PRs run **fail-fast** — a canceller stops the chain on the first failure (quick, cheap iteration); **ready** PRs run **full *relevant* signal** — for the domains the diff touches, chains run to completion so every relevant failure surfaces in one pass, while **untouched domains stay un-triggered** (existing path-filtering preserved). A **red-first re-run** ordering makes a new push to a previously-red PR execute the just-failed tests first, so a still-broken fix goes red fastest. The aggregate quality-gate **still blocks merge** in both modes; branch protection is unchanged.

**Existing machinery (must unify, not duplicate).** `ci-quality.yml` already carries a draft/ready model: the `ready_for_review` trigger, `quality_gate_decision.py` draft-aware gating, path-filtered `changes` detection, and a merge-gate contract guarded by `tests/architectural/test_suite_jobs_gate_blocking.py` and `test_ci_quality_path_filters.py`. Capability B extends this seam; it must keep those guard tests green and classify any new job as blocking-or-allowlisted.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Weekly false-red trend, incrementally (Priority: P1)

A maintainer wants to know, without re-running a manual squad, how much of this week's CI red was inactionable flake versus real defect, and which tests carry the timing cost — measured only over runs since the last report.

**Why this priority**: The shippable core and the mission's reason to exist. Independently valuable even if Capability B never ships.

**Independent Test**: Run the script against the committed golden reference fixture (a frozen run/log set); confirm it emits `metrics.json`, `durations.json`, `report.md`, `state.json`, and that the false-red rate and per-test medians reproduce the fixture's expected values within the stated tolerance.

**Acceptance Scenarios**:

1. **Given** a prior `state.json` artifact with a recorded window cursor, **When** the weekly job runs, **Then** it processes only runs whose completion is newer than the cursor (half-open), reports the delta versus the previous headline metrics, and advances the cursor only past *completed* runs.
2. **Given** no prior state artifact is found (first run, or lineage lost), **When** the job runs, **Then** it looks back 30 days from the run start and produces a full baseline, and the report states whether this was a true first run vs a lost-baseline fallback.
3. **Given** findings are produced, **When** the job finishes, **Then** the four artifacts are uploaded with a stable name independent of the workflow's display name and `retention-days: 90`; nothing is committed to the repo and no docs are modified.
4. **Given** a week with no newly-completed runs since the cursor, **When** the job runs, **Then** it reports "no new runs" and carries the previous state forward unchanged.
5. **Given** a run that was in progress at the previous report time and completed afterward, **When** the next delta runs, **Then** that run is enumerated exactly once (no permanent skip, no double-count).
6. **Given** a failure run whose logs are expired/unavailable, **When** it is classified, **Then** it lands in `needs_review`, is counted, and is excluded from the false-red-rate numerator and denominator.

---

### User Story 2 - Fast, cheap iteration on drafts; complete relevant signal on ready PRs (Priority: P2)

A contributor iterating on a **draft** PR wants the first failure fast and cheap. A reviewer on a **ready** PR wants every *relevant* failure in one pass, without fix-one-see-the-next.

**Why this priority**: High-value ergonomics and compute savings, but it touches merge-gating `ci-quality.yml`, so it is a separate, independently-landable WP behind the core.

**Independent Test**: Static assertion of the workflow structure (canceller job present with `actions: write`, in the NON_BLOCKING_ALLOWLIST; ready jobs use `if: always()`/relevance; gate reads `needs.<job>.result`) plus a sandbox PR: a draft with a failing early job cancels the chain; the same PR marked ready runs all *relevant* chains to completion; an untouched domain's suite stays un-triggered; merge stays blocked while a real failure is present.

**Acceptance Scenarios**:

1. **Given** a PR in **draft**, **When** an early job fails, **Then** the canceller stops the run/chain (fail-fast) and downstream jobs do not run.
2. **Given** a PR marked **ready**, **When** a job in a *relevant* (diff-touched) chain fails, **Then** the remaining relevant jobs still run to completion (full relevant signal) and all relevant failures are reported in that run.
3. **Given** a ready PR whose diff does **not** touch domain X, **When** CI runs, **Then** domain-X suites remain un-triggered (path-filtering preserved; full signal = full *relevant* signal).
4. **Given** a ready PR with a real failing job, **When** CI completes in full-signal mode, **Then** the aggregate quality-gate reads real step outcomes (`needs.<job>.result`, not a `continue-on-error`-masked success) and reports failure, so merge remains blocked.
5. **Given** a draft PR (whose fail-fast run cancelled required checks) is marked **ready**, **When** `ready_for_review` fires, **Then** a fresh full-relevant-signal run re-emits every branch-protection required-check context for the touched domains.
6. **Given** a PR whose previous run had failing tests, **When** a new commit is pushed, **Then** the previously-failed test nodeids run **first** (before the rest of the relevant suite) and their result is reported before the remainder completes.

---

### Edge Cases

- **Red-first list staleness**: previously-failed nodeids that were removed/renamed in the new commit are skipped harmlessly; the rest of the relevant suite still runs. No prior red (first push, or previously green) → red-first is a no-op with normal ordering.

- **Conclusion taxonomy**: `cancelled` (superseded push) and `action_required` (fork PR never ran), plus `skipped`/`neutral`/`stale`, are excluded from *both* numerator and denominator; `success`/`failure`/`timed_out`/`startup_failure` are the completed set.
- **Mixed-failure run** (timing flake + real defect) → classified **real/actionable**, with the co-occurring flake noted so raw flake incidence isn't understated.
- **Re-run / new attempt** after the window closed → keyed on run-id+attempt (or `updatedAt`) so the new conclusion is not lost to a stale `createdAt` cursor.
- **Corrupt/partial prior `state.json`** (e.g. a prior run hit a `gh` rate-limit) → schema-validated on read; invalid → treated as no-baseline (30-day fallback), flagged in the report.
- **`gh` rate-limit / API error** mid-mining → partial report with explicit gap annotations, not a silent short count.
- **`--durations` top-N truncation**: sub-second budget tests fall below the slice; a suite that runs pytest without `--durations` contributes zero samples — the report discloses both so absence ≠ zero cost.
- **`gh` pagination**: enumeration pins an explicit `--limit` and sorts by timestamp in-script so the input set is page-complete and stable.
- **Canceller race**: the draft canceller races the jobs it cancels; a job that finishes before the cancel API call still reports — accepted, and the canceller is non-gating (allowlisted).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Run enumeration & conclusion taxonomy | As a maintainer, I want each target-workflow run over a window enumerated and mapped by a pinned conclusion taxonomy (completed = {success, failure, timed_out, startup_failure}; excluded from all metrics = {cancelled, action_required, skipped, neutral, stale}) so that denominators are well-defined. | High | Open |
| FR-002 | Classification + pinned false-red rate | As a maintainer, I want each *completed failure* bucketed into `perf_timing_flake` / `infra_flake` / `real` / `needs_review` via a documented signature table (signatures keyed on test nodeids, not message substrings, where possible), with `false_red_rate = (perf_timing_flake + infra_flake) / (perf_timing_flake + infra_flake + real)` and `needs_review` reported separately and excluded from that rate, so the headline metric is reproducible. | High | Open |
| FR-003 | Per-test duration mining | As a maintainer, I want per-test CALL durations mined from run logs and aggregated (n, median/mean/max) with a defined long-pole threshold (median > 2s), and the report to note any mined suite that does not emit `--durations`, so timing cost is visible and its gaps disclosed. | High | Open |
| FR-004 | Incremental delta with correct boundary | As a maintainer, I want each report to process only runs completed after the previous cursor (half-open on completion time), advance the cursor only past completed runs (carrying an in-progress low-water mark so straddling runs are enumerated once when done), never regress the cursor, and compare current vs previous headline metrics. | High | Open |
| FR-005 | First-run / lost-baseline 30-day lookback | As a maintainer, I want the first run (or a run where the prior baseline is missing/corrupt) to look back 30 days from run start, with the report distinguishing "true first run" from "baseline lost", so there's always a baseline without silent regression to rescan. | High | Open |
| FR-006 | Flake-findings emitted as artifacts only | As a maintainer, I want the flake-report *findings* (`metrics.json`, `durations.json`, `report.md`, `state.json`) uploaded as artifacts with no repo commit and no docs change, so the report never mutates the tree. (Scope: findings only — Capability-B runbook edits under FR-013 are permitted.) | High | Open |
| FR-007 | Weekly + on-demand workflow with stable delta lineage | As a maintainer, I want a dedicated workflow on a weekly schedule plus `workflow_dispatch`, that retrieves the prior state artifact by a **stable name independent of the workflow display name**, validates its schema, uploads new findings with `retention-days: 90`, and falls back to 30-day baseline when no valid prior state exists. | High | Open |
| FR-008 | Bounded work with quantified caps | As a maintainer, I want concrete caps — at most 200 classified failures and 50 most-recent duration-mined runs per report, a per-log-fetch timeout, and `--log-failed`/selective `gh api` fetches over full-run-log zips — with the dropped count logged, so runtime is bounded without silent truncation. | Medium | Open |
| FR-009 | Draft fail-fast canceller | As a contributor, I want a draft PR's chain to stop on the first job failure via a dedicated canceller job (`actions: write`, calls the run-cancel API), so I get the first failure fast and cheap. | Medium | Open |
| FR-010 | Ready full-*relevant*-signal | As a reviewer, I want a ready PR to run all *diff-relevant* chains to completion (`if: always()`/relevance so a failed upstream doesn't skip its relevant downstream), while untouched domains stay un-triggered, so I see every relevant failure in one pass without running irrelevant suites. | Medium | Open |
| FR-011 | Merge-gate preserved (no false-green) | As a maintainer, I want the aggregate gate to block merge on any real failure in both modes, reading real step outcomes (`needs.<job>.result`), and I want full-signal to NOT be achieved via `continue-on-error` on gating jobs, so full-signal never means un-gated. | High | Open |
| FR-012 | Ready-transition re-emits required contexts | As a reviewer, I want `ready_for_review` to trigger a full-relevant-signal run that re-emits every branch-protection required-check context for the touched domains, so a draft's cancelled checks don't leave the PR stuck. | Medium | Open |
| FR-013 | Runbook: green-before-RFR | As a contributor/agent, I want the runbooks to document the draft=fail-fast / ready=full-relevant-signal contract and the rule that draft-PR users monitor their run until all jobs conclude `success` before flipping to ready-for-review, so a reviewer's full-signal pass isn't spent on a PR the author already knows is red. | Medium | Open |
| FR-014 | Configurable target workflow | As a maintainer, I want the measured workflow to default to `ci-quality.yml` but be overridable by input, so the tool can widen later without a rewrite. | Medium | Open |
| FR-015 | Coverage + reproducible input set | As a maintainer, I want `metrics.json` to carry classifier-coverage % (auto-classified ÷ completed failures), the `needs_review` count as first-class headline fields tracked in the delta, and the enumerated run-id set recorded in `state.json`, so classifier decay is visible and output is reproducible. | Medium | Open |
| FR-016 | Gate-contract guard for Capability B | As a maintainer, I want every Capability-B job (incl. the canceller) classified blocking-or-allowlisted in the same WP and `test_suite_jobs_gate_blocking.py` / `test_ci_quality_path_filters.py` kept green, so the draft/ready change cannot silently break the merge-gate contract. | High | Open |
| FR-017 | Golden reference fixture | As a maintainer, I want the reference window's raw run/log sample and expected classification/durations committed under the `tests/ci/fixtures/flake_report/`, so NFR-003 stays reproducible after live logs age out (C-006). | High | Open |
| FR-018 | Red-first re-run ordering | As a contributor, I want a new push to a PR whose previous run was red to run the previously-failed test nodeids FIRST (persisted from the prior run, ahead of the rest of the relevant suite), so I learn whether the fix worked as fast as possible; missing/renamed nodeids are skipped harmlessly. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Dependency-light tooling | The flake-report script uses only the Python standard library plus the `gh` CLI (no new third-party deps); passes `ruff` and `mypy --strict` with zero issues; functions kept at cyclomatic complexity ≤ 15. | Maintainability | High | Open |
| NFR-002 | Bounded weekly runtime | With the FR-008 caps applied, the weekly job completes in under 15 minutes for a typical week's run volume. | Performance | Medium | Open |
| NFR-003 | Classification fidelity vs a frozen fixture | Verified against the committed golden fixture (FR-017), the classifier reproduces expected buckets with false-red rate within ±2 percentage points and per-test median within ±10%, and routes every unmatched failure to `needs_review` (zero silent mis-bucketing). | Reliability | High | Open |
| NFR-004 | Deterministic output | Given the recorded input run-id set (FR-015), report content is byte-deterministic apart from explicit timestamps (stable ordering; in-script sort). | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Flake-findings: artifacts only | Flake-report *findings* are artifacts only — no auto-commit and no wiring into docs. (Does not restrict FR-013 runbook guidance, which is contributor-authored prose about the CI contract.) | Technical | High | Open |
| C-002 | Flake-report is non-gating | The flake-report workflow must not be a required status check and must never block a merge. | Technical | High | Open |
| C-003 | Gating semantics preserved | Capability B must not alter branch-protection required checks or the merge-gate contract; full-relevant-signal still blocks merge on real failure; no `continue-on-error` on gating jobs. | Technical | High | Open |
| C-004 | CI auth & permissions | The script authenticates `gh` via the workflow token (`actions: read` for enumeration/logs/artifacts); the FR-009 canceller job needs `actions: write`. Forked-PR runs may be unreadable in some org configs — the scheduled census targets internal/main runs. | Technical | High | Open |
| C-005 | Duration truncation disclosed | `--durations` prints only top-N slowest per job; the report must disclose that absence of a test ≠ zero cost. | Technical | Medium | Open |
| C-006 | Rolling history window | `gh` log/artifact retention (~90 days) bounds available history; the tool is a rolling census, not an all-time record. | Technical | Medium | Open |

### Key Entities

- **CI Run**: id, attempt, headBranch, PR number, event, `conclusion`, `status`, draft flag, createdAt, completedAt/updatedAt.
- **Failure Classification**: bucket (`perf_timing_flake` / `infra_flake` / `real` / `needs_review`) + reason + matched signature (nodeid where possible).
- **Test Duration Aggregate**: test node — n, median/mean/max CALL seconds, long-pole flag.
- **Report State**: window cursor (completion-time low-water mark), enumerated run-id set, generated-at, previous headline metrics, lineage flag (first-run vs lost-baseline).
- **Findings Bundle**: `metrics.json`, `durations.json`, `report.md`, `state.json`.
- **Golden Fixture**: committed frozen run/log sample + expected buckets/durations for NFR-003.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A run emits all four artifacts and, when a valid prior state exists, covers only runs completed after the cursor (half-open), advancing the cursor monotonically past completed runs only.
- **SC-002**: With no valid prior state, the analysed window is the trailing 30 days measured from run start, and the report labels it first-run vs lost-baseline.
- **SC-003**: Against the committed golden fixture, the report's false-red rate is within ±2pp and per-test medians within ±10% of expected, `false_red_rate` uses the FR-002 formula, and every unmatched failure is bucketed `needs_review`.
- **SC-004**: A draft PR with a failing early job cancels its chain (observably fewer job-minutes); the same PR marked ready runs all *diff-relevant* chains to completion while untouched domains stay un-triggered; a `continue-on-error` step cannot green a required job, and merge stays blocked while a real failure is present.
- **SC-005**: An on-demand `workflow_dispatch` run produces the same artifact set as the scheduled run, commits nothing, and changes no docs.
- **SC-006**: The contributor/agent runbooks state the draft=fail-fast / ready=full-relevant-signal contract and the "all jobs `success` before flipping to ready-for-review" rule, in named, discoverable files.
- **SC-007**: `metrics.json` reports classifier-coverage % and `needs_review` count as headline fields, and `test_suite_jobs_gate_blocking.py` / `test_ci_quality_path_filters.py` stay green after Capability B.
- **SC-008**: On a push to a PR with a prior red run, the previously-failed nodeids execute before the remainder of the relevant suite (observable ordering), so a still-failing fix surfaces before the full suite finishes; a green/absent prior run yields normal ordering.

---
title: 'ADR: Statistical performance-test pipeline (pytest-benchmark), off the PR path, per-domain'
description: 'Adopt pytest-benchmark + a per-domain performance.yml pipeline; all wall-clock performance tests run there only, off the PR path; the single-shot on-PR timing gate is retired.'
status: Accepted
date: '2026-08-22'
---

## Context and Problem Statement

Single-shot wall-clock budget assertions on shared CI runners are a **noisy signal**. A six-lens squad audit over a ~2.4-day window (mission `ci-flake-report-workflow-01M0M9D8`) measured **58.6% of CI failures as inactionable false-red**, **48.3% of them the wall-clock/timing class**, and **~92% false-red on main-branch runs**. Two tests carried 11 of 14 timing reds — a single cold-start outlier tripping a tight ceiling (e.g. warm runs `[2.744, 10.719, 3.056]` vs a 6.0s budget). A single-shot assertion on a busy runner cannot distinguish "code got slower" from "the runner was busy this minute", so it blocks unrelated PRs.

The repo already carries an interim mitigation (#3593): a `performance` pytest marker + an env-gated skip (`SPEC_KITTY_RUN_PERFORMANCE=1`, `tests/conftest.py`). But the design was never completed, and the population is fragmented:

- **`@pytest.mark.performance`** (3 tests) — held off the PR path, but measured single-shot, no statistics, no baseline.
- **`@pytest.mark.timing`** (2 tests) — still runs **on the PR path** in a dedicated `timing-nfr-serial` gate that **blocks merge** — the home-pin `three_warm_runs` test here is the single largest flake source.
- **~60 unmarked wall-clock budget asserts** — still running in contended parallel shards on every PR (the dangerous residue).

Issue #3595 asked for the "proper long-term fix": a dedicated, out-of-band job that measures timing **statistically** (Monte-Carlo iterate-and-aggregate → weighted-average/percentile) and **alerts on regression against a baseline**, never a single-shot hard assertion. It suggested a small hand-rolled harness and said not to pull in a heavy framework.

## Decision

**Adopt `pytest-benchmark` as the measurement engine and introduce a dedicated, per-domain `performance.yml` CI pipeline. ALL wall-clock performance tests run in that pipeline ONLY — never on any PR/blocking path — and the single-shot on-PR `timing` gate is retired.**

Concretely:

1. **Engine: `pytest-benchmark` (test-extra dependency).** It provides exactly what #3595 specifies as a maintained library: calibrated rounds × iterations with **warmup discard**, min/median/**mean/stddev/iqr/percentile** reporting, `--benchmark-save`/`--benchmark-compare`, and **`--benchmark-compare-fail=median:<pct>`** for baseline-relative regression alerting (non-zero exit). Verified working on this repo's **pytest 9.0.3** (5.2.3, released 2026-02). This **supersedes** #3595's "don't pull in a heavy framework" steer — a deliberate reversal: a maintained, statistically-correct engine beats a hand-rolled harness we would have to maintain and get right ourselves.

2. **The `performance` marker is the single home for every wall-clock/CPU-budget test.** The retired `timing` marker folds into `performance`. All ~60 genuine budget asserts are marked `performance`. `tests/conftest.py` already skips `-m performance` unless `SPEC_KITTY_RUN_PERFORMANCE=1`, so marking a test **removes it from every PR and blocking run**. No PR-path job selects `-m performance`, and the `timing-nfr-serial` on-PR gate is deleted.

3. **`performance.yml` is per-domain sharded, mirroring `ci-quality.yml`.** A scheduled (nightly/weekly) + `workflow_dispatch` workflow with one job per domain (doctrine, charter, sync, cli, core, lanes, merge, missions, next, review, status, upgrade, …), each running `SPEC_KITTY_RUN_PERFORMANCE=1 pytest -m performance <domain-paths> --benchmark-only --benchmark-compare-fail=median:<tolerance>` against a **committed per-domain baseline** under `tests/performance/baselines/`. It is **off the PR path** (no `pull_request` trigger), **non-gating** (not a required check), and uploads the benchmark JSON as artifacts. A `workflow_dispatch` input refreshes a baseline into an artifact for a human PR — never auto-commit.

### What moves and what explicitly does NOT

- **Moves to `performance` (off PR):** every test whose assertion is a **wall-clock or CPU budget** — `assert elapsed < N`, p95/p99 budgets, `_under_Ns` / `completes_under` / NFR-latency ceilings, AST/scan-duration budgets.
- **Stays on the PR path (NOT a performance test):** **behavioral non-hang / timeout guards** — a test that asserts elapsed time only to prove an operation *did not hang / did not block on a lock or a network wait* (e.g. fan-out-didn't-block, lease-wait-bounded, ReDoS-bound). These assert **correctness** (bounded behavior), not a performance budget; relocating them would drop a real correctness signal. The census in `ci-flake-report-workflow` already separated these two classes; only the budget class moves.

### Migration is per-domain and incremental

The 5 currently-marked tests (3 `performance` + 2 `timing`) are converted to the `benchmark` fixture with per-domain `group=` and committed baselines as the **exemplar** shape. The ~60-test residue is **marked `performance`** (so it is off the PR path immediately) and converted to the `benchmark` fixture **per domain** as follow-through — a test still asserting single-shot but running only in `performance.yml` is already off the blocking path; the statistical conversion is a quality increment, not a gate. Bulk-marking follows the occurrence-classification guardrail.

## Consequences

- **Positive:** the dominant false-red class leaves the PR/blocking path entirely; timing regressions are caught statistically vs a baseline, off-band, with no single-shot ceiling; the pipeline scales per-domain like the main CI; **never retry-to-green**.
- **Negative / risks:** a new test dependency (`pytest-benchmark` + `py-cpuinfo`); baselines are runner-class-specific (`blacksmith-4vcpu-ubuntu-2404`) and must be re-recorded if the runner changes (pinned in baseline metadata, warn-not-fail on mismatch); the on-PR timing signal is deferred to the scheduled run (acceptable — that signal was ~92% false-red).
- **Guard-test updates:** retiring `timing-nfr-serial` requires updating the arch tests that pin it (`tests/architectural/test_ci_quality_path_filters.py`, `_gate_coverage.py`, and the marker registry in `pytest.ini`). The `performance` marker's env-gate skip is unchanged.

## Alternatives considered

- **Hand-rolled iterate-and-aggregate harness (#3595's original suggestion).** Rejected: reimplements calibration, warmup, outlier handling, and baseline compare that `pytest-benchmark` already does correctly and maintains. The "don't add a framework" steer is reversed deliberately (see Decision §1).
- **`pytest-repeat` (`@pytest.mark.repeat(N)`).** Rejected as the engine: it reruns a test N times as independent **cold-start** items with no timing aggregation or baseline — the opposite of the warm, statistical measurement #3595 wants. (Useful for flake-hunting, not perf measurement.)
- **Keep the single-shot on-PR `timing` gate.** Rejected: it is the single largest false-red source in the measured window.

## References

- #3595 (dedicated performance-test workflow), #3593 (interim `performance` marker), epic #1931 (test-suite friction), #2342 (retrospective 5s NFR — a migration candidate).
- Mission `ci-flake-report-workflow-01M0M9D8` (the measurement that motivated this) and its `flake_report` false-red evidence.
- `pytest-benchmark` 5.2.3 usage docs; verified on pytest 9.0.3.

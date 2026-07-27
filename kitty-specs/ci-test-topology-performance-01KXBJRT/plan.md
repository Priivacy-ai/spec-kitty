# Implementation Plan: CI Test-Topology Performance

**Branch**: `feat/ci-test-topology-performance` (→ PR to `main`) | **Date**: 2026-07-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/ci-test-topology-performance-01KXBJRT/spec.md`

## Summary

Re-topologize the slowest PR-gating CI jobs — parallelize, shard, and re-scope selection — **without dropping coverage** and **without breaking real-port serial isolation**, by *generalizing* the project's existing shard substrate rather than cloning it. Grounded in run 29196440986 (`integration-tests-next` 69.2 min serial; `fast-tests-core-misc` 12.2 min imbalanced; `fast-tests-charter` 12 min; `slow-tests` 10.7 min; `fast-tests-cli` 8.3 min). Also restore a *fair* Sonar coverage denominator (exclude migration/glue/static; feed the Playwright UI-e2e suite's coverage in). Load-bearing invariant: coverage preservation enforced against a committed pre-change node-id baseline via the existing `_gate_coverage` model — not a marker-partition guard that proves assignment rather than execution.

**Engineering Alignment (confirmed via post-spec squad, no open decisions):** one N-group shard registry (arch + next as data rows); coverage-preservation wired into `_gate_coverage.same_tier_shard_counts` + orphan ratchet + required-selection-structures; a committed real-port fixed-range registry consumed by a generalized `test_serial_port_preservation.py`; budgets are measured-and-recorded (mirror `_TIMINGS_BASELINE`), not hard gates. No product code changes — only test-harness data/guards, CI workflow YAML, Sonar config, and docs.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pytest, pytest-xdist (`-n auto --dist loadfile`), GitHub Actions (matrix), SonarCloud (`sonar-project.properties`), Playwright (`tests/ui/`, headless), the in-repo test-topology substrate (`tests/_arch_shard_map.py`, `tests/conftest.py` collection hook, `tests/architectural/_gate_coverage.py`)
**Storage**: committed repo data files (shard registry `.py` tables, real-port registry, baseline node-id manifest, `_TIMINGS_BASELINE` timings artifact) — no runtime datastore
**Testing**: architectural/guard tests under `tests/architectural/` (completeness, serial-port preservation, workflow-YAML lint, marker-baseline); collection-equivalence re-verification per the stability ratchet; changes validated by real CI runs
**Target Platform**: GitHub Actions `ubuntu-latest` runners (assume ≥4 cores for the interim budgets; confirmed by the FR-001 `--durations` run)
**Project Type**: single (CI/test-infrastructure of a Python CLI monorepo)
**Performance Goals**: `integration-tests-next` ≤ 7 min (from 69.2); `slow-tests` ≤ 4; `fast-tests-cli` ≤ 5.5; `fast-tests-core-misc`/`fast-tests-charter` ≤ 7; `fast-tests-sync` −~130 s; shard skew ≤ 20%
**Constraints**: `--dist loadfile` only (never bare `load`); fixed-range real-port suites stay serial `-n0`; 0 tests dropped / double-run (enforced); sharded matrices carry `fail-fast: false`; no marker moved to hit a budget; no coverage-padding
**Scale/Scope**: ~45 CI jobs (ceiling 57), ~979 measured src files, 9 targeted jobs, 11 WPs (A–K)

## Charter Check

*GATE: Must pass before Phase 0. Re-checked after Phase 1.*

Template set `software-dev-default` (compact charter). Relevant standing orders — all **PASS by construction** in this plan:
- **Canonical Sources / Unification (DIR / D-044):** FR-002 *generalizes* the shard substrate to one registry; it does not clone a parallel mechanism. ✅
- **Close defect classes by construction (D-043):** real-port isolation via a committed registry + generalized guard; coverage preservation via a committed baseline diff — not per-file ad-hoc checks. ✅
- **Tests as scaffold / no fakeable DoD (D-041 / D-030):** the completeness guard is wired to `_gate_coverage` (execution + selection), not a marker-partition clone; C-005 is a marker-baseline diff, not an intent clause. ✅
- **Coverage is indicative — never pad (coverage memory):** the coverage-denominator work (WP-J/K) removes glue and credits real e2e coverage; it does NOT add frivolous tests to chase 80%. ✅
- **No suppression / ruff+mypy clean:** all new guard/registry code obeys the standard gates. ✅

No violations → Complexity Tracking is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/ci-test-topology-performance-01KXBJRT/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (registry/manifest/artifact schemas)
├── quickstart.md        # Phase 1 output (local verify recipe)
├── contracts/
│   └── guard-contracts.md   # invariant contracts the guards enforce
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code / surfaces touched (repository root)

```
tests/
├── _arch_shard_map.py                 # → GENERALIZE to an N-group shard registry (arch as data)
├── _next_shard_map.py                 # NEW data registration for integration-tests-next legs
├── _real_port_suites.py               # NEW committed registry of fixed-range daemon suites
├── conftest.py                        # collection hook: iterate registered shard groups
├── architectural/
│   ├── _gate_coverage.py              # coverage-preservation authority (same_tier_shard_counts, _TIMINGS_BASELINE)
│   ├── test_gate_coverage.py          # required-selection-structures + orphan ratchet (extend for next_shard_*)
│   ├── test_arch_shard_marker_completeness.py  # → parametrize over the registry
│   ├── test_serial_port_preservation.py        # → consume _real_port_suites.py (whole family)
│   ├── test_next_shard_marker_completeness.py   # NEW
│   ├── test_workflow_dist_lint.py     # NEW: C-001/C-002/C-007 YAML lint guard
│   └── baselines/next-nodeids.txt     # NEW committed pre-change node-id baseline (per re-scoped job)
└── sync/_daemon_harness.py            # fixed-range binder (source of the real-port family)

.github/workflows/
├── ci-quality.yml                     # job blocks: integration-tests-next, slow-tests, fast-tests-sync,
│                                       #   fast-tests-cli, fast-tests-core-misc, fast-tests-charter,
│                                       #   serial integration-tests-*, quality-gate.needs roster
└── ui-e2e.yml                         # add --cov / coverage feed (WP-K)

sonar-project.properties               # add sonar.coverage.exclusions (WP-J)
docs/guides/testing-parallel.md, docs/plans/testing/test-suite-acceleration-plan.md   # WP-G docs
```

**Structure Decision**: single-project CI/test-infrastructure change. No `src/` product code is modified; the "model" of this mission is committed *data* (shard registry, real-port registry, baseline manifest, timings artifact) plus architectural guards and workflow YAML.

## Complexity Tracking

*No Charter Check violations — none.*

## Implementation Concern Map

> Concerns, not WPs. `/spec-kitty.tasks` maps these to executable work packages (one IC may become several WPs, e.g. IC-04 fans out per job).

### IC-01 — Generalize the shard substrate to an N-group registry
- **Purpose**: One registry/hook/parametrized-guard drives all pole sharding; `arch` and `next` become data rows (satisfies C-003, D-044).
- **Relevant requirements**: FR-002; enables FR-010.
- **Affected surfaces**: `tests/_arch_shard_map.py` (generalize), `tests/_next_shard_map.py` (new data), `tests/conftest.py` hook, `tests/architectural/test_arch_shard_marker_completeness.py` (parametrize), new `test_next_shard_marker_completeness.py`.
- **Sequencing/depends-on**: consumes IC-04's `integration-tests-next` `--durations` evidence for balance; foundational for IC-04's `next` matrix and the `fast-tests-core-misc` rebalance.
- **Risks**: refactoring the arch table must keep `arch_shard_1/2/3` byte-stable (no arch-pole regression); the parametrized completeness guard must stay green for arch on day one.

### IC-02 — Coverage-preservation, enforced not asserted
- **Purpose**: Prove the executed-test *union* is unchanged (0 dropped / 0 double-run) against a committed baseline — the load-bearing invariant.
- **Relevant requirements**: FR-007, NFR-005, C-004; also protects Sonar `new_coverage` from regression.
- **Affected surfaces**: `tests/architectural/_gate_coverage.py` (`same_tier_shard_counts`, orphan ratchet), `test_gate_coverage.py` (`test_required_selection_structures_present` — add `next_shard_*`; `_REQUIRED_CORE_MISC_SHARDS`), committed `tests/architectural/baselines/*-nodeids.txt`, `fail-fast: false` on new matrices (C-006).
- **Sequencing/depends-on**: each selection-changing concern (IC-04) must ship its slice of this guard; the cross-job disjointness check (no double-run between the `-n0` orphan job and the sync pool) lives here.
- **Risks**: a marker-partition clone would be false-green on skipped/cancelled legs — MUST wire into `_gate_coverage` + shard-in-workflow linkage instead.

### IC-03 — Real-port fixed-range family isolation
- **Purpose**: Keep the *whole* `find_free_port_in_range` daemon family serial `-n0`; ephemeral port-0 binders stay parallel.
- **Relevant requirements**: FR-004, C-002, Scenario 3.
- **Affected surfaces**: new `tests/_real_port_suites.py` registry (orphan_sweep + daemon_orphan_classification + daemon_cleanup_boundary + issue_1071), generalize `test_serial_port_preservation.py` to consume it, `tests/sync/_daemon_harness.py` (source of truth for the range).
- **Sequencing/depends-on**: MUST land before IC-04 parallelizes `integration-tests-sync` (else the family scatters).
- **Risks**: FR-006's sweep is where the hidden family gets parallelized — the registry+guard must be in place first.

### IC-04 — Per-job parallelization, sharding & budgets
- **Purpose**: Apply the topology changes to each targeted job and record measured budgets.
- **Relevant requirements**: FR-001, FR-003, FR-004, FR-005, FR-006, FR-008, FR-010, FR-011; NFR-001..008.
- **Affected surfaces**: `.github/workflows/ci-quality.yml` job blocks (integration-tests-next flags + `next` matrix; slow-tests path-narrow + parallel; orphan-sweep → separate job; fast-tests-cli file split; fast-tests-core-misc rebalance; fast-tests-charter step split; serial integration-tests-* sweep), `_TIMINGS_BASELINE` update.
- **Sequencing/depends-on**: `integration-tests-next` shard (FR-002/IC-01) after its `--durations` (FR-001); `fast-tests-core-misc` rebalance (FR-010) after IC-01; the roster edits funnel through IC-05.
- **Risks**: `--dist loadfile` slowest-single-file floor caps `integration-tests-next`; the FR-011 charter job is two sequential `-n auto` steps (split to jobs); runner core-count assumption gates the interim budget.

### IC-05 — Shared CI-YAML roster/aggregation seam
- **Purpose**: One owner for every `quality-gate.needs` / `slow-tests.needs` roster edit + the `test_job_count_ceiling.py` ceiling, so job-adding concerns don't textually collide.
- **Relevant requirements**: cross-cutting for FR-004/FR-006 (new jobs); C-007.
- **Affected surfaces**: `ci-quality.yml` `needs:` arrays, `test_job_count_ceiling.py`, new `test_workflow_dist_lint.py` (no bare `load`; `-n auto`⇒`loadfile`; fixed-range never under `-n auto`; cross-job disjoint).
- **Sequencing/depends-on**: absorbs the job-add edits from IC-03/IC-04; the lint guard formalizes C-001/C-002.
- **Risks**: enumerated `needs:` list is the guaranteed merge-conflict point — serialize or single-own it.

### IC-06 — Coverage-denominator fairness
- **Purpose**: Make the Sonar LOC-to-test denominator reflect testable code — exclude glue, credit the Playwright suite.
- **Relevant requirements**: FR-012, FR-013.
- **Affected surfaces**: `sonar-project.properties` (`sonar.coverage.exclusions`: `src/specify_cli/migration/**`, `**/static/**`, `**/__main__.py`, `src/specify_cli/next/**`); `ui-e2e.yml` (`pytest tests/ui/ --cov …`, merge into the report; `sonar.javascript.lcov.reportPaths` from Playwright/istanbul if feasible).
- **Sequencing/depends-on**: independent of the topology concerns.
- **Risks**: excluding real code by accident — keep exclusions to confirmed glue; JS-lcov wiring may be deferred to Python-cov-only if Playwright coverage export is impractical (document the decision).

### IC-07 — Measurement/ratchet + docs
- **Purpose**: Record real post-change per-leg durations as a committed artifact; update the canonical topology docs; cross-cutting completeness audit.
- **Relevant requirements**: FR-008, FR-009; audit of FR-007 across all changed jobs.
- **Affected surfaces**: `_TIMINGS_BASELINE`-shaped timings artifact (with run-id provenance), `docs/guides/testing-parallel.md`, `docs/plans/testing/test-suite-acceleration-plan.md`; the cross-job union audit.
- **Sequencing/depends-on**: **after IC-01…IC-05** (needs the shipped topology to measure and audit).
- **Risks**: budgets are noisy wall-clock — record, don't hard-gate (flakiness policy); docs drift if not landed same-mission.

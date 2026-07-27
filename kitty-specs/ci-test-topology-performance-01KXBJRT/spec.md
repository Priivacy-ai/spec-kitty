# Feature Specification: CI Test-Topology Performance

**Mission**: `ci-test-topology-performance-01KXBJRT`
**Mission ID**: `01KXBJRTXD8VNCZ859AYM0WEFY`
**Mission type**: software-dev
**Target branch**: `feat/ci-test-topology-performance` → PR to `main`
**Umbrella epic**: #1931 (Test quality & suite hygiene)
**Status**: Draft — refined after post-spec adversarial squad (architect / debugger / reviewer / planner lenses) + run 29196440986 evidence.

## Purpose

Spec Kitty's PR-gating CI has one pathological job and a long tail of sub-optimal ones. This mission re-topologizes those jobs — parallelizing, sharding, and re-scoping selection — so contributors get fast, reliable CI feedback, **without dropping any coverage** and **without removing the serial isolation** real-port / daemon tests require. It builds on the project's existing shard substrate rather than inventing a parallel one.

## Evidence (run 29196440986 — the grounding data)

`main` @ `db904ebc5`, `workflow_dispatch`, overall **FAILURE**. Measured per-job wall-clock (the empirical basis for every budget below):

| Job | Wall-clock | Note |
|-----|-----------|------|
| `integration-tests-next` | **69.2 min** | 441 tests fully serial; no `-n auto`, no `--durations`. The dominant cost. |
| `fast-tests-core-misc (specify-cli-rest)` | 12.2 min | Newly surfaced by the actual timings; already a shard matrix but imbalanced (vs `core-misc` 4.7m). **In scope → WP-H (FR-010).** |
| `fast-tests-charter` | 12.0 min | Newly surfaced; already `-n auto` but two sequential steps sum. **In scope → WP-I (FR-011).** |
| `slow-tests` | 10.7 min | ~4 min is full-tree collection tax. |
| `fast-tests-cli` | 8.3 min | `--dist loadfile` tail on `test_charter_activate_commands.py`. |
| `fast-tests-sync` | 6.3 min | Mid-pack; **lower priority than initially assumed** (serial orphan-sweep step is ~130 s of it). |
| *(failing, now fixed & merged)* | — | `sonarcloud` 4.7m, `fast-tests-agent` 4.3m, `integration-tests-merge` 3.7m |

**Sonar quality gate (branch `main`): FAILED (ERROR)** — `new_coverage 60.1% < 80%`, `new_reliability_rating 3 > 1`, `new_security_rating 3 > 1` (maintainability/duplication/hotspots-reviewed OK). The security rating reflects the 19 code-scanning alerts remediated by merged PR #2579 (14 already-guarded false positives still await Sonar-UI disposition). **Scope split on coverage:** the `new_coverage 60.1%` denominator is partly *unfair* — it counts one-shot migration glue (`src/specify_cli/migration/`, missed by the plural-only exclusion glob), non-Python dashboard assets (`dashboard.js` ~720 lines at 0%), and code the Playwright/UI-e2e suite exercises but whose coverage never reaches Sonar. **Fixing that denominator (exclude glue, feed existing-suite coverage) is IN scope (FR-012/FR-013);** *raising* genuine core-Python coverage and the reliability rating stays OUT (sibling #2071). This perf work must also not *regress* `new_coverage` (protected by the coverage-preservation invariant below).

## User Scenarios & Testing

**Primary actor**: a contributor whose PR is gated by CI (and the maintainer merging to `main`).

- **Scenario 1 — fast PR feedback.** A push touching `tests/next/` no longer blocks for ~70 min; the job runs parallel across a balanced shard matrix within budget.
- **Scenario 2 — no coverage lost (the invariant).** When a job's selection is sharded or re-scoped, the *union of tests actually executed* still equals the pre-change set — none dropped by a narrowed filter, a skipped/cancelled matrix leg, or a de-selecting `-m`/`--ignore`; none run twice across jobs. Enforced against a committed pre-change baseline, not just internal partition consistency.
- **Scenario 3 — real-port safety.** The **fixed-range** daemon test family (not one file) keeps serial `-n0` isolation; no fixed-range port binder is ever scattered across `-n auto` workers.
- **Scenario 4 — evidence-based balancing & measurement.** `integration-tests-next` emits `--durations` first so shards balance on real wall-clock; post-change per-leg durations are measured and recorded as a committed artifact.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `integration-tests-next` MUST run in parallel (`-n auto --dist loadfile`), cache disabled (`-p no:cacheprovider`), durations reported (`--durations=25`). | Proposed |
| FR-002 | Sharding MUST **generalize the existing substrate to an N-group registry**, not clone a second table/hook/guard. Refactor `tests/_arch_shard_map.py` + the `tests/conftest.py` hook + `test_arch_shard_marker_completeness.py` into a group-keyed form (`group → roots, shard_count, marker_prefix, units`); register `next` as data (a 3-leg matrix selected by `-m next_shard_N`). Each `next_shard_N` MUST appear as a required matrix leg (linkage guard), and the `next` matrix MUST set `strategy.fail-fast: false`. | Proposed |
| FR-003 | `slow-tests` MUST narrow collected paths to the directories that actually contain `@slow` tests and run parallel (`-n auto --dist loadfile`), **preserving the existing `--ignore` set** so the executed set is unchanged. Guarded by the `_gate_coverage` reachability model against the job's real `(paths − ignores, -m slow)` selection — not a directory-membership scan. | Proposed |
| FR-004 | The fixed-range real-port suite `test_orphan_sweep.py` (currently a serial `-n0` *step* inside `fast-tests-sync`) MUST be promoted to its **own separate concurrent job** so it leaves that job's critical path; the parallel pool's selection MUST exclude it (no double-run). | Proposed |
| FR-005 | `fast-tests-cli` MUST no longer serialize its tail on one `--dist loadfile` worker: split/regroup `test_charter_activate_commands.py` so its tests fan out, with collection-equivalence re-verified per the stability ratchet. | Proposed |
| FR-006 | Every serial `integration-tests-*` single-dir job **that is not a real-port/daemon job** MUST be parallelized (`-n auto --dist loadfile -p no:cacheprovider`); the exact in-scope job set MUST be enumerated (precise selection criterion, no "e.g."). Any real-port/daemon directory in a swept job MUST be split to a serial `-n0` job/step first. | Proposed |
| FR-007 | Coverage preservation: for every sharded/re-scoped job the union of tests executed after the change MUST equal the set executed before (0 dropped, 0 double-run), enforced against a **committed frozen baseline of pre-change collected node-ids per job** via the existing `_gate_coverage` model (`same_tier_shard_counts` + orphan ratchet + required-selection-structures), fed by each changing WP. | Proposed |
| FR-008 | Post-change per-leg wall-clock MUST be **measured on a real run and recorded as a committed timings artifact** (mirroring `_gate_coverage._TIMINGS_BASELINE`, with the run id as provenance) — budgets are ratcheted, not declared. | Proposed |
| FR-009 | Canonical docs describing the topology (`docs/guides/testing-parallel.md`, `docs/plans/testing/test-suite-acceleration-plan.md`) MUST be updated in the same mission so they don't drift from the shipped topology. | Proposed |
| FR-010 | `fast-tests-core-misc` (already a shard matrix, but imbalanced: `specify-cli-rest` 12.2 min vs `core-misc` 4.7 min) MUST be **rebalanced** so no leg exceeds budget — by splitting the heavy `specify-cli-rest` leg into additional shards **through the FR-002 N-group registry** (data edit, not a new mechanism). | Proposed |
| FR-011 | `fast-tests-charter` (12.0 min despite `-n auto --dist loadfile`) MUST be brought within budget: it runs **sequential `-n auto` steps** (charter + agent) that sum on the job wall-clock and/or carries a `loadfile` single-file tail. Split the sequential steps into concurrent jobs and/or rebalance the heavy file, preserving `--dist loadfile`. | Proposed |
| FR-012 | **Coverage-denominator hygiene.** Duct-tape / one-shot glue and non-Python assets MUST be removed from the Sonar coverage (LOC-to-test) denominator via `sonar.coverage.exclusions` (kept in issue analysis). Concretely add: `src/specify_cli/migration/**` (one-shot mission-state migration/backfill code — the singular sibling of the already-excluded `**/migrations/**`, which the plural-only glob misses; ~1,333 uncovered lines at 0%), `**/static/**` (dashboard JS/CSS, e.g. `dashboard.js` ~720 lines), `**/__main__.py` (CLI entrypoints), `src/specify_cli/next/**` (deprecation shim, removed 3.3.0). | Proposed |
| FR-013 | **Feed the Playwright / UI-e2e suite's coverage into Sonar.** `ui-e2e.yml` runs `pytest tests/ui/` (Playwright-driven) but its coverage does not reach Sonar: (a) the run carries no `--cov`, so server-side dashboard Python exercised by the e2e is uncredited; (b) no JS coverage is produced and Sonar has no `sonar.javascript.lcov.reportPaths`, so `dashboard.js` reads 0% despite being driven by the suite. Wire the e2e Python coverage into the merged report (and JS lcov if feasible), or — for assets that genuinely cannot be covered — exclude them (FR-012) and document the decision. Net: the denominator must credit code the suite actually exercises. | Proposed |

## Non-Functional Requirements (measured-and-recorded targets, not hard CI gates)

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | `integration-tests-next` after FR-001+FR-002, on `ubuntu-latest` (state the runner core count; number contingent on the FR-001 durations run confirming the slowest `loadfile` file-chain < budget) | ≤ 7 min (from 69.2); interim ≤ ~18 min after FR-001 alone at ≥4 cores | Proposed |
| NFR-002 | `slow-tests` after re-scope + parallelize | ≤ 4 min (from 10.7) | Proposed |
| NFR-003 | `fast-tests-sync` critical-path reduction from the orphan-sweep job hoist | ≥ ~130 s off critical path (figure tied to the FR-008 artifact, not asserted) | Proposed |
| NFR-004 | `fast-tests-cli` after tail-fix | ≤ 5.5 min (from 8.3) | Proposed |
| NFR-005 | Coverage preservation (FR-007) — the one *enforced* invariant | 100% of prior node-ids run exactly once vs committed baseline; 0 dropped, 0 double-run | Proposed |
| NFR-006 | Shard-leg balance skew (`next_shard_N` and the rebalanced `fast-tests-core-misc` legs) | ≤ 20% wall-clock spread, verified from the FR-008 artifact | Proposed |
| NFR-007 | `fast-tests-core-misc` slowest leg after rebalance (FR-010) | ≤ 7 min (from 12.2) | Proposed |
| NFR-008 | `fast-tests-charter` after split/rebalance (FR-011) | ≤ 7 min (from 12.0) | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | All parallel runs use `--dist loadfile`; bare `--dist load` prohibited. | Proposed |
| C-002 | **Fixed-range** real-port binders (the `find_free_port_in_range` daemon family, listed in a committed registry) MUST keep serial `-n0` isolation; ephemeral port-0 binders are parallel-safe and are NOT serialized. | Proposed |
| C-003 | Reuse/generalize the shard substrate (one registry, one hook, one parametrized guard); do not invent or clone a parallel mechanism (see FR-002). | Proposed |
| C-004 | Each selection-changing WP ships its own completeness guard; WP-G verifies the union across all changed jobs (see WP ownership). | Proposed |
| C-005 | Markers reflect real test character: a committed guard asserts the identity/count of `@slow`/`@stress`/`@quarantine`-marked tests does **not grow** during this mission (baseline diff), so budget-motivated re-marking is surfaced for review. (Replaces the unfalsifiable "purely to hit a budget" intent clause.) | Proposed |
| C-006 | Every sharded matrix MUST set `strategy.fail-fast: false` so a failing leg cannot cancel siblings (which would silently drop their tests). | Proposed |
| C-007 | A committed workflow-YAML lint guard MUST assert: no bare `--dist load`; every `-n auto` run carries `--dist loadfile`; fixed-range real-port suites never appear under `-n auto`; and per-job selections are cross-job disjoint (no double-run). | Proposed |

## Success Criteria

- SC-001…004: each targeted job meets its NFR budget on the recorded FR-008 run (measured, with run-id provenance) — not on a human eyeballing "a representative run."
- SC-005: coverage-preservation (FR-007/NFR-005) is enforced by a guard wired into `_gate_coverage` against a committed baseline; a dropped or double-run test fails the build.
- SC-006: real-port fixed-range family stays serial and passes; the generalized `test_serial_port_preservation.py` guards the whole family, not one file.
- SC-007: shard assignment is committed data, balanced from measured durations; `arch` and `next` are two registrations of one mechanism.

## Key Entities

- **Shard registry** — one group-keyed table (generalized `_arch_shard_map.py`) that is the SSOT for every pole's disjoint+complete split; `arch` and `next` are data rows.
- **Real-port registry** — committed list of fixed-range `find_free_port_in_range` daemon suites that must stay `-n0`; consumed by the generalized serial-port guard.
- **Baseline node-id manifest** — committed pre-change collected node-ids per job; the FR-007 guard diffs against it.
- **Timings artifact** — committed measured per-leg durations (`_TIMINGS_BASELINE` shape) with run-id provenance.

## Work-Package Ownership & Sequencing

- WP-A (`integration-tests-next` flags + `--durations`) → WP-B (generalize substrate → N-group registry + `next` shards + linkage + `fail-fast:false`); **B depends on A**.
- WP-C/D (`slow-tests`), WP-E (orphan-sweep → separate job), WP-F (`fast-tests-cli` tail), WP-I (`fast-tests-charter`) are independent job blocks.
- WP-H (`fast-tests-core-misc` rebalance, FR-010) consumes the N-group registry, so **WP-H depends on WP-B**.
- WP-J (coverage-denominator exclusions, FR-012) is a standalone `sonar-project.properties` change — independent. WP-K (feed UI-e2e coverage into Sonar, FR-013) is an independent CI/reporting change; WP-J + WP-K together restore a fair coverage denominator.
- **One WP owns all job-roster / `quality-gate.needs` / `slow-tests.needs` edits** (the shared CI-YAML seam + `test_job_count_ceiling.py` ceiling), so job-adding WPs (E, G) don't textually collide.
- **Each selection-changing WP ships its own completeness guard.** WP-G is the cross-cutting audit that verifies the union across all changed jobs + owns FR-009 docs + the FR-008 measurement; **WP-G depends on WP-A…F**.

## Assumptions

- Per-worker HOME isolation makes `tests/next`/`tests/runtime`/the `slow` selection parallel-safe except the fixed-range real-port family.
- `-n auto` scales with `os.cpu_count()`; at 2 cores FR-001-alone yields ~2× (~35 min), not ≤18 min — the interim budget assumes ≥4 cores and is confirmed by the FR-001 durations run.
- The enforceable coverage substrate already exists in `tests/architectural/_gate_coverage.py`; the mission wires into it rather than cloning the weaker marker-partition guard.

## Out of Scope

- #2071 CT test-friction remediation (sibling mission). **Raising** genuine core-Python `new_coverage` and the `new_reliability_rating` stays out — but *fixing the coverage denominator's fairness* (FR-012/FR-013) is in.
- Arch-gate fidelity / consumer-repo parity (#2475 / #2476 / #2534).
- Any change to what tests assert — only how they are selected, distributed, and scheduled.

## Resolved Questions

- **OQ-1 (resolved — in scope):** `fast-tests-core-misc` (12.2m) and `fast-tests-charter` (12.0m), the run's #2/#3 offenders, are **added as WP-H (FR-010) and WP-I (FR-011)**.

## Dependencies & References

- Substrate: `tests/_arch_shard_map.py`, `tests/conftest.py::pytest_collection_modifyitems`, `tests/architectural/test_arch_shard_marker_completeness.py`, `tests/architectural/_gate_coverage.py` (`same_tier_shard_counts`, `_TIMINGS_BASELINE`, orphan ratchet), `test_gate_coverage.py::test_required_selection_structures_present`, `test_serial_port_preservation.py`, `tests/sync/_daemon_harness.py`, `test_job_count_ceiling.py`.
- CI: `.github/workflows/ci-quality.yml` (integration-tests-next, slow-tests, fast-tests-sync orphan-sweep step, sharded matrices' `fail-fast:false`, `quality-gate.needs` roster).
- Docs: `docs/guides/testing-parallel.md`, `docs/guides/testing-flakiness.md`, `docs/plans/testing/test-suite-acceleration-plan.md`.
- Tracker: file one umbrella issue as a native sub-issue of #1931 (its listed members are all closed).

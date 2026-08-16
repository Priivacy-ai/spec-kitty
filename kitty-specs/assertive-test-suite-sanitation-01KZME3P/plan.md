# Implementation Plan: Assertive Test Suite Sanitation

**Branch**: `pr/assertive-test-suite-sanitation` | **Date**: 2026-08-10 | **Spec**: `kitty-specs/assertive-test-suite-sanitation-01KZME3P/spec.md`  
**Input**: Approved specification and post-spec adversarial verdict.

## Summary

Reduce the test suite to executable, causally sensitive guards. First establish a reproducible inventory, a compact evidence ledger, and the #3283 bootstrap fix. Then independently adjudicate inert regression/skip states, dominated duplicates, spent structural/scaffold checks, and disproportionate CI routes. Every deletion names the current authority, route, overlap, and causal/non-causal probe. Final closure compares a frozen base workload to HEAD and requires green contract, architectural, and cross-repository E2E gates.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pytest, pytest-xdist, pytest-cov, filelock, mutmut, PyYAML; GitHub Actions  
**Storage**: repository YAML ledger and Markdown evidence report; pytest JUnit/duration artifacts  
**Testing**: red-first focused pytest; controlled fault/mutation probes; three equivalent collection/timing runs; full parallel suite; serial orphan sweep; mission-review hard gates  
**Target Platform**: Linux CI plus macOS/Windows compatibility-sensitive evidence  
**Project Type**: single Python CLI/package repository with a large pytest suite  
**Performance Goals**: target at least 15% lower median whole-suite collection and fixed-route cost without reducing unique causal coverage  
**Constraints**: no retry-to-green, blanket skip/xfail/quarantine, deliberate red required CI, deletion quota, or marker immunity; PR-only delivery  
**Scale/Scope**: baseline 37,444 nodes, 2,432 test files, 833,936 Python test lines; refreshed planning scan found 173 strict AST-body groups/365 members across 131 files (the earlier projections were 75 stricter and 171 normalized groups), with WP01's deterministic dual manifest authoritative. WP01's runtime census assigned all 234 repository-source scanner files—164 under `tests/architectural/` plus 70 non-architectural AST/source scanners, including the nested enrolment scanner—across six authority-coherent structural WPs.

## Charter Check

- **Charter loaded**: PASS — compact `plan` context resolves DIR-001..DIR-013 and project authority paths.
- **ATDD-first**: PASS by design — #3283 receives a red concurrency reproduction before harness repair; validation/ledger behavior receives tests before tooling implementation. Pure deletions require pre-deletion causal or non-causal evidence instead of replacement tests by default.
- **Regression vigilance**: PASS — accepted P0 reproductions follow the current red-main ADR: exactly one live blocking red per accepted P0, explicit known-red accounting, and red-to-green proof on the same entry point after repair.
- **Pre-existing reds**: PASS — initial harness cascade is filed as #3283. Any later base red blocks classification until issue evidence exists.
- **Cross-platform**: PASS — platform-specific tests cannot be removed on single-platform evidence.
- **Tracker ownership**: REQUIRED before implementation — assign #1931 and #3283 to the HiC and comment with this mission.
- **Quality gates**: contract and architectural suites pass unconditionally; E2E uses only the canonical environmental exception path.
- **PR workflow**: PASS — after analyze, push the planning branch and open a draft PR targeting `main` before WP claims so Linux/Windows PR jobs are reachable; mission integrations continue targeting `pr/assertive-test-suite-sanitation`; only the operator merges protected `main`.

Re-check after design: PASS. No charter exception or complexity violation is required.

## Resolved Planning Decisions

| ID | Decision | Resolution |
|----|----------|------------|
| D1 | Evidence granularity | One row per source function, coherent parameter family, or mechanically proven cluster; expand to node level on any path/oracle/outcome/route/cost/disposition divergence. |
| D2 | Retention proof | A `KEEP` row requires a plausible current-authority-violating fault that reaches Act and fails the intended oracle, or an incompatible consumed contract/known-bad live-entry proof. Scanner self-tests do not count. |
| D3 | Bootstrap comparison | Preserve raw #3283 failure; implement the lease/temp-build/validate/atomic-publish state machine in `research.md`; replay the exact patch artifact in disposable base and HEAD worktrees. |
| D4 | Timing universe | Freeze exact commands, path/marker route map, worker count, cache policy, and runner class before deletion; report sum compute and critical path separately. |
| D5 | Test inventory | Discover test-like source independently of pytest collection, then reconcile collected, ignored, deselected, errored, quarantined, and zero-node files. |
| D6 | Product scope | Only #3283/#2645 test-harness reliability/performance and caller-proven test-only dead symbols may change. Other product defects require separately authorized prerequisite/follow-up work; each accepted open P0 retains exactly one blocking live reproduction under the red-main ADR. |
| D7 | Mutation scope | Focus mutation/fault probes on changed clusters and claimed source targets; no global mutation percentage theater. Surviving unique non-equivalent kills are mandatory. |
| D8 | Delivery slicing | Foundation, inert states, three duplicate-domain WPs, six authority-coherent structural WPs, CI/bootstrap, and aggregate evidence use non-overlapping exact file ownership. Central shard-map integration has one downstream owner. |

## Project Structure

### Documentation and evidence

```text
kitty-specs/assertive-test-suite-sanitation-01KZME3P/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── disposition-ledger.md
│   ├── evidence-gates.md
│   └── ci-routing.md
├── tracer-approach.md
├── tracer-design-decisions.md
├── tracer-tooling-friction.md
└── tasks.md

docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/
├── audit.py                 # mission-scoped census/validator, not installed
├── dispositions/            # WP-owned non-overlapping deep-ledger shards
├── dispositions.yaml        # generated canonical aggregate, never hand-edited by WPs
├── raw/                     # command outputs/checksums, not hand-maintained prose
└── final-report.md          # generated from ledger + raw artifacts
```

### Source and test surfaces

```text
src/specify_cli/                 # only caller-proven dead test surfaces, if any
tests/
├── conftest.py                  # #3283 shared test-venv bootstrap + #2645 collection hook
├── sync/ readiness/ regression/ retrospective/  # inert/red/quarantine adjudication
├── runtime/ kernel/ git_ops/ test_dashboard/     # duplicate/shim adjudication
├── architectural/ release/ docs/ lanes/          # scaffold/shape/prose adjudication
└── contract/                    # hard gate; deletions only with consumed-contract proof
.github/workflows/               # explicit narrow routes + Windows platform proof
```

**Structure Decision**: keep one Python package. Census/validation logic is a mission-local evidence script, not installed production tooling and not a new permanent pytest subtree. The canonical ledger and raw artifacts generate the report; no duplicate hand-maintained timing narrative is introduced.

## Implementation Concern Map

### IC-01 — Reproducible inventory and ledger foundation

- **Purpose**: create a lightweight global machine census, reconcile source discovery with collection, and validate deep rows only for deletions, exceptions, fixes, and affected survivors.
- **Relevant requirements**: FR-001, FR-002, FR-014; NFR-001, NFR-002, NFR-009
- **Affected surfaces**: report-bundle `audit.py`, global census/raw artifacts, contracts; adjudication WPs own separate `dispositions/WP##.yaml` shards and only closure generates the aggregate
- **Sequencing/depends-on**: none
- **Risks**: a node-only narrative creates bureaucracy; a source-only census misses divergence. Machine census is global; deep proof expands only affected families.

### IC-02 — Base attribution and bootstrap reliability

- **Purpose**: reproduce and repair #3283, make base/HEAD comparison valid, and eliminate #2645's repeated whole-tree wall-clock scan without weakening its oracle.
- **Relevant requirements**: FR-010, FR-013, FR-015; NFR-004, NFR-005, NFR-006, NFR-008
- **Affected surfaces**: `tests/conftest.py`, wall-clock assertion support/tests, focused spawned-process bootstrap tests, Windows route, baseline evidence
- **Sequencing/depends-on**: IC-01 for evidence shape; repair may proceed in parallel after the schema is fixed
- **Risks**: a larger-than-minimal harness patch invalidates base replay; thread/fake races miss the inter-process defect; a stale scan cache could silently bypass enforcement.

### IC-03 — Inert, skipped, quarantined, and regression states

- **Purpose**: remove permanent skips/placeholders, correct invalid quarantine, and ensure each accepted P0 has exactly one live blocking red under the red-main ADR without self-skip or duplicate reds.
- **Relevant requirements**: FR-004, FR-009, FR-010, FR-011
- **Affected surfaces**: `tests/sync/`, `tests/readiness/`, `tests/regression/`, `tests/retrospective/`
- **Sequencing/depends-on**: IC-01; base attribution from IC-02 where an outcome claim is required
- **Risks**: deleting the only current defect reproduction; current authority requires exactly one accepted-P0 reproduction to remain live and blocking.

### IC-04 — Duplicate and compatibility-shim consolidation

- **Purpose**: delete exact/semantic duplicates while keeping every unique live boundary, platform case, or compatibility behavior.
- **Relevant requirements**: FR-003, FR-005, FR-008; NFR-007, NFR-010
- **Affected surfaces**: every file named by WP01's strict/normalized manifests split into core, Specify CLI/dashboard, and sync/status/upgrade WPs; exact task ownership remains mandatory
- **Sequencing/depends-on**: IC-01
- **Risks**: similar syntax can encode distinct public import paths; compatibility matrix and live callers decide.

### IC-05 — Structural, prose, and spent-scaffold retirement

- **Purpose**: remove tests that pin names, tokens, counts, exact prose, deleted branches, historical reports, or test-only symbols without a current invariant.
- **Relevant requirements**: FR-006, FR-007, FR-016
- **Affected surfaces**: all 234 repository-source scanner files split into six authority-coherent families (historical/migration, CI/gate, boundary/safety, doctrine/resolver, runtime/coordination, packaging/CLI), named release/scaffold files, and narrowly proven dead `src/` symbols; route/duplicate/inert exceptions retain exact alternate owners
- **Sequencing/depends-on**: IC-01; cohort handoffs converge only in IC-06's single central shard-map owner
- **Risks**: a negative invariant may be embedded beside positive-shape cruft; split and preserve it only after plausible fault proof.

### IC-06 — Proportional CI routing

- **Purpose**: stop whole-tree collection for stable narrow regression/quarantine classes and keep route ownership explicit.
- **Relevant requirements**: FR-012, FR-015; NFR-005, NFR-006
- **Affected surfaces**: `.github/workflows/ci-quality.yml`, central `tests/_arch_shard_map.py`, and four exact route/policy contract tests owned only by this concern (`test_ci_quality_path_filters.py`, `test_marker_job_completeness.py`, `test_quarantine_marker.py`, `test_suite_jobs_gate_blocking.py`)
- **Sequencing/depends-on**: IC-02 establishes reliable startup; IC-03/IC-04/all three IC-05 cohorts and baseline-red adjudication establish final paths before shard-map/route integration
- **Risks**: renamed/deleted routes can manufacture savings or strand tests. Frozen base route mapping is mandatory.

### IC-07 — Aggregate proof and closure

- **Purpose**: generate the final report from canonical ledger/raw artifacts, verify issue matrix and causal preservation, and execute route/platform/hard gates.
- **Relevant requirements**: all, especially FR-014/FR-015 and SC-001..SC-006
- **Affected surfaces**: mission evidence, testing docs, issue matrix
- **Sequencing/depends-on**: IC-01..IC-06
- **Risks**: aggregate passes can hide per-cluster proof gaps; validator rejects incomplete rows before hard gates.

## Complexity Tracking

No charter violation. Mission size is controlled through coherent, non-overlapping work packages and independent review rather than a deletion quota.

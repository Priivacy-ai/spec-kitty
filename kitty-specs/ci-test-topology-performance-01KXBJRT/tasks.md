# Tasks: CI Test-Topology Performance

**Mission**: `ci-test-topology-performance-01KXBJRT` | **Branch**: `feat/ci-test-topology-performance` → PR to `main`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Data model**: [data-model.md](./data-model.md) · **Contracts**: [contracts/guard-contracts.md](./contracts/guard-contracts.md)

## Decomposition note (ownership-clean)

The spec's conceptual WP-A…K are re-grouped into **9 executable WPs with disjoint `owned_files`**, because nearly all per-job edits target one file (`.github/workflows/ci-quality.yml`). That file is owned by **WP06 alone**; every other surface (each registry/guard file, `ui-e2e.yml`, `sonar-project.properties`, docs) is owned by exactly one WP. This keeps parallel lanes collision-free while WP06 serializes the YAML edits as subtasks.

**Ownership qualifier (rationale-backed leeway, not overlap):** WP06 makes small *post-measurement data edits* into files it does not own — the durations-driven shard-leg rebalance lands in WP01's `tests/_next_shard_map.py`/`tests/_arch_shard_map.py` (T017), and the narrowed `slow-tests` selection model may touch WP02's `_gate_coverage.py` (T015). Because WP06 now depends on WP01/WP02 (see graph), these are *sequential* edits to already-merged files with a one-line rationale — never a concurrent-lane collision. The disjoint-`owned_files` guarantee holds for scheduling; the "every surface owned by exactly one WP" claim is qualified for these shared *data* surfaces.

| Task WP | Concern | Spec WP-letters / FR | Owns |
|---------|---------|----------------------|------|
| WP01 | Shard substrate → N-group registry | WP-B / FR-002 | `tests/_arch_shard_map.py`, `tests/_next_shard_map.py`, `tests/conftest.py`, arch+next completeness guards |
| WP02 | Coverage-preservation authority | (IC-02) / FR-007 | `tests/architectural/_gate_coverage.py`, `test_gate_coverage.py`, `baselines/*nodeids*` |
| WP03 | Real-port family registry + serial guard | WP-E(guard) / FR-004, C-002 | `tests/_real_port_suites.py`, `test_serial_port_preservation.py` |
| WP04 | Workflow-dist lint + marker-baseline guards | (IC-05/C-005/C-007) | `test_workflow_dist_lint.py`, `test_marker_baseline.py`, `tests/architectural/marker_baseline.txt` |
| WP05 | fast-tests-cli file split | WP-F / FR-005 | the split `test_charter_activate_commands*.py` files |
| WP06 | CI workflow topology edits | WP-A/C/D/E(job)/G/H/I / FR-001,003,004,006,010,011 | `.github/workflows/ci-quality.yml`, `test_job_count_ceiling.py` |
| WP07 | Sonar coverage-denominator exclusions | WP-J / FR-012 | `sonar-project.properties` |
| WP08 | UI-e2e coverage feed | WP-K / FR-013 | `.github/workflows/ui-e2e.yml` |
| WP09 | Timings artifact + docs + cross-cutting audit | WP-G(audit) / FR-008, FR-009 | `docs/guides/testing-parallel.md`, `docs/plans/testing/test-suite-acceleration-plan.md`, timings artifact |

## Dependency graph

```
WP01 ─> WP02 ─┐
WP03 ─> WP04 ─┤
              ├─> WP06 ──> WP09        (WP06 depends on WP01, WP02, WP03, WP04)
WP05 (root)   WP07 (root)   WP08 (root)
```
Roots (parallel-startable, group 0): **WP01, WP03, WP05, WP07, WP08**. Group 1: WP02, WP04. Group 2: WP06. Group 3: WP09. WP05/WP07/WP08 are fully independent of the topology chain. **WP06 is gated on WP02 + WP04 (not only WP01/WP03)** so the coverage/marker baselines are frozen and the guards exist *before* WP06 changes any job selection (freeze-before-change; enforces FR-007/GC-2b).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Refactor `_arch_shard_map.py` into an N-group registry (group→roots, shard_count, marker_prefix, assignment); arch assignment byte-stable | WP01 | |
| T002 | Update `conftest.py` shard hook to iterate registered groups | WP01 | |
| T003 | Parametrize `test_arch_shard_marker_completeness.py` over the registry (arch green) | WP01 | |
| T004 | Add `_next_shard_map.py` — 3-leg `next` registration (placeholder balance, rebalanced from WP06 durations) | WP01 | |
| T005 | Add `test_next_shard_marker_completeness.py` | WP01 | [P] |
| T006 | Extend `_gate_coverage.py`: register `next` tier in `same_tier_shard_counts` + cross-job disjointness check | WP02 | |
| T007 | Extend `test_gate_coverage.py`: `_REQUIRED_*_SHARDS` += `next_shard_*`; required-selection-structures for next legs | WP02 | |
| T008 | Freeze committed baseline node-id manifests + baseline-diff guard (GC-2b) for re-scoped jobs | WP02 | |
| T009 | Add `_real_port_suites.py` (fixed-range daemon family list) | WP03 | |
| T010 | Generalize `test_serial_port_preservation.py` to consume the registry (whole family) | WP03 | |
| T011 | Add fault-injection negative: a fixed-range suite under `-n auto` is rejected | WP03 | [P] |
| T012 | Add `test_workflow_dist_lint.py` (GC-4: no bare `load`; `-n auto`⇒`loadfile`; fixed-range never `-n auto`; `fail-fast:false`) | WP04 | |
| T013 | Add `test_marker_baseline.py` + commit `marker_baseline.txt` (GC-5: `@slow/@stress/@quarantine` set doesn't grow) | WP04 | |
| T014 | integration-tests-next: add `-n auto --dist loadfile -p no:cacheprovider --durations=25`, then 3-leg `next_shard_N` matrix (`fail-fast:false`) | WP06 | |
| T015 | slow-tests: path-narrow selection (preserve `--ignore` set) + `-n auto --dist loadfile` | WP06 | |
| T016 | orphan-sweep: extract the `-n0` step into its own concurrent job; exclude it from the sync pool | WP06 | |
| T017 | fast-tests-core-misc: rebalance the imbalanced matrix (split the `specify-cli-rest` leg) | WP06 | |
| T018 | fast-tests-charter: split the two sequential `-n auto` steps into concurrent jobs | WP06 | |
| T019 | Sweep `-n auto --dist loadfile -p no:cacheprovider` across the serial non-real-port `integration-tests-*` single-dir jobs | WP06 | |
| T020 | Roster: enrol new jobs in `quality-gate.needs`/`slow-tests.needs`; bump `test_job_count_ceiling.py` | WP06 | |
| T021 | Split `test_charter_activate_commands.py` into balanced sibling files; re-verify collection-equivalence (ratchet) | WP05 | |
| T022 | Add `sonar.coverage.exclusions` (migration/**, static/**, __main__.py, next/**) with rationale comment | WP07 | [P] |
| T023 | UI-e2e Python coverage: `pytest tests/ui/ --cov=…` merged into the report | WP08 | |
| T024 | UI-e2e JS coverage: investigate Playwright/istanbul → lcov → `sonar.javascript.lcov.reportPaths`; else document deferral + rely on static exclusion | WP08 | |
| T025 | Record measured per-leg durations as a committed timings artifact (`_TIMINGS_BASELINE` shape, run-id provenance) | WP09 | |
| T026 | Cross-cutting audit: verify the executed-test union is unchanged across all re-topologized jobs (GC-2b) | WP09 | |
| T027 | Update `docs/guides/testing-parallel.md` + `docs/plans/testing/test-suite-acceleration-plan.md` to the shipped topology | WP09 | [P] |

---

## Work Packages

### WP01 — Shard substrate → N-group registry
**Goal**: Generalize the arch-pole shard mechanism to a registry so `arch` and `next` are data rows (FR-002; satisfies C-003/D-044). **Independent test**: arch completeness guard green + a `next` registration collectable. **Deps**: none. **Prompt**: [tasks/WP01-shard-registry.md](./tasks/WP01-shard-registry.md) (~250 lines).
- [x] T001 Refactor `_arch_shard_map.py` into an N-group registry (WP01)
- [x] T002 Update `conftest.py` shard hook to iterate groups (WP01)
- [x] T003 Parametrize `test_arch_shard_marker_completeness.py` (WP01)
- [x] T004 Add `_next_shard_map.py` 3-leg registration (WP01)
- [x] T005 Add `test_next_shard_marker_completeness.py` (WP01)

### WP02 — Coverage-preservation authority
**Goal**: Enforce 0-dropped/0-double-run against a committed baseline via `_gate_coverage` (FR-007, GC-2/GC-2b). **Independent test**: baseline-diff guard fails on an injected drop. **Deps**: WP01. **Prompt**: [tasks/WP02-coverage-preservation.md](./tasks/WP02-coverage-preservation.md) (~250 lines).
- [x] T006 Extend `_gate_coverage.py` (next tier + cross-job disjointness) (WP02)
- [x] T007 Extend `test_gate_coverage.py` (required next legs) (WP02)
- [x] T008 Freeze baseline node-id manifests + GC-2b diff guard (WP02)

### WP03 — Real-port family registry + serial guard
**Goal**: Keep the whole fixed-range daemon family serial `-n0` (FR-004/C-002, GC-3). **Independent test**: guard rejects a family file placed under `-n auto`. **Deps**: none. **Prompt**: [tasks/WP03-real-port-registry.md](./tasks/WP03-real-port-registry.md) (~200 lines).
- [x] T009 Add `_real_port_suites.py` (WP03)
- [x] T010 Generalize `test_serial_port_preservation.py` (WP03)
- [x] T011 Fault-injection negative case (WP03)

### WP04 — Workflow-dist lint + marker-baseline guards
**Goal**: Formalize C-001/C-002/C-006/C-007 (GC-4) and C-005 (GC-5) as committed guards. **Independent test**: lint guard fails on an injected bare `--dist load`. **Deps**: WP03. **Prompt**: [tasks/WP04-workflow-guards.md](./tasks/WP04-workflow-guards.md) (~220 lines).
- [x] T012 Add `test_workflow_dist_lint.py` (WP04)
- [x] T013 Add `test_marker_baseline.py` + baseline (WP04)

### WP05 — fast-tests-cli file split
**Goal**: Break the `--dist loadfile` single-worker tail by splitting `test_charter_activate_commands.py` (FR-005). **Independent test**: sibling files collect the same tests; ratchet re-verified. **Deps**: none. **Prompt**: [tasks/WP05-cli-file-split.md](./tasks/WP05-cli-file-split.md) (~180 lines).
- [x] T021 Split into balanced sibling files + ratchet re-verify (WP05)

### WP06 — CI workflow topology edits (`ci-quality.yml`)
**Goal**: Apply every per-job topology change + roster (FR-001/003/004-job/006/010/011). **Independent test**: each changed job green (budgets **recorded, not gated** per the flakiness policy); `_gate_coverage` + WP02/WP04 guards green against the edited file. **Deps**: WP01 (registry), WP02 (coverage baseline+guard frozen first), WP03 (real-port guard), WP04 (dist-lint/marker guards). **Prompt**: [tasks/WP06-ci-workflow-topology.md](./tasks/WP06-ci-workflow-topology.md) (~600 lines, 7 subtasks — upper bound, single-file YAML).
- [x] T014 integration-tests-next flags + `next` matrix (WP06)
- [x] T015 slow-tests narrow + parallel (WP06)
- [x] T016 orphan-sweep → own concurrent job (WP06)
- [x] T017 fast-tests-core-misc rebalance (WP06)
- [x] T018 fast-tests-charter step split (WP06)
- [x] T019 serial integration-tests-* sweep (WP06)
- [x] T020 roster + ceiling (WP06)

### WP07 — Sonar coverage-denominator exclusions
**Goal**: Remove glue/non-Python from the coverage denominator (FR-012, GC-6). **Independent test**: exclusion globs match only the intended glue. **Deps**: none. **Prompt**: [tasks/WP07-sonar-coverage-exclusions.md](./tasks/WP07-sonar-coverage-exclusions.md) (~120 lines).
- [x] T022 Add `sonar.coverage.exclusions` with rationale (WP07)

### WP08 — UI-e2e coverage feed
**Goal**: Feed Playwright/UI-e2e coverage into Sonar (FR-013). **Independent test**: `coverage.xml` includes dashboard server-side lines exercised by `tests/ui/`. **Deps**: none. **Prompt**: [tasks/WP08-uie2e-coverage-feed.md](./tasks/WP08-uie2e-coverage-feed.md) (~180 lines).
- [x] T023 UI-e2e Python coverage merged into the report (WP08)
- [x] T024 JS coverage → lcov (or documented deferral) (WP08)

### WP09 — Timings artifact + docs + cross-cutting audit
**Goal**: Record measured budgets, audit coverage-union across all jobs, update docs (FR-008/009). **Independent test**: timings artifact present with run-id; docs match shipped topology. **Deps**: WP06. **Prompt**: [tasks/WP09-timings-docs-audit.md](./tasks/WP09-timings-docs-audit.md) (~200 lines).
- [ ] T025 Committed timings artifact (WP09)
- [ ] T026 Cross-cutting coverage-union audit (WP09)
- [ ] T027 Update testing docs (WP09)

## MVP scope
**WP06** delivers the headline win (integration-tests-next 69.2→~7 min), but its safety net must land first. Correct order: **WP01 → WP03 → {WP02, WP04} → WP06 → WP09** — WP02/WP04 freeze the coverage + marker baselines and land the guards *before* WP06 changes any selection (freeze-before-change). The true critical path to the headline win is **4 hops** (`max(WP01,WP03) → {WP02,WP04} → WP06`), not 2. WP05/WP07/WP08 are independent value-adds runnable in parallel from the start.

---
work_package_id: WP06
title: CI workflow topology edits
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-006
- FR-010
- FR-011
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Topology
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1588895"
shell_pid_created_at: "1783893446.59"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/ci-quality.yml
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
- tests/architectural/test_job_count_ceiling.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – CI workflow topology edits

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

Apply every per-job CI topology edit that delivers this mission's headline win — `.github/workflows/ci-quality.yml` is the single-file authoritative surface for **all** of FR-001, FR-003, FR-004 (job half), FR-006, FR-010, FR-011, plus the roster/ceiling bookkeeping those edits require. Because nearly every concern in this mission touches the same file, this WP owns it alone and serializes the seven job-block edits as ordered subtasks (T014–T020) rather than splitting them across parallel WPs that would collide on the same lines.

Done when:
- `integration-tests-next` runs parallel + durations-instrumented, then as a 3-leg `next_shard_N` matrix (target: 69.2 min → ≤7 min per NFR-001, contingent on the FR-001 durations run).
- `slow-tests` is path-narrowed and parallelized (target: 10.7 → ≤4 min per NFR-002), with the existing `--ignore=tests/e2e --ignore=tests/cross_cutting` set preserved verbatim.
- The `test_orphan_sweep.py` real-port step is promoted out of `fast-tests-sync` into its own concurrent job (target: ≥~130s off `fast-tests-sync`'s critical path per NFR-003), with zero double-run against the parallel pool.
- `fast-tests-core-misc`'s `specify-cli-rest` shard (12.2 min) is rebalanced against `core-misc` (4.7 min) via the WP01 N-group registry (target: ≤7 min per NFR-007).
- `fast-tests-charter`'s two sequential `-n auto` steps become concurrent jobs (target: 12.0 → ≤7 min per NFR-008).
- Every serial non-real-port `integration-tests-*` single-dir job is parallelized (`-n auto --dist loadfile -p no:cacheprovider`); the exact in-scope set is enumerated below, not left to "e.g." (FR-006's precise-selection requirement).
- Every new/changed job id is enrolled in `quality-gate.needs` (and `slow-tests.needs` where applicable); `test_job_count_ceiling.py`'s `CEILING` is bumped only if the post-edit count genuinely requires it.
- Every new/changed `strategy.matrix` block carries `fail-fast: false` (C-006); no run-script anywhere uses bare `--dist load` (C-001).
- WP04's `test_workflow_dist_lint.py` and WP02's `_gate_coverage`-backed guards (`test_gate_coverage.py`, `test_required_selection_structures_present`, the GC-2b baseline diff) are GREEN against the edited file — this WP is the producer that those guards, landed by earlier WPs, now validate.

## Context & Constraints

- Read `kitty-specs/ci-test-topology-performance-01KXBJRT/spec.md` FR-001, FR-003, FR-004, FR-006, FR-010, FR-011, and constraints C-001, C-002, C-003, C-006, C-007 — this WP is the concrete realization of all of them at once, in one file.
- Read `kitty-specs/ci-test-topology-performance-01KXBJRT/plan.md` IC-04 (per-job parallelization/sharding/budgets) and IC-05 (shared CI-YAML roster seam) — IC-05 explicitly identifies the `needs:` roster as "the guaranteed merge-conflict point — serialize or single-own it," which is why this WP, not a parallel split, owns the roster edits.
- **Dependencies**: WP01 (`tests/_next_shard_map.py`, the N-group registry) must land first — T014's `next_shard_N` matrix and T017's `fast-tests-core-misc` rebalance are both **data edits through that registry**, not new mechanisms (C-003/D-044 unification — do not hand-roll a second ad-hoc matrix definition). WP03 (`tests/_real_port_suites.py`, the generalized `test_serial_port_preservation.py`) must land first — T016's orphan-sweep extraction must keep the family's serial guarantee intact and provably so.
- Read `kitty-specs/ci-test-topology-performance-01KXBJRT/contracts/guard-contracts.md` GC-2 (coverage preservation), GC-3 (serial real-port isolation), GC-4 (workflow-dist lint) — every edit in this WP must keep those three guards green, and GC-2b's baseline-diff requires this WP to either match WP02's committed pre-change node-id baseline or coordinate a deliberate, documented baseline regeneration with WP02's owner.
- The full evidence run this mission is grounded in is run **29196440986** (`integration-tests-next` 69.2 min serial; `fast-tests-core-misc` 12.2 min imbalanced; `fast-tests-charter` 12.0 min; `slow-tests` 10.7 min) — see `spec.md`'s Evidence table.
- **Every sharded/parallelized matrix this WP touches or adds MUST set `strategy.fail-fast: false` (C-006)** — a failing leg must never cancel siblings and silently drop their coverage. Verify this explicitly for every edit below, not just the new ones.
- **No bare `--dist load` anywhere (C-001)** — always pair `-n auto` with `--dist loadfile`.
- Budgets (NFR-001/002/007/008) are **measured-and-recorded, not hard gates** — do not add a CI step that fails the build if wall-clock exceeds budget; record the real numbers for WP09's timings artifact instead.

## Branch Strategy

- **Strategy**: Coordination-topology mission — this WP's changes land on a lane/feature branch and merge back through the mission's coordination branch (`kitty/mission-ci-test-topology-performance-01KXBJRT`) into the mission target branch. Confirm the exact lane assignment via `lanes.json` (materialized by `spec-kitty agent mission tasks-finalize`) at implement time — do not assume a lane id here. Because this WP depends on WP01 and WP03, do not start editing `ci-quality.yml` until those two WPs' registries are merged into this WP's base.
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### T014 – `integration-tests-next`: flags, then 3-leg `next_shard_N` matrix (FR-001, FR-002-consumer)

- **Purpose**: This is the mission's headline offender — 69.2 min fully serial. FR-001 requires parallelizing + instrumenting it first (to get real per-file duration data), then FR-002 requires converting it to a registry-driven shard matrix (not a bespoke one-off).
- **Steps**:
  1. Locate the job at `.github/workflows/ci-quality.yml` ~L2319 (`integration-tests-next`, currently `needs: [changes, fast-tests-next]`, running `pytest tests/next/ tests/specify_cli/next/ tests/runtime/ -m 'not windows_ci and (git_repo or integration)' -q --tb=short --cov=src/runtime/next ...` with no `-n`/`--dist` at all — fully serial).
  2. **First**, add `-n auto --dist loadfile -p no:cacheprovider --durations=25` to the existing single-job command (do not yet convert to a matrix) and land/measure this alone if the mission's sequencing calls for an interim durations run (per NFR-001's "contingent on the FR-001 durations run confirming the slowest `loadfile` file-chain < budget" — if a real CI run isn't available before the matrix conversion, proceed directly to the matrix using WP01's `_next_shard_map.py` initial placeholder balance and note in the Activity Log that leg balance is provisional pending WP09's real measurement).
  3. Convert the job to a `strategy: {matrix: {fail-fast: false, include: [...]}}` block with 3 legs, each selecting `-m "next_shard_N and not windows_ci and (git_repo or integration)"` (or the equivalent path+marker selection WP01's registry produces — consume `tests/_next_shard_map.py`'s `shard_for()`/marker-prefix output directly, do not hand-write a parallel path split).
  4. Preserve `--cov=src/runtime/next` and the coverage-report upload per leg (`coverage-integration-next-${{ matrix.shard }}.xml`, matching the existing `${{ matrix.shard }}`-suffix convention already used by `fast-tests-core-misc`/`integration-tests-core-misc`).
  5. Update `needs:` for this job unchanged (`[changes, fast-tests-next]`) — the matrix conversion does not change its upstream dependency, only its own internal sharding.
  6. Confirm `strategy.fail-fast: false` is present (C-006) — a leg failure must not cancel its siblings.
- **Files**: `.github/workflows/ci-quality.yml` (`integration-tests-next` job block).
- **Parallel?**: Do first — WP09's timings artifact and this WP's own T020 roster count both depend on knowing whether this becomes 1 job-id or stays 1 job-id (matrix legs share one job id in `needs:`, so no roster change is required here beyond confirming the existing entry still applies).
- **Notes**: A GitHub Actions matrix job shares one job id across all legs — converting to a 3-leg matrix does **not** add 2 new entries to `quality-gate.needs`; the existing single `integration-tests-next` entry continues to gate on all legs succeeding (`needs.integration-tests-next.result`). Confirm this in T020 rather than assuming a `needs:` change is required here.

### T015 – `slow-tests`: path-narrow + parallelize, preserving `--ignore` (FR-003)

- **Purpose**: `slow-tests` (10.7 min) currently collects the **entire tree** (`pytest -v -m "slow and not windows_ci" --ignore=tests/e2e --ignore=tests/cross_cutting ...`, no path positional) fully serially. FR-003 requires narrowing to just the directories that actually hold `@slow`-marked tests, while guaranteeing the executed set is unchanged.
- **Steps**:
  1. Locate the job at ~L2498 (`slow-tests`, `needs:` a long list of `fast-tests-*` jobs, `timeout-minutes: 30`).
  2. Enumerate the actual directories containing `@slow`-marked tests: `git grep -rl "@pytest.mark.slow" tests/ | xargs -n1 dirname | sort -u`. Compute the **real selection** the current command produces (`tests/ --ignore=tests/e2e --ignore=tests/cross_cutting -m "slow and not windows_ci"`, collect-only) and confirm the narrowed path list collects the identical set.
  3. Replace the bare `tests/` positional with the enumerated directory list (keep `--ignore=tests/e2e --ignore=tests/cross_cutting` **verbatim** — those two ignores must still apply against the narrowed path set exactly as they did against the full tree, so the executed selection is provably unchanged; if the narrowed path list does not include `tests/e2e`/`tests/cross_cutting` in the first place, keep the ignores anyway as defensive no-ops rather than silently dropping them — a future re-widening of the path list must not reintroduce an unguarded selection).
  4. Add `-n auto --dist loadfile` to the existing pytest invocation (currently has neither flag — this is the parallelization half of FR-003).
  5. Preserve `--durations=50`, the `--cov=src/specify_cli --cov=src/charter --cov=src/doctrine` flags, the `--cov-report`/`--junitxml` outputs, and the `|| test $? -eq 5` empty-selection tolerance exactly as they are today.
  6. This WP's guard obligation: the `_gate_coverage` reachability model (per FR-003's own text: *"Guarded by the `_gate_coverage` reachability model against the job's real `(paths − ignores, -m slow)` selection — not a directory-membership scan"*) must be updated/confirmed against the new narrowed path list — coordinate with WP02's owner if `_gate_coverage.py`'s job-selection model needs a data update for this job's new path set (do not silently diverge from what WP02 already encoded).
- **Files**: `.github/workflows/ci-quality.yml` (`slow-tests` job block).
- **Parallel?**: Independent of T014; can run before or after it, but must land before T020's roster/ceiling pass audits the whole file.
- **Notes**: Do not narrow paths by guessing — derive the directory list from `git grep` against the real `@pytest.mark.slow` usages at implementation time (the set may differ slightly from what's listed in the plan/spec, which describe the mechanism, not a frozen directory list).

### T016 – orphan-sweep: own concurrent job, excluded from the parallel pool (FR-004)

- **Purpose**: `test_orphan_sweep.py` binds the reserved daemon port range 9400–9449 (a `FIXED_RANGE_SUITES` member per WP03's registry) and currently runs as **step 2 of `fast-tests-sync`** (~L1008, `-n0`, serial, *after* the parallel `-n auto` step completes) — it is on that job's critical path even though it never touches the parallel worker pool. FR-004 requires promoting it to its own **separate concurrent job** so it stops blocking `fast-tests-sync`'s own completion.
- **Steps**:
  1. Locate `fast-tests-sync` (~L990–1036): step 1 (`Run fast tests — sync (parallel, orphan-sweep excluded)`, already `--ignore=tests/sync/test_orphan_sweep.py -n auto --dist loadfile`) and step 2 (`Run fast tests — sync orphan-sweep (serial, real ports)`, `pytest tests/sync/test_orphan_sweep.py -m "not windows_ci" -n0 --cov-append ...`).
  2. Extract step 2 into a **new top-level job**, e.g. `fast-tests-sync-orphan-sweep`, with `needs: [changes]` (same trigger condition as `fast-tests-sync` itself — `if: always() && needs.changes.outputs.sync == 'true'`) so it runs **concurrently** with `fast-tests-sync`, not after it.
  3. In the new job: `uv sync --frozen --all-extras`, `mkdir -p out/reports/coverage`, then the exact same `pytest tests/sync/test_orphan_sweep.py -q --tb=short -m "not windows_ci" -n0 --cov=src/specify_cli/sync --cov-report=xml:out/reports/coverage/coverage-fast-sync-orphan-sweep.xml || test $? -eq 5` command (drop `--cov-append` since it's no longer appending into the same job's report — use a standalone `--cov-report`, and confirm the coverage aggregator step later in the workflow already globs `coverage-fast-sync*.xml` or an equivalent pattern that still picks this file up; if it globs an exact filename list, add this new file to it).
  4. Remove step 2 from `fast-tests-sync` entirely — the remaining job keeps only the parallel step 1, becoming faster on its own critical path.
  5. Preserve the existing `--ignore=tests/sync/test_orphan_sweep.py` in `fast-tests-sync`'s step 1 (still correct — the orphan-sweep suite must never enter the parallel pool from either job).
  6. Add `fast-tests-sync-orphan-sweep` as a new entry to `quality-gate.needs` (T020 will do the actual roster edit — flag it here as required).
  7. Confirm zero double-run: `test_orphan_sweep.py` is collected by exactly one of the two jobs (the new dedicated one) — WP04's GC-4 lint and WP02's cross-job disjointness check (GC-2, "the serial `-n0` orphan-sweep job's selection ∩ the parallel pool's selection == ∅") both validate this; run them locally before considering T016 done.
- **Files**: `.github/workflows/ci-quality.yml` (`fast-tests-sync` job block; new `fast-tests-sync-orphan-sweep` job block).
- **Parallel?**: Independent of T014/T015; touches a disjoint region of the file.
- **Notes**: This is FR-004's job-half; WP03 already delivered the registry + guard half. Do not weaken or bypass the serial `-n0` isolation on the new job — the whole point is "still serial, just not blocking a sibling job's critical path."

### T017 – `fast-tests-core-misc`: rebalance the imbalanced matrix (FR-010)

- **Purpose**: `fast-tests-core-misc` is already a 2-shard matrix (~L1421), but `specify-cli-rest` (12.2 min, `paths: tests/specify_cli` minus several `--ignore`d dedicated-shard roots) badly outweighs `core-misc` (4.7 min, the whole-tree residual). FR-010 requires splitting `specify-cli-rest` into additional shards **through the WP01 N-group registry** — a data edit, not a new mechanism.
- **Steps**:
  1. Locate the matrix at ~L1421–1478 (`strategy.matrix.include`: `specify-cli-rest` and `core-misc` entries, each with `paths`/`ignore_args`).
  2. Using WP01's registry (`tests/_arch_shard_map.py`, generalized), register a new shard group (or extend the `core-misc` group's `shard_count`) that subdivides `tests/specify_cli` (minus its already-ignored dedicated roots: `cli`, `missions`, `lanes`, `next`, `status`, `charter_freshness`, `charter_lint`, `charter_preflight`) into 2+ balanced sub-shards, using real duration data (re-run `--durations=50` against the current `specify-cli-rest` selection to find the actual heavy subdirectories before picking a split point).
  3. Update the `matrix.include` list to add the new sub-shard entries (e.g. `specify-cli-rest-a`, `specify-cli-rest-b`), each with its own `paths`/`ignore_args` derived from the registry, replacing the single `specify-cli-rest` entry.
  4. **Preserve the ignore-mirror invariant** already documented in the file's own comment block (~L1385–1408): *"the residual ignores `tests/specify_cli`, the union re-covers exactly the pre-split fast universe... every carved root is ignored here AND owned as a positional by a dedicated shard, together"* — bound by `test_catch_all_ignore_lists_mirror_owned_roots_live`. Splitting `specify-cli-rest` into sub-shards must not change what `core-misc`'s `ignore_args` excludes; only the `specify-cli-rest` side's internal partitioning changes.
  5. Confirm `strategy.fail-fast: false` remains set (it already is, at ~L1428) — do not regress it while editing the `matrix.include` list.
  6. Preserve the `--cov=src/specify_cli --cov=src/glossary` flags and the `${{ matrix.shard }}`-suffixed coverage-report naming for every new sub-shard.
- **Files**: `.github/workflows/ci-quality.yml` (`fast-tests-core-misc` job block); `tests/_arch_shard_map.py` (WP01's registry — data addition only, coordinate with WP01's owner if this WP lands after WP01 is already merged and frozen, in which case this is a follow-on data edit to an already-landed file, not a new mechanism).
- **Parallel?**: Depends on WP01 (registry must exist) — do not attempt to hand-roll a parallel shard mechanism if WP01 hasn't landed yet; block on it.
- **Notes**: A matrix's shard count is a `needs:`-neutral change (matrix legs share one job id) — T020 does not need to add a new roster entry for this rebalance, only confirm `_REQUIRED_*_SHARDS` in `test_gate_coverage.py` (WP02's surface) is updated to match the new leg names — flag this coordination point to WP02's owner rather than silently editing `test_gate_coverage.py` from this WP (it is not in this WP's `owned_files`).

### T018 – `fast-tests-charter`: split sequential steps into concurrent jobs (FR-011)

- **Purpose**: `fast-tests-charter` (12.0 min) already uses `-n auto --dist loadfile` (~L1930) inside its single step, so the imbalance is not a missing-parallelism problem — the plan/spec's own text notes it "runs sequential `-n auto` steps (charter + agent) that sum on the job wall-clock." Concretely, `fast-tests-charter` (~L1910) and the *downstream* `fast-tests-agent` job (~L1953, which `needs: [changes, fast-tests-charter]`) currently execute back-to-back because `fast-tests-agent` is gated on `fast-tests-charter`'s completion — splitting them to run concurrently (removing the unnecessary serialization) is the FR-011 fix, alongside checking whether `fast-tests-charter`'s own single `-n auto --dist loadfile` file-chain has a `loadfile` single-file tail that also needs rebalancing.
- **Steps**:
  1. Read `fast-tests-charter` (~L1910–1944, one step: `pytest tests/charter tests/specify_cli/charter_freshness tests/specify_cli/charter_lint tests/specify_cli/charter_preflight -m "fast and not windows_ci" -n auto --dist loadfile --durations=50 --cov=src/charter --cov=src/specify_cli/charter_runtime --cov-fail-under=55`) and `fast-tests-agent` (~L1953–1990, `needs: [changes, fast-tests-charter]`, its own `pytest tests/agent -m "fast and not windows_ci" ...` — confirm whether it also carries `-n auto --dist loadfile` or is itself serial; read the actual block before editing).
  2. Determine whether `fast-tests-agent`'s `needs: fast-tests-charter` edge is a **true data dependency** (agent tests import/exercise charter-produced fixtures/state) or a **historical serialization artifact**. Read `docs/guides/testing-parallel.md` and any comment above these two jobs for the rationale before removing the edge.
  3. If the dependency is not load-bearing: change `fast-tests-agent`'s `needs:` to `[changes, kernel-tests, fast-tests-doctrine]` (mirroring `fast-tests-charter`'s own upstream needs, so both run concurrently off the same predecessors) — this is the "split the sequential steps into concurrent jobs" fix; the two jobs already exist as separate top-level jobs, the fix is removing the artificial ordering edge between them, not merging or duplicating job bodies.
  4. If `--durations=50` evidence (captured before this edit) shows `fast-tests-charter`'s own single step still has a `loadfile` single-file tail independent of the `fast-tests-agent` ordering, additionally rebalance the heaviest file inside `tests/charter`/`tests/specify_cli/charter_*` the same way WP05 rebalanced the CLI file (split it), preserving `--dist loadfile`.
  5. Preserve `--cov-fail-under=55` on `fast-tests-charter` — do not touch that coverage gate as part of a topology change.
  6. Confirm `quality-gate.needs` (T020) already lists both `fast-tests-charter` and `fast-tests-agent` as separate entries (it does, per the current roster) — removing the `needs:` edge between the two jobs does not change the roster's job-id set, only their scheduling relationship.
- **Files**: `.github/workflows/ci-quality.yml` (`fast-tests-charter`, `fast-tests-agent` job blocks).
- **Parallel?**: Independent of T014–T017; do after confirming with a real `--durations=50` run whether the ordering edge or the file-chain tail (or both) is the actual bottleneck — do not guess.
- **Notes**: "Split the sequential steps into concurrent jobs" in the spec's own FR-011 text describes the *effect* (two things that used to run one-after-another now run side by side); the two "steps" in question are already separate GitHub Actions jobs (`fast-tests-charter`, `fast-tests-agent`), not two `run:` steps inside one job — confirm this reading against the actual file structure before assuming a merge/extraction is needed.

### T019 – sweep serial non-real-port `integration-tests-*` single-dir jobs (FR-006)

- **Purpose**: Parallelize every serial `integration-tests-*` job that (a) selects a single test directory and (b) does not touch the real-port/daemon family, with the precise in-scope set enumerated (no "e.g.").
- **Steps**:
  1. Enumerate every `integration-tests-*` job in the file and classify each as: already-matrix-parallel (skip), contains-real-port-suite (must split real-port piece to serial `-n0` first, then parallelize the rest), or serial-single-dir-non-real-port (in scope for this sweep).
  2. From the current file (confirm at implementation time, re-enumerate if the file has changed since this prompt was written): `integration-tests-doctrine`, `integration-tests-charter`, `integration-tests-merge`, `integration-tests-missions`, `integration-tests-post-merge`, `integration-tests-release`, `integration-tests-status`, `integration-tests-review`, `integration-tests-lanes`, `integration-tests-dashboard`, `integration-tests-upgrade`, `integration-tests-cli`, `integration-tests-agent` are serial single-dir jobs today (each runs one `pytest <single-dir>/ -m 'not windows_ci and (git_repo or integration)' -q --tb=short --cov=... --cov-report=...` with no `-n`/`--dist`). `integration-tests-core-misc` is **already** a parallel matrix (`-n auto --dist loadfile` present, ~L1554) — out of scope, no change needed. `integration-tests-next` is T014's own subject (converts to a shard matrix, not this generic sweep) — do not double-edit it here.
  3. **`integration-tests-sync`** (~L2093) is the one job in this list that touches `tests/sync/` — cross-check against WP03's `FIXED_RANGE_SUITES` registry: if the job's selection (`tests/sync/ -m 'not windows_ci and (git_repo or integration)'`) collects any fixed-range suite, split that suite out to its own serial `-n0` step/job first (mirroring T016's pattern for `fast-tests-sync`), **then** add `-n auto --dist loadfile` to the remaining non-real-port residual. Do not blanket-parallelize `integration-tests-sync` without first confirming the real-port family is excluded — this is the one job in the sweep where getting the order wrong reintroduces the exact hazard WP03/GC-3 exists to prevent.
  4. For every other job in the enumerated list: add `-n auto --dist loadfile -p no:cacheprovider` to its existing single `pytest` invocation; preserve every existing flag (`-m` marker expression, `--cov=`, `--cov-report=`, `--tb=short`) verbatim.
  5. Confirm each edited job's `needs:` is unchanged (parallelizing within a job does not change its upstream dependency).
  6. Confirm `strategy.fail-fast: false` is **not required** for these jobs unless you also convert any of them to a `strategy.matrix` — a bare `-n auto --dist loadfile` single-job edit has no `strategy:` block and is exempt from C-006 (that constraint applies to sharded *matrices*, not to xdist parallelism within one job).
- **Files**: `.github/workflows/ci-quality.yml` (the 13 enumerated job blocks, plus `integration-tests-sync`'s split if applicable).
- **Parallel?**: Independent of T014/T016/T017/T018 (different job blocks); do after re-confirming the enumeration against the file as it stands when this WP is actually implemented (the file may have drifted since this prompt was authored).
- **Notes**: This is the FR-006 "precise selection criterion, no e.g." requirement — the enumerated list above IS the criterion; if the real file has jobs not listed here (or is missing one listed here), that drift itself is a finding to record in the Activity Log, not something to silently paper over.

### T020 – roster enrolment + ceiling bump (IC-05 / cross-cutting)

- **Purpose**: One owner for every `quality-gate.needs`/`slow-tests.needs` edit and the `test_job_count_ceiling.py` ceiling, so the job-adding edits from T014–T019 above don't textually collide with each other or with WP03's own job additions.
- **Steps**:
  1. After T014–T019 land, re-read `quality-gate.needs` (~L3520–3567, currently 47 entries) and `slow-tests.needs` (~L2500–2517).
  2. Add exactly one new entry for **each genuinely new top-level job id** introduced above: `fast-tests-sync-orphan-sweep` (T016). Confirm whether T018 removed a `needs:` *edge between* `fast-tests-charter`/`fast-tests-agent` (no roster change — both already have their own `quality-gate.needs` entries) versus added a new job id (it should not, per T018's notes). Confirm T014's matrix conversion and T017's shard-count rebalance are **both `needs:`-neutral** (matrix legs share one job id) — do not double-add.
  3. If `integration-tests-sync`'s T019 split produced a new dedicated real-port job id, add that entry too.
  4. Sum the final `quality-gate.needs` count. Current baseline is 47; `test_job_count_ceiling.py`'s `CEILING` is pinned at 57 (10 headroom before this WP's edits). Confirm the post-edit count stays ≤ 57. Only bump `CEILING` in `tests/architectural/test_job_count_ceiling.py` if the real post-edit count exceeds it — do not pre-emptively raise it "just in case."
  5. Run `uv run pytest tests/architectural/test_job_count_ceiling.py -v` to confirm both the ceiling-fits assertion and the headroom assertion (`test_ceiling_leaves_headroom_for_composite_design`) are green.
  6. Run WP04's `test_workflow_dist_lint.py` (if landed) and WP02's `_gate_coverage`-backed `test_gate_coverage.py`/`test_required_selection_structures_present` against the fully-edited file — this is the final cross-check that every prior subtask's edits compose correctly.
- **Files**: `.github/workflows/ci-quality.yml` (`quality-gate.needs`, `slow-tests.needs`), `tests/architectural/test_job_count_ceiling.py` (only if the ceiling itself must move).
- **Parallel?**: Must run **last**, after T014–T019 — it is the integration/reconciliation pass over the whole file.
- **Notes**: The roster is deliberately the single serialization point for this entire WP (per IC-05's own risk note: "the enumerated `needs:` list is the guaranteed merge-conflict point — serialize or single-own it") — this is why WP06 is one WP with seven ordered subtasks rather than seven parallel WPs.

## Test Strategy

Tests are the deliverable alongside the workflow edits — every subtask above is validated by a combination of local dry-runs and the guards landed by WP01–WP04.

- Validate the edited YAML parses and every job/matrix structure is well-formed:
  ```bash
  python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-quality.yml'))" && echo OK
  ```
- Run every guard this WP must keep green, after each major subtask (not just at the end):
  ```bash
  uv run pytest tests/architectural/test_workflow_dist_lint.py -v            # GC-4 (WP04)
  uv run pytest tests/architectural/test_serial_port_preservation.py -v      # GC-3 (WP03)
  uv run pytest tests/architectural/test_gate_coverage.py -v                 # GC-2 (WP02)
  uv run pytest tests/architectural/test_job_count_ceiling.py -v            # roster ceiling
  uv run pytest tests/architectural/test_arch_shard_marker_completeness.py tests/architectural/test_next_shard_marker_completeness.py -v   # GC-1 (WP01)
  ```
- Locally reproduce each edited job's new selection to confirm collection-equivalence before trusting a real CI run:
  ```bash
  uv run pytest tests/next/ tests/specify_cli/next/ tests/runtime/ -m "next_shard_1 and not windows_ci and (git_repo or integration)" --collect-only -q
  uv run pytest tests/sync/test_orphan_sweep.py -m "not windows_ci" -n0 --collect-only -q
  uv run pytest tests/specify_cli/ --ignore=tests/specify_cli/cli --ignore=tests/specify_cli/missions --ignore=tests/specify_cli/lanes --ignore=tests/specify_cli/next -m "fast and not windows_ci" --durations=50 -n auto --dist loadfile -q
  ```
- Push to a draft PR / branch and observe at least one **real CI run** per the mission's own measured-not-declared discipline (FR-008/NFR-001..008) — do not mark this WP done on local dry-runs alone; a GitHub Actions runner's core count and I/O characteristics differ from a local dev machine.
- Confirm `ruff check .github/workflows/` is not applicable (YAML, not Python) but `ruff check tests/architectural/test_job_count_ceiling.py` and `mypy` on any touched `.py` files are clean.

## Risks & Mitigations

- **Risk**: This WP's `needs:` roster edits (T020) are the single most collision-prone surface in the whole mission if any other in-flight branch also touches `ci-quality.yml`. **Mitigation**: land T020 last, after a fresh rebase onto the mission's coordination branch, and diff the final `needs:` list against the pre-WP06 baseline line-by-line before committing.
- **Risk**: Removing the `fast-tests-agent` → `fast-tests-charter` `needs:` edge (T018) without confirming it's not a true data dependency could introduce a race (agent tests reading charter-produced state that no longer exists yet). **Mitigation**: read `docs/guides/testing-parallel.md` and any historical comment/commit message explaining why the edge was added before removing it; if genuinely uncertain, keep the edge and rebalance the file-chain tail instead (T018 step 4's fallback).
- **Risk**: `integration-tests-sync`'s T019 sweep is the one place a naive blanket `-n auto` addition would reintroduce the real-port hazard WP03 exists to prevent. **Mitigation**: run WP03's generalized `test_serial_port_preservation.py` against the edited file before considering T019 done for that specific job — treat a red result there as a hard stop, not a warning.
- **Risk**: Budget targets (NFR-001/002/007/008) are wall-clock and runner-core-count sensitive; a local reproduction cannot validate them. **Mitigation**: defer final budget confirmation to WP09's real-CI timings artifact; this WP's own Done criteria are "the topology change is correct and guard-green," not "the number is hit," per the plan's own "measured-and-recorded, not hard gates" framing.
- **Risk**: `fast-tests-core-misc`'s rebalance (T017) could accidentally break the ignore-mirror invariant (`test_catch_all_ignore_lists_mirror_owned_roots_live`) if a newly-carved sub-shard's root isn't added to `core-misc`'s own `ignore_args`. **Mitigation**: run that specific architectural test immediately after T017, before moving to T018.

## Review Guidance

- Confirm every new/changed `strategy.matrix` block sets `fail-fast: false` (C-006) — check T014, T017, and any matrix T019 might introduce for `integration-tests-sync`.
- Confirm no bare `--dist load` was introduced anywhere (C-001) — re-run `test_workflow_dist_lint.py`.
- Confirm the T019 enumeration matches the real file at review time (not just this prompt's snapshot) — the reviewer should independently `grep -n "^  integration-tests-"` the file and cross-check against the claimed 13-job list.
- Confirm `test_orphan_sweep.py` (T016) and any real-port suite in `integration-tests-sync` (T019) are collected by exactly one job each — zero double-run, per GC-2's cross-job disjointness clause.
- Confirm the `quality-gate.needs`/`slow-tests.needs` diff (T020) adds only the genuinely new job ids, and that `test_job_count_ceiling.py`'s `CEILING` was not raised unless the real count required it.
- Confirm WP04's, WP02's, and WP01's guards are all green against the final edited file, and that WP05's `fast-tests-cli` split (a sibling WP, not touched here) still collects cleanly alongside this WP's edits.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-12T17:43:44Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP06 --to <status>` to change WP status.
- 2026-07-12T21:01:45Z – claude:sonnet:implementer-ivan:implementer – shell_pid=1436895 – Assigned agent via action command
- 2026-07-12T21:56:07Z – claude:sonnet:implementer-ivan:implementer – shell_pid=1436895 – Ready: 6 jobs re-topologized + roster; #2590 closed + WP03/WP04 guards de-xfailed & live-green; next shards rebalanced; all arch guards 0-failed (79 passed); YAML valid
- 2026-07-12T21:57:29Z – claude:opus:reviewer-renata:reviewer – shell_pid=1588895 – Started review via action command
- 2026-07-12T22:15:02Z – user – shell_pid=1588895 – Review passed: 6 jobs re-topologized, GC-2b unions == original baselines (baseline regen verified pure path-noise), #2590 closed + guards de-xfailed honestly, YAML/roster valid; guard suite 0 failed

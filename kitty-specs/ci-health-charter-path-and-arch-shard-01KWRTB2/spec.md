# CI Health: Charter-Path Hotfix + Arch-Adversarial Shard

**Mission ID**: 01KWRTB2ZF0DJYPQ09PYRNP013
**Status**: Draft
**Mission type**: software-dev
**Closes**: #2397 (and fixes red-main `fast-tests-docs`)

## Purpose

Restore CI health on two coordinated fronts:

- **Concern A — Red-main hotfix.** `tests/docs/test_current_charter_paths.py::test_current_docs_do_not_publish_memory_charter_path` fails on current `main` because `docs/guides/contributing.md` still publishes the retired legacy path `memory/charter.md`. This reds the `fast-tests-docs` job on **every** open PR. The canonical path today is `.kittify/charter/charter.md`.
- **Concern B — P1 CI optimization (#2397).** After PR #2391 de-serialized the arch-adversarial pole (−51% core-misc critical path), the `arch-adversarial` job remains a single **unsharded** bottleneck at ~14.4 min — now the slowest component in an otherwise parallelized pipeline. Matrix-shard it (same pattern as `fast-tests-core-misc`) to drop below the ~13.6-min sub-target **without weakening any architecture-suite coverage or coverage-ownership invariant**.

These are bundled by operator decision as one CI-health tidy despite spanning docs and CI-topology domains.

## User Scenarios & Testing

### Primary actors

- **Maintainer / PR author** — needs a green, fast `main` pipeline so their PRs are not blocked by unrelated red or throttled by a slow pole.
- **CI pipeline** — the automated system executing `.github/workflows/` jobs on every source change.

### Scenario A — Contributing guide no longer publishes a legacy charter path

1. **Trigger:** the docs guard suite (`fast-tests-docs`) runs on a PR or on `main`.
2. **Today (failing):** `docs/guides/contributing.md` contains `memory/charter.md`; `test_current_docs_do_not_publish_memory_charter_path` collects it as an offender and fails.
3. **Desired outcome:** the guide references the canonical `.kittify/charter/charter.md`; the guard finds zero offenders and passes.
4. **Exception considered:** the same stale path must not survive anywhere else under the guarded roots (`docs/context`, `docs/guides`, `docs/api`, `spec-driven.md`) — the fix is verified by the guard itself, not just the one known line.

### Scenario B — Arch-adversarial runs as always-on parallel shards

1. **Trigger:** a source change lands on a PR; `CI Quality` runs.
2. **Today:** a single `arch-adversarial` job runs the whole architecture-adversarial suite serially (~14.4 min), gating the critical path.
3. **Desired outcome:** the job fans out into N always-on, group-less shards that run concurrently; the slowest shard completes below the ~13.6-min sub-target; the aggregate still executes the full suite exactly once.
4. **Exceptions / invariants that must always hold:**
   - Every shard runs on **100% of source changes** (no differential/path-filtered triggering) — NFR-002.
   - Test-to-job routing remains **marker→job-authority** driven; no test is silently orphaned or double-owned across shards.
   - Coverage ownership (FR-006 of the prior CI missions) is partitioned with **no dropped and no double-counted** tests.
   - The **docs-only trim** introduced by PR #2391 still applies after the split (docs-only changes still skip the arch pole where they did before).

### Acceptance walkthrough

- Run the docs guard: `pytest tests/docs/test_current_charter_paths.py` → passes.
- Inspect the `arch-adversarial` matrix in `.github/workflows/`: shards are `always-on`, group-less, and collectively enumerate the same test set as the pre-split single job.
- The coverage-topology ownership test (`tests/release/test_coverage_topology_ownership.py`) passes with the sharded layout: union of shard ownership == full arch suite, intersection == ∅.
- A CI run shows the arch pole's slowest shard under the sub-target and the pipeline green.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The contributing guide (`docs/guides/contributing.md`) MUST reference the canonical charter path `.kittify/charter/charter.md` and MUST NOT contain the retired substrings `memory/charter.md` or `.kittify/memory/charter.md`. | Draft |
| FR-002 | `test_current_docs_do_not_publish_memory_charter_path` MUST pass (zero offenders across all guarded doc roots), verified by running the guard, not by inspecting the single known line. | Draft |
| FR-003 | The `arch-adversarial` CI job MUST be split into a matrix of N parallel shards (N >= 2) in `.github/workflows/`, following the established `fast-tests-core-misc` sharding pattern. | Draft |
| FR-004 | Shard-to-test assignment MUST be deterministic and driven by the existing marker->job-authority mechanism, so re-runs and local reproduction route each test to exactly one shard. | Draft |
| FR-005 | The union of all shards MUST execute the entire pre-split arch-adversarial test set; no test may be dropped, and no test may run in more than one shard (partition, not overlap). | Draft |
| FR-006 | Coverage ownership for the arch pole MUST be re-partitioned across shards such that `tests/release/test_coverage_topology_ownership.py` (and any coverage-ownership manifest it asserts) passes with the new layout. | Draft |
| FR-007 | The mission MUST update whatever committed topology/timings fixtures the CI-topology tests assert against (e.g. `tests/release/ci_topology_timings_*.json`) so the sharded shape is the asserted-canonical shape. | Draft |
| FR-008 | The mission MUST close issue #2397 and record which acceptance criteria (1-5 in the issue) were re-verified and how. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Arch-adversarial critical-path duration after sharding | Slowest shard completes in **< 13.6 min** (target set by #2397); measured on a representative CI run. | Draft |
| NFR-002 | Architecture-suite coverage completeness | Arch suite runs on **100%** of source-changing PRs; shards are always-on and group-less with **no** differential/path-based triggering that could skip the suite. | Draft |
| NFR-003 | No coverage regression | Line/branch coverage attributed to the arch pole after sharding equals the pre-split total (zero intentionally dropped tests; measurement noise excepted). | Draft |
| NFR-004 | Local reproducibility | Each shard's test subset is reproducible locally via a documented `pytest` invocation (marker/selection), matching what CI runs. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | PR targets **upstream/main** (`Priivacy-ai/spec-kitty`) via a PR branch per charter; no direct push to origin/main or upstream/main. Operator performs the final merge. | Draft |
| C-002 | Do not weaken, suppress, or `# noqa`/`# type: ignore` any guard, marker-authority, or coverage-ownership test to make the pipeline green; fix the underlying config/data instead. | Draft |
| C-003 | Preserve the PR #2391 docs-only trim behavior; the sharding change must not re-introduce the arch pole onto docs-only changes that previously skipped it. | Draft |
| C-004 | The docs hotfix (Concern A) is scoped to correcting the stale charter reference; it must not rewrite unrelated contributing-guide content. | Draft |
| C-005 | Terminology canon holds: use `Mission`, canonical charter path, no legacy `memory/charter.md` reintroduced elsewhere. | Draft |

## Success Criteria

- **SC-001:** The `fast-tests-docs` job passes on this branch and would pass on `main` (the charter-path guard reports zero offenders).
- **SC-002:** On a full CI run, the arch-adversarial pole runs as parallel shards and its slowest shard finishes below the ~13.6-min sub-target.
- **SC-003:** All CI-topology / coverage-ownership guard tests pass with the sharded layout — every arch test is owned by exactly one shard, none dropped, none double-counted.
- **SC-004:** A source-only PR still triggers the full arch suite (100% coverage), and a docs-only PR still skips the arch pole exactly as it did before #2391's trim.
- **SC-005:** Issue #2397's five acceptance criteria are each explicitly re-verified and the verification is recorded in the PR body.

## Key Entities

- **`.github/workflows/` CI Quality definition** — the workflow file(s) defining the `arch-adversarial` job and the existing `fast-tests-core-misc` matrix pattern to mirror.
- **Marker->job authority** — the mechanism (pytest markers + a manifest/map) that assigns each test to exactly one CI job/shard.
- **Coverage-topology fixtures** — committed JSON/tests under `tests/release/` (`test_coverage_topology_ownership.py`, `ci_topology_timings_*.json`) that assert the canonical CI shape and ownership.
- **Charter-path guard** — `tests/docs/test_current_charter_paths.py` enforcing that current docs publish only the canonical `.kittify/charter/charter.md`.

## Assumptions

- The `fast-tests-core-misc` sharding pattern is the intended template and is directly adaptable to the arch pole (confirmed by #2397 wording). If the arch pole's test-selection mechanism differs materially, the plan phase surfaces it.
- Shard count N will be chosen during plan to bring the slowest shard under 13.6 min given the ~14.4-min serial baseline (likely N=2-3); the exact N is a plan-phase decision, not a spec commitment.
- The docs-only trim from #2391 is expressed in the same workflow file(s) and can be preserved by mirroring its condition onto the sharded job.
- No product/runtime code changes are required; the mission touches docs prose, workflow YAML, and CI-topology test fixtures only.

## Out of Scope

- Any further CI optimization beyond the arch-adversarial pole (e.g. other jobs' timings).
- Rewriting or restructuring the contributing guide beyond the single stale-path correction.
- Changing the marker->job-authority mechanism itself (only re-partitioning within it).

---
work_package_id: WP09
title: Matrix reusable module-tests workflow(s)
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP08
requirement_refs:
- FR-001
- FR-006
- FR-008
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T045
- T046
- T047
- T048
- T049
- T050
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/module-tests.yml
create_intent:
- .github/workflows/module-tests.yml
- .github/workflows/ci-modules.yml
- tests/architectural/test_module_tests_matrix.py
execution_mode: code_change
owned_files:
- .github/workflows/module-tests.yml
- .github/workflows/ci-modules.yml
- tests/architectural/test_module_tests_matrix.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (TOPOLOGY T2 matrix half),
`contracts/router-two-authority.md` §"Module shard registry", `contracts/artefact-naming.md`,
and the charter §"ATDD-First" + SO#6.

**Cluster gate:** claim after ALL FOUNDATION (WP01–WP06) + WP08 (registry) are
approved/done.

## Objective

Give the suite a **public CI home** (FR-001) via **full-tree modular** reusable
workflows (FR-006): a `workflow_call` module-tests shard + a caller that **matrixes
over the WP08 registry** (FR-008 de-serialized). Every per-module group contributes to
one full run; each shard consumes the WP04 warmup env once and emits coverage/xunit
artefacts under the naming contract (consumed by WP10). Bounded set of reusable
workflows (≤20/caller), matrix over the registry — not ~40 files.

## Subtask guidance

### T045 — Red-first: `test_module_tests_matrix.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_module_tests_matrix.py`
asserting: the caller's matrix realizes **every** WP08 registry row (no row unshipped,
no shard over a non-registry module), `module-tests.yml` is `on: workflow_call` with
the expected inputs (module, roots, cov_target, tier, shard, mode), and the shard
consumes the warmup env. Run against base: red for the right reason (workflows absent).
**Collection-red lazy-load hygiene:** any import of a not-yet-existing module/helper is
lazy/in-test so the file still *collects* green on base — the red is a failed behavioral
assertion, never a collection/import error.

### T046 — Author `module-tests.yml` (reusable shard)

Create `.github/workflows/module-tests.yml` (`on: workflow_call`): consume the warmup
env (WP04 composite), run `pytest` for the passed module/roots/tier/shard with dotted
`--cov=<module>`, emit `coverage-<tier>-<module>.xml` + xunit under the naming contract
(forward-ref WP10). SHA-pin all actions.

### T047 — Author `ci-modules.yml` (matrix caller)

Create `.github/workflows/ci-modules.yml`: read the WP08 registry and `uses:
./.github/workflows/module-tests.yml` in a **matrix** over the rows, inside the parent
run so coverage aggregates into one run. Keep the reusable-workflow fan-out within the
≤20/caller ceiling (matrix realization).

### T048 — Per-shard artefact emission

Wire each shard's `actions/upload-artifact` (`name: <job>-reports`, `path:
out/reports/`, `if: always()`) and the `coverage-<tier>-<module>.xml` +
`xunit-result-<shard>-<run_id>.xml` paths per `contracts/artefact-naming.md`. Basename
unique per shard (a collision silently drops data). WP10 consumes these.

### T049 — Mode input threading + this workflow's own mode-conditioned fail-fast

Thread the `mode` (`pr`|`full`) input through `module-tests.yml`/`ci-modules.yml` (from
the warmup composite and the caller). **Declare `workflow_dispatch`; honor the `mode`
input** (PR=fail-fast/short-circuit, full=`if: always()`/run-all) in **this workflow's
own** fail-fast/`needs` behavior per FR-018/FR-019 — the mode-conditioned logic for the
module-tests shard/caller lives in these owned files. What stays with WP11 is only the
**cross-cutting** `test_dual_mode_contract` (which verifies this wiring), the
dispatched-run evidence doc, and the skipped≠green (SC-009) required-check assertion —
WP11 does NOT author this workflow's per-shard logic.

### T050 — Shard independence

Assert shards do **not** `needs:` each other (they run concurrently within a tier) and
each consumes the warmup env once (no per-shard re-install — the #3283 kill in
practice). This is the FR-008 de-serialization realized.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP09`.
- Depends on all FOUNDATION + WP08 — claim after approved/done.
- Commit order: **T045 red-first FIRST**, then T046–T050.

## Definition of Done

- T045 red on base (evidence captured), green on final.
- `module-tests.yml` (reusable) + `ci-modules.yml` (matrix caller) realize every
  registry row within the ≤20-reusable-workflow ceiling; all actions SHA-pinned.
- Shards emit coverage/xunit under the naming contract, consume warmup env once, and do
  not `needs:` each other.
- `mode` input threaded, and `module-tests.yml`/`ci-modules.yml` declare
  `workflow_dispatch` and honor the `mode` input (PR fail-fast vs full `if: always()`)
  in their own fail-fast/`needs` behavior (FR-018/FR-019) — verified by WP11's
  `test_dual_mode_contract`.
- Both workflows registered `introduced` in the map (coordinate with WP01's schema —
  the row edit is C-001 lockstep; if the map edit reaches WP01's owned file, hand the
  row addition to the orchestrator or land it in WP01's follow-up rather than editing
  WP01's owned file here).
- **Targeted test surface**: `pytest tests/architectural/test_module_tests_matrix.py tests/release/test_release_ci_ownership.py -q`.

## Risks

- **Governance-map lockstep (C-001)**: `module-tests.yml`/`ci-modules.yml` need
  `introduced` rows in `docs/convergence/interim-ci-producer.md` — owned by WP01. To
  avoid an owned_files overlap, coordinate the row addition with the orchestrator (or
  WP01 pre-registers the mission's net-new workflow names). Do NOT edit WP01's owned
  files from this WP.
- **Coverage basename collision**: dedup is by basename — a duplicate silently drops a
  shard's data. Enforce uniqueness (WP10's contract test backs this).
- **Ceiling breach**: keep the matrix realization; do not fan out to per-module files.
- **New-file arch battery**: new test dir routing / shard-map gates — pre-check locally.

## Reviewer guidance

- Confirm T045 red-on-base for the right reason.
- Confirm the matrix realizes every registry row and stays within the reusable-workflow
  ceiling.
- Confirm artefact naming matches the contract and basenames are unique.
- Confirm the `introduced` rows were added in lockstep (via the coordinated path) and
  `test_release_ci_ownership.py` is green.

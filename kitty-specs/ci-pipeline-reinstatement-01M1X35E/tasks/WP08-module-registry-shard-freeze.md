---
work_package_id: WP08
title: Module registry + `--durations` shard-freeze
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
requirement_refs:
- FR-006
- NFR-001
- NFR-005
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: .github/ci-module-registry.yml
create_intent:
- .github/ci-module-registry.yml
- .github/ci-shard-timings.json
- tests/architectural/test_module_shard_registry.py
execution_mode: code_change
owned_files:
- .github/ci-module-registry.yml
- .github/ci-shard-timings.json
- tests/architectural/test_module_shard_registry.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (TOPOLOGY T2),
`contracts/router-two-authority.md` §"Module shard registry", `data-model.md` E7, and
the charter §"ATDD-First" + SO#5.

**Cluster gate + sequencing:** claim after ALL FOUNDATION (WP01–WP06) + WP07 are
approved/done. The `--durations` measurement MUST run on the **post-scrub** live basis
(WP05) — never before (plan §"Why this order": scrub → durations → freeze).

## Objective

Freeze the **committed module registry** — the single data source for the per-module
test matrix — with shard boundaries **derived from a measured `--durations` run** on
the scrubbed live basis (not file counts), inter-shard skew ≤20% (NFR-005), so the
critical-path wallclock drops sharply (NFR-001). The registry realizes full-tree
modularization as a **matrix over a bounded set of reusable workflows** (≤ GitHub's
20-reusable-workflows-per-caller ceiling — NOT ~40 separate files). Adding a module is
a **registry row**, not a new workflow file.

## Subtask guidance

### T040 — Red-first: `test_module_shard_registry.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_module_shard_registry.py`
asserting: the registry covers every live `src/**` module in the WP05 scrub set (no
gaps, no retired surfaces), each row has `{roots, cov_target, tier, shard_count}`, the
inter-shard skew is ≤20% computed from the recorded timings, and the registry is
non-vacuous. Run against base: red for the right reason (registry absent). Load the
YAML lazily/in-test.

### T041 — Record a `--durations` run on the scrubbed basis

Run pytest with `--durations` over the **post-scrub** live test basis; capture the
run-id and per-test durations into `.github/ci-shard-timings.json`. This is the
measured basis for balancing (NFR-005) — record it as data, not a guess. Note the
run-id in the file so NFR-001/NFR-005 are validated against a recorded run, not
asserted.

### T042 — Derive the committed module registry

Write `.github/ci-module-registry.yml`: per module `{module, roots[], cov_target
(dotted `--cov=<module>`), tier, shard_count}`, with `shard_count` balanced on the
measured durations so skew ≤20%. Consume the WP05 scrub artefact for the roots/cov
targets — do not re-scrub. This is the single data source WP09's matrix reads.

### T043 — De-serialize the heavy poles

Encode the de-serialization: `integration-tests-next` runs `-n auto` (from 69.2 min
fully-serial) and the architectural pole runs **always-on and de-serialized** (adding
no filter group — consistent with WP07's fast/heavy split). Assert the registry/tiers
reflect this (the ≤7 min integration target, NFR-001, is validated when WP09 runs it).

### T044 — Single-data-source + ceiling assertions

Assert: (a) the registry is the single data source — adding a module is a row, not a
new workflow file; (b) the realization stays within the ≤20-reusable-workflows-per-
caller ceiling (the matrix-over-registry design, not ~40 `module-*.yml`). These are
the architect's HIGH folds — make them machine-checked, not prose.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP08`.
- Depends on all FOUNDATION + WP07 — claim after approved/done.
- Commit order: **T040 red-first FIRST**, then T041–T044.

## Definition of Done

- T040 red on base (evidence captured), green on final.
- `.github/ci-shard-timings.json` records a real `--durations` run (run-id captured) on
  the post-scrub basis.
- `.github/ci-module-registry.yml` covers every live module, is duration-balanced
  (skew ≤20%), uses dotted `--cov`, and stays within the 20-reusable-workflow ceiling.
- The registry is asserted as the single data source; heavy-pole de-serialization
  encoded.
- **Targeted test surface**: `pytest tests/architectural/test_module_shard_registry.py -q`
  plus the `--durations` capture command (recorded in the timings file).

## Risks

- **Unscrubbed-basis freeze**: if durations are measured before WP05's scrub lands, the
  freeze is invalid. Confirm WP05 is approved/done and the scrub set is current before
  T041.
- **Skew from a noisy run**: a single `--durations` run can be noisy; capture on stock-
  runner-representative hardware or average a couple of runs, and record the run-id.
- **Ceiling breach**: naïvely one-workflow-per-module breaches GitHub's 20/caller limit
  — keep the matrix-over-registry realization (T044).
- **New-file arch battery**: new test file + `.github/` data files may trip shard-map
  completeness / new-test-dir routing gates — pre-check locally.

## Reviewer guidance

- Confirm T040 red-on-base for the right reason.
- Confirm the timings file references a real run-id on the post-scrub basis.
- Recompute skew from the timings and confirm ≤20%.
- Confirm the registry consumes the WP05 scrub (no divergent re-scrub) and stays within
  the reusable-workflow ceiling.

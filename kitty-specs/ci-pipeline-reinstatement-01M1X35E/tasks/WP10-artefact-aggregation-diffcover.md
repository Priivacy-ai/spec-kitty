---
work_package_id: WP10
title: Artefact contract + aggregation + diff-cover gate + stale-artefact fallback
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP09
requirement_refs:
- C-005
- FR-007
- FR-009
- NFR-003
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
- T054
- T055
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/ci-aggregate.yml
create_intent:
- .github/workflows/ci-aggregate.yml
- tests/architectural/test_coverage_artefact_contract.py
execution_mode: code_change
owned_files:
- .github/workflows/ci-aggregate.yml
- tests/architectural/test_coverage_artefact_contract.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (TOPOLOGY T3),
`contracts/artefact-naming.md` (**authoritative**, preserve verbatim — C-005),
`data-model.md` E2, and the charter §"ATDD-First".

**Cluster gate:** claim after ALL FOUNDATION (WP01–WP06) + WP09 (shards emit
artefacts) are approved/done.

## Objective

Aggregate the per-shard coverage/xunit artefacts and enforce the **diff-coverage PR
gate** (FR-009 / NFR-003, ≥90% changed critical-path lines), under the **preserved
naming contract** (C-005), with a **stale-artefact fallback** (spec edge case). The
aggregator consumes the shards' `*-reports` without re-running tests (FR-007).

## Subtask guidance

### T051 — Red-first: `test_coverage_artefact_contract.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_coverage_artefact_contract.py`
asserting (against the on-disk workflows): coverage files are
`coverage-<tier>-<module>.xml` with **basename unique per shard**; artifact names end
`-reports` (consumers glob `*-reports`); the cobertura XML has ≤1 `<source>` (dotted
`--cov` guarantees this); `relative_files=true` is set. Run against base: red for the
right reason (`ci-aggregate.yml` absent / contract unmet). **Collection-red lazy-load
hygiene:** any import of a not-yet-existing module/helper is lazy/in-test so the file
still *collects* green on base — the red is a failed behavioral assertion, never a
collection/import error.

### T052 — Author `ci-aggregate.yml`

Create `.github/workflows/ci-aggregate.yml`: `needs:` the module shards, download
`pattern: '*-reports'`, dedup coverage by basename (a collision silently drops data —
guard it). SHA-pin all actions. Produce no single merged `coverage.xml` — consumers
merge as needed (Sonar merges server-side). **Declare `workflow_dispatch`; honor the
`mode` input** (PR=fail-fast/short-circuit, full=`if: always()`/run-all) in this
aggregator's own fail-fast/`needs` behavior per FR-018/FR-019 — the mode-conditioned
logic lives in this owned workflow file, verified by WP11's `test_dual_mode_contract`.

### T053 — diff-cover PR gate

Wire the `diff-cover` gate: `--fail-under=90` on changed critical-path lines (NFR-003).
This is the real PR merge-blocking coverage gate (distinct from Sonar's informational
whole-repo new-code gate — do not conflate them). Exclude census-`dead` surfaces from
the denominator (E3, via the WP02 census).

### T054 — Stale-artefact fallback

Implement the spec edge case: a partial re-trigger leaving some coverage artefacts
stale → the aggregator falls back to the **most-recent successful run's** `*-reports`
for shards that did not re-run. Assert this fallback behavior in the contract test
(the previously-orphan edge case now has a home).

### T055 — C-005 preservation assertions

Assert dotted `--cov=<module>` form (never path form), `relative_files=true`, and the
`coverage-<tier>-<module>.xml` + `*-reports` naming are preserved verbatim. These are
load-bearing so glob aggregators + Sonar resolve every shard's output. Note:
`relative_files = true` already exists in `pyproject.toml [tool.coverage.run]` — assert
it, do not regress it (do not add `pyproject.toml` to this WP's edits).

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP10`.
- Depends on all FOUNDATION + WP09 — claim after approved/done.
- Commit order: **T051 red-first FIRST**, then T052–T055.

## Definition of Done

- T051 red on base (evidence captured), green on final.
- `ci-aggregate.yml` downloads `*-reports`, dedups by basename, runs diff-cover
  `--fail-under=90` on changed critical-path lines, and falls back to the last
  successful run's artefacts on a partial re-trigger; all actions SHA-pinned.
- The contract test asserts naming/basename-uniqueness/≤1-`<source>`/`relative_files`
  and the stale-artefact fallback.
- `ci-aggregate.yml` declares `workflow_dispatch` and honors the `mode` input (PR
  fail-fast vs full `if: always()`) in its own fail-fast/`needs` behavior
  (FR-018/FR-019) — verified by WP11's `test_dual_mode_contract`.
- `ci-aggregate.yml` registered `introduced` (via the coordinated WP01 path — do NOT
  edit WP01's owned files here).
- **Targeted test surface**: `pytest tests/architectural/test_coverage_artefact_contract.py -q`.

## Risks

- **C-005 regression**: switching to path-form `--cov` or dropping `relative_files`
  reintroduces multi-`<source>` ambiguity Sonar cannot resolve — assert against it.
- **Governance-map lockstep**: the `introduced` row for `ci-aggregate.yml` is in WP01's
  owned file — coordinate via the orchestrator, do not edit across the partition.
- **Diff-cover base ref**: the changed-line set depends on the PR base ref; ensure the
  gate diffs against the correct merge base, not the tip.
- **New-file arch battery**: new test dir routing / shard-map — pre-check locally.

## Reviewer guidance

- Confirm T051 red-on-base for the right reason.
- Confirm basename-uniqueness and ≤1-`<source>` are actually asserted (not just naming).
- Confirm the stale-artefact fallback has a test (the edge case is not left as prose).
- Confirm diff-cover blocks a <90% changed-line PR and the census-dead denominator
  exclusion holds.

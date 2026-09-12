---
work_package_id: WP03
title: Doctrine + packs reusable workflows + CI-model guard updates
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
- NFR-001
- C-004
planning_base_branch: mission/modular-per-package-ci
merge_target_branch: mission/modular-per-package-ci
branch_strategy: Planning artifacts for this mission were generated on mission/modular-per-package-ci. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/modular-per-package-ci unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 2 - Generalize
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: .github/workflows/ci-quality.yml
create_intent:
- .github/workflows/module-doctrine.yml
- .github/workflows/module-packs.yml
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- tests/architectural/test_ci_collection_completeness.py
- tests/architectural/test_ci_quality_path_filters.py
- tests/architectural/test_coverage_root_collisions.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Doctrine + packs reusable workflows + CI-model guard updates

**Implements**: FR-006, FR-007, FR-008; NFR-001; C-004. IC-03. **Depends on WP01** (mechanism validated).

## Goal

Generalize the proven kernel pattern to `doctrine` (fast + integration legs) and `packs` (corpus group), and
update the architectural guards that parse the ci-quality job graph so they tolerate `uses:` caller jobs.

## Scope

- NEW `.github/workflows/module-doctrine.yml` (`on: workflow_call`): lift `fast-tests-doctrine`
  (`ci-quality.yml:1138-1185`, `--cov=doctrine --cov=charter` → `coverage-fast-doctrine.xml`) and
  `integration-tests-doctrine` (`:2506-2542` → `coverage-integration-doctrine.xml`). Preserve artifact names;
  keep any `${{ matrix.shard }}` suffix if sharded.
- NEW `.github/workflows/module-packs.yml` (`on: workflow_call`): lift `fast-tests-corpus`
  (`ci-quality.yml:1868-1895`, `--cov=src/doctrine` → `coverage-fast-corpus.xml`).
- MODIFY `ci-quality.yml`: replace the corresponding job bodies with `uses:` callers keeping same ids + gates.
- UPDATE the CI-model guards non-vacuously so `uses:` caller jobs inherit their delegate's
  emitter/path/marker/test-running role (not mis-flagged). **The affected set was empirically mapped by
  WP01's POC — see `tracers/design-decisions.md` DD-01.** WP01 already fixed the collection model
  (`_gate_coverage.py` `job_uses` + `active_job_keys` delegation, and `test_ci_collection_completeness.py`).
  WP03 must make the remaining guards delegation-aware and add them to `owned_files`:
  - `tests/architectural/test_coverage_consumer_needs.py` — a `uses:` caller counts as an emitter of its
    delegate's coverage (so `diff-coverage.needs: kernel-tests` is not "non-emitting").
  - `tests/architectural/test_workflow_coherence.py` — `src/kernel/*` critical path is cov-backed via the
    module; the workflow-file glob added to a filter group is "live".
  - `tests/architectural/test_src_filter_coverage.py` — the `kernel` group gates a test-running job; the
    catch-all `--ignore=tests/kernel` root is owned by the caller.
  - plus the WP01-declared trio (`test_ci_collection_completeness.py`, `test_ci_quality_path_filters.py`,
    `test_coverage_root_collisions.py`) as the doctrine/packs modules are extracted.
  NOTE: `test_release_ci_ownership.py` named in early planning does **not** exist in-tree — do not target it.
  Prefer DD-01 design (B) (splice a reusable workflow's steps into its caller at parse time) for cohesion, so
  all consumers become delegation-transparent through one seam rather than N per-guard patches.
- `spec-internal` is out of scope (C-009).

## ATDD / red-first (C-008)

- **T001 (RED first)**: extend the coverage-aggregation assertion (from WP01) to require
  `coverage-fast-doctrine.xml`, `coverage-integration-doctrine.xml`, `coverage-fast-corpus.xml` in the
  discovered set. RED before extraction, GREEN after.
- **T002**: guard-tolerance tests — add focused cases proving each updated CI-model guard accepts a `uses:`
  caller job (non-vacuous: a malformed `uses:` job or a dropped coverage root must still fail).
- **T003**: full ci-quality green on the mission PR; attach run link.

## Validation surface (targeted)

```bash
PWHEADLESS=1 pytest tests/architectural/test_ci_collection_completeness.py tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_coverage_root_collisions.py tests/architectural/test_coverage_consumer_needs.py tests/architectural/test_workflow_coherence.py tests/architectural/test_src_filter_coverage.py -q
# NOTE: guards touch frozen-baseline-adjacent invariants — do NOT run the full tests/architectural/ locally;
# push and let CI run the whole suite (docs/development/testing-*).
PWHEADLESS=1 pytest tests/doctrine/ tests/charter/ -m "fast and not windows_ci" -q
```

## Acceptance (SC-004)

- All three modules run as reusable workflows; full ci-quality green; no coverage regression (NFR-001);
  architectural CI-model guards pass and remain non-vacuous.

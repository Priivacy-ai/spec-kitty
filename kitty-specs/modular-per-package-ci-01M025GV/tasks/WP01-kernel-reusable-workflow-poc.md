---
work_package_id: WP01
title: Kernel reusable-workflow POC + coverage-aggregation proof
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-001
- NFR-002
- C-004
- C-005
planning_base_branch: mission/modular-per-package-ci
merge_target_branch: mission/modular-per-package-ci
branch_strategy: Planning artifacts for this mission were generated on mission/modular-per-package-ci. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/modular-per-package-ci unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-modular-per-package-ci-01M025GV
base_commit: b64f3b7902d9d2fa00993135b037efc6a1bc9d5c
created_at: '2026-08-15T08:09:10.542700+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - POC
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: .github/workflows/ci-quality.yml
create_intent:
- .github/workflows/module-kernel.yml
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- src/kernel/**
- tests/kernel/**
- tests/architectural/test_ci_collection_completeness.py
- tests/architectural/test_ci_quality_path_filters.py
- tests/architectural/test_coverage_root_collisions.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Kernel reusable-workflow POC + coverage-aggregation proof

**Implements**: FR-001, FR-002; NFR-001, NFR-002; C-004, C-005. IC-01. (Mission `research.md` D1.)

## Goal

Prove decision D1(a) end-to-end on the smallest package. Extract the `kernel-tests` job
(`.github/workflows/ci-quality.yml:1077-1133`) into a self-contained reusable workflow
`.github/workflows/module-kernel.yml` (`on: workflow_call`) and replace the ci-quality job body with a `uses:`
caller that keeps the **same job id (`kernel-tests`) and gate condition**. Confirm `coverage-kernel.xml` /
`kernel-test-reports` still aggregate into the single run consumed by `diff-coverage` and `sonarcloud`.

## Scope

- NEW `.github/workflows/module-kernel.yml` with `on: workflow_call`, containing the kernel steps verbatim
  (checkout → uv sync → `pytest tests/kernel/ … --cov=src/kernel --cov-report=xml:…/coverage-kernel.xml` → the
  inline 90% floor step → `upload-artifact` name `kernel-test-reports`, path `out/reports/`).
- MODIFY `ci-quality.yml`: `kernel-tests: { needs: [changes], if: <same gate>, uses: ./.github/workflows/module-kernel.yml }`.
  Downstream `needs: kernel-tests` (fast-tests-doctrine, diff-coverage, quality-gate, sonarcloud) must still resolve.
- Do NOT rename any artifact or coverage file (C-004). Do NOT change the coverage floor.

## ATDD / red-first (C-008)

- **T001 (RED first)**: add a test asserting the aggregated coverage set still contains `coverage-kernel.xml`
  after the refactor — e.g. extend/add an assertion in the coverage-root / collection guard
  (`tests/architectural/test_coverage_root_collisions.py` or `test_ci_collection_completeness.py`) that the
  kernel coverage file is discovered by the aggregators. Prove it RED on the planning base if the assertion is
  new-behaviour, GREEN after the extraction.
- **T002**: verify the architectural CI-model guards tolerate a `uses:` caller job for `kernel-tests`
  (`test_ci_collection_completeness.py`, `test_ci_quality_path_filters.py`). If they assume inline `steps:`,
  make the minimal non-vacuous update so a `uses:` job is understood; add a focused test for the new branch.
- **T003**: open the mission PR touching `src/kernel` and confirm on CI that the kernel steps run via the
  reusable workflow and coverage reaches diff-coverage in one run (attach the run link to the PR).

## Validation surface (targeted)

```bash
PWHEADLESS=1 pytest tests/architectural/test_coverage_root_collisions.py tests/architectural/test_ci_collection_completeness.py tests/architectural/test_ci_quality_path_filters.py -q
PWHEADLESS=1 pytest tests/kernel/ -m "fast and not windows_ci" -q
```

Plus a CI dry-run via the PR (reusable-workflow behavior can't be fully proven locally).

## Acceptance (SC-001)

- `module-kernel.yml` exists as `on: workflow_call`; ci-quality invokes it as `uses:` with the same job id + gate.
- `coverage-kernel.xml` appears in diff-coverage's discovered set and the nightly Sonar scan — one run.
- `quality-gate` still resolves as the required check (C-005). No coverage regression (NFR-001).

## Notes / risks

- Verify with the operator which check names branch protection pins before merge (repo-admin UI). The refactor
  is a non-event iff `quality-gate` is the pinned check.

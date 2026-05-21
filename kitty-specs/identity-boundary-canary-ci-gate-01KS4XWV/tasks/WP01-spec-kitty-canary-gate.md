---
work_package_id: WP01
title: spec-kitty canary-gate workflow + README section
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-009
- FR-010
- NFR-001
- NFR-004
- NFR-005
- C-001
- C-002
- C-009
planning_base_branch: kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV
merge_target_branch: kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
history:
- at: '2026-05-21T09:34:00Z'
  actor: claude
  action: created
authoritative_surface: .github/workflows/canary-gate.yml
execution_mode: code_change
mission_slug: identity-boundary-canary-ci-gate-01KS4XWV
owned_files:
- .github/workflows/canary-gate.yml
- README.md
priority: P1
status: planned
tags: []
---

# WP01 — spec-kitty repo: canary-gate workflow + README section

## Objective

Add a dedicated, named CI workflow in this repo that runs the drift-detector
test on every PR against `main`, so an admin can register it as a required
status check independently of `ci-quality.yml`'s matrix. Add the README
section explaining the gate.

## Acceptance

- `.github/workflows/canary-gate.yml` exists with job name `drift-detector`.
- Job runs on `pull_request` and `push` to `main`.
- `permissions: contents: read`; concurrency block; `timeout-minutes: 5`.
- Runs `pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v`.
- README has `## Identity-boundary canary CI gate` section.
- `pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v` passes locally.

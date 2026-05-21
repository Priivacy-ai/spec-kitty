---
work_package_id: WP03
title: spec-kitty-events cross-repo-harness-tests workflow + README (cross-repo manifest)
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-010
- NFR-002
- NFR-004
- NFR-005
- C-001
- C-002
planning_base_branch: kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV
merge_target_branch: kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
history:
- at: '2026-05-21T09:34:00Z'
  actor: claude
  action: created
authoritative_surface: kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/cross-repo-manifests/spec-kitty-events.md
execution_mode: planning_artifact
mission_slug: identity-boundary-canary-ci-gate-01KS4XWV
owned_files:
- kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/cross-repo-manifests/spec-kitty-events.md
priority: P1
status: planned
tags: []
---

# WP03 — spec-kitty-events: cross-repo-harness-tests workflow + README (cross-repo)

## Objective

Land a CI workflow + README section in `spec-kitty-events` running the
harness identity-boundary unit tests against the PR's events source.

## Acceptance

In `spec-kitty-events`:

- `.github/workflows/cross-repo-harness-tests.yml` with job
  `harness-unit-tests`, pinned e2e SHA
  `03e4d3c04fcdf641cd564badfbc87bb19a2a0982`, 10-minute timeout. Installs
  PR's events source via `uv pip install -e ../` into the e2e environment.
- README has `## Identity-boundary canary CI gate` section.

In this repo:

- `kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/cross-repo-manifests/spec-kitty-events.md`
  exists with canonical YAML, README section text, PR URL, head SHA.

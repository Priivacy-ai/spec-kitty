---
work_package_id: WP01
title: ADR hygiene + convergence-retirement ADR
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: tier3/governance-enforcement
merge_target_branch: tier3/governance-enforcement
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Governance record
agent_profile: doctrine-daphne
authoritative_surface: docs/adr/
role: implementer
task_type: implement
owned_files:
- docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md
- docs/adr/3.x/2026-04-11-1-saas-rollout-and-readiness.md
- docs/adr/3.x/2026-08-09-1-project-sync-store-boundary.md
- docs/adr/2.x/2026-02-27-1-cli-tracker-surface-gated-by-saas-sync-flag.md
- docs/adr/3.x/2026-09-06-1-convergence-retirement-and-client-repo-inversion.md
- tests/architectural/test_adr_hygiene_convergence_retirement.py
---

# WP01 — ADR hygiene + convergence-retirement ADR

Mark the four retired-subsystem ADRs `Superseded` and author one new convergence-retirement ADR that
supersedes them and records the client-repo inversion. Leave `2026-04-25-1` (shared-package-boundary)
`Accepted` — it is the precedent the inversion extends. A red-first ADR-hygiene gate asserts the whole
shape and proves its own teeth.

## Requirements
- **FR-001** four ADRs → `Superseded` + pointer.
- **FR-002** one new ADR (`Accepted`) supersedes the four and records the inversion.
- **FR-003** `2026-04-25-1` stays `Accepted`.

## Acceptance
- `test_adr_hygiene_convergence_retirement.py` passes: the four are Superseded and link the new ADR;
  the new ADR is Accepted, supersedes the four, and names the inversion; `2026-04-25-1` is Accepted; the
  non-vacuity guard flags a synthetic still-Accepted retired ADR.

---
work_package_id: WP05
title: Retire zero-value dirs + repoint documentation mission deliverables
dependencies:
- WP03
- WP04
requirement_refs:
- FR-006
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: docs/output/
create_intent: []
execution_mode: code_change
owned_files:
- research/**
- docs/core-concepts/**
- docs/updates/**
- docs/output/**
- src/specify_cli/missions/documentation/mission.yaml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load curator-carla
```
Confirm doctrine/knowledge-curation boundaries; delete-stale discipline.

## Objective
Retire the zero-value/placeholder surfaces and repoint the one code reference that blocks retiring
`docs/output/`. See [occurrence_map.yaml](../occurrence_map.yaml) and [plan.md](../plan.md) IC-04.

## Subtasks
- **T015** — FIRST repoint `src/specify_cli/missions/documentation/mission.yaml:41` `deliverables` off
  `docs/output/` (choose a non-retired target or drop the placeholder), with a regression check.
- **T016** — Retire `research/` (13 agent files + data-model/research/sample-agents — no live inbound;
  distil any genuine survivor into `docs/integrations/`, NOT `docs/plans/` per C-001), and retire the
  index-only `docs/core-concepts/`, `docs/updates/`, and `docs/output/` (keep "Core Concepts"/"Project
  Updates" as `toc.yml` nav zones — WP13 owns toc.yml). Record all retirements as this WP's
  occurrence-map fragment.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- `docs/output/` retired with mission.yaml repointed (documentation-mission test green); research/,
  core-concepts/, updates/ retired; fragment recorded. No dangling inbound links introduced.

## Risks
- Confirm zero live inbound for research/ before deleting (grep src/tests/docs); leave a redirect stub
  only if an inbound reference exists.

---
work_package_id: WP06
title: docs/api consolidation (fold reference/, rehome contract, reconcile index/toc)
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
- FR-005
- FR-007
- FR-012
- FR-013
- FR-014
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: docs/api/
create_intent: []
execution_mode: code_change
owned_files:
- docs/api/**
- docs/reference/**
- contracts/batch-api-contract.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load curator-carla
```

## Objective
Dissolve the non-canonical `reference/` umbrella into `api/`, rehome the API contract, and reconcile the
api landing/toc. See [plan.md](../plan.md) IC-05 (api ownership), [occurrence_map.yaml](../occurrence_map.yaml).

## Subtasks
- **T017** — Fold `docs/reference/` real content (`skills/`, `agent_profiles/`) under `docs/api/`; retire
  the `reference/` umbrella (keep "Reference" as a `toc.yml` nav zone — WP13 owns toc). Record the moves
  in this WP's fragment; run in-tree `relative_link_fixer` only on files you own.
- **T018** — Rehome `contracts/batch-api-contract.md` → `docs/api/`; reconcile the three competing api
  index pages into one `index.md`; drop the dead `apidoc/**` glob reference from `docfx.json` intent
  (flag to WP13, which owns docfx.json — do not edit it here). Update the enumerated `cli-cheatsheet.md`
  ref (`tests/docs/test_docs_query_cli.py:69`).
- **T019** — Kebab-case api filenames; ensure one `index.md`; migrate `audience:` on any of the 13
  free-text pages under api/ to catalog refs; **rewrite phase** (separately reviewed): scanability pass
  on touched api pages with the NFR-009 fidelity ledger (behavior-doc pages regenerated via
  `build_cli_reference.py`, not hand-edited).

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- `reference/` dissolved into api/; contract rehomed; one api index; kebab names; audience migrated on
  touched pages; rewrite phase ledgered. Moves recorded in fragment; owned-file links resolve.

## Risks
- Shared manifests (toc/docfx/redirect_map) are WP13-only — emit intent, don't edit them.

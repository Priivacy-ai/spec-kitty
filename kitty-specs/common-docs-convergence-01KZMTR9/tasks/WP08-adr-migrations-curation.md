---
work_package_id: WP08
title: 'docs/adr era-index, dated-prefix (2887) + migrations delete-stale'
dependencies:
- WP03
- WP04
- WP07
requirement_refs:
- FR-013
- FR-015
- FR-024
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: docs/adr/
create_intent: []
execution_mode: code_change
owned_files:
- docs/adr/**
- docs/migrations/**
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load curator-carla
```

## Objective
Polish the (largely compliant) ADR corpus and curate `migrations/` by delete-stale. Closes #2887,
reconciles #2227/#3227. See [plan.md](../plan.md) IC-05(adr)/IC-10, [occurrence_map.yaml](../occurrence_map.yaml).

## Subtasks
- **T024** — Author the distilled era-history content handed off from WP07 (from `architecture/README-1.x/2.x/3.x.md`)
  INTO `adr/{1.x,2.x,3.x}/` (this WP owns `docs/adr/**`). Place the era-index (`adr/{1.x,2.x,3.x}/index.md`) — reconcile with the #2227 lint
  exclusion (either normalize the 3 era READMEs here AND update `structural_lint_config`
  `frontmatter_in_scope_exclusions`, or explicitly leave them to #2227 — no silent double-ownership).
  Fix the #2887 date-sequence violations (3 duplicate `-1-` dates) and the 2 non-dated 3.x ADRs with
  redundant `doc_status` (drop `doc_status`, keep MADR `status`, add dated prefix). Record renames in the
  fragment (dated-prefix renames need redirect coverage). If `docs/adr/3.x/README` documents the failing
  `freshen_adr_inventory` command (#3227), fix or note it.
- **T025** — Curate `docs/migrations/`: reclassify completed one-off runbooks (`*teamspace*`,
  `upgrade-to-0-12-0`, `from-charter-2x`, flag-deprecations) to `deprecated`/`superseded` or distil to an
  ADR; kebab-rename the stray-numbered `06_migration_and_shim_rules.md`. Keep the CLAUDE.md-referenced
  runbooks live.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- Era-index normalized with #2227 reconciled; #2887 date-sequence + redundant-`doc_status` fixed;
  migrations curated; renames recorded in fragment; MADR `status` preserved (no `doc_status` on ADRs).

## Risks
- ADR renames create redirect entries — record them in the fragment; WP13 regenerates the map.
- Depends on WP07 (which distils the version-shadow content INTO adr/<era>/) — sequence after it.

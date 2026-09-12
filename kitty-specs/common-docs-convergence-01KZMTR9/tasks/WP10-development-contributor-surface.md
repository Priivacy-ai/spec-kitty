---
work_package_id: WP10
title: docs/development — contributor how-tos + reference_policy, subdivision
dependencies:
- WP01
- WP03
- WP04
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: docs/development/
create_intent:
- docs/development/getting-started/index.md
- docs/development/how-to/index.md
- docs/development/reference/index.md
- docs/development/testing/index.md
execution_mode: code_change
owned_files:
- docs/development/*.md
- docs/development/toc.yml
- docs/development/getting-started/**
- docs/development/how-to/**
- docs/development/reference/**
- docs/development/testing/**
- src/specify_cli/doc_analysis/gap_analysis.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load curator-carla
```

## Objective
Make `development/` the contributor surface per the audience-based routing: it is the config home for
`how_to` + `reference_policy` (internal audience). Subdivide the 22 flat files by concern. See
[plan.md](../plan.md) IC-06(development), D1/D2.

## Subtasks
- **T029** — Group the flat `development/` files by concern into subdirectories (e.g.
  `getting-started/`, `how-to/`, `reference/`, `testing/`), routing contributor how-tos +
  reference_policy content here (external/user how-tos go to `guides/` — WP09). Assign Divio `type:` to
  each page. Record moves in the fragment.
- **T030** — Add an `index.md` per new subdir + reconcile the top `development/index.md`; kebab-case
  names; migrate any free-text `audience:` to internal-persona catalog refs; **rewrite phase**
  (separately reviewed) with the NFR-009 fidelity ledger. Do NOT touch the `3-2-*.yaml` rollups (WP13);
  do NOT edit `CLAUDE.md`/`AGENTS.md` (WP13 updates those refs) — but LIST the dev pages you move so
  WP13 can repoint the ~4 CLAUDE.md references and the `CONTRIBUTING.md` symlink target.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- development/ subdivided by concern with per-dir index; every page typed; kebab; audience migrated;
  moved-page list handed to WP13 for CLAUDE.md/CONTRIBUTING updates; rewrite ledgered. Fragment recorded.

## Risks
- `CONTRIBUTING.md` is a symlink to `docs/development/contributing.md` — if that file moves, the symlink
  + `spec-driven.md` inbound refs must update (hand to WP13). Prefer keeping `contributing.md` at its
  path to avoid churn unless the concern grouping requires it.
- The `3-2-page-inventory.yaml`/`3-2-docs-retrieval-index.yaml` rollups live here but are WP13-owned
  (owned across ~10 live missions) — never move or edit them.

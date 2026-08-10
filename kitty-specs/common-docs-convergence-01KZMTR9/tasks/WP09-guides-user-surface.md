---
work_package_id: WP09
title: docs/guides — examples rehome, tutorials split, Divio type, subdivision
dependencies:
- WP01
- WP03
- WP04
requirement_refs:
- FR-004
- FR-005
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
- T026
- T027
- T028
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: comms-cleo
authoritative_surface: docs/guides/
create_intent: []
execution_mode: code_change
owned_files:
- docs/guides/**
- examples/**
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load comms-cleo
```
Confirm: name the target audience persona before drafting; edits minimal + rationale-backed; do not
alter factual claims without backing (publication-authority).

## Objective
Make `guides/` the user-facing surface: rehome `examples/`, place user how-tos, split tutorials from
how-tos, type every page, and subdivide by concern. See [plan.md](../plan.md) IC-06(guides), D1 audience routing.

## Subtasks
- **T026** — Rehome `examples/` (user scenario walkthroughs; rename off any prohibited "feature" term)
  into `docs/guides/`, deduping against existing guides. Ensure only **user-facing** how-tos live here
  (contributor how-tos go to `development/` — WP10); coordinate the split by each page's audience.
- **T027** — Split tutorials into `guides/tutorials/` and how-tos into `guides/how-to/`; collapse the 3
  index files (`index`, `how-to-index`, `tutorials-index`) into one landing + per-grouping index;
  backfill Divio `type:` on the ~32 untyped pages (6 tutorial / 21 how-to already typed).
- **T028** — Subdivide guides by concern with an `index.md` per subdir; kebab-case names; migrate any
  free-text `audience:` to external-persona catalog refs; **rewrite phase** (separately reviewed) —
  scanability pass grounded in each page's audience, with the NFR-009 fidelity ledger. Record all moves
  in this WP's occurrence-map fragment; run in-tree `relative_link_fixer` only on owned files.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- examples/ rehomed; tutorials/how-tos split; every guides page typed; subdivided with per-dir index;
  kebab; audience migrated; rewrite ledgered. Fragment recorded; placement gate (external→guides) green.

## Risks
- The concern-routing config edit is WP01's; consume it, don't re-edit the styleguide.
- Some guides pages are code-referenced (install-and-upgrade, use-retrospective-learning) — keep those
  paths stable or record the ref update for WP13/enumerated set.

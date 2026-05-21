---
work_package_id: WP09
title: Archive / migration plan (active bulk edit)
dependencies:
- WP02
requirement_refs:
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
agent: "claude:opus-4-7:curator-carla:implementer"
shell_pid: "98108"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: curator-carla
authoritative_surface: docs/development/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- docs/development/3-2-archive-migration-plan.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

## Objective

Author the page-level archive/migration plan: for every page tagged `archival` or `migration` in the inventory, declare what happens (move target, banner text, link redirects, whether the page is retired entirely). This is the planning artifact for the bulk-edit path moves under `filesystem_paths.rewrite` in `occurrence_map.yaml`. **No live page is moved during this WP**; the plan is the deliverable.

## Context

- FR-013.
- `occurrence_map.yaml` (WP01) declares the path-move rules; this WP enumerates the page-level dispositions.
- Bulk-edit gate applies: implement-review verifies that the plan matches the rules in `occurrence_map.yaml`.
- Plan default for decision `01KS4KTGTN4DBE60JFWKEA2FJB`: 3.1 pages become migration notes. This WP lists the specific pages to convert.

## Subtasks

### T027 — Page-level disposition table

For every `archival` and `migration` inventory row, write a row:

| Source path | Tag | Disposition | Target path | Banner | Notes |
|-------------|-----|-------------|-------------|--------|-------|

- `Disposition` ∈ `{move, banner-only, retire, convert-to-migration-note}`.
- `Target path` empty for `banner-only` and `retire`; required for `move` and `convert-to-migration-note`.
- `Banner` is the exact line that will be prepended (matches the banner regex in `contracts/version_leakage_check.md`).
- `Notes` calls out any non-trivial link redirects.

### T028 — Cross-check against inventory

- Confirm every inventory row with `tag in {archival, migration}` appears in the plan.
- Confirm every `move` target lands under `docs/archive/<1x|2x>/` per the `filesystem_paths` rule in `occurrence_map.yaml`.
- Confirm every `convert-to-migration-note` target lands under `docs/migration/`.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `C`. Reuses the lane-C worktree from WP08.

## Test Strategy

- Bulk-edit gate: dispositions match `occurrence_map.yaml` rules.
- Reviewer gate: plan covers every archival/migration inventory row.

## Definition of Done

- [ ] `docs/development/3-2-archive-migration-plan.md` exists with the page-level table.
- [ ] Every archival/migration inventory row appears in the table.
- [ ] Move targets align with `occurrence_map.yaml`.
- [ ] No live pages moved (`git status` shows no renames outside `owned_files`).

## Risks

- **Coverage gap** — Mitigation: implementer scripts the cross-check via `yq` or `python` against `3-2-page-inventory.yaml`.
- **Decision flip on 3.1** — Mitigation: pages converted from `migration` back to `supported` re-classify in inventory; this plan changes only the rows for those pages.

## Reviewer Guidance

- Spot-check 10 random archival rows.
- Verify the move-target rules exactly match `occurrence_map.yaml`.
- Confirm no live page renames in `git status`.

## Implement command

```bash
spec-kitty agent action implement WP09 --agent claude
```

## Activity Log

- 2026-05-21T08:43:25Z – claude:opus-4-7:curator-carla:implementer – shell_pid=98108 – Started implementation via action command

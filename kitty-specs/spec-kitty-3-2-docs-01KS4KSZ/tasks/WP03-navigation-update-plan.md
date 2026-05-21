---
work_package_id: WP03
title: Navigation update plan
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
agent: claude
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
- docs/development/3-2-navigation-plan.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load curator-carla
```

## Objective

Author a diff-shaped navigation plan that describes every move, add, and remove required in `docs/toc.yml` and every child TOC to separate 3.2-current content from 3.1-supported, migration, and archival content. **Do not edit any live TOC file** during this WP — the plan is the deliverable.

## Context

- FR-004 requires explicit nav groups for 3.2-current, 3.1-supported (conditional on decision `01KS4KTGTN4DBE60JFWKEA2FJB`), Migration, Archive (2.x), Archive (1.x).
- Research R-002 treats DocFX as the active site generator pending tasks-phase confirmation. The plan must work for both DocFX and MkDocs in case the generator differs.
- Plan default for the deferred 3.1 decision: fold 3.1 into 3.2 as migration notes; if the decision flips to "3.1 as supported version", a single section of this plan must shift cleanly.
- Inventory from WP02 is the source-of-truth for which page belongs in which nav group.

## Subtasks

### T007 — Diff-shaped plan for every TOC file

For every TOC file in the inventory (typically `docs/toc.yml` plus per-directory `docs/<area>/toc.yml`):

- **Before snapshot**: a YAML excerpt of the current entries (read-only quote).
- **After snapshot**: the proposed entries after rebalancing.
- **Diff**: explicit `+`/`-` lines or a unified-diff block.
- **Rationale**: 1–2 lines explaining why entries moved.

Cover every TOC file the page inventory references; if a file has no changes, record it explicitly with "no changes".

### T008 — Nav-group plan

Define the five nav groups for current 3.2 navigation:

| Group | Members |
|-------|---------|
| 3.2 (current) | All pages tagged `current`. |
| 3.1 (supported) | Conditional on decision `01KS4KTGTN4DBE60JFWKEA2FJB`. Plan default: this group is absent and 3.1 pages live in Migration. |
| Migration | All pages tagged `migration` (from 2.x → 3.2 and, by default, from 3.1 → 3.2). |
| Archive (2.x) | All pages tagged `archival` under `docs/2x/**`. |
| Archive (1.x) | All pages tagged `archival` under `docs/1x/**`. |

Document landing-page wording for each group (one to two sentences) so the WP07 reference and WP08 IA can cross-link.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `A`. Reuses the lane-A worktree.

## Test Strategy

- Reviewer gate (no automated tests for a plan doc).
- Curator verifies that every TOC file referenced in the inventory has either a before/after snapshot or a "no changes" entry.

## Definition of Done

- [ ] `docs/development/3-2-navigation-plan.md` exists with a section per TOC file.
- [ ] All five nav groups are documented with landing-page wording.
- [ ] Conditional 3.1 group is marked explicitly with the decision_id.
- [ ] No edits to any live TOC file (`docs/toc.yml` or child TOCs).
- [ ] No files outside `owned_files` modified.

## Risks

- **3.1 decision flip after WP03 lands** — Mitigation: the plan documents the flip path; only one section needs to shift (the 3.1 group reappears and the Migration group shrinks).
- **Doc-site generator differs from DocFX** — Mitigation: the plan uses generator-agnostic YAML where possible; T007 calls out any DocFX-specific syntax.

## Reviewer Guidance

- Confirm every TOC file appears at least once (including "no changes" entries).
- Confirm the conditional 3.1 group cites the decision_id `01KS4KTGTN4DBE60JFWKEA2FJB`.
- Confirm no live TOC file was edited (review `git diff --stat`).

## Implement command

```bash
spec-kitty agent action implement WP03 --agent claude
```

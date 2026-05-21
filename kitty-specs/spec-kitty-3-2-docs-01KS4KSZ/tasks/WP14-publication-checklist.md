---
work_package_id: WP14
title: Publication checklist + final sweep
dependencies:
- WP07
- WP09
- WP11
- WP12
- WP13
requirement_refs:
- FR-021
- NFR-006
- NFR-008
- NFR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T043
- T044
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "18671"
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
- docs/development/3-2-publication-checklist.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

## Objective

Author the 3.2 docs publication checklist that gates the public site update. The checklist references the artifacts produced by every other WP and ties each `spec.md` acceptance criterion to a concrete piece of evidence.

## Context

- FR-021.
- Pre-conditions: WP07 (rebuilt reference), WP09 (archive plan), WP11 (harness pages), WP12 (install lifecycle), WP13 (freshness orchestrator + CI step) must be merged before this WP starts.

## Subtasks

### T043 — Author the publication checklist

Create `docs/development/3-2-publication-checklist.md` with sections:

1. **Pre-flight gates** — every acceptance criterion from `spec.md` §"Acceptance Scenarios" with a citation to its evidence (file path, test ID, or freshness rule).
2. **CI checks** — list the workflow runs that must be green (e.g., `docs-freshness` from WP13, existing `tests/architectural/` runs from WP06).
3. **Manual review checklist** — 5–10 items a release engineer walks through before pushing the public site (e.g., spot-check 5 random `current` pages for version banners; verify the 3.2 landing page link; verify the CLI reference cross-link).
4. **Meta-issue dispatch path** — every `BLOCKING` row in `3-2-cli-reference-audit-meta-issues.md` must be resolved or explicitly accepted as `non_blocking` before publish.
5. **Rollback plan** — how to revert the docs site to the last known-good build if a regression slips through.

### T044 — Coverage cross-check

- For every `spec.md` acceptance criterion (9 scenarios + 7 success criteria + 9 NFR thresholds), confirm the checklist names a specific evidence artifact.
- For every workstream A–F, confirm at least one checklist item points at it.
- For every (tool × OS) cell in the install lifecycle (WP12), confirm a checklist item names it.
- For the harness support matrix (WP10), confirm a checklist item points at it.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `F`. Reuses the lane-F worktree from WP13.

## Test Strategy

- Reviewer gate.
- WP14 mission-review step verifies the checklist matches `spec.md` acceptance criteria exactly.

## Definition of Done

- [ ] `docs/development/3-2-publication-checklist.md` exists.
- [ ] Every spec.md acceptance criterion has an evidence citation.
- [ ] Every workstream A–F is represented.
- [ ] Every BLOCKING meta-issue has a resolution path.
- [ ] No files outside `owned_files` modified.

## Risks

- **Acceptance criteria drift** — Mitigation: copy criteria verbatim from `spec.md` at WP14 start; if drift occurs, fix `spec.md` first.
- **Late-arriving meta-issues** — Mitigation: WP14 starts only after WP07 lands; new blocking issues must resolve before this WP marks done.

## Reviewer Guidance

- Confirm coverage cross-check matrix is included.
- Confirm rollback plan is concrete (specific git commands, not platitudes).
- Confirm no meta-issue is left in BLOCKING status without an owner.

## Implement command

```bash
spec-kitty agent action implement WP14 --agent claude
```

## Activity Log

- 2026-05-21T09:17:20Z – claude:opus-4-7:curator-carla:implementer – shell_pid=16037 – Started implementation via action command
- 2026-05-21T09:22:05Z – claude:opus-4-7:curator-carla:implementer – shell_pid=16037 – WP14 ready (final WP): publication checklist with pre-flight gates, CI checks, manual review, meta-issue dispatch, rollback plan, coverage cross-check.
- 2026-05-21T09:22:32Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=18671 – Started review via action command
- 2026-05-21T09:23:23Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=18671 – Renata review: pass. Final WP. 25 pre-flight gates (S1-9 + SC1-7 + NFR-001..009) with citations; 10 manual review items; 3 blocking meta-issues tracked; concrete rollback plan; coverage cross-check ties every spec acceptance criterion to an evidence artifact.

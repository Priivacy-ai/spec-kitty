---
work_package_id: WP06
title: Author the Ops ADR (shared Op/lifecycle abstraction)
dependencies:
- WP02
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
agent: "claude:opus:tbd:implementer"
shell_pid: "822589"
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: architect-alphonso
authoritative_surface: architecture/3.x/adr/
execution_mode: code_change
owned_files:
- architecture/3.x/adr/**
role: architect
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load architect-alphonso`.

## Objective
Fill the top architecture gap (FR-007, `work/EPIC_ARCHITECTURE_CORRELATION.md`): author the **Ops ADR** ratifying "Op as a first-class execution artifact" (the tier between Mission and ad-hoc). **Scope the abstraction to also cover pre/post-mission lifecycle** so #1804 (Ops) and #1802 (lifecycle) share one primitive, not two (C-005).

## Context
- #1688 is the unratified proposal; #1810 collapses do/ask/advise → dispatch; #1802 lifecycle flows share the Op shape (bounded, governed, durable-record, no full ceremony). This ADR is the seam preventing divergence.
- Use `architecture/adr-template.md`. Lands in `architecture/3.x/adr/` (depends on WP02 layout).
- UPDATED sources (required — the Ops ADR must be coherent with the current execution shapes):
  - ADR `architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md` INCLUDING its 2026-06-10 addendum (Step 7 delivered; CommitTarget is `(ref, kind)`)
  - ADR `architecture/3.x/adr/2026-06-07-1-execution-state-canonical-surface.md` (`mission_runtime` canonical surface)
  - `src/specify_cli/core/commit_guard.py` (`GuardCapability` model)
  - C4/ADR content must depict these CURRENT shapes, not `execution_context.py` or `(worktree_root, destination_ref)`.

## Subtasks
### T019 — Author the ADR
Define the Op: bounded doctrine-governed action → dispatch (route → governance context → durable Op record → exit; agent acts on the panel). Cover Mission vs Op vs ad-hoc tiers; specify that pre/post-mission lifecycle actions (intake Op, correction Op) are Ops too. Decision, rationale, alternatives, consequences.
### T020 — Cross-link
Reference the ADR from #1804/#1802/#1810; update `work/EPIC_ARCHITECTURE_CORRELATION.md` (Ops gap closed → SC-2).

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json`.

## Ownership & out-of-map edits
Owned: `architecture/3.x/adr/**` (add one ADR; do not edit unrelated ADRs). **Out-of-map edits allowed with a recorded one-line rationale** (e.g. the correlation-matrix update under `work/`).

## Review / Sign-off (R-07)
**architect-alphonso sign-off** — the abstraction must be single + cover lifecycle.

## Definition of Done
- New ADR follows the template; defines the shared Op/lifecycle abstraction; cross-linked; correlation matrix shows the Ops gap closed.

## Risks
- Authoring two parallel abstractions (violates C-005) — the ADR must explicitly unify #1804/#1802.

## Activity Log

- 2026-06-11T15:28:16Z – claude:opus:tbd:implementer – shell_pid=822589 – Assigned agent via action command
- 2026-06-11T15:40:16Z – claude:opus:tbd:implementer – shell_pid=822589 – Moved to for_review

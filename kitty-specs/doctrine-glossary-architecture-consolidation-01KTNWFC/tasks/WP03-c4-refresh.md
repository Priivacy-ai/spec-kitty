---
work_package_id: WP03
title: Refresh the 3.x C4 model
dependencies:
- WP02
requirement_refs:
- FR-006
tracker_refs:
- '#1805'
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "856997"
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: architect-alphonso
authoritative_surface: architecture/diagrams/
execution_mode: code_change
owned_files:
- architecture/diagrams/**
role: architect
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load architect-alphonso`.

## Objective
Refresh the living C4 (hand-authored Markdown + Mermaid, numbered levels) to the **current 3.x domain model** — Governance / Mission-Management / Execution-Runtime, plus the Op/lifecycle tier (#1804/#1802) and the consolidated epic landscape. (R-04: keep markdown+mermaid; generated-C4 swap deferred to #1812.)

## Context
- Depends on WP02 (the `architecture/diagrams/` layout + carried-forward 2.x C4 must exist).
- Source of truth for the 3.x model: the execution-state ADRs (2026-06-03-1/2/3, 2026-06-07-1), the Ops ADR (WP06), and `work/EPIC_ARCHITECTURE_CORRELATION.md`.
- UPDATED sources (required — depict CURRENT shapes, not stale `execution_context.py` or `(worktree_root, destination_ref)`):
  - ADR `architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md` INCLUDING its 2026-06-10 addendum (Step 7 delivered; CommitTarget is `(ref, kind)`)
  - ADR `architecture/3.x/adr/2026-06-07-1-execution-state-canonical-surface.md` (`mission_runtime` canonical surface)
  - `src/specify_cli/core/commit_guard.py` (`GuardCapability` model; `commit_guard.evaluate` is the single authority)
  - Single resolution authorities: `resolve_placement_only` and `resolve_status_surface_with_anchor`
- Deliberately OUT of scope: deterministic diagram generation (upstream #1839, deduped vs #1812) — this WP refreshes the hand-authored C4 per R-04; cross-reference only.
- Closes #1805 (architecture/docs restructure + C4 refresh — folded as this mission's source FR).

## Subtasks
### T011 — Context level (01_context)
Update the system-context Mermaid to current actors/externals (operators, agents, SaaS, tracker).
### T012 — Container level (02_containers)
Reflect the three domains (Governance ⊕ Doctrine, Mission-Management durable, Execution/Runtime ephemeral) + the Op execution tier; status owned by Mission-Management (OHS facade). Depict `mission_runtime` as the canonical execution surface, `CommitTarget(ref, kind)` as the commit seam, and `GuardCapability` as the single commit-guard model — per the UPDATED sources listed in Context (do NOT depict `execution_context.py` or the old `(worktree_root, destination_ref)` pair).
### T013 — Component level (03_components)
Refresh components for the changed domains; ensure cross-links to the relevant 3.x ADRs.

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json`.

## Ownership & out-of-map edits
Owned: `architecture/diagrams/**`. **Out-of-map edits allowed with a recorded one-line rationale** (e.g. a cross-link fix in a neighbouring README).

## Review / Sign-off (R-07)
**architect-alphonso sign-off** — diagrams reflect the ratified 3.x model.

## Definition of Done
- C4 levels render on GitHub; reflect the 3.x domain model + Op tier; cross-linked to 3.x ADRs.

## Risks
- Mermaid drift from reality (accepted; #1812 tracks the generated-C4 follow-up).

## Activity Log

- 2026-06-11T15:28:03Z – claude:opus:tbd:implementer – shell_pid=822589 – Assigned agent via action command
- 2026-06-11T15:37:21Z – claude:opus:tbd:implementer – shell_pid=822589 – C4 refreshed to 3.x canonical shapes: four bounded modules + Op tier; mission_runtime canonical surface; CommitTarget(ref, kind); commit_guard.evaluate + GuardCapability; resolve_placement_only / resolve_status_surface_with_anchor; 9-lane WP FSM; retired execution_context.py and (worktree_root, destination_ref) explicitly omitted. 12 Mermaid blocks render (mmdc); markdownlint-cli2@0.18.1 0 errors; link-integrity + terminology guards green. Lane commit 2b6366d6a.
- 2026-06-11T15:38:31Z – claude:opus:reviewer-renata:reviewer – shell_pid=856997 – Started review via action command

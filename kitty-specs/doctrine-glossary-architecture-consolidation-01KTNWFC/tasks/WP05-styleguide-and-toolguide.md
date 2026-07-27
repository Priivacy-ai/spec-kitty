---
work_package_id: WP05
title: Author planning/tracking styleguide + toolguide
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "849040"
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: curator-carla
authoritative_surface: src/doctrine/styleguides/
execution_mode: code_change
owned_files:
- src/doctrine/styleguides/**
- src/doctrine/toolguides/**
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load curator-carla`.

## Objective
Author the planning/tracking **styleguide** and the gh/GraphQL **toolguide** as canonical doctrine artefacts (FR-003, FR-004), from the `work/` traces.

## Context
- Source material: `work/TRACKER_DOCTRINE_NOTES.md` (principles, styleguide rules) and `work/GH_TOOLING_NOTES.md` (toolguide mechanics + gotchas).
- Schemas: `src/doctrine/schemas/styleguide.schema.yaml`, `toolguide.schema.yaml`. `src/doctrine/toolguides/` may be empty — create per schema. C-002 (canonical templates).
- NOTE: the `work/` traces cited here predate the 2026-06-09 tracker cleanup — re-verify referenced tickets/epics against the live tracker at claim time.

## Subtasks
### T017 — Styleguide
Functional-epic-vs-meta-tracker rule; community-precedence on dedup; label/type/priority conventions (single `priority:Px`; `bug` ⟺ type Bug; `triage:{stale,needs-revision,maybe-duplicate}`, `usability`, `future`); epic naming; "no ticket list in epic body".
### T018 — Toolguide
gh CLI + GitHub GraphQL: sub-issues API (integer db-id vs `I_…` node-id; `-F`; single-parent; `--paginate`), GraphQL-variable pattern, secondary-rate-limit loop trap, auth (`unset GITHUB_TOKEN`), batched parent lookups. Include the pitfall table.

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json`.

## Ownership & out-of-map edits
Owned: `src/doctrine/{styleguides,toolguides}/**`. **Out-of-map edits allowed with a recorded one-line rationale.**

## Review / Sign-off (R-07)
Doctrine sign-off + **architect-alphonso sign-off** (these encode architecture/tooling conventions) + reviewer profile.

## Definition of Done
- Styleguide + toolguide authored, schema-valid, terminology guard passes; toolguide carries the node-id-vs-db-id and rate-limit gotchas.

## Risks
- Literal "Feature" issue-type term vs terminology guard — phrase carefully (it's the GitHub type, not the Mission domain object).

## Activity Log

- 2026-06-11T15:28:12Z – claude:opus:tbd:implementer – shell_pid=822589 – Assigned agent via action command
- 2026-06-11T15:35:59Z – claude:opus:tbd:implementer – shell_pid=822589 – Moved to for_review
- 2026-06-11T15:36:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=849040 – Started review via action command
- 2026-06-11T15:40:48Z – user – shell_pid=849040 – Review passed: planning/tracking styleguide (10 principles/4 patterns/3 anti-patterns) + github-tracker toolguide+md faithfully distilled from work/ traces; db-id-vs-node-id + secondary-rate-limit + --paginate + unset GITHUB_TOKEN gotchas all correct and matching CLAUDE.md; both schema-valid; graph.yaml regen purely additive (2 nodes, 0 edges); GitHub 'Feature' issue-type annotated; terminology guard + tests/doctrine (2144) + DRG shipped-graph-valid all green.

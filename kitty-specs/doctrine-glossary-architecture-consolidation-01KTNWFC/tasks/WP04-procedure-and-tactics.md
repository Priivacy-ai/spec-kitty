---
work_package_id: WP04
title: Author planning/tracking procedure + tactics
dependencies:
- WP01
- WP02
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "852587"
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: curator-carla
authoritative_surface: src/doctrine/procedures/
execution_mode: code_change
owned_files:
- src/doctrine/procedures/**
- src/doctrine/tactics/**
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load curator-carla`.

## Objective
Author the **planning/ticketing/tracing procedure** and supporting **tactics** as canonical doctrine artefacts (FR-001, FR-002), distilled from the `work/` traces. Conform to the doctrine schemas; they will be wired into the DRG by WP10.

## Context
- Source material (authoritative): `work/TRACKER_DOCTRINE_NOTES.md` (principles, 10-step workflow, iterative-deepening, MoSCoW reminder), `work/EXECUTIVE_SUMMARY.md`, `work/TRIAGE_FINDINGS_BUGS_P0_P1.md`.
- Schemas: `src/doctrine/schemas/procedure.schema.yaml`, `tactic.schema.yaml`. Use canonical templates — do not improvise structure (C-002).
- Depends on WP01/WP02 (settled glossary + architecture layout to reference).
- NOTE: the `work/` traces cited here predate the 2026-06-09 tracker cleanup — re-verify referenced tickets/epics against the live tracker at claim time.

## Subtasks
### T014 — Procedure: tracker-organisation workflow
Author the procedure: inventory → classify roots (functional/meta/orphan/closed) → drain closed epics / collapse passthrough tiers / relabel meta-trackers → re-slice catch-alls into buckets → sweep + scope-read + flag overlaps → dedup (community-precedence) → enforce hygiene invariants → verify. Schema-valid.
### T015 — Tactic: iterative-deepening review
Author the tactic: widening time windows (3-day → week → fortnight → month → close-out); batched parent lookups; flag emergent groupings → make epics before the next ring.
### T016 — Tactic: MoSCoW prioritisation
Author the MoSCoW *approach* as a scoping lens, **explicitly distinct from the `priority:Px` label taxonomy** (when each applies).

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json`.

## Ownership & out-of-map edits
Owned: `src/doctrine/{procedures,tactics}/**`. **Out-of-map edits allowed with a recorded one-line rationale** (e.g. a DRG hint — but the graph itself is WP10).

## Review / Sign-off (R-07)
Doctrine sign-off (curator) + reviewer profile. **architect-alphonso advisory** where the procedure encodes architecture-adjacent conventions.

## Definition of Done
- Procedure + 2 tactics authored, schema-valid (`spec-kitty doctor doctrine --json` healthy), terminology guard passes, referencing the settled glossary/architecture surfaces.

## Risks
- Terminology guard on prose ("Feature"/"features"); DRG must be regenerated after (WP10).

## Activity Log

- 2026-06-11T15:28:08Z – claude:opus:tbd:implementer – shell_pid=822589 – Assigned agent via action command
- 2026-06-11T15:36:23Z – claude:opus:tbd:implementer – shell_pid=822589 – Moved to for_review
- 2026-06-11T15:37:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=852587 – Started review via action command
- 2026-06-11T15:43:34Z – user – shell_pid=852587 – Review passed: 9-step tracker-organisation procedure + iterative-deepening-review & moscow-scoping-lens tactics all schema-valid (doctrine validate OK x3, doctor doctrine profile_health healthy 17/17). Content fidelity verified against work/TRACKER_DOCTRINE_NOTES.md + spec FR-001/FR-002 + WP01 planning-and-tracking glossary: meta-trackers reference-only (never canonical parents), functional epics own work, community-precedence migrates evidence BEFORE closing, passthrough-tier collapse, MoSCoW scoping lens crisply distinct from priority:Px ('translate, don't conflate'). graph.yaml additive-only (+3 nodes +6 edges, zero removals); all references resolve (issue-triage-state-machine procedure exists). Gates green: doctrine 2149 passed, DRG 77 passed, terminology guard 2 passed, graph freshness 5 passed, tactic-compliance 4 passed (root-level refs retained, no info lost). 'Feature' appears only as annotated GitHub issue-type enum. Steps non-contradictory (drain-closed corrects the no-orphan invariant). NOTE: WP05/lane-e independently regenerated graph.yaml -> integration-time re-regen required at merge.

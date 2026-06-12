---
work_package_id: WP10
title: Built-in DRG + profile re-curation
dependencies:
- WP04
- WP05
- WP09
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "909980"
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: curator-carla
authoritative_surface: src/doctrine/agent_profiles/
execution_mode: code_change
owned_files:
- src/doctrine/graph.yaml
- src/doctrine/agent_profiles/built-in/**
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load curator-carla`.

## Objective
Sanitize and re-curate the **built-in DRG and agent profiles** (FR-009, R-09): fold the new doctrine artefacts (WP04/WP05) into `graph.yaml` as nodes/edges, and prune stale/duplicate edges + dead profiles — so the graph reflects the consolidated doctrine (C-005: one coherent graph).

## Context
- Depends on WP04/WP05 (the new procedure/tactics/styleguide/toolguide must exist to be graphed) and WP09 (the regeneration command + symmetric detection).
- Owns the committed `src/doctrine/graph.yaml` and `src/doctrine/agent_profiles/built-in/**`.
- PROVENANCE STATUS (updated): the declared `provenance: str | None` field on `DRGNode`/`DRGEdge` **has shipped** (mission 01KTRC04; `_tag_source` returns `model_copy(update=...)` — no `object.__setattr__` sidecar exists or needs to be created). The `graph.yaml` extractor excludes this field — the committed `graph.yaml` format is unaffected. Do NOT attempt to add or recreate a provenance sidecar.

## Subtasks
### T029 — Add new artefacts to the DRG
Regenerate `graph.yaml` (via WP09's command) so the new doctrine artefacts appear as nodes with correct edges (`requires`/`suggests`/`specializes_from` as applicable).
### T030 — Prune stale/duplicate
Remove dead/duplicate edges and obsolete profiles; **drop no valid edge silently** — record removals with rationale.
### T031 — Validate
`spec-kitty doctor doctrine --json` healthy (no skipped profiles); freshness gate green.

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json`.

## Ownership & out-of-map edits
Owned: `src/doctrine/graph.yaml`, `src/doctrine/agent_profiles/built-in/**`. **Out-of-map edits allowed with a recorded one-line rationale.**

## Review / Sign-off (R-07)
Doctrine sign-off (curator) + reviewer profile; reviewer verifies no valid edge dropped + doctor healthy.

## Definition of Done
- New artefacts graphed; stale/duplicate pruned (rationale recorded); `doctor doctrine` healthy; freshness gate green.

## Risks
- Dropping a valid edge/profile — diff the graph before/after; record every removal.

## Activity Log

- 2026-06-11T15:44:35Z – claude:opus:tbd:implementer – shell_pid=874911 – Assigned agent via action command
- 2026-06-11T15:52:59Z – claude:opus:tbd:implementer – shell_pid=874911 – Moved to for_review
- 2026-06-11T18:46:22Z – claude:opus:reviewer-renata:reviewer – shell_pid=909980 – Started review via action command
- 2026-06-11T18:53:36Z – user – shell_pid=909980 – Review passed (reviewer-renata): Extractor blind-spot CONFIRMED (extractor.py walks references on directive/tactic/paradigm/procedure/agent_profile only, L204-428; styleguide/toolguide node-only at L559-577) — procedure-side fix is correct extractor-respecting shape (procedure->styleguide/toolguide => suggests). Graph delta: 0 nodes, +2 edges (the 2 intended suggests edges), ZERO removals/duplicates; regen byte-identical to committed (idempotent). Parent 29 orphans; WP10 wired the 2 WP05 orphans, leaving 27 pre-existing legacy orphans (out of scope). All 5 mission artifacts have >=1 edge. No sidecar/provenance touched. doctor doctrine healthy 17/17. Gates: doctrine 2161 pass, freshness/shipped-graph/profile-edge 486 pass, terminology 2 pass, doctrine validate OK, edge targets exist. FOLLOW-UP (non-blocking): extractor styleguide/toolguide reference-walk gap is ticket-worthy. Pre-existing (non-WP10) failure: test_example_round_trip charter-extends-and-drg-regen.md MISSING_FRONTMATTER reproduces on WP10 base (planning seed). Note: unstaged a stray non-WP10 mutants/test-feature-01KPN869 artifact to clear the move gate.

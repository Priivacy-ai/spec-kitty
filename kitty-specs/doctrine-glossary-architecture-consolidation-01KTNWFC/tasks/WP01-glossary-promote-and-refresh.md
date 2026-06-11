---
work_package_id: WP01
title: 'Glossary: promote to top-level + content refresh'
dependencies: []
requirement_refs:
- FR-005
- FR-010
- FR-011
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T021
- T022
agent: claude
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: curator-carla
authoritative_surface: glossary/
execution_mode: code_change
owned_files:
- glossary/**
- .kittify/glossaries/**
- src/glossary/scope.py
- src/glossary/seed_validation.py
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: run `/ad-hoc-profile-load curator-carla` (or `spec-kitty.profile-context --profile curator-carla`). Adopt its identity, boundaries, and initialization declaration for this WP.

## Objective

Make `glossary/` the **single canonical source of truth** (C-005, R-01): consolidate the scattered glossary locations into a top-level `glossary/` surface, update all code/path references, and refresh the glossary **content** for the new epic landscape + architectural direction. Record the runtime-`GlossaryScope` promotion as an explicit **defer** (FR-011, #1418).

## Context

- Decisions: `research.md` R-01 (promote glossary), R-08 (content now / scope defer), C-005 (no parallel mechanisms). This WP is **bulk_edit** — the path rewrites are governed by `occurrence_map.yaml` (glossary section); finalize that section as part of T001.
- Today glossary lives across `architecture/glossary/`, `.kittify/glossaries/`, and is loaded via `src/glossary/scope.py` (`GlossaryScope` enum → `<scope>.yaml`). Promotion = one canonical top-level `glossary/` (+ `contexts/`).
- `GlossaryScope` enum currently: mission_local / team_domain / audience_domain / spec_kitty_core. Promotion of the planning-and-tracking subset to a runtime scope is **deferred** (record rationale; do not add an enum value here).

## Subtasks

### T001 — Inventory + finalize occurrence map (glossary section)
Enumerate every glossary location and every reference site (charter authority paths, `src/glossary` loader, `.kittify/glossaries`, doctrine/doc cross-links). Fill the `glossary_promotion` move + the relevant categories in `occurrence_map.yaml` (filesystem_paths = rewrite; code_symbols/serialized_keys = review). All 8 categories must carry an explicit action.

### T002 — Move glossary content → top-level `glossary/` (+ `contexts/`)
Hard moves, no stubs. Preserve `contexts/` (charter authority path). Frozen historical glossary snapshots inside `architecture/<version>/` are NOT moved.

### T003 — Update the `GlossaryScope` loader + seed paths
Point `src/glossary/scope.py` / `seed_validation.py` at the canonical `glossary/` location. Keep the scope enum unchanged (FR-011 defer).

### T004 — Rewrite remaining references
`.kittify/glossaries` references + doctrine/doc cross-links to the new paths (coordinate the charter authority-path file with WP02, which owns `.kittify/charter/**`).

### T005 — Validate
`spec-kitty glossary validate glossary/**/*.yaml`; glossary loader tests; `pytest tests/architectural/test_no_legacy_terminology.py`.

### T021 — Refresh glossary content
Update/expand terms for the new epic landscape + architectural direction (Op, meta-tracker, functional epic, triage status, etc. — reconcile with the planning-and-tracking subset). Surfaces lowercase; validate.

### T022 — Record runtime-scope defer (FR-011)
Add an explicit deferral note (rationale: mission runs not tied into tracking concepts yet; reassess under #1418) where the subset is documented.

## Branch Strategy
Plan/merge target: `feat/doctrine-glossary-consolidation-01KTNWFC`. Execution worktree is allocated per the computed lane in `lanes.json` after finalize-tasks; enter the resolved workspace, do not reconstruct paths.

## Ownership & out-of-map edits
Owned: see frontmatter `owned_files`. **Out-of-map edits are permitted when clearly correct — record a one-line rationale in the WP history/PR for each.** The no-overlap rule is the real guard against parallel collisions; the charter authority-path file is owned by WP02 (coordinate, don't both edit).

## Review / Sign-off (R-07)
Doctrine/glossary sign-off + reviewer profile (reviewer-renata). Reviewer verifies: single glossary surface (no second location), validate passes, no dangling refs.

## Definition of Done
- Top-level `glossary/` is the only glossary surface; loader reads it; `glossary validate` + terminology guard pass; content refreshed; FR-011 defer recorded; occurrence_map glossary section finalized; no dangling references.

## Risks
- A missed reference breaks glossary loading or the charter authority path. Mitigate via the occurrence-map inventory + post-move grep.

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
base_branch: kitty/mission-doctrine-glossary-architecture-consolidation-01KTNWFC
base_commit: 7e8ba507b05d4a38ba4edf81f11008a583d0bc29
created_at: '2026-06-11T14:50:40.102072+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T021
- T022
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "781423"
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

**RECONCILE** the already-canonical top-level `glossary/` with the residual `architecture/glossary/` pointer content, and **DELETE** the residual (C-005, R-01): the top-level `glossary/` IS the single source of truth — this WP eliminates the parallel pointer surface, not moves content to a new location. Update all code/path references, and refresh the glossary **content** for the new epic landscape + architectural direction. Record the runtime-`GlossaryScope` promotion as an explicit **defer** (FR-011, #1418).

## Context

- Decisions: `research.md` R-01 (glossary top-level canonical), R-08 (content now / scope defer), C-005 (no parallel surfaces). The `architecture/glossary/` directory is a pointer README residual from pre-promotion — deleting it IS the C-005 fix; DO NOT re-fork a second surface. This WP is **standard** — the path rewrites are guided by the reference-rewrite checklist in `occurrence_map.yaml` (glossary section, O1 revert — advisory checklist, not an enforcement gate); finalize that section as part of T001.
- The top-level `glossary/` (+ `contexts/`) already exists as the charter authority path (established in the #1636/01KTB6AN era + 2026-03-10 `glossary/contexts/` promotion). Confirm its presence, then remove the residual `architecture/glossary/` pointer content.
- `GlossaryScope` enum currently: mission_local / team_domain / audience_domain / spec_kitty_core. Promotion of the planning-and-tracking subset to a runtime scope is **deferred** (record rationale; do not add an enum value here).

## Subtasks

### T001 — Inventory + finalize occurrence map (glossary section)
Confirm the canonical top-level `glossary/` surface and enumerate every residual reference site to `architecture/glossary/` (charter authority paths, `src/glossary` loader, `.kittify/glossaries`, doctrine/doc cross-links). Fill the `glossary_reconcile` rewrite + the relevant categories in `occurrence_map.yaml` (filesystem_paths = rewrite; code_symbols/serialized_keys = review). All 8 categories must carry an explicit action. The reference-rewrite checklist in `occurrence_map.yaml` is advisory (O1 revert — not an enforcement gate).

### T002 — Delete residual `architecture/glossary/` pointer content
Delete the `architecture/glossary/` directory (pointer README and any stubs). The canonical top-level `glossary/` (+ `contexts/`) already exists — do not re-fork. Frozen historical glossary snapshots inside `architecture/<version>/` are NOT touched. Rationale: C-005 forbids parallel surfaces; the residual pointer must be removed, not preserved as a redirect.

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
- Top-level `glossary/` is the only glossary surface (residual `architecture/glossary/` pointer content deleted — C-005); loader reads it; `glossary validate` + terminology guard pass; content refreshed; FR-011 defer recorded; occurrence_map glossary section finalized (advisory checklist, O1 revert); no dangling references.

## Risks
- A missed reference breaks glossary loading or the charter authority path. Mitigate via the occurrence-map inventory + post-move grep.

## Activity Log

- 2026-06-11T15:00:59Z – claude – shell_pid=754690 – Glossary reconcile complete: 7/7 subtasks done; residual architecture/glossary pointer deleted; planning-and-tracking context page added; 104 tests green incl. terminology guard; occurrence_map finalize relocated to planning branch. Implementer: curator-carla, lane-a 3c74f7686.
- 2026-06-11T15:01:38Z – claude:opus:reviewer-renata:reviewer – shell_pid=781423 – Started review via action command
- 2026-06-11T15:06:15Z – user – shell_pid=781423 – Review passed (reviewer-renata): single canonical glossary surface — architecture/glossary/ residual deleted (dir gone, zero live inbound links). New glossary/contexts/planning-and-tracking.md 7-term set matches the .yaml seed exactly (no drift); surfaces lowercase; no ceremony/status-writing in new content; 'Feature' = GitHub issue-type proper-noun not Mission domain object. GlossaryScope enum untouched (FR-011 defer recorded in seed header + page, #1418). Lane commit 3c74f7686 has ZERO kitty-specs/ paths; occurrence_map finalize correctly relocated to planning branch (7011a17ae). Gates run: terminology guard 2 passed; glossary suite 197 passed; glossary validate both seeds Valid (7+99 terms); 23 link tests passed. Anti-pattern checklist: doc/deletion/comment only, no production code — dead-code/synthetic-fixture/silent-return N/A; no frozen/MUST-NOT violations; shared architecture/README.md row left to WP02. Issue-matrix resolved: #1418 deferred-with-followup, rest in-mission (later-WP FRs).

---
work_package_id: WP05
title: File bugs + migration manifest (G5, FR-008)
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-006
- FR-008
- C-004
planning_base_branch: kitty/mission-self-doc-gapclose
merge_target_branch: kitty/mission-self-doc-gapclose
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-self-doc-gapclose. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-self-doc-gapclose unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
phase: Phase 1
history:
- timestamp: '2026-08-15T08:10:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: docs/development/
create_intent:
- docs/development/agent-memory-migration-manifest.md
- tests/docs/test_migration_manifest_complete.py
execution_mode: code_change
mission_id: 01M0287XCV1R9VDEXHSDB0RTYR
owned_files:
- docs/development/**
- tests/docs/test_migration_manifest_complete.py
tags: []
tracker_refs: []
wp_code: WP05
---

# Work Package Prompt: WP05 – File bugs + migration manifest (G5, FR-008)

## Objective
File the three behavior-quirk bugs (fixes DEFERRED), and write the committed manifest that is the repo-testable proof of migration.

## Subtasks
- **T014 File bugs** (filing only, no fixing): finalize-tasks-clobbers-issue-matrix; move-task double-increments review-cycle counter; status-daemon auto-commits with previous message. Record issue refs.
- **T015 Manifest.** `docs/development/agent-memory-migration-manifest.md` maps each audited G1–G6 gap-filler (from `work/memory-gap-filler-analysis.md`) → its repo home (file/assertion), its tracking issue, OR an explicit 'behavior retired — delete memory, no repo home' (e.g. shard-registration via #2671). Deletion of the private memory is an operator checklist on #3448, out of mission scope (C-004).
- **T016 Completeness test (real resolution).** `tests/docs/test_migration_manifest_complete.py` derives the G1–G6 gap-filler set from the **section headers in `work/memory-gap-filler-analysis.md`** (not an inline literal that could be trimmed to match), asserts each appears in the manifest with a resolution, and — for `home:` resolutions — asserts the referenced path exists on disk. Structure-only presence is insufficient.

## Done
SC-005: manifest complete; every gap-filler resolved (home / issue / retired).
- **T017 Freshness (the manifest is an inventoried page).** `docs/development/*.md` is inventoried + DocFX-published, so after the manifest lands, regenerate both rollups (`inventory_lockfile.py --write`) and confirm `check_docs_freshness --ci` errors=0 (frontmatter, description 50–180 chars, registration). WP05 owns `docs/development/**` so it holds the authority; this runs last (after WP04's regen).

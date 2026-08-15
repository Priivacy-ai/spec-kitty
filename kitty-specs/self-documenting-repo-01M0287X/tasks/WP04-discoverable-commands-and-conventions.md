---
work_package_id: WP04
title: Discoverable commands + env/tracker docs (G4, G6)
dependencies:
- WP03
requirement_refs:
- FR-005
- FR-007
- C-003
- NFR-001
planning_base_branch: kitty/mission-self-doc-gapclose
merge_target_branch: kitty/mission-self-doc-gapclose
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-self-doc-gapclose. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-self-doc-gapclose unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
phase: Phase 1
history:
- timestamp: '2026-08-15T08:10:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: docs/development/
execution_mode: code_change
mission_id: 01M0287XCV1R9VDEXHSDB0RTYR
owned_files:
- docs/development/3-2-page-inventory.yaml
- docs/development/3-2-docs-retrieval-index.yaml
tags: []
tracker_refs: []
wp_code: WP04
---

# Work Package Prompt: WP04 – Discoverable commands + env/tracker docs (G4, G6)

## Objective
Make repo-owned workflow commands discoverable + document env/tracker conventions. Depends on WP03 to serialize the shared generated-yaml regen.

## Subtasks
- **T011 Commands.** Document docs-inventory freshen (`scripts/docs/inventory_lockfile.py --write`) + the mission wrap-up sequence (DIRECTIVE_046) in `docs/development/**`. Reference #3447 for asset/prompt regen — do NOT duplicate its entrypoint (C-003).
- **T012 Conventions.** Document env gotchas (pyenv-editable-shadows-pipx; `.git/hooks/pre-commit` interpreter pin) in dev-setup docs, and tracker conventions (retired `bug` label → native issue type; `tension`/`opposed_by` edges) in contributing docs.
- **T013 Regenerate rollups** (serialized after WP03); `check_docs_freshness --ci` errors=0.

## Done
Fresh reader finds all four command/convention topics from docs alone; docs-freshness errors=0.

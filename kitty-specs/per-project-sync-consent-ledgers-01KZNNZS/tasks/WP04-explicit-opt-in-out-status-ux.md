---
work_package_id: WP04
title: Explicit opt-in/out/status UX
dependencies:
- WP01
- WP02
requirement_refs:
- FR-006
- FR-007
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 4 - UX and status
history:
- timestamp: '2026-08-10T11:25:00Z'
  agent: codex
  action: Prompt generated via mission task materialization
authoritative_surface: src/
create_intent:
- docs/sync.md
- tests/cli/commands/test_sync_project_consent_3262.py
- tests/sync/test_sync_status_project_consent_3262.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- docs/sync.md
- tests/cli/commands/test_sync_project_consent_3262.py
- tests/sync/test_sync_status_project_consent_3262.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – Explicit opt-in/out/status UX

Expose project-scoped consent to users with clear opt-in, opt-out, status,
doctor/routes, and documentation language.

## Requirements

- FR-006, FR-007, FR-014
- Plan concern: IC-04

## Acceptance

- Users can explicitly opt one project in and later opt it out.
- Status/doctor output is concise and project-scoped.
- Docs never describe the global env flag as consent.

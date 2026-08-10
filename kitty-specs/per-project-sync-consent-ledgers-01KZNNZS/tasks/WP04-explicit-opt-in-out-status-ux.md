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

## Implementation evidence — 2026-08-10

Current origin HEAD already implements the WP04 UX/status invariant:

- `src/specify_cli/cli/commands/sync.py` exposes explicit `sync opt-in` and
  `sync opt-out` commands and renders per-project consent state in `sync status`
  / `sync doctor`.
- Status/doctor surfaces distinguish unreadable/undetermined consent from a
  missing record and tell the operator not to re-record consent for readability
  faults.
- Existing output text treats `SPEC_KITTY_ENABLE_SAAS_SYNC` as a rollout/status
  preflight flag, not as a project consent grant.

Focused validation:

```bash
SPEC_KITTY_NO_UPGRADE_CHECK=1 env -u SPEC_KITTY_ENABLE_SAAS_SYNC \
  uv run --group dev --extra test pytest \
  tests/cli/commands/test_sync_commands.py \
  tests/cli/commands/test_sync_doctor_consent_health_3030.py \
  tests/cli/commands/test_sync_report_label_is_a_purge_selector_3030.py \
  tests/sync/test_sync_status_command.py \
  tests/cli/commands/test_sync_migrate_backfills_h4.py -q
```

Result: `67 passed in 49.87s`.

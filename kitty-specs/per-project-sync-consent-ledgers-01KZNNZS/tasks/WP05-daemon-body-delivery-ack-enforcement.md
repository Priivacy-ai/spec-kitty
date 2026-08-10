---
work_package_id: WP05
title: Daemon, body-upload, delivery, and ack enforcement
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
- FR-005
- FR-009
- FR-012
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 5 - Runtime enforcement
history:
- timestamp: '2026-08-10T11:25:00Z'
  agent: codex
  action: Prompt generated via mission task materialization
authoritative_surface: src/
create_intent:
- tests/delivery/test_dispatch_project_consent_3262.py
- tests/sync/test_body_upload_project_consent_3262.py
- tests/sync/test_background_project_consent_3262.py
execution_mode: code_change
owned_files:
- src/specify_cli/delivery/dispatcher.py
- src/specify_cli/delivery/retention.py
- src/specify_cli/sync/background.py
- src/specify_cli/sync/body_upload.py
- src/specify_cli/sync/body_transport.py
- src/specify_cli/sync/history_import/upload.py
- tests/delivery/test_dispatch_project_consent_3262.py
- tests/sync/test_body_upload_project_consent_3262.py
- tests/sync/test_background_project_consent_3262.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 – Daemon, body-upload, delivery, and ack enforcement

Wire every runtime egress path through row/task project consent: background
daemon drain, body upload, history import upload, SaaS client send wrappers,
old-client/bypass seams, acknowledgement, purge, and retention.

## Requirements

- FR-004, FR-005, FR-009, FR-012, FR-013
- Plan concern: IC-05

## Acceptance

- Non-consenting projects are refused in daemon/body/background paths.
- Refused rows are not acknowledged or purged as success.
- Lower-level bypass seams fail closed.

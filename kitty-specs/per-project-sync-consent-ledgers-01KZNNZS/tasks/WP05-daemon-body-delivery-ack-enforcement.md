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

## Implementation evidence

- Runtime enforcement was already present in the #3030 remediation surface; this WP records closure evidence rather than adding duplicate source churn.
- Focused validation on 2026-08-10:
  - `SPEC_KITTY_NO_UPGRADE_CHECK=1 env -u SPEC_KITTY_ENABLE_SAAS_SYNC SPEC_KITTY_TEST_DB_NAME=test_per_project_sync_consent_ledgers_01KZNNZS_lane_e uv run --group dev --extra test pytest tests/delivery/test_dispatch_project_consent_3030.py tests/delivery/test_dispatch_window_consent_3030.py tests/delivery/test_cross_project_refusal_state_3030.py tests/delivery/test_dispatch_honours_drain_blocked_3031.py tests/delivery/test_body_queue_purge_differential_3030.py tests/sync/test_body_upload_consent_3030.py tests/sync/test_body_drain_consent_3030.py tests/sync/test_no_queue_drain_constructed_3030.py tests/sync/test_background_body.py tests/sync/test_background_auth_backoff_3030.py tests/sync/test_daemon_publish_consent_3030.py tests/sync/test_history_import_consent_3030.py tests/sync/tracker/test_saas_client_consent_gate_3030.py tests/specify_cli/saas_client/test_client_consent_gate_3030.py -q`
  - Result: `132 passed in 54.09s`.
- The create-intent #3262 filenames remain planned closure labels, but the existing #3030 regression files are the canonical runtime pins for the same incident paths: dispatcher selection/window/refusal state, body queue upload/drain, daemon publish, history import upload, and lower-level SaaS client wrappers.

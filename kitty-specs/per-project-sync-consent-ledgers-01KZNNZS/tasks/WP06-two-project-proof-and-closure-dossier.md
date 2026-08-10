---
work_package_id: WP06
title: Two-project proof and closure dossier
dependencies:
- WP05
requirement_refs:
- FR-013
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
phase: Phase 6 - Evidence
history:
- timestamp: '2026-08-10T11:25:00Z'
  agent: codex
  action: Prompt generated via mission task materialization
authoritative_surface: docs/
create_intent:
- docs/runbooks/hosted-sync-consent-incident.md
execution_mode: code_change
owned_files:
- docs/runbooks/hosted-sync-consent-incident.md
tags: []
tracker_refs: []
---

# Work Package Prompt: WP06 – Two-project proof and closure dossier

Collect final evidence and make the closure boundary explicit. This WP supports
#3262 closure and #585 remediation planning; it does not close #585 unless the
historical 1,322-event disposition is approved.

## Requirements

- FR-013, FR-015
- Plan concern: IC-06

## Acceptance

- Two-project end-to-end proof covers interactive, daemon, body upload, and ack.
- `issue-matrix.json` maps every FR/SC to tests and PR evidence.
- Closure dossier and runbook document prevention versus historical remediation.

## Implementation evidence

- Added `docs/runbooks/hosted-sync-consent-incident.md` to document operator rules, closure procedure, proof anchors, and reopening triggers.
- Updated the closure dossier to mark prevention evidence complete while preserving the #585 historical-remediation boundary.
- Focused validation on 2026-08-10:
  - `SPEC_KITTY_NO_UPGRADE_CHECK=1 env -u SPEC_KITTY_ENABLE_SAAS_SYNC SPEC_KITTY_TEST_DB_NAME=test_per_project_sync_consent_ledgers_01KZNNZS_lane_f uv run --group dev --extra test pytest tests/delivery/test_incident_reproduction_3030.py tests/delivery/test_liveness_predicate_before_limit_3030.py tests/delivery/test_cross_project_refusal_state_3030.py tests/delivery/test_body_queue_purge_differential_3030.py tests/sync/test_body_drain_consent_3030.py tests/sync/test_daemon_publish_consent_3030.py tests/sync/test_history_import_consent_3030.py tests/sync/tracker/test_saas_client_consent_gate_3030.py tests/specify_cli/saas_client/test_client_consent_gate_3030.py tests/cli/commands/test_sync_status_per_project_3030.py tests/cli/commands/test_sync_purge_3030.py -q`
  - Result: `126 passed in 54.12s`.

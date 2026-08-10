---
title: Hosted Sync Consent Incident Runbook
description: 'How to verify per-project hosted sync consent prevention while keeping SaaS #585 historical remediation separate.'
doc_status: active
updated: '2026-08-10'
type: runbook
related:
- docs/guides/accept-and-merge.md
- docs/development/red-main-and-release-readiness.md
- docs/api/environment-variables.md
---

# Hosted sync consent incident runbook

This runbook separates the prevention closure for core #3262 from the historical
remediation still required for SaaS #585.

## Incident boundary

- Core #3262 is the prevention class: hosted sync must be explicitly opted in per
  project, and every retained row, body upload, daemon path, delivery attempt,
  acknowledgement, and purge selector must be scoped to the project that owns the
  data.
- SaaS #585 is the historical incident: 1,322 events from five non-consenting
  projects were already delivered alongside the intended opted-in project. This
  runbook does not declare those delivered events remediated.
- Closing #3262 is allowed only when prevention evidence is present. Closing #585
  also requires an approved disposition for the already-delivered 1,322 events.

## Operator rules

1. Treat `SPEC_KITTY_ENABLE_SAAS_SYNC` as rollout arming only. It never grants a
   project consent to egress.
2. Absence of a project consent record is denial.
3. Rows whose project ownership cannot be resolved remain local-only until
   ownership is proven or an operator explicitly purges them.
4. Do not use a real operator queue for closure proof. Set an isolated
   `SPEC_KITTY_HOME` and leave hosted SaaS sync unexported unless the test itself
   patches the rollout surface.
5. Refusal is not success: a refused row or task must not be acknowledged,
   purged, or counted as delivered.

## Prevention evidence checklist

| Evidence | Proof anchor |
| --- | --- |
| Default-deny consent resolver | `tests/sync/test_consent_resolver_3030.py` |
| Rollout flag cannot grant consent | `tests/cli/commands/test_sync_commands.py`, `tests/sync/test_dossier_trigger.py` |
| Per-project journal/ledger selection | `tests/delivery/test_dispatch_project_consent_3030.py`, `tests/delivery/test_consented_batch_3030.py` |
| Multi-project incident reproduction | `tests/delivery/test_incident_reproduction_3030.py` |
| Predicate before delivery window/limit | `tests/delivery/test_liveness_predicate_before_limit_3030.py` |
| Refusals do not destroy consented data | `tests/delivery/test_cross_project_refusal_state_3030.py` |
| Body upload and daemon enforcement | `tests/sync/test_body_drain_consent_3030.py`, `tests/sync/test_daemon_publish_consent_3030.py` |
| Lower-level SaaS client fail-closed seam | `tests/specify_cli/saas_client/test_client_consent_gate_3030.py`, `tests/sync/tracker/test_saas_client_consent_gate_3030.py` |
| Operator visibility and purge selectors | `tests/cli/commands/test_sync_status_per_project_3030.py`, `tests/cli/commands/test_sync_purge_3030.py` |

## Closure procedure

1. Confirm the prevention PR contains the Spec Kitty mission artifacts:
   `spec.md`, `plan.md`, `tasks.md`, `analysis-report.md`, `issue-matrix.json`,
   and this runbook.
2. Run the focused closure proof from an isolated checkout:

   ```bash
   SPEC_KITTY_NO_UPGRADE_CHECK=1 \
   env -u SPEC_KITTY_ENABLE_SAAS_SYNC \
   SPEC_KITTY_TEST_DB_NAME=test_per_project_sync_consent_ledgers_01KZNNZS_lane_f \
   uv run --group dev --extra test pytest \
     tests/delivery/test_incident_reproduction_3030.py \
     tests/delivery/test_liveness_predicate_before_limit_3030.py \
     tests/delivery/test_cross_project_refusal_state_3030.py \
     tests/delivery/test_body_queue_purge_differential_3030.py \
     tests/sync/test_body_drain_consent_3030.py \
     tests/sync/test_daemon_publish_consent_3030.py \
     tests/sync/test_history_import_consent_3030.py \
     tests/sync/tracker/test_saas_client_consent_gate_3030.py \
     tests/specify_cli/saas_client/test_client_consent_gate_3030.py \
     tests/cli/commands/test_sync_status_per_project_3030.py \
     tests/cli/commands/test_sync_purge_3030.py \
     -q
   ```

3. Attach the result to the mission closure dossier and PR.
4. For core #3262, cite the prevention PR and the focused proof result.
5. For SaaS #585, do not close until the historical 1,322-event disposition is
   approved. Acceptable dispositions include documented deletion, tenant/customer
   notification, legal sign-off, or a written decision that no further
   remediation is required.

## Reopening triggers

Reopen or block closure if any of these are observed:

- A non-consenting project can send a journal row, body upload, daemon publish,
  history import upload, tracker request, or SaaS client request.
- A refused row is acknowledged or purged as if delivered.
- A status or doctor command reports a project as healthy based only on global
  rollout arming.
- The #585 historical events are treated as remediated without an approved
  disposition.

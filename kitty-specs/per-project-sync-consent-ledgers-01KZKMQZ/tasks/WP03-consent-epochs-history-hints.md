---
work_package_id: WP03
title: Sole consent writer, sequence epochs, deny hints, and history capability
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-011
- FR-017
- FR-021
- FR-022
- FR-023
- FR-028
- FR-032
- NFR-004
- NFR-007
- C-002
- C-003
- C-009
planning_base_branch: feat/per-project-sync-consent
merge_target_branch: feat/per-project-sync-consent
branch_strategy: Planning artifacts for this mission were generated on feat/per-project-sync-consent. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/per-project-sync-consent unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/consent.py
create_intent:
- src/specify_cli/sync/history_disclosure.py
- src/specify_cli/sync/deny_hints.py
- tests/sync/test_project_consent_authority.py
- tests/sync/test_consent_epochs.py
- tests/sync/test_history_disclosure.py
- tests/sync/test_daemon_deny_hints.py
- tests/sync/test_legacy_grant_writers.py
- tests/architectural/test_sync_writer_census.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/consent.py
- src/specify_cli/sync/config.py
- src/specify_cli/sync/routing.py
- src/specify_cli/sync/history_disclosure.py
- src/specify_cli/sync/deny_hints.py
- tests/sync/test_project_consent_authority.py
- tests/sync/test_consent_epochs.py
- tests/sync/test_history_disclosure.py
- tests/sync/test_daemon_deny_hints.py
- tests/sync/test_legacy_grant_writers.py
- tests/sync/test_consent_resolver_3030.py
- tests/sync/test_consent_write_refusal_3030.py
- tests/architectural/test_egress_consent_boundary.py
- tests/architectural/test_sync_writer_census.py
role: implementer
tags: []
tracker_refs:
- Priivacy-ai/spec-kitty#3262
---

## ⚡ Do This First: Load Agent Profile

Load the assigned implementation profile before inspecting the worktree:

```text
/ad-hoc-profile-load python-pedro
```

Read the spec's User Stories 2, 3, and 5, research Decisions 2, 3, and 7, the data-model sections for ProjectConsentDecision/ConsentEpoch/DaemonDenyHint, and WP01's grant-writer census.

## Objective

Make one versioned record in the UUID-owned store the sole local hosted-sync grant authority. Allow local capture without hosted disclosure by assigning monotonic capture sequences to explicit epochs. Make sealed-history disclosure an immutable, previewed, confirmed action. Give the daemon a physical hint that can suppress work but can never grant.

## Authority rules

Absence denies. Only explicit project opt-in writes `granted`; explicit opt-out writes `refused`; migration may import an explicit refusal only. Login, host URL, target readiness, repository slug/default, checkout record, remote, machine index, environment, discovery, store existence, and legacy grant do not grant.

`SPEC_KITTY_ENABLE_SAAS_SYNC` is a deny-only egress switch. Opt-in must persist locally while it is false or offline, with remote admission separately pending. Opt-out seals eligibility but does not purge captured data.

## Subtask T011 — Collapse to one consent writer

Refactor `consent.py` to read/write ProjectConsentDecision only through ProjectSyncStore. Preserve a typed diagnostic vocabulary for absent, granted, refused, unreadable, and incompatible states. Delete or hard-fail alternate grant resolution branches rather than maintaining parity fallbacks.

The explicit writer must record action, actor/provenance, UTC timestamp, schema version, idempotency identity, and monotonic generation. Same-action retry is idempotent; a later opposite action advances generation. A legacy refusal may create `migrated_refusal`; a legacy grant stays absent/denied.

Keep the public API narrow. Bulk/machine writers must not remain a hidden grant surface.

## Subtask T012 — Capture sequence and consent epochs

Implement store-local monotonic capture allocation in the same transaction as epoch assignment. Initial denied capture uses `capture_only`. Opt-in atomically observes the inclusive current tail and opens a new eligible epoch whose ordinary candidates have sequence strictly greater than that tail. Opt-out seals the current epoch and advances the decision generation without deleting rows.

Test both transaction orderings around capture-versus-opt-in. A capture committed at or below the recorded tail stays sealed; one committed strictly after the new epoch opens belongs only to that epoch. Target change and re-opt-in never relabel older rows.

## Subtask T013 — Immutable history disclosure capability

Create `history_disclosure.py`. Preview computes exact stable row IDs, count, content-hash aggregate, and source epoch set without granting eligibility. Confirmation persists actor, operation/idempotency key, preview identity, and current consent/target/admission generations.

Consumption must revalidate the immutable cohort and unchanged authority. Ordinary selection cannot create or consume this capability. Purged/terminal rows cannot be resurrected. Any mismatch, stale preview, or uncertain operation fails closed with actionable diagnostics.

Do not implement automatic history redrain or inspect the 1,322 historical SaaS events; this capability is local core state only.

## Subtask T014 — Narrowing-only deny hints

Create one atomically replaced JSON hint per canonical UUID under `projects/.deny-hints/`. The schema can represent only deny/revoke, authority generation, expiration, reason category, layout version, and integrity checksum—never a grant.

Publish deny/revoke only after the store transaction commits; remove the hint only after opt-in commits. Missing, expired, malformed, generation-mismatched, pending, or possibly granted state requires an authoritative store read. A stale deny may delay liveness and must appear in diagnostics, but it cannot disclose payload or credentials.

Directory enumeration must not create stores or decisions.

## Subtask T015 — Retire legacy grant writers and prove actions

Turn checkout-only/default inheritance, repository-default setters, consent-index backfill, and other census entries into removed APIs or non-zero migration guidance. They create no grant, even when environment/login/target values are favorable.

Because WP10 owns the large CLI command module, expose typed service results and
migration-guidance errors here; WP10 will wire final command behavior without
duplicating authority. Preserve read-only legacy diagnostics where necessary and
clearly label them non-authoritative.

Write public-routing tests for offline opt-in, kill-switch-off opt-in, opt-out sealing, idempotent retry, re-opt-in, and all implicit input combinations.

## Branch Strategy

Start through `spec-kitty agent action implement WP03 --agent <name>` after WP02 approval. Use only the allocated lane. Planning base and merge target are `feat/per-project-sync-consent`. Do not publish, deploy, or mutate production.

## Test strategy

Commit the implicit-grant matrix and capture-tail ordering test red-first. Run all five owned test files plus existing #3030 consent resolver/write-refusal tests. Run strict typing and ruff on touched files. Inject mutants for environment grant, repo-default grant, history selection without capability, and a grant-valued daemon hint.

## Definition of Done

- One project-store action is the only callable local grant writer.
- Capture sequences/epochs have deterministic transactional order.
- Opt-in never retroactively includes history; opt-out never silently purges.
- History disclosure requires immutable preview and confirmation.
- Deny hints have no grant state and unknown state opens authority.
- Every legacy grant flag/path fails non-zero or is removed with tests.

## Risks and reviewer guidance

Reviewers must search for all former writer symbols and direct config mutation, not only exercise the happy path. Verify the kill switch can suppress but never grant/delete. Race captures against opt-in repeatedly under real SQLite. Corrupt/stale hint tests must fail closed without payload access. Reject a history boolean or request flag that bypasses the persisted capability.

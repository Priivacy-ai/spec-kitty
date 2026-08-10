# Implementation Plan: Per-project sync consent ledgers

**Branch**: `feat/per-project-sync-consent` | **Date**: 2026-08-10 | **Spec**: `kitty-specs/per-project-sync-consent-ledgers-01KZNNZS/spec.md`  
**Input**: Core #3262 and SaaS #585 require a structural consent redesign, not another caller-local guard.

## Summary

Implement #3262 by making hosted sync consent and sync state project-scoped end to end. The existing #3030 work already introduced project identity, consent decisions, `ConsentedBatch`, and architectural guards against unfiltered egress. This mission finishes the redesign by moving remaining shared-state assumptions behind project-owned ledgers and by proving every interactive, daemon, body-upload, old-client, and acknowledgement path asks the event/task’s own project authority rather than the current checkout or machine-global environment.

The implementation is deliberately decomposed into PR-ready work packages:

1. Define one canonical project consent/ledger authority.
2. Migrate shared journal/offline/body state into project-scoped ledgers without silently admitting historical data.
3. Wire explicit opt-in/opt-out/status surfaces to that authority.
4. Enforce per-project selection/transmit/acknowledgement for interactive and daemon delivery.
5. Prove old-client/bypassed-gate refusal and two-project isolation.
6. Produce closure/remediation evidence for #3262/#585 while keeping #3135 separate.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer CLI, SQLite local stores, Spec Kitty event journal/delivery stack, `spec-kitty-tracker` SaaS client interfaces  
**Storage**: Local SQLite files under `~/.spec-kitty/` and project `.kittify/` config; event journal, delivery ledger, offline queue, body-upload queue  
**Testing**: pytest unit/integration/architectural tests under `tests/sync`, `tests/delivery`, `tests/event_journal`, `tests/cli/commands`, and `tests/architectural`  
**Target Platform**: Local CLI on macOS/Linux/Windows-compatible filesystem paths  
**Project Type**: Python CLI/library  
**Performance Goals**: Preserve existing status/doctor performance envelope; avoid full-journal scans on hot selection paths where project-indexed predicates already exist  
**Constraints**: Fail closed; no default-on; no global env-as-consent; no destructive purge of historical state during migration; #585 not closed without remediation disposition  
**Scale/Scope**: Multi-project developer machine with hundreds/thousands of local retained events and body uploads, including legacy rows predating #3030 identity columns

## Current Architecture Notes

- `src/specify_cli/sync/consent.py` is the current consent resolver. It still has three levels: project-local, machine UUID index, and `ENV`. #3262 requires removing or demoting env as a grant source so it can only deny/disable.
- `src/specify_cli/event_journal/` owns retained event rows and already has project identity columns and reporting helpers.
- `src/specify_cli/delivery/consent_gate.py`, `selection.py`, `dispatcher.py`, `ledger.py`, and `retention.py` own consented batch construction, selection, delivery ledger, acknowledgement, and purge/report behavior.
- `src/specify_cli/sync/body_queue.py`, `body_upload.py`, `background.py`, and `dossier_pipeline.py` own body upload preparation and daemon/background drains; these must use the same project consent predicate as event delivery.
- `src/specify_cli/sync/routing.py` still exposes `is_sync_enabled_for_checkout()`. This can remain as compatibility/readiness sugar, but must not be authoritative for egress.
- Existing tests named `*_3030.py`, `*_3108.py`, and architectural guards are valuable regression anchors and should be extended rather than bypassed.

## Charter Check

No charter exception is planned.

- **Architectural integrity**: one consent/ledger authority; no ad hoc predicates.
- **Specification fidelity**: all acceptance criteria trace back to #3262/#585 rows in the spec.
- **Locality of change**: changes stay in sync/delivery/event_journal/CLI docs/tests unless evidence demands otherwise.
- **Test-first development**: each WP starts from a red fixture around the missing #3262 behavior.
- **Black-box integration testing**: at least one real two-project fixture must drive CLI-facing selection/daemon behavior, not only unit-level function calls.
- **Living documentation sync**: docs/runbooks and issue evidence must be updated with shipped behavior and remaining historical-remediation disposition.

## Project Structure

### Documentation and mission artifacts

```
kitty-specs/per-project-sync-consent-ledgers-01KZNNZS/
├── spec.md
├── plan.md
├── tasks.md
├── wps.yaml
├── issue-matrix.json
├── quickstart.md
├── data-model.md
├── contracts/
└── tasks/
```

### Source/test surfaces

```
src/specify_cli/
├── sync/
│   ├── consent.py
│   ├── routing.py
│   ├── queue.py
│   ├── body_queue.py
│   ├── body_upload.py
│   ├── background.py
│   ├── migrate_journal.py
│   └── cli command integrations
├── event_journal/
│   ├── journal.py
│   ├── models.py
│   └── coalesce.py
├── delivery/
│   ├── consent_gate.py
│   ├── selection.py
│   ├── dispatcher.py
│   ├── ledger.py
│   ├── retention.py
│   └── status_report.py
└── cli/commands/sync.py

tests/
├── sync/
├── delivery/
├── event_journal/
├── cli/commands/
└── architectural/
```

**Structure Decision**: Implement as a single core CLI mission. SaaS #585 remains an evidence/closure consumer, not an implementation target in this repository. Core PR #3135 is explicitly out of scope and must be repaired separately.

## Implementation Concern Map

### IC-01 — Canonical project consent authority

- **Purpose**: Make “may this project egress?” answerable by exactly one explicit project-scoped authority.
- **Relevant requirements**: FR-001, FR-002, FR-006, FR-007, FR-008, FR-012, C-001, C-002, C-003
- **Affected surfaces**: `sync/consent.py`, `sync/routing.py`, `cli/commands/sync.py`, `tests/sync`, `tests/cli/commands`, architectural consent boundary tests
- **Sequencing/depends-on**: none
- **Risks**: Existing tests may assume `SPEC_KITTY_ENABLE_SAAS_SYNC=1` grants consent. Those tests must be split between rollout-surface enablement and project egress authority.

### IC-02 — Per-project ledger/storage resolver

- **Purpose**: Stop shared machine ledgers from being the unit of selection/acknowledgement by introducing project-scoped journal/offline/body/delivery stores or an equivalent scoped resolver.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-010, FR-011, NFR-003, NFR-004
- **Affected surfaces**: `event_journal/journal.py`, `event_journal/models.py`, `sync/queue.py`, `sync/body_queue.py`, `delivery/ledger.py`, `delivery/selection.py`, `delivery/status_report.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: A purely logical filter may leave shared-store footguns. If physical split is too broad for one PR, the plan must still prove every selector and ack path is project-keyed and document the remaining physical split as not complete.

### IC-03 — Safe migration from shared state

- **Purpose**: Move pre-#3262 rows into per-project ledgers without silently admitting historical projects or dropping ambiguous rows.
- **Relevant requirements**: FR-010, FR-011, NFR-003, NFR-004, NFR-006
- **Affected surfaces**: `sync/migrate_journal.py`, `event_journal` migrations/helpers, `sync purge`, migration tests and fixtures
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: Existing local machine state contains legacy event rows and body uploads. Migration tests must use isolated temp homes and fixture DBs, never the operator’s real `~/.spec-kitty` stores.

### IC-04 — Interactive opt-in/out/status UX

- **Purpose**: Give users an explicit per-project consent surface and make queue/consent state visible before drain.
- **Relevant requirements**: FR-006, FR-007, FR-014, SC-001, SC-006, SC-007
- **Affected surfaces**: `cli/commands/sync.py`, docs/API help text, `sync status`, `sync doctor`, `sync routes`
- **Sequencing/depends-on**: IC-01, partial IC-02
- **Risks**: Wording must avoid implying the global env var is consent. Status output can be long on historical journals; tests should cover concise per-project reporting.

### IC-05 — Delivery, daemon, body-upload, and acknowledgement enforcement

- **Purpose**: Ensure every delivery path filters by the row/task’s own project consent before transmit and before acknowledgement/purge.
- **Relevant requirements**: FR-004, FR-005, FR-009, FR-012, FR-013, NFR-001, NFR-002
- **Affected surfaces**: `delivery/selection.py`, `delivery/dispatcher.py`, `delivery/ledger.py`, `sync/background.py`, `sync/body_upload.py`, `sync/body_transport.py`, `sync/history_import/upload.py`, SaaS client send wrappers
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: Old-client/bypass tests must hit low-level seams, not just CLI commands. Acknowledgement bugs are subtle: a row refused before transmit must not become delivered/terminal-success.

### IC-06 — Evidence, runbook, and issue closure boundary

- **Purpose**: Record what is structurally fixed and what remains a historical remediation decision before #585 can close.
- **Relevant requirements**: FR-015, SC-008, C-004, C-005, C-006
- **Affected surfaces**: `docs/runbooks/`, mission issue matrix, GitHub issue comments for #3262/#585 after PR publication
- **Sequencing/depends-on**: IC-01–IC-05 evidence
- **Risks**: “Prevention shipped” can be mistaken for “incident closed.” The closure artifact must explicitly require disposition of the 1,322 already-delivered events.

## Proposed PR / WP Decomposition

1. **Consent authority PR**: fail default, remove env-as-grant, explicit project opt-in/out model.
2. **Ledger/storage PR**: per-project ledger resolver and selector/ack scoping.
3. **Migration PR**: mixed shared-journal migration and ambiguous-row local-only classification.
4. **Daemon/body PR**: background daemon and body upload enforcement.
5. **Proof/closure PR**: two-project, old-client/bypass, status/doctor evidence, runbook and issue-matrix closure.

Billing, onboarding, and PR #3135 repairs are outside this mission and should not be folded into these PRs.

## Testing Strategy

- Extend existing #3030 tests:
  - `tests/delivery/test_dispatch_project_consent_3030.py`
  - `tests/delivery/test_incident_reproduction_3030.py`
  - `tests/delivery/test_consented_batch_3030.py`
  - `tests/sync/test_capture_gate_project_identity_3030.py`
  - `tests/sync/tracker/test_saas_client_consent_gate_3030.py`
- Add/extend two-project integration tests that use temp homes and two repo roots.
- Add daemon/background tests using fake transports and isolated queue DBs.
- Add migration tests with pre-#3262 mixed journals/body queues.
- Keep/strengthen architectural guards:
  - `tests/architectural/test_egress_consent_boundary.py`
  - `tests/architectural/test_unfiltered_journal_read_boundary.py`
  - tracker egress guard tests.
- Run focused validation per WP plus final broad sync/delivery/architectural suite.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Multiple storage surfaces touched | The incident crosses event journal, offline queue, body upload queue, delivery ledger, daemon, and status surfaces. | Fixing only the CLI command path leaves background/old-client bypasses able to leak. |
| Migration plus new behavior in one mission | #3262 explicitly requires migration from shared state before #585 can close. | Shipping new-project-only behavior would leave existing machines in the incident shape. |

## Deliverables

- Updated core code and tests proving per-project consent/ledger isolation.
- Mission tasks/WP artifacts mapping each concern to reviewable PR slices.
- Closure artifact that states #585 remains open until historical remediation disposition is approved.
- GitHub issue comments linking mission/PR evidence once remote PRs exist.

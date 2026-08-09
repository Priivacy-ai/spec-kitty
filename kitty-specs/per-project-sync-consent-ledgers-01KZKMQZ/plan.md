# Implementation Plan: Per-Project Sync Consent Ledgers

**Branch**: `feat/per-project-sync-consent` | **Date**: 2026-08-09 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/kitty-specs/per-project-sync-consent-ledgers-01KZKMQZ/spec.md`

## Summary

Replace live machine-global sync storage and multi-source granting with one `sync.db` per canonical UUID, opened only through a connection-owning ProjectSyncStore unit of work, and one versioned consent writer. Local capture assigns a monotonic sequence in explicit epochs; opt-in records the inclusive tail, while sealed history requires an immutable preview/confirmation capability. Egress requires current consent/epoch, exact binding audience, per-write admission generation, and a durable transport attempt. Admit/revoke uses a durable operation outbox. Partition legacy state through daemon and current-writer layout-generation participation, read-only logical snapshots, exact verification, and atomic cutover. Opt-out cancels pre-start work, waits for bounded started attempt/result reconciliation, seals without purging, and reports remote revocation truthfully.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer, SQLite, toml, requests/httpx/WebSocket stack, `filelock`, existing Spec Kitty runtime/paths abstractions; no new dependency  
**Storage**: `.../projects/<uuid>/sync/sync.db` containing control/epoch/sequence/journal/attempt/result/outbox/target/admission-operation/history-action/migration tables, plus `egress.lock`; atomic denial hints live at `projects/.deny-hints/<uuid>.json`
**Testing**: pytest unit/integration/CLI, connection/commit instrumentation, cross-process and hard-kill transport barriers, migration writer-race/WAL injection, old-daemon protocol, architecture/writer census, mutation controls, reproducible process-warm/cold benchmarks, cross-platform CI, real CLI↔SaaS contract/E2E
**Target Platform**: Linux, macOS, Windows 10+; local/offline operation plus the canonical SaaS contract, with hosted mutation limited to a dynamically discovered Upsun branch environment  
**Project Type**: Python CLI/runtime with background daemon and multiple transport adapters  
**Performance Goals**: 200 warm scans of the specified 100-store fixture complete within 500 ms p95 and 30 fresh-process scans within 1 s p95, without opening payload tables for 80 valid denied hints
**Constraints**: one UUID authority/grant writer/live connection owner; deterministic ASCII paths; no implicit grant or dual-read; monotonic capture sequence; immutable history capability; exact binding audience; durable operation/attempt identity; strict typing; no production mutation
**Scale/Scope**: all live event/body/history/daemon/WebSocket/tracker-hosted sender classes, mixed legacy state, and six-project cross-repository acceptance

## Charter Check

*GATE: PASS before Phase 0; PASS again after Phase 1 design.*

- **Single canonical authority — PASS**: `sync/consent.py` is reduced to one project-store record and writer. Path, repo-default, UUID index/backfill, checkout-only flags, local config, login, environment, and target cannot grant.
- **Architectural alignment — PASS**: project identity owns store resolution; target remains a separate value; SaaS admission remains an external authority consumed through the canonical contract.
- **ATDD-first — PASS**: implementation starts with A/B store-open traps, implicit-grant/writer negative matrices, capture-epoch tests, two-ordering revocation barriers, and hard-kill migration tests through public CLI/runtime entry points.
- **Structural closure — PASS**: live store constructors require `ProjectSyncContext`; no-argument/global resolvers are removed from live paths. Shrink-only call-site censuses and mutants prove the boundary is non-vacuous.
- **Campsite rule — PASS WITH REQUIRED FIRST SLICE**: scout the large consent/routing/sync-command/emitter surfaces and fix only domain-matched blockers before functional edits.
- **Cross-platform identity — PASS**: canonical UUID tokens are ASCII by construction and use `get_runtime_root`; Windows/macOS/Linux tests include non-ASCII display names and path variants.
- **Transactional coherence — PASS**: one ProjectSyncStore unit of work owns the live connection/outer transaction; component repositories cannot independently connect/commit. Fault tests cover atomic control/epoch/journal/outbox/attempt/result changes.
- **Contract authority — PASS**: SaaS owns `../spec-kitty-saas/contracts/cli-saas-current-api.yaml`; core adds compatibility code/tests only after the SaaS contract is fixed.
- **Issue/tracker hygiene — PASS**: #3262 and companion #585 are claimed/commented; predecessor and adjacent issues have matrix rows.
- **Reviewer separation — PASS**: each work package uses different implementer/reviewer profiles in Spec Kitty worktrees.
- **Supply chain — PASS**: no package added; existing authenticity, lockfile, lifecycle-script, and Node LTS gates remain unchanged.
- **Deployment/release safety — PASS**: local mission work only; hosted mutation may use only a dynamically discovered Upsun branch environment. Production, publishing, PR creation, mainline integration, and deployment require explicit operator authorization.

## Project Structure

### Documentation (this mission)

```text
kitty-specs/per-project-sync-consent-ledgers-01KZKMQZ/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── issue-matrix.json
├── contracts/
│   ├── project-sync-store-layout.md
│   └── sender-and-migration-matrix.md
└── traces/
    ├── tooling-friction.md
    ├── approach.md
    └── design-decisions.md
```

### Source Code (repository root)

```text
src/specify_cli/
├── event_journal/
│   └── journal.py                    # explicit project-owned path only
├── delivery/
│   ├── dispatcher.py                 # immutable context and final barrier
│   ├── ledger.py                     # project-owned ledger
│   ├── retention.py                  # project-scoped purge/diagnostics
│   ├── selection.py                  # preserved consent-bearing selection
│   └── status_report.py
├── sync/
│   ├── project_store.py              # canonical UUID path/store aggregate
│   ├── project_context.py            # store+epoch+audience/admission binding
│   ├── consent.py                    # sole project-control authority/writer
│   ├── admission_operations.py        # durable admit/revoke operation outbox
│   ├── history_disclosure.py          # preview/confirm sealed cohort capability
│   ├── transport_attempts.py          # crash-aware attempt/result protocol
│   ├── routing.py                    # opt-in/opt-out orchestration
│   ├── project_store_migration.py    # preview/copy/verify/cutover/quarantine
│   ├── daemon_protocol.py             # quiesce/restart layout handshake
│   ├── queue.py                      # project outbox; no shared live sender
│   ├── body_queue.py
│   ├── daemon.py
│   ├── runtime.py
│   ├── emitter.py
│   ├── client.py
│   ├── local_commit.py
│   └── history_import/
├── cli/commands/sync.py              # explicit commands and diagnostics
└── state/contract.py                 # declared project-store ownership

tests/
├── sync/
│   ├── test_project_store.py
│   ├── test_project_consent_authority.py
│   ├── test_project_store_migration.py
│   ├── test_consent_epochs.py
│   ├── test_history_disclosure.py
│   ├── test_admission_operations.py
│   ├── test_transport_attempt_recovery.py
│   ├── test_opt_out_barrier.py
│   ├── test_legacy_grant_writers.py
│   ├── test_daemon_project_isolation.py
│   ├── test_daemon_cutover_protocol.py
│   └── test_saas_admission_compatibility.py
├── architectural/
│   ├── test_project_store_boundary.py
│   └── test_egress_consent_boundary.py
└── contract/

../spec-kitty-saas/contracts/cli-saas-current-api.yaml
../end-to-end-testing/
```

**Structure Decision**: `project_uuid` owns one SQLite database, and `ProjectSyncStore.unit_of_work()` owns every live connection/outer transaction. Component repositories are connection-free adapters. The aggregate exposes one typed context containing capture sequence/epoch and exact target audience rather than loose parameters. Existing `consent.py` becomes the sole grant writer. Control operations, history disclosure, and transport attempts are durable store entities. Selection and final egress remain defense in depth and consume only the context/capabilities.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Supersede #3030 shared-store non-goal | #3262 explicitly requires physical project isolation and local capture must no longer depend on a shared hosted-consent gate. | Retaining a shared database with stronger predicates reproduces containment, not the requested structural boundary. |

This is an intentional predecessor decision supersession, not a charter exception; it must be recorded in an ADR/Decision Moment and validated through migration/compatibility tests.

## Implementation Concern Map

### IC-01 — Baseline, campsite, and structural test harness

- **Purpose**: Freeze all live store resolvers and sender call sites, then establish red-first cross-store and implicit-grant evidence.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-010, FR-018, FR-023, FR-026; NFR-001, NFR-004, NFR-007.
- **Affected surfaces**: current journal/ledger/queue resolvers, consent/routing, dispatcher, emitter, runtime, daemon, CLI tests and architecture census.
- **Sequencing/depends-on**: none.
- **Risks**: broad fixtures currently grant consent by monkeypatch; tests must prove patch targets are live and include positive/mutation controls.

### IC-02 — Project store and one consent authority

- **Purpose**: Build the connection-owning unit of work, sole grant writer, monotonic capture sequences/epochs, immutable history capability, and exact audience-bound admission operation state.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-017, FR-021, FR-022, FR-023, FR-026, FR-027, FR-028, FR-031, FR-032.
- **Affected surfaces**: `sync/project_store.py`, `sync/project_context.py`, `sync/consent.py`, `sync/routing.py`, `sync/config.py`, `sync/target_authority.py`, state contract and diagnostics.
- **Sequencing/depends-on**: IC-01.
- **Risks**: hidden component commits/connections, promoting legacy inputs, treating target as grant, capture/opt-in off-by-one, or ordinary selection minting history authority.

### IC-03 — Project-owned journals, delivery, and outboxes

- **Purpose**: Require the context/epoch for capture and payload state; persist admission operations and transport attempts before network I/O; reconcile native idempotency/results after crashes.
- **Relevant requirements**: FR-002, FR-006, FR-007, FR-010, FR-016, FR-017, FR-018, FR-021, FR-022, FR-025, FR-027, FR-028, FR-030, FR-031, FR-032.
- **Affected surfaces**: event journal, delivery ledger/selection/retention/status, offline/body queue, emitter, local commit.
- **Sequencing/depends-on**: IC-02.
- **Risks**: cross-pairing, crash after remote acceptance/before local result, unsafe automatic resend, and breaking native Event/body/LocalCommit correlation.

### IC-04 — Legacy partition, quarantine, and exclusive cutover

- **Purpose**: Quiesce recognized daemons and current foreground writers, take read-only logical snapshots with WAL semantics, copy/verify, atomically cut over, redirect current writers, and diagnose unrecognized late residue.
- **Relevant requirements**: FR-012, FR-013, FR-014, FR-015, FR-024, FR-029; NFR-002, NFR-005, NFR-007.
- **Affected surfaces**: shared journal, delivery ledger, offline/body queues, `sync/project_store_migration.py`, CLI migrate/doctor/status commands.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: constructor-mutated sources, WAL/SHM omission, hard-kill partial phases, foreground write loss, ghost results, unrecognized binaries, and protocol skew.

### IC-05 — Revocation barrier and sender convergence

- **Purpose**: Carry one context/attempt through every sender; cancel pre-start work; reconcile started results after timeout/crash; and apply physical atomic narrowing-only hints.
- **Relevant requirements**: FR-008, FR-009, FR-010, FR-011, FR-016, FR-025, FR-027, FR-030, FR-031; NFR-003, NFR-004, NFR-006.
- **Affected surfaces**: dispatcher, runtime, daemon, emitter WebSocket, relay, body transport, final sync, reconnect flush, history import, tracker-hosted/generic clients.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: recheck/send race, indefinite wait, unknown remote outcome, duplicate disclosure, cross-process workers, stale hint liveness, and falsely complete revoke.

### IC-06 — SaaS admission compatibility and cross-repository proof

- **Purpose**: Establish/revoke exact-target server admission, send per-write proof, consume correlated refusal, and prove the split six-project end-to-end boundary.
- **Relevant requirements**: FR-004, FR-007, FR-009, FR-016, FR-019, FR-020, FR-022; all SCs.
- **Affected surfaces**: SaaS client, delivery result classification, central contract tests, end-to-end-testing harness, issue/acceptance evidence.
- **Sequencing/depends-on**: SaaS mission contract and IC-02 through IC-05.
- **Risks**: landing core against an unstable contract or confusing local opt-out with acknowledged server revocation.

## Delivery sequence

1. Establish failing connection/commit, implicit-grant/writer, capture-sequence/history, migration-writer/WAL/hard-kill, daemon, transport-crash, and revocation tests plus live censuses.
2. Introduce the connection-owning project unit of work, sole consent writer, sequence/epochs, denial hints, and immutable history capability.
3. Add exact audience binding and durable admit/revoke operation records; move journal/outbox/result state behind the unit of work.
4. Persist transport attempts before I/O and converge every sender on context, native idempotency reconciliation, and bounded result leases.
5. Implement daemon/current-writer layout participation, read-only logical snapshot migration, verification, atomic cutover, redirect, quarantine, and late-residue diagnostics.
6. Integrate the complete SaaS contract and run conforming omission, bypass refusal, old-client upgrade refusal, and stale-generation parking.
7. Run the reproducible process-warm/cold benchmark and full architecture/mutation/cross-platform gates; complete tracker evidence without production mutation or unauthorized publication.

## Post-design Charter Re-check

PASS. Phase 1 selects one UUID-owned SQLite database, one connection/transaction owner, and one grant writer; makes every live writer context/sequence/epoch-bound; persists control and transport uncertainty before I/O; scopes admission to a verifiable audience; and gives migration writers a layout-generation barrier with read-only WAL-aware snapshots. Opt-out recovery, history capability, denial hints, benchmarks, and proof splitting now have executable protocols. The #3030 supersession remains explicit and scoped.

# Implementation Plan: Per-Project Sync Consent Ledgers

**Branch**: `feat/per-project-sync-consent` | **Date**: 2026-08-09 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/kitty-specs/per-project-sync-consent-ledgers-01KZKMQZ/spec.md`

## Summary

Replace live machine-global sync storage and multi-source granting with one `sync.db` per canonical UUID, opened only through a connection-owning ProjectSyncStore unit of work, and one versioned consent writer. ProjectSyncStore also owns the machine layout-generation/write-permit API before payload repositories migrate, so every current-version writer participates in later cutover. Local capture assigns a monotonic sequence in explicit epochs; opt-in records the inclusive tail, while sealed history requires an immutable preview/confirmation capability. Egress requires current consent/epoch, exact binding audience, per-write admission generation, and a durable transport attempt. Admit/revoke uses a durable operation outbox. Partition legacy state through daemon and current-writer layout participation, read-only logical snapshots, exact verification, and atomic cutover. Opt-out cancels pre-start work and reconciles or irrevocably terminalizes orphaned old-generation attempts before acknowledgement. Compatibility consumes a pinned SaaS candidate commit and contract digest; coordinated closure emits a checksum manifest with one owner per evidence claim.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer, SQLite, toml, requests/httpx/WebSocket stack, `filelock`, existing Spec Kitty runtime/paths abstractions; no new dependency  
**Storage**: `.../projects/<uuid>/sync/sync.db` containing control/epoch/sequence/journal/attempt/result/outbox/target/admission-operation/history-action/migration tables, plus `egress.lock`; one machine layout-generation authority/write-permit API; atomic denial hints at `projects/.deny-hints/<uuid>.json`; checksum-addressed acceptance manifests outside payload stores
**Testing**: pytest unit/integration/CLI, connection/commit instrumentation, cross-process and hard-kill transport barriers, migration writer-race/WAL injection, old-daemon protocol, architecture/writer census, mutation controls, reproducible process-warm/cold benchmarks, cross-platform CI, real CLI↔SaaS contract/E2E
**Target Platform**: Linux, macOS, Windows 10+; local/offline operation plus the canonical SaaS contract, with hosted mutation limited to a dynamically discovered Upsun branch environment  
**Project Type**: Python CLI/runtime with background daemon and multiple transport adapters  
**Performance Goals**: 200 warm scans of the specified 100-store fixture complete within 500 ms p95 and 30 fresh-process scans within 1 s p95, without opening payload tables for 80 valid denied hints
**Constraints**: one UUID authority/grant writer/live connection owner; one layout-generation writer authority; deterministic ASCII paths; no implicit grant or dual-read; monotonic capture sequence; immutable history capability; exact binding audience; durable operation/attempt identity; pinned SaaS candidate commit/contract digest; strict typing; no production mutation
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
- **Layout authority — PASS**: ProjectSyncStore introduces the machine layout-generation/write-permit API before repository conversion; every WP04 writer consumes it and migration only advances it after exact verification.
- **Contract authority — PASS**: SaaS owns `contracts/cli-saas-current-api.yaml`; core accepts an explicit SaaS candidate checkout/ref/digest after SaaS WP04 and refuses ambient relative sibling resolution.
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
│   ├── interfaces.py                # target/delivery capability interfaces
│   ├── targets.py                   # project-store-backed exact target registry
│   ├── dispatcher.py                 # immutable context and final barrier
│   ├── ledger.py                     # project-owned ledger
│   ├── retention.py                  # project-scoped purge/diagnostics
│   ├── selection.py                  # preserved consent-bearing selection
│   └── status_report.py
├── sync/
│   ├── project_store.py              # canonical UUID path/store aggregate
│   ├── layout_generation.py          # sole current-writer layout authority/API
│   ├── project_context.py            # store+epoch+audience/admission binding
│   ├── consent.py                    # sole project-control authority/writer
│   ├── admission_operations.py        # durable admit/revoke operation outbox
│   ├── history_disclosure.py          # preview/confirm sealed cohort capability
│   ├── transport_attempts.py          # crash-aware attempt/result protocol
│   ├── transport_lease.py             # cross-process final-gate/result barrier
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
│   ├── test_transport_result_lease.py
│   ├── test_transport_orphan_settlement.py
│   ├── test_interactive_transport_convergence.py
│   ├── test_background_authority_convergence.py
│   ├── test_transport_revocation_matrix.py
│   ├── test_transport_crash_matrix.py
│   ├── test_legacy_grant_writers.py
│   ├── test_daemon_project_isolation.py
│   ├── test_daemon_cutover_protocol.py
│   └── test_saas_admission_compatibility.py
├── architectural/
│   ├── test_project_store_boundary.py
│   └── test_egress_consent_boundary.py
└── contract/

<explicit-saas-candidate>/contracts/cli-saas-current-api.yaml
<explicit-e2e-checkout>/
```

**Structure Decision**: `project_uuid` owns one SQLite database, and `ProjectSyncStore.unit_of_work()` owns every live connection/outer transaction. ProjectSyncStore also exposes the sole layout-generation/write-permit API. Component repositories are connection-free adapters and every current writer uses the permit immediately before insert. The aggregate exposes one typed context containing capture sequence/epoch and exact target audience rather than loose parameters. Existing `consent.py` becomes the sole grant writer. Delivery target interfaces/exports and the concrete target registry move with the target/admission slice. Control operations, history disclosure, and transport attempts are durable store entities. Selection and final egress remain defense in depth and consume only the context/capabilities.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Supersede #3030 shared-store non-goal | #3262 explicitly requires physical project isolation and local capture must no longer depend on a shared hosted-consent gate. | Retaining a shared database with stronger predicates reproduces containment, not the requested structural boundary. |

This is an intentional predecessor decision supersession, not a charter exception; it must be recorded in an ADR/Decision Moment and validated through migration/compatibility tests.

## Implementation Concern Map

### IC-01 — Baseline, campsite, and structural test harness

- **Purpose**: Freeze all live store resolvers and sender call sites and provide green census, instrumentation, positive-control, and mutation-harness foundations. Each later behavior package owns its own first red acceptance commit.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-010, FR-018, FR-023, FR-026; NFR-001, NFR-004, NFR-007.
- **Affected surfaces**: current journal/ledger/queue resolvers, consent/routing, dispatcher, emitter, runtime, daemon, CLI tests and architecture census.
- **Sequencing/depends-on**: none.
- **Risks**: broad fixtures currently grant consent by monkeypatch; tests must prove patch targets are live and include positive/mutation controls.

### IC-02 — Project store, layout authority, and one consent authority

- **Purpose**: Build the connection-owning unit of work and machine layout-generation API, then the sole grant writer, monotonic capture sequences/epochs, immutable history capability, and exact audience-bound admission operation state.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-017, FR-021, FR-022, FR-023, FR-026, FR-027, FR-028, FR-031, FR-032.
- **Affected surfaces**: `sync/project_store.py`, `sync/project_context.py`, `sync/consent.py`, `sync/routing.py`, `sync/config.py`, `sync/target_authority.py`, state contract and diagnostics.
- **Sequencing/depends-on**: IC-01.
- **Risks**: hidden component commits/connections, privately inferred writer layout, promoting legacy inputs, treating target as grant, capture/opt-in off-by-one, or ordinary selection minting history authority.

### IC-03 — Project-owned journals, delivery, and outboxes

- **Purpose**: Require the context/epoch and a fresh layout write permit for
  capture and payload state. Move target interfaces/registry/exports into the
  project boundary; WP05 and IC-04 own control-operation/transport uncertainty.
- **Relevant requirements**: FR-002, FR-006, FR-007, FR-010, FR-016, FR-017, FR-018, FR-021, FR-022, FR-025, FR-027, FR-028, FR-030, FR-031, FR-032.
- **Affected surfaces**: event journal, delivery ledger/selection/retention/status,
  offline/body queue, delivery target interfaces/registry/exports.
- **Sequencing/depends-on**: IC-02.
- **Risks**: cross-pairing, crash after remote acceptance/before local result, unsafe automatic resend, and breaking native Event/body/LocalCommit correlation.

### IC-04 — Durable attempt and transport/result lease protocol

- **Purpose**: Persist attempts before I/O, define one cross-process lease, cancel pre-start work, and settle or irrevocably terminalize orphaned old-generation attempts before opt-out acknowledgement.
- **Relevant requirements**: FR-008, FR-009, FR-010, FR-025, FR-027, FR-030, FR-031; NFR-003, NFR-004.
- **Affected surfaces**: transport-attempt repository, consent gate, egress lock/lease, recovery service, protocol-level tests.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: recheck/send race, OS lock release after process death, indefinite wait, unknown remote outcome, duplicate disclosure, and falsely complete revoke.

### IC-05 — Interactive transport convergence

- **Purpose**: Carry the immutable context/attempt/lease through dispatcher HTTP, WebSocket/Event relay, LocalCommit, body/dossier, history, tracker-hosted, and generic SaaS adapters with native correlation.
- **Relevant requirements**: FR-005, FR-007, FR-010, FR-016, FR-018, FR-025, FR-030, FR-031; NFR-003, NFR-004, NFR-007.
- **Affected surfaces**: dispatcher, emitter/relay, body/dossier, LocalCommit, history import, SaaS/tracker client adapters.
- **Sequencing/depends-on**: IC-04 and the explicit SaaS WP04 candidate contract.
- **Risks**: request-wide proof, transport-specific bypass, incorrect terminal classification, and fresh identity after uncertainty.

### IC-06 — Daemon and background convergence

- **Purpose**: Apply project authority and deny-only discovery to daemon/background writers while preserving another project's liveness.
- **Relevant requirements**: FR-005, FR-010, FR-011, FR-029; NFR-001, NFR-006, NFR-007.
- **Affected surfaces**: daemon, runtime, background discovery, denial hints, focused daemon tests.
- **Sequencing/depends-on**: IC-04.
- **Risks**: long-lived grant caches, directory enumeration creating stores, or a current writer bypassing layout generation.

### IC-07 — Aggregate revocation and crash matrix

- **Purpose**: Prove both revoke orderings and every kill window across all transport families, including kill-during-response followed immediately by opt-out and late recovery.
- **Relevant requirements**: FR-008, FR-010, FR-025, FR-030; NFR-003, NFR-004; SC-004, SC-012.
- **Affected surfaces**: aggregate acceptance/race tests only; underlying sender source remains owned by IC-04 through IC-06.
- **Sequencing/depends-on**: IC-05, IC-06.
- **Risks**: representative sampling, late success after acknowledgement, hidden automatic resend, and cross-project starvation.

### IC-08 — Legacy partition, quarantine, and exclusive cutover

- **Purpose**: Consume the existing layout authority to quiesce recognized daemons/current writers, take read-only logical snapshots with WAL semantics, copy/verify, atomically cut over, redirect, and diagnose unrecognized late residue.
- **Relevant requirements**: FR-012, FR-013, FR-014, FR-015, FR-024, FR-029; NFR-002, NFR-005, NFR-007.
- **Affected surfaces**: migration/cutover services, daemon protocol, CLI migration/status commands, migration tests. Current writer source files remain owned by IC-03 and must already participate.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: constructor-mutated sources, WAL/SHM omission, hard-kill partial phases, foreground write loss, ghost results, unrecognized binaries, and protocol skew.

### IC-09 — Pinned SaaS compatibility and coordinated evidence

- **Purpose**: Establish/revoke exact-target server admission against a pinned candidate contract, prove the core-owned six-project bytes/parking boundary, and emit the checksum manifest that references separately owned SaaS refusal/tombstone/hosted evidence.
- **Relevant requirements**: FR-004, FR-007, FR-009, FR-016, FR-019, FR-020, FR-022, FR-033, FR-034; all SCs.
- **Affected surfaces**: contract selection/attestation, core integration and cross-platform tests, discovery benchmark, evidence manifest/docs.
- **Sequencing/depends-on**: SaaS WP04 before core admission compatibility; IC-04 through IC-08 plus reviewed SaaS WP02 anti-rematerialization and WP08 server/effect boundaries before coordinated acceptance.
- **Risks**: landing core against an unstable contract or confusing local opt-out with acknowledged server revocation.

## Delivery sequence

1. Establish green census/instrumentation/positive-control/mutation-harness foundations; each behavior package then commits its own failing ATDD test before source changes.
2. Introduce the connection-owning project unit of work and layout-generation/write-permit authority, then the sole consent writer, sequence/epochs, denial hints, and immutable history capability.
3. Move every current journal/delivery/event-outbox/body writer behind the unit of work and layout permit; add exact target/audience binding and durable admit/revoke operation records against the SaaS WP04 pinned contract.
4. Implement durable attempt and cross-process lease/recovery, then converge interactive transports and daemon/background paths in separate reviewable packages.
5. Run the aggregate revoke/crash matrix, including kill-during-response -> immediate opt-out -> late recovery.
6. Consume the existing layout authority in read-only logical snapshot migration, verification, atomic cutover, redirect, quarantine, and late-residue diagnostics.
7. After core transport and reviewed SaaS WP02/WP08 readiness, run core-owned conforming omission/stale parking/local isolation evidence and reference SaaS-owned refusal/zero-effect/hosted evidence by exact commit/digest.
8. Emit the immutable evidence manifest, run process-warm/cold benchmark and full architecture/mutation/cross-platform gates, and complete tracker evidence without production mutation or unauthorized publication.

## Post-design Charter Re-check

PASS. Phase 1 selects one UUID-owned SQLite database, one connection/transaction owner, and one grant writer; makes every live writer context/sequence/epoch-bound; persists control and transport uncertainty before I/O; scopes admission to a verifiable audience; and gives migration writers a layout-generation barrier with read-only WAL-aware snapshots. Opt-out recovery, history capability, denial hints, benchmarks, and proof splitting now have executable protocols. The #3030 supersession remains explicit and scoped.

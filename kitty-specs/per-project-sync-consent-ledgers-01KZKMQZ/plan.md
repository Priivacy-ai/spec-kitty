# Implementation Plan: Per-Project Sync Consent Ledgers

**Branch**: `feat/per-project-sync-consent` | **Date**: 2026-08-09 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/kitty-specs/per-project-sync-consent-ledgers-01KZKMQZ/spec.md`

## Summary

Replace live machine-global sync storage and multi-source granting with one transactionally coherent `sync.db` per canonical UUID and one versioned consent authority inside it. Local capture remains project-isolated and offline-capable in explicit capture epochs; opt-in starts eligibility at the current tail, while sealed history requires a separate previewed action. Egress requires the deny-only global switch, current project grant/epoch, exact target/account/Private-Teamspace admission generation, and an immutable context. Partition legacy state through daemon quiesce, copy, exact verification, and atomic cutover. Opt-out cancels pre-start work, waits for already-started transport/result settlement, seals without purging, and reports remote revocation truthfully.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer, SQLite, toml, requests/httpx/WebSocket stack, `filelock`, existing Spec Kitty runtime/paths abstractions; no new dependency  
**Storage**: `get_runtime_root().base/projects/<canonical-uuid>/sync/sync.db` containing control/epoch/journal/delivery/outbox/target/migration tables, plus project `egress.lock` and non-sensitive reports; legacy shared stores become diagnostic/purge-only  
**Testing**: pytest unit/integration/CLI, cross-process transport/result barriers, filesystem/database-open instrumentation, hard-kill migration fault injection, old-daemon protocol tests, architecture/writer census, mutation controls, reproducible benchmarks, cross-platform CI, real CLI↔SaaS contract/E2E  
**Target Platform**: Linux, macOS, Windows 10+; local/offline operation plus the canonical SaaS contract, with hosted mutation limited to a dynamically discovered Upsun branch environment  
**Project Type**: Python CLI/runtime with background daemon and multiple transport adapters  
**Performance Goals**: 200 warm scans of the specified 100-store fixture complete within 500 ms p95 and 30 cold scans within 1 s p95, without opening payload tables for 80 valid denied hints  
**Constraints**: one UUID authority and grant writer; deterministic ASCII paths; no implicit grant; no live dual-read fallback; capture epochs; target-scoped admission; opt-out/result linearization; strict typing; no production mutation  
**Scale/Scope**: all live event/body/history/daemon/WebSocket/tracker-hosted sender classes, mixed legacy state, and six-project cross-repository acceptance

## Charter Check

*GATE: PASS before Phase 0; PASS again after Phase 1 design.*

- **Single canonical authority — PASS**: `sync/consent.py` is reduced to one project-store record and writer. Path, repo-default, UUID index/backfill, checkout-only flags, local config, login, environment, and target cannot grant.
- **Architectural alignment — PASS**: project identity owns store resolution; target remains a separate value; SaaS admission remains an external authority consumed through the canonical contract.
- **ATDD-first — PASS**: implementation starts with A/B store-open traps, implicit-grant/writer negative matrices, capture-epoch tests, two-ordering revocation barriers, and hard-kill migration tests through public CLI/runtime entry points.
- **Structural closure — PASS**: live store constructors require `ProjectSyncContext`; no-argument/global resolvers are removed from live paths. Shrink-only call-site censuses and mutants prove the boundary is non-vacuous.
- **Campsite rule — PASS WITH REQUIRED FIRST SLICE**: scout the large consent/routing/sync-command/emitter surfaces and fix only domain-matched blockers before functional edits.
- **Cross-platform identity — PASS**: canonical UUID tokens are ASCII by construction and use `get_runtime_root`; Windows/macOS/Linux tests include non-ASCII display names and path variants.
- **Transactional coherence — PASS**: consent, epochs, journal, delivery, outbox, target/admission, and cutover metadata share one project SQLite transaction boundary.
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
│   ├── project_context.py            # store+epoch+target/account/team admission
│   ├── consent.py                    # sole project-control authority/writer
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

**Structure Decision**: `project_uuid` owns a directory under the canonical runtime root containing one transactionally coherent SQLite database. The aggregate exposes one typed context rather than loose journal/ledger/target parameters. Existing `consent.py` becomes the sole decision authority and grant writer. Capture epochs and exact target admission are explicit context members. Existing selection and final egress gates remain defense in depth but accept only the bounded project context.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Supersede #3030 shared-store non-goal | #3262 explicitly requires physical project isolation and local capture must no longer depend on a shared hosted-consent gate. | Retaining a shared database with stronger predicates reproduces containment, not the requested structural boundary. |

This is an intentional predecessor decision supersession, not a charter exception; it must be recorded in an ADR/Decision Moment and validated through migration/compatibility tests.

## Implementation Concern Map

### IC-01 — Baseline, campsite, and structural test harness

- **Purpose**: Freeze all live store resolvers and sender call sites, then establish red-first cross-store and implicit-grant evidence.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-010, FR-018, FR-023; NFR-001, NFR-004, NFR-007.
- **Affected surfaces**: current journal/ledger/queue resolvers, consent/routing, dispatcher, emitter, runtime, daemon, CLI tests and architecture census.
- **Sequencing/depends-on**: none.
- **Risks**: broad fixtures currently grant consent by monkeypatch; tests must prove patch targets are live and include positive/mutation controls.

### IC-02 — Project store and one consent authority

- **Purpose**: Resolve deterministic UUID-owned single-database storage, make consent the sole grant writer, create capture epochs, and keep exact-target admission separate.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-017, FR-021, FR-022, FR-023.
- **Affected surfaces**: `sync/project_store.py`, `sync/project_context.py`, `sync/consent.py`, `sync/routing.py`, `sync/config.py`, `sync/target_authority.py`, state contract and diagnostics.
- **Sequencing/depends-on**: IC-01.
- **Risks**: accidentally promoting the old UUID index/local config, treating target selection as grant, or making prior capture eligible at opt-in.

### IC-03 — Project-owned journals, delivery, and outboxes

- **Purpose**: Require the project context and epoch for local capture, delivery status, body/offline tasks, purge, diagnostics, and every per-write admission proof.
- **Relevant requirements**: FR-002, FR-006, FR-007, FR-010, FR-016, FR-017, FR-018, FR-021, FR-022.
- **Affected surfaces**: event journal, delivery ledger/selection/retention/status, offline/body queue, emitter, local commit.
- **Sequencing/depends-on**: IC-02.
- **Risks**: independently pairing A's journal with B's ledger/target; constructors and live APIs must reject mismatch before reads.

### IC-04 — Legacy partition, quarantine, and exclusive cutover

- **Purpose**: Quiesce recognized old daemons, copy identifiable rows/status into staged project stores, verify exactly, atomically cut over, and make late old writes non-deliverable residue.
- **Relevant requirements**: FR-012, FR-013, FR-014, FR-015, FR-024; NFR-002, NFR-005, NFR-007.
- **Affected surfaces**: shared journal, delivery ledger, offline/body queues, `sync/project_store_migration.py`, CLI migrate/doctor/status commands.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: hard-kill partial phases, ghost delivery rows, conflicting identity, unrecognized old writers, protocol skew, and an opt-in that touches other projects.

### IC-05 — Revocation barrier and sender convergence

- **Purpose**: Carry one context through every sender; cancel pre-start work; settle already-started transport/results truthfully; and apply narrowing-only daemon hints.
- **Relevant requirements**: FR-008, FR-009, FR-010, FR-011, FR-016, FR-025; NFR-003, NFR-004, NFR-006.
- **Affected surfaces**: dispatcher, runtime, daemon, emitter WebSocket, relay, body transport, final sync, reconnect flush, history import, tracker-hosted/generic clients.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: recheck-then-send race, deadlock or unbounded result wait, cross-process workers, stale hints, cwd-derived state, and remote revoke pending being reported as complete.

### IC-06 — SaaS admission compatibility and cross-repository proof

- **Purpose**: Establish/revoke exact-target server admission, send per-write proof, consume correlated refusal, and prove the split six-project end-to-end boundary.
- **Relevant requirements**: FR-004, FR-007, FR-009, FR-016, FR-019, FR-020, FR-022; all SCs.
- **Affected surfaces**: SaaS client, delivery result classification, central contract tests, end-to-end-testing harness, issue/acceptance evidence.
- **Sequencing/depends-on**: SaaS mission contract and IC-02 through IC-05.
- **Risks**: landing core against an unstable contract or confusing local opt-out with acknowledged server revocation.

## Delivery sequence

1. Establish failing store-open, implicit-grant/writer, epoch, migration-hard-kill, daemon-protocol, and two-ordering revocation tests plus live sender/store/writer censuses.
2. Introduce the one-database project store/context/control authority, capture epochs, explicit history preview, and exact-target admission state.
3. Move journal, delivery, offline/body, purge, and status surfaces onto project-owned contexts with per-write proof.
4. Implement daemon quiesce, copy-only migration, exact verification, quarantine, atomic cutover, and late-residue diagnostics.
5. Converge all senders and daemon discovery on the context, deny-only hint, and transport/result barrier.
6. Integrate the published SaaS admission/refusal contract and run the split six-project matrix and stale-generation race.
7. Run the reproducible performance protocol and focused/full/architecture/mutation/cross-platform gates; complete tracker evidence without production mutation or unauthorized publication.

## Post-design Charter Re-check

PASS. Phase 1 selects one UUID-owned SQLite transaction boundary and one grant writer, reuses existing dependencies and runtime-root conventions, makes every live writer context/epoch-bound, scopes SaaS admission to the exact authenticated destination, and treats compatibility state as migration input rather than authority. Opt-out settlement, daemon cutover, benchmarks, and evidence splitting have executable protocols. The #3030 supersession is explicit, scoped, and preserved as defense in depth where compatible.

# Implementation Plan: Event sync — preserve local events & track per-target drains

**Branch**: `mission/event-sync-retention-delivery` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md`

## Summary

Split the CLI's local sync queue into two concepts that today are conflated in one deletable row: an **append-only event journal** (payloads, repo/install/session-local; producer identity attached when known) and **per-target delivery state** (a ledger keyed by event × target). First settle #2146 target authority so config/env/auth/network/status resolve one target model; then successful upload becomes a ledger update, never event destruction, so retained events can be re-drained to a fresh delivery target. An `EventSyncConfig` policy layer selects retention (on/off) × delivery (none / Teamspace / external-receiver); a localhost stub receiver gets fork CI off the `teamspace_key` dependency. Modeled as separate core domains (`event_journal/` + `delivery/`) per Stijn's hard requirement, with migration off the current `server|user|team`-scoped queue.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib `sqlite3` (local store), `typer`/`rich` (CLI surface), `requests` (delivery transport), `spec_kitty_events.*` (event contracts — consumed via public imports only, per the Shared Package Boundary)
**Storage**: local SQLite under the spec-kitty home (the sync DB today scoped via `build_queue_scope`, `src/specify_cli/sync/queue.py:391`); new shape = target-authority diagnostics + journal + delivery_targets + delivery ledger tables, journal **repo/install/session-local** and producer-scoped when user/team is known, not server-scoped
**Testing**: `pytest` (`PWHEADLESS=1 pytest tests/ -n auto --dist loadfile`); assert observable CLI output + on-disk/ledger state, not call order; a stub receiver replaces any real Teamspace dependency; real-port/daemon tests run serially (`-n0`)
**Target Platform**: developer workstations + CI (Linux/macOS/Windows); offline-capable (journal works with no network)
**Project Type**: single (CLI library — `src/specify_cli/`)
**Performance Goals**: a `sync now` over a typical journal (hundreds–low thousands of events) completes without noticeable lag; no full-table rewrite per sync (selection is index-assisted on delivery state)
**Constraints**: append-only journal; non-destructive sync; canonical target authority before migration/drain; separate core domain (no new event-delivery logic inside `queue.py`); single active delivery target for MVP (ledger shaped to grow into fan-out); event IDs unchanged
**Scale/Scope**: per-repo journals up to ~10k+ events before explicit GC; a small number of delivery targets per operator

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Terminology Canon** — "Mission" not "feature"; no `feature*` aliases in new flags/commands/fields. PASS (design uses event/journal/target/delivery/ledger vocabulary).
- **Separate-domain / anti-spaghetti** (Stijn, C-001) — new logic lands in `event_journal/` + `delivery/`, not `queue.py` and not existing `src/specify_cli/events/`. PASS by construction.
- **Complexity ceiling 15** (ruff C901 / Sonar S3776) — dispatcher selection + migration are the at-risk functions; keep each ≤15 by extracting select/post/record phases. PASS with discipline.
- **New branch/helper ⇒ tests in same PR** — every selection/state/migration branch gets focused tests (NFR-001/002). PASS.
- **No-direct-push / PR flow** — planning artifacts committed to the mission branch, merged via PR. PASS.

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/event-sync-retention-delivery-01KVYWRG/
├── spec.md              # complete
├── plan.md              # this file
├── contracts/
│   └── event-sync-delivery-contract.md
└── tasks/               # WP breakdown (/spec-kitty.tasks output)
```

### Source Code (repository root)

```
src/specify_cli/
├── event_journal/              # NEW domain — the journal
│   ├── journal.py              #   append-only payload store (producer-scoped)
│   └── models.py               #   Event record + coalesce rules
├── delivery/                   # NEW domain — targets, ledger, dispatch
│   ├── targets.py              #   Delivery Target Registry (URL+scope identity; deployment metadata)
│   ├── ledger.py               #   per-event/per-target delivery state
│   ├── dispatcher.py           #   select-undelivered → post → record; never deletes
│   ├── receivers.py            #   Teamspace + external-receiver target types + stub
│   └── config.py               #   EventSyncConfig (retention × delivery presets)
├── sync/
│   ├── target_authority.py     #   NEW — canonical runtime target resolver/diagnostics (#2146)
│   ├── queue.py                #   KEEPS body_upload_queue/body_upload_failure_log (setup-plan/
│   │                           #   dossier sync — NOT event queueing); only EVENT queueing moves out
│   └── migrate_journal.py      #   NEW — discover queue-<digest>.db scoped DBs → journal + ledger backfill
└── cli/commands/sync*          #   sync now / server / status / gc / archive wiring

tests/
├── sync/                       # dispatcher, migration, status/gc (incl. serial daemon cases)
├── event_journal/ + delivery/  # journal, ledger, targets, config, receivers, stub
└── ...                         # observable-state + on-disk assertions
```

**Structure Decision**: Single-project CLI library. The two new domains (`event_journal/`, `delivery/`) carry all new event-delivery logic. The existing `src/specify_cli/events/` package remains the event-log integration/decision-log surface and is not repurposed. `sync/queue.py` is **not** retired: it continues to own `body_upload_queue` / `body_upload_failure_log` (setup-plan / dossier body uploads, which are not event queueing — C-006). Only the event-queueing responsibility moves out, so existing `sync` CLI commands keep working with new semantics and non-event uploads are untouched.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-00 — Canonical sync target authority (#2146)

- **Purpose**: Resolve the split-brain between `config.toml`, `SPEC_KITTY_SAAS_URL`, auth/readiness, WebSocket, tracker, queue scope, diagnostics, and network calls before journal migration or delivery logic uses a target. Queue scope remains a derived isolation key, not a selector.
- **Relevant requirements**: FR-016, FR-019, C-002, C-007, SC-008.
- **Affected surfaces**: `src/specify_cli/sync/target_authority.py`, `sync/config.py`, `auth/config.py`, `sync/queue.py`, `sync/preflight.py`, `sync/owner.py`, `sync/runtime.py`, `sync/tracker_client_glue.py`, `saas/readiness.py`, `cli/commands/sync.py`.
- **Sequencing/depends-on**: none; this must be first because all journal/ledger target identity and migration backfill depend on it.
- **Risks**: leaving env/config behavior ambiguous would let the new ledger record delivery for one target while network calls hit another. Tests must cover env/config disagreement, stale `active_queue_scope`, and `sync status --check --json` diagnostics.

### IC-01 — Core domain scaffolding & boundaries

- **Purpose**: Stand up `event_journal/` and `delivery/` as clean domains with explicit interfaces so nothing leaks back into `queue.py` or the existing `events/` package (the anti-spaghetti requirement).
- **Relevant requirements**: C-001.
- **Affected surfaces**: `src/specify_cli/event_journal/`, `src/specify_cli/delivery/`.
- **Sequencing/depends-on**: IC-00.
- **Risks**: getting the seam wrong forces later churn; define the journal/ledger/dispatch interfaces before filling them.

### IC-02 — Event Journal (append-only, producer-scoped)

- **Purpose**: Durable local payload store that does not know delivery state; repo/install/session-local and producer-scoped when identity is known, not server-scoped and not blocked by auth/team/sync/network gates. **Append-only with NO coalescing at this stage** — coalescing is deliberately deferred to IC-02a because it needs the ledger to answer "delivered anywhere?".
- **Relevant requirements**: FR-001, FR-003, FR-017, C-008, SC-009.
- **Affected surfaces**: `event_journal/journal.py`, `event_journal/models.py`, current event producers that now gate before queueing.
- **Sequencing/depends-on**: IC-01.
- **Risks**: must not re-introduce the in-place mutation that today's `_try_coalesce` does; until IC-02a lands, every produced event is a distinct row. Teamspace-bound producers must not treat `SPEC_KITTY_ENABLE_SAAS_SYNC=0`, missing auth/team, or Private-Teamspace rejection as "do not write".

### IC-02a — Coalescing with delivered-event immutability (deferred until the ledger exists)

- **Purpose**: Re-introduce coalescing safely — collapse only events with no terminal delivery to any target; once an event has been delivered anywhere it is immutable and a new event is a new row (mark the prior superseded).
- **Relevant requirements**: FR-011.
- **Affected surfaces**: `event_journal/journal.py` (coalesce path), `delivery/ledger.py` (delivered-anywhere query).
- **Sequencing/depends-on**: IC-02, **IC-04 (ledger must exist first)**.
- **Risks**: the correctness trap from the review — delivered-event immutability is a **required DB test** (NFR-002), not prose. A coalesce attempt against a delivered event must leave it byte-for-byte unchanged.

### IC-03 — Delivery Target Registry & identity

- **Purpose**: Canonical-URL + user/team scope identity derived from IC-00 target authority; record (not key on) deployment metadata; detect target reset when metadata exists.
- **Relevant requirements**: FR-002, C-002, FR-012, FR-016.
- **Affected surfaces**: `delivery/targets.py`.
- **Sequencing/depends-on**: IC-00, IC-01.
- **Risks**: deployment_id churn must not fork identity; reset-detection is advisory/follow-on, not automatic re-drain and not an MVP blocker.

### IC-04 — Delivery Ledger

- **Purpose**: Per-event/per-target state answering "delivered to Y, when, result?"; shaped to grow into many-targets without schema break.
- **Relevant requirements**: FR-002, FR-004, C-003.
- **Affected surfaces**: `delivery/ledger.py`.
- **Sequencing/depends-on**: IC-01, IC-03.
- **Risks**: index design drives dispatcher selection performance.

### IC-04a — `DeliveryReceiver` contract (Teamspace / external / stub)

- **Purpose**: Define one explicit `DeliveryReceiver` contract before dispatcher implementation: **endpoint URL**, **auth/headers**, **per-event result mapping** (success/duplicate/pending/rejected/terminal-failed/transient), **retry semantics**, and **which gates apply**. The current Teamspace batch path is SaaS-gated + Private-Teamspace-gated + Bearer-auth + fixed to `/api/v1/events/batch/` (`sync/batch.py`) — that becomes the Teamspace receiver; `external` is operator-supplied URL/auth with no Teamspace gating; `stub` is a localhost receiver with no credentials.
- **Relevant requirements**: FR-007, FR-008, FR-014, SC-005, SC-007.
- **Affected surfaces**: `delivery/receivers.py`, `delivery/dispatcher.py` (consumes the contract), test fixtures, `contracts/batch-api-contract.md`.
- **Sequencing/depends-on**: IC-00, IC-03, IC-04; schedule before IC-05 dispatcher wiring.
- **Risks**: the stub must be a real target type implementing the same contract, not a test-only fork of the dispatch path. Gates must be expressed per receiver, not hard-coded in the dispatcher.

### IC-05 — Sync Dispatcher

- **Purpose**: Select journal events lacking terminal delivery for the active target, post, update the ledger; never delete source events. Outcome mapping (today `success`/`duplicate`/`failed_permanent` all DELETE, `queue.py:1693`): `success`/`duplicate` → terminal-success ledger rows; `pending`/`rejected`/`failed_transient` keep their current semantics (already aligned, `queue.py:1666-1678`) as ledger state, not deletes. **`failed_permanent` is NOT a delete and NOT a success** — see IC-05a.
- **Relevant requirements**: FR-001, FR-004, FR-005.
- **Affected surfaces**: `delivery/dispatcher.py`, `cli/commands/sync*`.
- **Sequencing/depends-on**: IC-02, IC-04, IC-04a.
- **Risks**: complexity ceiling — split select/post/record phases.

### IC-05a — Terminal-failed state machine (`failed_permanent`)

- **Purpose**: Decide what a permanent failure (e.g. oversized event) means once events are never deleted. Resolution: a **terminal-failed ledger state** that is *selector-excluded* from future drains (so the drain still progresses, as the old DELETE achieved) and stays inspectable; the payload is retained, never deleted. Re-attempt only via explicit operator action.
- **Relevant requirements**: FR-015.
- **Affected surfaces**: `delivery/ledger.py` (state), `delivery/dispatcher.py` (selection excludes terminal-failed).
- **Sequencing/depends-on**: IC-04, IC-05.
- **Risks**: forgetting to exclude terminal-failed from the selector would loop the drain on an oversized event. Tests for oversized events are required.

### IC-06 — EventSyncConfig policy & modes

- **Purpose**: Operator/repository dial selecting retention × delivery; four presets (TEAMSPACE / EXTERNAL_RECEIVER / LOCAL_RETENTION / OPT_OUT).
- **Relevant requirements**: FR-006, FR-007.
- **Affected surfaces**: `delivery/config.py`, `cli/commands/sync*`.
- **Sequencing/depends-on**: IC-00, IC-05.
- **Risks**: clear mode semantics: LOCAL_RETENTION journals without delivery; OPT_OUT only drops local-only/discardable families and must refuse or audit Teamspace-bound discard attempts.

### IC-07 — Migration off the hash-scoped queues

- **Purpose**: Migrate currently-queued events out of the existing `queue-<digest>.db` scoped DBs into the journal + ledger. The digest is a one-way hash of `server|user|team`, so URL/scope **cannot be recovered from the filename** — the migration must therefore: (a) **discover** all scoped DBs (glob the queue dir, not just the legacy `queue.db` the current migration handles), (b) attach migrated events to a **best-effort or explicitly-`unknown`** delivery target rather than fabricating identity, (c) apply duplicate collision policy, (d) **skip/handle an unrecognized digest** without aborting, and (e) be explicit that delivered-and-deleted events are unrecoverable (only currently-queued payloads survive).
- **Duplicate policy**: same `event_id` + identical canonical payload imports once and records all source DB provenance; same `event_id` + divergent canonical payload writes a migration-conflict/audit row, leaves the source DB untouched, blocks cleanup, and exits non-zero/blocked until operator resolution. It never rewrites event IDs and never silently overwrites payload bytes.
- **Relevant requirements**: FR-013, FR-018, NFR-005, SC-006, SC-011.
- **Affected surfaces**: `sync/migrate_journal.py`, existing `queue.py` scope helpers (`build_queue_scope`, the digest path builder).
- **Sequencing/depends-on**: IC-00, IC-02, IC-04.
- **Risks**: atomicity per DB; idempotent re-run; plural-source tests (multiple DBs, unknown scope, duplicate `event_id`) are required by SC-006 — a single-DB happy path is insufficient.

### IC-08 — `sync status` / `gc` / `archive`

- **Purpose**: Report retained vs per-target delivered counts; explicit-only destructive cleanup preserving ledger history; surface journal growth; extend the existing `sync status --check --json` contract with additive target-authority/journal/delivery/migration/body-upload fields.
- **Relevant requirements**: FR-009, FR-010, FR-019, NFR-004.
- **Affected surfaces**: `cli/commands/sync*`, `delivery/ledger.py`, `event_journal/journal.py`, `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-status-output.md`.
- **Sequencing/depends-on**: IC-05.
- **Risks**: status back-compat — existing stats consumers must keep working with clarified semantics.

### IC-09 — (Sequenced follow-on) SaaS `/health` deployment metadata

- **Purpose**: Consume `server_instance_id`/`deployment_id`/`environment_name`/`git_sha` from `/api/v1/sync/health/` to strengthen target provenance + reset-detection.
- **Relevant requirements**: C-004.
- **Affected surfaces**: `delivery/targets.py` (CLI side); a separate `spec-kitty-saas` change exposes the metadata.
- **Sequencing/depends-on**: IC-03; **gated on the SaaS change** — ship CLI with URL-only identity first. Likely a separate follow-on mission, not in this MVP's critical path.
- **Risks**: cross-repo coordination; don't let it block IC-01–IC-09.

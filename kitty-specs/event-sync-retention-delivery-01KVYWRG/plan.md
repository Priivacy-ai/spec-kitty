# Implementation Plan: Event sync — preserve local events & track per-target drains

**Branch**: `mission/event-sync-retention-delivery` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md`

## Summary

Split the CLI's local sync queue into two concepts that today are conflated in one deletable row: an **append-only event journal** (payloads, producer-scoped) and **per-target delivery state** (a ledger keyed by event × target). A successful upload becomes a ledger update, never event destruction, so the same retained events can be re-drained to a fresh delivery target. An `EventSyncConfig` policy layer selects retention (on/off) × delivery (none / Teamspace / external-receiver); a localhost stub receiver gets fork CI off the `teamspace_key` dependency. Modeled as a separate core domain (`events/` + `delivery/`) per Stijn's hard requirement, with a migration off the current `server|user|team`-scoped queue.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib `sqlite3` (local store), `typer`/`rich` (CLI surface), `requests` (delivery transport), `spec_kitty_events.*` (event contracts — consumed via public imports only, per the Shared Package Boundary)
**Storage**: local SQLite under the spec-kitty home (the sync DB today scoped via `build_queue_scope`, `src/specify_cli/sync/queue.py:391`); new shape = journal + delivery_targets + delivery ledger tables, journal **producer-scoped** (`user|team`/repo), not server-scoped
**Testing**: `pytest` (`PWHEADLESS=1 pytest tests/ -n auto --dist loadfile`); assert observable CLI output + on-disk/ledger state, not call order; a stub receiver replaces any real Teamspace dependency; real-port/daemon tests run serially (`-n0`)
**Target Platform**: developer workstations + CI (Linux/macOS/Windows); offline-capable (journal works with no network)
**Project Type**: single (CLI library — `src/specify_cli/`)
**Performance Goals**: a `sync now` over a typical journal (hundreds–low thousands of events) completes without noticeable lag; no full-table rewrite per sync (selection is index-assisted on delivery state)
**Constraints**: append-only journal; non-destructive sync; separate core domain (no new logic inside `queue.py`); single active delivery target for MVP (ledger shaped to grow into fan-out); event IDs unchanged
**Scale/Scope**: per-repo journals up to ~10k+ events before explicit GC; a small number of delivery targets per operator

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Terminology Canon** — "Mission" not "feature"; no `feature*` aliases in new flags/commands/fields. PASS (design uses event/journal/target/delivery/ledger vocabulary).
- **Separate-domain / anti-spaghetti** (Stijn, C-001) — new logic lands in `events/` + `delivery/`, not `queue.py`. PASS by construction.
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
└── tasks/               # WP breakdown (/spec-kitty.tasks output)
```

### Source Code (repository root)

```
src/specify_cli/
├── events/                     # NEW domain — the journal
│   ├── journal.py              #   append-only payload store (producer-scoped)
│   └── models.py               #   Event record + coalesce rules
├── delivery/                   # NEW domain — targets, ledger, dispatch
│   ├── targets.py              #   Delivery Target Registry (URL+scope identity; deployment metadata)
│   ├── ledger.py               #   per-event/per-target delivery state
│   ├── dispatcher.py           #   select-undelivered → post → record; never deletes
│   ├── receivers.py            #   Teamspace + external-receiver target types + stub
│   └── config.py               #   EventSyncConfig (retention × delivery presets)
├── sync/
│   ├── queue.py                #   shrinks to a thin compat/shim over events+delivery (or retires)
│   └── migrate_journal.py      #   NEW — server-scoped queue → journal + ledger backfill
└── cli/commands/sync*          #   sync now / server / status / gc / archive wiring

tests/
├── sync/                       # dispatcher, migration, status/gc (incl. serial daemon cases)
├── events/ + delivery/         # journal, ledger, targets, config, receivers, stub
└── ...                         # observable-state + on-disk assertions
```

**Structure Decision**: Single-project CLI library. The two new domains (`events/`, `delivery/`) carry all new logic; `sync/queue.py` is reduced to a compatibility seam (or retired) once the dispatcher/journal land, so existing `sync` CLI commands keep working with new semantics.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Core domain scaffolding & boundaries

- **Purpose**: Stand up `events/` and `delivery/` as a clean domain with explicit interfaces so nothing leaks back into `queue.py` (the anti-spaghetti requirement).
- **Relevant requirements**: C-001.
- **Affected surfaces**: `src/specify_cli/events/`, `src/specify_cli/delivery/`.
- **Sequencing/depends-on**: none (foundation).
- **Risks**: getting the seam wrong forces later churn; define the journal/ledger/dispatch interfaces before filling them.

### IC-02 — Event Journal (append-only, producer-scoped)

- **Purpose**: Durable local payload store that does not know delivery state; producer-scoped, not server-scoped.
- **Relevant requirements**: FR-001, FR-003, FR-011 (coalesce only among undelivered events).
- **Affected surfaces**: `events/journal.py`, `events/models.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: coalescing must not mutate an event with any terminal delivery — the correctness trap; needs the ledger to answer "delivered anywhere?".

### IC-03 — Delivery Target Registry & identity

- **Purpose**: Canonical-URL + user/team scope identity; record (not key on) deployment metadata; detect target reset.
- **Relevant requirements**: FR-002, C-002, FR-012.
- **Affected surfaces**: `delivery/targets.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: deployment_id churn must not fork identity; reset-detection is advisory, not automatic re-drain.

### IC-04 — Delivery Ledger

- **Purpose**: Per-event/per-target state answering "delivered to Y, when, result?"; shaped to grow into many-targets without schema break.
- **Relevant requirements**: FR-002, FR-004, C-003.
- **Affected surfaces**: `delivery/ledger.py`.
- **Sequencing/depends-on**: IC-01, IC-03.
- **Risks**: index design drives dispatcher selection performance.

### IC-05 — Sync Dispatcher

- **Purpose**: Select journal events lacking terminal successful delivery for the active target, post, update the ledger; never delete source events. Map `success`/`duplicate`/`failed_permanent` to ledger writes (today they DELETE, `queue.py:1693`); keep `pending`/`rejected`/`failed_transient` semantics (already aligned, `queue.py:1666-1678`).
- **Relevant requirements**: FR-001, FR-004, FR-005, FR-011.
- **Affected surfaces**: `delivery/dispatcher.py`, `cli/commands/sync*`.
- **Sequencing/depends-on**: IC-02, IC-04.
- **Risks**: complexity ceiling — split select/post/record phases.

### IC-06 — EventSyncConfig policy & modes

- **Purpose**: Operator/repository dial selecting retention × delivery; four presets (TEAMSPACE / EXTERNAL_RECEIVER / LOCAL_RETENTION / OPT_OUT).
- **Relevant requirements**: FR-006, FR-007.
- **Affected surfaces**: `delivery/config.py`, `cli/commands/sync*`.
- **Sequencing/depends-on**: IC-05.
- **Risks**: clear mode semantics (LOCAL_RETENTION journals-no-deliver; OPT_OUT neither).

### IC-07 — External receiver & test stub

- **Purpose**: Generalize delivery to an operator endpoint; provide a localhost stub that accepts+records, so tests/fork-CI need no Teamspace/`teamspace_key`.
- **Relevant requirements**: FR-007, FR-008, SC-005.
- **Affected surfaces**: `delivery/receivers.py`, test fixtures.
- **Sequencing/depends-on**: IC-05, IC-06.
- **Risks**: stub must be a real target type, not a test-only fork of the dispatch path.

### IC-08 — Migration off the server-scoped queue

- **Purpose**: Consolidate possibly-several `server|user|team` queue DBs into one producer-scoped journal + backfill ledger; preserve all currently-queued payloads; be explicit that delivered-and-deleted events are unrecoverable.
- **Relevant requirements**: FR-013, NFR-005.
- **Affected surfaces**: `sync/migrate_journal.py`, existing `queue.py` scope helpers.
- **Sequencing/depends-on**: IC-02, IC-04.
- **Risks**: atomicity per DB; idempotent re-run; honest handling of multiple source DBs.

### IC-09 — `sync status` / `gc` / `archive`

- **Purpose**: Report retained vs per-target delivered counts; explicit-only destructive cleanup preserving ledger history; surface journal growth.
- **Relevant requirements**: FR-009, FR-010, NFR-004.
- **Affected surfaces**: `cli/commands/sync*`, `delivery/ledger.py`, `events/journal.py`.
- **Sequencing/depends-on**: IC-05.
- **Risks**: status back-compat — existing stats consumers must keep working with clarified semantics.

### IC-10 — (Sequenced follow-on) SaaS `/health` deployment metadata

- **Purpose**: Consume `server_instance_id`/`deployment_id`/`environment_name`/`git_sha` from `/api/v1/sync/health/` to strengthen target provenance + reset-detection.
- **Relevant requirements**: C-004.
- **Affected surfaces**: `delivery/targets.py` (CLI side); a separate `spec-kitty-saas` change exposes the metadata.
- **Sequencing/depends-on**: IC-03; **gated on the SaaS change** — ship CLI with URL-only identity first. Likely a separate follow-on mission, not in this MVP's critical path.
- **Risks**: cross-repo coordination; don't let it block IC-01–IC-09.

# Implementation Plan: Journal Project Consent

**Branch**: `feat/journal-project-consent-3030` | **Date**: 2026-07-28 | **Spec**: [`spec.md`](spec.md)
**Mission**: `journal-project-consent-3030-01KYKWQS` | **Issue**: `Priivacy-ai/spec-kitty#3030` (P0)

## Summary

Give the delivery context a consent gate it does not currently have, and make project consent a
per-event predicate applied inside the journal read so authorization and delivery finally happen at
the same scope. Ships in two waves: a containment wave that needs no schema change and converts a
silent leak into a loud refusal, then a durable wave that adds project identity as an indexed journal
column, a uuid-keyed consent index, and a project-filtered read seam.

## Technical Context

**Language/runtime**: Python 3.11+, Typer CLI, SQLite stores.

**The two stores, and which one matters.** The drain for `sync now` reads the append-only journal at
`~/.spec-kitty/event_journal/journal-<producer-token>.db` (`event_journal/journal.py:78-90`, keyed on
`user_id`/`team_slug` — per *producer*, not per project). `sync/queue.py`'s `queue` table is the
retired legacy store, kept "only as the legacy batch-transport bridge" (`queue.py:1-12`), still
drained by the background daemon (`sync/background.py:589-592` → `455-461` → `batch_sync`). Both must
end up enforcing the invariant, or the uncovered store keeps shipping (FR-012).

**Where the leak actually is.** `delivery/dispatcher.py:192-223` `_select_undelivered` takes its
universe from `journal.read_all()` (`dispatcher.py:214`) — every row of every project — and the
delivery gate vocabulary is `GateKind = {SAAS_ENABLED, PRIVATE_TEAMSPACE, AUTH, ENDPOINT_CONFIGURED}`
(`delivery/receivers.py:143-146`), which has no consent concept. `is_sync_enabled_for_checkout` has
zero callers under `delivery/`.

**Boundary that constrains the design.** `event_journal` "imports nothing from
`specify_cli.delivery`" (`journal.py:19`) and its `Event` record is "deliberately delivery-agnostic"
(`event_journal/models.py:2-9`). Consent is delivery policy. So: the journal gains identity columns as
a *derived data projection* and stays ignorant of consent; the predicate lives in the delivery context
as an injected port modelled on `ReceiverGate`/`GateContext` (`receivers.py:165-203`, "pure data,
never reads globals").

**Testing**: pytest. The recording ingress must advertise a realistic
`sync_ingress.limits.max_events_per_batch` over a host that passes `_should_probe_advertised_limits`
(`sync/batch.py:177-183` returns False for localhost/`.example`, which would elide the batch-window
variable the liveness class depends on — NFR-007). Live verification against `spec-kitty-dev` only.

**Performance**: NFR-003 — 100k rows / 20 projects, no full-table payload decode per drain.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Note |
|---|---|---|
| Additive, backward-compatible schema | Pass by design | C-001; nullable columns only, older CLI keeps reading the DB |
| No destructive migration | Pass by design | C-002; backfill never deletes, purge is an explicit operator act |
| Bounded-context integrity | Pass with named translation layer | C-003; journal stays delivery-agnostic, consent lives in delivery |
| Reuse over reinvention | Pass | Purge routes through `delivery/retention.py`; supersedes `queue.remove_project_events` |
| No production access | Pass | SC-008 pinned to `spec-kitty-dev` |
| Fail-closed defaults | **Requires deliberate inversion** | FR-002 inverts today's default-allow at `routing.py:82-87`; see Complexity Tracking |

## Project Structure

### Documentation (this mission)

```
kitty-specs/journal-project-consent-3030-01KYKWQS/
├── spec.md
├── plan.md
├── research.md          # dual-store trace, four open decisions
├── data-model.md        # journal columns, consent index, conflict rule
└── tasks/
```

### Source Code (repository root)

```
src/specify_cli/
├── delivery/
│   ├── dispatcher.py    # _select_undelivered -> consume filtered read (FR-007/FR-008)
│   ├── receivers.py     # + GateKind.PROJECT_CONSENT, consent port (FR-001)
│   └── retention.py     # purge primitive reused by sync purge (FR-016/FR-017)
├── event_journal/
│   ├── models.py        # + project_uuid / project_slug in ORDERED_COLUMNS (FR-006)
│   └── journal.py       # + filtered read API; migration + backfill (FR-008/FR-009)
├── sync/
│   ├── consent.py       # NEW: uuid-keyed consent index + resolution rule (FR-013)
│   ├── routing.py       # fail closed; write uuid consent on enable/disable (FR-003/FR-013)
│   ├── config.py        # persist uuid-keyed records alongside path-keyed
│   ├── emitter.py       # identity mandatory at journal write (FR-010)
│   ├── background.py    # daemon drain enforces the invariant (FR-012)
│   └── batch.py         # terminal reject classification (FR-014)
└── cli/commands/sync.py # doctor/status/migrate per-project reporting (FR-015), purge (FR-016/17)
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Inverting an established default (`routing.py:87` default-allow → deny for delivery) | The five leaked projects had **no** consent record; a default-allow registry reads them as consented, so the P0 is not closed without the inversion | Keeping default-allow and relying on explicit opt-out requires every user to enumerate every project they *don't* want synced — unbounded, and fails for projects created after the fact |
| A second consent key (uuid) alongside the existing path key | Events carry `project_uuid`; consent is keyed by absolute path (`config.py:216,233`) and no mapping exists. Without a uuid key the predicate has no data source | Deriving uuid from path at read time requires the checkout to exist on disk; a moved or deleted checkout would silently strand the operator's own history |
| Two enforcement points (journal dispatcher + daemon queue drain) | Both drains are live over different stores (`background.py:455-461`) | Covering only the dispatcher leaves the daemon shipping; removing the daemon drain outright is a larger change than this P0 should carry unilaterally — see research decision 1 |

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Containment: fail closed and refuse loudly

- **Purpose**: Convert the silent leak into a refusal with no schema change, so containment ships in
  hours rather than behind a migration.
- **Relevant requirements**: FR-004, FR-005; FR-003 (other paths only — see risk); SC-003
- **Affected surfaces**: a `delivery/dispatcher.py` pre-flight, `cli/commands/sync.py:1001-1049`,
  `sync/routing.py:114-116`, `sync/batch.py:1092-1156` (empty-batch short-circuit and the misleading
  no-Private-Teamspace message at `batch.py:1484-1488`)
- **Sequencing/depends-on**: none — critical path, lands first
- **Risks**: **Containment comes from FR-004 alone, not from the fail-closed gate.** Verified:
  `is_sync_enabled_for_checkout` has zero callers under `delivery/` — its only callers are
  `sync/emitter.py:1890,1921`, `sync/batch.py:338`, `sync/body_upload.py:150` and
  `sync/runtime.py:77`. So FR-003 hardens the emit path, the daemon batch drain and body uploads, but
  **does not touch the drain that leaked**. Do not let FR-003 create a false sense of containment.
  FR-004 is implementable here with no schema change because it inspects only the already-selected
  batch (a bounded set) and resolves identity in-memory from `payload` — the journal's
  `ORDERED_COLUMNS` (`event_journal/models.py:31-40`) carries no identity column, so in-memory
  resolution over a bounded batch is the only option pre-IC-02, and it does not violate NFR-003,
  which constrains full-store decode. Note FR-004 is a no-op on a single-project machine; its value
  is precisely the incident's multi-project case.
- **Honest limit**: this concern makes the leak loud, not fixed. Correct delivery for a
  multi-project machine arrives with IC-04.

### IC-02 — Project identity as a stored, indexed journal column

- **Purpose**: Make consent evaluable in SQL instead of by decoding every payload.
- **Relevant requirements**: FR-006, FR-009, FR-010, FR-011; NFR-003, NFR-004; C-001, C-002, C-003
- **Affected surfaces**: `event_journal/models.py:31-58` (`ORDERED_COLUMNS`),
  `event_journal/journal.py` schema + migration, `sync/emitter.py:1688-1691` (identity enrichment via
  `setdefault`), `emitter.py:2081-2085` (identity-less enqueue), `emitter.py:2150` (nil sentinel)
- **Sequencing/depends-on**: none, but IC-03/IC-04/IC-06 depend on it
- **Risks**: Identity resolves from three sites (`namespace.project_uuid`, top-level, payload —
  `sync/queue.py:1714-1720`); backfill and any recorder must use the same chain or the column and the
  predicate will disagree. The nil UUID must count as unresolvable, not as a groupable value, or the
  backfill writes a consentable identity for identity-less rows.

### IC-03 — Consent index and resolution rule

- **Purpose**: Give the predicate a durable, machine-global data source keyed the way events are.
- **Relevant requirements**: FR-013, FR-002 (FR-002 moved here from IC-01: "absence of a consent
  record denies" cannot be evaluated per-project on the dispatcher path until this index exists,
  because consent is otherwise only readable per-checkout via `routing.py`, which the dispatcher never
  calls)
- **Affected surfaces**: new `sync/consent.py`, `sync/config.py:186-234`,
  `sync/routing.py:64,89-98,130-182` (`enable_checkout_sync`/`disable_checkout_sync` already hold both
  `repo_root` and the resolved uuid at decision time)
- **Sequencing/depends-on**: IC-02 (shares the identity-resolution helper)
- **Risks**: The relation is many-to-one — two checkouts can share a `project_uuid` via a committed
  `.kittify/config.yaml` and hold opposite overrides. Conflict rule is **deny if any checkout of the
  project is opted out**, encoded once, not re-derived per call site. Backfilling path-keyed records
  requires reading each checkout; unreadable paths become "consented but unresolvable" rather than
  silently denied.

### IC-04 — Filtered journal read and the delivery consent gate

- **Purpose**: Put the predicate inside selection, at the seam where delivery is actually decided.
- **Relevant requirements**: FR-001, FR-007, FR-008; NFR-001, NFR-002, NFR-003
- **Affected surfaces**: `event_journal/journal.py` (new `read_all(project_uuids=…)` filtered API),
  `delivery/dispatcher.py:192-223`, `delivery/receivers.py:143-146,165-203` (new `GateKind` + consent
  port), `cli/commands/sync.py:681-686` (`GateContext` construction)
- **Sequencing/depends-on**: IC-02, IC-03
- **Risks**: **Liveness.** The predicate must be applied *before* the row limit. Filtering after
  selection yields an empty batch whenever the oldest window is entirely non-consented, and
  `_should_stop_sync_loop` then ends the drain — permanently stranding consented events behind older
  client rows. This is the most likely way to implement the spec and still ship a defect; NFR-002 and
  SC-002 exist to catch it.

### IC-05 — Operator visibility

- **Purpose**: Make store contents and consent state answerable without hand-querying SQLite.
- **Relevant requirements**: FR-011, FR-015; SC-004
- **Affected surfaces**: `cli/commands/sync.py:3502-3560` (`status`/`diagnose`), `:3906+` (`doctor`),
  `sync/migrate_journal.py` reporting, `delivery/status_report.py:313` (`_event_journal_section`)
- **Sequencing/depends-on**: IC-02 (needs the column); **#3004** folded in first
- **Risks**: `doctor`'s queue-health block reads `OfflineQueue().get_queue_stats()`
  (`cli/commands/sync.py:3619-3627`) and `diagnose` reads `OfflineQueue()` (`:3531-3534`) — both empty
  after `sync migrate`, which is exactly why `doctor` read healthy during the incident. Reconcile
  against the journal's retained count (`_count_retained_events`, `cli/commands/sync.py:714-717`) or
  the new report inherits the false-green.

### IC-06 — Purge

- **Purpose**: Let the operator remove non-consenting data locally.
- **Relevant requirements**: FR-016, FR-017; NFR-006; C-004
- **Affected surfaces**: `delivery/retention.py:51,150,189` (`_PURGE_SQL`, `gc_payloads`,
  `_purge_journal_rows`), the delivery ledger (`SqliteDeliveryLedger`, path at
  `cli/commands/sync.py:535`), new `sync purge` command
- **Sequencing/depends-on**: IC-02; independent of IC-03/IC-04, so it can be pulled forward despite
  its P2 label
- **Risks**: Purge spans **two** stores — journal rows and ledger history. The spec's "delivered,
  rejected and undelivered" are ledger concepts, not journal columns (the journal knows only
  `archived_at`, `models.py:27`). `journal.py:5-8` states the journal "never deletes a payload on the
  normal path", so destructive work routes through `retention.py`. Research decision 2 settles whether
  ledger history survives a purge.

### IC-07 — Terminal reject classification (cross-repo)

- **Purpose**: Let a server refusal be classified permanent so the drain stops retrying, unblocking
  `saas#585` FR-004.
- **Relevant requirements**: FR-014; SC-009; C-007 exception
- **Affected surfaces**: `sync/batch.py:414-418` (today the only `failed_permanent` producer),
  `:885-899` (per-event results), `:934-952` (400 details), `queue.py:1780-1805`
  (`process_batch_results` maps `rejected` → `retry_count + 1`, never deletes)
- **Sequencing/depends-on**: none; deliverable in parallel
- **Risks**: There is no retry ceiling on the drain path — `get_events_by_retry_count`
  (`queue.py:1820-1841`) exists but `drain_queue` has no `retry_count` predicate. Without this
  concern a refused project pins the FIFO head forever. Folds #3005.

### IC-08 — Daemon drain parity

- **Purpose**: Ensure the second live drain cannot ship non-consenting events.
- **Relevant requirements**: FR-012; SC-005
- **Affected surfaces**: `sync/background.py:395,455-461,589-592`, `sync/batch.py:1064-1080`
- **Sequencing/depends-on**: IC-03 (needs the consent index); IC-01 supplies the fail-closed gate
- **Risks**: Enforce on the queue drain, or remove the queue drain. Removal converges on the canonical
  surface, but `queue.py:1-12` warns that removing it before the journal dispatcher is fully
  authoritative "would strand in-flight events". Research decision 1.

### IC-09 — Documentation

- **Purpose**: Stop recommending a machine-global export without a warning.
- **Relevant requirements**: FR-018
- **Affected surfaces**: sync docs env-var reference
- **Sequencing/depends-on**: none
- **Risks**: Must be CI-checkable (anchor test) or it silently rots.

## Open decisions for research

1. **Daemon drain: enforce or remove?** (IC-08) — governs whether FR-012 is a gate or a deletion.
2. **Ledger history on purge: retain or remove?** (IC-06) — affects NFR-006's differential count.
3. **Consent-index storage**: extend `SyncConfig`'s YAML, or a separate SQLite index? YAML matches
   today's records; SQLite indexes better for the per-project report at scale.
4. **Is egress-only sufficient?** C-006 records that collection continues after this mission. Operator
   decision, not an implementation choice — surfaced, not assumed.

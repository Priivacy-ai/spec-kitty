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

**One shared identity resolver, named before slicing.** Three consumers need the *identical*
resolution chain and NFR-001 demands they agree: FR-004's pre-flight (in `delivery/`), FR-009's
backfill, and FR-013's consent writer (in `sync/`). But the canonical implementation
`_resolve_event_or_payload` is **module-private to `sync/queue.py`** (`queue.py:122-128,1714-1722`),
and `delivery/dispatcher.py:34` states it "imports nothing from `sync/queue.py`" while `event_journal`
may import nothing from `delivery` (`journal.py:19`). With no named home each work package will copy
it. **Decision**: promote it to `sync/project_identity.py` — today a 29-line re-export shim, and a
neutral module `delivery/targets.py:56` already precedents importing from `specify_cli.sync.*`. Ship a
test asserting a single definition site. `event_journal` importing `sync` needs an explicit charter
note if the backfill lives there; prefer putting the backfill in `sync/` to avoid that.

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
| Bounded-context integrity | Pass with named translation layer | C-003 (restated): journal carries no *target* identity; it already stores an eligibility verdict, so consent must extend that vocabulary or be explicitly a second one |
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
- **Relevant requirements**: FR-001, FR-004, FR-005; FR-003 (other paths only — see risk); SC-003.
  **FR-001 moved here from IC-04**: `GateContext` is four run-scoped booleans with no project dimension
  and `evaluate_gates` yields one `GateDecision` per receiver per run, which aborts the whole drain
  (`cli/commands/sync.py:1032-1046`). So a `GateKind` can only express machine-level facts — "consent
  unresolvable" or "this batch spans projects" — never "project X consented". IC-04 keeps only the
  per-project seam (FR-007/FR-008).
- **Second leak class, closed here, migration-free.** The journal already stores a delivery-eligibility
  verdict: `classify_drain_blocked_reason(gate: CaptureGateState)` (`event_journal/journal.py:338`) maps
  `saas_enabled`/`checkout_enabled`/`authenticated`/`team_slug` onto the `drain_blocked_reason` column
  (`models.py:26`, in `ORDERED_COLUMNS`). Verified that `delivery/` **never reads it** — `read_all()`
  returns blocked rows and `read_blocked()` (`journal.py:268`) exists only for diagnostics. So events
  captured while a checkout was opted out are already stamped `DRAIN_BLOCKED_SAAS_DISABLED`
  (`journal.py:345`, which reads `gate.checkout_enabled`) **and shipped anyway**. Exclude non-null
  `drain_blocked_reason` from `_select_undelivered`'s universe. No schema change, and it closes a leak
  class the original spec never named.
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
- **Relevant requirements**: FR-006, FR-009; FR-011 (the unresolved-identity **count**; IC-05 owns its
  surfacing); NFR-003, NFR-004, NFR-005; C-001, C-002, C-003
- **FR-010 is split out of this concern — as stated it is unsatisfiable.** "Identity mandatory at
  journal write" contradicts NFR-005 ("no event dropped at write time"), contradicts
  `sync/emitter.py:2081-2085` which deliberately routes identity-less events to the *legacy* queue
  (so they land on the IC-08 drain, not the journal), and contradicts `emitter.py:2150` which
  substitutes the nil sentinel this concern's own risk note says must count as unresolvable. Mandatory
  identity + never drop + nil-is-unresolvable cannot all hold. Restate FR-010 as: *the journal write
  requires identity, and identity-less capture is stamped into a named non-deliverable state* — which
  `drain_blocked_reason` can already express (see IC-01).
- **Affected surfaces**: `event_journal/models.py:31-58` (`ORDERED_COLUMNS`),
  `event_journal/journal.py` schema + migration, `sync/emitter.py:1688-1691` (identity enrichment via
  `setdefault`), `emitter.py:2081-2085` (identity-less enqueue), `emitter.py:2150` (nil sentinel)
- **Sequencing/depends-on**: none, but IC-03/IC-04/IC-06 depend on it
- **BLOCKER, decided here: the journal has no schema-migration mechanism.** `_ensure_schema`
  (`event_journal/journal.py:209-214`) runs only `CREATE_TABLE_SQL` plus two
  `CREATE INDEX IF NOT EXISTS` — no `ALTER`, no `PRAGMA user_version`, no `table_info` probe. And
  `INSERT_SQL`, `SELECT_ALL_SQL`, `SELECT_BY_ID_SQL` and `SELECT_BLOCKED_SQL` are **all** derived from
  `_COLUMN_LIST` (`event_journal/models.py:41,77-80`). So adding the columns to `ORDERED_COLUMNS`
  without a migration bricks **every existing journal file** on first read —
  `CREATE TABLE IF NOT EXISTS` is a no-op on an existing table, so `sync status`, `sync now` and the
  backfill itself would raise `no such column: project_uuid`. The Charter Check's
  "older CLI keeps reading the DB" verifies only the reverse direction.
  **Required**: an additive migration inside `_ensure_schema` (so it is unconditional on construction
  and `get_journal`'s cache cannot skip it), idempotent, running before any use of the derived SQL
  constants, reusing the in-repo precedent at `sync/queue.py:1242-1248`
  (`PRAGMA table_info(...)` → `ALTER TABLE … ADD COLUMN`). Ship a test that opens a **pre-migration**
  journal file and reads it successfully.
- **Risks**: Identity has a **fourth** site the canonical chain misses: `_enrich_proof_subject` writes
  `payload["subject"]["project_uuid"]` (`sync/emitter.py:2037,2048-2049`), which
  `_resolve_event_or_payload`'s chain (`namespace.project_uuid` → top-level → `payload.project_uuid`,
  `sync/queue.py:1714-1720`) never inspects. `envelope_fields` can also overwrite the top-level value.
  The exact chain must be **one ordered constant list** in the shared resolver, with a fixture per
  site, or backfill and predicate will silently disagree — the single likeliest divergence in this
  mission. The nil sentinel `00000000-0000-0000-0000-000000000000` (`emitter.py:2150`) normalizes to
  NULL at both write and backfill, so it is never a groupable, consentable value.

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
  project is opted out**, encoded once, not re-derived per call site.
- **Decided here (three invention points closed):**
  1. **Unresolvable paths need a storage representation.** uuid resolution requires
     `load_identity(repo_root/".kittify"/"config.yaml")` (`routing.py:64`), so an absent or unreadable
     path yields **no key at all** — at the predicate that is indistinguishable from "no record", i.e.
     deny, while US2 scenario 3 promises to *report* it as "consented but unresolvable". Retain the
     path-keyed entry with an `unresolved` marker that FR-015 renders and the predicate ignores, so
     reported state and enforced state agree.
  2. **`enable_checkout_sync` with no resolvable uuid must fail loudly.**
     `_build_checkout_sync_routing` yields `None` when identity carries no uuid (`routing.py:91`).
     Writing only the path-keyed record under FR-002's inversion would leave the uuid index empty and
     silently never deliver the user's own explicitly opted-in project — the exact failure the
     Complexity Tracking row exists to avoid. `enable_checkout_sync` already calls `resolve_identity`,
     so it either mints identity or errors; it must not half-succeed.
  3. **Research decision 3 is consequential, and is resolved here to a batched write.** Every
     `SyncConfig` setter is a whole-file read-modify-write (`config.py:198-234`) with no visible
     locking, and the daemon (`sync/background.py`) writes the same file as an interactive
     `sync enable`. A lost record is now a **silent delivery denial**, not a cosmetic loss, and a
     backfill over N paths would be N full cycles. Keep YAML (it matches today's records) but perform
     the backfill as a **single batched write**, and state the concurrency assumption explicitly.

### IC-04 — Filtered journal read and the delivery consent gate

- **Purpose**: Put the predicate inside selection, at the seam where delivery is actually decided.
- **Relevant requirements**: FR-007, FR-008; NFR-001, NFR-002, NFR-003, NFR-007; SC-001, SC-002
  (FR-001 relocated to IC-01 — `GateContext` has no project dimension)
- **Affected surfaces**: `event_journal/journal.py` (new `read_all(project_uuids=…)` filtered API),
  `delivery/dispatcher.py:192-223`, `delivery/receivers.py:143-146,165-203` (new `GateKind` + consent
  port), `cli/commands/sync.py:681-686` (`GateContext` construction)
- **Sequencing/depends-on**: IC-02, IC-03
- **Decided here: the filtered read is an identity projection and takes NO `LIMIT`.** Verified that
  `ledger.select_undelivered` fetches the full terminal-id set and slices the already-filtered
  universe, so moving the project predicate into the journal read composes correctly **as long as no
  `LIMIT` is pushed into the filtered SQL**. Pushing one in — the obvious next optimization for
  NFR-003 — reintroduces the exact starvation NFR-002 bans: already-delivered terminal rows would fill
  the SQL window and then be stripped by the ledger, yielding an empty selection while consented
  undelivered rows sit behind them. The ledger is a **separate SQLite file**
  (`cli/commands/sync.py:535`), so no join can rescue it. Therefore: the filtered read returns
  `event_id`, `created_at`, `project_uuid` (no payload BLOB) to build the universe, and payloads are
  hydrated via `read_by_id` over the ledger-selected batch only. That also satisfies NFR-003's intent
  rather than its letter — an unlimited filtered read that still materializes every payload of a
  100k-row project would pass the letter and miss the point.
- **Risks**: **Liveness**, per the above — NFR-002 and SC-002 exist to catch it, and SC-002 should be
  written red-first at this seam. **Dual authority on NULL identity**: SQL `WHERE project_uuid IN (…)`
  never matches NULL, so a legacy or nil-sentinel row is invisible here while IC-01's in-memory
  FR-004 check often resolves it — the same event would be "deliverable" on one path and "denied" on
  the other. Pinned rule: post-backfill the **stored column is the sole authority for selection**; the
  in-memory chain is used only by FR-004's refusal check and by the backfill. NULL rows are
  permanently unselectable and counted under FR-011, not lazily re-resolved.

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
- **Sequencing/depends-on**: **undetermined until research decision 1 is answered — which is why that
  decision must be resolved before `/spec-kitty.tasks`.** If the answer is *enforce*, this depends on
  IC-03. If the answer is *remove*, it has **no** dependency on IC-03, needs no schema, and is the
  single highest-value containment action available — it deletes an entire leaking drain — so it
  belongs in the containment wave beside IC-01. The current sequencing silently assumes *enforce*.
- **Risks**: `queue.py:1-12` warns that removing it before the journal dispatcher is fully authoritative
  "would strand in-flight events" — that is the argument to weigh. Note C-004 couples IC-06 to the same
  decision ("treat `queue.remove_project_events` as superseded and remove it").

### IC-10 — Live verification (owns the anti-fake-green controls)

- **Purpose**: Prove the invariant against a real server, not a fake, and own the criteria that no
  other concern claimed.
- **Relevant requirements**: NFR-007; SC-008
- **Affected surfaces**: test harness for the recording ingress; a live two-project drain against
  `spec-kitty-dev`
- **Sequencing/depends-on**: IC-04
- **Risks**: A coverage audit found NFR-007 and SC-008 owned by **no** concern — unowned by an IC means
  unowned by a work package means never executed, which is exactly how a fake-green ships. NFR-007
  matters because `_should_probe_advertised_limits` (`sync/batch.py:177-183`) returns False for
  localhost and `.example`, so a naive fake never applies `max_events_per_batch` — the variable that
  decides whether non-consented rows fill the selection window. SC-008's deliverable is the **captured
  server-side aggregation output**, not a green test. Never production (`docs/production-safety-guardrails.md`).

### IC-09 — Documentation

- **Purpose**: Stop recommending a machine-global export without a warning.
- **Relevant requirements**: FR-018
- **Affected surfaces**: sync docs env-var reference
- **Sequencing/depends-on**: none
- **Risks**: Must be CI-checkable (anchor test) or it silently rots.

## Open decisions for research

1. **Daemon drain: enforce or remove?** (IC-08) — governs whether FR-012 is a gate or a deletion.
   **Still open.**
2. **Ledger history on purge: retain or remove?** (IC-06) — affects NFR-006's differential count.
   **Still open.**
3. ~~**Consent-index storage**: YAML or SQLite?~~ **Resolved** in IC-03: keep YAML, backfill as a
   single batched write. It was not cosmetic — `SyncConfig` setters are unlocked whole-file
   read-modify-writes and a lost record is now a silent delivery denial.
4. **Is egress-only sufficient?** C-006 records that collection continues after this mission. Operator
   decision, not an implementation choice — surfaced, not assumed. **Still open.**
5. **Where does the backfill live** — `sync/` or `event_journal/`? Prefer `sync/`, so `event_journal`
   never imports `sync` and the C-003 boundary stays clean.

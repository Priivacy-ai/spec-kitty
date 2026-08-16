# Data Model: Legacy→Journal Capture Cutover

Behavioral / state model for the capture surface (revised post-squad). No new persistent
schema; this documents entities, the layout state machine, and the invariants the
implementation must preserve. Cutover **reuses** `migrate_journal` /
`project_store_migration` — this model describes the states around those engines, not a
new copy engine.

## Entities

### LayoutState (per repository-root checkout)

- **`.initialized` marker** (`marker_path`): durable "this root has been initialized"
  signal. **Its presence does NOT mean "migrated"** — a greenfield root gets it written
  on first read.
- **`.layout-generation.json` record** (`record_path`): `generation`, `mode`
  (`LEGACY` | `CUTOVER_PENDING` | `PROJECT_ONLY`), `migration_id`, `updated_at`.
- **Current bug**: `_read_locked` on a fresh root writes `_initial_state()` = `LEGACY`
  + marker, so the "never migrated" signal self-destructs on first emit.
- **Target**: the no-legacy-data decision runs **before** that LEGACY write, so a
  greenfield root is published `PROJECT_ONLY` and never persists LEGACY.

### LegacyQueue (source, preserved)

- **Store**: legacy `queue.db` + scoped `queue-<digest>.db`, discovered via
  `migrate_journal.discover_source_dbs`.
- **Role**: migration input only; **rows never deleted** (C-002, #2750 out of scope).
  Consequence: honest `sync now` convergence (#3278) is **deferred** — copy-without-delete
  cannot converge the legacy-row boundary (documented at `migrate_journal.py:40-52`).

### EventJournal / ProjectSyncStore (authoritative destination)

- **Store**: per-project event journal selected by ProjectSyncStore (#3293 — kept).
- **Guard**: `_require_project_destination` (`journal.py:117-119`,
  `ProjectLayoutRequiredError`) — live writes require `PROJECT_ONLY`.
- **Dedup**: `append` idempotence keys on `event_id`; cutover dedup keys on
  `(event_id, source_digest)` (IC-00).

### Credentials → auth signal (not a path)

- `read_queue_scope_from_credentials` yields a boolean "authenticated?" for the setup-plan
  gate. It must NOT drive `scope_db_path(...)` at `preflight.py`/`target_authority.py`
  (C-003/FR-009 revert-risk).

## Layout State Machine

```
   marker/record absent
          │
          ▼  detect legacy data (real reader: discover_source_dbs + row counts)
   ┌──────────────┐   no legacy data      ┌──────────────┐
   │ (unresolved) │ ────────────────────▶ │ PROJECT_ONLY │  live writes land (terminal)
   └──────────────┘   (decided BEFORE      └──────────────┘
          │            any LEGACY persist)        ▲
          │ legacy data present                   │ migrate_journal / project_store_migration
          ▼                                        │ (stable migration_id, dedup, attribution)
   ┌──────────────┐  begin_cutover   ┌──────────────────┐  publish_project_only
   │    LEGACY    │ ───────────────▶ │  CUTOVER_PENDING │ ─────────────────────▶ PROJECT_ONLY
   │(migration    │                  │ live writes:     │
   │  input)      │                  │ block-and-retry, │  crash here ⇒ re-enter same
   └──────────────┘                  │ then loud (never │  migration_id, complete/retry
          ▲                          │ silent LEGACY)   │  (never brick)
          │ SPEC_KITTY_NO_AUTO_CUTOVER└──────────────────┘
          │ ⇒ stay LEGACY, surface loud actionable refusal (manual migrate)
```

## Invariants (must always hold)

- **INV-1 (no silent success)**: no capture path returns success while journaling zero
  events (FR-001/NFR-001).
- **INV-2 (conservation)**: after cutover, every pre-existing legacy event appears in the
  authoritative store exactly once — 0 loss, 0 duplication, incl. ownerless rows
  (FR-003/FR-005/NFR-002). Guaranteed by reusing the engines' copy-verify-under-lock.
- **INV-3 (idempotence / crash-safety)**: an interrupted cutover re-enters the same
  `migration_id` and converges with no extra/divergent writes; a crash never bricks the
  root (NFR-005).
- **INV-4 (source preservation)**: legacy rows are read, never deleted (C-002). (Verified:
  the current engine only unlinks temp scratch files.)
- **INV-5 (no mid-cutover drop)**: a live write arriving during `CUTOVER_PENDING` must not
  silently route to LEGACY-and-swallow — it blocks-and-retries, then surfaces loudly.
  *(Replaces the deferred honest-sync-now invariant.)*
- **INV-6 (selection preserved)**: ProjectSyncStore-owned queue selection is unchanged
  (#3293 kept — C-003/FR-009); restoring credential parsing does not change which physical
  store a live write lands in.

## Cutover Transitions (auto, reusing canonical engines)

1. On first live write, resolve layout (before any LEGACY persist).
2. `PROJECT_ONLY` → write (done).
3. Unresolved + no legacy data (real reader) → publish `PROJECT_ONLY` → write.
4. Legacy data present + escape hatch unset → `begin_cutover` (deterministic
   root-derived `migration_id`) → **copy via `migrate_journal`/`project_store_migration`**
   (dedup `(event_id, source_digest)`, attribute `project_uuid` to ownerless rows,
   quarantine divergent payloads; **source retained**) → `publish_project_only` → write.
   Live writes during `CUTOVER_PENDING`: block-and-retry, else loud. Re-entrant on crash.
5. Legacy data present + `SPEC_KITTY_NO_AUTO_CUTOVER` set → do not mutate; surface a loud,
   actionable refusal pointing at `sync project-store-migrate` (never silent).

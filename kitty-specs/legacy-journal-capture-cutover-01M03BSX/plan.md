# Implementation Plan: Legacy→Journal Capture Cutover

**Branch**: `fix/legacy-journal-capture-cutover` | **Date**: 2026-08-15 (rev. post-squad) | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/legacy-journal-capture-cutover-01M03BSX/spec.md`

## Summary

Un-migrated machines default to a legacy capture layout, so live event/body writes are
refused and swallowed — silent zero-capture while reporting success (#3425). A #3293
regression also narrowed credential parsing so authenticated hosts are refused. This
mission restores credential parsing (auth-signal only, no path-derivation revert),
resolves fresh roots to `project_only` **before** any LEGACY write is persisted,
auto-migrates legacy-with-data roots by **reusing the canonical migration engines**
(`migrate_journal` / `project_store_migration`) — never a bespoke drain — deduplicating
the copy (#2846), surfaces cutover/backfill failures loudly (#3476), and makes capture
failure observable at the command boundary via the emitter (folds #3391). It rewrites
the mis-built #3425 reproductions to the real contract and keeps #3293's ProjectSyncStore
selection (no revert). **Honest `sync now` convergence (#3278) is deferred** (it requires
legacy-row cleanup / #2750, out of scope).

> This plan was revised after a post-plan adversarial squad (architecture/SSOT,
> test-strategy, risk/data-safety). Findings + remediations:
> `work/3425-legacy-layout-research/post-plan-squad/` (gitignored).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing only — SQLite (`sqlite3`), `filelock`; **canonical migration engines reused, not added**: `src/specify_cli/sync/migrate_journal.py` (`migrate_queues_to_journal`, `discover_source_dbs`, `(event_id, source_digest)` provenance, divergent-duplicate quarantine) and `src/specify_cli/sync/project_store_migration.py` (`MigrationPhase` state machine, snapshot/fingerprint, `project_uuid` attribution). **No dependency add/upgrade/removal.**
**Storage**: SQLite (event journal + legacy `queue.db` / `queue-<digest>.db`), filesystem markers (`.layout-generation.initialized` marker + `.layout-generation.json` record) per checkout
**Testing**: pytest, red-first (C-011). **Isolation is mandatory** — all cutover/layout tests run against temp roots via `SPEC_KITTY_HOME`/`HOME` fixtures; **never** the real machine-global `~/.spec-kitty` (this dev box is itself a live legacy root — see Risk note)
**Target Platform**: Linux, macOS, Windows 10+ CLI
**Project Type**: single (`src/specify_cli/`)
**Performance Goals**: cutover runs at most once per root; lock-hold bounded to the copy; no measurable hot-path cost on already-migrated roots
**Constraints**: zero event loss/duplication incl. ownerless legacy rows (NFR-002); lock-safe + idempotent + crash-recoverable, never bricking a root (NFR-005); emitter fix stays non-fatal while becoming boundary-observable (FR-010); keep ProjectSyncStore selection (C-003); legacy write path not retired, source rows never deleted (C-002)
**Scale/Scope**: per-machine roots; bounded event counts

### Supply-Chain Security (advisory — issue 051)

No dependency add/upgrade/removal. All changes are first-party `src/specify_cli/sync/**`,
`src/specify_cli/event_journal/**`, `src/specify_cli/cli/commands/agent/**`, and tests.
Registry/lifecycle/freshness checks N/A. Explicit examination, not silence.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| Single canonical authority | ✅ (fixed) | Cutover **reuses** `migrate_journal`/`project_store_migration` rather than re-deriving dedup/provenance/quarantine — the post-squad correction of the original plan's canonical-source violation. |
| Use canonical sources, never improvise | ✅ (fixed) | Prior draft reinvented the migration engines; now cites the canonical entry points as the copy mechanism. |
| ATDD-first / red-first (C-011) | ✅ | Red-first tests for idempotence-under-interruption, zero-loss/dup conservation, mid-cutover concurrency, and the escape hatch — not just happy-path integration. Test A rewritten but keeps its behavioral pins. |
| Regression vigilance | ✅ | Fixes the real #3293 credential regression; NFR-004 pins on-branch green **including** the ~80 LEGACY-referencing files outside the blocking selection (coordinated-update set enumerated in tasks). |
| Ownership boundaries for mutating flows | ✅ | Auto-cutover is idempotent, crash-recoverable (defined `CUTOVER_PENDING`/`FAILED` recovery), non-destructive; emitter fix (#3391) coordinated with assignee (MOES-Media). |
| Pre-existing failure reporting | ✅ | Distinguishes the real #3293 regression from CI-env auth artifacts (research.md). |

**No charter violations after revision.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/legacy-journal-capture-cutover-01M03BSX/
├── plan.md · research.md · data-model.md · quickstart.md
└── tasks.md   # /spec-kitty.tasks — NOT created here
```

### Source Code (repository root)

```
src/specify_cli/sync/
├── layout_generation.py        # resolve BEFORE persisting LEGACY on greenfield; CUTOVER_PENDING window (IC-02)
├── migrate_journal.py          # REUSED copy engine — discover_source_dbs, (event_id,source_digest) dedup, quarantine (IC-00/02/03)
├── project_store_migration.py  # REUSED — MigrationPhase, project_uuid attribution for ownerless rows (IC-00/02)
├── queue.py                    # read_queue_scope_from_credentials (IC-01); detectors detect_legacy_rows_for_scope (stub→real, IC-02)
├── preflight.py                # credential→scope consumers split("|") / scope_db_path (IC-01, revert-risk seam)
├── target_authority.py         # _read_cached_scope / build_queue_scope → scope_db_path (IC-01, revert-risk seam)
├── consent.py                  # per-project consent (touch only if scope-derivation requires)
└── emitter.py                  # BOTH swallow sites: _capture_to_journal (~2114) + _emit_for_project_context (~2334-2336); process-level captured-failure flag (IC-05)
src/specify_cli/event_journal/journal.py   # _require_project_destination guard; append() event_id idempotence (IC-02/03)
src/specify_cli/cli/commands/agent/mission_setup_plan.py  # FR-011 auth gate: consume boolean auth-signal, not a derived path (IC-01)

tests/
├── regression/test_issue_3425_setup_plan_legacy_layout_silent_capture.py  # rewritten, attribution corrected (IC-06)
├── sync/                       # layout resolution, credential parsing, cutover concurrency/idempotence/conservation, escape hatch
└── event_journal/              # journal guard + dedup
```

**Structure Decision**: Single CLI project, confined to the sync + event-journal surface
changed by #3293 plus the setup-plan auth gate. No new packages.

## Complexity Tracking

*No Charter Check violations after revision — table intentionally empty.*

## Engineering Alignment (confirmed + post-squad revisions)

- **Scope** (user-confirmed): fix #3425 (silent-capture) + credentials regression + #2846
  dedup + #3391 emitter + #3476 loud cutover. **Deferred:** #3278 honest sync-now (needs
  legacy-row cleanup / #2750). **Out:** retiring legacy `queue.db` (#2750).
- **Auto-cutover — reuse canonical engines, stable id, crash-safe (BLOCKER-1/2, risk-1)**:
  the lazy first-write cutover calls `migrate_journal.migrate_queues_to_journal` /
  `project_store_migration` with a **deterministic, root-derived `migration_id`** and
  **auto-discovered source** (`discover_source_dbs`), not operator-supplied args. Recovery
  is defined: a `CUTOVER_PENDING` root re-enters and completes the same migration_id
  (idempotent); a `FAILED` manifest is cleared/retried under a documented rule — a crash
  between begin and publish must never brick the root.
- **Close the mid-cutover drop window (BLOCKER-2)**: live writes arriving while
  `mode == CUTOVER_PENDING` must NOT resolve to LEGACY-and-swallow. Chosen model:
  **block-and-retry within a bounded wait**, and if cutover cannot complete, route to the
  loud emitter surface (IC-05) — never silent. A red-first test emits *during* an
  in-progress cutover and asserts zero loss.
- **Detection before LEGACY persist (MAJOR-5)**: the "no-legacy-data ⇒ `project_only`"
  decision happens **before** `_initial_state` writes LEGACY in `_read_locked`, so a
  greenfield root never persists LEGACY on first emit. Detection uses the real reader
  (`migrate_journal.discover_source_dbs` + queued-row counts), not the stub
  `detect_legacy_rows_for_scope`. Data-model corrected to the `.initialized` marker.
- **Emitter observability (MAJOR-3, FR-010)**: fix **both** swallow sites; deliver
  boundary observability via a **process-level captured-failure flag/counter** the command
  epilogue inspects (and non-zero-exits or reports on), threaded without changing the ~30
  `emit_*` signatures or `_emit`'s never-raises contract. Coordinate the seam with #3391.
- **IC-01 auth-signal vs path derivation (MAJOR-4)**: the setup-plan gate needs a boolean
  "authenticated?", not a live scope→path. Restoring parsing must NOT re-introduce
  credential→`scope_db_path` derivation at `preflight.py`/`target_authority.py` (that is
  the C-003/FR-009 revert). A test asserts restoring parsing does not change which physical
  store a live write lands in.
- **Dedup identity is foundational (MAJOR-6)**: ownerless legacy rows must acquire a
  `project_uuid` (via `project_store_migration` attribution) before/at copy; dedup keys on
  `(event_id, source_digest)`. This precedes the cutover copy (IC-00), inverting the
  original IC-02→IC-03 order.
- **Test isolation (risk MINOR-8)**: this dev box's `~/.spec-kitty` is a live machine-global
  legacy root; every cutover/layout test MUST use isolated temp roots. No test or manual
  step may run cutover against the real store.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-00 — Dedup identity + ownerless-row attribution (foundation)

- **Purpose**: Pin the stable copy identity so the cutover copy cannot duplicate or drop, including legacy rows that predate per-project ownership.
- **Relevant requirements**: FR-005 (#2846); NFR-002.
- **Affected surfaces**: `migrate_journal.py` (`(event_id, source_digest)` provenance, quarantine), `project_store_migration.py` (`project_uuid` attribution), `journal.py` `append` idempotence, `queue.py` `queue_event` owner check (346-348).
- **Sequencing/depends-on**: none — precedes IC-02 copy.
- **Risks**: ownerless legacy rows raise "project UUID does not match store owner" on naïve copy — attribution must run first.

### IC-01 — Restore credential→scope parsing as an AUTH SIGNAL (no path revert)

- **Purpose**: Stop the auth gate refusing authenticated hosts, WITHOUT re-introducing credential→path derivation (C-003/FR-009).
- **Relevant requirements**: FR-004, FR-009; NFR-004, SC-002.
- **Affected surfaces**: `queue.py` `read_queue_scope_from_credentials`; `mission_setup_plan.py` gate; **`preflight.py:480/516`, `target_authority.py:401/466`** (revert-risk consumers); possibly `consent.py`.
- **Sequencing/depends-on**: none (independent un-redder).
- **Risks**: the pre-#3293 `server|user|team` piped form flows into `scope_db_path` — must gate to auth-signalling only; test physical-store invariance.

### IC-02 — Layout resolution + canonical, crash-safe auto-cutover

- **Purpose**: Fresh→`project_only` before any LEGACY persist; legacy-with-data→cutover via the canonical engine with stable id, closed drop window, and defined recovery.
- **Relevant requirements**: FR-002, FR-003; NFR-002, NFR-005; SC-001, SC-004, SC-005.
- **Affected surfaces**: `layout_generation.py` (`_read_locked` order, `_destination`, `begin_cutover`/`publish_project_only`, `CUTOVER_PENDING` write routing), `migrate_journal`/`project_store_migration` (invoked), `queue.py` real detector.
- **Sequencing/depends-on**: IC-00 (identity), IC-01 (scope signal).
- **Risks**: bricking on crash mid-cutover; concurrency at the first-write trigger; the LEGACY default is heavily test-pinned.

### IC-03 — Divergent-duplicate elimination (#2846)

- **Purpose**: Guarantee the cutover copy yields exactly one authoritative record per event; quarantine genuine divergent payloads rather than dropping.
- **Relevant requirements**: FR-005 (#2846); NFR-002.
- **Affected surfaces**: reuse `migrate_journal` quarantine; `journal.py` idempotence. (No `sync now` change — #3278 deferred.)
- **Sequencing/depends-on**: IC-00, IC-02.
- **Risks**: divergent-payload conflicts must quarantine, not silently last-write-win.

### IC-04 — Loud cutover / backfill failures (#3476)

- **Purpose**: Cutover/backfill writes that cannot land surface the failure, distinguishable from a legitimate already-migrated no-op.
- **Relevant requirements**: FR-007; NFR-001.
- **Affected surfaces**: backfill-runtime-state path + `layout_generation.py` cutover write.
- **Sequencing/depends-on**: IC-02.
- **Risks**: must not flag a legitimate no-op as failure.

### IC-05 — Observable emitter capture failure (folds #3391)

- **Purpose**: No silent-success capture: fix **both** swallow sites and surface a genuinely-unrecoverable failure at the command boundary via a process-level flag — non-fatal.
- **Relevant requirements**: FR-001, FR-010; NFR-001.
- **Affected surfaces**: `emitter.py` `_capture_to_journal` (~2114) + `_emit_for_project_context` (~2334-2336); a captured-failure flag/counter + command-epilogue inspection.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: must not break `_emit`'s never-raises contract (~30 callers); rate-limit so the loud path can't warning-storm; coordinate with #3391 assignee (MOES-Media).

### IC-06 — Rewrite #3425 reproductions to the real contract (+ hard-invariant coverage)

- **Purpose**: Turn the mis-built red-first tests green against the real ProjectSyncStore contract while KEEPING the behavioral pins (journal conservation + warning-absence); add the missing red-first invariant tests; un-red the blocking gate.
- **Relevant requirements**: FR-008, FR-009; NFR-003, NFR-004; SC-003.
- **Affected surfaces**: `tests/regression/test_issue_3425_*` (correct attribution to `journal.py:119 ProjectLayoutRequiredError`, drop retired no-arg queue API, keep end-to-end assertions); new red-first tests for idempotence-under-interruption, zero-loss/dup conservation, mid-cutover concurrency, escape hatch; enumerate + update the ~80 LEGACY-referencing files (`tests/sync`, `event_journal`) outside the blocking selection; pin auth tests on `SPEC_KITTY_HOME` (not just `HOME`).
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: a green blocking gate can mask NFR-003/004 reds in the non-blocking suites — the coordinated-update set must be explicit; rewritten tests must stay behavioral, not permit-enum assertions.

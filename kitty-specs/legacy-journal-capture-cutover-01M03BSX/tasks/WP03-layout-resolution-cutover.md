---
work_package_id: WP03
title: Layout resolution + canonical crash-safe auto-cutover
dependencies:
- WP01
- WP02
requirement_refs:
- FR-002
- FR-003
planning_base_branch: fix/legacy-journal-capture-cutover
merge_target_branch: fix/legacy-journal-capture-cutover
branch_strategy: Planning artifacts for this mission were generated on fix/legacy-journal-capture-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/legacy-journal-capture-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
history:
- at: '2026-08-15T00:00:00Z'
  actor: claude
  note: WP authored by tasks phase
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/sync/test_layout_cutover.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/layout_generation.py
- tests/sync/test_layout_cutover.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your operating profile:

```
/ad-hoc-profile-load implementer-ivan
```

This binds your identity, boundaries, and governance scope for the whole work
package. Do not begin editing code or tests before the profile is loaded — the
profile carries the red-first (C-011) and canonical-source discipline this WP
lives or dies by. If the load fails, stop and surface it; do not improvise a
substitute role.

## Objective

This is the **P0 core** of the mission (IC-02 in `plan.md:155-161`). It closes the
silent zero-capture defect (#3425) at its origin: the layout-resolution state machine
in `src/specify_cli/sync/layout_generation.py`.

Deliver three behaviors, in this exact ordering of concern:

1. **Fresh roots journal by default (FR-002).** A greenfield repository-root checkout
   — no `.layout-generation.json` record and **no legacy data** — must resolve to
   `PROJECT_ONLY` **before** any `LEGACY` state is persisted. Today `_read_locked`
   (`layout_generation.py:176-188`) writes `_initial_state()` = `LEGACY` on the very
   first read, so the "never migrated" signal self-destructs and the root is stuck
   `LEGACY` forever (leaving `LEGACY` is manual-only). The greenfield decision must be
   made and published *ahead of* that write, so a fresh root emits its first event and
   the journal actually contains it (currently: zero).

2. **Legacy-with-data roots auto-migrate via the canonical engines (FR-003).** A root
   that holds real legacy queue data is auto-migrated lazily on first live write by
   **reusing** `migrate_journal.migrate_queues_to_journal` (`migrate_journal.py:677`)
   and the `project_store_migration` engine (`MigrationPhase`,
   `project_store_migration.py:90-100`) — never a bespoke drain/copy (Decision 8,
   `research.md:87-97`). Source discovery is automatic via
   `discover_source_dbs` (`migrate_journal.py:144`); the migration identity is a
   **deterministic, root-derived `migration_id`** (not operator-supplied), so re-entry
   after a crash targets the *same* migration.

3. **Close the `CUTOVER_PENDING` drop window with crash-safe recovery (NFR-005, INV-3,
   INV-5).** A crash between `begin_cutover` (`layout_generation.py:339-362`) and
   `publish_project_only` (`layout_generation.py:364-390`) must leave a re-enterable
   state that the next run completes — never bricking a root. Live writes arriving while
   `mode == CUTOVER_PENDING` must not silently route to `LEGACY` and swallow.

The mission-critical property: **no state of the layout machine may return
capture-success while journaling zero events** (INV-1, `data-model.md:68-70`).

## Context

Read `plan.md` (IC-02, Engineering Alignment lines 96-133), `spec.md` (FR-002/FR-003,
US1, Edge Cases lines 135-146, NFR-002/NFR-005), `research.md` (Decisions 2, 8, 9, 10),
and `data-model.md` (state machine lines 46-65, INV-1..6, Cutover Transitions lines
86-97). Then internalize **the three hazards** — each is a concrete line in
`layout_generation.py` that will silently defeat the fix if handled naïvely:

### Hazard (a) — `_destination` returns LEGACY for CUTOVER_PENDING

`_destination` (`layout_generation.py:268-272`) maps `PROJECT_ONLY → PROJECT_STORE` and
**everything else → LEGACY**. So while a migration is in flight (`CUTOVER_PENDING`), the
issued write permit points at `LEGACY`; `journal.py:117-119`
(`_require_project_destination` → `ProjectLayoutRequiredError`) then refuses the live
write, the emitter swallows it, and the exact P0 is made **permanent** for the duration
of the window (Decision 9, `research.md:99-106`). The write routing for
`CUTOVER_PENDING` must change: block-and-retry within a bounded wait, and if the
migration cannot complete, route to the loud emitter surface — **never** silent LEGACY.

### Hazard (b) — the "never migrated" marker self-destructs

`_read_locked` (`layout_generation.py:176-188`) on a fresh root writes
`_initial_state()` = `LEGACY` (`layout_generation.py:129-136`) **and** the durable
`.initialized` marker (`_write_marker_locked`, path set at `layout_generation.py:407`)
on the first read. After that single read the greenfield signal is gone — the root looks
"initialized-as-LEGACY" indistinguishably from a real legacy root. Therefore the
no-legacy-data decision must run **before** that persist (Decision 10 / MAJOR-5,
`research.md:114-116`). Note `peek_state` (`layout_generation.py:256-266`) is the
existing **non-mutating** snapshot reader — the greenfield detection path must be
snapshot-shaped like it, not `_read_locked`-shaped.

### Hazard (c) — the real engine needs `migration_id` + source; derive them, define re-entry

`migrate_queues_to_journal` and `project_store_migration` were built for an
operator-driven `sync project-store-migrate` (explicit `--migration-id` / `--source`).
Auto-cutover has no operator, so:

- **`migration_id`** is derived deterministically from the root identity (e.g. the
  store's canonical `project_uuid` / runtime root), so a crash-and-retry re-enters the
  *same* migration. `begin_cutover` (`layout_generation.py:347-350`) already treats a
  re-entered `CUTOVER_PENDING` with a matching `migration_id` as idempotent and a
  mismatched one as "another migration owns cutover" — lean on that, do not fight it.
- **source** is discovered via `discover_source_dbs` (`migrate_journal.py:144`) — the
  **real reader**. Do **NOT** use the `queue.py` stub `detect_legacy_rows_for_scope`
  (`queue.py:204`): it `raise`s `LegacyQueueMigrationRequiredError` unconditionally, as
  does `default_queue_db_path` (`queue.py:195`). Detection and copy both go through the
  real `migrate_journal` surface.
- **re-entry contract**: a `CUTOVER_PENDING` record whose migration cannot yet publish
  re-enters on the next run and completes; a `FAILED` `MigrationPhase`
  (`project_store_migration.py:100`) manifest is cleared/retried under a documented rule.
  The invariant: a crash between `begin_cutover` and `publish_project_only` **always**
  converges on a later run and **never** bricks the root.

Legacy source rows are **read, never deleted** (INV-4, C-002; #2750 out of scope) — the
copy is non-destructive, so the mutation is inherently recoverable.

## Subtasks

Each subtask is red-first where marked: write the failing test in
`tests/sync/test_layout_cutover.py` **first**, watch it fail for the right reason, then
implement in `layout_generation.py`. All tests use isolated temp roots (see Test
Strategy) — **never** the live `~/.spec-kitty`.

### T011 — RED-FIRST: greenfield → PROJECT_ONLY, never persists LEGACY, captures

- **File**: `tests/sync/test_layout_cutover.py` (new), then `layout_generation.py`.
- **Red test**: build a `LayoutGenerationAuthority` (via
  `_new_layout_generation_authority`, `layout_generation.py:393-409` — the direct
  constructor at `layout_generation.py:103-108` raises by design) over a temp runtime
  root with **no** `.layout-generation.json` record, **no** `.initialized` marker, and
  **no** legacy queue DBs under the discovered `queues/` dir. Drive the first-write
  resolution path and assert:
  1. the published record `mode` is `PROJECT_ONLY` with `migration_id is None`;
  2. at **no point** was a record with `mode == LEGACY` written to `record_path`
     (`layout_generation.py:405`) — assert on the persisted JSON on disk, not merely on
     the returned `LayoutGenerationState`. A record that flickered LEGACY→PROJECT_ONLY
     between two writes still fails this assertion (spy on `_write_locked` or diff the
     file after each step);
  3. the issued permit's `destination` is `PROJECT_STORE` (`_destination`,
     `layout_generation.py:270-271`), so a subsequent live write is authorized by
     `_require_project_destination` (`journal.py:117-119`) and the journal count goes
     from 0 → 1 (SC-001, US1 acceptance scenario 1, `spec.md:50`).
- **Validation — why it is red today**: `_read_locked`
  (`layout_generation.py:181-184`) on a fresh root unconditionally writes
  `_initial_state()` = LEGACY (`layout_generation.py:129-136`) plus the marker, so
  assertion (2) fails immediately and (1)/(3) never reach PROJECT_ONLY (leaving LEGACY is
  manual-only). Watch it fail here before implementing.
- **Implement**: introduce a greenfield-resolution step that runs the real detector
  (T015) **before** the LEGACY persist and, on no-legacy-data, publishes `PROJECT_ONLY`
  directly (generation 1, `migration_id=None`). Keep the detection read snapshot-safe —
  shaped like `peek_state` (`layout_generation.py:256-266`), which reads without
  materializing the marker (`materialize_marker=False`, `layout_generation.py:265`) —
  so detection itself never trips Hazard (b).
- **Edge case**: a fresh root with **zero events emitted yet** must resolve
  `PROJECT_ONLY` as a no-op-safe default, not an error (`spec.md:145-146`). Assert that
  merely constructing the authority and reading state on a greenfield root does not error
  and does not persist LEGACY even before any write is attempted.
- **Regression guard**: assert an **already-migrated** (`PROJECT_ONLY`) root is untouched
  by the new path — read it, confirm the record bytes are unchanged and generation does
  not advance (NFR-003: zero behavior change for migrated roots).

### T012 — RED-FIRST: idempotence under interruption (crash between begin/publish)

- **File**: test first, then `layout_generation.py`.
- **Red test**: seed a temp root with real legacy data. Begin cutover (deterministic
  `migration_id` from T016), then simulate a crash **after** `begin_cutover`
  (`layout_generation.py:339-362`) advanced the record to `CUTOVER_PENDING` but
  **before** `publish_project_only` (`layout_generation.py:364-390`) ran. Re-enter the
  resolution path and assert: the same `migration_id` is reused (no "another migration
  owns cutover" from `layout_generation.py:350`), the migration converges to
  `PROJECT_ONLY`, the journal holds each pre-existing legacy event **exactly once** (0
  loss, 0 dup — INV-2/NFR-002/SC-004/SC-005), and **no additional writes** beyond
  convergence occur.
- **Validation**: assert an event-count **and** identity diff of the journal
  before/after re-entry equals the pre-crash snapshot — a pure count check would miss a
  drop masked by an equal-count duplicate. Prove convergence is a **no-op** when already
  `PROJECT_ONLY` (re-running a completed cutover writes nothing new — spy on
  `_write_locked` and assert zero calls on the second pass). Assert the re-entry does
  **not** raise `LayoutAuthorityError("another migration owns cutover")`
  (`layout_generation.py:350`), which would prove the `migration_id` was
  non-deterministic — the classic bricking bug (see Risks).
- **Implement**: the deterministic `migration_id` (T016) plus the re-entry rule (T016).
  `begin_cutover` already short-circuits a re-entered `CUTOVER_PENDING` whose
  `migration_id` matches (`layout_generation.py:347-349`, returns `current`
  unchanged) — the implementation must feed it the *same* id after a crash so this branch
  is taken, then resume the copy + `publish_project_only`.
- **Edge case**: root with both legacy data **and** partial project-store state must
  reconcile, not double-count (`spec.md:139-140`). The engine's
  `(event_id, source_digest)` provenance primary key (`migrate_journal.py:175`,
  `INSERT OR IGNORE`, `migrate_journal.py:243`) guarantees idempotent copy; the test
  seeds one already-copied event, re-runs, and asserts it is not re-copied (dedup, not
  duplicate).
- **Edge case**: a `MigrationPhase.FAILED` (`project_store_migration.py:100`) manifest
  from a prior failed attempt must be cleared and retried under the deterministic id, not
  left wedging the root — assert a FAILED-then-retry path converges to `PROJECT_ONLY`.

### T013 — RED-FIRST: emit during CUTOVER_PENDING → zero loss

- **File**: test first, then `layout_generation.py`.
- **Red test**: drive the machine to `CUTOVER_PENDING` and hold it there (a migration
  that has not yet published). Issue a **live write** while in that state. Assert the
  write is **not** silently routed to LEGACY-and-swallowed (INV-5,
  `data-model.md:79-81`): it blocks-and-retries within a bounded wait and, once cutover
  publishes, lands in the project store; if cutover cannot complete inside the bound, the
  write surfaces **loudly** (routed to the loud emitter surface, WP owned by IC-05), not
  silent. Zero events lost across the window.
- **Validation — why it is red today**: `_destination`
  (`layout_generation.py:268-272`) returns `LEGACY` for any non-`PROJECT_ONLY` mode, so
  `issue_write_permit` (`layout_generation.py:274-281`) hands out a LEGACY-destination
  permit while `CUTOVER_PENDING`; `execute_write` (`layout_generation.py:299-337`) then
  invokes the writer against LEGACY, `_require_project_destination`
  (`journal.py:117-119`) raises `ProjectLayoutRequiredError`, and the emitter swallows it.
  The test must fail on exactly that swallow first, asserting the dropped event is
  observable nowhere.
- **Implement**: T017 (CUTOVER_PENDING write routing: block-and-retry, else loud). The
  bounded wait must be deterministic in tests — inject the bound and use a synchronization
  hook shaped like `LayoutTestHooks.before_revalidate` (`layout_generation.py:75-79`,
  wired through `execute_write`'s `test_hooks` param at `layout_generation.py:304`), never
  wall-clock-flaky.
- **Edge case**: if the migration publishes `PROJECT_ONLY` *during* the retry window, the
  write must proceed to the project store on the next revalidation — assert the event
  lands exactly once (not dropped, not double-written) when publish races the retry.
- **Edge case**: if the bounded wait elapses with the migration still pending, the write
  routes to the loud emitter surface (IC-05, owned by another WP) — assert the WP03 code
  raises/signals a distinguishable "cutover-not-yet-complete" condition rather than
  returning success, so the loud surface has something to report.

### T014 — RED-FIRST: SPEC_KITTY_NO_AUTO_CUTOVER → loud actionable refusal, no mutation

- **File**: test first, then `layout_generation.py`.
- **Red test**: seed a legacy-with-data root, set `SPEC_KITTY_NO_AUTO_CUTOVER` in the
  environment, and drive first-write resolution. Assert: (1) the layout is **not**
  mutated — the record stays `LEGACY`, no `begin_cutover` occurs, no `migration_id`
  written; (2) a **loud, actionable** refusal is surfaced pointing at
  `sync project-store-migrate` (Cutover Transition 5, `data-model.md:96-97`); (3) the
  refusal is **never** a silent LEGACY swallow.
- **Validation**: assert `record_path` (`layout_generation.py:405`) is byte-identical
  before/after (no mutation — no `begin_cutover` generation bump), and that the refusal
  message names the manual `sync project-store-migrate` command so an operator can act on
  it. The refusal is loud (raised/routed), never a silent LEGACY swallow.
- **Implement**: read the escape hatch from the environment (T017) and gate the
  auto-cutover branch; when set on a legacy-with-data root, skip the mutation entirely and
  raise/route the actionable refusal. The check must read the env at resolution time (not
  import time) so tests can toggle it per-case.
- **Edge case**: the escape hatch must still allow a **greenfield** (no legacy data) root
  to resolve `PROJECT_ONLY` — the hatch suppresses *auto-cutover of legacy data*, not
  greenfield journaling. Add an assertion covering that split: hatch set + no legacy data
  ⇒ `PROJECT_ONLY` and a captured event; hatch set + legacy data ⇒ loud refusal, no
  capture, no mutation.
- **Edge case**: a root already in `CUTOVER_PENDING` (crash mid-migration) with the hatch
  set — decide and document: recovery of an in-flight migration should still complete
  (the migration was already authorized), i.e. the hatch gates *initiating* auto-cutover,
  not *finishing* one that was already begun. Assert the in-flight case converges rather
  than wedging.

### T015 — Detection-before-persist + real detector via discover_source_dbs

- **File**: `layout_generation.py` (+ test coverage folded into T011/T012).
- **Implement**: a detection helper that answers "does this root hold legacy data?" using
  the **real reader** `discover_source_dbs` (`migrate_journal.py:144`) plus queued-row
  counts — **not** the stub `detect_legacy_rows_for_scope` (`queue.py:204`, raises). The
  helper runs **before** any LEGACY persist in the resolution path (Hazard (b)), so a
  no-legacy-data root never writes LEGACY.
- **Validation**: unit-test the helper directly on (a) an empty/absent `queues/` dir → no
  legacy data → greenfield; (b) a dir with a real scoped `queue-<digest>.db`; (c) the
  legacy `queue.db`; (d) both. `discover_source_dbs` returns `[]` for an absent/empty
  queue dir with no error (`migrate_journal.py:150-151`), so greenfield detection is
  clean and never raises. The legacy `queue.db` is included only when it is an actual
  file (`migrate_journal.py:160-162`).
- **Row-count nuance**: a *present but empty* source DB (file exists, zero queued rows)
  is **not** legacy data awaiting migration — the detector must consult queued-row counts
  through the real `migrate_journal` read surface, not merely the existence of a `.db`
  file, or a stale empty queue would trigger a pointless cutover. Test the empty-DB case
  explicitly resolves greenfield.
- **Edge case**: a malformed queue filename (does not match the hex-digest shape) is
  skipped by `discover_source_dbs` (`migrate_journal.py:156-158`, `_parse_digest` →
  `None` → `continue`), so it must not be misread as legacy data. Seed a
  `queue-notahex.db` and assert greenfield.
- **Boundary discipline**: the helper must **not** import or call the `queue.py` stubs
  `detect_legacy_rows_for_scope` (`queue.py:204`) or `default_queue_db_path`
  (`queue.py:195`) — both raise `LegacyQueueMigrationRequiredError` unconditionally
  (`queue.py:196`, `queue.py:206`) and exist only as retired shims. A grep of the diff
  for those symbols must come back empty.

### T016 — Lazy auto-cutover invoking canonical engines + deterministic id + recovery

- **File**: `layout_generation.py`.
- **Implement**: on first live write to a legacy-with-data root (escape hatch unset),
  derive a **deterministic root-derived `migration_id`** (stable across process
  restarts — from the store's canonical `project_uuid` / runtime root, **not** `uuid4`),
  call `begin_cutover(migration_id)` (`layout_generation.py:339-362`), run the copy via
  `migrate_queues_to_journal` (`migrate_journal.py:677`) with auto-discovered source and
  `project_store_migration` attribution, then `publish_project_only(migration_id, verify_exact=...)`
  (`layout_generation.py:364-390`). The `verify_exact` callback is the engine's
  copy-verify (conservation), so publication only happens after the copy is proven exact.
- **Recovery rule (document inline)**: a re-entered `CUTOVER_PENDING` with the matching
  `migration_id` resumes and completes (idempotent — `layout_generation.py:347-349`); a
  `MigrationPhase.FAILED` (`project_store_migration.py:100`) manifest is cleared and
  retried against the same deterministic `migration_id`. A crash between begin and
  publish **always** converges on a later run; the root is **never** bricked.
- **Validation**: covered by T012 (crash/idempotence) + a focused unit test asserting the
  derived `migration_id` is identical across two constructions of the authority over the
  same root (determinism), and distinct across two different roots.
- **Canonical-source discipline**: do **not** reimplement dedup, provenance, quarantine,
  or attribution — those live in the engines (`migrate_journal.py:175` provenance PK,
  `project_store_migration.py` `project_uuid` attribution). Reuse only. The copy call is
  `migrate_queues_to_journal(spec_kitty_dir, journal=..., audit=..., resolved_target=...)`
  (`migrate_journal.py:677-683`); its `MigrationResult.exit_code`/`blocked`
  (`migrate_journal.py:693-694`) stay non-zero/True while any conflict is unresolved —
  the cutover drive must treat a blocked result as "do not publish", surfacing it loudly
  (IC-04) rather than publishing over an unresolved conflict.
- **verify_exact wiring**: `publish_project_only`'s `verify_exact` callback
  (`layout_generation.py:368,379-380`) must return `True` only when the engine has proven
  the copy exact (every discovered source event present in the journal exactly once).
  A `False`/non-`True` return raises `LayoutVerificationError`
  (`layout_generation.py:380`) and correctly refuses to publish — assert that a
  deliberately-incomplete copy does **not** publish `PROJECT_ONLY`.

### T017 — CUTOVER_PENDING write routing + escape-hatch implementation

- **File**: `layout_generation.py`.
- **Implement (write routing)**: change how a live write behaves when the current state is
  `CUTOVER_PENDING`. Instead of `_destination` silently yielding `LEGACY`
  (`layout_generation.py:272`) and `execute_write` (`layout_generation.py:299-337`)
  handing the writer a LEGACY permit, the `CUTOVER_PENDING` path blocks-and-retries within
  a bounded, injectable wait for the migration to publish `PROJECT_ONLY`; on success it
  proceeds to the project store; on timeout it routes to the loud emitter surface (IC-05)
  — **never** a silent LEGACY write. Preserve `execute_write`'s existing under-lock
  revalidation and single-redirect semantics (`layout_generation.py:317-337`); the new
  behavior is a `CUTOVER_PENDING`-specific branch, not a rewrite of the permit machinery.
- **Implement (escape hatch)**: `SPEC_KITTY_NO_AUTO_CUTOVER` gates the auto-cutover branch
  in T016; when set on a legacy-with-data root, no mutation, loud actionable refusal
  (T014).
- **Validation**: T013 (zero loss under CUTOVER_PENDING) + T014 (escape hatch). Assert the
  bounded wait is deterministic via an injected hook, not wall-clock.
- **Edge case**: concurrent writers during cutover — the "project sync store is locked"
  contention observed live during `mission create` (`spec.md:141-142`) must not corrupt or
  drop; the block-and-retry runs under the existing `FileLock` (`layout_generation.py:319`)
  discipline.

## Branch Strategy

- **Base branch**: `fix/legacy-journal-capture-cutover`.
- **Merge target**: `fix/legacy-journal-capture-cutover` (lane strategy — this WP lands
  back onto the mission branch, not `main`).
- **Worktree**: per-lane, allocated from `lanes.json`. Do **not** hand-construct the
  worktree path — let the resolver create it.
- **Command** (only supported way to prepare the workspace):

  ```
  spec-kitty agent action implement WP03 --agent <name>
  ```

- **Dependency gate**: WP01 and WP02 must be `approved` or `done` before WP03 can be
  claimed (`dependencies: ["WP01","WP02"]`). WP01 supplies the restored credential
  auth-signal / detection groundwork and WP02 the identity/attribution foundation this
  cutover copy depends on (IC-00 precedes IC-02, `plan.md:139-161`). Do not attempt to
  claim WP03 until both are green — the dependency-readiness gate will refuse it.

## Test Strategy

- **Red-first (C-011).** For T011–T014, the failing test lands and is observed failing for
  the correct reason **before** any implementation. Do not write the fix first and
  back-fill a test.
- **⚠️ Isolation is mandatory — non-negotiable.** **ALL** tests use isolated temp roots
  via `SPEC_KITTY_HOME` / `HOME` fixtures. **NEVER** run cutover against the live
  machine-global `~/.spec-kitty`. This dev box is **itself a live legacy root** — running
  cutover against it would migrate the whole machine's real queue data (risk MINOR-8,
  `plan.md:131-133`, `research.md:120-121`). Every test constructs its own temp runtime
  root, points the authority's `record_path` / `marker_path` /
  `queues/` dir inside it, and asserts nothing touches the real home.
- **Determinism.** No wall-clock sleeps in the block-and-retry tests — inject the bound and
  use a synchronization hook shaped like `LayoutTestHooks`
  (`layout_generation.py:75-79`, `before_revalidate`). Race behavior must be reproducible.
- **Conservation assertions.** T012 asserts a before/after event-count **and** identity
  diff (not just a count), so a drop that is masked by an equal-count duplicate is caught.
- **Real engines, not stubs.** Detection and copy go through `discover_source_dbs` /
  `migrate_queues_to_journal`; a test that reaches `detect_legacy_rows_for_scope`
  (`queue.py:204`) or `default_queue_db_path` (`queue.py:195`) is wired wrong — both
  raise unconditionally.
- **Run**:

  ```
  PWHEADLESS=1 .venv/bin/python -m pytest tests/sync/test_layout_cutover.py -q
  ```

  (Use the hand-built `.venv`; a bare `uv run` re-syncs and can destroy it.)

## Definition of Done

- All four red-first tests (T011, T012, T013, T014) are green, each having first failed
  for the documented reason.
- **No silent-capture window remains in any layout state** — including `CUTOVER_PENDING`.
  INV-1 (no silent success) and INV-5 (no mid-cutover drop) hold under test.
- Greenfield roots resolve `PROJECT_ONLY` **before** any LEGACY persist; a fresh root's
  first event lands in the journal (SC-001).
- Crash-recovery is proven: an interrupted cutover (crash between `begin_cutover` and
  `publish_project_only`) re-enters the same deterministic `migration_id` and converges,
  with zero additional/divergent writes (INV-3/NFR-005/SC-005), never bricking the root.
- Auto-cutover copy is performed **only** by the canonical engines
  (`migrate_queues_to_journal` + `project_store_migration`) — no bespoke drain, no
  re-derived dedup/provenance/quarantine (Decision 8).
- `SPEC_KITTY_NO_AUTO_CUTOVER` yields a loud, actionable, non-mutating refusal (T014).
- `ruff check .` and `mypy` are clean on the touched files with zero new issues and zero
  new suppressions. Any function touched stays at complexity ≤ 15 — extract helpers for
  the detection / cutover-drive / write-routing phases rather than growing one method.
- No files outside `owned_files` are modified in this WP.

## Risks & Reviewer Guidance

- **Bricking (highest risk).** The failure mode to hunt: a crash mid-cutover that leaves a
  `CUTOVER_PENDING` record no later run can complete (e.g. a non-deterministic
  `migration_id`, so re-entry hits "another migration owns cutover",
  `layout_generation.py:350`). Reviewer: verify the `migration_id` is derived
  deterministically from stable root identity and that T012 genuinely simulates the
  crash *between* `begin_cutover` and `publish_project_only`, not around the whole flow.
- **Concurrency at the first-write trigger.** Two writers racing to trigger auto-cutover
  on the same root must not double-begin or corrupt. The block-and-retry and cutover drive
  run under the existing `FileLock` (`layout_generation.py:319`); reviewer confirms no new
  unlocked read-decide-write gap was introduced ahead of the LEGACY-persist decision.
- **The LEGACY default is heavily test-pinned.** Roughly ~80 files across `tests/sync` and
  `tests/event_journal` assert the current LEGACY-default behavior. **Do not fight those
  pins in this WP** — WP06 (IC-06) owns reconciling the external pins. If a pre-existing
  test outside `owned_files` goes red purely because the greenfield default flipped, that
  is expected and is WP06's remit; note it, do not edit it here.
- **No silent LEGACY-swallow window may survive.** The reviewer's primary acceptance
  check: walk every layout state (`LEGACY`, `CUTOVER_PENDING`, `PROJECT_ONLY`) and confirm
  none returns write-success while the event is journaled to nowhere. `CUTOVER_PENDING` is
  the trap — confirm it block-and-retries then goes loud, and never silently issues a
  LEGACY permit via `_destination` (`layout_generation.py:268-272`).
- **Canonical-source discipline.** Reviewer confirms the copy is the engine's, not a
  hand-rolled loop — grep the diff for any re-implementation of `(event_id, source_digest)`
  dedup or `project_uuid` attribution; there must be none.
- **Scope discipline.** Only `layout_generation.py` and the new
  `tests/sync/test_layout_cutover.py` change here. The emitter observability surface
  (IC-05), the credential auth-signal (IC-01/WP01), and the regression-test rewrite
  (IC-06/WP06) are **other** WPs — do not reach into them.

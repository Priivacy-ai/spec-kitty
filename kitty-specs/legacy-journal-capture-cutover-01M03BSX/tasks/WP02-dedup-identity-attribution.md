---
work_package_id: WP02
title: Dedup identity + ownerless-row attribution foundation
dependencies: []
requirement_refs:
- FR-005
planning_base_branch: fix/legacy-journal-capture-cutover
merge_target_branch: fix/legacy-journal-capture-cutover
branch_strategy: Planning artifacts for this mission were generated on fix/legacy-journal-capture-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/legacy-journal-capture-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
history:
- at: '2026-08-15T00:00:00Z'
  actor: claude
  note: WP authored by tasks phase
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/sync/test_cutover_conservation.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/migrate_journal.py
- src/specify_cli/sync/project_store_migration.py
- src/specify_cli/event_journal/journal.py
- tests/sync/test_cutover_conservation.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before doing anything else, load your governance profile:

```
/ad-hoc-profile-load implementer-ivan
```

This binds your identity, boundaries, and the doctrine context (red-first / ATDD,
canonical-sources, ownership boundaries) that governs every step below. Do not begin
reading or editing until the profile is loaded.

## Objective

Pin the **copy identity** so the legacy→journal cutover can never duplicate or drop an
event — **including ownerless legacy rows that predate per-project ownership**. This work
package is the FOUNDATION (Implementation Concern **IC-00** in
[`plan.md`](../plan.md)) that WP03's cutover copy consumes: WP03 invokes the copy engine,
but only *after* this WP has guaranteed that (a) dedup keys deterministically on
`(event_id, source_digest)` provenance, (b) ownerless rows carry a `project_uuid` before
they hit any owner check, and (c) genuine divergent-payload collisions **quarantine**
rather than last-write-win (#2846).

**REUSE the canonical engines — do not reinvent dedup, provenance, or attribution.** The
copy semantics already live in `migrate_journal.py` (provenance + quarantine) and
`project_store_migration.py` (`project_uuid` attribution). Your job is to *confirm, wire,
and harden* those entry points and lock the conservation invariant (INV-2 in
[`data-model.md`](../data-model.md)) behind red-first tests — not to author a new drain or
copy path. Any bespoke copy loop is a charter "canonical sources" violation and an
automatic reviewer rejection.

Satisfies **FR-005** (single authoritative record, dedup by stable identity incl.
ownerless legacy rows) and underwrites **NFR-002** (zero loss / zero dup on cutover).

## Context

- **Ownerless legacy rows are the trap.** Rows written before per-project ownership have
  no `project_uuid` that matches the destination store. A naïve copy therefore trips the
  owner guard: `queue.py:346-348` computes `owner = _owner_from_event(event)` and raises
  `ValueError("event project UUID does not match store owner")` when `owner !=
  self.project_uuid`. The journal side has the twin guard at
  `journal.py:170-171` (`event.project_uuid != self.project_uuid` →
  `ValueError("event-declared project UUID does not match store owner")`). Attribution
  (assigning the canonical `project_uuid` to an ownerless row) MUST run **before** either
  check — this is the whole reason IC-00 precedes the IC-02 copy.
- **Dedup keys on `(event_id, source_digest)`.** The provenance ledger in
  `migrate_journal.py` is keyed exactly this way — see the `migration_provenance` table
  (`PRIMARY KEY (event_id, source_digest)`, migrate_journal.py:175) and
  `MigrationAudit.record_provenance` (migrate_journal.py:240-244), which does an
  `INSERT OR IGNORE` so re-runs never double-count. `event_id` is carried through
  verbatim, never rewritten (module docstring, migrate_journal.py:27).
- **Divergent payloads QUARANTINE, not last-write-win (#2846).** A same-`event_id`
  collision whose canonical payload *differs* is parked for an operator via
  `MigrationAudit.quarantine_conflict` (migrate_journal.py:317-335, idempotent on
  `(event_id, source_digest)`). Silently keeping the last write is the #2846 bug this WP
  must prevent regressing.
- **Idempotence backstop.** `EventJournal.append` short-circuits on a prior assignment for
  the same `event_id` (`existing = self._existing_assignment(event.event_id)` /
  `if existing is not None: return existing`, journal.py:172-173) — the last line of
  defense so a replayed copy is a no-op, not a duplicate.

## Subtasks

### T006 — Red-first conservation test (0 loss / 0 dup, incl. ownerless rows)

- **File**: create `tests/sync/test_cutover_conservation.py` (declared in
  `create_intent`).
- **Write RED first.** Seed a temp `spec_kitty_dir` (via `tmp_path` /
  `SPEC_KITTY_HOME` — see Test Strategy) with a legacy `queue.db` plus at least one scoped
  `queue-<digest>.db`, holding a known set of events where **some rows are ownerless**
  (no `project_uuid`, or a `None`/empty one). Snapshot the pre-cutover event-id multiset so
  the assertion is a before/after diff, not a fixed literal.
- **Drive the real engine.** Build the destination `EventJournal` against the temp root and
  call `migrate_journal.migrate_queues_to_journal(spec_kitty_dir, journal=<journal>)`
  (migrate_journal.py:677). Enumerate sources with `discover_source_dbs`
  (migrate_journal.py:144) so the fixture matches exactly what the engine walks — do not
  hand-list paths the engine would not discover.
- **Assert conservation (INV-2)**: every pre-existing `event_id` appears in the destination
  **exactly once** — assert BOTH count equality (destination event count ==
  distinct-source event count) AND identity-set equality (the set of destination
  `event_id`s == the set of source `event_id`s). Ownerless rows are included in both sides.
- **Validation**: run only this file; confirm it is RED against `main`'s behavior for the
  ownerless leg (the owner guard rejects the un-attributed row today), then GREEN after
  T008/T009 wiring. The count-and-identity assertion is what pins NFR-002.
- **Edge cases**:
  - Empty legacy store → no-op, no error, destination stays empty.
  - Identical duplicate rows spanning two source digests collapse to ONE destination
    record while accumulating BOTH provenance rows (assert via `provenance_for`,
    migrate_journal.py:267).
  - A scoped `queue-<digest>.db` with zero queued rows is skipped, not errored.
  - Re-running the copy a second time adds no rows (idempotent) — assert the destination
    multiset is unchanged after a second `migrate_queues_to_journal`.

### T007 — Red-first divergent-payload quarantine test

- **File**: same `tests/sync/test_cutover_conservation.py` (new test function).
- **Write RED first.** Seed two source DBs that carry the **same `event_id`** but
  **divergent canonical payloads** (different `payload_sha`). This is the #2846 shape: the
  legacy and journal stores disagree on the body for one identity.
- **Assert the copy does NOT last-write-win.** Exactly one authoritative record lands for
  the shared `event_id`, and the divergence is parked as a quarantined conflict:
  - Assert a conflict row exists for that `(event_id, source_digest)` via the
    `MigrationAudit` conflict surface — `quarantine_conflict` (migrate_journal.py:317) and
    the conflict iterator (`iter_conflicts`, migrate_journal.py:299-306).
  - Assert `MigrationResult.blocked` is truthy / `exit_code` is non-zero while the conflict
    is unresolved (cleanup is blocked — see the `migrate_queues_to_journal` docstring,
    migrate_journal.py:684-695).
- **Validation**: RED before T008 confirms the quarantine path is genuinely exercised (not
  bypassed by a silent overwrite); GREEN after. This test is the standing #2846 regression
  guard — without it, a future "simplification" back to last-write-win passes CI.
- **Edge cases**:
  - Identical payloads under the same `event_id` are DEDUP (one record, both provenance
    rows), NOT quarantine — assert the conflict table is empty in that case.
  - Quarantine is idempotent — a second `migrate_queues_to_journal` does not add a second
    conflict row for the same `(event_id, source_digest)` (`INSERT OR IGNORE`,
    migrate_journal.py:333-334).
  - The authoritative destination record is deterministic (stable choice), not
    run-order-dependent — assert it does not flip between the two payloads across re-runs.

### T008 — Wire `(event_id, source_digest)` provenance dedup via `migrate_journal`

- **File**: `src/specify_cli/sync/migrate_journal.py`.
- **Confirm and, only where missing, wire** that the copy path routes every source event
  through `MigrationAudit.record_provenance` (migrate_journal.py:240-244) keyed on
  `(event_id, source_digest)`, and that a same-`event_id` divergent payload is sent to
  `quarantine_conflict` (migrate_journal.py:317-335) rather than overwriting. Do NOT add a
  parallel dedup mechanism — thread the existing audit ledger. If the plumbing is already
  correct, the deliverable is the T006/T007 tests that pin it plus any narrowly-scoped
  hardening the tests expose.
- **Validation**: T006 and T007 both GREEN; `provenance_for(event_id)`
  (migrate_journal.py:267-273) returns every contributing `source_digest` for a
  multi-source event (provenance accumulates, dedup does not lose sources). Confirm the
  `migration_provenance` PRIMARY KEY `(event_id, source_digest)` (migrate_journal.py:175)
  is what enforces the once-per-source ledger — do not add a second keying scheme.
- **Edge cases**:
  - A locked/corrupt source DB isolates to a per-source failure and does not abort the
    whole run (module docstring guarantee, migrate_journal.py:25-26).
  - `event_id` is carried through verbatim, never rewritten (migrate_journal.py:27) — assert
    a copied event keeps its exact source `event_id`.
  - `record_provenance` is `INSERT OR IGNORE` (migrate_journal.py:243) so a replayed source
    row does not create a second provenance entry.

### T009 — Ownerless-row `project_uuid` attribution via `project_store_migration`

- **File**: `src/specify_cli/sync/project_store_migration.py` (+ the call seam in
  `migrate_journal.py` if the attribution is invoked from there).
- **Ensure ownerless rows acquire a canonical `project_uuid` before the owner check.** Do
  NOT invent a new attribution routine — reuse the existing canonicalization surface:
  - `_canonical_project` (project_store_migration.py:406) normalizes a raw uuid to
    `(canonical, reason)`.
  - The extraction helpers `_project_uuid_value` (project_store_migration.py:375) and
    `_payload_project_uuid` (project_store_migration.py:392) read the uuid from the row and
    from the payload respectively.
  - Attribution is driven through the `MigrationPhase` state machine
    (project_store_migration.py:90) via `LegacyProjectStoreMigration.migrate`
    (project_store_migration.py:1236), whose durable monotonic phases keep the operation
    idempotent and crash-recoverable.
- **Attribution must resolve to the destination store's owner** so the row then passes the
  owner guards at `journal.py:170-171` and `queue.py:346-348` on copy. This ordering — attribute
  first, THEN copy — is the entire reason IC-00 precedes the IC-02 copy: an un-attributed
  ownerless row raises the "project UUID does not match store owner" `ValueError`.
- **Validation**: the ownerless-row leg of T006 goes GREEN. Add a focused unit assertion
  that a row with a `None`/missing `project_uuid` is attributed to the canonical owner (not
  dropped, not quarantined) and afterward satisfies the owner check.
- **Edge cases**:
  - A row whose payload `project_uuid` **conflicts** with the store owner is a genuine
    conflict, NOT free attribution — it maps to `CONFLICTING_PROJECT_UUID`
    (project_store_migration.py:121).
  - Preserve the three distinct reasons: `MISSING_PROJECT_UUID`
    (project_store_migration.py:118), `NIL_PROJECT_UUID` (project_store_migration.py:120),
    and `CONFLICTING_PROJECT_UUID` (project_store_migration.py:121). Collapsing them into one
    is a regression — `MISSING`/`NIL` are attributable, `CONFLICTING` is not.

### T010 — Confirm / harden `journal.append` `event_id` idempotence

- **File**: `src/specify_cli/event_journal/journal.py`.
- **Confirm the idempotence backstop holds and is covered.** `append`
  (journal.py:163) must return the existing assignment for a replayed `event_id` without a
  second write — the `existing = self._existing_assignment(event.event_id)` /
  `if existing is not None: return existing` guard (journal.py:172-173), backed by
  `_existing_assignment` (journal.py:148). Do NOT weaken the owner guard at
  journal.py:170-171 — attribution (T009) runs upstream; the guard stays.
- **Validation**: a test appends the same `Event` twice and asserts one row / identical
  receipt (no duplicate `capture_sequence`). Fold this assertion into
  `tests/sync/test_cutover_conservation.py` so the conservation file owns the end-to-end
  idempotence pin — the replayed-copy no-op is what makes a re-run of
  `migrate_queues_to_journal` safe (T006's second-run assertion leans on this backstop).
- **Do not weaken the owner guard.** `journal.py:170-171` (`event.project_uuid !=
  self.project_uuid → ValueError`) stays exactly as-is. Attribution (T009) is the upstream
  fix; the guard is the invariant that keeps a mis-attributed event out of the wrong store.
  Any change that relaxes this guard to "fix" ownerless rows is the wrong layer and a
  reviewer rejection.
- **Edge cases**:
  - A suppressing coalesce strategy still returns a stable receipt for the collapsed event
    (journal.py:176-185) — do not regress that contract.
  - `_existing_assignment` (journal.py:148) is the single lookup; the replay no-op must go
    through it, not a new parallel dedup check.
  - Only harden the `event_id`-replay no-op if the tests expose a genuine gap; if the
    backstop already holds, the deliverable is the covering test, not a code change.

## Branch Strategy

- **Base branch**: `fix/legacy-journal-capture-cutover`.
- **Merge target**: `fix/legacy-journal-capture-cutover` (mission integration branch; this
  is NOT `main`).
- **Lane worktree**: per-lane worktree materialized from `lanes.json` — do not hand-build
  or reconstruct the path.
- **Prepare the workspace only via the resolver**:

  ```
  spec-kitty agent action implement WP02 --agent <name>
  ```

  Consume the resolved workspace path; never `cd` into a reconstructed
  `.worktrees/...` directory.

## Test Strategy

- **Red-first (C-011).** Every subtask that adds behavior lands its failing test first
  (T006, T007 especially), then the wiring that turns it green.
- **Temp roots ONLY — never the real `~/.spec-kitty`.** This dev box is itself a live
  machine-global legacy root; a cutover test run against it would mutate real data. Every
  test MUST resolve its `spec_kitty_dir` from an isolated temp root — `tmp_path` plus the
  `SPEC_KITTY_HOME` / `HOME` fixtures — so `discover_source_dbs`
  (migrate_journal.py:144) sees only the seeded fixtures. No test or manual step may point
  the engine at the real store (plan Risk MINOR-8 / research Decision 10).
- **Run targeted, not the full suite** (the full suite hangs the session):

  ```
  PWHEADLESS=1 pytest tests/sync/test_cutover_conservation.py -q
  ```

## Definition of Done

- `tests/sync/test_cutover_conservation.py` exists and is GREEN: conservation
  (0 loss / 0 dup incl. ownerless rows) AND divergent-payload quarantine (#2846) both
  pinned red-first then green.
- Ownerless legacy rows are attributed a canonical `project_uuid` before any owner check;
  divergent-uuid rows quarantine under the correct distinct reason.
- `event_id` idempotence backstop in `journal.append` is confirmed and test-covered.
- **Canonical engines REUSED — cite the entry points in the PR**: dedup/provenance/
  quarantine via `migrate_journal.migrate_queues_to_journal` (migrate_journal.py:677) +
  `MigrationAudit` (migrate_journal.py:214, `record_provenance` :240,
  `quarantine_conflict` :317); attribution via `project_store_migration` (`MigrationPhase`
  :90, `_canonical_project` :406, `LegacyProjectStoreMigration.migrate` :1236). **No
  bespoke drain/copy loop.**
- `ruff check .` and `mypy` clean on the touched files — zero new issues, zero
  suppressions.
- No file outside `owned_files` is modified.

## Risks & Reviewer Guidance

- **Reviewer: confirm there is NO bespoke drain/copy.** The single most likely failure
  mode is an agent re-implementing dedup or attribution inline instead of threading the
  canonical `migrate_journal` / `project_store_migration` entry points. Reject any parallel
  copy loop; require the cited entry points.
- **Attribution must run BEFORE the owner check.** Verify ordering: an ownerless row is
  assigned its canonical `project_uuid` upstream of `queue.py:346-348` and
  `journal.py:170-171`. If the "project UUID does not match store owner" `ValueError` can
  still fire for a legitimately-attributable legacy row, the ordering is wrong.
- **Quarantine, not last-write-win.** Confirm T007 actually exercises the
  `quarantine_conflict` path (a real conflict row lands, `MigrationResult.blocked` is set)
  and that identical payloads dedup rather than quarantine — the two must not be conflated.
- **Distinct quarantine reasons preserved.** `MISSING_` / `NIL_` / `CONFLICTING_PROJECT_UUID`
  (project_store_migration.py:118-121) are semantically different; a fix that maps all
  three to one reason is a regression.
- **Isolation.** Confirm no test touches the real `~/.spec-kitty`; a fixture that leaks the
  real `HOME`/`SPEC_KITTY_HOME` is a data-safety defect on this box.
- **Foundation contract for WP03.** WP03 depends on the guarantees pinned here; a weak or
  skipped conservation/quarantine test silently degrades WP03's cutover safety.

# WP02 Review Cycle 1 — Changes Requested

## 1. The unit-of-work port leaks transaction ownership

`ProjectUnitOfWork.execute()` and `executemany()` return the raw
`sqlite3.Cursor`, whose public `.connection` can commit, roll back, or close the
outer connection. The same public `execute()` method accepts transaction-control
SQL. Both bypasses were reproduced at final HEAD:

- `unit.execute("SELECT 1").connection.commit()` persisted a prior mutation
  after a later business exception;
- `unit.execute("COMMIT")` likewise persisted a mutation after a later business
  exception.

This contradicts FR-026, SC-011, the store-layout contract rule 7, and
`project_store.py:87-103`'s claim that components cannot own connection or
transaction lifecycle. Return an opaque result/cursor facade that does not expose
the connection, reject transaction-control statements through repository SQL
ports, and add negative tests proving neither path can make a partial commit.
Extend the fault bundle through `delivery_results`, and prove rollback of a
failing explicit savepoint without ending the outer transaction.

## 2. Context and capabilities are caller-minted rather than store-derived

`ProjectSyncStore.create_context()` accepts caller-supplied consent, epoch,
admission, binding, kill-switch, and lease values. A review probe created an
`egress_eligible=True` context while the verified store contained zero consent,
epoch, and target/admission rows. The public `VerifiedProjectStoreIdentity`,
`ProjectCaptureCapability`, and `ProjectStoreMaintenanceCapability` dataclasses
also accepted a capability whose top-level UUID was A while its store identity
was B at an arbitrary path.

That violates FR-010/T009 and Decision 9: a verified UUID/path plus coherent
authority must be store-derived, and cross-pairing must be impossible or rejected.
At this WP stage, expose only absent/denied authority unless it is read from the
verified unit of work; do not permit callers to mint eligible authority. Make
store identity and derived capability construction factory-controlled (or enforce
all UUID/path/version invariants in their constructors), and add negative tests
for forged store identity, A/B capability pairs, nonexistent epochs, and
caller-supplied grants/admissions.

## 3. Layout authority can fork and can fail open after cutover

`LayoutGenerationAuthority` is public and directly accepts a caller-selected
`runtime_root`, so a component can create a private `.layout-generation.json`
instead of going through `ProjectSyncStore`. More seriously, `_read_locked()`
treats any missing record as a fresh legacy installation. After publishing
`project_only`, deleting the authority record caused the next permit to become
`legacy`, generation 1. Loss of the sole cutover record therefore silently
reopens the retired destination.

This contradicts FR-029, T008, Decision 8, and the fail-closed/no-private-layout
rules. Make authority construction store-controlled and distinguish explicit
first bootstrap from missing-after-initialization/cutover so record loss fails
closed without rewriting evidence. Register both the machine layout record and
its lock in `STATE_SURFACES`; they are currently omitted. Add missing, malformed,
locked, foreign-root, and post-cutover-loss tests.

## 4. The aggregate schema omits contract fields

The schema test checks table names only. `PRAGMA table_info` confirms two required
data-model fields are absent:

- `delivery_results.epoch_id` — `data-model.md:120` requires every journal,
  attempt, result, and outbox row to carry the owner UUID, epoch, and stable ID;
- `migration_manifests.source_paths` — `data-model.md:158` requires the exact
  inventoried legacy source paths.

Add the fields with the appropriate owner/epoch foreign-key constraints and add
an exact column/constraint mirror test for every aggregate table. Table-name
presence alone is not a contract round trip.

## 5. Required concurrency evidence is not committed

The current shared-UUID test uses threads, not processes, and the layout race
only commits the cutover-first/stale-redirect ordering. Independent review probes
show the implementation currently serializes two processes correctly and also
handles writer-first (one legacy write while cutover waits) plus cutover-first
(one project-store redirect), but T010 and the reviewer guidance require these as
durable tests. Commit deterministic cross-process SQLite coverage and both layout
orderings without sleeps. Keep the exact-verification false/true controls and the
single-redirect/no-double-write assertions.

## 6. Formatting gate is red

`uv run --with ruff ruff check ...` and strict mypy pass, but
`uv run --with ruff ruff format --check ...` reports nine files requiring
formatting, including all five touched source modules and both changed
architecture tests. Format the owned files and rerun check, format-check, mypy,
diff-check, the 111-test gate, and the 47-pass/2-xfail architecture gate.

## Verified evidence

- Red commit `d307032e5`: four expected collection errors on the absent APIs.
- Green commit `66f8654ab`: official gates reproduce as `111 passed` and
  `47 passed, 2 xfailed`; strict mypy and Ruff check pass; `git diff --check`
  passes.
- Census mutation: a new component `sqlite3.connect()` plus `.commit()` produced
  two growth keys; a generation-bypassing `INSERT` produced a layout-writer
  growth key. The canonical exact-count additions are narrow.
- All 13 `TODO(#3280)` comments remain unchanged; deferred #3280 work is not part
  of this rejection.
- UUID normalization/path isolation, owner/version/corrupt/SQLite-lock refusal,
  exact verification callback, one-redirect behavior, and local platform cases
  otherwise pass.
- The only ignored baseline is the accepted #3130/#3237 lifecycle pin.

## Anti-pattern checklist

1. **Dead code — N/A**: this WP explicitly stages the aggregate before dependent
   repository conversion; production payload wiring belongs to later WPs.
2. **Synthetic-fixture test — PASS**: the owned tests invoke the real store,
   SQLite, layout authority, and context APIs, although the missing contract
   cases above must be added.
3. **Silent empty return — PASS**: no new silent empty-return path was found.
4. **FR coverage — FAIL**: FR-002, FR-010, FR-026, and FR-029 have the blocking
   gaps above.
5. **Frozen surface — PASS**: no frozen surface was modified.
6. **Locked decision — FAIL**: transaction ownership, store-derived authority,
   and sole fail-closed layout authority are locked decisions and are not yet
   enforced.
7. **Shared-file ownership — PASS**: `cf3d15090` records the authorized census
   ownership; exact additions are narrow and #3280 comments are unchanged.
8. **Production fragility — PASS**: new raises are fail-closed boundary errors;
   no new transient request-handler raise was introduced.

WP03, WP04, and WP05 depend on WP02 and must rebase after the corrected reroll.

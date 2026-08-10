---
affected_files: []
cycle_number: 1
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-10T02:47:58Z'
reviewer_agent: codex
wp_id: WP04
---

# WP04 Review Cycle 1 — Changes Requested

The project-store repository conversion is directionally sound, but the current
implementation does not enforce the locked consent, exact-purge, and A/B
isolation boundaries. The following are material blockers.

## 1. Any object can authorize sealed-history selection

`SqliteDeliveryLedger.select_undelivered()` accepts `history_action: object |
None` and trusts only duck-typed `project_uuid` and `row_ids` attributes
(`src/specify_cli/delivery/ledger.py:365-379`). It neither requires WP03's
factory-controlled `HistoryDisclosureCapability` nor revalidates the persisted
action/cohort/current consent, target, and admission authority through
`consume_history_disclosure()`.

An exact real-store probe captured `sealed-row` before opt-in. Ordinary
selection returned `[]`; passing
`SimpleNamespace(project_uuid=PROJECT, row_ids=("sealed-row",))` returned
`["sealed-row"]`. This bypasses WP03's deliberately non-public capability
constructor and can disclose capture-only or sealed rows without persisted
operator confirmation. Bind the selection API to a genuine capability and a
store-owned revalidation path; add negative tests for arbitrary lookalikes,
fabricated row IDs, stale confirmation after opt-out, changed cohort, and
cross-project capability use.

## 2. The live body purge reports removal but retains the confidential body

`OfflineBodyUploadQueue.remove_project_tasks()` marks every row `uploaded`
instead of deleting it (`src/specify_cli/sync/body_queue.py:361-367`), while
`count_by_project()` deliberately counts terminal rows. Consequently
`purge_project_body_uploads()` (`src/specify_cli/delivery/retention.py:234-244`)
cannot satisfy its own exactness result.

An exact real-store probe enqueued `spec.md` containing `secret body`, then ran
the live non-dry-run purge. It reported `removed=1`, but `target_before=1`,
`target_after=1`, and `is_exact=False`; direct SQL still found one
`body_upload_tasks` row whose `body_reference` contained the secret, merely in
state `uploaded`. Physically delete the selected current-store body rows under
the sole immediate layout permit and prove 100% of A/0% of B with a direct
on-disk differential.

The old #3030 tests also need explicit sequential ownership rather than being
left red or motivating a compatibility constructor:

- `tests/delivery/test_body_queue_purge_differential_3030.py` belongs to WP04.
  Re-pin its current per-project exact-purge contract to
  `ProjectSyncStore`/UoW and the `body_upload_tasks` table. At this HEAD it has
  one failure and seven setup errors because it still calls the retired
  `OfflineQueue()`/`db_path=` constructors.
- `tests/delivery/test_purge_all_body_uploads_3030.py` belongs to WP10. Its
  shared `queue.db`, blank/whitespace owner rows, and total legacy-store
  disposition are migration/quarantine/cutover concerns. It currently fails
  collection because the retired `purge_all_body_uploads` symbol was removed;
  WP10 must preserve equivalent total legacy-source disposition without WP04
  restoring a live shared-store API.

## 3. Project A status can read and attribute project B's body queue

`build_project_store_status()` validates the journal and ledger owners but
accepts `body_upload_queue: Any` and never validates its owner
(`src/specify_cli/delivery/status_report.py:533-545,588-590`). A real two-store
probe passed A's context/journal/ledger and B's body queue. The function emitted
`project_uuid=A` with `body_task_count=1` read from B, without rejection.

This violates the task's explicit rule to reject adapters that accept
independently paired store/UUID authorities even when current callers happen to
pair them correctly. Require a typed project-owned queue and verify it is bound
to the same active store/UoW before reading. Add the A-context/B-queue negative
case and a direct zero-B-open/read assertion.

## 4. The repository's normal pytest and formatting gates are red

Every normal pytest invocation is stopped during collection by the repository's
wall-clock assertion gate. Candidate commit `bea905e79` introduced
`assert time.time() >= now` at `tests/sync/test_body_queue.py:270`; the gate
reports that exact line and runs zero tests. The focused suites pass only when
the root collection hook is bypassed with per-directory `--confcutdir`, which is
diagnostic evidence, not a valid green receipt.

Ruff lint passes, but `ruff format --check` reports all 24 files in
`bea905e79` would be reformatted. Strict mypy passes on the ten touched source
modules and `git diff --check 4f0233f66^..bea905e79` passes. Remove the wall-clock
assertion, format the owned change, and rerun the ordinary repository commands
without bypassing collection controls.

## Verified passing and boundary evidence

- Focused owned tests: 12 passed (5 journal, 4 delivery/retention, 3 outbox).
- Architecture gates: 52 passed, 2 expected failures across project-store,
  egress-consent, and writer-census coverage, including the resolver and permit
  mutants.
- Sequentially authorized migrated suites: 34 journal, 93 delivery, and 64 sync
  tests passed under diagnostic `--confcutdir` runs.
- The journal/ledger/outbox rollback tests use one outer UoW; A/B store ownership,
  FIFO ordering, stable identities, capture sequence/epoch assignment, terminal
  parking, SQL UUID/eligible-epoch selection, and no component connect/commit
  behavior otherwise passed review.
- `preserve_delivery_history` has no current call-site inversion: GC explicitly
  passes `True` and preserves ledger history; explicit project purge uses the
  default `False` and removes aggregate delivery children. No fallback call site
  was found.
- The WP04 implementation commit does not touch WP07/WP10 reserved source or
  test files. The architectural files contain exactly 12 `TODO(#3280)` markers;
  the repository-wide thirteenth is the separate pre-existing incident-baseline
  marker.

## Anti-pattern checklist

1. **Dead code — FAIL**: the live body purge path reports a destructive action
   while leaving the payload row and body bytes on disk.
2. **Synthetic fixtures — PASS**: the blocking consent, purge, and A/B probes
   use real `ProjectSyncStore` instances, UoWs, and SQLite rows.
3. **Silent empty/success return — FAIL**: the body purge reports `removed=1`
   despite retaining the row; its `is_exact=False` exposes the contradiction but
   does not make the destructive primitive correct.
4. **Functional-requirement coverage — FAIL**: FR-010/FR-017/FR-028, NFR-004,
   and C-002/C-009 remain unenforced at the three boundaries above.
5. **Frozen surface — PASS**: no frozen external contract was identified in the
   owned change.
6. **Locked decisions — FAIL**: explicit/revalidated sealed-history authority,
   exact purge, and physical A/B isolation are locked mission decisions.
7. **Shared-file ownership — FAIL**: the per-project and total-body #3030 tests
   were left unassigned/unmigrated; use the WP04/WP10 split above.
8. **Production fragility — FAIL**: ordinary pytest collection is globally red,
   and status can misattribute a foreign project's live queue count.

WP06 and WP07 depend on this repository/selection boundary and must use the
corrected WP04 reroll. WP10 must receive the explicit legacy total-body-purge test
ownership before cutover work begins.

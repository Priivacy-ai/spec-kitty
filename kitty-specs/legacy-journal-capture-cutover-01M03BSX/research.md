# Research: Legacy→Journal Capture Cutover

Phase 0 consolidation. Source: pre-mission research squad (gitignored
`work/3425-legacy-layout-research/` — `01-root-cause-and-fix-options.md`,
`02-related-p0-bugs-same-surface.md`, `03-open-pr-conflict-scan.md`) plus live
dogfood evidence (mission `create` emitted the #3425 warning five times).

## Decision 1 — #3425 is two distinct bugs; the reproductions are mis-attributed

- **Decision**: Treat the credential/queue regression and the layout silent-capture as
  separate defects with separate fixes (IC-01 and IC-02).
- **Rationale**: The three red-first tests never reach the layout silent-capture path.
  Test A fails at `default_queue_db_path()` (`sync/queue.py:195`), which raises
  *unconditionally* (not layout-gated — the test docstring is wrong) and asserts a
  retired no-arg `OfflineBodyUploadQueue().db_path` API. Tests B & C fail because
  `read_queue_scope_from_credentials` (`sync/queue.py:175`) was rewritten JSON-only and
  no longer derives a scope from the TOML credentials the tests write, so the FR-011
  auth gate (`mission_setup_plan.py:1043-1075`, runs before the boundary preflight)
  refuses an authenticated host with exit 2.
- **Correction recorded**: the two "SAAS auth refusal" failures are a **real #3293
  credentials-parser regression**, NOT CI-env artifacts (PR #3467's body and the first
  triage mislabeled them). This satisfies the charter Pre-existing Failure Reporting rule.
- **Alternatives considered**: (a) treat all three as CI-env noise — rejected, they
  fail deterministically on a coherent host; (b) revert #3293 — rejected (C-003).

## Decision 2 — Fresh roots resolve to `project_only`; legacy-with-data auto-cutover

- **Decision**: `_initial_state()`/resolution returns `project_only` for a root with no
  `.layout-generation.json` **and** no legacy data; a root with real legacy data is
  auto-migrated (lazy, on first live write).
- **Rationale**: The `LayoutMode.LEGACY` default (`sync/layout_generation.py:129-136`)
  is correct only for a root that actually holds legacy data awaiting migration; a
  greenfield root has none and is stuck LEGACY forever because leaving LEGACY is
  manual-only (`sync project-store-migrate` → `begin_cutover` → `publish_project_only`).
- **Non-destructive**: because retiring `queue.db` (#2750) is out of scope, cutover
  *reads* the legacy store and never deletes it — the source is preserved as migration
  input, making the mutation recoverable and low-risk (no heavyweight backup needed).
- **Alternatives considered**: (a) keep manual, just make failure loud (detect-and-refuse)
  — rejected by user (they chose auto-cutover); (b) eager cutover at startup — rejected
  as more invasive than lazy-on-first-write with equal safety.

## Decision 3 — Fold #3391: make the emitter capture failure observable

- **Decision (updated per user)**: FOLD #3391 into this mission. The common-case write
  is made to *succeed* (Decision 2), and the emitter swallow site
  (`sync/emitter.py:2114`, `_capture_to_journal`) is fixed to surface a genuinely-
  unrecoverable failure loud-but-non-fatal — closing #3391.
- **Rationale**: #3391 is an assigned *issue* with no PR/active work, and FR-001's
  "no silent-success capture" guarantee has a real gap for unrecoverable cases without
  the loud backstop. Depending on someone else's unstarted issue is fragile; folding it
  in makes the mission self-contained. Coordinate with the assignee (MOES-Media) so the
  fix lands once. Constraint: must stay **non-fatal** — a capture failure must not crash
  the host command; and must not warning-storm (IC-02 fixes the common case, so the loud
  path is exceptional).
- **Alternatives considered**: (a) depend on #3391 landing first — rejected (unstarted
  issue, fragile); (b) leave the emitter swallow untouched and rely only on writes
  succeeding — rejected (leaves the unrecoverable-case silent-success gap in FR-001).

## Decision 4 — Keep ProjectSyncStore-owned queue selection; rewrite Test A

- **Decision**: Preserve #3293's ProjectSyncStore selection; rewrite Test A to assert
  that contract (drop the retired no-arg queue API) while still pinning the no-silent-
  capture behavior.
- **Rationale**: #3293 was a deliberate recent landing closing #3262; reverting it is
  out of scope and would regress the per-project consent work.

## Decision 5 — Fold the same-root cluster (minus #3278)

- **Decision**: Fold #3476 (backfill cutover silent no-op — IC-04) and #2846 (divergent
  duplicate legacy↔journal events — IC-03). **#3278 (honest `sync now`) is DEFERRED.**
- **Rationale**: all share the legacy↔journal split root surface. #2750 (retire legacy
  path) is out of scope; #2688 auto-migration direction is partially realized by Decision 2.
  Nearest architectural parent: #2144 (event durability, stijn-dejongh).

## Decision 7 (post-squad, user) — Drop #3278 to resolve the FR-006 ↔ #2750 contradiction

- **Decision**: Defer honest `sync now` convergence (#3278, was FR-006) to a separate mission.
- **Rationale**: the post-plan architecture lens surfaced a documented, code-level
  contradiction — `migrate_journal.py:40-52` records that *import-alone never converges the
  legacy-row boundary* (`sync now` refuses forever) because the convergence/cleanup step was
  retired (`OfflineQueue` has no source-path constructor). Honest sync-now therefore requires
  DELETING migrated legacy rows, which reopens #2750 (kept out of scope). Rather than reopen
  #2750 or invent new "migrated-retained" state semantics, the user chose the smallest
  coherent scope: keep #2750 out, defer #3278. #2846 dedup still applies (the copy must not
  duplicate); only sync-now reporting is deferred.

## Decision 8 (post-squad) — Reuse the canonical migration engines

- **Decision**: Auto-cutover calls `migrate_journal.migrate_queues_to_journal` /
  `project_store_migration` (dedup by `(event_id, source_digest)`, `project_uuid`
  attribution for ownerless rows, divergent-payload quarantine, documented idempotence) —
  never a bespoke drain/copy.
- **Rationale**: charter "use canonical sources"; the engines already implement exactly the
  copy semantics the original plan proposed to rebuild, and their reuse is required for
  INV-2 conservation and ownerless-row handling (arch BLOCKER-1, MAJOR-6). Deterministic
  root-derived `migration_id` + auto source discovery (`discover_source_dbs`) replace the
  operator-supplied `--migration-id`/`--source` the engine otherwise needs.

## Decision 9 (post-squad) — Close the CUTOVER_PENDING drop window; crash-safe recovery

- **Decision**: While `mode == CUTOVER_PENDING`, live writes block-and-retry within a bounded
  wait; if cutover cannot complete they route to the loud emitter surface (never silent). A
  crash between begin and publish leaves a re-enterable `CUTOVER_PENDING`/`FAILED` state that
  the next run completes/retries under a documented rule — never bricking the root.
- **Rationale**: `_destination` returns LEGACY for `CUTOVER_PENDING` (268-272) → both write
  guards raise → swallowed → the exact P0, made permanent (arch BLOCKER-2, risk BLOCKER-1).

## Decision 10 (post-squad) — Emitter observability mechanism; detection order; auth-signal seam

- **Emitter (MAJOR-3)**: fix BOTH swallow sites (`_capture_to_journal` ~2114 and
  `_emit_for_project_context` ~2334-2336 — the latter is the live-reproduced one); deliver
  boundary observability via a process-level captured-failure flag the command epilogue
  inspects, not by raising (`_emit` never-raises across ~30 callers).
- **Detection (MAJOR-5)**: decide `project_only` for no-legacy-data roots BEFORE `_read_locked`
  persists LEGACY; use the real reader (`discover_source_dbs`), not the stub
  `detect_legacy_rows_for_scope`; data-model corrected to the `.initialized` marker.
- **Auth-signal (MAJOR-4)**: IC-01 restores parsing to yield a boolean "authenticated?" for
  the gate; it must NOT re-introduce credential→`scope_db_path` derivation at
  `preflight.py`/`target_authority.py` (the C-003/FR-009 revert).
- **Test isolation (MINOR-8)**: cutover/layout tests use isolated temp roots; never the live
  machine-global `~/.spec-kitty` (this dev box is itself a legacy root).

## Decision 6 — Conflict posture

- **Decision**: Proceed on `fix/legacy-journal-capture-cutover`; rebase before landing.
- **Rationale (squad finding 03)**: 0 of 25 open PRs touch the six target files
  (LOW risk); no open PR addresses #3425. Watch draft #3300 (per-project sync consent)
  — same family, currently no `src/` edits. All target files were last modified by
  merged #3293 (`cd3d6a91d2`); nothing has re-touched them since.

## Adversarial Evidence

No security-impacting dependency decision (no dependency changes). A pre-`tasks`
adversarial-squad pass is not required by the supply-chain contract here; a squad may
still be run at the post-tasks anti-laziness point-cut per campsite discipline. No
contested finding outstanding.

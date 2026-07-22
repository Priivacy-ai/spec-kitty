# WP01 re-work — `verify_backfill` library correctness (discovered by WP03's real corpus run)

WP03 ran `migrate backfill-runtime-state` over the real 300-mission dogfood corpus: dry-run clean (285 missions, 3303 would-seed events), but the **real run failed fail-closed verify on 8 missions** (exit 1). Corpus-wide verify is NOT `ok`, so NFR-001/SC-001 cannot be met and WP03 is blocked. The spec's assumption "the WP03 backfill library is complete and correct" is **falsified**. Fix `src/specify_cli/migration/backfill_runtime_state.py::verify_backfill` (this is now in WP01's scope — FR-002 "wire the fail-closed verify" is incomplete if the wired verify is wrong on the real corpus). All are deterministic, so a re-run yields byte-identical seeds.

## Defect 1 (7 missions) — never-claimed WPs hard-failed by verify (contradicts spec Edge Case)
- **Missions:** `005-refactor-mission-system`, `055-agent-skills-pack`, `057-doctrine-stack-init-and-profile-integration`, `062-fix-doctrine-migration-test-failures` (WP11), `analysis-report-coord-worktree-fix-01KV6DC9`, `merge-coord-rollback-transactionality-01KXTM59`, and our own live mission's not-yet-claimed WPs.
- **Mismatch:** `"WPxx: legacy carries runtime state but snapshot has none (count mismatch)"`.
- **Root cause:** these WPs carry evictable state (done subtasks in `tasks.md`) but have **no claim anchor** (no transition events). `_build_seed_events` (~:397) **correctly skips** them ("no claim anchor — runtime seed skipped"), but `verify_backfill` (~:702) builds `legacy_runtime_wps = {has_evictable_state()}` **without** excluding anchor-less WPs → counts them → false count-mismatch.
- **Spec Edge Case (binding):** "A WP that was never claimed carries no claim anchor; its runtime seeds are skipped … Backfill must **warn, not fail**."
- **Fix:** `verify_backfill` must mirror `_build_seed_events`' skip — exclude WPs with no `_claim_anchors` entry from the count-parity comparison (or count them as legitimately-empty). Add a unit test: a fixture WP with done subtasks in tasks.md but zero transition events → verify passes (warns), does not fail.

## Defect 2 (1 mission) — `tracker_refs` dup-vs-union parity divergence
- **Mission:** `unshim-wave2-01KWMCAX` (WP01–09).
- **Mismatch:** `legacy=['#','2','2','9','1'] snapshot=['#','2','9','1']`.
- **Root cause:** that WP's frontmatter authored `tracker_refs` as a `CommentedSeq` of single characters **with a duplicate** (`'2'`) — corrupt authored data (a string `"#2291"`-ish char-split). Legacy reader preserves the 5-tuple; the reducer folds `tracker_refs` as a **set-union that dedups** → 4 elements → parity mismatch.
- **Fix:** `verify_backfill` should compare `tracker_refs` **consistently** with how the reducer folds it (set/multiset semantics), or normalize the malformed authored value before comparison, so a benign dedup is not a "value mismatch". Add a unit test with a duplicate-bearing `tracker_refs` fixture.

## Defect 3 (design) — live / already-migrated mission tolerance
- Our own `runtime-state-corpus-cutover-01KXZ0AX` shows a **reverse** divergence (`subtasks`/`shell_pid`/`agent` present in snapshot, absent in legacy) because it is the **actively-running** mission whose lane-a WP01 already emitted **real** `InnerStateChanged` events during this very migration.
- **Spec Edge Case (binding):** "A partially-migrated corpus (some missions flipped, some not) must be a valid intermediate state." A WP whose snapshot already carries event-sourced runtime state (not just frontmatter) is already-migrated and must not fail verify.
- **Fix:** `verify_backfill` must tolerate a WP whose snapshot carries runtime state absent from legacy frontmatter (already event-sourced / mid-migration) — verify parity only for WPs the backfill is responsible for seeding, and treat already-event-sourced WPs as consistent. Consider skipping the actively-running mission, or (better) making verify robust to snapshot-ahead-of-legacy.

## Write-location finding (for WP03's eventual commit)
`canonicalize_feature_dir` + `locate_project_root()` redirect the backfill's writes to the **primary-partition / repo-root checkout** (`/home/jeroennouws/dev/spec-kitty/kitty-specs/`, branch `feat/runtime-state-corpus-cutover`), **not** the lane worktree. This is consistent with the status-authority model (status → primary partition) but means WP03's large seed payload commits on the primary partition, not lane-c. Decide the commit target when WP03 re-runs (the seeds must land within the mission's cutover merge unit on `feat/runtime-state-corpus-cutover`).

## Acceptance for the fix
- `migrate backfill-runtime-state` real run over the full dogfood corpus verifies **`ok` corpus-wide** (zero mismatches), exit 0.
- New unit tests for Defects 1–3 (never-claimed skip, tracker_refs dup, already-event-sourced tolerance) — non-vacuous.
- Deterministic: re-run seeds byte-identical; idempotent.
- No new suppressions; `ruff`+`mypy` clean; cx≤15.

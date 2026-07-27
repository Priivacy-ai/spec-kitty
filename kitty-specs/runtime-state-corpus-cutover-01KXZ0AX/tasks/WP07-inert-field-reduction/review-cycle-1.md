---
affected_files: []
cycle_number: 1
mission_slug: runtime-state-corpus-cutover-01KXZ0AX
reproduction_command: null
reviewed_at: '2026-07-20T14:05:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP07
---

# WP07 Review — APPROVED (IC-06 inert-field reduction + dead-closure fold)

Commits 1d189bd95 (Parts A+B) + b25292a02 (straggler). Verified: 120 tests pass; the sole failure is the pre-existing `SYNC_DISABLE_ENV_VARS` phantom (base-red, #2814 — WP07's fold orphaned ZERO new dead symbols, confirmed).

- **Part A — inert reduction (rigorous, not assumed):** removed `branch_strategy_override` — the only WPMetadata field that is BOTH zero-reader across src/ AND parse-safe under `extra="forbid"` (a merge-test-repair vestige). Proved the review/observed fields (review_status×109, reviewed_by×106, reviewer_agent×245, …) are corpus-locked by `extra="forbid"` → removing any raises ValidationError (the regression the WP forbids); snapshot carriers + `WP_FIELD_ORDER` + `feature_slug` correctly kept; `status_phase` out of bounds (not a WPMetadata field). T030 zero-readers guard (AST sweep) + durable co-located poison-test (non-vacuous, mirrors WP06 SC-009); red-first demonstrated. 10 tests.
- **Part B — FOLD (campsite consequence of WP05):** all 9 production-dead move-task write/commit functions deleted (each proven callerless via grep; boundary `_collect_status_artifacts`/`_mt_resolve_current_agent` kept live). Cross-mission source-SHA-pin `test_wp07_diff_does_not_touch_status_bundling_symbols` correctly DELETED with its now-deleted symbols. ~5 missions' test surfaces reconciled (compat-surface 145→136; placement/partition files deleted; degod/seam/coord_2155 arms). tasks.py re-exports removed. `test_no_dead_symbols` green (no new offender), all move-task gates green.
- **Straggler reconciled STRONGER (not weakened):** `test_shell_pid_string_in_file` → `test_shell_pid_is_snapshot_sourced_not_frontmatter` — drives a real claim, writes a STALE frontmatter shell_pid, asserts the snapshot value wins (405597) and the divergent frontmatter (111) does NOT leak + coercion applies. test_wp_metadata.py 87 pass. Confirmed the only such straggler in that file.
- ruff+mypy clean; zero new suppressions; pure deletion (no cx growth).
- Corpus-on-feat caveat honored (test_dogfood_corpus_backfilled not chased).

**Verdict: APPROVED.** Phase 1 (WP01–07) is complete: fail-closed corpus cutover + unconditional flip + fallback removal + invariant hardening + inert reduction, all with non-vacuous proofs and honest reconciliation.

---
affected_files: []
cycle_number: 3
mission_slug: runtime-state-corpus-cutover-01KXZ0AX
reproduction_command: null
reviewed_at: '2026-07-20T12:17:27Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP01
---

# WP01 Review — Cycle 3: APPROVED (verify_backfill corpus-correctness fold)

WP03's real 300-mission run exposed 3 `verify_backfill` defects; this cycle folds the library fix into WP01 (FR-002 completion). Verified against the diff (`906af76f5`) + re-run tests + the fail-closed integrity (the load-bearing NFR-001 concern).

## Fail-closed integrity — PRESERVED (the critical check)
Every value dimension checks **legacy ⊆ snapshot** (data loss still aborts), tolerating only benign ahead-ness/dedup:
- `tracker_refs`: `legacy_refs <= snap_refs` else "legacy refs lost" — set semantics dedup a malformed authored duplicate (Defect 2) but a genuinely-lost ref fails.
- `subtasks`: `legacy_done <= snap_done` else "completed subtasks lost" — progress-ahead tolerated, lost completion fails.
- scalars: a `None` legacy places no constraint; a real legacy value must be reflected.
- count: only anchored-evictable WPs are count-checked (`seeded_wps`), so never-claimed WPs warn-not-fail (Defect 1, spec Edge Case); a snapshot WP with **no legacy WP file at all** is a phantom → aborts.
Follow-up correction: the final verifier checks the exact deterministic seed-row payload, so a later
same-slot runtime event remains legitimate latest-wins history. The anchored-WP-data-loss count check,
pre-strip ordering guard, and unreadable-log guard remain fail-closed.

## Non-vacuity proven
- `test_verify_fails_when_anchored_wp_runtime_missing_from_snapshot` — removing an anchored WP's runtime from the snapshot (genuine data loss) still ABORTS. ✅ (the fix is not vacuous)
- `test_refuse_to_flip_on_conflicting_seed_leaves_meta_untouched` — corruption of the exact deterministic seed row → verify fails → flip refused, meta byte-untouched. ✅
- `test_verify_never_claimed_wp_warns_not_fails` (Defect 1), `test_verify_tolerates_snapshot_ahead_of_legacy` (Defect 3), tracker_refs-dup (Defect 2) — all pass. ✅

## Corpus proof
`cutover_repo` over all dogfood missions from the fixed src: **total 299 · flipped 299 · seed events 3303 · FAILED 0 · exit OK** — the 8 previously-failing missions now verify. Seed payload reverted from the primary checkout (WP03 owns the commit).

## Verification (re-run by reviewer)
- `test_runtime_state_cutover.py` + `test_backfill_runtime_state.py` (`tests/unit/migration/`) + `test_backfill_runtime_state_cli.py`: **59 passed**.
- `ruff` + `mypy` on `backfill_runtime_state.py`: **clean**; cx ≤15.
- `backfill_runtime_state.py` + its unit test are out-of-map (coordinator-authorized FR-002-completion — the wired verify was buggy on the real corpus).

**Verdict: APPROVED.** WP01 now delivers a fail-closed verify that is correct on the real corpus while preserving zero-silent-data-loss (NFR-001). Note for WP03: the retained `read_legacy_runtime`/`LegacyWPRuntime` dead-symbol residuals need a `src/` caller (or `__all__` fold) to fully drain the shrunk allowlist.

---
affected_files: []
cycle_number: 1
mission_slug: ci-suite-stability-test-isolation-01M22MM5
reproduction_command: spec-kitty agent tasks move-task WP06 --to approved --mission ci-suite-stability-test-isolation-01M22MM5
reviewed_at: '2026-09-09T17:57:12Z'
reviewer_agent: user
wp_id: WP06
---

Approved by user: Review passed: 14 MIXED splits verified (functional asserts stay per-PR unmarked, timing→@performance via assert_timing_budget with budgets preserved; lanes cycle-detection split ADDS real per-PR functional coverage by dropping the skipif gate). Vocab-blocked deletion test_resolve_context_within_research_2x fully removed, file collects (12 tests), time/statistics imports cleaned. backfill 'left unchanged' call is sound (happens-after ordering assert, not a wall-clock budget). Guards green (85 passed incl timing-coverage-invariant + ratchet), TIMING_ASSERTION_VOCABULARY untouched (C-004). @performance run 18 passed budgets intact + nightly-collected; per-PR 235 passed; ruff clean. Minor non-blocking: orphaned _RESEARCH_ACTIONS constant left in drg-nodes.

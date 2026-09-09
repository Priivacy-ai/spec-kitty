---
affected_files: []
cycle_number: 2
mission_slug: ci-suite-stability-test-isolation-01M22MM5
reproduction_command: spec-kitty agent tasks move-task WP07 --to approved --mission ci-suite-stability-test-isolation-01M22MM5
reviewed_at: '2026-09-09T17:50:43Z'
reviewer_agent: user
wp_id: WP07
---

Approved by user: Cycle-2 review passed: timeout marker moved off helper onto both split siblings (functional companion + @performance), both carry 10s hang-cap and collect/pass with pytest-timeout 2.4.0; exclude-ratchet green (85 passed); test_observation graduated + format-clean, test_reconcile clean, other excluded files still genuinely reformat; TIMING_ASSERTION_VOCABULARY unchanged (C-004); vocab-blocked deletion gone; ruff check clean

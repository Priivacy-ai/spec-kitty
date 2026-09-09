---
affected_files: []
cycle_number: 1
mission_slug: ci-suite-stability-test-isolation-01M22MM5
reproduction_command: spec-kitty agent tasks move-task WP08 --to approved --mission ci-suite-stability-test-isolation-01M22MM5
reviewed_at: '2026-09-09T17:43:23Z'
reviewer_agent: user
wp_id: WP08
---

Approved by user: Review passed: #4015 MIXED splits across auth/cross_cutting/review/status/zeitgeist_client all preserve functional coverage (functional assert stays unmarked per-PR; timing assert relocated to @pytest.mark.performance via assert_timing_budget with budget PRESERVED). Spot-checked auth_doctor(3s), tail_reader(0.05), repo_identity(x2), cross_cutting/misc(x3), verdict_commit_queue(x2). auth_doctor <3s split not deleted. No deletions (diff-filter=D empty). Guards green 79 passed; TIMING_ASSERTION_VOCABULARY token set byte-identical to base (C-004). @performance suite 29 passed/1 pre-existing-quarantine skip. Per-PR -m 'not performance' 238 passed. ruff clean.

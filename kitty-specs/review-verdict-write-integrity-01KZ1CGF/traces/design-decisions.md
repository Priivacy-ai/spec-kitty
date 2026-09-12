# Tracer: design-decisions

One entry per finding: `YYYY-MM-DD · actor · <text>`.

---

2026-08-02 · claude · Post-merge validation (running the full targeted suite on the merged target branch, the first point WP01+WP02 code coexists) caught a regression neither WP01's declared Test Strategy nor either independent reviewer's scoped runs included: tests/regression/test_2684_force_provenance.py started failing because WP01's cycle-2 commit-status-check fix (raise on any non-'committed' CommitArtifactResult status) didn't account for --no-auto-commit callers, where a 'no_op_wrong_surface' status is an expected, benign no-op (operator explicitly opted out of commits), not a failure. Fixed by threading st.resolved_auto_commit into both tasks_move_task.py call sites, passing commit_router=None (cycle.py's own documented 'skip commit' contract) when auto-commit is off -- matching the existing convention at line 327 of the same file. Lesson: a WP's declared Test Strategy scope (tests/review/ tests/post_merge/ tests/agent/) can miss regressions in adjacent, topically-unrelated test files (tests/regression/) that exercise the same code path from a different angle (--no-auto-commit + protected-main fixtures); the post-merge full-suite run on the target branch is the real safety net for this class of gap.

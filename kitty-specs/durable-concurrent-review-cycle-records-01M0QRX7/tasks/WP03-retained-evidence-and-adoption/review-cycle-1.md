---
affected_files: []
cycle_number: 1
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T05:37:24Z'
reviewer_agent: user
wp_id: WP03
---

# WP03 Review Feedback — Cycle 1

**Issue 1 [BLOCKER] — retained-record discovery holds `feature_status_lock` across Git subprocesses.**

`_adopt_or_allocate_review_cycle_locked()` acquires `feature_status_lock` at `src/specify_cli/review/cycle.py:852` and calls `_matching_retained_review_cycle()` before releasing it. That helper resolves placement and, for matching records, invokes `_read_artifact_at_ref()`; the latter runs `git show` at lines 692–702. The no-candidate path also calls `_allocate_and_write_review_cycle_locked()` while the outer lock is held, and its nested `feature_status_lock()` acquisition resolves the Git common directory with `git rev-parse`. A direct subprocess spy on the automatic path observed `git symbolic-ref`, `git branch --show-current`, and `git rev-parse --git-common-dir` while the feature-status lock bookkeeping was non-empty. This violates spec C-002 and plan.md lines 52 and 85–86, which require the short status lock to be released before *any* Git subprocess.

Refactor adoption into phases so local candidate enumeration/allocation and validation occur under the short status lock, while placement resolution and governed-ref reads occur outside it. Avoid nested `feature_status_lock()` acquisition from an already-locked caller. Revalidate the selected local candidate under the short lock before adopting it so the split does not create a TOCTOU ambiguity. Add a production-path boundary test that spies on every Git subprocess during automatic retained adoption and fails if `feature_status_lock` is held; it must cover both the no-candidate allocation route and an existing-candidate governed-ref read.

**Issue 2 [BLOCKER] — the queue non-acquisition test exercises only local-only mode.**

`test_cycle_writer_never_acquires_verdict_save_queue()` calls `create_rejected_review_cycle()` without a `commit_router`, so it takes the explicit `local_only` branch. It would remain green if queue acquisition were added only to the automatic persistence/adoption branch that WP04 actually calls. T013 requires proof for the non-acquiring automatic operation, not only for the documented queue-bypass mode.

Drive this test with a commit router through automatic allocation and retained adoption (including a failure/retained retry), keep the acquisition seam patched to raise, and assert the expected typed outcomes. Retain the local-only queue-bypass case as a separate assertion.

**Issue 3 [BLOCKER] — T015's retained-artifact index-state matrix is not covered.**

The added repository-state test covers an unrelated partially staged file while the new evidence file is untracked, but T015 explicitly requires retry/recovery cases where the failed/retained evidence artifact itself is untracked, staged, and partially staged, plus adopted already-committed recovery. There is no test that stages or partially stages `review-cycle-*.md` before an identical retry, so index restoration damage on the artifact path can pass the suite.

Add real-router recovery tests for retained evidence in each required index state. Snapshot the relevant cached/worktree bytes and porcelain state before retry, verify the governed destination bytes after a durable result (or explicit retained failure), and prove unrelated staged/worktree/untracked state is unchanged.

Validation evidence collected: `tests/review/test_cycle.py` 39 passed; downstream verdict durability/rejection tests 14 passed; Ruff passed; strict mypy passed; changed-line diff coverage against `a831487d` was 92.6% (95 changed lines, 7 missing). These green gates do not cover the blockers above.

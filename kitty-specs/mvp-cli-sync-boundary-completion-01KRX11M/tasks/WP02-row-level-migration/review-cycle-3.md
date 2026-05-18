---
affected_files: []
cycle_number: 3
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
reproduction_command:
reviewed_at: '2026-05-18T09:30:12Z'
reviewer_agent: codex:gpt-5:reviewer-rita:reviewer
verdict: approved
wp_id: WP02
---

# WP02 — Row-level queue migration (cycle 2 review, override-approved)

**Verdict: approved**

This artifact records the cycle-2 approval that the original reviewer
(`codex:gpt-5:reviewer-rita:reviewer`) issued verbally but could not persist
because the codex sandbox denied writes to the planning repo. The orchestrator
applied `spec-kitty agent tasks move-task WP02 --to approved
--skip-review-artifact-check` with the verbal approval recorded in the
override note.

## Summary

- `_migrate_legacy_queue_to_scope()` now commits `dst` (scoped DB) BEFORE
  `src` (legacy DB) so a `src.commit()` failure-after-`dst.commit()`-success
  leaves the legacy rows intact for retry. Retry is safe because the scoped
  inserts use `INSERT OR IGNORE` keyed on event_id / upload_id.
- New regression test `test_migration_durability_dst_commit_first` simulates
  `src.commit()` failure after `dst.commit()` and proves legacy rows survive.
- Body-upload migration covers the non-empty-scoped case; idempotent retry.
- 11 migration tests pass; 35 sync tests pass overall.

## Acceptance criteria

- [x] FR-006 (non-empty scoped DB merge)
- [x] FR-007 (body_upload_queue coverage)
- [x] NFR-001 (≥90% coverage)
- [x] NFR-002 (no new mypy --strict errors)

## Implementing commit

`e5e3330f fix(WP02): reverse commit order so destination persists before legacy delete`

---
affected_files: []
cycle_number: 2
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
reproduction_command:
reviewed_at: '2026-05-18T09:19:18Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
review_artifact_override_at: "2026-05-18T09:30:12Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP02"
review_artifact_override_reason: "Cycle 2 review approved (codex verdict): durability fix verified — dst.commit before src.commit; test_migration_durability_dst_commit_first regression test in place. 11 migration tests pass; mypy strict clean on the diff."
---

**Issue 1: `_migrate_legacy_queue_to_scope()` is not atomic across the two SQLite connections.**

In `src/specify_cli/sync/queue.py`, the migration deletes legacy rows from `src` and then commits `src` before committing `dst`:

```python
src.commit()
dst.commit()
```

If `dst.commit()` fails after `src.commit()` succeeds, the legacy rows have already been deleted and committed while the scoped destination may roll back or fail to persist. That violates WP02's atomicity requirement for the legacy-to-scoped migration and can strand/drop body-upload rows under the exact retry/failure scenario this WP is meant to harden.

Fix by making the durable write to the scoped DB happen before the legacy deletion commit. A safe order is:

1. Insert rows into `dst` and delete matching rows from `src` inside their open transactions.
2. Commit `dst` first.
3. Commit `src` second.
4. If `src.commit()` fails after `dst.commit()` succeeds, leave the legacy rows in place; retry remains safe because the destination insert path uses `INSERT OR IGNORE`.

Add a regression test that simulates `dst.commit()` failure and proves legacy rows remain available for retry. The current rollback test only raises before either commit runs, so it does not cover the durability edge above.

## Resolution: PR #1107

This issue is fixed by PR #1107 (mission `mvp-cli-sync-boundary-completion-01KRX11M`).

### What changed (this issue's scope)

- Row-level legacy → scoped queue migration now covers `body_upload_queue` rows alongside `queue` (event) rows (FR-007). Previously the migration was implicit and could leave body uploads stranded in the legacy DB if the scoped DB had any unrelated row. Implementation: `_migrate_table_row_level()` in `src/specify_cli/sync/queue.py:641` operates per-table with `INSERT OR IGNORE` keyed on schema-correct dedup tuples (events: `event_id`; body uploads: composite `(project_uuid, mission_slug, artifact_path, content_hash)`).
- Re-running the migration is idempotent. Already-migrated rows are dropped silently by `INSERT OR IGNORE`; a second migration pass produces no new rows and no errors (FR-006). Tested by `test_migrate_row_level_is_idempotent_on_rerun`.
- Migration is durable across crashes between source delete and destination write. The fix in `e5e3330f` reverses commit order: destination commit (`dst.commit()`) lands before legacy source commit (`src.commit()`), so a power-cut mid-migration loses at worst the legacy delete (the data is already persisted in the scoped DB), not the data itself.
- Non-empty scoped DB is supported. The previous whole-DB emptiness guard is gone; rows merge into a scoped DB that already contains unrelated rows from another session.

### Verification

```
$ uv run --with pytest python -m pytest tests/sync/test_queue_row_level_migration.py -q
...........                                                              [100%]
11 passed in 0.43s
```

Full transcripts: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/test-transcripts/targeted.txt`.

Live boundary check on this machine showed the active scoped DB at `/Users/robert/.spec-kitty/queue.db` with `event_count=2869, body_upload_count=1282, rows_in_scope=4151`, demonstrating body-upload coverage in the post-migration accounting. Transcript: `evidence/test-transcripts/sync-status-check-coherent.txt`.

### Code references

- `src/specify_cli/sync/queue.py:494` — `_QUEUE_TABLES_FOR_MIGRATION` includes `body_upload_queue`.
- `src/specify_cli/sync/queue.py:537-558` — Per-table dedup-key tuples; `body_upload_queue` uses the composite `(project_uuid, mission_slug, artifact_path, content_hash)` documented in the schema, not a synthetic `id` that would collide on `INSERT OR IGNORE`.
- `src/specify_cli/sync/queue.py:641` — `_migrate_table_row_level()` implements `INSERT OR IGNORE` per-table merge.
- `src/specify_cli/sync/queue.py:670` — Composed `INSERT OR IGNORE INTO {table} ({insert_columns}) SELECT ...` statement (column names are schema-derived, not user input).
- `src/specify_cli/sync/queue.py:875-915` — `detect_legacy_rows_for_scope()` surfaces both event and body-upload counts so the preflight + status can report them separately.

### Implementing commits

- `5211dce7` — feat(WP02): Row-level queue migration covers body uploads + idempotent retry
- `e5e3330f` — fix(WP02): reverse commit order so destination persists before legacy delete

Closing per the mission's Definition of Done.

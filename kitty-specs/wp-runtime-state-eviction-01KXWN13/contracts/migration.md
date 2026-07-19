# Contract: migration backfill + cutover (FR-010, FR-011)

## Strict order (both clobber-windows closed)

```
backfill → verify(FAIL-CLOSED) → reader cutover → writer cutover → delete fallbacks → land hash guard
```

- **backfill**: for every WP in the live corpus, emit seed `transition` + `InnerStateChanged` events
  reconstructing frontmatter/checkbox runtime state. Seed `event_id` = deterministic namespaced ULID
  (`mission_id+wp_id+field`); idempotent (re-run seeds nothing). Subtask marks clamp `at` to the WP's
  `claimed`; the seed ULID orders **after** the `claimed` transition at that equal `at`.
- **verify (fail-closed)**: assert the reduced snapshot equals the value the OLD frontmatter/checkbox
  reader produces, by **count + value** parity. Any mismatch (or a fault-injected corrupt seed) MUST
  **abort before reader cutover**.
- **reader cutover**: readers resolve from the snapshot; the frontmatter fallback stays behind a flag.
- **writer cutover**: writers stop touching the WP file. To avoid the symmetric split-brain, the emit
  path switches **atomically with the reader per field** (or dual-writes during the window) so a fresh
  runtime write is never invisible to a snapshot-first reader.
- **delete fallbacks**: remove the FR-005 flag and the legacy `workflow_cores.py:340-348` /
  `done_bookkeeping.py:104-105` fallbacks — **only now**, because they synthesise done-evidence for
  un-migrated on-disk WPs until backfill seeds those approvals as events.

## `MUTABLE_FIELDS` extension (do not fork)

Add `shell_pid_created_at`, `review_artifact_override_*`, `reviewer_shell_pid`; move `history` out of
`STATIC_FIELDS`; retire `progress`. `history[]` and `progress` are deleted outright **after a
zero-reader verification** (no live reader anywhere, not merely no authority-read).

## Honesty bound (no-data-loss)

"No data loss" is asserted against count+value parity of the reduced snapshot, **not** temporal
fidelity: backfilled subtask-completion timestamps are clamped (fictional), and seed ULIDs are
content-namespaced (not chronological). The contract holds only because **no consumer reads
subtask-completion time or relies on seed-ULID chronological order** — asserted as a precondition.

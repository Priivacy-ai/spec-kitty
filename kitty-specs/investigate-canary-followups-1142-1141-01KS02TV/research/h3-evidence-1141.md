# #1141 Hypothesis 3 (sequencing race) — RULED OUT

**Claim**: The peek-the-queue assertion at scenario 4 line 543 races against the `move-task` write of the rollback row.

## Evidence against

The peek implementation (`_peek_latest_wp_status_changed`, scenario file lines 231–294) does not race the write because:

1. **The peek runs in a separate subprocess** via `run_spec_kitty_python`. The Python subprocess starts AFTER the `move-task` subprocess has already exited (the test code awaits the move-task `CommandResult` before invoking `_peek_latest_wp_status_changed`). There is no concurrent producer.
2. **The offline queue is SQLite-backed** with WAL semantics; by the time the move-task process exits, any rows it wrote have been flushed (Python's `sqlite3` defaults to autocommit-on-connection-close).
3. **The peek uses `drain_queue(limit=1000)`** which reads (without removing) all rows oldest-first, then filters and returns the LAST match. Even if there were a theoretical visibility race, the peek would either see the row or not — it would not see a stale `for_review → in_review` and miss a fresh `in_review → planned` selectively, because they live in the same SQLite table.

In the captured failure, the peek **did find a row** (the `for_review → in_review` one). If a race had merely delayed visibility of the rollback row, the peek would have returned the previous-latest, which is exactly what we see — but the same race would mean the rollback row arrives milliseconds later in the same DB file, in which case re-running the canary would intermittently pass. The issue body characterizes the failure as deterministic (consistent across runs), not intermittent.

## Verdict

**RULED OUT.** The peek operates on a settled SQLite WAL after a serialized subprocess exit. The failure is structural, not a race.

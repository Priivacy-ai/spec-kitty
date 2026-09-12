# WP03 gates — post-freeze addendum: the two rollback truncates close (spec-kitty #3960, DRIFT-2)

This note is a **new file**, not an edit of the frozen `WP03-gates.md` ledger
beside it: `kitty-specs/` is one of the four immutable historical-record roots
enforced by `tests/architectural/test_archive_root_byte_identical.py`, which
permits new archive files but refuses any modification of a pre-existing one.
The DRIFT-2 closure therefore lives here.

The post-merge mission review (DRIFT-2) found the two rollback truncates the
WP03 ledger recorded but did not close: the coord fallback arm's
`coordination/status_transition.py::_restore_coord_status_artifacts` and its
`cli/commands/agent/workflow.py::_restore_status_artifacts` twin both
truncated `status.events.jsonl` back to a pre-emit byte size without
verifying the tail they cut. Both migrated onto one status-owned, lock-held,
tail-verified helper — `specify_cli.status.rollback.rollback_events_log_tail`
(raw truncate primitive `store.truncate_events_log`; the helper re-acquires
the same per-mission `feature_status_lock` the pipeline uses and refuses to
cut a tail that is not exactly the rows the operation appended). Gate effect:
the `ALLOWED_OUT_OF_STORE_WRITE_SITES` entry for the coord fallback arm and
the `EXPECTED_UNRESOLVED_EVENT_NAMED_WRITE_SITES` pin for the workflow twin
are REMOVED (ledger −2, shrink-only honored); the `_LEDGERED_SHAPES`
path-open-truncate floor case is re-keyed to the transactional arm's own
`self._events_path` entry, which stays ledgered (its truncate runs inside the
transaction's own L1); the store's positive census gains the
`("Path.open", "ab")` rollback-restore shape; and the R14 lock-composition
census adds `specify_cli.status.rollback`.

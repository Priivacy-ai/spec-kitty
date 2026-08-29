# Contract: emission no-op + anti-swallow

## No-op when inactive
When `not sync_active()`, every emission entrypoint returns without side effects:
create, mark-status, move-task, issue-verdict, accept, implement, merge, doctor, dashboard, next, finalize, retrospective, init, tracker.

- **INV-1**: 0 daemon spawns, 0 events enqueued, 0 network calls, 0 `sync store is locked`/`Event routing failed` warnings across all listed surfaces. Verified by spies on the spawn + enqueue seams (NFR-001/SC-001) — not by absence of log text.

## Anti-swallow when active (#3470 / FR-008)
- **INV-2**: with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and a LEGACY layout, a genuine `_require_project_destination` violation still surfaces as an error (SC-005). The #3470 fix is a gated early-return, NOT a broad try/except.

# WP06 review cycle 2 — changes requested

## Verified

- Fresh immutable base+WP02: 12 failed/33 passed; HEAD 139 passed; exact 21-survivor run passed.
- Frozen 177→139 (`-38`), net `-1794` test LOC, no production edit.
- Ledger validator 27 dispositions/46 members/0 errors; Ruff/diff clean.
- Controlled pre-repair port-claim fault reproduced; repaired path passed.

## Final-cycle corrections

1. Four “exact survivor” mappings overclaim equivalence: FIFO queue order maps to a size-only test; alias persistence maps to returned-event-only; actor/reason persistence maps to force/lane-only; full sync lifecycle maps to a different status surface. Use actual biting survivors, strengthen an owned survivor, or classify stale/obsolete honestly.
2. Make daemon pre-repair rows replayable by binding exact source commit/tree, complete preparation command, and defined/persisted row-hash bytes. Current patch does not apply directly to cycle-2 HEAD.
3. Bind `wp06-sync-survivor-map.json` SHA-256 in results/ledger.

This is actual cycle 2. One final implementation/review decision remains; no fourth cycle.

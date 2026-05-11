# WP02: Baseline Audit Results

## Blocker Summary Table

| Repo | Total Missions | Missions w/ Blockers | Total Blockers | Shape Counters |
|------|---------------|---------------------|----------------|---------------|
| spec-kitty-saas | 48 | 33 | 1773 | ACTOR_DRIFT:138, IDENTITY_MISSING:1, LEGACY_KEY:1772, UNKNOWN_SHAPE:1899 |
| spec-kitty-events | 18 | 15 | 499 | IDENTITY_MISSING:2, LEGACY_KEY:483, SNAPSHOT_DRIFT:14, UNKNOWN_SHAPE:581 |
| spec-kitty-runtime | 4 | 4 | 174 | LEGACY_KEY:170, SNAPSHOT_DRIFT:4, UNKNOWN_SHAPE:185 |

## Repos Requiring Repair

All three repos have `missions_with_teamspace_blockers > 0`:
- **spec-kitty-saas**: 33 missions, 1773 blockers (LEGACY_KEY dominant)
- **spec-kitty-events**: 15 missions, 499 blockers (LEGACY_KEY dominant)
- **spec-kitty-runtime**: 4 missions, 174 blockers (LEGACY_KEY dominant + SNAPSHOT_DRIFT errors)

## spec-kitty-runtime Inclusion Gate

Gate criterion (from WP01 T004): include runtime if `missions_with_teamspace_blockers > 0`

Result: `missions_with_teamspace_blockers = 4` → **INCLUDE spec-kitty-runtime in WP03 repair**

This is consistent with PR #19 (side-log classification) — but runtime still has LEGACY_KEY blockers in meta.json
and status.events.jsonl that PR #19 did not address.

## Audit JSON Structure Note

The actual JSON output structure differs slightly from the contract schema:
- Contract expects: flat keys `total_missions`, `missions_with_teamspace_blockers`, etc.
- Actual output: nested under `repo_summary`; blocker codes under `shape_counters`
- All required data is present; the wrapper differs.

## Unexpected Errors

- spec-kitty-saas: IDENTITY_MISSING (1 mission with absent meta.json) — non-blocking, repair will skip
- spec-kitty-events: IDENTITY_MISSING (2 missions), SNAPSHOT_DRIFT (14 missions) — SNAPSHOT_DRIFT = error severity
- spec-kitty-runtime: SNAPSHOT_DRIFT (4 missions) — all missions have drift errors

SNAPSHOT_DRIFT means `reducer output does not match persisted status.json`. This is repairable.
No findings block repair from proceeding.

## Audit File Locations

- `spec-kitty-saas.before.audit.json` — workspace root (spec-kitty-saas: 817 KB)
- `spec-kitty-events.before.audit.json` — workspace root (spec-kitty-events: 235 KB)
- `spec-kitty-runtime.before.audit.json` — workspace root (spec-kitty-runtime: 94 KB)

# Research: Frontmatter History to Canonical JSONL

**Feature**: 035-frontmatter-history-to-canonical-jsonl
**Date**: 2026-02-09

## R1: History Format Detection

**Question**: How many history formats exist in WP frontmatter?

**Finding**: Only ONE format exists (Format A). All 203 WP files across 34 features use:

```yaml
history:
  - timestamp: '2026-02-08T14:07:18Z'
    lane: planned
    agent: system
    shell_pid: ''
    action: Prompt generated via /spec-kitty.tasks
```

**Format B** (`date`, `status`, `by`, `notes`) was hypothesized in the fancy-tumbling-rabin.md plan but does not exist anywhere in the codebase. Zero instances found.

**Decision**: Parse Format A only. No format detection logic needed.
**Rationale**: Engineering for a format that doesn't exist adds complexity with zero benefit.
**Alternatives rejected**: Multi-format parser with auto-detection (unnecessary).

## R2: Current Migration Limitations

**Question**: What does the current `migrate_feature()` miss?

**Finding**: Current code (line 180-192 of `migrate.py`) creates exactly ONE event per WP:

- `from_lane=Lane.PLANNED` (hardcoded sentinel)
- `to_lane=Lane(canonical_lane)` (current frontmatter lane)
- `force=False` (latent bug: many transitions like `planned->done` are not in `ALLOWED_TRANSITIONS`)

**What's lost**: A WP that went `planned -> doing -> for_review -> done` gets a single `planned -> done` event. The 3 intermediate transitions are discarded.

**Decision**: Replace with full reconstruction algorithm.
**Rationale**: Event log must represent actual project history, not a lossy summary.

## R3: Atomic Write Pattern

**Question**: How to write multiple events per feature atomically?

**Finding**: `store.py` provides only `append_event()` (single line, append mode). `reducer.py` demonstrates the atomic write pattern for `status.json`: write to `.tmp` file, then `os.replace()`.

**Decision**: Implement `_write_events_atomic()` in `migrate.py` using the same pattern as `materialize()`:

1. Write all events to `status.events.jsonl.tmp`
2. `os.replace()` to `status.events.jsonl`

**Rationale**: Mirrors existing pattern in the codebase. Ensures either all events or none are persisted.
**Alternatives rejected**: Using `append_event()` in a loop (not atomic across multiple events).

## R4: Idempotency Guard Design

**Question**: How to prevent duplicate events on re-run?

**Finding**: Three real scenarios exist:

1. **No events file**: Fresh migration needed
2. **Events file with only migration actors**: Legacy bootstrap that should be replaced with full history
3. **Events file with live (non-migration) actors**: Must not be touched

Current code uses a simple "non-empty file → skip" check, which conflates scenarios 2 and 3.

**Decision**: 3-layer check:

- Layer 1: Check for `historical_frontmatter_to_jsonl:v1` marker in event reasons → skip
- Layer 2: Check for any non-migration actors → skip (live data)
- Layer 3: All migration actors → backup and replace

**Rationale**: Distinguishes between "already fully migrated", "has live data", and "has only legacy bootstrap data".
**Alternatives rejected**: Per-event hash fingerprinting (over-engineered for a run-once operation); single "non-empty" check (can't upgrade legacy bootstrap data).

## R5: DoneEvidence Availability

**Question**: How many WPs have extractable review evidence?

**Finding**: Searched all 203 WP files. Many done WPs have:

- `review_status: "approved"` (or `"has_feedback"`)
- `reviewed_by: "<name>"`

These can construct `DoneEvidence(review=ReviewApproval(...))` for the `for_review -> done` transition.

WPs without these fields will use `force=true` with explicit reason noting missing evidence.

**Decision**: Extract evidence when `review_status == "approved"` AND `reviewed_by` is present.
**Rationale**: Reduces forced-without-evidence technical debt. Makes the event log more honest.

## R6: Upgrade Migration Framework Integration

**Question**: How does the upgrade wrapper integrate?

**Finding**: 39 existing migrations use `BaseMigration` with `detect()`, `can_apply()`, `apply()`. Current version is `2.0.0a1`. No existing migrations interact with the status module.

The `MigrationRegistry.register` decorator auto-registers. The runner calls `has_migration(id)` on `ProjectMetadata` to skip already-applied migrations.

**Decision**: Create `m_2_0_0_historical_status_migration.py` with:

- `migration_id = "2.0.0_historical_status_migration"`
- `detect()`: Scan for features with WPs but no events (or only migration-actor events)
- `apply()`: Call `migrate_feature()` per feature, aggregate results

**Rationale**: Follows existing patterns. Same migration_id on 0.x backport ensures cross-branch idempotency via `has_migration()`.

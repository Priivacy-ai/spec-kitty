# Quickstart: Frontmatter History to Canonical JSONL

**Feature**: 035-frontmatter-history-to-canonical-jsonl

## What This Does

Replaces the bootstrap-only `status migrate` command with full history reconstruction. Instead of creating one event per WP (`planned -> current_lane`), it reconstructs every intermediate transition from the WP's `history[]` frontmatter array.

## Key Files

| File | Role |
|------|------|
| `src/specify_cli/status/history_parser.py` | NEW: Parse history, build transition chain, extract evidence |
| `src/specify_cli/status/migrate.py` | MODIFY: Wire history_parser, add idempotency layers, atomic write |
| `src/specify_cli/upgrade/migrations/m_2_0_0_historical_status_migration.py` | NEW: Upgrade wrapper |
| `tests/specify_cli/status/test_history_parser.py` | NEW: Parser tests |
| `tests/specify_cli/status/test_migrate.py` | MODIFY: Update + expand |
| `tests/specify_cli/upgrade/test_historical_status_migration.py` | NEW: Wrapper tests |

## Implementation Order

1. `history_parser.py` + `test_history_parser.py` (parser + tests, no dependencies)
2. `migrate.py` + `test_migrate.py` (engine rewrite + test updates)
3. `m_2_0_0_historical_status_migration.py` + `test_historical_status_migration.py` (wrapper)

## Critical Design Rules

**All migration events use `force=true`** with `reason="historical migration"`. This is because:
- Historical transitions bypassed live validation
- `planned -> done` and similar jumps are not in `ALLOWED_TRANSITIONS`
- Current code's `force=False` is a latent bug

**Do NOT use `emit_status_transition()`**. Migration bypasses the emit pipeline because:
- emit validates guards (would reject historical transitions)
- emit triggers SaaS sync (unwanted during migration)
- emit materializes per-event (wasteful for N events)

Instead: build `StatusEvent` objects directly, write atomically, call `materialize()` once.

**3-layer idempotency**:
1. Marker `historical_frontmatter_to_jsonl:v1` in event reasons → skip
2. Non-migration actors in events → skip (live data)
3. Only migration actors → backup + replace with full history

## Reconstruction Algorithm (cheat sheet)

```
history: [planned, doing, for_review, done], current_lane=done
  → normalize: [planned, in_progress, for_review, done]
  → collapse dupes: [planned, in_progress, for_review, done]
  → pair: planned→in_progress, in_progress→for_review, for_review→done
  → gap-fill: none needed (last entry == current lane)
  → result: 3 events

history: [planned], current_lane=done
  → normalize: [planned]
  → pair: (none, single entry)
  → gap-fill: planned→done
  → result: 1 event

history: [], current_lane=done
  → fallback: planned→done
  → result: 1 event

history: [], current_lane=planned
  → result: 0 events
```

## Running Tests

```bash
# Parser tests only
python -m pytest tests/specify_cli/status/test_history_parser.py -v

# Migration engine tests
python -m pytest tests/specify_cli/status/test_migrate.py -v

# Upgrade wrapper tests
python -m pytest tests/specify_cli/upgrade/test_historical_status_migration.py -v

# All status tests
python -m pytest tests/specify_cli/status/ -v

# Full test suite
python -m pytest tests/ -x -q
```

## Migration ID

`2.0.0_historical_status_migration` — Same ID on both 2.x and 0.x branches for cross-branch idempotency.

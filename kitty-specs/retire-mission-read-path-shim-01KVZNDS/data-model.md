# Data Model: Retire mission_read_path Backcompat Shim

**No domain data entities.** This is a code-retirement / architectural-debt mission; it introduces
no persisted data, schemas, or value objects.

The only structured artifacts touched are architectural-gate ledgers, recorded here for precision:

## Architectural ledger entries (state being removed)

| Artifact | Key / member | Before | After |
|----------|--------------|--------|-------|
| `tests/architectural/_baselines.yaml` | `category_4_backcompat_shims` | `9` | `8` |
| `tests/architectural/test_no_dead_modules.py` → `_CATEGORY_4_BACKCOMPAT_SHIMS` | `"specify_cli.mission_read_path"` | present | removed |
| `tests/architectural/test_no_dead_symbols.py` → `_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT` | `"specify_cli.mission_read_path::resolve_mission_read_path"` | present | removed |

**Invariant (C-001)**: `_baselines.yaml.category_4_backcompat_shims` MUST equal the live size of
`_CATEGORY_4_BACKCOMPAT_SHIMS` after the edit. `test_ratchet_baselines.py` enforces this equality
and additionally forbids the value from increasing relative to the committed baseline (SHRINK
ratchet). Decrement (9→8) satisfies both.

## Symbol contract (unchanged)

| Symbol | Canonical home | Visibility | Importer after repoint |
|--------|----------------|-----------|------------------------|
| `_resolve_mission_read_path` | `specify_cli.missions._read_path_resolver` | private (not in `__all__`) | imported + aliased to `resolve_mission_read_path` in `test_coord_reader_fixes.py` |
| `StatusReadPathNotFound` | `specify_cli.missions._read_path_resolver` | public (`__all__`) | imported directly |

No symbol is added, renamed, or promoted; only the shim's redundant re-export is removed.

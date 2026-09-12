# Data Model: SymbolKey source_module (#3552)

## SymbolKey (`tests/architectural/_symbol_key.py`)

The dead-symbol identity. Frozen dataclass.

| Field | Type | Compare? | In `body_hash`? | In `key_tier`? | In `as_tuple()`? | Notes |
|-------|------|----------|-----------------|----------------|------------------|-------|
| `bare_name` | `str` | yes | yes | yes | yes | The `__all__` symbol name. |
| `body_hash` | `str` | yes | (is the hash) | — | yes | Relocation-tolerant content hash. |
| `module_path` | `str \| None` | yes | no | yes (tier discriminator) | yes (when set) | `None` = content-tier; set = collision-tier. |
| **`source_module`** (NEW) | `str \| None` | **no (`compare=False`)** | **no** | **no** | **no** | Provenance-only machine identity. Default `None`. |

**Invariants (pinned by G1–G6):**
- **I1/I2**: equality, `__hash__`, and frozenset membership ignore `source_module` → `final_key in allowlist` unaffected.
- **I3**: `body_hash` determinism — `source_module` never enters the hash.
- **I4/I8**: `key_tier`/`is_content_tier` are `module_path`-only; provenance never escalates content→collision (non-goal).
- **I7**: `as_tuple()` stays a 2-/3-tuple; `source_module` excluded.
- **I10**: allowlist set cardinality invariant under provenance (363 total) → no ratchet count moves.

**Tiers:**
- **Content-tier**: `SymbolKey(bare_name, body_hash)` — location-free (D-1 relocation-tolerance). 338 entries; all gain `source_module=`.
- **Collision-tier**: `SymbolKey(bare_name, body_hash, module_path=...)` — 25 entries; already structured.

## AllowlistEntry (`_refresh_dead_symbol_hashes.py`)

Parsed representation of one allowlist `SymbolKey(...)` call.

- `module_path` property: **before** — recovered from provenance comment when content-tier; **after** — returns `source_module` directly (comment branch retired).
- Drops the comment-recovery code path (`_recover_provenance`, `_comments_by_row`). `Outcome.UNRECOVERABLE` is **retained** as the generic fail-closed backstop (the guard against a future entry missing `source_module`); only its comment-specific docstring wording is updated.
- **Blast radius**: `tests/architectural/test_refresh_dead_symbol_hashes.py` constructs `AllowlistEntry` via a local helper (`provenance_module=`/`kwarg_module_path=`) and asserts on `Outcome.UNRECOVERABLE` — its fixtures/asserts move with this change; the two #3560 Finding-1 tests stay green.

## DeadLocation (`_refresh_dead_symbol_hashes.py`) — unchanged

Carries `module_path`, `bare_name`, `new_hash`, `requires_module_path` (from #3558). No change; `source_module` flows through the entry, not the location.

## Backfill source

`source_module` values for the 338 content-tier entries are the module names currently encoded in their `# module::Name` provenance comments (all parseable today). One-time scripted AST rewrite.

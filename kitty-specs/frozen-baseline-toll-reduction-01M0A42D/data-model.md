# Data Model: Frozen-baseline toll reduction

Test-infrastructure entities (no runtime/product data). These are the shapes the refresh helper and the derived gates operate on.

## SymbolKey (existing — the single hashing authority's output)

The identity of an allowlisted dead symbol. Two tiers (`tests/architectural/_symbol_key.py`):

| Tier | Fields | When used |
|---|---|---|
| **content** | `name` (bare), `body_hash`, `module_path = None` | default; **location-free by design** (relocation-proof, FR-007 of the original dead-symbol mission) |
| **collision** | `name` (bare), `module_path`, `body_hash` | when a `bare_name` collides across modules |

- **Invariant**: the key is produced only by `resolve_symbol_key` / `key_tier` / `classify_collisions`. The refresh helper MUST reuse these — no private hash recompute.
- **Consequence for FR-002**: across a body edit the `body_hash` changes, and content-tier keys carry no `module_path`, so re-identifying "the same symbol" needs an out-of-key discriminator (the provenance comment).

## Dead-symbol allowlist entry

A `SymbolKey` plus its provenance context, living inside `tests/architectural/test_no_dead_symbols.py` frozensets.

- **Fields**: the `SymbolKey`, and a `# <module>::<Name>` **provenance comment** (trailing or preceding — inconsistent today; the highest project risk).
- **State**: an entry is *live-refreshable* (its symbol is still dead and uniquely identifiable), *dangling* (symbol deleted/relocated/now-called — 0 candidates), or *ambiguous* (≥2 still-dead candidates for its `bare_name` — refuse).
- **Live cardinality**: 354 entries (329 content-tier, 25 collision-tier); 10 duplicate `bare_name`s (3 already collision-tier, 7 content-tier).

## Refresh candidate

A live `__all__` symbol location considered as the target of a refresh.

- **Derivation**: for allowlist entry `E`, candidates = live `__all__` locations where `location.bare_name == E.bare_name`, resolved through the authority, **filtered to still-dead**, then to `E`'s recovered `module_path` when available.
- **Selection rule (fail-closed)**: refresh iff exactly one still-dead candidate; 0 → leave dangling (red); ≥2 → refuse (ambiguous).

## Dead auto-discovered migration (FR-004 derivation domain)

- **Definition**: an `m_*.py` module under `src/specify_cli/upgrade/migrations/` with **no static `src/` importer** — the gate's own predicate in `test_no_dead_modules.py`.
- **Live**: 105 `m_*.py` files − 5 statically-imported = **100** dead. The 5 static importers are the enumerated exceptions in research.md.
- **Authority rule (post-plan correction)**: the derived `category_1` count is `len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)` (the hand-curated frozenset, already imported at `test_ratchet_baselines.py:270/:405`) — the single authority. Do **not** re-implement the `glob ∩ no-static-importer` predicate (no accessor exists; it would create a `_has_caller` split-brain) and do **not** use `len(glob("m_*.py"))` (105, over-counts by 5). The frozenset's *membership correctness* is validated by `test_no_dead_modules` (untouched); the derived count is redundant accounting.

## Baseline key (`_baselines.yaml` entry)

A named integer high-water mark read (or, post-mission, *derived*) by `test_ratchet_baselines.py`.

- **Toll keys in scope**: `skip_marker_blocks` (13 → warn-not-fail, FR-003), `category_1_auto_discovered_migrations` (100 → derived, FR-004), `test_no_dead_symbols:` block (inert → deleted, FR-005).
- **Load-bearing keys out of scope (C-001)**: `legacy_contract_allowlist=151`, `grandfathered_orphans`, `no_inert_schema_slots`, `reference_enum_ratchet`, `egress_consent_boundary`×2, `unfiltered_journal_read_boundary`, `backcompat_shims=0`, `known_ungated_files=0`.
- **Grandfather residue (FR-005)**: `_GRANDFATHERED_UNREGISTERED_KEYS = frozenset({"test_no_dead_symbols"})` in `test_ratchet_baselines.py`, plus a coupled equality literal (~`:530`) — both drained to `frozenset()` to close the re-entry hole.

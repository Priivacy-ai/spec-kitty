# Contract: Symbol-Key Resolver + Live Collision Classifier

Module: `tests/architectural/_symbol_key.py` (NEW; consumed by `test_no_dead_symbols.py`).

## `resolve_symbol_key(node, module_path, tree) -> SymbolKey | None`

Produces the relocation-tolerant key for one `__all__`-declared symbol.

- **Content tier (default)**: `(bare_name, body_hash)`, `module_path=None`.
- **body_hash**: hash of `anchoring.code_tokens_by_line` over the definition span.
  Span MUST cover: `ClassDef`, `FunctionDef`, `AsyncFunctionDef`, `Assign`,
  **`AnnAssign`** (FR-002 — the T001 gap), and `ImportFrom` **scoped to the single
  aliased name** (FR-004 — not the whole statement).
- **Facade-dict exports (FR-003 — rescoped)**: handle BOTH shapes — `sync _LAZY_IMPORTS`
  `{name:(module,attr)}` (2-tuple) and `runtime _EXPORT_MODULES` `{name:module_const}`
  (1-value; the 6 `specify_cli.runtime::*` entries the gate's `_record_facade_edges`
  skips via its `len!=2` guard). **Re-derive the dict-parse KEY-side** to yield
  `name → (module, attr)` (needed to locate the body to hash). Reuse ONLY the two PURE
  helpers `_find_facade_lazy_dict_name` + `_resolve_relative_module`; do NOT reuse/edit
  `_record_facade_edges` (byte-frozen C-005, caller-graph-shaped, discards the name).
  Enumerate by shape, not "all 8".
- **Undecidable**: return `None` for any shape the resolver cannot span. NEVER guess.

### Postconditions
- Deterministic across 3.11↔3.12 for every supported shape (DoD j proves AnnAssign +
  single-alias; the spike proved ClassDef/FunctionDef).
- Pure code motion (module move, sibling reorder, blank/comment insertion, annotation
  whitespace) → **identical** key (NFR-001).

## `classify_collisions(all_symbols) -> dict[str, list[Location]]`  (LIVE, per run — FR-005/D-2)

- Build a `bare_name → [live __all__ locations with matching body_hash]` index by ONE
  walk of the `src/` tree. Build **once per gate run**, not per entry (perf).
- A `bare_name` with ≥2 entries sharing a `body_hash` is a **collision `bare_name`**.
- Today's collision set == the ArtifactKind trio; the classifier MUST re-derive it, not
  hard-code it (a future byte-identical pair must be caught automatically).

## `key_tier(key, collision_index) -> "content" | "module_path" | FAIL`  (FR-005/FR-009/D-3)

- content key whose `bare_name` is NOT in the collision index AND resolves to exactly
  one live location → **content** (relocation-proof).
- content key whose `bare_name` IS a collision `bare_name`, OR that resolves to ≥2 live
  locations → **escalate to module_path** (if module_path disambiguates) OR **FAIL
  (fail-closed)** — never silently exempt.
- `None` key → **FAIL** (fail-closed).

## `is_dangling(entry, live_index) -> bool`  (FR-008/D-4)

- content-tier entry: `(bare_name, body_hash)` → 0 live locations → dangling.
- module_path-tier entry: `(bare_name, module_path)` → no live `__all__` decl → dangling.
- A body edit produces exactly ONE signal (offender-refresh), reconciled so it does not
  also trip the prune ratchet (no double-flag).

## Non-negotiables
- No `if key is None: <exempt>` fallback ([[no_legacy_resolver_paths]]).
- Reuse `anchoring.code_tokens_by_line`; do not fork a normalizer (S3776).
- The bite battery drives assertions through the **production `_compute_offenders`/stale
  path** (C-007), not this module's functions in isolation.
- **Perf**: the body-hash introduces a net-new `tokenize` pass (the current gate makes
  ZERO). Build the `(bare_name → [locations])` index + hashes ONCE per run over the
  cached `_walk_modules` trees (extend `_walk_modules` to retain source — it is NOT
  C-005-frozen); add a perf-budget assertion to the gate self-test so a regression shows.

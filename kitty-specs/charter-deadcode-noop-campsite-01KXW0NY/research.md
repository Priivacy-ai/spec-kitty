# Phase 0 — Research (pre-spec grounding squad)

Three read-only Explore agents grounded each scope item against the live tree at
`main@4c93a0f58` (merged #2773) before the spec was written. Findings below are the
authority for the plan; re-verify with `git grep` if the tree moves.

## §1 — `charter.generator` is dead (VERDICT: safe to delete)

- Public symbols: `CharterDraft` (dataclass), `build_charter_draft` (wraps
  `compile_charter`), `write_charter` (symlink-guarded md writer) — `generator.py:12-73`.
- **Zero live `src/` callers.** Only references: `src/charter/__init__.py:31` (import) +
  `__all__` lines 108-110, and `tests/charter/test_generator.py:10`.
- **Landmine CLEAR — no `charter.md` scaffold gap.** `charter generate`
  (`cli/commands/charter/generate.py:335-350`) builds via `compile_charter` →
  `write_compiled_charter`, which writes **`charter.yaml` only** (asserted at
  `test_generator.py:123`). `charter.md` is hand-authored post-#2773; `_sync_charter_if_present`
  skips entirely when it is absent. `charter interview` writes only `answers.yaml`. Nothing
  bootstraps an initial `charter.md` from generator.
- **Test split:** DIE with the module — `test_build_charter_draft_defaults`,
  `test_build_charter_draft_invalid_template_set_raises`, `test_write_charter_respects_force`,
  `test_write_charter_rejects_symlink_even_with_force`. SURVIVE (cover the live compiler,
  don't import generator) — the 4 `test_write_compiled_charter_*` symlink-guard tests.

## §2 — `charter.extractor` is dead (VERDICT: safe to delete; 3 allowlist edits required)

- Remaining husk: `Extractor` class + `_detect_catalog_references` + `ExtractionResult`.
  The #2773-deleted symbols (`SECTION_MAPPING`, `write_extraction_result`, `extract_with_ai`,
  `_classify_section`) are confirmed gone.
- **Zero non-test `src/` callers.** (`src/doctrine/drg/migration/extractor.py` is an unrelated
  module.) Not reexported in `src/charter/__init__.py`.
- **Three deferred allowlist entries (remove together, else gate red):**
  1. `tests/architectural/_baselines.yaml:58` — `category_5_wp_in_flight_adapters: 1` → `0`.
  2. `tests/architectural/test_no_dead_modules.py:339-344` — `"charter.extractor"` in
     `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS`. If left after deletion → `stale_allowlist_entries`
     assert fails (`test_no_dead_modules.py:596-598`).
  3. `tests/architectural/test_no_dead_symbols.py:907-913` — `Extractor` `SymbolKey` frozenset
     `_CATEGORY_C_WP_IN_FLIGHT_EXTRACTOR_RETIREMENT` + its `|` term in `_SYMBOL_ALLOWLIST`. If
     left after deletion → `dangling` assert fails (`test_no_dead_symbols.py:1753-1790`).
  Note: no symbol-baseline *number* changes (that category has no key in the baseline section).
- **Ratchet direction:** `_baselines.yaml` header — growth FAILS, shrinkage only WARNS and needs
  no workflow step; lowering `1 → 0` is a legal downward edit.
- **Extractor-importing test files:** `test_extractor.py`, `test_extractor_activations.py`,
  `test_extractor_selection.py`, `test_sync_authority_paths.py`, `test_sync_references.py`
  (line 156 already broken `Extractor(tactic_registry=...)`), plus Extractor usage in
  `test_activate_resolves_no_answers_edit.py:213` and `test_charter_context_spdd_reasons.py:459`.

## §3 — #2373 render-path bug is already fixed; residual churn is elsewhere (VERDICT: bundle deep fix)

- **`build_charter_context` no longer writes tracked doctrine.** #2773 (commit `53030b051`)
  made `sync()` inert; the only write in `context.py` is `_write_state` →
  `.kittify/charter/context-state.json` at `context.py:2896`, which is **gitignored**
  (`.gitignore:88`) — intentional untracked runtime state, not the bug.
- **Residual churn lives in the preflight auto-refresh.**
  `charter_runtime/preflight/runner.py:340` `_attempt_auto_refresh` shells out to
  `spec-kitty charter synthesize` (`:406`) when `synthesized_drg` is not fresh (`:404`).
  Freshness is computed in `charter_runtime/freshness/computer.py`. A misfire (no-op judged
  stale) → synthesize → doctrine churn. `write_pipeline.promote` already has partial no-op
  guards (`_substantively_equal`, `_VOLATILE_GRAPH_FIELDS`, #1912).
- **⚠ Masking landmine:** this checkout's local `.git/info/exclude:12` excludes
  `.kittify/doctrine/`, hiding the churn; the committed `.gitignore:96-107` *tracks* those
  artifacts via negations. Reproduce red-first in a doctrine-tracked checkout.
- **Doctrine readers require materialized artifacts:** drg loader, `charter/_drg_helpers.py`,
  `doctrine_service_factory`, preflight runner, `charter_runtime/lint/_drg.py`, freshness
  computer — many load from disk, so the fix confines regeneration to explicit write / genuine
  change, NOT on-demand-only (C-005).
- **Existing tests to extend red-first:** `tests/charter/test_context.py` (render byte-stability
  → add git-clean assertion); `tests/charter/synthesizer/test_write_pipeline.py`,
  `test_orchestrator_resynthesize.py`, `test_provenance.py` (carry #1912 no-churn assertions →
  add synthesize-twice-clean ratchet).

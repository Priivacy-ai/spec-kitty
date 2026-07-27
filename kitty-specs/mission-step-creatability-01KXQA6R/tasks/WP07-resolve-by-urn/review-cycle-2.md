---
affected_files:
- path: tests/architectural/test_no_dead_symbols.py
  line_range: 872-921
cycle_number: 2
mission_slug: mission-step-creatability-01KXQA6R
reproduction_command: uv run pytest tests/architectural/test_no_dead_symbols.py -q
reviewed_at: '2026-07-17T16:00:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP07
---

# WP07 review — cycle 2 (APPROVED)

Reviewer: reviewer-renata (claude:opus). Lane: lane-g. Focused re-review of the single cycle-1 blocker. Fix commit: `58422cbb5`.

## Verdict: APPROVED

Cycle 1 recorded every substantive criterion as PASS (two-lane preservation, by-URN==by-name equivalence, override-wins, C-002 scalar fence, C-001 fail-closed, convergence, scope) and gated approval on ONE blocker: the symbol-level dead-code gate (`test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`) went red because WP07's two new public symbols (`resolve_template_by_urn`, `TemplateURNError`) are designed-ahead-of-consumer exports with zero production importers. That blocker is now resolved via the scope-preserving allowlist route the cycle-1 review prescribed.

## Blocker resolution — verified

- **Canonical allowlist route, not suppression.** The fix adds a `_CATEGORY_C_URN_RESOLUTION_LANE` frozenset of content-hashed `SymbolKey` entries for both symbols and folds it into the aggregate `_SYMBOL_ALLOWLIST`. It is the established gate mechanism — no `pytest.mark.skip`, no `# noqa`, no gate-logic edit, no assertion relaxation.
- **Hashes are real, not guessed.** The gate recomputes each symbol's content hash and only treats an allowlist entry as matching when the hash equals the live symbol content. The gate now runs GREEN (24 passed), which proves both hashes match the actual symbol bodies.
- **Rationale + follow-up ticket present.** Each entry carries the qualified `module::Name`, the compatibility-contract rationale (C-004 / FR-010 URN lane; consumer `charter context --include template:<id>` arrives later), and the consumer-wiring tracker ref **#2761**, per the gate's FR-303 instruction.
- **Scope preserved.** `git show 58422cbb5 --stat` shows ONLY `tests/architectural/test_no_dead_symbols.py` changed (23 insertions). `resolver.py` and the two WP07 test files (`tests/runtime/test_resolve_by_urn.py`, `tests/architectural/test_urn_resolver_scalar_fence.py`) are untouched — the cycle-1-approved surfaces are frozen.
- **`__all__` intact (C-004).** Both `TemplateURNError` and `resolve_template_by_urn` remain in `resolver.py`'s `__all__`; the URN lane stays a public compatibility surface. The allowlist (not `__all__` removal) is the correct route for a designed-ahead public export.

## Gates (this cycle)

- `uv run pytest tests/architectural/test_no_dead_symbols.py -q` → **24 passed** (GREEN).
- `uv run pytest tests/runtime/test_resolve_by_urn.py tests/architectural/test_urn_resolver_scalar_fence.py -q` → **18 passed** (WP07 tests still green).
- `uv run ruff check tests/architectural/test_no_dead_symbols.py` → clean.

No changes required. WP07 moves to approved. This is the final WP — the mission is fully implemented.

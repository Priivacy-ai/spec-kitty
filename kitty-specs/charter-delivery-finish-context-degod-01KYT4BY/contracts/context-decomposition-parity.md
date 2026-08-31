# Contract: context.py decomposition parity & completion (US3 / FR-007…FR-009, NFR-001/002/005, SC-004)

## Behaviour-preserving surface
`build_charter_context`, `build_charter_context_include`, `build_charter_context_json`
produce **byte-identical** output before/after decomposition.

## Non-fakeable parity corpus (NFR-001)
The golden fixture MUST include, at minimum, one input each that traverses:
- token-budget substitution (over-budget body → fetch-stanza swap),
- catalog-miss fall-through (missing artefact → structured miss stanza),
- first-load state bookkeeping (state-file write path).
Enforcement (not just prose): the parity test **enumerates the three named cases** and independently asserts each hit its distinguishing marker (over-budget → fetch-stanza swap line present; miss → structured miss stanza present; first-load → state file written). Deleting any input reds the suite — this is what makes "0 diffs" meaningful (a no-op passes byte-parity over any corpus).

## Baseline provenance (Decision 10)
The parity-baseline-capture WP **depends on** the US1 (empty-charter) + US2 (prose) WPs being approved, and the captured golden **must include the empty-charter input** producing the generic-agent / empty-Directive-IDs output — proving the baseline was generated post-US1 (guards the US1∩US3 collision, since all WPs share one mission with no inter-workstream merge).

## Completion signal (SC-004) — WIRED, non-fakeable
A dedicated test `tests/charter/test_context_decomposition_completion.py` (owned by the last US3 WP) asserts BOTH:
1. **Primary (un-fakeable): seam-existence manifest** — each named seam module (see data-model.md) **exists** AND is imported by ≥1 non-`context` caller (imported *from the seam*, not only re-exported through `context.py`).
2. **Secondary: LOC gate** — `wc -l src/charter/context.py ≤ 600` (grounded floor ≈500–540; ≤500 is the aspirational stretch; the earlier 400 is dropped). If context.py cannot reach ≤600, that is a BLOCKER requiring explicit operator re-sign-off — NOT an implementer-side ceiling adjustment.

## Regression guards (already green on the monolith — NOT completion signals)
- `test_layer_rules.py`, `test_runtime_charter_doctrine_boundary.py` — no `specify_cli` import under `src/charter/`.
- `test_no_dead_symbols.py` — every `src/charter/` module declares `__all__`, every export called.

## Cycle dissolution (NFR-001 acyclicity)
The 4 symbols `profile_sections.py` function-locally imports from `charter.context`
(`_render_fetch_stanza`, `_budget_estimate`, `_diagnose_catalog_miss`,
`_PROFILE_INLINE_BODY_LIMIT_CHARS`) move to LEAF homes; `profile_sections.py` imports
them at top level; both `# noqa: PLC0415` are deleted; no new cycle.

## FR-009 preserved surface
Every private symbol imported from `charter.context` by tests (test-only; ~40 incl.
`_reset_agent_profile_cache` used by 4 files) stays importable via a
`# FR-009 preserved surface` re-export block in `context.py`.

## Ordering (Decision 8)
US3 parity baseline captured only after US1+US2 merge; `profile_resolution` +
`doctrine_service_builder` seams extracted LAST against the frozen US1 wrapper region.

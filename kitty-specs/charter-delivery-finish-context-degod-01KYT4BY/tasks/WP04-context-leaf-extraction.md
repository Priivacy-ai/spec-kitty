---
work_package_id: WP04
title: 'US3: context.py leaf/pure extraction + cycle dissolution + parity baseline (#2532)'
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-007
- FR-008
- FR-009
- NFR-001
planning_base_branch: feat/charter-delivery-finish-context-degod
merge_target_branch: feat/charter-delivery-finish-context-degod
branch_strategy: Planning artifacts for this mission were generated on feat/charter-delivery-finish-context-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-delivery-finish-context-degod unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
- T023
history:
- at: '2026-07-30'
  actor: planner-priti
  note: WP authored from plan IC-04 + architect-alphonso decomposition map.
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
create_intent:
- src/charter/context_renderers/catalog_diagnosis.py
- src/charter/context_renderers/artifact_bodies.py
- src/charter/charter_md_parsing.py
- src/charter/context_state.py
- tests/charter/test_context_parity.py
- tests/charter/test_context_leaf_seams.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/charter/context_renderers/catalog_diagnosis.py
- src/charter/context_renderers/token_budget.py
- src/charter/context_renderers/reference_pointers.py
- src/charter/context_renderers/profile_sections.py
- src/charter/context_renderers/artifact_bodies.py
- src/charter/charter_md_parsing.py
- src/charter/context_state.py
- tests/charter/test_context_parity.py
- tests/charter/test_context_leaf_seams.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```
Apply the resolved initialization/boundaries/directives/tactics; confirm which in one line, then proceed.

## Objective

Begin the #2532 decomposition of `src/charter/context.py` (3243 LOC): capture the **non-trivial parity baseline** (after WP01/WP02/WP03), then extract the **low-risk pure/leaf seams** and **dissolve the `profile_sections` import cycle** — with byte-identical output. This WP continues the existing `context_renderers/` package convention; it does NOT change behaviour.

Design authority: [`../data-model.md`](../data-model.md) (seam→home map), [`../research.md`](../research.md) (Decisions 7, 9, 12), [`../contracts/context-decomposition-parity.md`](../contracts/context-decomposition-parity.md).

## Critical context (verified)

- **This WP runs AFTER WP01/WP02/WP03 are approved** — so the parity baseline captures post-US1 output (Decision 10). Capture the golden FIRST (T017), before any extraction.
- `context.py` is owned by **WP06**. This WP creates NEW seam modules + consolidates a few existing ones; edits to `context.py` (removing moved code, adding imports/re-exports) are **declared coupled out-of-map edits** — record a one-line rationale. WP04→WP06 are a sequential chain (no parallel collision).
- **Cycle**: `context_renderers/profile_sections.py:160-165` function-locally imports 4 symbols from `charter.context` (`_render_fetch_stanza` — already moved by WP01 —, `_budget_estimate`, `_diagnose_catalog_miss`, `_PROFILE_INLINE_BODY_LIMIT_CHARS`). After this WP moves the remaining 3 to leaf homes, replace those with top-level imports and delete both `# noqa: PLC0415`.
- **Placement guardrail (Decision 12)**: `token_budget.py` already imports `fetch_stanza.py`. Put `_budget_estimate` + `_PROFILE_INLINE_BODY_LIMIT_CHARS` in `token_budget.py`. Do NOT put the budget gate into `fetch_stanza.py` (would form `fetch_stanza → token_budget → fetch_stanza`).
- **FR-009**: keep every private symbol tests import from `charter.context` importable — via a re-export shim in `context.py` (the shim binds the function object by reference, so caches stay single-source). The full test-import list is in the architect map ([`../notes/`] / data-model.md).

## Subtasks

### T017 — Capture the non-trivial parity baseline
Create `tests/charter/test_context_parity.py`. Build a corpus that MUST include one input each traversing: token-budget substitution (over-budget body → fetch-stanza swap), catalog-miss fall-through (missing artefact → structured miss stanza), first-load state bookkeeping (state-file write). For each of the 3 public entry points (`build_charter_context`, `_include`, `_json`), snapshot output as the golden. Add per-case assertions that each input hit its distinguishing marker, so **deleting an input reds the suite**. Include the empty-charter input (provenance proof it's post-WP02/03).

### T018 — Extract `catalog_diagnosis.py` (new leaf)
Move `_diagnose_catalog_miss` + its private helper `_available_catalog_ids` to `src/charter/context_renderers/catalog_diagnosis.py` (deps: `charter._catalog_miss` only). Declare `__all__`.

### T019 — Consolidate `token_budget.py`
Move `_budget_estimate`, `_PROFILE_INLINE_BODY_LIMIT_CHARS`, `_enforce_token_budget` into the existing `token_budget.py`. Update `__all__`. Keep the re-export shim in `context.py` for any test-imported names.

### T020 — Consolidate `reference_pointers.py` + new `charter_md_parsing.py`
Move `_load_references` into the existing `reference_pointers.py`. Create `src/charter/charter_md_parsing.py` for `_extract_policy_summary` + `_find_section_start`. Declare `__all__` on the new module.

### T021 — New `artifact_bodies.py` + `context_state.py`
Move the artifact-body formatters (the 9 `_format_inline_*`, `_format_full_artifact_payload_body`, `_format_profile_directive_code`, `_jsonable_artifact_value`) to `context_renderers/artifact_bodies.py`. Move the state cluster (`_ContextStateBundle`, `_load_state`, `_write_state`, `_mark_action_loaded`, `_prepare_context_state`) to `src/charter/context_state.py`. Declare `__all__` on each.

### T022 — Dissolve the import cycle
In `profile_sections.py`, replace the function-local `from charter.context import (…)` with top-level imports from the leaf homes (`token_budget`, `catalog_diagnosis`, `fetch_stanza`); delete both `# noqa: PLC0415`. Confirm no new cycle (leaf modules must not import `context`). Add/refresh the `context.py` FR-009 re-export block for every moved private the tests import.

### T023 — Verify
`tests/charter/test_context_leaf_seams.py` — focused unit tests for the extracted seams. Run:
```
uv run pytest tests/charter/test_context_parity.py tests/charter/test_context_leaf_seams.py tests/charter/test_context*.py -q
uv run pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py -q
uv run ruff check src/charter/ && uv run mypy src/charter/
```
Parity MUST be byte-identical.

## Branch strategy
Planning base `feat/charter-delivery-finish-context-degod`; merge target `main` (PR). Depends on WP01/WP02/WP03 — enter via `spec-kitty agent action implement WP04 --agent claude`.

## Definition of Done
- [ ] Parity baseline captured post-US1 with per-case markers (fails if an input is removed).
- [ ] `catalog_diagnosis.py`, `artifact_bodies.py`, `charter_md_parsing.py`, `context_state.py` created; `token_budget.py`/`reference_pointers.py` consolidated; each declares `__all__`.
- [ ] Cycle dissolved (both `noqa: PLC0415` gone, no new cycle).
- [ ] FR-009 re-export shim keeps all test imports working.
- [ ] Byte-parity green; layer-rule/dead-symbol green; ruff+mypy clean.

## Risks
- Capturing a stale/happy-path baseline (T017 must include the 3 behaviour-bearing cases + empty-charter input).
- Re-forming the cycle via wrong placement (Decision 12 guardrail).
- Shared-mutable-state trap on caches (they stay single-source via reference re-export; verify).

## Reviewer guidance
Confirm the baseline corpus is non-trivial and provenance-correct; confirm the cycle is gone (grep `PLC0415`); confirm no `specify_cli` import entered `src/charter/`; verify byte-parity, not just "tests pass".

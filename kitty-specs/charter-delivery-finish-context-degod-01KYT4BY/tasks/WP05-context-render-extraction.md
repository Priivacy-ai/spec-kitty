---
work_package_id: WP05
title: 'US3: context.py render-seam extraction (#2532)'
dependencies:
- WP04
requirement_refs:
- FR-008
- FR-009
planning_base_branch: feat/charter-delivery-finish-context-degod
merge_target_branch: feat/charter-delivery-finish-context-degod
branch_strategy: Planning artifacts for this mission were generated on feat/charter-delivery-finish-context-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-delivery-finish-context-degod unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
history:
- at: '2026-07-30'
  actor: planner-priti
  note: WP authored from plan IC-04/IC-05 + decomposition map (render cluster).
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
create_intent:
- src/charter/context_renderers/template_include.py
- src/charter/context_renderers/selection_block.py
- src/charter/context_renderers/activation_block.py
- src/charter/context_renderers/bootstrap_text.py
- src/charter/context_renderers/compact_governance.py
- tests/charter/test_context_render_seams.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/charter/context_renderers/template_include.py
- src/charter/context_renderers/selection_block.py
- src/charter/context_renderers/activation_block.py
- src/charter/context_renderers/bootstrap_text.py
- src/charter/context_renderers/compact_governance.py
- tests/charter/test_context_render_seams.py
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

Continue #2532: extract the **render seams** from `context.py` into new `context_renderers/` modules — byte-parity preserved. Depends on **WP04** (parity baseline + leaf cluster).

Design authority: [`../data-model.md`](../data-model.md) (seam→home map), [`../research.md`](../research.md) (Decision 7), [`../contracts/context-decomposition-parity.md`](../contracts/context-decomposition-parity.md).

## Critical context
- `context.py` is owned by **WP06**; edits here (removing moved code, adding imports/re-exports) are declared coupled out-of-map edits (sequential chain).
- Reuse the WP04 parity fixture (`tests/charter/test_context_parity.py`) as the byte-parity guard after each extraction — do not weaken it.
- Every new module declares `__all__`. Keep the FR-009 re-export shim in `context.py` current for any moved test-imported private.

## Subtasks

### T024 — `template_include.py`
Move the 6 `_render_*_include` functions + `_default_missions_root` (backs `build_charter_context_include`). Thin the `_include` orchestrator in `context.py` to delegate. `__all__`.

### T025 — `selection_block.py`
Move the 11 `_render_selected_*` functions + `_render_selection_block` + the `_SELECTED_*_HEADER` constants + `_provenance_suffix` + `_extend_named_artifact_lines` + the org-source-map helpers (`_collect_org_source_map`, `_build_action_org_source_map`). Large but render-pure. `__all__`.

### T026 — `activation_block.py`
Move `_load_governance_activations`, `_read_org_activations`, `_union_activations`, `_render_activation_block`. `__all__`.

### T027 — `bootstrap_text.py` + `compact_governance.py`
Move the bootstrap-assembly cluster (`_render_bootstrap_text`, `_render_action_doctrine_lines`, `_ActionRenderRow`/`_ACTION_RENDER_ROWS`, headers/constants) to `bootstrap_text.py`; move the compact-governance render cluster (`_render_compact_governance`, `_compact_section_block`, `_render_compact_from_bundle`) to `compact_governance.py`. `__all__` on each. (Note: `compact_governance.py` is the NEW render seam; the existing `compact.py` — touched by WP03 — is a different file, do not conflate.)

### T028 — Shim + parity + seam tests
Refresh the `context.py` FR-009 re-export block for moved privates. Add `tests/charter/test_context_render_seams.py` (focused unit tests). Run:
```
uv run pytest tests/charter/test_context_parity.py tests/charter/test_context_render_seams.py tests/charter/test_context*.py -q
uv run ruff check src/charter/context_renderers/ && uv run mypy src/charter/
```
Byte-parity MUST hold.

## Branch strategy
Planning base `feat/charter-delivery-finish-context-degod`; merge target `main` (PR). Depends on WP04 — enter via `spec-kitty agent action implement WP05 --agent claude`.

## Definition of Done
- [ ] 5 render seams extracted; each declares `__all__`.
- [ ] `_include` orchestrator thinned to delegation.
- [ ] FR-009 shim current; all test imports resolve.
- [ ] Byte-parity green; ruff+mypy clean.

## Risks
- Subtle output drift when moving large render functions (rely on the parity fixture per extraction).
- Confusing the new `compact_governance.py` seam with the existing `compact.py` (WP03).

## Reviewer guidance
Confirm byte-parity after each extraction; verify no behaviour change; confirm no `specify_cli` import under `src/charter/`; check `__all__` on every new module.

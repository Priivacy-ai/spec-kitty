---
work_package_id: WP04
title: Global Selection Rendering (5 new render helpers + provenance)
dependencies:
- WP02
requirement_refs:
- FR-005
- NFR-001
- NFR-002
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T023
agent: claude
agent_profile: python-pedro
authoritative_surface: src/charter/context.py
execution_mode: code_change
owned_files:
- src/charter/context.py
- tests/charter/test_context_selection_render.py
role: implementer
history: []
tags: []
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Extend `build_charter_context` in `src/charter/context.py` to render every globally-selected artifact across all 5 new kinds. Each render emits the artifact ID plus body inline by default, or ID + fetch + when-doing stanza when token-budget overflow triggers. Org-distributed artifacts additionally carry provenance metadata so the operator can audit which pack contributed which rule.

After this WP, Case 1 (project-layer styleguide) and Case 2 (org-pack styleguide) "always-on" global activation both work end-to-end.

---

## Context

Today `src/charter/context.py` has two renderers (`_render_profile_directives`, `_render_profile_tactics`, lines 941 and 1000) called from `build_charter_context` at lines 1083–1084. The pattern is established; this WP extends it to 5 new kinds.

The fetch-stanza helper (`charter.context_renderers.fetch_stanza.fetch_stanza_lines`) handles token-budget overflow. New renderers reuse it.

See:
- [plan.md §2.4](../plan.md)
- [contracts/selection-schema.md](../contracts/selection-schema.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP04 --agent claude`

---

## Subtasks

### T017 — Add `_render_selected_styleguides`

**File**: `src/charter/context.py`

Helper signature mirrors `_render_profile_directives`:

```python
def _render_selected_styleguides(
    selected_ids: list[str],
    service: DoctrineService,
    *,
    budget_remaining: int,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected styleguides into prompt lines.

    Returns inline body lines when budget allows; fetch + when-doing stanzas
    when overflow triggers. ``org_source_map`` maps artifact_id → pack name
    for provenance bookkeeping (e.g. ``{"caveman-comments": "very-serious-developers"}``).
    """
    ...
```

Body emits a `Selected styleguides:` header followed by per-artifact ID + body or fetch stanza. Provenance is appended as `(source: org, pack: <name>)` after each org-sourced artifact ID.

### T018 — Add the 4 remaining `_render_selected_<kind>` helpers

Identical shape to T017 for the 4 remaining kinds:

- `_render_selected_toolguides`
- `_render_selected_procedures`
- `_render_selected_agent_profiles`
- `_render_selected_mission_step_contracts`

Each reads from the matching `DoctrineService` repository (`service.toolguides.get(id)`, etc.) and renders the artifact body or fetch stanza.

### T019 — Wire into `build_charter_context`

Add 5 lines after the existing tactic line (`tactic_lines = _render_profile_tactics(...)` at line ~1084) calling each new renderer with the matching `DoctrineSelectionConfig.selected_<kind>` list. Concatenate output into the assembled context text.

### T020 — Provenance metadata

Before calling the new renderers, build `org_source_map` from the `DoctrineService.styleguides.all()` (etc.) iteration, tagging each artifact's source layer. Pass the map to each renderer. Org-sourced artifacts get the `(source: org, pack: <name>)` suffix; project / built-in are unannotated (matches today's convention).

This satisfies `test_case_2_org_pack_styleguide_appears_in_consumer_prompt`'s `has_org_provenance` assertion.

### T021 — Unit tests

**File**: `tests/charter/test_context_selection_render.py`

Coverage:

- One-artifact-per-kind fixture: each kind renders its artifact ID + body when budget allows.
- Token-budget overflow fixture: large body triggers fetch + when-doing stanza substitution.
- Org-provenance fixture: a styleguide loaded via the org layer carries `source: org` / pack name in the rendered output.
- Empty selection: no output line emitted (no leading header, no trailing artifact section).
- Latency: per-render call stays under the existing budget (per `test_wp_prompt_build_latency.py`).

---

## Definition of Done

- ✅ `tests/integration/test_user_doctrine_artifact_lifecycle.py::test_case_1_project_styleguide_appears_in_implement_prompt` turns GREEN
- ✅ `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_org_pack_styleguide_appears_in_consumer_prompt` turns GREEN (provenance branch covered here; pre-fill union by WP06)
- ✅ `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 stays green
- ✅ `tests/architectural/test_wp_prompt_build_latency.py` — 2/2 stays green
- ✅ New unit tests cover all 5 kinds + provenance + overflow

---

## Risks

| Risk | Mitigation |
|------|------------|
| Token budget overflow when many selections active (NFR-001) | Reuse `fetch_stanza_lines` helper; budget participates uniformly across kinds. |
| Latency regression (NFR-002) | Each renderer is one repository walk + per-artifact render; no N+1 calls. `test_wp_prompt_build_latency.py` is the gate. |
| Provenance source map computed N times per build | Compute once at `build_charter_context` start; pass into all 5 renderers. |
| Charter renders ID-only artifacts twice (once via directives wrapper, once via direct selection) | Track rendered-IDs set; deduplicate. Edge case — test with directive+styleguide pointing to the same wrapper. |

---

## Reviewer Guidance

- Verify each new renderer signature mirrors the existing `_render_profile_directives` shape.
- Verify provenance suffix is emitted only for org-sourced artifacts (not built-in, not project).
- Verify the empty-selection case doesn't emit a stray header.
- Run latency test to confirm no regression.

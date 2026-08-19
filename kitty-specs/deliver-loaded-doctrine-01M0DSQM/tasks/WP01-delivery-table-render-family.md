---
work_package_id: WP01
title: Delivery-table & render family (glossary slot, stated-reason class, step description)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-011
- NFR-001
- NFR-003
planning_base_branch: m4-doctrine-delivery
merge_target_branch: m4-doctrine-delivery
branch_strategy: Planning artifacts for this mission were generated on m4-doctrine-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into m4-doctrine-delivery unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-deliver-loaded-doctrine-01M0DSQM
base_commit: 7fdec0995d96d8974343f64331a13be6b7d3647b
created_at: '2026-08-19T20:21:48.905959+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- Created by /spec-kitty.tasks (M4 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
create_intent:
- tests/charter/test_glossary_delivery_render.py
- tests/charter/test_step_description_render.py
execution_mode: code_change
owned_files:
- src/charter/context_renderers/delivery_table.py
- src/charter/context_renderers/bootstrap_text.py
- src/charter/context_renderers/artifact_bodies.py
- src/charter/context_renderers/profile_sections.py
- src/charter/action_doctrine_bundle.py
- tests/charter/test_action_bundle_delivery.py
- tests/charter/test_glossary_delivery_render.py
- tests/charter/test_step_description_render.py
- tests/doctrine/drg/test_kind_mapping_totality.py
- tests/doctrine/drg/test_unknown_kind_fails_loudly.py
role: implementer
tags: []
tracker_refs:
- '3489'
- '3488'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Close the **action-doctrine bundle** delivery/render no-ops so authored doctrine reaches the agent, and close the missing-reason class on the delivery table.

- **SC (FR-001/FR-002)**: an activated, graph-reachable glossary pack is delivered — its term **surfaces** (names) render under the action doctrine as a surface list plus a `--include glossary-pack:<id>` fetch pointer. No full term **definitions** are inlined (NFR-001).
- **SC (FR-003/NFR-003)**: after this WP, **every** `slot=None` row in `_ACTION_BUNDLE_DELIVERY_BY_KIND` carries a stated reason — glossary resolves to a slot; `ANTI_PATTERN` (glossary's twin) gains its reason. Zero unexplained `None` rows.
- **SC (FR-004)**: a procedure/tactic step with a non-empty `description` renders that description alongside its `title` in both the action-doctrine bundle body and the profile-channel inline body. Byte-identical when `description` is absent.
- **SC (FR-005)**: the styleguide/toolguide profile-channel pointer-only choice is documented as intentional (stated reason on the renderer + a schema/doc note); no runtime/behaviour change.
- **SC (FR-011)**: an **org-authored** glossary pack (M2 bridge landed) reaches the agent through the same path as a built-in pack.

## Context & Constraints

Read `kitty-specs/deliver-loaded-doctrine-01M0DSQM/{spec.md,plan.md,research.md,data-model.md}` and `contracts/delivery-and-render-contract.md`.

Current state (verified against `upstream/main`):
- `context_renderers/delivery_table.py::_ACTION_BUNDLE_DELIVERY_BY_KIND` — `GLOSSARY_PACK` (L113) and `ANTI_PATTERN` (L114) are the **only two** `_KindDelivery(None, …)` rows lacking a trailing stated-reason comment; every other `None` row has one. `_empty_slot_map()` derives its accumulator from the table, so a kind flipped into a slot grows an accumulator automatically.
- `action_doctrine_bundle.py::_ActionDoctrineBundle` carries `directive_ids … procedure_ids, asset_ids, service`; `_load_action_doctrine_bundle` builds them from `ids_by_slot = _classify_artifact_urns(...)` via `ids_by_slot.get("<slot>", ())`.
- `context_renderers/bootstrap_text.py::_ACTION_RENDER_ROWS` drives the render (`_render_action_doctrine_lines`), one `_ActionRenderRow(heading, ids_attr, service_attr, title_attr, summary_attr, progressive_kind)` per delivered kind; `_extend_named_artifact_lines` (in `selection_block.py`) renders via `title_attr`/`summary_attr` and **cannot** express a term-list.
- `context_renderers/artifact_bodies.py::_format_inline_procedure_body` (L~213) and `_format_inline_tactic_body` (L~173) render steps with `step_title = getattr(step, "title", str(step))` — `description` never read.
- `context_renderers/profile_sections.py::format_inline_named_body` (L~143) uses `getattr(step, "title", None) or getattr(step, "description", None) or str(step)` — `title` is required so `description` is unreachable.
- `ProcedureStep`/`TacticStep`: `title: str` (required), `description: str | None = None`.
- `GlossaryPack(id, provenance, terms: list[GlossaryTerm], description)`, `GlossaryTerm.surface`/`.definition`; `service.glossary_packs` repo exists.
- `render_profile_styleguides`/`render_profile_toolguides` pass `body_fn=None` (pointer-only, deliberate NFR-001).

**Constraints**: glossary render is **names-only** + pointer (NFR-001). `charter` must not import `specify_cli` (C-001). Zero `ruff`/`mypy --strict` suppressions (C-002). Red-first (C-003). No cascade/edge change, no golden-count ripple (C-004). No profile-channel glossary renderer (C-007).

## Branch Strategy

Planning base **`m4-doctrine-delivery`**; final merge target **`m4-doctrine-delivery`** (single_branch topology). Execution worktrees are allocated per computed lane from `lanes.json`; do not hand-create branches. One PR to `main` lands the whole mission later.

## Subtasks & Detailed Guidance

### Subtask T001 – Red: glossary delivers to a slot + no unexplained None rows
Extend `tests/charter/test_action_bundle_delivery.py` (and/or `tests/doctrine/drg/test_kind_mapping_totality.py`): assert `action_bundle_bucket(NodeKind.GLOSSARY_PACK) == "glossary_packs"`, and assert that **for every** `NodeKind` whose delivery row has `slot is None`, a stated reason is recorded. Encode the "stated reason" check the way the module already models it — if reasons are inline comments only, add an explicit `_DELIVERY_REASON_BY_KIND` (or equivalent) so the reason is machine-checkable, and assert its keys cover every `None`-slot kind. This must **fail** on `upstream/main` (glossary has no slot; anti_pattern/glossary have no recorded reason). Prove red on the merge-base first.

### Subtask T002 – Glossary slot + close the stated-reason class
In `delivery_table.py`: change `GLOSSARY_PACK` to `_KindDelivery("glossary_packs", _Gate.ACTIVATED)`. Add the stated reason for `ANTI_PATTERN`'s `None` row (e.g. validation-tier topology only, never a bundle artefact — mirror the existing reason-comment style, and populate the machine-checkable reason map from T001). Confirm `_empty_slot_map()` now yields a `"glossary_packs"` accumulator automatically. Keep the table total over `NodeKind`.

### Subtask T003 – Bundle field `glossary_pack_ids`
In `action_doctrine_bundle.py`: add `glossary_pack_ids: list[str]` to `_ActionDoctrineBundle` and populate it in `_load_action_doctrine_bundle` from `ids_by_slot.get("glossary_packs", ())` (mirror `procedure_ids`/`asset_ids`). Keep field ordering/defaults consistent with the dataclass.

### Subtask T004 – Glossary render row/helper (names-only + pointer)
The generic `_ActionRenderRow` cannot express a term-list, so add a dedicated glossary render path in `bootstrap_text.py`. Add `_format_inline_glossary_body(pack) -> list[str]` in `artifact_bodies.py` emitting the pack id/heading + `Terms: <surface1>, <surface2>, …` (from `[t.surface for t in pack.terms]`, names only — **never** `t.definition`) + a `--include glossary-pack:<id>` fetch stanza (reuse `render_fetch_stanza`). Wire `_render_action_doctrine_lines` to emit the glossary block after the existing rows, resolving packs from `service.glossary_packs`. Add render coverage in `tests/charter/test_glossary_delivery_render.py`: a pack with 3 terms renders 3 surfaces + a pointer and **no** definition text; assert an org-sourced pack renders identically (FR-011). This is the red-first render test (assert absent pre-fix).

### Subtask T005 – Red: step description undeliverable
Write `tests/charter/test_step_description_render.py`: build a `ProcedureStep(title="do X", description="the long how")` (and a `TacticStep` equivalent); render through the action-doctrine bundle body (`_format_inline_procedure_body`/`_format_inline_tactic_body`) and the profile inline body (`format_inline_named_body`); assert the `description` text appears. **Fails** on `upstream/main` (title-only). Prove red first.

### Subtask T006 – Render step description
In `artifact_bodies.py` (`_format_inline_procedure_body`, `_format_inline_tactic_body`) and `profile_sections.py` (`format_inline_named_body`): when a step's `description` is a non-empty string, emit it as an additional indented sub-line under the step title (e.g. `        <description>`), preserving the existing `title` line. When `description` is empty/whitespace/absent, output is byte-identical to today. Make T005 pass. Add a byte-identical-when-absent assertion.

### Subtask T007 – Document styleguide/toolguide pointer-only
Keep `render_profile_styleguides`/`render_profile_toolguides` `body_fn=None`. Replace the incidental "bodies vary and are pulled on demand" note with an explicit, stated reason (a named constant or a precise docstring line) that this is a deliberate NFR-001 token-budget choice — pointer-only by design, not a silent no-op. Add a short note to the profile-channel schema/doc surface (the docstring at the top of `profile_sections.py` is acceptable) so it is discoverable. No runtime/behaviour change. Record subtasks: `spec-kitty agent tasks mark-status T001 T002 T003 T004 T005 T006 T007 --status done --mission deliver-loaded-doctrine-01M0DSQM`.

## Test Strategy
Red-first (T001, T004, T005 fail on base). Run targeted:
`PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/charter/test_action_bundle_delivery.py tests/charter/test_glossary_delivery_render.py tests/charter/test_step_description_render.py tests/doctrine/drg/test_kind_mapping_totality.py tests/doctrine/drg/test_unknown_kind_fails_loudly.py -q`.
Then: `ruff check src/charter/context_renderers src/charter/action_doctrine_bundle.py` and `mypy --strict src/charter`.

## Risks & Mitigations
- **Totality tests redden until slot + render row land together** → land T002 (slot) and T004 (render) in the same change; that redness is the guard working.
- **Glossary render blowing NFR-001** → surfaces only, never definitions; assert no definition text in T004.
- **Reason "check" being vacuous** → make the stated reason machine-checkable (T001) so a future `None` row without a reason reddens.
- **`ARG`/unused-arg or `type: ignore` temptation** → prefer real fixes / precise naming over suppressions (C-002).

## Review Guidance
Verify: `charter` does not import `specify_cli`; glossary renders names-only + pointer (no definitions); every `None` delivery row has a machine-checkable stated reason; step `description` renders in all three render fns and is byte-identical when absent; styleguide/toolguide stay pointer-only with a documented reason; zero new suppressions; `mypy --strict` clean.

## Activity Log
- (implementer appends entries here)

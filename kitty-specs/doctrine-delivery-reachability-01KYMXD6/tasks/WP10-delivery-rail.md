---
work_package_id: WP10
title: The delivery rail carries every kind
dependencies:
- WP07
- WP08
requirement_refs:
- C-006
- C-008
- FR-009
- FR-011
- NFR-002
- NFR-005
- NFR-006
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T053
- T054
- T055
- T056
- T057
- T058
phase: Phase 4 - Delivery
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/context.py
create_intent:
- tests/charter/test_action_bundle_delivery.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/context.py
- src/charter/resolver.py
- tests/charter/test_action_bundle_delivery.py
- tests/charter/test_context.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP10 — The delivery rail carries every kind

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`**. **Do not read the raw `*.agent.yaml`**.

---

## Objective

Everything the bundle resolves reaches the **rendered output**, with the delivery gate expressed as a
**total function over kinds** rather than an enumerated exception.

## Context — the shape traps

- **Do not create a sixth per-kind projection.** `_classify_artifact_urns` (`context.py:729`) already
  builds `dict[str, list[str]]` and **destroys it** at the return boundary (`:748`) into a positional
  4-tuple. There are already five parallel per-kind projections in this path with five different
  subsets, and every subset difference is a live delivery defect. **Return the mapping** —
  `ids_by_slot: Mapping[str, tuple[str, ...]]` with the slot set derived from
  `_ACTION_BUNDLE_SLOT_BY_KIND` — so totality and delivery become one statement.
- **The gate must be total.** `activated(asset)` is `∅` by construction (assets are not activatable),
  so an equality stated as `activated ∩ reachable` makes `asset_ids = []` the conforming
  implementation forever. Express `gate(kind)` as a column of the NodeKind-keyed table:
  `activated(kind)` for activatable kinds, `ALL` for delivered-but-ungated kinds (assets). `TEMPLATE`
  then gets a stated reason instead of being ASSET's untreated twin.
- **The slot table is already total and guarded.** The work is flipping `PROCEDURE` and `ASSET` from
  `None` to real slots — **and this reverses PR #3007 WP03's recorded verdict** ("state them, not
  render them"). Record the reversal and the criterion, or the next mission flips two more by the same
  unstated reasoning.
- **Fixing `resolver.py`'s four `[]` literals changes nothing observable on its own** — `_render_text`
  never reads those fields. The styleguide/toolguide render drop is one layer lower (that is WP11's
  render work). Here, ensure the bundle **resolves** every kind and `GovernanceResolution` is populated
  from the canonical `PackContext` path (not a fifth reader).

Read [`contracts/activation-delivery.md`](../contracts/activation-delivery.md) §2 (B-1 to B-5).

## Subtasks

### T053 — Return the per-kind mapping
1. Change `_classify_artifact_urns` to return `Mapping[str, tuple[str, ...]]` keyed by slot, derived
   from `_ACTION_BUNDLE_SLOT_BY_KIND.values()`.
2. Update the single call site and the render concatenation to iterate the mapping.

### T054 — Add `procedure_ids` and `asset_ids`
1. Add both fields to `_ActionDoctrineBundle` (keep the existing `mission` and `service` fields — the
   contract sketch omits them; do not).
2. 13 of 18 activated procedures are already graph-reachable (WP08 measures which) — adding the slot
   delivers them immediately.

### T055 — Express the delivery gate as a total function
1. `gate(kind)` is a column of the NodeKind table: `activated(kind)` for activatable, `ALL` for
   assets. `delivered(kind) = gate(kind) ∩ channel_reachable`.
2. Assert for a named (action, mission_type) that the delivered set equals the gate intersection,
   non-empty for at least directives, tactics, styleguides, toolguides, procedures on
   `software-dev`/`implement`.

### T056 — Flip the PROCEDURE and ASSET slot verdicts; record the reversal
1. `_ACTION_BUNDLE_SLOT_BY_KIND`: `PROCEDURE` and `ASSET` map to real slots.
2. Every other kind keeps a **stated** verdict (not a bare `None`).
3. Record the reversal of WP03's verdict from `doctrine-silence-guards`, with the criterion that
   distinguishes the flipped kinds from the still-excluded ones.

### T057 — Renderer emits every resolved kind
1. Ensure the render path emits every kind the bundle now resolves (procedures, assets). The
   styleguide/toolguide render drop lives in `_render_bootstrap_text` — coordinate the boundary with
   WP11, which owns the render/every-load work. Here: the **bundle** carries them; WP11 makes the
   **render** show them.

### T058 — `GovernanceResolution` from the canonical path only
1. If you populate `GovernanceResolution`'s previously-empty lists, populate them **from**
   `PackContext` / `resolve_config_activated_roots` — not by reading a store directly. A second reader
   is a defect (V-4). Add its asset field so it is not one kind narrower than the bundle.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP07 (single activation
authority) and WP08 (the reachability measure the gate intersects with). `spec-kitty implement WP10`
resolves the workspace.

**File-ownership note**: `src/charter/context.py` is shared with WP11, WP12, WP13. You own the
bundle/classification/gate; WP11 owns render + every-load; WP12 owns the profile render; WP13 owns the
reference block. Under the no-net-growth constraint, extract helpers rather than growing the module.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/charter/test_action_bundle_delivery.py tests/charter/test_context.py tests/charter/test_compact.py -q
```

## Definition of Done

- [ ] `_classify_artifact_urns` returns a mapping; **no sixth positional per-kind projection is created**
- [ ] The bundle carries `procedure_ids` and `asset_ids` (and keeps `mission`/`service`)
- [ ] `gate(kind)` is total; `asset_ids = []` is NOT the conforming outcome
- [ ] The delivered set equals `gate ∩ reachable`, non-empty for ≥5 kinds on software-dev/implement
- [ ] Every slot-table verdict is stated; the PROCEDURE/ASSET reversal is recorded with its criterion
- [ ] `GovernanceResolution` is populated from the canonical path, with an asset field
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean; `context.py` did not grow net

## Risks

| Risk | Mitigation |
|---|---|
| Sixth per-kind projection | Return the mapping (T053) |
| `asset_ids = []` conforms | Total gate function (T055) |
| Unrecorded verdict reversal | T056 records it with a criterion |
| Fifth activation reader | Populate from `PackContext` only (T058) |

## Reviewer guidance

1. Count per-kind projections in the delivery path before and after — it must not increase.
2. Confirm assets are delivered when reachable, not gated to empty.
3. Confirm the slot-table reversal carries a written criterion.
4. Confirm no new store-read for `GovernanceResolution`.

---
work_package_id: WP03
title: Relocate three-layer DRG merge into doctrine
dependencies:
- WP02
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts were generated on mission/org-doctrine-profile-integrity-activation-closure. During implement this WP runs in its computed lane; completed changes merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/merge.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/doctrine/drg/merge.py
- src/charter/drg.py
- tests/doctrine/test_drg_merge.py
role: implementer
tags: []
---

# WP03 — Relocate three-layer DRG merge into doctrine

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Realize OQ-2(ii) / C-009: **doctrine owns the canonical relationship merge**. Move `merge_three_layers` (and its helpers) from `charter/drg.py` into a new `doctrine/drg/merge.py`, taking built-in graph + org/project fragments as **data** (no `specify_cli`/`charter` imports). Reduce `charter/drg.py` to a thin caller that adds activation-aware filtering/aggregation. Fix the org-fragment **silent-drop** of unknown relations so lineage edges from org/project fragments validate identically to shipped (FR-003). Use the strangler-fig approach (`refactoring-strangler-fig`): protect behavior with tests, build the new path, reroute, delete the old.

## Context

- Spec: FR-003; research R-011-A (org-fragment `_bridge_org_edge_to_drg_edge` silently drops unknown relations at ~`charter/drg.py:432-439`; project-fragment path rejects loudly via Pydantic — normalize the asymmetry).
- Data model: §2 (canonical merge relocated). Contract: [../contracts/wave0-foundation.md](../contracts/wave0-foundation.md) C0.3, C0.4.
- Charter rule: `doctrine` must not import `charter`/`specify_cli` (`tests/architectural/test_layer_rules.py:151`).

### Code map

- `src/charter/drg.py` — `merge_three_layers` (~:457-546), `_merge_org_fragment`, `_warn_project_override`, `_bridge_org_edge_to_drg_edge` (~:409-460, the silent-drop), `filter_graph_by_activation` (~:715), `_node_is_activated` (~:653). `_RELATION_ALIASES` (~:409).
- `src/doctrine/drg/` — `models.py` (post-WP02 has `SPECIALIZES_FROM`, `edges_to`), `loader.py`, `org_pack_loader.py`, `query.py`.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`.
- Depends on WP02 (the enum member must exist before the bridge can accept `specializes_from`). Runs in the lane after WP02.

## Subtasks

### T009 — Create `doctrine/drg/merge.py` with relocated merge

**Purpose**: Make the merged DRG a doctrine-layer artifact.

**Steps**:
1. Create `src/doctrine/drg/merge.py`. Move `merge_three_layers` and its pure helpers here, signature taking data: `merge_three_layers(built_in: DRGGraph, org_fragments: list[<fragment>], project_fragments: list[<fragment>]) -> DRGGraph`.
2. Move the org-fragment→`DRGEdge` bridging (`_bridge_org_edge_to_drg_edge`, `_RELATION_ALIASES`) into doctrine (it is pure graph logic). Ensure it imports only `doctrine`+`kernel`.
3. Keep `__all__` accurate.

**Files**: `src/doctrine/drg/merge.py` (new).

**Validation**: - [ ] `merge.py` imports nothing from `charter`/`specify_cli`; - [ ] `mypy` clean.

### T010 — Reduce `charter/drg.py` to caller + fix silent-drop

**Steps**:
1. Replace the in-`charter` merge body with a call into `doctrine.drg.merge.merge_three_layers`. Keep `filter_graph_by_activation`/`_node_is_activated` (activation-aware aggregation) in `charter` — those are charter concerns.
2. Fix FR-003: in the relocated bridge, a relation string not in the enum/aliases must **raise a structured error** (naming the offending relation + fragment) instead of returning `None` and dropping the edge. A valid `specializes_from` now resolves (WP02 added it).
3. Remove now-dead merge code from `charter/drg.py`.

**Files**: `src/charter/drg.py`.

**Validation**: - [ ] `charter/drg.py` no longer defines the merge; - [ ] unknown relation raises; - [ ] `specializes_from` org-fragment edge resolves.

### T011 — Behavior-preservation + layer-rule tests

**Steps**:
1. In `tests/doctrine/test_drg_merge.py`, capture a representative built-in + org + project fragment input and assert the merged node/edge set matches the pre-relocation output (golden snapshot or recomputation). Reuse/port the existing `test_org_overrides_shipped_field_merge` expectations.
2. Add a test that an org-fragment `specializes_from` edge appears in the merged graph (FR-003) and that an unknown relation raises.
3. Run `tests/architectural/test_layer_rules.py` and confirm green (do not edit it unless the relocation requires an allowed-import update; if so, note precisely why).

**Validation**: - [ ] merged graph identical to baseline; - [ ] layer-rule suite green.

### T012 — Normalize org-vs-project fragment handling parity

**Steps**: Ensure shipped, org, and project fragments all route a valid lineage/augmentation edge into the merged graph identically, and all reject an unknown relation identically (no silent path on any tier). Add a parametrized test across the three sources.

**Validation**: - [ ] parametrized test passes for shipped/org/project.

## Definition of Done

- [ ] Merge owned by `doctrine.drg.merge`; `charter/drg.py` is a thin caller + activation filter.
- [ ] FR-003 silent-drop fixed; three-source parity tested.
- [ ] `test_layer_rules.py` + `test_drg_merge.py` + CC-2 gates green; merged-graph behavior preserved.

## Risks

- **Highest-risk structural change.** Use strangler-fig: land the new module + reroute + delete old in one reviewable diff; rely on the behavior-preservation snapshot.
- Watch for `charter`-only helpers accidentally pulled into `doctrine` (would need a `charter` import — forbidden). Keep activation filtering in `charter`.
- Other consumers import `merge_three_layers` from `charter.drg` — grep and update import sites (those that are read-only callers may need a re-export shim in `charter.drg`; prefer updating call sites, but if a shim is needed keep it thin and documented).

## Reviewer Guidance (reviewer-renata)

- Verify `doctrine/drg/merge.py` has zero `charter`/`specify_cli` imports.
- Verify the behavior-preservation test is a real equality check, not a smoke test.
- Confirm FR-003 raises (not warns/drops) on unknown relations across all three tiers.

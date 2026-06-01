---
work_package_id: WP04
title: Augmentation auto-emit single-source + parity
dependencies:
- WP01
- WP02
requirement_refs:
- FR-028
- FR-029
- FR-030
- FR-031
- FR-032
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/org_pack_loader.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/doctrine/drg/org_pack_loader.py
- src/specify_cli/doctrine/pack_validator.py
- tests/doctrine/test_org_pack_augmentation.py
role: implementer
tags: []
---

# WP04 — Augmentation auto-emit single-source + parity

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Make augmentation/lineage edges flow from **DRG fragments** (not artifact fields), complete coverage across all 9 kinds, derive the augmentation kind set from a single source, achieve validator parity for the newly-covered kinds, resolve the mission-type asymmetry, and define topology field-merge semantics (FR-028..FR-032). This is the engine WP06 (field removal) and WP07 (data migration) build on.

## Context

- Spec: FR-028..FR-032; research R-010 (5 kinds had fields, 4 didn't; mission-type NOT in the 8-kind org-pack DRG universe), R-012 (DRG canonical), R-011-A (hardcoded `("enhances","overrides")` tuple; two hand-synced augmentation tables).
- Data model: §3. Contract: [../contracts/wave2-authoring-migration.md](../contracts/wave2-authoring-migration.md) C2.4, C2.5.

### Code map

- `src/doctrine/drg/org_pack_loader.py:89` `_AUGMENTATION_PLURAL_TO_KIND` (5 kinds), `_collect_augmentation_edges` (~:333-379, hardcoded field tuple), `_ORG_DRG_CANONICAL_KINDS` (~:102, the 8-kind universe; **no mission_type**), `_ORG_DRG_KIND_ALIASES`.
- `src/specify_cli/doctrine/pack_validator.py:65` `_AUGMENTATION_PLURAL_KINDS` ("kept in sync with" the loader — collapse to one source), intent-aware checks (~:14-99: `same_id_collision`, `unknown_target`, `intent_conflict`).

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP01 (kind resolver) + WP02 (relation enum).

## Subtasks

### T013 — Single-source augmentation kind set

**Steps**: Define one shared constant (derived from `ArtifactKind` + the augmentation-eligible set) and have both `org_pack_loader._AUGMENTATION_PLURAL_TO_KIND` and `pack_validator._AUGMENTATION_PLURAL_KINDS` derive from it. Remove the "kept in sync" hand-duplication (R-011-A, FR-030).

**Validation**: - [ ] one definition; both modules import/derive it; adding a kind is a one-line change.

### T014 — Emit augmentation + `specializes_from` edges from fragments

**Steps**:
1. Refactor `_collect_augmentation_edges`: stop scanning artifact **fields**; emit edges from **fragment-authored** relationships. Extract the per-relation list into a module constant `_AUGMENTATION_FIELDS`/`_RELATIONS` incl. `("specializes_from", Relation.SPECIALIZES_FROM)` so lineage edges auto-emit too (FR-001 plumbing).
2. Split the per-file extraction into a helper to keep `_collect_augmentation_edges` under the ruff C901 limit (`refactoring-extract-class-by-responsibility-split`).

**Validation**: - [ ] fragment-authored `enhances`/`overrides`/`specializes_from` produce the right `DRGEdge`s; field scanning removed.

### T015 — Extend augmentation eligibility to the 4 uncovered kinds

**Steps**: Add directive, toolguide, mission-step-contract to the augmentation-eligible set (mission-type handled in T017). Ensure fragment edges for these validate.

**Validation**: - [ ] fragment `enhances`/`overrides` on a directive/toolguide/step-contract validates.

### T016 — Validator intent-aware parity (FR-031)

**Steps**: In `pack_validator.py`, apply the existing `same_id_collision` suppression / `unknown_target` hard-error / `intent_conflict` logic uniformly to the newly-covered kinds, reading fragment edges.

**Validation**: - [ ] declared intent suppresses the advisory; unknown target hard-errors; both-declared → `intent_conflict` — for the new kinds too.

### T017 — Mission-type augmentation resolution (FR-032)

**Steps**: **Decision locked (FR-032): expand `_ORG_DRG_CANONICAL_KINDS` to include mission types** — the separate-path alternative is rejected. Add mission types to the canonical universe, update `_ORG_DRG_KIND_ALIASES`, and update the contract-test sweep that guards drift against `charter.activations._ALLOWED_KINDS` **in lockstep** (binding change to the 8-kind universe). Mission types MUST NOT be silently dropped. Record the locked decision inline (DIRECTIVE_003).

**Validation**: - [ ] mission-type fragment augmentation validates; contract-test sweep updated and green; no silent drop.

### T018 — Topology field-merge semantics (FR-029)

**Steps**: For mission-step-contract and mission-type, define `enhances` field-merge semantics: which fields merge vs replace, and that action-sequence ordering + step I/O contracts are preserved; `overrides` = full replacement. Implement the merge accordingly (or constrain it) consistent with ADR `2026-05-16-1`.

**Validation**: - [ ] an `enhances` overlay on a step contract preserves action-sequence ordering + step I/O; `overrides` fully replaces.

## Definition of Done

- [ ] All 6 subtasks complete; single-source augmentation set; fragment-based emission incl. lineage; 9-kind coverage; validator parity; mission-type resolved; topology semantics defined+tested.
- [ ] `tests/doctrine/test_org_pack_augmentation.py` + CC-2 gates green.

## Risks

- **Mission-type universe expansion is binding (C-009-adjacent)**: the contract-test sweep will fail until updated — update it deliberately, do not weaken it.
- Field-merge for topology kinds is subtle; lean on the ADR and add explicit ordering assertions.

## Reviewer Guidance (reviewer-renata)

- Confirm there is exactly one augmentation kind set, derived, not duplicated.
- Confirm emission reads fragments, not artifact fields (the whole point of the cutover).
- Confirm mission-type is not silently dropped and the sweep was updated, not bypassed.

---
work_package_id: WP02
title: 'Pack identity: stable pack_id'
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: feat/pack-metadata-manifest-unification
merge_target_branch: feat/pack-metadata-manifest-unification
branch_strategy: Planning artifacts for this mission were generated on feat/pack-metadata-manifest-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pack-metadata-manifest-unification unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
history:
- at: '2026-08-16'
  note: Authored at /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/
create_intent:
- src/specify_cli/doctrine/pack_descriptor.py
- tests/doctrine/test_pack_id_identity.py
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/pack_descriptor.py
- src/doctrine/drg/org_pack_config.py
- tests/doctrine/test_pack_id_identity.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile before anything else: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`).

## Objective

Give every pack a stable, immutable ULID `pack_id` as the **sole runtime identity**, and add the authored lineage-edge fields to the pack descriptor. Built-in pack first (Q2); org/fetched backfill is a later slice.

## Context

Design: [plan.md](../plan.md) IC-04 + [data-model.md](../data-model.md) `PackDescriptor`. Packs are keyed only by config `name` today at **`src/doctrine/drg/org_pack_config.py:166`** (the DRG layer — governed by the shared-package-boundary arch tests). Mirror the Mission-Identity ULID model (CLAUDE.md 083+): identity is minted once and immutable, disambiguated with **no silent fallback**.

## Subtasks

### T008 — `PackDescriptor` model
Create `src/specify_cli/doctrine/pack_descriptor.py`: the authored descriptor model with `pack_id` (ULID), `pack_version` (field lives here; relocation of the writer is WP04), `parent_pack: ULID|None`, `accompanies_doctrine_pack: ULID|None`, `name` (human handle). Define the fields now so WP03 (lineage resolution) and WP04 (authored file) build on a stable model. Test: `test_pack_id_identity.py`.

### T009 — Mint + idempotent backfill built-in `pack_id`; DRG key
Add a `pack_id` key to `OrgPackConfig` (`src/doctrine/drg/org_pack_config.py`); make `pack_id` the sole runtime identity with `name` a handle. Mint a stable `pack_id` for the built-in pack; backfill must be **idempotent** (mint once; re-runs are no-ops). Resolution disambiguates with **no silent fallback** (structured error on ambiguity, per the mission-identity WP07 regression lesson). Test: minted id is stable across two runs; ambiguous lookup errors rather than guessing.

### T010 — Confirm DRG boundary tolerance
The edit crosses into `src/doctrine/drg/` (a distinct package boundary). Run and confirm the shared-package-boundary arch tests (`tests/architectural/test_shared_package_boundary.py`, `test_layer_rules.py`) still pass with the `pack_id` addition; if the boundary rejects a needed import, record the seam and route through the sanctioned direction rather than adding a bypass.

## Definition of Done
- Built-in pack carries a stable, immutable `pack_id`; backfill idempotent; no silent identity fallback; descriptor model carries the lineage-edge fields; DRG arch tests green; `ruff`/`mypy` clean; new branches tested.

## Reviewer guidance
Verify `pack_id` immutability + idempotent backfill; `name` demoted to a handle; no silent fallback; the DRG-tree edit does not trip the shared-package-boundary ratchet.

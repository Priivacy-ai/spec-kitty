---
work_package_id: WP04
title: Activation authority + retire the implicit fallback
dependencies:
- WP03
requirement_refs:
- FR-007
- FR-008
- NFR-003
planning_base_branch: feat/resolution-activation-foundation
merge_target_branch: feat/resolution-activation-foundation
branch_strategy: Planning artifacts for this mission were generated on feat/resolution-activation-foundation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/resolution-activation-foundation unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
history:
- at: '2026-08-05'
  actor: claude
  note: Authored during /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/activation/pack_context.py
- src/charter/activation/mission_type_profiles.py
- tests/charter/test_pack_context.py
- tests/charter/test_mission_type_activation_gating.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: run `/ad-hoc-profile-load python-pedro` (role: implementer). Adopt
its identity, boundaries, and quality discipline before reading further.

## Objective

Make the provisioned charter the single activation authority by removing the implicit config-absent
"all four" backfill. After WP03 provisioning exists, an absent `mission_type_activations` resolves from
the provisioned charter or fails closed — never a silent full-roster default.

Governing: spec FR-007/008, NFR-003; contracts C-A1/C-A2/C-A6; data-model Seam 2 (I-7); research D-03/D-08.
**Depends on WP03** (provisioning must exist before the fallback is removed).

## Context

- The implicit fallback is at `charter/pack_context.py:601-619` (`_read_activated_mission_types`): returns
  `builtin_mission_type_id_set()` when the key is absent. This is the hidden second availability source.
- `mission_type_profiles.existing_mission_types` (`:498`) delegates to `activated_mission_types` and is the
  live authority consumer (with `charter/drg.py:441,471` gating). `list_available_missions` does NOT read
  it (fenced out of scope, C-003).
- **Scope guard**: only the `mission_type_activations` fallback is in scope. The `_read_activated_kinds`
  FR-039 fallback (`pack_context.py:591-598`) is a DIFFERENT contract — do NOT touch it (C-008 sibling).

## Subtasks

### T019 — RED acceptance test
In `tests/charter/test_pack_context.py` + `test_mission_type_activation_gating.py`. Note: "provisioned"
means the `mission_type_activations` key is **present** in config (WP03 writes it); "absent" means genuinely
missing. Three honest cases:
- (a) **key present** (provisioned with the four built-ins) → `existing_mission_types` returns exactly
  those four; no more, no fewer. This IS the C-A6/NFR-003 authority parity — measured at
  `existing_mission_types`, NOT `list_available_missions` (which is fenced unchanged and would be a no-op).
- (b) **key genuinely absent** → the read does NOT return `builtin_mission_type_id_set()` (no implicit
  full-roster backfill); it **fails closed** with an actionable error (C-A1/C-A4/NFR-001, scoped to
  `mission_type_activations`).
- (c) authored `mission_type_activations: []` → `frozenset()`, unchanged (C-A2/C-008).
Update the existing bare-project cases (they currently assert the full-catalog fallback) — flipping them
to fail-closed is the expected behavior change. Keep T034 (custom type not dropped) + T036 (subset). Must
fail first.

### T020 — Remove the config-absent backfill (name the replacement)
Delete the `builtin_mission_type_id_set() if activated is None else activated` backfill at
`pack_context.py:619`. `_read_activated_mission_types` returns a non-optional `frozenset[str]` today, so
the absent branch needs an explicit replacement: **fail closed** — raise the charter fail-closed error
(e.g. `CharterPackConfigError`) with an actionable message (the project is unprovisioned; run
`spec-kitty upgrade` / init provisioning), NOT a roster return and NOT `None`. **Do NOT add a runtime
`default.yaml` read here** — provisioning (WP03) is the sole writer of the key; WP04 is delete-only at the
read boundary (adding a read would be the second availability source WP05 T023 catches). An explicit
`mission_type_activations: []` still returns `frozenset()` (C-008). Keep the field docstrings accurate.

### T021 — Update the authority delegation/docstring
Update `mission_type_profiles.existing_mission_types` docstring/delegation to reflect that
`activated_mission_types` is now authoritative (no implicit default). No behavior change for provisioned
projects. Preserve T034 (custom type not dropped) and T036 (subset narrowing) behavior.

### T022 — Update the tests
`test_pack_context.py` + `test_mission_type_activation_gating.py` green with the revised bare-project
expectation; keep the T034/T036 durability guards intact.

## Branch Strategy

Planning/base and merge target: `feat/resolution-activation-foundation`. Enter the resolved workspace via
`spec-kitty implement WP04` (dependencies: WP03) — the lane is computed from `lanes.json`.

## Definition of Done

- C-A1 no implicit backfill site remains (scoped to `mission_type_activations`); C-A2 authored-empty
  preserved; C-A6/NFR-003 authority parity green for provisioned projects.
- T034/T036 gating behavior intact.
- `mypy --strict` + `ruff` clean; complexity ≤15; no new suppressions.

## Risks / reviewer guidance

- Requires WP03 provisioning — a bare project with no provisioning + no key must now fail closed, NOT
  return all four. Confirm the WP03 provisioning covers fresh-init and migration so real projects always
  have the key.
- Do NOT harmonize the `_read_activated_kinds` FR-039 fallback — different contract, out of scope.
- NFR-003 parity MUST be measured at the activation authority, never `list_available_missions` (a fenced
  no-op).

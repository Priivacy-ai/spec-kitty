---
work_package_id: WP02
title: Downstream delegation, default_missions_root, sibling-pattern authority
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-005
- FR-012
- FR-013
- NFR-006
planning_base_branch: feat/resolution-activation-foundation
merge_target_branch: feat/resolution-activation-foundation
branch_strategy: Planning artifacts for this mission were generated on feat/resolution-activation-foundation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/resolution-activation-foundation unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
history:
- at: '2026-08-05'
  actor: claude
  note: Authored during /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent:
- tests/doctrine/test_missions_root_packs_env.py
execution_mode: code_change
owned_files:
- src/doctrine/pack_paths.py
- src/doctrine/missions/repository.py
- src/specify_cli/runtime/agent_commands.py
- tests/doctrine/test_missions_root_packs_env.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: run `/ad-hoc-profile-load python-pedro` (role: implementer). Adopt
its identity, boundaries, and quality discipline before reading further.

## Objective

Route the doctrine resolvers through the WP01 kernel primitive so the whole built-in pack (missions
included) honors `SPEC_KITTY_PACKS_ROOT` by construction, and collapse the drifting sibling-pattern
constants onto one authority.

Governing: spec FR-001/003/004/005/012/013, NFR-006; contracts C-R1/C-R2/C-R3/C-R4; data-model Seam 1
(I-3/I-4/I-5/I-6); research D-01/D-02. **Depends on WP01** (the kernel primitive must exist).

## Context

- `doctrine/pack_paths.py::_resolve_built_in` currently reads `_PACKS_ROOT_ENV` itself (`:204`) and
  translates `SiblingPathNotFound → PackRootNotFound`. Consumers depend on the specific `PackRootNotFound`
  type (`pack_validator.py:83,793`) — the translation MUST survive at the doctrine boundary.
- `doctrine/missions/repository.py::default_missions_root` passes `env_override=None` (`:144`) — the
  env-blind gap. `built_in_root()` = `resolve_pack_root("built-in")` resolves `packs/built-in`.
- Sibling pattern is forked: `kernel/paths.py` `_MISSION_ASSETS_SIBLING_PATTERN`,
  `repository.py:29` `_MISSIONS_ROOT_SIBLING_PATTERN`, `agent_commands.py:93` `_MISSIONS_SIBLING_PATTERN`.

## Subtasks

### T008 — RED acceptance test (NFR-006)
Create `tests/doctrine/test_missions_root_packs_env.py` (new): with `SPEC_KITTY_PACKS_ROOT=<tmp>`,
**both** `default_missions_root()` and `get_package_asset_root()` resolve under `<tmp>/built-in/missions`
(C-R2); with both env vars set, PACKS_ROOT wins (C-R3). Must fail first (`default_missions_root` ignores
PACKS_ROOT today).

### T009 — Delegate `_resolve_built_in` to the kernel primitive
`pack_paths._resolve_built_in` calls the WP01 kernel entry point instead of reading `_PACKS_ROOT_ENV`
itself. Keep the `SiblingPathNotFound → PackRootNotFound` translation at this doctrine boundary (a
consumer depends on the type). Retire the now-duplicate env read.

### T010 — `default_missions_root = built_in_root()/"missions"` (+ fail-closed)
Rewrite `default_missions_root` as `built_in_root() / "missions"`. **Delta-review caveat**: `built_in_root()`
only verifies `packs/built-in` exists, so add an `.is_dir()` check on the `/missions` leaf and raise
`MissionsRootNotFound` on absence (preserves FR-013/C-R4/I-4). Remove the local `env_override=None`
sibling walk.

### T011 — Sibling-pattern single authority (FR-012)
Have the kernel authority own the `built-in` pattern + the `missions` leaf name; collapse
`_MISSIONS_ROOT_SIBLING_PATTERN` (repository.py) and `_MISSIONS_SIBLING_PATTERN` (agent_commands.py) onto
it via a downward import. **agent_commands.py: constant only** — do NOT change its
`_get_command_templates_dir` body (out of scope; it is startup-cheap doctrine-anchored discovery).

### T012 [P] — Fix the false `dev_roots` docstring
Correct `repository.py:37-44` (`MissionsRootNotFound` eager-eval note): there is no `dev_roots` tuple in
`home.py`; the claim is false (fold F2, FR-005 doctrine half). Rewrite to the real topology.

### T013 — Green the tests
`tests/doctrine/` + affected `tests/charter/` resolver tests green. Run from the primary checkout.

## Branch Strategy

Planning/base and merge target: `feat/resolution-activation-foundation`. Enter the resolved workspace
via `spec-kitty implement WP02` (dependencies: WP01) — the lane is computed from `lanes.json`.

## Definition of Done

- C-R2 regression green (both resolvers relocate via PACKS_ROOT); C-R3 both-vars precedence green.
- `default_missions_root` fail-closed with `.is_dir()` + `MissionsRootNotFound` (C-R4/I-4).
- `PackRootNotFound` still raised at the doctrine boundary (`pack_validator` consumer unbroken).
- Sibling pattern owned once; `repository.py`/`agent_commands.py` constants delegate (FR-012).
- `mypy --strict` + `ruff` clean; complexity ≤15; no new suppressions.

## Risks / reviewer guidance

- Do NOT touch the availability readers or the nested-vs-flat `mission_types/` path (scope fence C-002/C-003).
- Verify `built_in_root()/"missions"` yields byte-identical paths to today's resolution under default env
  (NFR-003 path parity) — the WP05 arch/parity guard will assert single-source.

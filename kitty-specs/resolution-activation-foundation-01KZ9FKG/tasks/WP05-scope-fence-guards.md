---
work_package_id: WP05
title: Single-source + scope-fence architectural guards
dependencies:
- WP01
- WP02
- WP04
requirement_refs:
- NFR-001
- NFR-002
- NFR-005
planning_base_branch: feat/resolution-activation-foundation
merge_target_branch: feat/resolution-activation-foundation
branch_strategy: Planning artifacts for this mission were generated on feat/resolution-activation-foundation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/resolution-activation-foundation unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
history:
- at: '2026-08-05'
  actor: claude
  note: Authored during /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_resolution_activation_foundation.py
execution_mode: code_change
owned_files:
- tests/architectural/test_resolution_activation_foundation.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: run `/ad-hoc-profile-load python-pedro` (role: implementer). Adopt
its identity, boundaries, and quality discipline before reading further.

## Objective

Add the durable regression guards that prove the foundation is single-sourced and stayed scoped. These
are the invariants the whole mission exists to establish; they must fail if a future change reintroduces
a second source or crosses the scope fence.

Governing: spec NFR-001/002/005, SC-001/SC-005; constraints C-001/C-003; contracts C-R1/C-S1. **Depends
on WP01, WP02, WP04** (the code they assert must exist). Run all assertions from the **primary checkout**
(arch gates are vacuous inside a worktree — tracer W3).

## Context

- Proof markers verified assertable today (delta review): `MissionTypeNotAnArtifactKind`
  (`doctrine/artifact_kinds.py:219`), `_MISSION_TYPE_UNIVERSE_EXTENSION` (`org_pack_loader.py:129`),
  `list_available_missions` (`mission.py:489`), `_build_discovery_context` (`runtime_bridge_io.py:231`).
- The existing `test_kernel_no_doctrine_import.py` covers kernel↔doctrine; this WP adds the
  mission-specific single-source + fence guards in one new file.

## Subtasks

### T023 — Single-source resolution/availability guard (NFR-001 / SC-001)
Create `tests/architectural/test_resolution_activation_foundation.py` asserting: (a) exactly one
`SPEC_KITTY_PACKS_ROOT` **read** across `src/` — match actual env reads (`os.environ.get("SPEC_KITTY_PACKS_ROOT")`
/ `os.getenv(...)` / `os.environ[...]`), NOT raw string occurrences, so the retained docstring
(`pack_paths.py:13`) and constant name (`pack_paths.py:88` `_PACKS_ROOT_ENV`) do not false-positive; the
one legitimate read lives in the kernel primitive after WP02 retires the doctrine read; (b) exactly one
`get_package_asset_root` implementation body; (c) 0 implicit config-absent `mission_type_activations`
all-four backfill site. **Scope (c) to `mission_type_activations`** — the `_read_activated_kinds`
three-state fallback and the directive/kind fallbacks are legitimate and MUST NOT be flagged.

### T024 — Scope-fence guard (C-S1 / SC-005 / C-001, C-003)
Assert: `MissionTypeNotAnArtifactKind` is still raised for `"mission-type"`; `_MISSION_TYPE_UNIVERSE_EXTENSION`
intact; `list_available_missions` + `_build_discovery_context` are unchanged (still filesystem-based, do
NOT consult the activation set); `src/specify_cli/missions/` still present on disk. (C-002/C-004 are
review-only fences — optionally assert `built_in_dir(kind)` gains no mission-type entry; do not attempt to
assert "no decision was made".)

### T025 — Layer + terminology gates green (NFR-002 / NFR-005)
Run and **cite green** (in the WP history/PR notes) the three named gates from the **primary checkout**:
`tests/architectural/test_kernel_no_doctrine_import.py`, the layer-rule gate
(`test_layer_rules.py`), and `test_no_legacy_terminology.py` — proving 0 new upward edges and 0 new
`feature*` prose. This is a verify-and-cite step, not "add a note if you feel like it".

## Branch Strategy

Planning/base and merge target: `feat/resolution-activation-foundation`. Enter the resolved workspace via
`spec-kitty implement WP05` (dependencies: WP01, WP02, WP04) — the lane is computed from `lanes.json`.

## Definition of Done

- SC-001 fully asserted (single PACKS_ROOT read / door body / no mission_type_activations backfill).
- SC-005 scope fence asserted (kind contract + readers unchanged + tree present).
- NFR-002/NFR-005 gates green from the primary checkout.
- `mypy --strict` + `ruff` clean; complexity ≤15; no new suppressions.

## Risks / reviewer guidance

- This WP is verify-last: run after WP01/WP02/WP04 land, from the primary checkout (a green run inside a
  `.worktrees/` lane proves nothing — tracer W3).
- Keep the single-source assertion narrowly scoped to `mission_type_activations` and the pack-root read —
  over-broad matching will flag the legitimate directive/kind three-state fallbacks and go red falsely.

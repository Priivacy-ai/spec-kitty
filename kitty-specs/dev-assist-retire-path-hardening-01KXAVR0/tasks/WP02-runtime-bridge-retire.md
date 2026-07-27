---
work_package_id: WP02
title: Runtime-bridge dev-assist retire/narrow
dependencies: []
requirement_refs:
- FR-003
- FR-006
- NFR-002
- NFR-003
- NFR-004
- C-002
- C-003
tracker_refs:
- '2557'
planning_base_branch: feat/dev-assist-retire-path-hardening
merge_target_branch: feat/dev-assist-retire-path-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/dev-assist-retire-path-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dev-assist-retire-path-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dev-assist-retire-path-hardening-01KXAVR0
base_commit: 4e129fc35c2c4d8ee3b87208b14e6c2be7c9c237
created_at: '2026-07-12T11:24:24.503260+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Dev-assist retirement
shell_pid: "250232"
agent: "claude"
history:
- at: '2026-07-12T10:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/runtime/
create_intent: []
execution_mode: code_change
owned_files:
- tests/runtime/test_bridge_cores.py
- tests/runtime/test_bridge_retrospective.py
- tests/runtime/test_bridge_composition.py
- tests/runtime/test_bridge_io.py
- tests/runtime/test_bridge_parity.py
role: implementer
tags: []
task_type: implement
---

# WP02 — Runtime-bridge dev-assist retire/narrow

## Context

The standing family guard `tests/runtime/test_bridge_compat_surface.py::test_guard_b_identity_reexport_for_relocated_symbols` iterates `ALL_COMPAT_SYMBOLS` (50) and already asserts every relocated symbol is a native delegate or identity re-export. Research R2 verified per-candidate symbol-set membership. Do NOT edit `test_bridge_compat_surface.py` (it is the coverage authority, read-only for this WP).

## Approach (coverage before deletion, C-002)

1. **T001 — RETIRE pure duplicates** (all symbols ∈ `ALL_COMPAT_SYMBOLS`): `test_bridge_cores.py::test_tracked_guard_and_parse_symbols_are_native_delegates` **and** its now-unused `_TRACKED_NATIVE_DELEGATES` constant; `test_bridge_retrospective.py::test_runtime_bridge_keeps_native_thin_delegates_for_compat_guarded_names`; `test_bridge_composition.py::test_runtime_bridge_keeps_native_thin_delegates_for_compat_guarded_names`. Keep each file's `_COMPAT_GUARDED_NAMES` constant (still used by `test_seam_defines_every_relocated_symbol`).
2. **T002 — RETIRE inert** `test_bridge_parity.py::test_nfr006_timing_seed` (its consumer, WP10's timing-parity test, was deleted in #2558; it only asserts `duration > 0`).
3. **T003 — NARROW** `test_bridge_io.py::test_runtime_bridge_keeps_native_thin_delegates_for_compat_guarded_names`: iterate only `_PUBLIC_RELOCATED_NAMES` (`get_or_start_run`, `build_operational_context_for_claim` — 2 public symbols the family guard, which tracks only `_`-privates, does not cover). Rename to reflect it now guards public relocated names.
4. **T004 — KEEP + re-point docstrings** (FR-006): keep `test_bridge_cores.py::test_untracked_parse_helpers_are_identity_reexports` (5 unpatched helpers, not in baseline — unique). Update the `test_seam_defines_every_relocated_symbol` docstrings in retrospective/composition that reference "the delegate assertions below" (now removed) so they read as standalone seam-completeness checks.
5. **T005 — anti-vacuity + green**: plant a silent copy-instead-of-delegate re-export → confirm `test_bridge_compat_surface.py` fails → revert. Full `tests/runtime/` suite green; net test LOC down.

## Acceptance

- The 3 duplicates + inert seed removed; io test narrowed; unique test kept; docstrings re-pointed.
- Family guard still passes and still catches a planted regression.
- `PWHEADLESS=1 uv run pytest tests/runtime/ -q` green; `ruff` clean.

## Branch Strategy

Planning branch: `feat/dev-assist-retire-path-hardening`; final merge target the same (PR'd to `main` at close). Worktree per lane from `lanes.json`.

## Activity Log

- 2026-07-12T11:54:19Z – claude – shell_pid=250232 – Moved to for_review
- 2026-07-12T12:14:17Z – claude – shell_pid=250232 – LAND review a106606a

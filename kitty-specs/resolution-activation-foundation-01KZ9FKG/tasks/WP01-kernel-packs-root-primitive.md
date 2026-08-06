---
work_package_id: WP01
title: Kernel PACKS_ROOT-aware resolution primitive + collapse the second copy
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-004
- FR-005
- FR-006
- FR-013
planning_base_branch: feat/resolution-activation-foundation
merge_target_branch: feat/resolution-activation-foundation
branch_strategy: Planning artifacts for this mission were generated on feat/resolution-activation-foundation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/resolution-activation-foundation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-resolution-activation-foundation-01KZ9FKG
base_commit: 4a81da40f324e9ec2fbe17c7fe69c7b6a4553fd6
created_at: '2026-08-05T20:13:02.449836+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- at: '2026-08-05'
  actor: claude
  note: Authored during /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: src/kernel/
create_intent: []
execution_mode: code_change
owned_files:
- src/kernel/paths.py
- src/kernel/__init__.py
- src/kernel/README.md
- src/kernel/sibling_paths.py
- src/specify_cli/runtime/home.py
- src/specify_cli/runtime/__init__.py
- tests/kernel/test_paths.py
- tests/runtime/test_home_unit.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: run `/ad-hoc-profile-load python-pedro`
(role: implementer). Adopt its identity, boundaries, and quality discipline for this work package.

## Objective

Establish the **single** built-in-pack-root resolution authority at the kernel floor (DR-1) and
collapse the runtime second copy. The `built-in` pack — missions included — is located from the
default- or env-supplied pack root (`SPEC_KITTY_PACKS_ROOT`). After this WP there is one
`SPEC_KITTY_PACKS_ROOT` read, one `get_package_asset_root` body, and one
`_find_relocated_missions_ancestor`.

Governing: ADR `docs/adr/3.x/2026-08-05-1-…` (2026-08-05 DR-1/DR-2 addendum), spec FR-001/002/004/005/006/013,
contracts C-R1/C-R2/C-R4/C-R5, data-model Seam 1. Delta-review confirmed the layer-move is clean
(`kernel/paths.py` already reads `SPEC_KITTY_HOME`, `SPEC_KITTY_TEMPLATE_ROOT`; the AST gate
`tests/architectural/test_kernel_no_doctrine_import.py` excludes env-var strings).

## Context

- `kernel/sibling_paths.py::resolve_installed_sibling(anchor_file, env_override, sibling_relative_path)`
  is the env-agnostic algorithm — the caller supplies the env override. Reuse it; do not reimplement.
- Today: `kernel/paths.py::get_package_asset_root` honors only `SPEC_KITTY_TEMPLATE_ROOT`;
  `SPEC_KITTY_PACKS_ROOT` is read only in `doctrine/pack_paths.py` (WP02 will delegate to us).
- Today: `specify_cli/runtime/home.py::get_package_asset_root` is a second body that reaches doctrine
  and carries `specify_cli/missions` + `dev_root` legacy fallbacks. Those fallbacks are dropped (DR-2).

## Subtasks

### T001 — RED acceptance test
Add failing tests in `tests/kernel/test_paths.py` (+ `tests/runtime/test_home_unit.py`): (a) with
`SPEC_KITTY_PACKS_ROOT=<tmp>` containing `built-in/missions`, `get_package_asset_root()` resolves under
`<tmp>`; (b) a pack root with no `built-in/missions` fails closed (raises, no fall-through); (c) with
both `SPEC_KITTY_PACKS_ROOT` and `SPEC_KITTY_TEMPLATE_ROOT` set, PACKS_ROOT wins for pack-root location.
These must fail first (door is PACKS_ROOT-blind today).

### T002 — Kernel PACKS_ROOT-aware primitive (public)
Add a kernel entry point that reads `SPEC_KITTY_PACKS_ROOT`, joins `/built-in`, and passes it as
`env_override` to `resolve_installed_sibling` (pattern `packs/built-in`). **Ordering (delta-review):**
insert the PACKS_ROOT branch **ahead of** the retained `SPEC_KITTY_TEMPLATE_ROOT` branch — do not
delete TEMPLATE_ROOT handling (C-009). Kernel reading an env var is layer-legal (no doctrine import).
**Export it publicly (post-tasks squad):** add the new entry point AND the sibling-pattern constant
(`_MISSION_ASSETS_SIBLING_PATTERN` → a public name) to `kernel.__all__`, so WP02's delegation + FR-012
constant-collapse import a **public** kernel symbol, not a private one (kernel `__all__` is `[]` today).

### T003 — Repoint the door (+ C-009 caller census)
`get_package_asset_root()` resolves `<built-in-pack-root>/missions` through the T002 primitive. Preserve
the fail-closed contract (raise, never a nonexistent path). **C-009 census (post-tasks squad — a DoD
item, not just a risk):** enumerate the door's callers (`init.py`, `runtime/resolver.py`, `bootstrap.py`,
`migrate.py`, `show_origin.py`, `agent_commands.py`, `charter/catalog.py`) and confirm each still gets
correct behavior — PACKS_ROOT-first with the TEMPLATE_ROOT branch retained means no existing
TEMPLATE_ROOT-relying caller regresses. Record the census result in the WP history/PR notes.

### T004 — Collapse `home.py`; drop legacy fallbacks
Make `specify_cli/runtime/home.py::get_package_asset_root` a thin delegation to the kernel authority.
Remove the `specify_cli/missions` importlib fallback and the `dev_root` fallback (fail-closed, DR-2).
The surviving content detector must be the **enumeration-free wildcard**, not per-type enumeration via
`builtin_mission_type_ids()` (D-06). Update `specify_cli/runtime/__init__.py`'s re-export mapping to the
single authority. **Retarget** the monkeypatch seams in `tests/runtime/test_home_unit.py` (C-007) — do
not orphan them.

### T005 — De-duplicate the ancestor walk
One `_find_relocated_missions_ancestor` definition (kernel's, constant-based). Remove home.py's inline copy.

### T006 [P] — Correct false docstrings
Fix the false "re-exported by `specify_cli.runtime.home`" claims in `kernel/__init__.py` and
`kernel/README.md` to describe the real single-door topology (FR-005 kernel half).

### T007 — Green the tests
`tests/kernel/test_paths.py` + `tests/runtime/test_home_unit.py` green. Run from the primary checkout.

## Branch Strategy

Planning/base and merge target: `feat/resolution-activation-foundation`. Execution worktrees are
allocated per computed lane from `lanes.json` (created by `finalize-tasks`); enter the resolved
workspace via `spec-kitty implement WP01` — do not reconstruct the path.

## Definition of Done

- SC-001 partial: one `get_package_asset_root` body, one `_find_relocated_missions_ancestor`, one
  `SPEC_KITTY_PACKS_ROOT` read (kernel) — the arch assertion itself lands in WP05.
- C-R2/C-R4 door behavior green (PACKS_ROOT relocation; fail-closed; both-vars precedence).
- C-R5 kernel docstrings truthful.
- `mypy --strict` + `ruff` clean; complexity ≤15; no new suppressions; monkeypatch seams retargeted.

## Risks / reviewer guidance

- **C-009**: confirm TEMPLATE_ROOT still works for existing door callers — this WP adds PACKS_ROOT-first
  ordering, it does NOT remove TEMPLATE_ROOT. WP02 owns the doctrine delegation; do not edit doctrine here.
- Verify the AST layer gate (`test_kernel_no_doctrine_import.py`) stays green — the env read is a string
  literal excluded by the gate; adding a doctrine import would fail it.

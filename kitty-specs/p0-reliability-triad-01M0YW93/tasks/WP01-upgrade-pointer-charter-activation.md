---
work_package_id: WP01
title: Upgrade heals pointer-based charter activations (#3282)
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: fix/p0-reliability-triad
merge_target_branch: fix/p0-reliability-triad
branch_strategy: Planning artifacts for this mission were generated on fix/p0-reliability-triad. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/p0-reliability-triad unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history:
- '2026-08-26: authored by tasks flow'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/upgrade.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/cli/commands/upgrade.py
- tests/specify_cli/upgrade/test_upgrade_provisions_mission_type_activations.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, boundaries, and TDD discipline for the whole work package.

## Objective

`spec-kitty upgrade` currently writes mission-type activations to `.kittify/config.yaml`, but a project using a **pointer-based charter** (`config.yaml` carries `charter: .kittify/charter/charter.yaml`) reads activations from the pointed-at `charter.yaml`. The written key is ignored → the effective registry stays empty → `mission create` / `setup-plan` fail closed with "Unknown mission type". Fix the write side to target the same authority the read side uses, and make the dry-run predicate agree.

Bug is LIVE on main. Root cause and fix direction are in `research.md` (WP01) and `contracts/behavioral-contracts.md` (C-WP01).

## Branch Strategy

- Planning base: `fix/p0-reliability-triad`. Final merge target: `fix/p0-reliability-triad`.
- Execution worktree is allocated per computed lane from `lanes.json` (created by `finalize-tasks`). Enter it via `spec-kitty agent action implement WP01 --agent claude`; do not reconstruct the path.

## Subtasks

### T001 — RED test first
- Extend `tests/specify_cli/upgrade/test_upgrade_provisions_mission_type_activations.py`.
- Add a **pointer-charter fixture**: `config.yaml` with `charter: .kittify/charter/charter.yaml` + a `charter.yaml` that lacks `mission_type_activations`.
- Drive the pre-existing public entry point — the `upgrade` CLI via `_run_upgrade([...])` (CliRunner), mirroring `test_upgrade_heals_stranded_project_and_unblocks_mission_creation`.
- Assert: `PackContext.from_config(project).activated_mission_types` is non-empty AND the key landed in `charter.yaml`, not `config.yaml`; `existing_mission_types(project) != []`.
- Add a second case: `charter.yaml` with an **authored empty** `mission_type_activations: []` → upgrade is a no-op (preserved, not overwritten).
- Confirm these are RED on current code before touching source.

### T002 — Route through the pointer-aware writer
- In `src/specify_cli/cli/commands/upgrade.py`, change `_provision_missing_mission_type_activations` to seed through `charter.compiler.provision_mission_type_activations` (which delegates to `charter.pack_manager.resolve_activation_write_target` → `charter.yaml` for pointer projects, `config.yaml` for legacy). **Do not** modify `resolve_activation_write_target` or `provision_default_mission_type_activations` (C-004; fresh-init blast radius).

### T003 — Fix the pending predicate + dangling-pointer contract
- Rewrite `_mission_type_activation_provisioning_pending` to inspect the resolved write target (or `PackContext.from_config(...).activated_mission_types`) so the dry-run / `--json pending_provisioning` preview is truthful for pointer projects.
- The resolver **raises** `CharterPackConfigError` on a dangling/unreadable `charter:` pointer. Keep a **defined, non-crashing** dry-run contract: catch it and report a stable preview state (not an unhandled raise, not a silent False that hides a broken pointer).

### T004 — Preserve semantics + docstring + lint
- Preserve additive/idempotent semantics and the authored-empty-`[]` no-op (verify against the existing idempotency test + the new authored-empty pointer test).
- Update the `_provision_missing_mission_type_activations` docstring: after this fix, fresh-init stays on the pointer-blind `provision_default_mission_type_activations` while upgrade uses the pointer-aware writer — the divergence is intentional, not a regression.
- `ruff check` + `mypy` clean; no new suppressions; complexity ≤15.

## Definition of Done
- New pointer-charter + authored-empty tests RED before, GREEN after.
- No new migration added (NFR-003 — the finalizer runs every upgrade).
- `resolve_activation_write_target` / `provision_default_mission_type_activations` untouched (C-004).
- ruff + mypy clean.

## Risks / Reviewer guidance
- **Tempting wrong edit**: patching `provision_default_mission_type_activations` (shared with fresh init, pinned by `test_init_provisioning`) — reject; pointer logic lives only in the upgrade helper.
- Reviewer confirms WP01's write authority matches the read-path validation authority that #3702 consults (consistency, not a fold).
- Verify serialization parity (byte-stable round-trip) when the non-pointer path routes through the resolver's `_save_config`.

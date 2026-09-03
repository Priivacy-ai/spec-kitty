---
work_package_id: WP04
title: commit_router fail-loud all sites + align (DD-3)
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: fix/coord-commit-surface-authority
merge_target_branch: fix/coord-commit-surface-authority
branch_strategy: Planning artifacts for this mission were generated on fix/coord-commit-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/coord-commit-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
history:
- at: '2026-09-03T00:00:00+00:00'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/coordination/test_commit_router_fail_loud.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/commit_router.py
- tests/coordination/test_commit_router_fail_loud.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`); apply and state. Stay within `owned_files`.

## Objective

Close the "silent misroute to primary" defect class by construction (INV-3 / DIR-043): every silent `return repo_root, files` fallback in `commit_router` that changes the commit surface without signalling must fail loud (coord-routed missions only reach these paths in genuinely corrupt state). Align the router's refuse path to the shared rule.

**Squad-critical**: DD-3 as first written named only ONE site. There are ~4. Cover them all (or consciously document any exclusion with rationale), else the class is not closed.

Read first: [contracts/authoritative-surface.md](../contracts/authoritative-surface.md) rule 1 & 5, [research.md](../research.md) D-004, [plan.md](../plan.md) DD-3. **Depends on WP01.**

## Why fail-loud is correct here
`_materialise_coord_worktree` is reached ONLY under `if use_coord:` (`:316`), i.e. the mission routes through coordination. Reaching a fallback means a coord-routed mission has a missing/short `mission_id` or a coord-worktree resolution failure — a corrupt state where silently writing a coordination-kind artifact to the primary checkout is exactly the INV-3 misroute we target. Flattened / SINGLE_BRANCH / LANES missions never enter this function (architect-verified), so no legitimate caller relies on the fallback.

## Subtasks

### T014 — Fail-loud on `_resolve_mid8 → None` (`:700-701`)
Replace the silent `if mid8 is None: return repo_root, files` in `_materialise_coord_worktree` with a fail-loud error naming the mission and the corrupt `meta.json` (coordination-routed but no resolvable `mission_id`). Structured error; non-zero exit at the command boundary.

### T015 — Fail-loud on the twin/sibling fallbacks (zero exclusions)
Same treatment for **all** of:
- the `except Exception → primary` in `_materialise_coord_worktree` (`:705-711`)
- `_resolve_commit_worktree_for_kind` mid8-None (`:939-940`) and its `except Exception` (`:950-954`)
By this WP's own analysis (all four sites are reached only in corrupt coord state; no legitimate caller relies on the fallback — architect-verified) the correct number of exclusions is **zero**: make all four fail loud. Any exclusion requires explicit architect sign-off referencing the line — it is NOT an implementer judgment call. Note the two *correct* primary-routing early-returns in `_resolve_commit_worktree_for_kind` (`:933`, `:936`, which return `repo_root, paths` for primary-kind / coord-less topology) are **intentional and must NOT be hardened** — list them as explicit exclusions in the ledger. Update the module docstring (`:665-666`, "C-004 strangler safety") to match the new contract.

### T016 — Align the refuse path to `resolve_surface_authority`
`commit_router._commit_partition_group` (`:288-314`): have the protected-primary refusal derive from `resolve_surface_authority` (rules 1–5), and ensure `no_op_wrong_surface` maps to a Refuse verdict (exit 1), never treated as an exit-0 no-op. Preserve the existing typed no-op vocabulary (`unchanged`, `no_op_already_committed`, `no_op_no_changes` stay exit-0).

### T017 — Guard tests `[P]`
`tests/coordination/test_commit_router_fail_loud.py` (NEW): for each of the four hardened sites, construct the trigger (corrupt/truncated `meta.json` so `_resolve_mid8` returns None; a `CoordinationWorkspace.resolve` raise) and assert the command fails loud **asserting JSON-mode exit codes** (non-zero, coord-routed error) rather than silently committing to primary. Add a positive test that a healthy coord mission still commits to its coord surface unchanged, and re-run WP01's `tests/coordination/test_surface_authority_goldens.py` spec-commit `unchanged` row to prove exit-0 no-op is intact (#2739).

## Branch Strategy
Base/merge: `fix/coord-commit-surface-authority`. One lane; worktree from `lanes.json`.

## Definition of Done
- All four named silent primary-fallback sites (`:701`, `:711`, `:940`, `:954`) fail loud; **zero exclusions** (any exclusion carries architect sign-off). The two correct primary-routing early-returns (`:933`, `:936`) are listed as intentional exclusions, not hardened.
- Refuse path derives from the shared rule; `no_op_wrong_surface` → exit 1 (JSON-mode asserted).
- Typed genuine no-ops still exit 0 (WP01 spec-commit golden stays green — no #2739 regression).
- New guard tests pass (JSON-mode exit codes); healthy-coord positive test passes. `ruff`/`mypy` clean, no suppressions.

## Reviewer Guidance
- Run `grep -nE 'return repo_root, (files|paths)' src/specify_cli/coordination/commit_router.py` and reconcile EVERY hit against a fail-loud-or-intentional-exclusion ledger (the bare `files` grep misses the `:940`/`:954` `paths`-family sites — do not use it).
- Confirm the #2739 no-op contract (exit-0 `unchanged`) is intact (run WP01 spec-commit golden).
- Confirm no new `coordination→cli` import when consuming the helper.

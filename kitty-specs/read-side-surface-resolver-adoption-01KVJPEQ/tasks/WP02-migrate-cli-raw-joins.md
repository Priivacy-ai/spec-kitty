---
work_package_id: WP02
title: Migrate the 4 raw-join read-CLI residuals
dependencies:
- WP01
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: feat/read-side-surface-resolver-adoption
merge_target_branch: feat/read-side-surface-resolver-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/read-side-surface-resolver-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-side-surface-resolver-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2392474"
history:
- at: '2026-06-20T14:30:00Z'
  actor: claude
  note: WP authored from plan IC-02a (FR-002). The 4 raw-join read-CLI residuals.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/cli/commands/agent/context.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/decision.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Route the **four** raw-join read-CLI bootstraps through WP01's `resolve_handle_to_read_path` seam, eliminating the hand-rolled `repo_root / KITTY_SPECS_DIR / raw_handle` → `load_meta` → `mid8` blocks. Behavior-preserving for `<slug>-<mid8>`/full-id handles. (IC-02a; FR-002)

## Context (allowlist dispositions are NOT uniform — squad-corrected)
- These are four entries in 01KVGCE8's `_ALLOWLISTED_RAW_JOINS`, but under **two different dispositions** (verified in `tests/architectural/test_single_mission_surface_resolver.py`):
  - **THREE tagged `#2046` read-side residual:** `agent/context.py:72` `_find_feature_directory`; `agent/mission.py:1327` `_find_feature_directory` + `mission.py:1378` `.is_dir()` existence probe. These are FR-007's drain set.
  - **ONE tagged `D-6 factory boundary`:** `decision.py:464` `cmd_verify` (NOT a #2046 residual — a separate disposition). Migrating it is a **consolidation** that removes a parallel cascade; its D-6 allowlist entry drains as a consequence. Do NOT relabel it a #2046 residual.
- (Audit-verified) NONE pre-validate the handle today — the seam's FR-004 guard fixes that for free.
- The seam (WP01) does the guarded probe + mid8 derivation + routing. Each site becomes a one-line `feature_dir = resolve_handle_to_read_path(repo_root, handle)`.

## Subtasks
### T006 — Migrate `context.py:72` [P]
- Replace the raw-join + `load_meta` + `resolve_mid8` block with `resolve_handle_to_read_path(repo_root, raw_handle)`. Preserve the surrounding command behavior (what it does with the returned dir).
### T007 — Migrate `mission.py:1327` + `:1378`
- `:1327` `_find_feature_directory`: same replacement. `:1378` `.is_dir()` existence probe: route the path-derivation through the seam (or, if it only needs existence, use the seam's resolved dir + `.exists()`); preserve the probe's intent.
### T008 — Migrate `decision.py:464` (D-6 consolidation)
- `cmd_verify`: replace the D-6 factory-boundary bootstrap with the seam call. Note in the commit that this drains the **D-6** allowlist entry (a consolidation), not a #2046 residual — WP05 confirms the drain by re-derivation.
### T009 — Behavior-preserving verify (NFR-002)
- For each of the 3 CLIs: a focused test (in an existing CLI test module, or assert inline) confirming `<slug>-<mid8>` and full-`mission_id` handles resolve the SAME dir as before. (The bare-slug coord e2e is WP06; the equivalence-cell flip is WP04.)

## Branch Strategy
Planning/base + merge target: `feat/read-side-surface-resolver-adoption`. Worktree per lane. Depends **WP01** (the seam).

## Definition of Done
- [ ] All 4 raw-join bootstraps at the 3 files replaced by the seam; no `KITTY_SPECS_DIR / raw_handle` join remains in these files.
- [ ] Behavior-preserving for non-bare-slug handles (verified).
- [ ] ruff + mypy --strict clean; existing context/mission/decision test suites pass.

## Risks / Reviewer guidance
- **Risk**: a site relied on a subtle detail of its old bootstrap (e.g. the `.is_dir()` probe's exact semantics). Verify each migrated site's command still behaves identically for non-bare-slug.
- **Reviewer**: confirm zero raw `KITTY_SPECS_DIR/<handle>` joins remain in the 3 files; confirm the seam is the single call; spot-check `<slug>-<mid8>` resolution unchanged.

## Activity Log

- 2026-06-20T16:36:52Z – claude:opus:python-pedro:implementer – shell_pid=2351526 – Assigned agent via action command
- 2026-06-20T16:54:52Z – claude:opus:python-pedro:implementer – shell_pid=2351526 – 4 raw-join CLIs (3 #2046 + decision D-6) → seam; mission.py:1378 via primary_feature_dir_for_mission (preserves #1718 finalize-reads-primary); lane 7957a832c. NOTE: pruned 4 stale allowlist entries in WP05-owned test (staleness gate); 2 line-drift failures left for WP05
- 2026-06-20T16:55:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=2392474 – Started review via action command
- 2026-06-20T17:02:20Z – user – shell_pid=2392474 – reviewer-renata APPROVE: 4 raw-joins→seam, mission.py:1378 correctly via primary_feature_dir_for_mission (#1718-safe), equivalence tests real, WP05-owned allowlist prune forced+surgical, pre-existing failures baseline-confirmed

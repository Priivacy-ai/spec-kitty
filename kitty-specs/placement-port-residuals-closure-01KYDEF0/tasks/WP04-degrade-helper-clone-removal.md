---
work_package_id: WP04
title: Degrade helper + verbatim-clone removal
dependencies: []
requirement_refs:
- FR-005
planning_base_branch: placement-port-residuals
merge_target_branch: placement-port-residuals
branch_strategy: Planning artifacts for this mission were generated on placement-port-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into placement-port-residuals unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-placement-port-residuals-closure-01KYDEF0
base_commit: 485311ee629cbe7bb4fcb57fba43e3316f02bfb2
created_at: '2026-07-26T20:47:55.789711+00:00'
subtasks:
- T017
- T018
- T019
- T020
history:
- at: '2026-07-25T21:12:34Z'
  actor: tasks
  note: WP created from IC-06a (FR-005, mechanical clone removal)
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent:
- src/mission_runtime/write_target_degrade.py
- tests/mission_runtime/test_write_target_degrade.py
execution_mode: code_change
model: claude-haiku-4-5-20251001
owned_files:
- src/mission_runtime/write_target_degrade.py
- src/mission_runtime/__init__.py
- src/specify_cli/events/decision_log.py
- src/specify_cli/git/bookkeeping_commit.py
- tests/mission_runtime/test_write_target_degrade.py
- tests/architectural/test_mission_runtime_surface.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading anything else**, load `python-pedro` (role `implementer`) via `/ad-hoc-profile-load`;
adopt its directives/tactics and state which you applied. Then proceed.

## Objective

Extract ONE kind-parameterized `resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref)`
in `src/mission_runtime/` that unifies **port-resolution + the `_mission_meta_exists` pre-gate** (NOT the degrade
policy), and route the TWO verbatim `_mission_meta_exists` clones through it, deleting the clones (SC-004).

Read first: `spec.md` (FR-005, C-004), `plan.md` (IC-06a), `contracts/degrade-and-read-hygiene.md` (C-DEGRADE-1).
This WP is IC-06a only — `status_transition` is WP05.

## Context

- Verbatim clones (byte-identical): `events/decision_log.py:57-80` + `git/bookkeeping_commit.py:115-138`
  (`_mission_meta_exists`).
- The three sites have THREE distinct null-`degrade_ref` policies — do NOT flatten them:
  - `decision_log._resolve_commit_target` (:173): fail-open → `return CommitTarget(ref=destination_ref)`.
  - `bookkeeping_commit._resolve_bookkeeping_commit_target` (:150): fail-closed → `raise ActionContextError` when branch is None.
  - (`status_transition` is WP05.)
- The helper unifies resolution + the pre-gate; `degrade_ref` is **caller-computed** so each site keeps its policy.

## Subtasks

### T017 — Red-first (behavioral, NOT a scaffold/mock)
In `tests/mission_runtime/test_write_target_degrade.py`, assert the **observable outcomes through the public
entry points** (do NOT assert the helper symbol exists or mock it — an ImportError/mock RED is a scaffold, not a
contract): in the no-`meta.json` bootstrap window, `decision_log`'s resolve returns `CommitTarget(ref=destination_ref)`
(fail-open) and `bookkeeping_commit`'s resolve **raises `ActionContextError`** when its branch is None (fail-closed).
The durable fake-proof is these two behavioral pins + SC-004's grep, not a wiring red. Confirm RED where applicable.

### T018 — Extract the helper (+ public-surface lockstep)
Create `src/mission_runtime/write_target_degrade.py` with
`resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref) -> CommitTarget`:
- pre-gate via `_mission_meta_exists` semantics (mission bootstrapped?),
- else `resolve_placement_only(repo_root, mission_slug, kind=kind)` inside a typed-exception guard,
- on degrade return `CommitTarget(ref=degrade_ref)`.
- **kind-parameterized** (C-004): coord kinds resolve to the coord ref, primary kinds to the primary home — never flatten coord onto PRIMARY.
- **Export lockstep (MR-1 gate)**: consumers outside `mission_runtime` MUST import `from mission_runtime import resolve_write_target_or_degrade` (importing the submodule directly reds `test_mission_runtime_surface` MR-1). So add the symbol to `src/mission_runtime/__init__.py` (import + `__all__`) **AND** to `_PUBLIC_SURFACE` in `tests/architectural/test_mission_runtime_surface.py` **in the same commit** — the `__all__ == _PUBLIC_SURFACE` assert reds otherwise.

### T019 — Migrate the two clones
Route `decision_log._resolve_commit_target` (pass `degrade_ref=destination_ref`) and
`bookkeeping_commit._resolve_bookkeeping_commit_target` (compute `degrade_ref` = its branch; keep its raise
for the None case BEFORE/around the call so the fail-closed contract is preserved) through the helper. **Delete
both verbatim `_mission_meta_exists` defs.**

### T020 — Verify
`grep` proves 0 verbatim `_mission_meta_exists` clones remain (SC-004). Red-first test green. `ruff` + `mypy --strict`
clean (mind the `follow_imports=skip` narrowing the clones carried — re-narrow in the helper if needed, no `# type: ignore`).

## Branch Strategy
Planning base / merge target `placement-port-residuals`. Worktree per `lanes.json` via
`spec-kitty agent action implement WP04 --agent claude`. Lane B; WP05 depends on this.

## Definition of Done
- [ ] One helper in `mission_runtime`; both clones deleted; SC-004 "0 verbatim clones" proven.
- [ ] Each site keeps its fail-open / fail-closed degrade policy (degrade_ref caller-computed).
- [ ] Helper exported via `mission_runtime/__init__.py` `__all__` AND `_PUBLIC_SURFACE` (MR-1 lockstep) — surface test green.
- [ ] Helper kind-parameterized; red-first test asserts observable outcomes (not a mock); ruff/mypy clean.

## Risks / reviewer guidance
- Do NOT fold the three degrade POLICIES into the helper — only resolution + pre-gate are shared.
- Reviewer: confirm bookkeeping still raises when branch is None; confirm decision_log still fail-opens; confirm kind-parameterization.

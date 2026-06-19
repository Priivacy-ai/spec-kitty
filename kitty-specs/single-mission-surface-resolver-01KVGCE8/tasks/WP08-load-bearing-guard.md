---
work_package_id: WP08
title: Load-bearing architectural guard
dependencies:
- WP01
- WP06
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
agent: claude
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: WP authored from plan IC-07 (FR-004); clone 01KVFTFV guard.
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_single_mission_surface_resolver.py
create_intent:
- tests/architectural/test_single_mission_surface_resolver.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- tests/architectural/test_single_mission_surface_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Clone the 01KVFTFV load-bearing guard for surface resolution: a `tests/architectural/` test, anchored on WP01's audited-surface inventory, that FAILS when a new `raw-bypass` join (`repo_root/KITTY_SPECS_DIR/<slug>` outside the canonical resolver/delegator set) is introduced — proven load-bearing. (IC-07; FR-004, SC-002)

## Context
- WP01 produced `tests/architectural/surface_resolution_audit/audited-surfaces.md` + `audit.py` — anchor on THAT inventory (not a blanket `Path /` matcher).
- Runs on the collapsed tree (WP06 done), so it is green; the existing `tests/architectural/test_topology_resolution_boundary.py` is a sibling pattern.

## Subtasks
### T030 — Implement the guard
- `tests/architectural/test_single_mission_surface_resolver.py`: import/reuse the WP01 `audit.py`; assert every audited surface routes the canonical resolver/delegator; zero `raw-bypass` rows remain. Anchor strictly on the inventory.
### T031 — Load-bearing self-test (two mutations)
- (a) Real-code mutation: inject a `repo_root / KITTY_SPECS_DIR / mission_slug` raw join into an actual audited source file → the guard FLAGS it; revert → clears. (b) Coverage assertion: the inspected surface set is non-empty AND equals the WP01 inventory. Record both mutation results in the WP history.
### T032 — Gate placement + full run
- Confirm the guard is collected by the architectural suite (CI core-misc); `PWHEADLESS=1 python -m pytest tests/architectural/ -p no:cacheprovider -q` green on the collapsed tree; ruff + mypy --strict clean.

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends **WP01** (inventory) + **WP06** (collapsed state).

## Definition of Done
- [ ] Guard anchored on WP01's inventory (not a blanket heuristic); zero raw-bypass on the collapsed tree.
- [ ] Load-bearing proven: real-code raw-bypass mutation flags; coverage assertion non-empty == inventory.
- [ ] Green in the architectural suite; ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk**: a vacuous guard (matches nothing) — the coverage assertion + real-code mutation are the antidote; insist the self-test bites.
- **Reviewer**: independently inject a raw-bypass join into a real audited file and confirm the guard catches it.

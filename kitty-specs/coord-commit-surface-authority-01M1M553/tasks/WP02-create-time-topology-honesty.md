---
work_package_id: WP02
title: Create-time topology honesty (#2533)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-006
planning_base_branch: fix/coord-commit-surface-authority
merge_target_branch: fix/coord-commit-surface-authority
branch_strategy: Planning artifacts for this mission were generated on fix/coord-commit-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/coord-commit-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
history:
- at: '2026-09-03T00:00:00+00:00'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/regression/test_coord_topology_no_strand.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_create.py
- src/specify_cli/core/mission_creation.py
- tests/specify_cli/cli/commands/agent/test_mission_create.py
- tests/regression/test_coord_topology_no_strand.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile via `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`); apply and state what you applied. Stay within `owned_files`.

## Objective

Stop minting redundant coordination topology. A `--pr-bound` mission created with `--start-branch <unprotected feature branch>` must yield `SINGLE_BRANCH`, not `COORD` — eliminating the stranded coord branch that produced the #2533 split-brain and the B16-clause-2 "cross-contamination" appearance (research D-002).

Read first: [contracts/authoritative-surface.md](../contracts/authoritative-surface.md) §1, [research.md](../research.md) D-001 locus 1 / D-002, [plan.md](../plan.md) DD-2. **Depends on WP01** (`coord_topology_reachable`).

## Key constraint (squad-critical)
Key on the **primary TARGET branch's** protection, NOT the current checkout. This is an **insertion into the `pr_bound` arm** of `_resolve_default_topology_phase` (`mission_create.py:391`) — do **not** rewrite the function; preserve the `None`-guard arm (`:393-394`) and the non-pr-bound `current==primary → COORD` arm (`:399-401`).

## Subtasks

### T005 — Consume `coord_topology_reachable` in `_resolve_default_topology_phase`
`mission_create.py:373-401`. Replace the bare `if pr_bound: return COORD` (line 391) with:
```python
if pr_bound:
    primary_branch = resolve_primary_branch(repo_root)
    primary_protected = ProtectionPolicy.resolve(repo_root).is_protected(primary_branch)
    current_is_primary = current_branch == primary_branch
    return MissionTopology.COORD if coord_topology_reachable(pr_bound, primary_protected, current_is_primary) else MissionTopology.SINGLE_BRANCH
```
- `ProtectionPolicy` import is available (used identically in `tasks_shared.py:322`); `resolve_primary_branch` is already lazily imported in this function.
- Keep the existing `repo_root is None or current_branch is None → COORD` fail-safe arm ahead of this.

### T006 — Thread topology through `create_mission_core`
`core/mission_creation.py` — confirm the resolved topology flows through to `topology_mints_coordination_branch` (no coord branch minted for SINGLE_BRANCH). No new logic; just verify/adjust threading. `pr_bound` remains persisted separately in `meta.json` (merge/finalize gate on `coordination_branch` presence, not on `pr_bound⇒coord` — so SINGLE_BRANCH is coherent downstream).

### T007 — Freeze the tripwire test `[P]`
`tests/specify_cli/cli/commands/agent/test_mission_create.py:455` — `test_create_pr_bound_on_non_primary_branch_still_defaults_to_coord` (pr-bound on `feature/my-fix`, `--target-branch main`). With target-protection keying this MUST stay green (target `main` is protected → still COORD). If it flips, you keyed on the checkout, not the target — fix the keying. Add an assertion/comment documenting why it stays green.

### T008 — Regression: no coord branch on pr-bound + unprotected `[P]`
`tests/regression/test_coord_topology_no_strand.py` (NEW): create a `--pr-bound --start-branch fix/x` mission on an unprotected primary; assert `topology == SINGLE_BRANCH`, `coordination_branch` absent from meta, and `git branch --list 'kitty/*'` empty. This asserts the mint DECISION (not the absence of stranding), closing #2533 and the B16-c2 appearance by construction. Also add a two-concurrent-missions variant to prove no stranded/mislabelled coord branch.

## Branch Strategy
Base/merge: `fix/coord-commit-surface-authority`. One lane; worktree from `lanes.json`.

## Definition of Done
- `--pr-bound --start-branch <unprotected>` → SINGLE_BRANCH, no coord branch minted.
- Tripwire T007 green (target-protection keying proven).
- Regression T008 green (single + concurrent).
- `ruff`/`mypy` clean, no suppressions. Full existing `test_mission_create.py` green.

## Reviewer Guidance
- Confirm keying is on primary-**target** protection (T007 is the proof).
- Confirm the other COORD arms are preserved (non-pr-bound-on-primary still COORD).
- Confirm no downstream merge/finalize breakage (they gate on `coordination_branch` presence).

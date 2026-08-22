---
work_package_id: WP05
title: '#3536 no-coord protected-branch refusal fix'
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: rc3-lane-allocation-single-seam-01M0GGX8
merge_target_branch: rc3-lane-allocation-single-seam-01M0GGX8
branch_strategy: Planning artifacts for this mission were generated on rc3-lane-allocation-single-seam-01M0GGX8. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-lane-allocation-single-seam-01M0GGX8 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-lane-allocation-single-seam-01M0GGX8
base_commit: 2520e7ad4243857b18f3b6c26eb9e14df33b855a
created_at: '2026-08-22T06:43:59.237375+00:00'
subtasks:
- T017
- T018
- T019
- T020
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_3536_no_coord_remedy.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/policy.py
- src/specify_cli/coordination/commit_router.py
- tests/specify_cli/coordination/test_3536_no_coord_remedy.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objective

Fix the un-followable #3536 remedy: on a `lanes`/`single_branch` topology with a protected `target_branch`,
the `PROTECTED_BRANCH_REFUSED` refusal tells the operator to "target the coordination branch" — but that
topology mints no coord branch. Emit an **accurate, followable** remedy instead (FR-005). This is the
mission's only net-new user-facing behavior. Depends on **WP01** (the authoritative topology predicate
that supplies the no-coord answer). Cross-reference epic **#2739** (same protected-primary seam) so the two
fixes converge.

## Context

- Refusal site: `src/specify_cli/coordination/policy.py:225-236` — the `Refused(error_code=
  PROTECTED_BRANCH_REFUSED, message="… Bookkeeping commits must target the coordination branch.",
  next_step="Re-run … through the coordination transaction …")`.
- **Keep `commit_guard.evaluate` ref-only / environment-free (C-GUARD-3a).** The topology fact lives
  OUTSIDE the ref-only guard; supply it at the `Refused` construction site.
- Coupling: `src/specify_cli/coordination/commit_router.py` decides routing and calls the policy; it holds
  (or can resolve) the topology / coord-availability. Thread that fact to the refusal.
- Contract: `contracts/topology-predicate-and-3536.md` (Part B, INV-3536-1..3).

## Subtasks

### T017 — thread coord-availability into the refusal
At the `PROTECTED_BRANCH_REFUSED` construction, obtain whether the mission's topology has a coordination
branch (via the authoritative predicate / `coordination_branch` presence — the WP01 authority, NOT a fresh
local `coordination_branch is None` check). Pass it into the branch below. Do not change `evaluate`.

### T018 — branch the remedy
- **coord-available topology** → keep the current message + "re-run through the coordination transaction"
  (unchanged — INV-3536-2 regression guard).
- **no-coord topology** (`lanes`/`single_branch`) → emit an accurate, followable remedy: name the real
  destination the bookkeeping should use, OR direct the operator to the existing `ProtectionState` escape
  hatch (declare the target unprotected for this repo). **Never** the "coordination branch" instruction.

### T019 — commit_router coupling + #2739 convergence
Ensure `commit_router` passes the topology fact to the policy (the one coupling point). Confirm the
no-coord answer is exposed via the shared predicate so #2739's sub-issues consume the SAME answer
(INV-3536-3) — do not mint a parallel local topology check in `policy.py`. Add a comment cross-referencing
#2739.

### T020 — red-first tests (`tests/specify_cli/coordination/test_3536_no_coord_remedy.py`)
- INV-3536-1: a `lanes`/`single_branch` mission with a protected `target_branch` hitting the refusal gets a
  remedy that does NOT mention "the coordination branch" and names a real, followable action.
- INV-3536-2: a coord-topology mission's refusal remedy is UNCHANGED.
- INV-3536-3: the no-coord answer is sourced from the shared predicate, not a local `policy.py` check.

## Definition of Done
- The no-coord refusal remedy is accurate + followable; coord-topology remedy unchanged.
- `evaluate` stays ref-only/env-free; no parallel topology check minted in `policy.py`.
- New tests pass; `.venv/bin/ruff check .` + `.venv/bin/mypy src/` clean; existing policy/commit_router
  tests green.
- `.venv/bin/python -m pytest tests/specify_cli/coordination/ -k "3536 or protected_branch_refused or no_coord" -q` green.

## Risks
- Leaking topology into the ref-only guard (mitigated: thread at the refusal-construction site).
- Diverging from #2739 (mitigated: single shared no-coord answer, INV-3536-3).

## Reviewer Guidance
Confirm the remedy is genuinely followable on a lanes/single-branch mission, `evaluate` is untouched, the
topology fact flows from the WP01 authority (not a new local check), and the coord-topology path is a
pinned regression.

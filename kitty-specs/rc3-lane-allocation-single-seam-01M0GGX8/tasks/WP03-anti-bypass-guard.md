---
work_package_id: WP03
title: Anti-bypass guard (recurrence prevention)
dependencies:
- WP02
- WP04
requirement_refs:
- FR-007
planning_base_branch: rc3-lane-allocation-single-seam-01M0GGX8
merge_target_branch: rc3-lane-allocation-single-seam-01M0GGX8
branch_strategy: Planning artifacts for this mission were generated on rc3-lane-allocation-single-seam-01M0GGX8. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-lane-allocation-single-seam-01M0GGX8 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-lane-allocation-single-seam-01M0GGX8
base_commit: 2520e7ad4243857b18f3b6c26eb9e14df33b855a
created_at: '2026-08-22T06:46:34.348138+00:00'
subtasks:
- T014
- T015
- T016
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_lane_allocation_single_seam.py
execution_mode: code_change
owned_files:
- tests/architectural/test_lane_allocation_single_seam.py
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

Ship the structural **anti-bypass guard** (FR-007): a `tests/architectural/` test that fails when a new
allocation route computes a parent ref inline, or a new read-degrade `try/except` is added, without routing
through the seam — naming the offending `file:line`. This is the mission's **recurrence guarantee**.

**Depends on WP02 (the allocation seam) AND WP04 (the read companion + migration)** — the guard asserts
both. It may be *authored* red-first before them, but only *approved* after both land.

## Context

- Contract: `contracts/anti-bypass-guard.md` (positive def-use, non-vacuity, allowlist criterion).
- Seam symbol (WP02): `resolve_lane_base_or_refuse` in `src/specify_cli/lanes/worktree_allocator.py`.
  Creation calls: `_create_lane_worktree`, `_ensure_mission_branch`.
- Read companion (WP04): `resolve_read_dir_or_degrade` in `src/mission_runtime/read_dir_degrade.py`.
- Mirror the existing architectural guard style (`tests/architectural/test_shared_package_boundary.py`).
- **Anti-fakeability (post-plan squad, debugger MED):** do NOT key on the literal spelling
  `coordination_branch if … else mission_branch` — assert POSITIVELY via AST def-use that every parent-ref
  argument to a creation call traces to a `resolve_lane_base_or_refuse` return. Anchor on symbols.

## Subtasks

### T014 — allocation single-seam check (FR-001/002)
In `tests/architectural/test_lane_allocation_single_seam.py`, `ast`-parse `worktree_allocator.py` and
assert: (a) every value flowing into a `_create_lane_worktree`/`_ensure_mission_branch` parent argument, on
every route, has its data-dependency origin in a `resolve_lane_base_or_refuse` call; (b) each of the four
`LaneAllocationRoute` branches reaches the seam (or raises `UnhonorableBaseError` via it). No other function
derives a lane parent ref.

### T015 — read-degrade family check + allowlist (FR-006/007)
Assert every read-side degrade `try/except` around a coord-surface read either calls
`resolve_read_dir_or_degrade` or is on an explicit allowlist. Seed the allowlist with the WP04 bespoke /
pass-through sites, each carrying the **acceptance-criterion** rationale (names the failed strategy + why):
- `status/aggregate.py` — "fails DEGRADE_TO_*/ZERO_EVIDENCE (no single degrade dir) and FAIL_CLOSED (must
  re-wrap StatusReadPathNotFound→CoordAuthorityUnavailable while re-raising CoordinationBranchDeleted, #1848)".
- `cli/commands/agent/status.py:154/:195` — "FAIL_CLOSED pass-through; caller owns typer.Exit".
- `cli/commands/_review_cycle_reconcile_doctor.py` — "absorb-before-read, not a resolve-then-degrade shape".
An entry with no failed-strategy reason must itself fail the test (anti-rubber-stamp).

### T016 — deterministic non-vacuity
Parse a **synthetic bypassing function** from an in-test AST fixture (a Python source string that computes
a parent ref inline / adds an un-allowlisted degrade `try/except`) and assert the checker flags THAT
fixture's `file:line` with the right rule. Then run the checker over the live modules and assert clean.
This proves the checker detects bypasses without relying on a hand-introduced temp edit.

## Definition of Done
- `test_lane_allocation_single_seam.py` exists; passes against the WP02+WP04 end state.
- The synthetic-fixture assertions prove non-vacuity for both the allocation and read-degrade checks.
- `.venv/bin/python -m pytest tests/architectural/test_lane_allocation_single_seam.py -q` green.
- `ruff` + `mypy` clean on the new test.

## Risks
- Fakeable check (mitigated: positive def-use + synthetic fixture). Allowlist rubber-stamp (mitigated:
  each entry must name a failed strategy + reason). AST brittleness — anchor on symbols, not line numbers.

## Reviewer Guidance
Confirm the checks are positive/structural (not substring greps), that removing the seam call in a fixture
turns the guard red, and that every allowlist entry carries a checkable failed-strategy rationale.

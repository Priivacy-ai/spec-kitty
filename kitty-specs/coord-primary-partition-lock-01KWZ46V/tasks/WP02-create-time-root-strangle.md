---
work_package_id: WP02
title: Create-time root strangle (unowned bullseye)
dependencies:
- WP01
requirement_refs:
- C-001
- C-006
- FR-004
- NFR-004
tracker_refs: []
planning_base_branch: design/coord-primary-partition-lock
merge_target_branch: design/coord-primary-partition-lock
branch_strategy: Planning artifacts for this mission were generated on design/coord-primary-partition-lock. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-primary-partition-lock unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1607768"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/mission_creation.py
create_intent:
- tests/specify_cli/core/test_mission_creation_placement.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/mission_creation.py
- tests/specify_cli/core/test_mission_creation_placement.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` (implementer) via `/ad-hoc-profile-load` before anything else. Then read
`spec.md`, `plan.md` (IC-02), `research.md` (D5), and `contracts/seam-api.md`. This WP depends
on **WP01** (the seam must exist) — implement via `spec-kitty agent action implement WP02 --agent claude`.

## Objective

Route the **create-time split-brain root** — `mission_creation.py:176` (`_commit_feature_file`)
— through the seam. Today it commits the spec (a primary/planning artifact) via
`CommitTarget(ref=current_branch)`, deriving the destination from the current checkout. This is
the single highest-leverage unowned target. **Red-first (C-006).**

## Context

- The spec is a `SPEC` kind → primary partition. Its commit destination must come from
  `seam.write_target(SPEC)`, not the checkout.
- This is the root the whole mission's Context section blames; it is not caught by the existing ratchet.

## Subtasks

### T006 — Red-first reproduction
- Write a failing test in `tests/specify_cli/core/test_mission_creation_placement.py` that drives
  `_commit_feature_file` (via the real `mission create` entry point) and asserts the spec commit's
  destination is the **partition-correct** surface — proving it currently derives from the current
  checkout (red against pre-fix code). Cover a coord-routing mission where checkout ≠ target.

### T007 — Route through the seam
- Replace the `CommitTarget(ref=current_branch)` construction with `seam.write_target(SPEC)`.
- No behavior change to *which* surface a `SPEC` resolves to (it's primary either way for planning) —
  the point is that the decision now comes from the seam, not the checkout (C-001). Verify parity
  for coord and non-coord topologies.

### T008 — Green + regression
- The T006 test passes. Add regression coverage: coord-routing mission and `SINGLE_BRANCH`/`LANES`
  mission both land the spec on primary via the seam; the create flow no longer reads `current_branch`
  for placement.

### T009 — Campsite (Sonar)
- Hoist `'mission_type'` (×3) and `'created_at'` (×3) to module constants (small file, low-risk).

## Campsite (Sonar issues in owned files)

| File | Rule | Location | Class | Action |
|------|------|----------|-------|--------|
| `core/mission_creation.py` | S1192 | `'mission_type'` ×3, `'created_at'` ×3 | SAFE | Hoist to module constants |

## Branch Strategy

Planning base / merge target: `design/coord-primary-partition-lock` (→ operator PR to `main`).
Execution worktree per computed lane from `lanes.json` — enter via the implement command; do not
reconstruct paths. **Depends on WP01** — branch from the correct base as the command directs.

## Definition of Done

- T006 red-before, green-after; `_commit_feature_file` obtains its destination from `seam.write_target(SPEC)`.
- Regression green for coord + non-coord; no `current_branch` read in the placement path.
- `ruff` + `mypy` clean; ≤15 complexity; constants hoisted.

## Risks & Reviewer guidance

- Create-time is load-bearing (every mission) — reviewer must confirm no lifecycle regression (mission create still succeeds end-to-end, protected-primary path still safe).
- Confirm the red test genuinely failed against pre-fix code (not a vacuous assertion).
- This site is one of the `CommitTarget(ref=<checkout>)` grammar targets WP07 will lock — leave it seam-routed so WP07's ratchet stays green.

## Activity Log

- 2026-07-07T22:45:01Z – claude:sonnet:python-pedro:implementer – shell_pid=1503078 – Assigned agent via action command
- 2026-07-07T23:04:21Z – claude:sonnet:python-pedro:implementer – shell_pid=1503078 – Ready; ruff diff-scoped exit 0; red-first proven
- 2026-07-07T23:05:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=1607768 – Started review via action command
- 2026-07-07T23:10:59Z – user – shell_pid=1607768 – Review passed: seam-routing confirmed (_commit_feature_file derives destination from placement_seam.write_target(SPEC); get_current_branch retained only as git-repo guard). Red-first GENUINE and non-vacuous: neutralizing the fix reproduced ref='main' (checkout) vs expected 'design/coord-target' (seam) on both coord + single_branch mismatch tests, checkout==target case stayed green. C-002 mapping unchanged (SPEC->primary target_branch for every topology; decision source changed, not surface). Write-side ratchet green (no CommitTarget(ref=<checkout>) at this site). No lifecycle regression: existing create suites (fire_once, specify_started) pass end-to-end with real safe_commit; contextlib.suppress guarantees create never hard-fails. Campsite done (_META_KEY_MISSION_TYPE/_CREATED_AT hoisted). ruff+mypy clean. Changes confined to owned files.

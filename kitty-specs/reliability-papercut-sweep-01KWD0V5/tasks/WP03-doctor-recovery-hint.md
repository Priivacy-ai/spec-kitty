---
work_package_id: WP03
title: 'Doctor coordination recovery hint + #1890 recurrence guard'
dependencies:
- WP02
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: fix/reliability-papercut-sweep
merge_target_branch: fix/reliability-papercut-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/reliability-papercut-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reliability-papercut-sweep unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "878200"
history:
- at: '2026-06-30T20:12:14Z'
  actor: claude
  note: WP authored from IC-03; depends on WP02 (shared _coordination_doctor.py, C-002)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/_coordination_doctor.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_coordination_doctor.py
- src/specify_cli/cli/commands/_workspace_husk_doctor.py
- tests/specify_cli/cli/commands/test_doctor_coordination.py
- tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries before proceeding.

## Objective

Ensure every recovery command `doctor coordination` recommends both **exists** and **performs
the recovery it promises**, add a standing regression test guarding the recurred #1890
dead-command class, and handle a stale-behind-tip coordination worktree. (FR-003 / #2240)

## Context

- **Depends on WP02** — both edit `_coordination_doctor.py`; WP02 lands first (C-002). This WP
  owns the entire doctor surface, including the user-facing never-created hint that pairs with
  WP02's classification fix.
- `src/specify_cli/cli/commands/_coordination_doctor.py` — `_WORKSPACE_RECOVERY_CMD` (~:65) +
  the findings for `COORDINATION_WORKTREE_MISSING` (~:296-300) and branch-mismatch (~:223-226).
  The literal phantom `agent worktree repair` was removed under **#1890** (`ecf45f52c`) — but
  #2240 recurred: the recommended `doctor workspaces --fix` only *removes* `.worktrees/` husks
  (`_workspace_husk_doctor.py:53-86`) — it cannot RECREATE a missing coord worktree.
- `src/specify_cli/cli/commands/_workspace_husk_doctor.py` — `fix_workspace_husks`.
- Precedent: **#1890** (closed, same class). See-also **#2017** (workflow-guard friction).

## Subtasks

### T010 — Red-first: recovery hint EFFICACY (not mere existence)
**IMPORTANT (anti-laziness):** the literal #1890 phantom is already removed and `doctor workspaces
--fix` *exists*, so an existence-only assertion is GREEN today and would not exercise #2240. Anchor
the red-first on **efficacy**: for a missing/never-created coordination worktree, assert that
following the recommended recovery actually resolves the state (worktree recreated, or the
never-created case routed to flatten). On pre-fix code the recommendation (`doctor workspaces --fix`,
which only *removes* `.worktrees/` husks — it cannot recreate a coord worktree) does NOT resolve the
state → RED. Keep a SECONDARY standing invariant that every recommended command exists (guards the
#1890 class), but it is not the red-first.

### T011 — Fix the recovery hint to a real, working path
In `_coordination_doctor.py`, make the `COORDINATION_WORKTREE_MISSING` / never-created
recommendation point at a recovery that actually performs the stated action (recreate the coord
worktree, or — for a never-created branch — lead with flatten, consistent with WP02). No
recommendation may name a command that doesn't exist or that can't do what the text claims.

### T012 — Handle stale-behind-tip coordination worktree
Add handling/diagnosis for a coordination worktree that exists but is stale (behind tip) — the
sub-ask in #2240 — routing to the correct refresh/recovery path in `_workspace_husk_doctor.py`.

### T013 — Re-pin the doctor tests
Update `test_doctor_coordination.py` (the `next_step`/recovery-hint assertions, incl. the WP05/#1890
comment at ~:132) and the golden snapshot `test_doctor_cli_surface_golden.py:155` to the new hint
text. Re-pin (topology-aware), do not delete coverage.

## Branch Strategy

Planning/base + merge target: `fix/reliability-papercut-sweep`. Worktrees per `lanes.json`.
**This WP depends on WP02** — run it after WP02 is approved/done:
`spec-kitty agent action implement WP03 --agent claude`.

## Definition of Done

- T010 red-first targets EFFICACY (recommended recovery resolves the missing/never-created worktree
  state): RED on pre-fix code, GREEN after. Secondary invariant (every recommended command exists)
  also green — guards the #1890 class.
- Every doctor-coordination recommendation exists and performs its stated recovery.
- Stale-behind-tip worktree handled.
- Both doctor tests re-pinned (no lost coverage).
- ruff + mypy clean; complexity ≤ 15.

## Reviewer guidance

Confirm the standing regression test actually parses recommendation strings and checks them
against the live CLI (not a hardcoded allow-list that could rot). Confirm the recommended recovery
genuinely recreates/handles the worktree (the #2240 substance), not just that the string exists.
Verify the never-created hint is consistent with WP02's classification.

## Activity Log

- 2026-06-30T21:50:00Z – claude:sonnet:python-pedro:implementer – shell_pid=704116 – Assigned agent via action command
- 2026-06-30T22:28:01Z – claude:sonnet:python-pedro:implementer – shell_pid=704116 – Ready: efficacy red-first green, recovery resolves the state, tests re-pinned
- 2026-06-30T22:30:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=834474 – Started review via action command
- 2026-06-30T22:38:36Z – user – shell_pid=834474 – Moved to planned
- 2026-06-30T23:06:16Z – claude:opus:reviewer-renata:reviewer – shell_pid=834474 – Cycle 2: added stale-refresh efficacy test (HEAD==tip, STALE cleared); refresh path now covered end-to-end
- 2026-06-30T23:06:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=878200 – Started review via action command

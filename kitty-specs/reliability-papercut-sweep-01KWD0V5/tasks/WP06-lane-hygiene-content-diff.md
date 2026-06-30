---
work_package_id: WP06
title: 'Lane-hygiene guard: content-diff not commit-history'
dependencies: []
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: fix/reliability-papercut-sweep
merge_target_branch: fix/reliability-papercut-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/reliability-papercut-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reliability-papercut-sweep unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "635607"
history:
- at: '2026-06-30T20:12:14Z'
  actor: claude
  note: 'Folded #2274 post-tasks (Lane A); shares tasks.py with WP07 → WP07 sequenced after'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_lane_hygiene_content_diff.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/agent/test_lane_hygiene_content_diff.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries before proceeding.

## Objective

The `kitty-specs`-on-lane hygiene guard must compare by **content** against the planning-branch
tip, not by commit-history (merge-base) diff. After a legitimate planning-branch rebase, a lane
branch shares only an ancient merge-base, so `kitty-specs/` files byte-identical to the planning
tip get falsely flagged as "kitty-specs changes on a lane branch" — a false-positive `move-task`
block clearable only with `--force`, inflating `force_count` and eroding the guard's signal.
(FR-007 / #2274)

## Context

- `src/specify_cli/cli/commands/agent/tasks.py` — `_list_wp_branch_mission_specs_changes` (~:876-913):
  computes `git merge-base HEAD base_branch` (~:877) then `git diff --name-only {merge_base}..HEAD
  -- kitty-specs/` (~:894). That merge-base/commit-history comparison is the defect — no content
  check against the planning tip exists.
- This is **directly relevant to THIS mission**: the planning branch `fix/reliability-papercut-sweep`
  was just rebased onto a refreshed upstream base, so lanes will hit this guard at implement time.
- Occurrence class A3 of #2017. Surfaced during `doc-quality-hardening-2245` (PR #2272).
- **Shares `tasks.py` with WP07** — WP06 owns `tasks.py`; WP07 is sequenced after and makes a small
  documented out-of-map edit to the approval handler.

## Subtasks

### T024 — Red-first: byte-identical kitty-specs flagged after rebase
Add `tests/specify_cli/cli/commands/agent/test_lane_hygiene_content_diff.py`: construct a lane
branch whose `kitty-specs/` content is byte-identical to the planning tip but whose merge-base is
ancient (simulate a planning-branch rebase). Assert the guard currently FLAGS it (false positive).
RED on pre-fix code through the real guard entry point.

### T025 — Content re-check against the planning tip
In `_list_wp_branch_mission_specs_changes`, after the merge-base diff yields candidate paths,
re-check each against the planning-branch tip — `git diff <planning-tip> -- kitty-specs/<file>` —
and drop any path whose content diff is empty. Only genuine divergence from the planning tip
remains flagged (still requires `--force`).

### T026 — Green + force-count guard
Make T024 green; add a counter-assertion that a genuinely-divergent `kitty-specs/` file IS still
flagged (the guard keeps its real signal). Confirm no `force_count` inflation for the
byte-identical case.

## Branch Strategy

Planning/base + merge target: `fix/reliability-papercut-sweep`. Worktrees per `lanes.json`.
Run `spec-kitty agent action implement WP06 --agent claude`. **WP07 depends on this WP** (shared
`tasks.py`) — WP06 lands first.

## Definition of Done

- T024 RED pre-fix, GREEN after.
- Lane-hygiene guard compares `kitty-specs/` by content vs the planning tip; byte-identical files
  after a rebase are not flagged; genuinely-divergent files still are (counter-assertion green).
- ruff + mypy clean; complexity ≤ 15.

## Reviewer guidance

Confirm the fix compares against the **planning tip content**, not just a different ref's history.
Confirm the genuine-divergence counter-assertion holds (the guard isn't neutered). Confirm no edit
outside `tasks.py` + the new test.

## Activity Log

- 2026-06-30T21:22:10Z – claude:sonnet:python-pedro:implementer – shell_pid=590810 – Assigned agent via action command
- 2026-06-30T21:32:40Z – claude:sonnet:python-pedro:implementer – shell_pid=590810 – Ready: content-diff guard, red-first green, genuine divergence still flagged
- 2026-06-30T21:33:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=635607 – Started review via action command
- 2026-06-30T21:41:59Z – user – shell_pid=635607 – reviewer-renata approved; issue-matrix populated

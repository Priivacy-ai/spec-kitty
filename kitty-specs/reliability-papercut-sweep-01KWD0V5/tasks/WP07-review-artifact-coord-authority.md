---
work_package_id: WP07
title: Review-artifact coord authority (approve-over-rejected)
dependencies:
- WP06
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: fix/reliability-papercut-sweep
merge_target_branch: fix/reliability-papercut-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/reliability-papercut-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reliability-papercut-sweep unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "797288"
history:
- at: '2026-06-30T20:12:14Z'
  actor: claude
  note: 'Folded #2275 post-tasks (Lane A); depends on WP06 (shared tasks.py); small out-of-map edit to tasks.py approval handler'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_materialization.py
create_intent:
- tests/specify_cli/post_merge/test_approve_over_rejected_coord_artifact.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_materialization.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- src/specify_cli/review/artifacts.py
- tests/specify_cli/post_merge/test_approve_over_rejected_coord_artifact.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries before proceeding.

## Objective

Close the lane-vs-coord review-artifact authority split: `move-task --to approved` over a
coord-latest `verdict: rejected` must persist an approved review-cycle artifact (or honored
override) in the **coordination** worktree — where the merge gate reads — so a genuinely-approved
terminal WP is not blocked by `REJECTED_REVIEW_ARTIFACT_CONFLICT`. (FR-008 / #2275)

## Context

- **Depends on WP06** (both touch `tasks.py`; WP06 owns it). This WP's edit to the
  `move-task --to approved` handler in `tasks.py` (~:1120-1138) is a **small, documented
  out-of-map edit** — record it with a one-line rationale; WP06 lands first so there is no
  parallel collision.
- The split (verified on current main):
  - Approval guard resolves the artifact dir from `wp.path` (`tasks.py:~1120-1138`) — the lane
    checkout, which has no `review-cycle-*.md` (they live in the coord worktree) — so the
    rejected branch is skipped and approval passes with no override stamped.
  - `_persist_review_artifact_override` (`tasks_materialization.py:~46-67`) writes to `repo_root`
    (lane/main), NOT the coord worktree.
  - Merge gate reads the coord artifact: `post_merge/review_artifact_consistency.py:~13-15,197`
    (`REJECTED_REVIEW_ARTIFACT_CONFLICT` / `terminal_wp_latest_review_artifact_must_not_be_rejected`)
    via `review/artifacts.py:~322-340`. The #1924 override-honoring fires only if the override
    block is present **on the coord artifact** — which the approval path never writes there.
- Sibling **#1817** under epic **#2160** (review-artifact authority unification). Cite #2160.

## Subtasks

### T027 — Red-first: approve-over-coord-rejected → merge gate blocks
Add `tests/specify_cli/post_merge/test_approve_over_rejected_coord_artifact.py`: a terminal WP
whose coord-latest review artifact is `rejected`, then `move-task --to approved`; assert the merge
gate currently FIRES `REJECTED_REVIEW_ARTIFACT_CONFLICT` despite the approved status-lane event.
RED on pre-fix code.

### T028 — Persist the approval where the merge gate READS (read/write symmetry)
On `move-task --to approved` over a coord-latest `rejected`, write a new `review-cycle-<N+1>.md`
(or stamp the honored override) into the **coord** artifact dir. **Resolve that dir the SAME way the
merge gate's caller does** — the gate reads via `find_rejected_review_artifact_conflicts(feature_dir)`
→ `_artifact_dirs_for_wp(feature_dir, wp_id)` (`post_merge/review_artifact_consistency.py:54-55,119`)
where `feature_dir` is the **coord feature_dir** resolved by `cli/commands/review/_lane_gate.py:54`.
NOTE: review-cycle artifacts have **no `MissionArtifactKind`**, so `resolve_planning_read_dir(kind=)`
is not literally invokable for them — resolve the coord feature_dir via the **write-side** resolver,
then write into the `_artifact_dirs_for_wp`-shaped path under it (NOT a hand-built path).
`_persist_review_artifact_override` (`tasks_materialization.py:46`) already imports the
planning-surface seam — extend it to target the coord worktree, guaranteeing byte-for-byte symmetry
with the gate read.

### T029 — Verify the merge gate honors it (+ approval-handler wiring)
Confirm `post_merge/review_artifact_consistency.py` / `review/artifacts.py` treat the new
coord-side approved/override artifact as terminal-not-rejected (honor the existing #1924
`has_complete_override` — do not duplicate it). Make the small documented out-of-map edit to the
`tasks.py` approval handler (`:1120-1121`) so the approve path actually invokes the coord-side
persistence (record the out-of-map rationale in the WP history/PR).

### T030 — Green end-to-end
Make T027 green: approve-over-rejected now merges without the false conflict. Add a counter-assertion
that a genuinely-rejected-latest (no approval) STILL blocks (the gate keeps its real signal).

## Branch Strategy

Planning/base + merge target: `fix/reliability-papercut-sweep`. Worktrees per `lanes.json`.
**Depends on WP06** — run after WP06 is approved/done:
`spec-kitty agent action implement WP07 --agent claude`.

## Definition of Done

- T027 RED pre-fix, GREEN after.
- Approve-over-rejected persists the approved/override artifact in the COORD worktree; merge gate
  no longer false-blocks; a genuine rejected-latest still blocks (counter-assertion green).
- The `tasks.py` approval-handler edit is recorded as a justified out-of-map change (WP06 owns tasks.py).
- ruff + mypy clean; complexity ≤ 15.

## Reviewer guidance

Confirm the artifact is written where the MERGE GATE reads (coord worktree via the kind-aware
seam), not the lane checkout. Confirm the #1924 override is honored, not duplicated. Confirm the
counter-assertion (genuine rejection still blocks) holds. Verify the out-of-map `tasks.py` edit is
minimal and recorded.

## Activity Log

- 2026-06-30T21:44:23Z – claude:sonnet:python-pedro:implementer – shell_pid=677497 – Assigned agent via action command
- 2026-06-30T22:10:54Z – claude:sonnet:python-pedro:implementer – shell_pid=677497 – Ready: approval persisted where gate reads, #1924 honored, red-first green
- 2026-06-30T22:12:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=797288 – Started review via action command

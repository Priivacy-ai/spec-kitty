# Execution Lanes

Spec Kitty uses a lane-based execution model.

- `finalize_tasks` computes `lanes.json` from dependencies, ownership, and predicted surfaces.
- Each lane gets exactly one git worktree and one lane branch.
- Sequential work packages in the same lane reuse that same worktree.
- Independent lanes can run in parallel in separate worktrees.

## Core Rules

1. Planning happens in the primary repository checkout.
2. `spec-kitty implement WP##` requires a valid `lanes.json`.
3. The runtime chooses the lane worktree. Agents do not pick a base branch manually.
4. If a feature computes one lane, the feature uses one worktree.
5. Merge always follows `lane branches -> mission branch -> target branch`.

## Naming

- Mission branch: `kitty/mission-<feature>`
- Lane branch: `kitty/mission-<feature>-lane-a`
- Lane worktree: `.worktrees/<feature>-lane-a/`

## Why This Replaced Per-WP Worktrees

Per-work-package worktrees allowed overlapping work packages to run in parallel and collide at merge time. Execution lanes eliminate that by forcing dependent or overlapping work packages into the same lane, branch, and worktree.

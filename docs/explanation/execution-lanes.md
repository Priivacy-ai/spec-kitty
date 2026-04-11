# Execution Lanes

Spec Kitty uses a lane-based execution model.

- `finalize_tasks` computes `lanes.json` from dependencies, ownership, and predicted surfaces.
- Each lane gets exactly one git worktree and one lane branch.
- Sequential work packages in the same lane reuse that same worktree.
- Independent lanes can run in parallel in separate worktrees.

## Core Rules

1. Planning happens in the primary repository checkout.
2. `spec-kitty agent action implement WP## --agent <name>` requires a valid `lanes.json`.
3. The runtime chooses the lane worktree. Agents do not pick a base branch manually.
4. If a feature computes one lane, the feature uses one worktree.
5. Merge always follows `lane branches -> mission branch -> target branch`.

## Naming

As of mission `083-mission-id-canonical-identity-migration`, every mission carries a ULID
identity (`mission_id`), and branch and worktree names embed the first 8 characters of
that ULID (`mid8`) to guarantee collision-free naming even when two missions share the
same human slug.

- Mission branch: `kitty/mission-<human-slug>-<mid8>`
- Lane branch: `kitty/mission-<human-slug>-<mid8>-lane-a`
- Lane worktree: `.worktrees/<human-slug>-<mid8>-lane-a/`

Example, for a mission with `mission_slug=my-feature` and
`mission_id=01J6XW9KQT7M0YB3N4R5CQZ2EX` (so `mid8=01J6XW9K`):

- Mission branch: `kitty/mission-my-feature-01J6XW9K`
- Lane branch: `kitty/mission-my-feature-01J6XW9K-lane-a`
- Lane worktree: `.worktrees/my-feature-01J6XW9K-lane-a/`

Legacy (pre-083) forms such as `kitty/mission-001-my-feature-lane-a` and
`.worktrees/001-my-feature-lane-a/` remain readable by current tooling but
are no longer the form produced by `implement`. Upgrade via the
[mission identity migration runbook](../migration/mission-id-canonical-identity.md).

## Why This Replaced Per-WP Worktrees

Per-work-package worktrees allowed overlapping work packages to run in parallel and collide at merge time. Execution lanes eliminate that by forcing dependent or overlapping work packages into the same lane, branch, and worktree.

## Parallelism Preservation

`finalize-tasks` assigns WPs to lanes based on two criteria:

1. **File ownership overlap** — WPs that declare no files in common are placed in separate lanes and run in parallel.
2. **Explicit dependencies** — If WP B lists WP A in its `dependencies` field, they are assigned to the same lane and run sequentially (A then B).

When neither criterion forces a merge, the pipeline keeps WPs in separate lanes to maximise parallelism. When a merge is forced, it is recorded in `lanes.json` under the `collapse_report` field:

```json
{
  "collapse_report": [
    {
      "merged_wps": ["WP02", "WP03"],
      "reason": "overlapping owned files: src/foo.py"
    }
  ]
}
```

Each entry in `collapse_report` lists the WPs that were merged into a single lane and the reason (file overlap or explicit dependency). Inspect this field after `finalize-tasks` to understand why two WPs share a lane.

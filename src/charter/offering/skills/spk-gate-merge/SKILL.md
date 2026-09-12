---
name: spk-gate-merge
description: "Merge an accepted Spec Kitty mission safely, preserving git invariants, mission state, and post-merge follow-through."
---

# spk-gate-merge

Use this skill after `spk-gate-accept` passes or when a user asks to merge a
mission.

## Flow

1. Confirm the mission passed accept.
2. Run `/spec-kitty.merge` or the equivalent CLI command.
3. Resolve git/worktree blockers with `spk-admin-git-workflow`.
4. After merge, route to `spk-gate-mission-review`.
5. Then route to `spk-gate-retrospective`.

## Rule

Do not merge rejected, blocked, or partially reviewed work.

---
title: How to Accept and Merge a Mission
description: "How to accept and merge a mission with Spec Kitty 3.2: Use this guide to validate mission readiness and merge to the mission's target branch."
doc_status: active
updated: '2026-06-03'
related:
- docs/guides/install-and-upgrade.md
- docs/guides/keep-main-clean.md
- docs/guides/merge-feature.md
- docs/guides/review-work-package.md
- docs/guides/run-an-autonomous-mission.md
- docs/guides/troubleshoot-merge.md
- docs/guides/use-retrospective-learning.md
---
# How to Accept and Merge a Mission

Use this guide to validate mission readiness and merge to the mission's target branch.

## Prerequisites

- All WPs are `approved` or `done`, with review feedback resolved
- You are in a checkout where the mission can be resolved (repository root checkout or execution workspace)

## Accept the Mission

Run acceptance after the implement-review loop approves every WP and before
merge. This is a readiness nudge for humans and LLMs; merge still performs its
own gates and remains the mission-close operation.

In your agent:

```text
/spec-kitty.accept
```

Or in your terminal:

```bash
spec-kitty accept
```

### What Accept Checks

- All WPs are `approved` or `done`
- Required metadata and activity logs are present
- No unresolved `[NEEDS CLARIFICATION]` markers remain

To run a read-only checklist (in your terminal):

```bash
spec-kitty accept --mode checklist
```

## Merge to the Target Branch

In your agent:

```text
/spec-kitty.merge --push
```

Or in your terminal:

```bash
spec-kitty merge --push
```

By default, `spec-kitty merge` lands in the mission's recorded target branch. Use `spec-kitty merge --target <branch>` only when you intentionally need to override that destination.

For detailed merge options including dry-run, strategies, and cleanup flags, see [Merge a Mission](merge-feature.md).

### When Local `main` Is Not Publishable

Autonomous local runs can leave `main` ahead of or diverged from `origin/main`
with planning, status, review, and orchestration commits. If merge refuses with
`TARGET_BRANCH_NOT_SYNCHRONIZED`, do not reset, rebase, force-push, or push
local `main` only to satisfy the pre-flight.

Open a focused PR from the mission result instead:

```bash
git push -u origin kitty/mission-<mission-slug>
gh pr create --base main --head kitty/mission-<mission-slug> --fill
```

Or create a dedicated PR branch from the mission branch:

```bash
git switch -c kitty/pr/<mission-slug>-to-main kitty/mission-<mission-slug>
git push -u origin kitty/pr/<mission-slug>-to-main
gh pr create --base main --head kitty/pr/<mission-slug>-to-main --fill
```

Prefer squash-merge when the autonomous run accumulated many orchestration
commits. For the full end-to-end path, see
[Run an Autonomous Mission](run-an-autonomous-mission.md).

## After Merge

Complete the following three steps before declaring the mission done.

**1. Mission review** — run the post-merge mission review to confirm spec→code fidelity and FR
coverage:

```bash
# In your agent:
/spec-kitty-mission-review

# Or directly:
spec-kitty agent mission review --mission <handle>
```

**2. Author or verify the retrospective** — under default policy the record was already written
during merge. Verify with:

```bash
cat .kittify/missions/$(jq -r .mission_id kitty-specs/<slug>/meta.json)/retrospective.yaml
```

If the file is absent (for example, an older mission predating 3.2.0), author it now:

```bash
spec-kitty retrospect create --mission <handle>
```

Reserve the noun "capture" for the event-log fact `RetrospectiveCaptured`, not for the
operator verb.

**3. Surface findings** — aggregate across recent missions or inspect proposals for this one:

```bash
# Cross-mission view (read-only aggregation)
spec-kitty retrospect summary

# Preview proposals in this mission's retrospective.yaml (dry-run by default)
spec-kitty agent retrospect synthesize --mission <handle>

# Apply a proposal (requires explicit --apply)
spec-kitty agent retrospect synthesize --mission <handle> --apply <proposal-id>
```

For full details on each command, see
[How to Use Retrospective Learning](use-retrospective-learning.md).

## Merge Strategies

- **Default (merge commit)**: `spec-kitty merge`
- **Squash**: `spec-kitty merge --strategy squash`

Note: Rebase is not supported for multi-workspace missions. Use `merge` or `squash` instead.

## Cleanup

By default, merge removes resolved execution worktrees and deletes the mission branch. Use these flags to keep them (in your terminal):

```bash
spec-kitty merge --keep-worktree --keep-branch
```

## Abandon a Mission (Manual Cleanup)

If you decide to drop a mission without merging, remove its execution worktrees and branches manually.
These steps are safe and reversible until you delete the branch and commit the cleanup.

1. List worktrees to find all workspaces for the mission:
```bash
git worktree list
```

2. Remove each execution worktree for the mission:
```bash
git worktree remove .worktrees/<mission-slug>-lane-a
git worktree remove .worktrees/<mission-slug>-lane-b
```

If a worktree has uncommitted changes you want to discard, use `--force`:
```bash
git worktree remove --force .worktrees/<mission-slug>-lane-a
```

3. Delete the mission branches:
```bash
git branch -D <mission-slug>-lane-a
git branch -D <mission-slug>-lane-b
```

4. Remove the planning artifacts from the repository root checkout (spec/plan/tasks), then commit:
```bash
rm -rf kitty-specs/<mission-slug>
git add kitty-specs/
git commit -m "Remove abandoned mission <mission-slug>"
```

## Troubleshooting

- **Accept reports blockers**: Resolve the listed issues, then rerun `/spec-kitty.accept`.
- **Merge fails**: Ensure your current checkout is clean and the mission resolves correctly.
- **Merge reports `TARGET_BRANCH_NOT_SYNCHRONIZED`**: Use the focused-PR path when local `main` contains autonomous-run history that should not be published directly.
- **Merge is heading to the wrong branch**: Inspect the mission's recorded target branch before retrying, and use `spec-kitty merge --target <branch>` only if you intend to override it.

For detailed troubleshooting including pre-flight failures, conflict resolution, and merge recovery, see [Troubleshoot Merge Issues](troubleshoot-merge.md).

---

## Command Reference

- [Slash Commands](../api/slash-commands.md) - All `/spec-kitty.*` commands
- [CLI Commands](../api/cli-commands.md) - Full CLI reference

## See Also

- [Merge a Mission](merge-feature.md) - Detailed merge workflow
- [Run an Autonomous Mission](run-an-autonomous-mission.md) - End-to-end autonomous run and focused-PR fallback
- [Keep Main Clean](keep-main-clean.md) - Choose a target branch without changing planning location
- [Troubleshoot Merge Issues](troubleshoot-merge.md) - Recovery and conflict resolution
- [Review a Work Package](review-work-package.md) - Required before accept
- [Upgrade to 0.11.0](install-and-upgrade.md) - Breaking changes in v0.11.0

## Background

- [Execution Lanes](../architecture/execution-lanes.md) - Worktree cleanup
- [Git Worktrees](../architecture/git-worktrees.md) - How worktrees work

## Getting Started

- [Your First Feature](your-first-feature.md) - Complete workflow walkthrough

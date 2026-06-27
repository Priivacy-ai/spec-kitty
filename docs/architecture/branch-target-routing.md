---
title: Branch-Target Routing
description: Explanation of how Spec Kitty decides which git branch receives each type of change — planning artifacts, status events, code, and documentation.
doc_status: active
updated: '2026-06-17'
type: explanation
related:
- docs/architecture/execution-lanes.md
- docs/architecture/git-worktrees.md
---
# Branch-Target Routing

When spec-kitty runs a mission with execution lanes, different kinds of changes
land on different branches. This page explains the routing table — which
artefact type goes where and why — plus the **simple case**: what happens when
there are no lanes or coordination branches at all.

## Why branch-target routing exists

Before execution lanes, every change from every work package landed on the same
branch. That worked fine for sequential missions, but breaks down when two work
packages run in parallel: their changes would collide, producing merge conflicts
on files neither WP was supposed to touch.

The routing model solves this by giving each category of change a **dedicated
landing zone**:

- Work-package code stays in an isolated lane branch so two lanes never
  touch each other's files.
- Planning artifacts and status events land on a shared coordination surface so
  every lane can read them without checking out a different branch.
- Shared documentation and the final merge-target stay on the base branch
  so they are accessible from any context.

The routing decision happens automatically. You do not choose a landing branch
manually; spec-kitty resolves the right destination for each category of diff.

## The routing table

| Diff type | Where it lands |
|-----------|----------------|
| Planning artifacts (spec, plan, tasks) | coordination branch |
| Status and task events | coordination branch |
| Lane definitions (`lanes.json`) | coordination branch |
| Code changes | the lane branch (per-WP worktree) |
| Shared documentation | base branch |
| Merge target | base branch |

**Coordination branch** — a branch that acts as the shared visibility surface
for a mission. All lanes read planning artifacts from it; all lanes write status
events to it. It keeps these mission-wide concerns out of the lane branches.

**Lane branch** — the branch checked out inside a lane's worktree. Only the
work packages assigned to that lane write code here. Lane branches are isolated
from each other.

**Base branch** — the mission's base (e.g. `feat/my-mission` or `main`).
Documentation and the final merge target always resolve to base so they are
available regardless of which lane is active.

## The simple case: flat topology (no lanes, no coordination)

When a mission has only one work package and no coordination branch is
configured, every category in the routing table resolves to the **base branch**.
There are no lane worktrees and no coordination surface — spec-kitty runs
exactly as it did before lanes were introduced.

This is the **all-base collapse**: planning artifacts go to base, status goes to
base, code goes to base, documentation goes to base, merge-target is base. The
result is byte-identical to the single-branch workflow from earlier versions of
spec-kitty. No worktree directories are created or read; no coordination branch
is touched.

The flat topology is not a special mode you activate — it is simply what
happens when the routing table has no coordination branch or lane worktrees
declared. If you are running a straightforward, single-threaded mission, you are
already in the simple case.

## How the routing decision is made

spec-kitty consults a **branch-target context object** built from the mission's
`lanes.json` and coordination metadata before any write operation occurs. That
object holds one resolved destination per diff category. Each write site asks
the context object "where should this go?" rather than hard-coding a branch.

Because the context object is the single authority for routing:

- Adding a new diff category never requires touching existing write sites.
- Swapping from flat topology to lane topology is a configuration change in the
  context, not a code change in every write site.
- The simple-case collapse is guaranteed: when the context object has no
  coordination branch and no lane branches, every resolved destination is the
  base branch.

## Relationship to execution lanes

The routing table describes *where* changes land. The execution lanes model
describes *how* work packages are grouped and run in parallel. These two
concerns are complementary:

- Execution lanes allocate work packages to lane branches (the "code" row in
  the routing table).
- Branch-target routing ensures that the coordination surface and base remain
  accessible to all lanes simultaneously.

See [Execution Lanes](execution-lanes.md) for how lanes are computed, how
worktrees are created, and how lane branches merge back to the mission branch.

See [Git Worktrees Explained](git-worktrees.md) for the underlying git mechanism
that makes isolated lane workspaces possible.

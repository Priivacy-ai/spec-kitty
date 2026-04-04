---
name: spec-kitty-git-workflow
description: >-
  Understand how Spec Kitty manages git: what git operations Python handles
  automatically, what agents must do manually, worktree lifecycle, auto-commit
  behavior, merge execution, and the safe-commit pattern.
  Triggers: "how does spec-kitty use git", "worktree management", "auto-commit",
  "who commits what", "git workflow", "merge workflow", "rebase WPs",
  "worktree cleanup", "safe commit".
  Does NOT handle: runtime loop advancement (use runtime-next),
  setup or repair (use setup-doctor), mission selection (use mission-system).
---

# spec-kitty-git-workflow

Understand the boundary between what spec-kitty's Python code does with git
and what LLM agents are expected to do. This boundary is critical — agents
that try to create worktrees manually or skip implementation commits will
break the workflow.

---

## The Core Boundary

**Python handles infrastructure git** — worktrees, lane commits, merges,
cleanup. **Agents handle content git** — implementation commits, rebases,
conflict resolution.

| Git Operation | Who Does It | When |
|---|---|---|
| `git worktree add` | Python | `spec-kitty implement WP##` (lane worktree when `lanes.json` exists, legacy WP worktree otherwise) |
| `git commit` (planning artifacts) | Python | Before worktree creation |
| `git commit` (lane transitions) | Python | WP moves to doing/for_review |
| `git commit` (implementation code) | **Agent** | After writing code in worktree |
| `git rebase` (stacked WPs) | **Agent** | When base WP has new changes |
| `git merge` (WP → target) | Python | `spec-kitty merge` |
| `git push` | Python (opt-in) | `spec-kitty merge --push` only |
| `git push` | **Agent** | Any other push scenario |
| Conflict resolution | **Agent** | During rebase or manual merge |
| `git worktree remove` | Python | After successful merge |
| `git branch -d` (cleanup) | Python | After successful merge |

---

## What Python Does Automatically

### 1. Worktree Creation

When you run `spec-kitty implement WP01`, Python resolves the execution topology first.

For modern lane-based features (`lanes.json` present), it creates or reuses the lane worktree for that WP:

```
git branch kitty/mission-042-feature main
git worktree add -b kitty/mission-042-feature-lane-a .worktrees/042-feature-lane-a kitty/mission-042-feature
```

Sequential WPs in the same lane reuse that same worktree; Spec Kitty updates
workspace context to point the active WP at the shared lane workspace.

For legacy features without lanes, Python still uses one worktree per WP:

```
git worktree add -b 042-feature-WP01 .worktrees/042-feature-WP01 main
```

It also configures sparse checkout to exclude `kitty-specs/` from the
worktree so agents don't accidentally modify planning artifacts from the
worktree context.

The agent never creates worktrees. Always use `spec-kitty implement`.

For dependent WPs with `--base`, Spec Kitty still validates the dependency intent:

```
spec-kitty implement WP02 --base WP01
```

Legacy WP-specific features branch from WP01's branch instead of main:

```
git worktree add -b 042-feature-WP02 .worktrees/042-feature-WP02 042-feature-WP01
```

### 2. Planning Artifact Auto-Commits

Before creating a worktree, Python checks if `kitty-specs/042-feature/` has
uncommitted changes on the primary branch. If so, it auto-commits:

```
git add -f kitty-specs/042-feature/
git commit -m "chore: Planning artifacts for 042-feature"
```

**Controlled by:** `auto_commit: true` in `.kittify/config.yaml` (default: true).
Can be disabled per-command with `--no-auto-commit`.

### 3. Lane Transition Auto-Commits

When a WP moves to `doing` or `for_review`, Python uses the **safe-commit
pattern** to commit only the WP frontmatter file:

- Moving to doing: `"chore: Start WP01 implementation [claude]"`
- Moving to for_review: `"chore: Start WP01 review [claude]"`

**The safe-commit pattern** prevents accidentally committing agent
work-in-progress:
1. Stash current staging area
2. Stage only the target files (WP frontmatter, status artifacts)
3. Commit
4. Pop stash to restore previous staging

### 4. Status Event Log (No Auto-Commit)

`emit_status_transition()` appends to `status.events.jsonl`, updates
`status.json`, and modifies WP frontmatter — but does **NOT** auto-commit
these files. They accumulate as uncommitted changes until the next lane
transition auto-commit or the agent commits them.

This is by design — status changes happen frequently and committing each
one would create excessive git noise.

### 5. Merge Execution

`spec-kitty merge --feature 042-feature` runs the merge sequence that matches the feature topology.

For lane-based features it merges lane branches into the mission branch, then the mission branch into the target branch:

```
git checkout main
git merge --no-ff kitty/mission-042-feature
git worktree remove .worktrees/042-feature-lane-a --force
git branch -d kitty/mission-042-feature-lane-a
git branch -d kitty/mission-042-feature
```

Legacy features without lanes still merge WP branches/worktrees in dependency order.

Supports 3 strategies: `merge` (--no-ff, default), `squash`, `rebase`.

`--push` is opt-in — without it, the merge is local only.

### 6. Pre-flight Validation (Read-Only)

Before merge, Python validates:
1. All expected WPs have worktrees
2. All worktrees are clean (`git status --porcelain`)
3. Target branch is not behind origin (`git rev-list --left-right --count`)
4. WPs in done lane with missing worktrees are skipped (already merged)

If any check fails, merge is blocked with specific error messages.

---

## What Agents Must Do

### 1. Implementation Commits

All actual code work must be committed by the agent. Python creates the
worktree but never commits code:

```bash
cd <workspace printed by spec-kitty agent workflow implement>
# ... write code, run tests ...
git add src/ tests/
git commit -m "feat(WP01): implement auth middleware"
```

**Validation:** When the agent tries to move WP to `for_review`, spec-kitty
checks that the worktree has commits ahead of the base branch
(`git rev-list --count <base>..HEAD`). If zero commits, the transition is
rejected.

### 2. Rebasing Dependent WPs

When the base branch for your workspace has changed since it was created:

```bash
cd <workspace printed by spec-kitty>
git rebase <base-branch printed by spec-kitty>
# resolve conflicts if any
git add .
git rebase --continue
```

Python displays a rebase warning but does not execute it. The agent must
handle this manually.

**When this happens:** After WP01 is reviewed and gets changes, or after
WP01 is merged and WP02 needs to pick up those changes.

### 3. Multi-Parent Dependencies

If WP04 depends on both WP02 and WP03, use `--base` for one and manually
merge the other when you are in a legacy WP-specific branch. In lane mode,
the resolved workspace may already be a shared lane workspace and no separate
WP branch will exist.

```bash
spec-kitty implement WP04 --base WP03    # branches from WP03
cd <resolved workspace>
git merge 042-feature-WP02               # manually merge WP02 when needed
```

### 4. Pushing

`spec-kitty merge` only pushes with `--push`. All other pushing is the
agent's responsibility.

### 5. Conflict Resolution

If `spec-kitty merge` encounters conflicts, the agent must resolve them.
Python does not attempt automatic conflict resolution.

---

## Auto-Commit Configuration

```yaml
# .kittify/config.yaml
auto_commit: true    # default
```

When `true`, spec-kitty auto-commits:
- Planning artifacts before worktree creation
- WP frontmatter on lane transitions (doing, for_review)

When `false`, agents must commit everything manually.

Per-command override: `--no-auto-commit` flag on `spec-kitty implement`.

---

## Worktree Lifecycle

```
1. CREATED
   spec-kitty implement WP01
   → git worktree add -b kitty/mission-042-feature-lane-a .worktrees/042-feature-lane-a kitty/mission-042-feature
   → .kittify/workspaces/042-feature-lane-a.json created

2. ACTIVE (agent works here)
   cd .worktrees/042-feature-lane-a
   → agent writes code, commits, tests
   → WP status: in_progress

3. FOR REVIEW
   spec-kitty agent tasks move-task WP01 --to for_review
   → auto-commit: "chore: Start WP01 review"
   → reviewer checks the diff

4. MERGED
   spec-kitty merge --feature 042-feature
   → git merge --no-ff kitty/mission-042-feature
   → git worktree remove .worktrees/042-feature-lane-a --force
   → git branch -d kitty/mission-042-feature-lane-a
   → .kittify/workspaces/042-feature-lane-a.json removed

5. CLEANED UP
   Worktree directory gone, branch deleted, workspace context removed
```

---

## No Git Hooks

Spec-kitty does NOT use git hooks. Feature 043 replaced the pre-commit hook
(which handled UTF-8 encoding validation) with a Python codec layer
(`src/specify_cli/codec/`). No `.git/hooks/` files are installed or managed.

---

## Key Anti-Patterns

1. **Agent creates worktree manually** — Don't `git worktree add` yourself.
   Use `spec-kitty implement`. Manual worktrees won't have workspace context,
   sparse checkout, or proper branch naming.

2. **Agent commits in main repo during implementation** — Implementation
   commits belong in the worktree, not in the main repo. The main repo is
   for planning artifacts only.

3. **Agent pushes without being asked** — Never auto-push. Only push when
   the user explicitly requests it or when using `spec-kitty merge --push`.

4. **Agent modifies other WPs from a worktree** — Each worktree is isolated
   to one WP. Don't modify files belonging to other WPs.

5. **Agent skips commits before for_review** — Spec-kitty validates that
   worktree has commits ahead of base before accepting the transition.

---

## References

- `references/git-operations-matrix.md` -- Complete matrix of every git command spec-kitty runs

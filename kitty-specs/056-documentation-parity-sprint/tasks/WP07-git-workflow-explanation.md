---
work_package_id: WP07
title: Git Workflow Explanation
lane: "for_review"
dependencies: [WP01]
requirement_refs: [FR-009]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: 056-documentation-parity-sprint-WP01
base_commit: a3c2fae9fa7c40e05f6ae6b06619574b80195a42
created_at: '2026-03-22T14:58:56.191229+00:00'
subtasks: [T032, T033, T034, T035, T036, T037]
agent: coordinator
shell_pid: '21973'
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 3
---

# WP07: Git Workflow Explanation

## Objective

Create `docs/explanation/git-workflow.md` — a user-facing explanation distilled
from the `spec-kitty-git-workflow` skill. Help users understand what spec-kitty
does with git automatically vs what they (or their agents) must do manually.

## Source Material

Read `src/doctrine/skills/spec-kitty-git-workflow/SKILL.md` and
`references/git-operations-matrix.md`. Also check existing
`docs/explanation/git-worktrees.md` (308 lines) to avoid duplication.

## Implementation

### T032: Core boundary section

Open with the key insight: "Python handles infrastructure git, agents handle
content git." Include the summary table from the skill showing who does what.

### T033: Worktree lifecycle

Document the 5 stages at user level:
1. Created by `spec-kitty implement WP##`
2. Agent works in the worktree (writes code, commits)
3. WP moves to for_review
4. Merged by `spec-kitty merge`
5. Worktree removed, branch deleted

Include the `--base` flag for dependent WPs.

### T034: Auto-commit behavior

Explain what gets auto-committed and when:
- Planning artifacts before worktree creation
- WP frontmatter on lane transitions

Explain the `auto_commit` config setting and how to disable it.

### T035: What users/agents must do

Clearly list what's NOT automatic:
- All implementation commits (code, tests, config)
- Rebasing dependent WPs when the base changes
- Pushing (only automatic with `spec-kitty merge --push`)
- Resolving merge conflicts

Include practical examples:
```bash
cd .worktrees/042-feature-WP01
git add src/ tests/
git commit -m "feat(WP01): implement auth"
```

### T036: Anti-patterns

Document common mistakes:
- Creating worktrees manually (no workspace context, no sparse checkout)
- Committing in the main repo during implementation
- Pushing without being asked
- Modifying other WPs from a worktree

### T037: Update toc.yml

Add `git-workflow.md` to `docs/explanation/toc.yml`. Position it near the
existing `git-worktrees.md` entry.

## Definition of Done

- [ ] Guide created at `docs/explanation/git-workflow.md`
- [ ] No duplication with existing git-worktrees.md (complementary, not overlapping)
- [ ] Boundary table included
- [ ] Worktree lifecycle documented
- [ ] Anti-patterns documented
- [ ] toc.yml updated

## Implementation Command

```bash
spec-kitty implement WP07 --base WP01
```

## Activity Log

- 2026-03-22T14:58:56Z – coordinator – shell_pid=21973 – lane=doing – Assigned agent via workflow command
- 2026-03-22T15:02:59Z – coordinator – shell_pid=21973 – lane=for_review – Git workflow explanation created with responsibility boundary table, worktree lifecycle, auto-commit behavior, manual operations, and anti-patterns. toc.yml updated.

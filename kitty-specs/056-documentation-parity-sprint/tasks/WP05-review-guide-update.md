---
work_package_id: WP05
title: Review Work Package Guide Update
lane: "doing"
dependencies: [WP01]
requirement_refs: [FR-007]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: 056-documentation-parity-sprint-WP01
base_commit: a3c2fae9fa7c40e05f6ae6b06619574b80195a42
created_at: '2026-03-22T14:58:51.307231+00:00'
subtasks: [T022, T023, T024, T025, T026]
shell_pid: "21973"
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 2
---

# WP05: Review Work Package Guide Update

## Objective

Expand existing `docs/how-to/review-work-package.md` with content from the
`spec-kitty-runtime-review` skill. Add the discovery step, --feature flag
guidance, governance context, and downstream impact checking that the current
guide lacks.

## Source Material

Read `src/doctrine/skills/spec-kitty-runtime-review/SKILL.md` and
`references/review-checklist.md`. Read the existing guide at
`docs/how-to/review-work-package.md` to understand what's already covered.

## Implementation

### T022: Add discovery step

The existing guide assumes the reviewer already knows which WP to review.
Add a section at the top showing how to find reviewable WPs:

```bash
spec-kitty agent tasks list-tasks --lane for_review --feature <slug> --json
```

Explain that if the for_review lane is empty, there's nothing to review.

### T023: Add --feature flag guidance

Add a note that `--feature` is required in multi-feature repos. Without it,
commands fail with "Multiple features found." Show the flag on every command
example in the guide.

### T024: Add governance context step

Add a step for loading governance context before reviewing:

```bash
spec-kitty constitution context --action review --json
```

Note that if governance files are missing, the command still works with
fallback defaults — it's not a blocker.

### T025: Add downstream impact checking

Add a post-review step for rejection cases:

```bash
spec-kitty agent tasks list-dependents WP## --feature <slug>
```

Explain that if the rejected WP has downstream dependents, the reviewer
should include a rebase warning in feedback.

### T026: Preserve existing content

Do not rewrite the existing guide. Read it first, identify where new content
fits naturally, and extend. The existing sections on claiming, reviewing diffs,
and issuing verdicts should remain.

## Definition of Done

- [ ] Existing guide extended (not rewritten)
- [ ] Discovery step added at top
- [ ] --feature flag on all command examples
- [ ] Governance context step added
- [ ] Downstream impact checking added for rejections
- [ ] All commands verified against --help

## Implementation Command

```bash
spec-kitty implement WP05 --base WP01
```

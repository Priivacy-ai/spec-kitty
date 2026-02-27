---
description: Merge a completed feature into the target branch and clean up worktree
scripts:
  sh: "spec-kitty agent feature merge"
  ps: "spec-kitty agent"
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root.

# Merge Feature Branch

Use `spec-kitty merge` as the single source of truth for merge execution.

## Canonical Location Rule

Run merge from the **primary repository checkout root** (the repository root outside `.worktrees/`).

- The primary checkout can be on any branch chosen by the developer.
- "Primary repository" does **not** mean the branch must be named `main`.

## Deterministic Flow (Required)

1. Run dry-run planning first:

```bash
spec-kitty merge --feature <feature-slug> --dry-run --json
```

2. Parse JSON fields:
- `all_wp_branches`
- `effective_wp_branches`
- `skipped_already_in_target`
- `skipped_ancestor_of`
- `planned_steps`

3. Execute one merge command from the primary checkout root:

```bash
spec-kitty merge --feature <feature-slug>
```

## Hard Rules

- Do **not** manually run `git merge <feature-WP##>` loops.
- Do **not** merge one WP at a time unless `spec-kitty merge` fails and the user explicitly asks for manual recovery.
- If `effective_wp_branches` contains one tip, merge only that tip; other WP branches are already contained.
- If `effective_wp_branches` is empty, treat as already integrated and stop.

## Notes

- Workspace-per-WP features are merged using ancestry-aware pruning.
- Cleanup flags remain optional (`--keep-branch`, `--keep-worktree`).
- Use `--push` only when requested.

---
description: Merge a completed feature into the target branch and clean up worktree
---

# /spec-kitty.merge - Deterministic Merge

Run merge from the **primary repository checkout root** (outside `.worktrees/`).
The checkout branch can be whatever branch the developer is using.

## Required Execution Sequence

1. Generate deterministic merge plan first:

```bash
spec-kitty merge --feature <feature-slug> --dry-run --json
```

2. Confirm effective merge tips from JSON (`effective_wp_branches`).

3. Execute the actual merge once:

```bash
spec-kitty merge --feature <feature-slug>
```

## Prohibited Behavior

- Never run manual `git merge <feature-WP##>` loops by default.
- Never merge WP01→WP02→... just by numbering.
- Only attempt manual git merges if `spec-kitty merge` fails and the user asks for manual recovery.

## Interpretation Rules

- Single effective tip: merge that tip only.
- Empty effective set: already integrated; no merge needed.
- `all_wp_branches` may be larger than `effective_wp_branches`; this is expected.

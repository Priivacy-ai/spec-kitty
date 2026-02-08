---
description: Analyze project state and recommend the next step with a ready-to-use command.
---

# /spec-kitty.next - What Should I Do Next?

**Version**: 0.14.1+
**Purpose**: Read current project state and recommend what to do next with a copy-paste command.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). If the user asks about a specific feature or phase, tailor the recommendation to that context.

## Philosophy

This command is the **conductor**. It reads the state of the project and tells you exactly what to do next. Designed for vibe coders who don't want to memorize the workflow.

**No questions asked.** This command analyzes and recommends. The user copies the command and runs it.

**Keep output concise.** State, recommendation, command. That's it.

## Execution Steps

### 1. Check Product Vision

Check if `.kittify/memory/vision.md` exists.

- If **missing** and no features exist yet: Recommend `/spec-kitty.vision` and stop.
- If **missing** but features already exist: Note it as a suggestion but don't block. The user started without vision - that's fine.
- If **exists**: Load it and extract the feature map (MVP, Phase 2, Future sections).

### 2. Check Constitution

Check if `.kittify/memory/constitution.md` exists.

- If missing: Note as optional. Never block on this.
- If exists but is the placeholder ("Constitution skipped"): Same as missing.

### 3. Scan Feature State

List all feature directories in `kitty-specs/`:

```bash
ls kitty-specs/ 2>/dev/null
```

For each feature directory found, check which files exist:
- `spec.md` exists? -> specified
- `plan.md` exists? -> planned
- `tasks.md` exists? -> tasks generated
- `tasks/*.md` WP files? -> check frontmatter `lane:` field for kanban state

Build a state map of all features and their progress.

### 4. Check Kanban State

For features with WP task files, read each WP's YAML frontmatter to determine lane:
- Count WPs in each lane: `planned`, `doing`, `for_review`, `done`

You can also run:
```bash
spec-kitty agent tasks status
```

### 5. Determine Recommendation

Apply this priority order. Stop at the first match:

**Priority 1 - Blocked work needs attention:**

If any WPs are in `for_review`:
-> Recommend: `/spec-kitty.review [WP##]`
-> Why: "WP## is waiting for review. Unblock it before starting new work."

**Priority 2 - Complete in-progress features:**

If a feature has all WPs in `done`:
-> Recommend: `/spec-kitty.accept`
-> Why: "All work packages are done. Validate and accept the feature."

If a feature is accepted and ready to merge:
-> Recommend: `/spec-kitty.merge`
-> Why: "Feature is accepted. Merge it into main."

**Priority 3 - Advance a feature through the pipeline:**

If a feature has WPs in `planned` (none in `doing` or `for_review`):
-> Recommend: `/spec-kitty.implement [WP##]`
-> Why: "WP## is ready to implement."

If a feature has `plan.md` and `tasks.md` but no WP files in `tasks/`:
-> Recommend: `/spec-kitty.tasks`
-> Why: "Plan is ready. Generate work packages."

If a feature has `plan.md` but no `tasks.md`:
-> Recommend: `/spec-kitty.tasks`
-> Why: "Plan is complete. Generate work packages."

If a feature has `spec.md` but no `plan.md`:
-> Recommend: `/spec-kitty.plan`
-> Why: "Spec is ready. Create the implementation plan."

If a feature has only `spec.md` and could benefit from clarification:
-> Optionally suggest: `/spec-kitty.clarify` before plan
-> But don't block: "You can run `/spec-kitty.clarify` first or go straight to `/spec-kitty.plan`"

**Priority 4 - Start a new feature:**

If vision exists with features in the feature map that don't have matching `kitty-specs/` directories:
-> Find the highest-priority unstarted feature (MVP first, then Phase 2, etc.)
-> Check its dependencies are met (dependent features are merged)
-> Recommend: `/spec-kitty.specify [blurb from vision feature description]`
-> Include a ready-to-paste description derived from the vision's feature map entry

**Priority 5 - No vision yet:**

If no vision exists and no features exist:
-> Recommend: `/spec-kitty.vision`
-> Why: "Start by defining your product vision."

**Priority 6 - Everything is done:**

If all vision features have been built and merged:
-> Congratulate the user
-> Suggest: "Update your vision with new goals: `/spec-kitty.vision`"

### 6. Format Output

Present the recommendation in this exact format:

```
## Project State

[1-2 lines summarizing current state. Example: "1 feature in progress (001-timestamp-crud), 3 of 5 WPs done. No other features started."]

## Next Step

[What to do and WHY - 1-2 sentences max]

## Command

[The command to run, in a code block. For specify commands, include the description blurb.]
```

For `/spec-kitty.specify` recommendations, format the blurb as:

```
/spec-kitty.specify [descriptive blurb derived from vision feature map entry]
```

The blurb should be a natural language description that specify's discovery can use as a starting point - typically 1-2 sentences covering what the feature does and why it matters.

### 7. Optional: After That

If helpful, add a brief "After that" line showing what comes next in the pipeline:

```
## After That

[One line: "After planning, you'll generate work packages with `/spec-kitty.tasks`"]
```

## Edge Cases

- **Multiple features in progress**: Recommend completing the most advanced one first (closest to done). Mention the others briefly.
- **Blocked feature**: If a feature's next WP depends on an unmerged WP, note the blocker and suggest reviewing/completing the dependency first.
- **No vision, but features exist**: User started without vision. Don't block. Recommend the next step for existing features, and suggest `/spec-kitty.vision` as a side note to organize remaining work.
- **WPs in doing**: Someone is implementing. Don't recommend starting another WP for the same feature unless parallelizable. Suggest checking status: `/spec-kitty.status`.
- **Feature map mismatch**: If vision features don't map cleanly to kitty-specs directories (names changed, features split/merged), do your best to match by description and note any ambiguity.
- **Empty project**: No vision, no constitution, no features. Recommend `/spec-kitty.vision`.

## Rules

- **Never ask questions.** This command analyzes and recommends.
- **Always provide a copy-paste command.** The user should be able to act immediately.
- **Keep output concise.** State, recommendation, command. Three sections, done.
- **Be honest about blockers.** If something is stuck, say so and suggest how to unblock.
- **Respect the pipeline order.** Don't skip steps (e.g., don't recommend implement before tasks exist).
- **Use vision feature map as the source of truth** for what to build next, when available.

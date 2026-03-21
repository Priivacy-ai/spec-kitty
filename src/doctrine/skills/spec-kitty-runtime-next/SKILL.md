---
name: spec-kitty-runtime-next
description: >-
  Drive the canonical spec-kitty next --agent <name> control loop for mission advancement.
  Triggers: "run the next step", "what should runtime do next", "advance the mission",
  "what is the next task", "continue the workflow", "what step comes next".
  Does NOT handle: setup or repair requests (use spec-kitty-setup-doctor),
  purely editorial glossary or doctrine maintenance (use spec-kitty-glossary-context
  or spec-kitty-constitution-doctrine), or direct code review (use spec-kitty-runtime-review).
---

# spec-kitty-runtime-next

This skill teaches agents how to advance a Spec Kitty mission through the canonical runtime control loop.

## When to Use This Skill

Use this skill when the user wants to:

- Advance a mission to its next step
- Understand what the runtime will do next
- Unblock a stalled mission
- Interpret runtime outcomes (ready, blocked, failed, review-required)

## Step 1: Load Runtime Context

Before invoking the runtime, gather the current state.

**Commands:**

```bash
# Check which feature/mission is active
spec-kitty agent tasks status

# Check current mission state
spec-kitty agent context resolve --action implement --json
```

**What to look for:**

- Active feature slug and mission type
- Current WP lane status (planned, doing, for_review, done)
- Whether there are WPs ready for implementation or review
- Any blocked or failed WPs that need attention first

## Step 2: Run the Next Command

The canonical control loop is `spec-kitty next --agent <name>`.

**Commands:**

```bash
# Run the next step (replace <agent> with the active agent identifier)
spec-kitty next --agent <agent>
```

**The runtime determines the next action based on:**

1. Mission state machine (current phase and transitions)
2. WP dependency graph (which WPs are unblocked)
3. Lane status (what needs implementation vs review)
4. Doctrine and constitution constraints

## Step 3: Interpret the Result

The runtime returns one of several outcome types. See `references/runtime-result-taxonomy.md` for the complete taxonomy.

**Common outcomes and what to do:**

| Outcome | Meaning | Next Action |
|---------|---------|-------------|
| **ready** | A WP is available for implementation | Run `spec-kitty implement WP##` |
| **review-required** | A WP needs review before advancing | Run `/spec-kitty.review` on the WP |
| **blocked** | Dependencies not met or external input needed | Check dependency graph, resolve blockers |
| **failed** | A step failed and needs retry or escalation | Read error details, fix, retry |
| **complete** | Mission is finished | Run `/spec-kitty.accept` for final validation |

## Step 4: Handle Blocked States

When the runtime reports a blocked state, diagnose the cause.

**Common blockers and recovery:**

See `references/blocked-state-recovery.md` for detailed recovery patterns.

**Quick diagnostic:**

```bash
# Check dependency graph
spec-kitty agent tasks status --feature <feature-slug>

# Check if blocked WP has unmet dependencies
grep -A2 'dependencies:' kitty-specs/<feature>/tasks/WP##-*.md
```

## Step 5: Advance and Record

After completing the runtime action:

1. **Record the result** in the WP activity log
2. **Move the WP** to the appropriate lane if the action changed its status
3. **Re-run `spec-kitty next`** to check if another step is available
4. **Report the outcome** to the user with the WP ID and new state

**The runtime loop continues until:**

- All WPs are in the `done` lane
- The mission reaches a terminal state
- External input is required (human decision, blocked dependency)

## Important: Runtime Precedence Rules

1. **Always use `spec-kitty next`** rather than manually sequencing phases
2. **Respect mission state machine transitions** — do not skip steps
3. **Check doctrine and constitution** before executing runtime actions
4. **Glossary terms apply** to all runtime outputs — use canonical terminology
5. **Review-required outcomes are mandatory** — do not skip reviews

---
name: spec-kitty-runtime-next
description: >-
  Drive the canonical spec-kitty next --agent <name> control loop for mission advancement.
  Triggers: "run the next step", "what should runtime do next", "advance the mission",
  "what is the next task", "continue the workflow", "what step comes next".
  Does NOT handle: setup or repair requests, purely editorial glossary or doctrine
  maintenance, or direct code review.
---

# spec-kitty-runtime-next

This skill teaches agents how to advance a Spec Kitty mission through the canonical runtime control loop.

## When to Use This Skill

Use this skill when the user wants to:

- Advance a mission to its next step
- Understand what the runtime will do next
- Unblock a stalled mission
- Interpret runtime outcomes (step, blocked, decision_required, terminal)

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
- Any blocked WPs that need attention first

## Step 2: Run the Next Command

The canonical control loop is `spec-kitty next --agent <name>`.

**Commands:**

```bash
# Run the next step (replace <agent> with the active agent identifier)
spec-kitty next --agent <agent>

# Use --json for machine-readable output
spec-kitty next --agent <agent> --json
```

**The runtime determines the next action based on:**

1. Mission state machine (current phase and transitions)
2. WP dependency graph (which WPs are unblocked)
3. Lane status (what needs implementation vs review)
4. Guard conditions (required artifacts, prerequisites)

## Step 3: Interpret the Result

The runtime returns a decision with one of four `kind` values. See `references/runtime-result-taxonomy.md` for the complete taxonomy.

**Decision kinds and what to do:**

| Kind | Meaning | Next Action |
|------|---------|-------------|
| **step** | An action is available — read the prompt file and execute | Read `prompt_file` from the output, execute the action |
| **decision_required** | Runtime needs input before continuing | Answer the question using `spec-kitty next --agent <agent> --answer "..." --decision-id "..."` |
| **blocked** | Cannot proceed — prerequisites or state invalid | Read `reason` and `guard_failures`, resolve the blockers |
| **terminal** | Mission is complete — agent loop should exit | Run `/spec-kitty.accept` for final validation |

**Key output fields:**

- `kind` — the decision type (step, decision_required, blocked, terminal)
- `action` — the action to take (e.g., "implement", "review", "specify")
- `wp_id` — work package identifier if iterating (e.g., "WP01")
- `workspace_path` — path to the worktree directory for this WP
- `prompt_file` — path to the prompt file the agent should read and follow
- `reason` — explanation for blocked or terminal decisions
- `guard_failures` — list of guard failure descriptions (may appear on any kind)
- `progress` — WP progress summary with counts per lane

## Step 4: Handle Blocked States

When the runtime reports `kind: "blocked"`, diagnose the cause.

**Common blockers and recovery:**

See `references/blocked-state-recovery.md` for detailed recovery patterns.

**Quick diagnostic:**

```bash
# Check WP status and dependency graph
spec-kitty agent tasks status --feature <feature-slug>

# Check if blocked WP has unmet dependencies
grep -A2 'dependencies:' kitty-specs/<feature>/tasks/WP##-*.md
```

## Step 5: Advance and Record

After completing the runtime action:

1. **Read the `prompt_file`** returned by the decision — it contains full context
2. **Execute the action** following the prompt instructions
3. **Record the result** in the WP activity log
4. **Move the WP** to the appropriate lane when the action completes
5. **Re-run `spec-kitty next`** to check if another step is available

**The runtime loop continues until:**

- The decision kind is `terminal` (mission complete)
- The decision kind is `blocked` and the blocker requires external input
- The decision kind is `decision_required` and only the user can answer

## Important: Runtime Precedence Rules

1. **Always use `spec-kitty next`** rather than manually sequencing phases
2. **Respect mission state machine transitions** — do not skip steps
3. **Read the `prompt_file`** — it contains the full context the agent needs
4. **Check doctrine and constitution** before executing runtime actions
5. **Glossary terms apply** to all runtime outputs — use canonical terminology

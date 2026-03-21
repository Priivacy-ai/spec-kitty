# Runtime Result Taxonomy

Reference for interpreting `spec-kitty next --agent <name>` decision output.

## Decision Kinds

The runtime returns decisions with exactly four `kind` values.

### step

A normal action step. The agent should read the prompt file and execute the action.

**Key fields:**
- `action`: The action to take (e.g., "implement", "review", "specify", "plan")
- `wp_id`: Work package identifier if iterating (e.g., "WP03")
- `workspace_path`: Path to the worktree directory for this WP
- `prompt_file`: Path to the prompt file the agent should read and follow

**Agent response:** Read `prompt_file`, execute the action described within it. For implementation actions, the workspace is already prepared at `workspace_path`.

### decision_required

The runtime needs input before it can determine the next step. The agent must answer the question or escalate to the user.

**Key fields:**
- `question`: The decision question text
- `options`: List of valid answer options
- `decision_id`: ID to pass back when answering
- `input_key`: Runtime input key for the answer
- `prompt_file`: May contain additional context for the decision

**Agent response:** Answer using:
```bash
spec-kitty next --agent <agent> --answer "<choice>" --decision-id "<decision_id>"
```

If the agent cannot determine the answer, escalate to the user with the question and options.

### blocked

The runtime cannot proceed. Guards are failing or the mission state is invalid.

**Key fields:**
- `reason`: High-level description of why the mission is blocked
- `guard_failures`: List of specific guard failure descriptions

**Note:** Blocked decisions do not populate `action` — the runtime could not determine a valid action.

**Common causes:**
- Required artifacts missing (e.g., plan.md not yet created)
- Prerequisites not met (e.g., upstream WP not done)
- Configuration invalid (e.g., mission not activated)

**Agent response:** Read `reason` and `guard_failures` to understand what is missing. Resolve each guard failure, then retry `spec-kitty next`.

**Note on guard_failures:** This field may also appear on `step` decisions when the runtime reuses the current step after guard evaluation. Always check it regardless of kind.

### terminal

The mission has reached its final state. The agent loop should exit.

**Key fields:**
- `reason`: Explanation of terminal state (e.g., "all work packages complete")
- `progress`: Final WP progress summary

**Agent response:** Run `/spec-kitty.accept` for final validation. Report completion to the user.

## Progress Field

Every decision includes a `progress` object summarizing WP status:

```json
{
  "total_wps": 9,
  "done_wps": 7,
  "approved_wps": 2,
  "in_progress_wps": 1,
  "planned_wps": 1,
  "for_review_wps": 0
}
```

## Precedence Rules

When multiple actions are possible:

1. **Reviews before new implementations** (unblock downstream work)
2. **Higher priority WPs first** (P0 before P1 before P2)
3. **Dependency-free WPs before dependent ones** (enable parallelization)
4. **Guard resolution before retry** (fix blockers, don't retry blindly)

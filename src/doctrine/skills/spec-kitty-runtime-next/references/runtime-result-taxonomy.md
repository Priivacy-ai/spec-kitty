# Runtime Result Taxonomy

Reference for interpreting `spec-kitty next --agent <name>` outcomes.

## Result Types

### ready

The runtime has identified a WP or action that is available for execution.

**Fields returned:**
- `action`: The specific action to take (e.g., "implement", "review")
- `wp_id`: The work package identifier (e.g., "WP03")
- `reason`: Why this WP was selected (e.g., "dependencies met, highest priority")

**Agent response:** Execute the identified action. For implementation, run `spec-kitty implement WP##`. For review, run `/spec-kitty.review`.

### review-required

A WP has reached the `for_review` lane and must be reviewed before the mission can advance.

**Fields returned:**
- `wp_id`: The WP awaiting review
- `reviewer`: Suggested reviewer agent (from agent config)
- `blocking`: List of WPs that depend on this review completing

**Agent response:** Switch to reviewer mode or dispatch a review agent. Do not skip the review — the mission state machine requires it.

### blocked

No WPs are currently actionable. All remaining WPs have unmet dependencies or are waiting for external input.

**Fields returned:**
- `blocked_wps`: List of blocked WP IDs with their unmet dependencies
- `reason`: High-level description of the blockage
- `suggestion`: Recommended action to unblock

**Common causes:**
- Upstream WP not yet merged
- Review feedback not addressed
- External dependency (human decision, API key, infrastructure)

**Agent response:** Diagnose the specific blocker. If it is within the agent's capability, resolve it. Otherwise, report to the user with actionable next steps.

### failed

A runtime action failed and needs intervention.

**Fields returned:**
- `wp_id`: The WP that failed
- `error`: Error description
- `retry_allowed`: Whether automatic retry is permitted

**Agent response:** Read the error details. If `retry_allowed` is true, attempt the action again after fixing the root cause. If not, escalate to the user.

### complete

All WPs are in the `done` lane and the mission has reached its terminal state.

**Fields returned:**
- `mission`: The completed mission identifier
- `total_wps`: Number of WPs completed
- `duration`: Time from first WP to last

**Agent response:** Run `/spec-kitty.accept` for final validation. Report completion to the user.

## Precedence Rules

When multiple WPs are ready simultaneously:

1. **Higher priority WPs first** (P0 before P1 before P2)
2. **Dependency-free WPs before dependent ones** (enable parallelization)
3. **Reviews before new implementations** (unblock downstream work)
4. **Smaller WPs before larger ones** (quick wins build momentum)

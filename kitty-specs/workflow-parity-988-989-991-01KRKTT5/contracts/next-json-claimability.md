# Contract: `next --json` claimability payload (issue #988)

## Inputs

```
spec-kitty next --mission <handle> --json
```

Mission state: `mission_state == "implement"`, `preview_step == "implement"`, at least one WP in lane `planned` whose dependencies are satisfied.

## Output (JSON, success path)

```jsonc
{
  "mission_state": "implement",
  "planned_wps": <int>,
  "preview_step": "implement",
  "wp_id": "WP##",          // REQUIRED: concrete WP that `agent action implement` would claim
  "selection_reason": null  // null when wp_id is set
  // ... existing fields unchanged
}
```

## Output (JSON, no-candidate path)

```jsonc
{
  "mission_state": "implement",
  "planned_wps": <int>,
  "preview_step": "implement",
  "wp_id": null,
  "selection_reason": "no_planned_wps" | "all_wps_in_progress" | "dependencies_unsatisfied" | "baseline_violation"
  // ... existing fields unchanged
}
```

## Invariants

- `wp_id != null` iff `selection_reason == null`.
- `wp_id` MUST equal the WP that an immediately-following `spec-kitty agent action implement --mission <handle> --agent <name>` would claim, given the same mission state.
- Non-implement `mission_state` values keep their existing payload shape (wire shape is unchanged for them — see spec C-001).

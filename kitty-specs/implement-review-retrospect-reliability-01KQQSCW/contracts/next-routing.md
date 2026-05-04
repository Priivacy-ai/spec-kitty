# Contract: Finalized Task Routing for `spec-kitty next`

## Scope

This contract covers #961.

## Rule

When a mission has finalized tasks and WP files, canonical task board and WP lane state are authoritative for implement-review routing. Stale runtime or mission phase state must not route the agent back to discovery.

## Inputs

- Mission handle from `--mission`.
- Mission directory under `kitty-specs/<mission>/`.
- `tasks.md`.
- `tasks/WP*.md`.
- Canonical `status.events.jsonl` reduced lane state.
- Existing runtime state, if present.

## Outputs

`spec-kitty next --mission <mission> --agent <agent> --json` returns one of:

- Implement step for the next implementable WP.
- Review step for the next reviewable WP.
- Merge/completion step when all WPs are approved or done.
- Terminal state for completed missions.
- Blocked decision with guard failures when finalized state is inconsistent.

## Prohibited Output

- `discovery` or another early planning phase solely because stale runtime/phase state says so after finalized tasks and WP lane state exist.

## Regression Fixture Requirements

Create a fixture mission with:

- `spec.md`, `plan.md`, `tasks.md`.
- At least one `tasks/WP*.md`.
- Canonical status events showing finalized WP state.
- Stale runtime/phase state set to discovery or equivalent early phase.

Assertions:

- Planned/in-progress WPs route to implement.
- `for_review` or `in_review` WPs route to review or active review handling.
- Approved/done WPs route toward merge/completion.
- Blocked WPs produce blocked output rather than discovery.

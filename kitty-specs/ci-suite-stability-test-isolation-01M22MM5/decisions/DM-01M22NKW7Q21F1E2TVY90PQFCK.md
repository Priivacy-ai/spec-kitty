# Decision Moment `01M22NKW7Q21F1E2TVY90PQFCK`

- **Mission:** `ci-suite-stability-test-isolation-01M22MM5`
- **Origin flow:** `plan`
- **Slot key:** `plan.4017.check-assets-scope`
- **Input key:** `check_assets_scope`
- **Status:** `resolved`
- **Created:** `2026-09-09T08:47:39.255881+00:00`
- **Resolved:** `2026-09-09T08:53:45.232118+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Should the #4017 re-assess-under-lock + role-tag fix land in the GENERIC check_assets surface (covering runtime + agent_commands + agent_skills + managed_skills owners) or be RUNTIME-scoped only? The architect found all owners race identically on the shared home, so runtime-only would leave the two-owned-worktree model crashing when a peer materializes agent-command/skill destinations.

## Options

- Generic (all owners)
- Runtime-scoped only
- Other

## Final answer

Generic — all owners. Land the re-assess-under-lock + observe() role-tag in the generic check_assets/ensure_runtime path so runtime + agent_commands + agent_skills + managed_skills owners are all covered; runtime-only would leave the two-owned-worktree model crashing when a peer materializes agent-command/skill destinations.

## Rationale

_(none)_

## Change log

- `2026-09-09T08:47:39.255881+00:00` — opened
- `2026-09-09T08:53:45.232118+00:00` — resolved (final_answer="Generic — all owners. Land the re-assess-under-lock + observe() role-tag in the generic check_assets/ensure_runtime path so runtime + agent_commands + agent_skills + managed_skills owners are all covered; runtime-only would leave the two-owned-worktree model crashing when a peer materializes agent-command/skill destinations.")

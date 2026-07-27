# Decision Moment `01KQW556RAG1N0QF7PVSTP08P7`

- **Mission:** `stable-320-release-blocker-cleanup-01KQW4DF`
- **Origin flow:** `plan`
- **Slot key:** `plan.merge-preflight.missing-branch-behavior`
- **Input key:** `missing_branch_behavior`
- **Status:** `resolved`
- **Created:** `2026-05-05T13:27:36.458699+00:00`
- **Resolved:** `2026-05-05T13:29:04.935164+00:00`
- **Other answer:** `false`

## Question

For a fresh single-branch smoke where the expected kitty/mission-<slug> branch is absent, should merge --dry-run (A) always report ready:false with a structured blocker and remediation command the user must run manually, (B) auto-create the branch when the mission state is valid and dry-run reports that planned action, or (C) detect context and choose: blocker if in a lane-based worktree, auto-create if in a fresh single-branch smoke?

## Options

- always_blocker
- auto_create_when_valid
- context_detect
- Other

## Final answer

always_blocker

## Rationale

_(none)_

## Change log

- `2026-05-05T13:27:36.458699+00:00` — opened
- `2026-05-05T13:29:04.935164+00:00` — resolved (final_answer="always_blocker")

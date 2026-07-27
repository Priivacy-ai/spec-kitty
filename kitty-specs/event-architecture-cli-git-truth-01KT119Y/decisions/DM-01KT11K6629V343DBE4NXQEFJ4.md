# Decision Moment `01KT11K6629V343DBE4NXQEFJ4`

- **Mission:** `event-architecture-cli-git-truth-01KT119Y`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.decision-commit-strategy`
- **Input key:** `decision_commit_strategy`
- **Status:** `resolved`
- **Created:** `2026-06-01T07:32:56.130228+00:00`
- **Resolved:** `2026-06-01T07:39:13.511262+00:00`
- **Other answer:** `false`

## Question

Should the git commit of decisions.events.jsonl happen (A) immediately at emit time inside the emitter, batching request+answer when they occur in the same operation, or (B) lazily at the end of each session/engine run, committing all pending decision events together?

## Options

- A: Eager per-emit commit (request commits when emitted; answer commits immediately when received)
- B: Lazy session-end commit (all pending decisions committed together when the session/run ends)
- Other

## Final answer

Eager per-answer commit: append DecisionInputRequested immediately (OS durability); append DecisionInputAnswered immediately; git commit triggered by the answer event, capturing the complete request+answer pair. Orphaned request lines (crash before answer) are left in the file — SaaS reader handles gracefully.

## Rationale

_(none)_

## Change log

- `2026-06-01T07:32:56.130228+00:00` — opened
- `2026-06-01T07:39:13.511262+00:00` — resolved (final_answer="Eager per-answer commit: append DecisionInputRequested immediately (OS durability); append DecisionInputAnswered immediately; git commit triggered by the answer event, capturing the complete request+answer pair. Orphaned request lines (crash before answer) are left in the file — SaaS reader handles gracefully.")

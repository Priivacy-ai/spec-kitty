# Decision Moment `01KXW0PN2KDS5M5GR9CMDPWV5F`

- **Mission:** `charter-deadcode-noop-campsite-01KXW0NY`
- **Origin flow:** `specify`
- **Slot key:** `specify.scope.item3-bundle-vs-split`
- **Input key:** `item3_scope`
- **Status:** `resolved`
- **Created:** `2026-07-19T01:43:56.243822+00:00`
- **Resolved:** `2026-07-19T01:43:57.242053+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Given #2373's render-path bug is already fixed by #2773, how should item 3 (no-op-stability) be scoped: guard+close, bundle the deep freshness/preflight fix, or dead-code-only?

## Options

- Bundle deep fix
- Guard and close
- Dead-code only

## Final answer

Bundle deep fix: delete generator + extractor (dead-code), add red-first render-cleanliness guard, AND fix the residual no-op churn in the preflight auto-refresh -> charter synthesize surface (freshness-misfire in charter_runtime/freshness/computer.py + preflight runner + synthesizer no-op ratchets). Reproduce red-first where doctrine is tracked (this checkout masks it via .git/info/exclude).

## Rationale

_(none)_

## Change log

- `2026-07-19T01:43:56.243822+00:00` — opened
- `2026-07-19T01:43:57.242053+00:00` — resolved (final_answer="Bundle deep fix: delete generator + extractor (dead-code), add red-first render-cleanliness guard, AND fix the residual no-op churn in the preflight auto-refresh -> charter synthesize surface (freshness-misfire in charter_runtime/freshness/computer.py + preflight runner + synthesizer no-op ratchets). Reproduce red-first where doctrine is tracked (this checkout masks it via .git/info/exclude).")

# Decision Moment `01KWCA4N3MEA9S89GB1QA6S4C0`

- **Mission:** `sync-worktree-clean-invariant-01KWC9Y0`
- **Origin flow:** `specify`
- **Slot key:** `specify.scope.breadth`
- **Input key:** `scope_breadth`
- **Status:** `resolved`
- **Created:** `2026-06-30T13:05:19.476595+00:00`
- **Resolved:** `2026-06-30T13:05:20.763868+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How broad should the worktree-clean fix scope be?

## Options

- Comprehensive test-driven
- Narrow two-source only
- Other

## Final answer

Comprehensive, test-driven: fix every read/background path that can dirty the worktree, enforced by a parametrized no-dirty-tree test across the full command surface {emit, sync pull/push/run/status, tracker status/map list, dashboard daemon tick}.

## Rationale

_(none)_

## Change log

- `2026-06-30T13:05:19.476595+00:00` — opened
- `2026-06-30T13:05:20.763868+00:00` — resolved (final_answer="Comprehensive, test-driven: fix every read/background path that can dirty the worktree, enforced by a parametrized no-dirty-tree test across the full command surface {emit, sync pull/push/run/status, tracker status/map list, dashboard daemon tick}.")

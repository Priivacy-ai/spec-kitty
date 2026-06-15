# Decision Moment `01KV5F16HBCX6A99J9AY97B3T5`

- **Mission:** `codebase-sanitization-1060-1622-01KV5F0B`
- **Origin flow:** `specify`
- **Slot key:** `specify.status_service.wire_or_retire`
- **Input key:** `status_service_wire_or_retire`
- **Status:** `resolved`
- **Created:** `2026-06-15T11:00:26.283393+00:00`
- **Resolved:** `2026-06-15T11:54:59.942883+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

For the 3 test-exercised status_service symbols (StatusContractError, StatusReadSource, EventLogWriteTarget): wire them to a live call site, or retire them together with their tests and a documented rationale?

## Options

- wire-to-live-callsite
- retire-with-tests
- Other

## Final answer

Neither wire nor retire — already resolved by 01KTPKST WP09 (commit be932d19a, approved 2026-06-09). The 2 truly-dead funcs (append_event_log_batch, read_wp_lane_actor) were deleted; the 3 remaining (StatusReadSource/EventLogWriteTarget/StatusContractError) are load-bearing live internals of EventLogReadContract/EventLogWriteContract/read_event_log/append_event_log (live callers in status_transition.py, transaction.py, store.py, event_log_merge.py, workflow.py) and were correctly de-exported, not deleted. Re-deleting breaks the build. #1622 reduces to a verify-only task: confirm the resolved state and close the ticket. No code change.

## Rationale

_(none)_

## Change log

- `2026-06-15T11:00:26.283393+00:00` — opened
- `2026-06-15T11:54:59.942883+00:00` — resolved (final_answer="Neither wire nor retire — already resolved by 01KTPKST WP09 (commit be932d19a, approved 2026-06-09). The 2 truly-dead funcs (append_event_log_batch, read_wp_lane_actor) were deleted; the 3 remaining (StatusReadSource/EventLogWriteTarget/StatusContractError) are load-bearing live internals of EventLogReadContract/EventLogWriteContract/read_event_log/append_event_log (live callers in status_transition.py, transaction.py, store.py, event_log_merge.py, workflow.py) and were correctly de-exported, not deleted. Re-deleting breaks the build. #1622 reduces to a verify-only task: confirm the resolved state and close the ticket. No code change.")

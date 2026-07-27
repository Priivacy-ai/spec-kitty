# Decision Moment `01KQH1YZGKKMJPJ7DGKKSKJ7XS`

- **Mission:** `private-teamspace-ingress-safeguards-01KQH03Y`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.rehydrate-single-flight`
- **Input key:** `rehydrate_single_flight`
- **Status:** `resolved`
- **Created:** `2026-05-01T06:00:07.956097+00:00`
- **Resolved:** `2026-05-01T06:22:47.573921+00:00`
- **Other answer:** `false`

## Question

How should concurrent rehydrate attempts (batch + websocket + queue + emitter all firing) be coordinated within one CLI process?

## Options

- asyncio_lock_in_token_manager
- once_per_process_negative_cache
- both_lock_and_cache
- no_coordination_each_call_site_attempts
- Other

## Final answer

Both: asyncio.Lock in TokenManager during attempt, plus a process-lifetime negative cache so one broken session causes exactly one /api/v1/me GET per process. Negative cache is cleared/bypassed when (a) stored session identity changes, (b) a fresh login completes, or (c) a forced repair / auth-doctor path explicitly requests rehydrate.

## Rationale

_(none)_

## Change log

- `2026-05-01T06:00:07.956097+00:00` — opened
- `2026-05-01T06:22:47.573921+00:00` — resolved (final_answer="Both: asyncio.Lock in TokenManager during attempt, plus a process-lifetime negative cache so one broken session causes exactly one /api/v1/me GET per process. Negative cache is cleared/bypassed when (a) stored session identity changes, (b) a fresh login completes, or (c) a forced repair / auth-doctor path explicitly requests rehydrate.")

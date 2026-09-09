# Decision Moment `01M1VAHPARWJKB35F6E1VH8ZTW`

- **Mission:** `dead-port-disposition-01M1TZVN`
- **Origin flow:** `plan`
- **Slot key:** `plan.emitter.adr-timing`
- **Input key:** `emitter_adr_gate`
- **Status:** `resolved`
- **Created:** `2026-09-06T12:19:32.312666+00:00`
- **Resolved:** `2026-09-06T12:20:21.031778+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

OD7: PR #3898 (emitter ADR) is still open/Proposed at plan time. Ship the P4 slice as the shrunk residue-only variant with emitter execution minted as a follow-up?

## Options

- Shrunk variant; follow-up for execution
- Wait for ADR
- Other

## Final answer

Shrunk variant. PR #3898 is OPEN with the ADR at status Proposed at plan time (verified via gh 2026-09-06); the tasks-time gate 'merged AND Accepted' is not met. WP03 ships residue + the event_emitter.py:1-10 docstring correction pointing at the real E3 seam (status/adapters.py:364-366) + the FR-011 verified record (research/emitter-adr-inputs.md); emitter execution (collision, sync_emitter pass, flush-target adjudication, parity oracle) is minted as a follow-up WP/mission once the ADR lands. Re-check the gate at tasks-finalize; if the ADR merged meanwhile, WP03's scope grows per FR-012.

## Rationale

_(none)_

## Change log

- `2026-09-06T12:19:32.312666+00:00` — opened
- `2026-09-06T12:20:21.031778+00:00` — resolved (final_answer="Shrunk variant. PR #3898 is OPEN with the ADR at status Proposed at plan time (verified via gh 2026-09-06); the tasks-time gate 'merged AND Accepted' is not met. WP03 ships residue + the event_emitter.py:1-10 docstring correction pointing at the real E3 seam (status/adapters.py:364-366) + the FR-011 verified record (research/emitter-adr-inputs.md); emitter execution (collision, sync_emitter pass, flush-target adjudication, parity oracle) is minted as a follow-up WP/mission once the ADR lands. Re-check the gate at tasks-finalize; if the ADR merged meanwhile, WP03's scope grows per FR-012.")

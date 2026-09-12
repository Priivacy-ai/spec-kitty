# Decision Moment `01M1VAHS32VMZPYYXWKW7D2KPG`

- **Mission:** `dead-port-disposition-01M1TZVN`
- **Origin flow:** `plan`
- **Slot key:** `plan.residue.decision-py-owner`
- **Input key:** `decision_py_dead_readers_owner`
- **Status:** `resolved`
- **Created:** `2026-09-06T12:19:35.138249+00:00`
- **Resolved:** `2026-09-06T12:20:23.650997+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

OD9: decision.py dead DSL readers (derive_mission_state, evaluate_guards): Mission A WP05 lane (open now) or a small Mission B WP owning decision.py alone after A merges?

## Options

- Mission B follow-up WP after A merges
- Mission A WP05 lane now
- Other

## Final answer

Mission B WP04: a small WP that owns runtime/next/decision.py alone and deletes derive_mission_state (:187) and evaluate_guards (:218) plus tests/next/test_decision_unit.py's legacy section; sequenced after Mission A merges into the branch (mission-level ordering, C-001). Rationale: Mission A's WP05 is claimed and running with a deliberately small scope ('land small, land early' to free Mission B's files); adding a deletion rider mid-flight risks its review; the runtime ledger keeps the mission_v1 edge via next_invocation_lifecycle.py:332 so no ledger edit is triggered.

## Rationale

_(none)_

## Change log

- `2026-09-06T12:19:35.138249+00:00` — opened
- `2026-09-06T12:20:23.650997+00:00` — resolved (final_answer="Mission B WP04: a small WP that owns runtime/next/decision.py alone and deletes derive_mission_state (:187) and evaluate_guards (:218) plus tests/next/test_decision_unit.py's legacy section; sequenced after Mission A merges into the branch (mission-level ordering, C-001). Rationale: Mission A's WP05 is claimed and running with a deliberately small scope ('land small, land early' to free Mission B's files); adding a deletion rider mid-flight risks its review; the runtime ledger keeps the mission_v1 edge via next_invocation_lifecycle.py:332 so no ledger edit is triggered.")

# Decision Moment `01KQAVR8S1299R9N67BTFAD67Q`

- **Mission:** `charter-contract-cleanup-tranche-1-01KQATS4`
- **Origin flow:** `plan`
- **Slot key:** `plan.ci.mypy-availability-policy`
- **Input key:** `mypy_availability_policy`
- **Status:** `resolved`
- **Created:** `2026-04-28T20:16:10.017601+00:00`
- **Resolved:** `2026-04-28T20:20:57.288223+00:00`
- **Other answer:** `false`

## Question

How should the CI 'e2e-cross-cutting' job handle the mypy dependency for tests/cross_cutting/test_mypy_strict_mission_step_contracts.py?

## Options

- install_mypy_in_job
- skip_with_clear_message
- fail_with_actionable_error
- Other

## Final answer

install_mypy_in_job — install mypy in the e2e-cross-cutting CI job rather than weakening or reclassifying the test. The test enforces a real contract; CI must provide the dependency and keep the signal. Aligns with the charter's 'mypy --strict must pass' policy.

## Rationale

_(none)_

## Change log

- `2026-04-28T20:16:10.017601+00:00` — opened
- `2026-04-28T20:20:57.288223+00:00` — resolved (final_answer="install_mypy_in_job — install mypy in the e2e-cross-cutting CI job rather than weakening or reclassifying the test. The test enforces a real contract; CI must provide the dependency and keep the signal. Aligns with the charter's 'mypy --strict must pass' policy.")

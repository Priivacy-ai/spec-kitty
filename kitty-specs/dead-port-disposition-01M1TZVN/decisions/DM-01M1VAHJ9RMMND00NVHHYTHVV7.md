# Decision Moment `01M1VAHJ9RMMND00NVHHYTHVV7`

- **Mission:** `dead-port-disposition-01M1TZVN`
- **Origin flow:** `plan`
- **Slot key:** `plan.dsl.events-home`
- **Input key:** `events_module_home`
- **Status:** `resolved`
- **Created:** `2026-09-06T12:19:28.184165+00:00`
- **Resolved:** `2026-09-06T12:20:16.994558+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

OD4: events.py stays at specify_cli.mission_v1.events (rewrite package docstring) or relocates (touches two runtime lazy imports, seam test, runtime ledger)?

## Options

- Stay; rewrite docstring
- Relocate under status/
- Other

## Final answer

Stay at specify_cli.mission_v1.events; rewrite the package docstring to stop advertising the DSL; __init__ re-exports only emit_event/read_events. Rationale: relocation touches two runtime lazy imports (next_invocation_lifecycle.py:332, decision.py:200), the seam test, and the runtime ledger entry 'mission_v1' (test_layer_rules.py:194) — runtime files adjacent to Mission A; not worth it for a one-module package. Follow-up candidate for Mission D (runtime facade).

## Rationale

_(none)_

## Change log

- `2026-09-06T12:19:28.184165+00:00` — opened
- `2026-09-06T12:20:16.994558+00:00` — resolved (final_answer="Stay at specify_cli.mission_v1.events; rewrite the package docstring to stop advertising the DSL; __init__ re-exports only emit_event/read_events. Rationale: relocation touches two runtime lazy imports (next_invocation_lifecycle.py:332, decision.py:200), the seam test, and the runtime ledger entry 'mission_v1' (test_layer_rules.py:194) — runtime files adjacent to Mission A; not worth it for a one-module package. Follow-up candidate for Mission D (runtime facade).")

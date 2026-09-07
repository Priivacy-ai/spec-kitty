# Decision Moment `01M1V80R6F6RTMR7Y3C2WBKR32`

- **Mission:** `fsm-write-path-integrity-01M1TZV6`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.named-orchestrator`
- **Input key:** `named_orchestrator`
- **Status:** `resolved`
- **Created:** `2026-09-06T11:35:20.015774+00:00`
- **Resolved:** `2026-09-06T11:44:13.470647+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Q4: Which surface is NAMED the one orchestrator for status writes: MissionStatus (the aggregate, per Accepted ADR chain #1667/C-004) composed over the promoted status-owned pipeline, or the pipeline itself with the aggregate as one caller?

## Options

- MissionStatus aggregate over the pipeline (debrief recommendation)
- The pipeline itself; aggregate is one caller
- Other

## Final answer

Option 2 with rider: the promoted status-owned pure pipeline is the named single validation-and-event-build authority; exactly two composition shells (flat/primary in status/emit, transactional in coordination) keep lock/commit/fan-out ordering with explicit per-shell failure policies (C-007). MissionStatus remains the intended domain facade for callers but is NOT the write chokepoint until a later caller-migration mission; the 8 direct transactional callers do not migrate in WP02. Record as an amendment note to the #1667/C-004 ADR chain (directive 003) in the WP02 design note. Evidence: AST scan shows aggregate has 1 production caller, transactional door 8+2, plain door 0 outside fallback arms; aggregate's lazy coordination import is the C-006 precedent violation.

## Rationale

_(none)_

## Change log

- `2026-09-06T11:35:20.015774+00:00` — opened
- `2026-09-06T11:44:13.470647+00:00` — resolved (final_answer="Option 2 with rider: the promoted status-owned pure pipeline is the named single validation-and-event-build authority; exactly two composition shells (flat/primary in status/emit, transactional in coordination) keep lock/commit/fan-out ordering with explicit per-shell failure policies (C-007). MissionStatus remains the intended domain facade for callers but is NOT the write chokepoint until a later caller-migration mission; the 8 direct transactional callers do not migrate in WP02. Record as an amendment note to the #1667/C-004 ADR chain (directive 003) in the WP02 design note. Evidence: AST scan shows aggregate has 1 production caller, transactional door 8+2, plain door 0 outside fallback arms; aggregate's lazy coordination import is the C-006 precedent violation.")

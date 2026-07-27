# Contract: force-provenance on backward transitions (FR-015)

## Rule

`build_transition_plan` (`tasks_transition_core.py:218-219`) MUST NOT auto-promote `emit_force` on a
backward edge that the FSM accepts **force-free given the supplied evidence**. Decide by asking the FSM,
not by a hard-coded edge list:

```
if not force and _is_backward_transition(old, target):
    legal_force_free, _ = validate_transition(old, target, ctx_with_evidence)  # force=False
    emit_force = not legal_force_free      # only promote when the FSM genuinely requires it
```

## The five evidence-gated exempt edges (confirmatory/illustrative — NOT the implementation surface)

> The mechanism is the FSM query above; this table documents the *expected* result and MUST NOT be
> encoded as a hard-coded edge list (it would rot if the matrix changes — FR-015 / close-by-construction).

| Edge | Required evidence |
|---|---|
| `in_progress → planned` | `reason` |
| `approved → in_progress` | `review_ref` |
| `approved → planned` | `review_ref` |
| `in_review → in_progress` | structured `review_result` (reviewer+verdict+reference) |
| `in_review → planned` | structured `review_result` |

Evidence is **edge-specific and not interchangeable** (a scalar reason is rejected on the `in_review→*`
edges, `wp_state.py:624`). Genuinely force-requiring backward edges (e.g. leaving terminal
`done`/`canceled`, and all `for_review→*`/`claimed→*` rewinds) keep `force` truthfully.

## Persisted-layer assertion (SC-007)

The gate is the **persisted** `StatusEvent.force` on `status.events.jsonl` after driving the **real
move-task entry point** — not the plan object. Existing plan-level assertions
(`test_tasks_transition_core.py:527,532,542`, `test_tasks_backward_emit.py`,
`test_status_e2e_integration.py`, `test_status_cli.py`) are **re-pointed** to the correct expected
values (falsy for the five edges; a retained genuine-force edge as a truthy positive control) — never
deleted. Distinct from `spec-kitty-saas#509` (server transition matrix).

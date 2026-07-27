# Contract — Dead-code gate: first-party dynamic-access awareness (IC-01 / FR-001, FR-002)

## Behaviour
- GIVEN a first-party symbol referenced only via `module.attr` dynamic access (e.g. `_runtime_bridge_module().get_or_start_run`),
  WHEN the dead-code scanner classifies it,
  THEN it MUST be classified **live** (a reference site exists), NOT dead.
- GIVEN a symbol with no static import and no first-party dynamic access,
  WHEN classified,
  THEN it MUST be classified **dead** (the negative direction still holds).

## Non-fakeable evidence
- Focused AST tests exercise BOTH directions (dynamic-access→live, unreferenced→dead) against fixtures, not the live tree only.
- At least the 4 known `runtime.next.runtime_bridge` façade symbols (`get_or_start_run`, `query_current_state`, `answer_decision_via_runtime`, `QueryModeValidationError`) are removed from the permanent allowlist and pass as recognised-live.

## Anti-goals
- Do NOT widen liveness to *any* attribute access (would mask real dead code); scope to first-party module resolution.
- Do NOT special-case `runtime_bridge` by name — resolve the dynamic-accessor shape generally.

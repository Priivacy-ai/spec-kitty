# Contract — `spec-kitty next` decision JSON output

**Owning WP**: WP04
**Backing FR**: FR-019, FR-020, FR-021

## Invariants

The decision JSON returned by `spec-kitty next --json` MUST satisfy:

1. **No implicit success**. A bare call (no `--result`) MUST NOT set
   `result=success` server-side. The runtime treats `result is None` as
   *query*, not *outcome*. (FR-019)
2. **No `unknown` mission state**. For a valid mission run with persisted
   state, `mission_state` MUST be set to a real state from the mission's
   state machine (`discovering`, `specifying`, `planning`, `tasking`,
   `implementing`, `reviewing`, `accepting`, or `done`). It MUST NOT be the
   string `"unknown"`. (FR-020)
3. **No `[QUERY - no result provided]`**. The decision JSON's
   `prompt_file`, `reason`, and `question` fields MUST NOT contain that
   placeholder. (FR-020)
4. **Structured blocked decision on resolution failure**. When the runtime
   cannot determine the next step (missing artifact, failing guard,
   ambiguous WP graph), it returns `kind="blocked"` with a concrete
   `reason` and a populated `guard_failures` list. (FR-020)
5. **Mission YAML schema validates**. The shipped `plan` mission's
   `mission-runtime.yaml` MUST validate against the runtime schema. The
   contract test loads the file and asserts. (FR-021)

## JSON shape (informative)

```json
{
  "kind": "step | decision_required | blocked | terminal",
  "agent": "claude | codex | gemini | ...",
  "mission_slug": "<slug>",
  "mission": "<mission-type-key>",
  "mission_state": "<state-from-mission-state-machine>",
  "action": "specify | plan | ... | implement | review | accept",
  "wp_id": "<str | null>",
  "workspace_path": "<path | null>",
  "prompt_file": "<absolute path | null>",
  "reason": "<str | null>",
  "guard_failures": [],
  "progress": { "...": "..." },
  "run_id": "<ulid>",
  "step_id": "<id>",
  "decision_id": "<ulid | null>",
  "question": "<str | null>",
  "options": null
}
```

## Tests

- `tests/contract/test_next_no_implicit_success.py` — bare call does not
  advance state.
- `tests/contract/test_next_no_unknown_state.py` — for a fixture mission,
  `mission_state != "unknown"`.
- `tests/contract/test_plan_mission_yaml_validates.py` — schema validation.

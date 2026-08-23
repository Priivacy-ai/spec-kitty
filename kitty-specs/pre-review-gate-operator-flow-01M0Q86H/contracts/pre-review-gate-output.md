# Contract: Public Pre-Review Gate Output

## Human mode

### Running

- announce gate start within 1 second;
- receive a typed `scope_assessed` event and, if classification is unknown, state before launch that it will run under the existing timeout;
- while the process remains active, emit elapsed liveness at least every 30 seconds;
- emit exactly one final outcome.

### Oversized refusal

The final output must state:

- validation did not start because the scope is explicitly oversized;
- the normalized target(s) and effective budget;
- the work package remains in its prior lane;
- recovery choices: bounded `pre_review_test_scope` or explicit `--skip-pre-review-gate`.

### Unknown timeout

The final output must state:

- timeout and unknown classification;
- normalized scope identity and targets;
- configured effective budget and monotonic-clock observed elapsed time;
- unchanged lane;
- evidence is a candidate for a reviewed metadata update, not an automatic classification.

## Structured mode

Stdout contains exactly one final JSON document. There are no progress JSON objects and no human heartbeat text mixed into stdout.

The existing `pre_review_gate` object is extended additively:

```json
{
  "outcome": "timed_out",
  "reason": "...",
  "test_targets": ["tests/example"],
  "run_state": "timed_out",
  "budget_classification": "unknown",
  "scope_identity": "...",
  "effective_budget_seconds": 300,
  "matched_budget_rule": null,
  "classification_candidate": true,
  "observed_elapsed_seconds": 300.0,
  "classification_guidance": "Propose a reviewed metadata update if evidence shows structural oversize"
}
```

The final envelope carries authoritative top-level `transition_applied: false`. Oversized refusal uses nested `outcome: "scope_oversized"`, `run_state: "not_started"`, `classification_candidate: false`, and both recovery choices. Existing skip, disable, warning, block, success, timeout, and cancellation fields remain compatible.

The existing top-level `transition_applied` field is authoritative. Whenever a nested mirror is present inside `pre_review_gate`, tests require equality with the top-level value.

## Precedence

1. explicit per-invocation skip;
2. first truthy canonical disable variable;
3. scope-budget assessment;
4. gate execution and terminal/block/warn aggregation;
5. transition application.

No refusal or timeout may report a successful transition.

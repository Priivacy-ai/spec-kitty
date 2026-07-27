# #1141 Hypothesis 4 (fixture state error) — RULED OUT

**Claim**: The scenario 4 fixture does not actually advance the WP to `in_review`, so the rollback runs against a different lane state.

## Evidence against

The captured failure quoted in `mission-exception.md` records:

```
AssertionError: peeked row is not the rollback we triggered:
  from='for_review' to='in_review' payload=...
  at test_scenario_4_review_rejection_contract.py:543
```

The peeked row is `for_review → in_review`. That is the canonical forward transition into `in_review`. If the WP never reached `in_review`, the queue would not contain a `for_review → in_review` row at all. Its presence proves the fixture **did** advance the WP all the way to `in_review`.

The scenario 4 fixture (`tests/identity_boundary/test_scenario_4_review_rejection_contract.py`, lines 300–540) is also structurally explicit: it walks the WP through `planned → claimed → in_progress → for_review → in_review` via four sequential `move-task` calls, each verified via `--json` parse before proceeding. The implementation reads as a properly sequenced chain, not as a "fire and forget then immediately rollback" flow.

## Verdict

**RULED OUT.** The fixture reaches `in_review` as designed. The failure is downstream of the fixture.

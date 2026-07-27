# Contract: merge --dry-run review-artifact consistency gate (issue #991)

## Inputs

```
spec-kitty merge --mission <handle> --dry-run [--json]
```

Mission state: at least one WP has lane `approved` AND its latest `tasks/<WP>/review-cycle-N.md` artifact has `verdict: rejected` (or otherwise fails `find_rejected_review_artifact_conflicts()`).

## Output (failure path, --json)

- Exit code: non-zero.
- JSON payload includes `REJECTED_REVIEW_ARTIFACT_CONFLICT` under the same key the real merge uses (typically a `blockers` / `errors` array).
- Each entry identifies the offending `wp_id` and the offending review-cycle file path.
- Diagnostic payload shape MUST match the real merge's emission of the same conflict (consumers should not need to branch on dry-run vs. real-merge JSON).

## Output (failure path, human / non-JSON)

- Exit code: non-zero.
- Human output contains a clearly-labeled `REJECTED_REVIEW_ARTIFACT_CONFLICT` line that names the offending WP.

## Output (success path)

- Unchanged from today: existing dry-run preview is emitted with no behavior change.

## Invariants

- Dry-run and real merge MUST share a single helper that calls `find_rejected_review_artifact_conflicts()`.
- Existing tests in `tests/post_merge/test_review_artifact_consistency.py` and `tests/merge/test_merge_post_merge_invariant.py` remain green.
- The success path of dry-run produces no new false-positive blockers (spec C-002).

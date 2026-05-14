# Contract: lightweight review missing-baseline diagnostic (issue #989)

## Inputs

```
spec-kitty review --mission <handle> --mode lightweight
```

Mission state: `meta.json` has `mission_id` set (modern mission), `baseline_merge_commit` is `null`.

## Output (failure path, modern mission)

- Exit code: non-zero.
- Verdict: non-passing.
- Structured diagnostic emitted with code `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`.
- Payload fields:
  - `code`: `"LIGHTWEIGHT_REVIEW_MISSING_BASELINE"`
  - `mission_id`: canonical ULID
  - `mission_slug`: human slug
  - `remediation`: string containing the substring `baseline_merge_commit`

## Output (legacy mission, no `mission_id` in meta.json)

- Exit code: zero (preserves historical behavior).
- Verdict: passing, but tagged with `LEGACY_MISSION_DEAD_CODE_SKIP` so the path is greppable and discoverable.

## Output (modern mission, `baseline_merge_commit` populated)

- Unchanged from today: dead-code scan runs normally.

## Invariants

- Modern missions with `baseline_merge_commit: null` MUST NOT exit zero with a clean pass.
- The diagnostic code is referenced at least once in production source and once in tests so `rg "LIGHTWEIGHT_REVIEW_MISSING_BASELINE"` returns hits in both surfaces (NFR-004).

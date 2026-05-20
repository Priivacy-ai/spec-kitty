# Re-Activation Plan

## Trigger

Both **spec-kitty#1141** AND **spec-kitty#1182** are closed on `origin/main` AND a post-rc15 RC (v3.2.0rc16+) is published to PyPI.

## State Machine Operations

1. **WP01** — move back to planned:
   ```
   spec-kitty agent tasks move-task WP01 --to planned --force \
     --note "Re-activating: blockers now closed" \
     --mission phase4-canary-gate-01KS1W46
   ```
2. **WP02** — move back to planned: same pattern as WP01.
3. **WP03** — do NOT move back unless SaaS health state has changed. Verify `/health/ready/` is still 200 and drain counts are unchanged before using cached result.
4. **WP04** — move back to planned: same pattern as WP01.
5. **WP05–WP08** — move back to planned: same pattern as WP01.

## Re-Execution Sequence

| Step | Action |
|------|--------|
| 1 | Re-implement WP01 (T001-T006 in full — T004-T006 can now execute since merge commits exist) |
| 2 | Re-implement WP02 (T007-T012 in full — install rc16) |
| 3 | Verify WP03 cached result, or re-run if SaaS redeployed |
| 4 | Re-implement WP04 (T017-T023 in full — run `--single` canary with rc16) |
| 5–8 | WP05–WP08 in sequence (depend on WP04 passing) |

## Pre-Step-4 Harness Investigation

Before Step 4, investigate the 2 failing harness tests in `test_harness_sync_and_ids.py` (see RISK-2 in mission review). Determine whether they affect live canary execution before proceeding.

## WP03 Re-Preflight Rule

If more than 24 hours have elapsed since the WP03 snapshot (captured 2026-05-20), re-run WP03 before WP04 regardless of approved state.

## gh Issue Reopen Guard

When T023 fires (canary failure), check issue state before reopening:

```
gh issue view <N> --json state
```

If `state` is already `OPEN`, skip `gh issue reopen` and add a comment only.

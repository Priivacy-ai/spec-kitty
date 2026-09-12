---
affected_files: []
cycle_number: 3
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-11T16:04:43Z'
reviewer_agent: user
wp_id: WP07
---

# WP07 cycle-2 independent reviewer feedback

Verdict: CHANGES REQUIRED for candidate
`949268f8e50a4cc19bf6fae1f405354442ccf883`.

## Blocking finding

The cycle-1 remediation introduced a strict-type-check regression at
`src/specify_cli/delivery/ledger.py:181-184`. When the complete 22-module WP07
source surface is checked in one strict mypy invocation, the cast around
`list_delivery_attempt_projections(self._unit)` fails as redundant:

```text
src/specify_cli/delivery/ledger.py:181: error: Redundant cast to
"list[DeliveryAttemptProjection]"  [redundant-cast]
Found 1 error in 1 file (checked 22 source files)
```

The line was introduced by remediation commit `99a78d9b2` and belongs to WP07.
Remove or replace the cast so both the isolated module and aggregate 22-module
strict checks pass.

## Passing evidence

- Recovered authoritative selected-path gate: 1539 passed, 1 skipped,
  2 xfailed, 1 unchanged tracker coroutine warning in 116.71 seconds.
- Ruff check and format: all 67 WP07 Python files passed.
- Cycle-1 fixture, global policy-refusal parking, `project_refused`, generic
  413 target scope, and #3108 positive blockers are closed non-vacuously.
- T031-T035 contract, security, recovery, correlation, ownership, and refreshed
  WP07 to WP08/WP10 dependency review found no additional blocker.
- No WP08 product or baseline artifact was changed by the review.

The canonical structured record is `review-cycle-2.md`; this temporary file is
the underlying independent reviewer feedback source required by the lifecycle
guard.

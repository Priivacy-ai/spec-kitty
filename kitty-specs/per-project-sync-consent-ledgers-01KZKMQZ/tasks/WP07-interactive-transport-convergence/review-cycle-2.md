---
affected_files:
- src/specify_cli/delivery/ledger.py
cycle_number: 2
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command: >-
  mypy --strict --no-incremental <the 22 WP07 source modules changed between
  e510ec74b..e46fecebd plus src/specify_cli/delivery/ledger.py from 99a78d9b2>
reviewed_at: '2026-08-11T16:33:00Z'
reviewer_agent: codex
wp_id: WP07
---

# WP07 whole-work-package review — changes requested

Reviewed candidate: `949268f8e50a4cc19bf6fae1f405354442ccf883`.

Reviewer: Reviewer Renata / codex, independent whole-WP review.

## Verdict

Changes requested. All cycle-1 behavioral blockers are closed, but the cycle-2
remediation introduces a strict-type-check regression in a WP07-owned source
file. The charter's review checklist requires strict mypy to pass.

## Blocking finding

### The remediation's attempt-row cast fails the whole-WP strict gate

`src/specify_cli/delivery/ledger.py:181-184` wraps
`list_delivery_attempt_projections(self._unit)` in a cast to
`list[DeliveryAttemptProjection]`. When the 22 WP07 source modules are checked
together, mypy sees the function's declared return type and reports:

```text
src/specify_cli/delivery/ledger.py:181: error: Redundant cast to
"list[DeliveryAttemptProjection]"  [redundant-cast]
Found 1 error in 1 file (checked 22 source files)
```

This line was introduced by cycle-1 remediation commit `99a78d9b2` and is owned
by WP07. A narrow one-file invocation does not expose it because the repository
configuration skips imported `specify_cli.*` modules; checking the complete
changed source surface does. Remove the redundant cast (or otherwise type the
boundary without producing either an `Any` return in the isolated check or a
redundant-cast error in the aggregate check), then rerun strict mypy over all 22
WP07 source modules in one invocation.

## Verification evidence

The recovered authoritative selected-path gate otherwise passes exactly:

```text
1539 passed, 1 skipped, 2 xfailed, 1 warning in 116.71s
```

The warning is the unchanged tracker coroutine warning from
`tests/sync/tracker/test_local_service.py::TestSyncOperations::test_sync_pull_delegates_to_connector`.
Ruff check and Ruff format pass all 67 WP07 Python files; `git diff --check`
passes. The prior fixture, terminal-parking, `project_refused`, generic-413, and
#3108 positive blockers are non-vacuously closed. Contract/security and recovery
inspection found no further blocker: authorization remains header-only; exact
project/audience/generation/native correlation and UNKNOWN recovery are covered;
no independent grant/store or raw emitter seam was added; and the refreshed
WP07→WP08/WP10 dependency analysis is truthful. No WP08 product or baseline
artifact was changed by this review.

## Anti-pattern checklist

- Dead code: PASS — no dead production seam found; the redundant cast is the
  separate strict-static blocker above.
- Synthetic fixture: PASS — the repaired suites exercise production project
  stores, receiver/dispatcher attempts, correlated I/O, and fresh UoWs.
- Silent empty return: PASS — no new failure-obscuring empty return found.
- FR coverage: PASS — the selected-path gate covers T031–T035 and all prior
  cycle-1 regressions.
- Frozen surface: PASS — pinned SaaS Event/body/LocalCommit contracts remain
  preserved.
- Locked decisions: PASS — no query-token auth, ambient authority,
  request-wide proof, private parser, or raw WebSocket bypass found.
- Shared-file ownership: PASS — the product delta is covered by WP07 ownership;
  shared `sync.py` sequencing to WP10 is explicit.
- Production fragility: PASS — no new transport/recovery fragility found.

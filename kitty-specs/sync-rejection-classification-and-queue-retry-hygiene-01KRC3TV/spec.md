# Spec: Sync Rejection Classification And Queue Retry Hygiene

## Purpose (TL;DR)

Stop incrementing `retry_count` for batch-level auth/teamspace failures. After the
private-Teamspace ingress hardening, the typical shared-team 403 path is fixed,
but if a POST still returns 401/403 (auth_expired, unauthorized, or
direct_ingress_missing_private_team) after events were drained from the queue,
`queue.process_batch_results()` still flags those events as `rejected` and bumps
`retry_count`. These are batch-level (not per-event) failures: the server never
inspected individual rows, so per-event retry attribution is incorrect and
eventually poisons the queue.

## Context

GitHub issue: Priivacy-ai/spec-kitty#889.

Today, in `src/specify_cli/sync/batch.py`, when a batch POST fails with HTTP
401/403/5xx the CLI walks every drained event and records:

```python
BatchEventResult(
    event_id=...,
    status="rejected",
    error=...,
    error_category=<auth_expired | unauthorized | direct_ingress_missing_private_team | server_error>,
)
```

It then calls `queue.process_batch_results(result.event_results)`, which in
`queue.py` runs:

```sql
UPDATE queue SET retry_count = retry_count + 1
WHERE event_id IN (...)
```

That is fine for events the server actually evaluated and refused (per-event
rejections returned in a 200 response body), but it is wrong for:

| Category | Reality |
|----------|---------|
| `auth_expired` (401) | Token issue; events were never adjudicated |
| `unauthenticated` | Same as above |
| `unauthorized` (403, not teamspace) | Permission issue; server didn't reach event validation |
| `direct_ingress_missing_private_team` (403) | Private Teamspace not provisioned for this user |
| `server_error` (5xx) | Server fault; events were not evaluated |
| `retryable_transport` (timeout, connection) | Network fault; same as above |

For these categories, the queue should treat the events as **non-mutating** —
do not bump `retry_count`. Events must remain durably queued for a later drain
once the operator fixes auth, the teamspace is provisioned, or the server
recovers.

`failed_permanent` (e.g. oversized event) and `rejected` (per-event 200-response
rejection because the server actually validated and refused that row) keep their
existing behavior.

## In Scope

- Classify the following categories as **batch-level / non-mutating**:
  `auth_expired`, `unauthenticated`, `unauthorized`,
  `direct_ingress_missing_private_team`, `server_error`, `retryable_transport`.
- Extend `BatchEventResult` to carry a new status `"failed_transient"` (or
  equivalent) so `process_batch_results` can distinguish per-event content
  rejections (`rejected`, retry_count bumped) from batch-level transient
  failures (`failed_transient`, retry_count untouched).
- Update every call site in `batch.py` that records `status="rejected"` with
  one of the batch-level categories to use the new transient status instead.
- Update `process_batch_results` so:
  - `success` / `duplicate` / `failed_permanent` → DELETE from queue.
  - `rejected` → bump `retry_count` (true per-event content rejection).
  - `failed_transient` → no mutation (leave row untouched for next drain).
- Add focused regression tests under `tests/sync/` proving:
  - 401 batch POST: `retry_count` does not advance for queued events.
  - 403 with `direct_ingress_missing_private_team`: `retry_count` unchanged.
  - 403 generic (unauthorized): `retry_count` unchanged.
  - 5xx: `retry_count` unchanged.
  - 200 response with per-event rejections: `retry_count` still increments
    (existing behavior preserved).
- Keep operator-facing stdout/log output clear and unchanged in tone; only the
  queue-mutation semantics change.

## Out of Scope

- Changing categorization keyword lists or summary formatting.
- Daemon backoff/scheduling for transient failures (the queue stays as-is; the
  daemon will retry naturally on its next tick).
- Body queue (`body_queue.py`) — different retry path, not in this mission.

## Acceptance Criteria

1. New tests under `tests/sync/` cover all categories above. Each asserts both
   `BatchEventResult.error_category` and the post-call `retry_count` for the
   affected queue rows.
2. `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/ -q` passes for the
   tests we add and does not regress any tests previously passing (the seven
   pre-existing, infrastructure-related failures remain out of scope).
3. `process_batch_results` no longer bumps `retry_count` for batch-level auth /
   teamspace / 5xx / transport failures.
4. Existing per-event content-rejection semantics (status `rejected` from the
   200-response body) continue to bump `retry_count` exactly as before.
5. Operator-facing summary lines (e.g. `format_sync_summary`) still surface the
   categorized failure clearly.

## Functional Requirements

- **FR-1** `BatchEventResult` MUST distinguish per-event content rejection
  (`rejected`) from batch-level transient failure (`failed_transient`).
- **FR-2** `OfflineQueue.process_batch_results` MUST NOT bump `retry_count`
  for `failed_transient` results.
- **FR-3** Batch HTTP 401 responses MUST classify every drained event as
  `failed_transient` with category `auth_expired`.
- **FR-4** Batch HTTP 403 responses where the body matches
  `direct_ingress_missing_private_team` MUST classify every drained event as
  `failed_transient` with that category.
- **FR-5** Batch HTTP 403 responses that do NOT match teamspace messaging MUST
  classify events as `failed_transient` with category `unauthorized`.
- **FR-6** Batch HTTP 5xx responses MUST classify events as `failed_transient`
  with category `server_error`.
- **FR-7** Timeout / connection / network failures MUST classify events as
  `failed_transient` with category `retryable_transport`.
- **FR-8** The "skipped: no Private Teamspace" pre-flight path (`_team_slug`
  returns `None`) MUST classify events as `failed_transient` with category
  `direct_ingress_missing_private_team`.
- **FR-9** Per-event content rejections from a 200 response MUST continue to
  produce `rejected` results that bump `retry_count`.
- **FR-10** `failed_permanent` semantics (oversized events) remain unchanged.

## Non-Functional Requirements

- **NFR-1** No new dependencies.
- **NFR-2** Changes confined to `src/specify_cli/sync/batch.py`,
  `src/specify_cli/sync/queue.py`, and `tests/sync/`.
- **NFR-3** Operator-facing stdout in `format_sync_summary` must continue to
  list categories and counts; transient and content-rejection counts may both
  appear under `failed_results` for summary purposes.

## Risks

- A consumer that reads `BatchEventResult.status` and expects only the existing
  three values could break. Mitigation: the only consumer in-tree is
  `process_batch_results` plus formatting helpers; both are updated in this
  mission.
- If a future caller forgets to call `process_batch_results`, transient events
  will simply be drained from local memory but stay in SQLite — same as today.

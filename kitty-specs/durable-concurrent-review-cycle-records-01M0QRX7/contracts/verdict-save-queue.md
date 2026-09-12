---
divio_type: reference
audience: automation-agent
updated: 2026-08-23
---

# Contract: Verdict Save Queue and Persistence Result

## Scope

This is an internal Python/CLI contract, not a network API. It governs automatic verdict evidence saves only.

## Queue contract

```text
acquire_verdict_save_queue(repository, timeout_seconds=10.0)
```

- Resolve the key from the canonical Git common directory.
- Wait in line for no longer than `timeout_seconds` using monotonic elapsed time.
- Return a context manager that releases on normal exit, exception, or process termination through OS lock cleanup.
- Raise a typed busy error on timeout.
- Do not retry the verdict operation, spawn a service, or acquire the queue while holding the mission status lock.
- `--no-auto-commit` must not call this contract.
- Command orchestration is the sole acquisition owner. The evidence persistence operation is invoked inside the lease and must never reacquire the queue.

## Automatic-save outcomes

| Condition | Exit | Classification | Durable flag | Evidence behavior |
|---|---:|---|---:|---|
| Evidence commit and destination read-back succeed; event append succeeds | 0 | `durable` | true | Return stable evidence reference. |
| Queue unavailable after 10 seconds | nonzero | `busy` | false | No evidence/event mutation. |
| Router returns error or wrong-surface no-op | nonzero | `persistence_failed` | false | Retain written artifact and return its path. |
| Router raises | nonzero | `persistence_failed` | false | Retain written artifact and return its path. |
| Router says unchanged without verified identical destination content | nonzero | `persistence_failed` | false | Retain written artifact. |
| Event append fails after verified evidence commit | nonzero | `persistence_failed` | false | After the event status lock is released, first run the existing evidence-deletion compensator under the queue. Successful compensation removes evidence; only loud compensation failure or an explicit future policy change may leave non-current history. Never claim verdict success. |
| Explicit `--no-auto-commit` | 0 | `local_only` | false | Preserve local evidence and `no_auto_commit` reason. |

## Machine-readable response requirements

Every result includes:

- `result`: success only for `durable` or explicitly requested `local_only`.
- `verdict_durably_persisted`: boolean derived from verified outcome, never configuration.
- `durability_classification`: stable classification from the table above.
- `durability_reason`: stable reason for every false durability flag.
- `evidence_ref`: stable governed path when an artifact exists.
- `destination_ref`: placement-selected ref for durable success.

Busy and persistence failures must use a nonzero command exit and an error envelope. Human-readable output must convey the same classification.

## Retry contract

- The CLI performs no automatic business retry.
- An operator may resubmit after contention clears.
- An identical retry adopts the retained record, preserving its path and bytes.
- If that identical record is already present at the governed destination, read-back verification makes the retry idempotent.
- A different reviewer/body/affected-file submission must not adopt the retained record.

## Concurrency acceptance contract

For every synchronized pair, the only valid terminal states are:

1. two durable successes with distinct evidence references; or
2. one durable success and one explicit nonzero refusal caused by a measured 10-second queue timeout or an independently valid state-machine prohibition.

At least one deterministic concurrent case must keep both submissions state-valid, release the first queue lease within 10 seconds, and prove that the waiting second submission also completes durably. A sequential two-success proxy does not satisfy this contract.

Every durable success must be proven by both an event-history reference and `git show` of matching evidence at the governed destination ref.

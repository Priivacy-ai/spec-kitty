---
divio_type: reference
audience: agentic-framework-core-team
updated: 2026-08-23
---

# Data Model: Durable Verdict Saves

## VerdictCommitQueue

Checkout-wide synchronization primitive for automatic review evidence commits.

| Field | Type | Rule |
|---|---|---|
| `git_common_dir` | absolute path | Resolve through the canonical Git topology helper. |
| `lock_path` | absolute path | Mission-independent stable filename below the common directory. |
| `timeout_seconds` | float | Defaults to exactly `10.0`; must be positive. |
| `acquired_at` | monotonic timestamp | Process-local diagnostic only; never persisted as authority. |

Relationships: one queue covers every mission and linked worktree sharing a Git common directory; independent clones have independent queues.

## ReviewCycleEvidence

Existing durable evidence-content entity, extended only with pending/adoption lifecycle behavior.

| Field | Type | Rule |
|---|---|---|
| `mission` | mission identity | Must match the active mission. |
| `work_package` | WP identity | Must match the submitted WP. |
| `cycle` | positive integer | Allocated under the short mission status lock. |
| `reviewer` | string | Part of identical-submission matching. |
| `body` | rendered evidence | Part of identical-submission matching. |
| `affected_files` | ordered/canonical collection | Part of identical-submission matching. |
| `path` | governed relative path | Stable pointer returned to the event/result. |
| `destination_ref` | Git ref | Selected by existing placement governance. |

The artifact does not own the verdict value. It remains authoritative only for review evidence content.

## VerdictPersistenceOutcome

Typed result carried from evidence persistence to the reviewer command.

| Field | Type | Rule |
|---|---|---|
| `classification` | enum | `durable`, `busy`, `persistence_failed`, or `local_only`. |
| `verdict_durably_persisted` | bool | True only for independently verified `durable`. |
| `evidence_ref` | optional path | Required for durable success and failures after a file was written. |
| `destination_ref` | optional ref | Required for durable success. |
| `reason` | optional stable code | Required for every non-durable outcome. |
| `message` | human-readable text | Must not contradict classification. |

## State transitions

```text
requested
├── --no-auto-commit ───────────────> local_only
└── automatic
    ├── queue timeout ──────────────> busy
    └── queue acquired
        ├── adopt matching pending evidence
        └── allocate + write evidence
              ├── commit/read-back failure -> persistence_failed (artifact retained)
              └── committed/read-back verified -> evidence_durable
                    ├── event append succeeds -> durable
                    └── event append fails
                          ├── serialized compensation succeeds -> persistence_failed (evidence removed)
                          └── compensation fails loudly -> persistence_failed (evidence may remain non-current)
```

## Validation invariants

1. `durable` implies the event exists, references `evidence_ref`, and that exact content is reachable at `destination_ref`.
2. `busy` mutates neither evidence nor current-verdict state.
3. `persistence_failed` is never wrapped in a success result; a written artifact is retained and named.
4. `local_only` is successful only as an explicitly requested non-durable operation.
5. Two durable concurrent submissions have distinct evidence references.
6. An identical retry reuses the same pending evidence path and bytes; a non-identical retry never adopts it.
7. Current verdict is reduced only from event history; evidence content is read only from review-cycle records.
8. Command orchestration owns the queue lease. The evidence persistence operation never reacquires it, and event-failure compensation reacquires it only after the event status lock has been released.

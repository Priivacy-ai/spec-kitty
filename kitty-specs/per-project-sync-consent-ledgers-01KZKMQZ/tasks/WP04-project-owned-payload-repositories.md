---
work_package_id: WP04
title: Project-owned repositories and current-writer participation
dependencies:
- WP02
- WP03
requirement_refs:
- FR-002
- FR-006
- FR-010
- FR-017
- FR-018
- FR-021
- FR-022
- FR-028
- FR-029
- FR-032
- NFR-001
- NFR-004
- NFR-007
- C-002
- C-008
- C-009
planning_base_branch: feat/per-project-sync-consent
merge_target_branch: feat/per-project-sync-consent
branch_strategy: Planning artifacts for this mission were generated on feat/per-project-sync-consent. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/per-project-sync-consent unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/event_journal/journal.py
create_intent:
- tests/event_journal/test_project_store_journal.py
- tests/delivery/test_project_store_ledger.py
- tests/sync/test_project_store_outboxes.py
- tests/delivery/test_project_store_retention.py
execution_mode: code_change
owned_files:
- src/specify_cli/event_journal/journal.py
- src/specify_cli/event_journal/models.py
- src/specify_cli/event_journal/coalesce.py
- src/specify_cli/delivery/ledger.py
- src/specify_cli/delivery/selection.py
- src/specify_cli/delivery/retention.py
- src/specify_cli/delivery/status_report.py
- src/specify_cli/sync/queue.py
- src/specify_cli/sync/body_queue.py
- src/specify_cli/sync/__init__.py
- tests/architectural/test_project_store_boundary.py
- tests/architectural/test_egress_consent_boundary.py
- tests/event_journal/test_project_store_journal.py
- tests/delivery/test_project_store_ledger.py
- tests/sync/test_project_store_outboxes.py
- tests/delivery/test_project_store_retention.py
role: implementer
tags: []
tracker_refs:
- Priivacy-ai/spec-kitty#3262
---

## ⚡ Do This First: Load Agent Profile

Load the assigned implementation profile first:

```text
/ad-hoc-profile-load python-pedro
```

Then read WP02/WP03 outputs, the store layout contract, and all existing #3030 journal, delivery, queue, purge, and status tests before changing constructors.

## Objective

Move every live event journal, delivery ledger/result, event outbox, and body/offline repository into the UUID-owned `sync.db` and outer unit of work. Component adapters become connection-free. Every current-version writer identified by WP01 must obtain WP02's generation-bound layout permit immediately before insert. Preserve #3030's independent selection, SQL identity, terminal parking, final-gate preparation, retention, and explicit purge defenses.

## Fixed boundaries

This WP changes storage, repository, writer-placement APIs, and `sync/__init__.py` exports; it does not implement network transport (WP06-WP09) or legacy cutover (WP10). There is no compatibility fallback to the shared journal/queue on a live path. Legacy sources remain read-only migration/diagnostic inputs.

Every payload row carries owner UUID, capture sequence, epoch ID, and stable native identity. Store context, not cwd or active target, selects the repository. A's unfiltered database queries must be physically incapable of returning B.

## Subtask T016 — Event journal conversion

Change `EventJournal` and coalescing to receive a ProjectSyncStore unit-of-work repository port rather than a path and private connection. Capture obtains/revalidates the layout permit immediately before insert and assigns sequence and epoch atomically. Verify event-declared UUID equals the store owner before payload insert.

Remove/restrict global resolver cache behavior from live APIs. Keep explicit
legacy read adapters for WP10 behind named migration mode only. Preserve stable
Event IDs, ordering, coalescing semantics, created timestamps, identity
projection, and blocked/archived state.

Tests must trap connection opens and show A capture never touches B, including same slug/different UUID and same UUID/shared worktrees.

## Subtask T017 — Delivery ledger, selection, and status

Convert `SqliteDeliveryLedger` into a repository over the unit of work. Any current legacy result/status writer obtains/revalidates the layout permit immediately before insert. Preserve stable statuses, attempts, target identities, duplicate/success semantics, terminal refusal, and pending selection order.

Rewrite selection to consume context and current epoch/capability, then retain:

- consent-bearing candidates;
- project UUID predicate in SQL;
- terminal rows excluded;
- final transport revalidation delegated to WP06;
- no starvation behind ineligible rows;
- sealed rows available only to confirmed HistoryDisclosureAction.

Status/diagnostics read exactly one explicit project store at a time and report decision, epoch, target/admission, migration, quarantine, and blocking reason without payloads/secrets.

## Subtask T018 — Event and body/offline outboxes

Refactor `OfflineQueue` and `OfflineBodyUploadQueue` as project-store repositories. Remove server/user/team-scoped database path ownership from live payload state; those values are target/audience attributes, not physical project identity.

Enqueue validates owner UUID, obtains/revalidates the layout permit immediately before insert, and assigns capture sequence/epoch in the outer transaction. Drain returns typed project-bound tasks. Mark-synced/retry/permanent operations validate ownership. Preserve queue caps, coalescing, failure categories, body hash/native identity, and stats.

Legacy scoped queue discovery remains WP10 input only and must not be opened by
normal constructors.

## Subtask T019 — Retention, explicit purge, and #3030 defenses

Adapt retention and purge to one project store/capability. Purge remains a separate explicit operation and reports exact before/after/selected/other-project differential. Opt-out never calls purge.

Retain tests proving:

- purging A deletes zero B rows/frames/bodies;
- terminal refusal stays parked across re-opt-in/target change;
- sealed history is not ordinary pending work;
- status cannot label unresolved identity as a consenting project;
- a consent-bearing batch and SQL UUID restriction remain independently load-bearing.

Do not preserve shared-store APIs merely to satisfy old tests; re-pin valid tests to the new public boundary and delete stale tests only with recorded justification.

## Subtask T020 — Writer participation, exports, and cross-project proof

Add fault-injection tests spanning journal+ledger+outbox changes in one outer transaction. A failure at each boundary must roll back all parts. Update `sync/__init__.py` only to export the project-store repository/write-permit entry points; no legacy constructor may remain a live default. Run WP01's AST census and prove these modules contain no live `sqlite3.connect()`, component commit, or writer that chooses its destination without WP02's permit.

Instrument filesystem/database/table opens across capture, selection, acknowledge, retry, diagnose, retention, and purge. All A operations observe zero B access. For every current writer class, pause before permit/insert and advance layout: the write redirects exactly once and never lands in both stores. Add mutations that reintroduce a global journal resolver or bypass the layout permit and confirm named architecture tests fail.

## Branch Strategy

Run `spec-kitty agent action implement WP04 --agent <name>` after WP02 and WP03 are approved. The computed execution lane may run parallel to WP05 only after ownership validation. WP10 depends on this completed writer conversion and must not later edit these writer files. Merge only through the mission workflow into `feat/per-project-sync-consent`; do not publish.

## Test strategy

Commit a failing public capture/store-open test before implementation. Run the four owned tests plus focused existing `tests/event_journal`, `tests/delivery`, and queue/body #3030 tests. Use real SQLite transactions and connection/open spies. Run ruff and strict mypy for touched modules.

## Definition of Done

- All live payload repositories use the ProjectSyncStore unit of work.
- Every current-version writer uses the sole layout-generation permit immediately before insert.
- No component opens or commits its own live SQLite connection.
- Every row is owner/epoch/sequence bound.
- A operations make zero B opens and cannot query B from A.
- Selection, terminal parking, final-gate preparation, retention, and purge defenses remain independently tested.
- Shared stores are absent from live constructors and remain migration-only.

## Risks and reviewer guidance

Reviewers should search for default constructors, private layout checks, and path fallbacks, not just direct connects. Run existing incident, both layout-ordering, and poison/starvation tests. Confirm changing storage did not convert opt-out into deletion, make sealed history pending, or weaken terminal results. Reject an adapter that accepts independently supplied store and UUID even if current call sites pair them correctly.

## Activity Log

- 2026-08-10T01:18:46Z – codex – shell_pid=1091 – Before source work, recovered the allocator-omitted approved WP03 dependency without conflict at lane merge 36e9cb818 and verified approved WP01 2ee80fbe0, WP02 10dccf3bf, WP03 7f9366cea, and current coordination ancestry. The arbiter authorized ownership of the two T020 architecture ratchets only; recorded as root 867643c73, coordination 4cc32490b, and lane a89d4903e while preserving every TODO(#3280), non-vacuity floor, and mutation guard. Reproductions are attached to #3281; the synthetic baseline JUnit failure is the existing #2929 defect.

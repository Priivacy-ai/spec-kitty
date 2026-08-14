---
work_package_id: WP02
title: ProjectSyncStore, layout authority, schema, and identity
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-010
- FR-026
- FR-029
- FR-032
- NFR-001
- NFR-005
- C-001
- C-003
planning_base_branch: feat/per-project-sync-consent
merge_target_branch: feat/per-project-sync-consent
branch_strategy: Planning artifacts for this mission were generated on feat/per-project-sync-consent. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/per-project-sync-consent unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/project_store.py
create_intent:
- tests/architectural/test_project_store_boundary.py
- src/specify_cli/sync/project_store.py
- src/specify_cli/sync/layout_generation.py
- src/specify_cli/sync/project_context.py
- tests/sync/test_project_store.py
- tests/sync/test_project_sync_context.py
- tests/sync/test_project_store_transactions.py
- tests/sync/test_layout_generation.py
execution_mode: code_change
owned_files:
- tests/architectural/test_project_store_boundary.py
- tests/architectural/test_egress_consent_boundary.py
- src/specify_cli/sync/project_store.py
- src/specify_cli/sync/layout_generation.py
- src/specify_cli/sync/project_context.py
- src/specify_cli/sync/project_identity.py
- src/specify_cli/state/contract.py
- tests/sync/test_project_store.py
- tests/sync/test_project_sync_context.py
- tests/sync/test_project_store_transactions.py
- tests/sync/test_layout_generation.py
role: implementer
tags: []
tracker_refs:
- Priivacy-ai/spec-kitty#3262
---

## ⚡ Do This First: Load Agent Profile

Load the Python implementation profile before reading anything else:

```text
/ad-hoc-profile-load python-pedro
```

Then read the store layout contract, data model, research Decisions 1, 8, and 9, and WP01's merged ADR/censuses.

## Objective

Implement the structural aggregate: one deterministic physical `sync.db` per canonical immutable project UUID, verified on every open, with `ProjectSyncStore.unit_of_work()` as the only live SQLite connection and outer transaction owner. Add the sole machine layout-generation/write-permit API now, before payload repositories migrate. Expose an immutable ProjectSyncContext so later repositories and senders cannot cross-pair identity, store, consent, target, or admission.

## Required design

The path is exactly:

```text
<get_runtime_root().base>/projects/<lowercase-hyphenated-uuid>/sync/sync.db
```

Sibling `egress.lock` and non-sensitive migration report locations are derived by the store, never accepted from callers. Slug, display name, path, remote, account, and target never influence storage identity. Nil, missing, braced, dashless, uppercase, and malformed inputs are normalized once or rejected according to the spec matrix.

The database owns an immutable owner UUID plus schema/layout version. All transactionally coupled tables live here, even if later WPs populate them. Component repositories receive a unit-of-work/connection port; they never connect or commit. A separate machine-local layout-generation record and lock are reached only through ProjectSyncStore; no writer or migration module may infer layout from file presence.

## Subtask T006 — Canonical identity and path resolution

Refine `project_identity.py` around one strict UUID parser/value object. Preserve existing public identity behavior only where it agrees with the spec. Add deterministic path helpers that:

- emit lowercase hyphenated ASCII UUID tokens;
- use only `get_runtime_root()` and honor isolated `SPEC_KITTY_HOME` tests;
- reject nil/missing/malformed identities before filesystem creation;
- produce the same path for legitimate worktrees sharing one UUID;
- produce distinct paths for same-slug different-UUID projects;
- never accept an arbitrary live database path.

Do not use Unicode `\w` sanitization. Add accented Latin and non-Latin display-name cases proving display text is irrelevant and the storage token is `.isascii()`.

## Subtask T007 — Store schema, owner verification, and unit of work

Create `project_store.py` with the schema tables/constraints named in `data-model.md`: metadata/layout owner, consent decisions, epochs/sequences, journal, delivery attempts/results, outbox/body, target/admission operations, history actions, and migration/cutover state.

Schema creation must occur only for the expected project owner. On every open, verify the persisted UUID and compatible layout version before exposing repositories. A mismatch, corrupt store, lock failure, or incompatible schema fails closed without rewriting evidence.

Keep schema migrations explicit and transaction-bound. Implement a typed context manager whose outer scope opens the connection, begins/commits/rolls back, and closes it. Repository ports expose SQL execution without owning connection lifecycle. Nested business operations reuse the outer transaction; named savepoints are allowed only when intentional. Do not add silent compatibility reads from shared paths.

Guard against:

- repository-local `.commit()` or `.rollback()`;
- a second live connection to the same unit of work;
- constructing a repository from a raw caller path;
- committing after an exception;
- partially committing a decision/epoch/journal/outbox/attempt bundle.

Avoid global connection caches. Cross-process concurrency uses SQLite discipline plus later `egress.lock`, not a process-only mutex.

## Subtask T008 — Layout-generation authority and write permits

Create `layout_generation.py` as the sole API for current-version writer placement. Under one machine layout lock it returns a generation-bound `LayoutWritePermit` containing canonical project UUID and exactly one destination kind. Every permit is revalidated immediately before insert. If generation changed, the caller retries through the API and redirects exactly once; `project_only` can never name a legacy path.

Expose explicit migration operations to begin cutover and publish project-only generation only after an exact-verification callback succeeds. Do not put snapshot/copy/cutover orchestration here; WP10 consumes this API. Add test-only synchronization hooks so WP04 and WP10 can prove both writer orderings without time-based sleeps.

## Subtask T009 — Immutable ProjectSyncContext

Create the context/capability type with canonical UUID, verified store identity, consent decision/generation and epoch slots, target/audience/admission slots, kill-switch result, and optional transport lease identity. At this stage authority fields may be absent/denied, but mismatched combinations must be impossible or rejected.

Construct contexts through ProjectSyncStore factories, not arbitrary public dataclass calls. Keep eligibility evaluation pure; the context cannot mutate consent. Provide narrow derived capabilities for capture and store maintenance that later WPs can extend without loose UUID/path pairs.

## Subtask T010 — Atomicity and physical isolation proof

Write ATDD tests first for:

1. A/B distinct paths and zero B opens during A operations.
2. Shared-UUID worktrees using one store with serialized writes.
3. Owner UUID tamper causing fail-closed refusal.
4. Fault injection between each table mutation rolling back the whole outer transaction.
5. Nested repository activity using one connection and no independent commits.
6. Corrupt/locked/incompatible stores preserving evidence.
7. Two current writers racing a generation advance without double-write or loss.
8. A stale permit refusing insert and redirecting exactly once through the authority.

Wire WP01's census to recognize this module as the single live connection authority. The gate must still reject any component-local connection added later.

## Branch Strategy

Run `spec-kitty agent action implement WP02 --agent <name>` only after WP01 is approved. Use the lane worktree computed by Spec Kitty. Planning base and merge target are `feat/per-project-sync-consent`; no direct protected-branch operation or publication is authorized.

## Test strategy

Commit a failing public store/isolation/layout-permit test before implementation. Run the four owned test files, relevant runtime-path tests, strict mypy on touched modules, and ruff on touched files. Keep the complete cross-platform matrix for WP11, but include local deterministic identity cases here.

## Definition of Done

- One UUID maps to one verified `sync.db`; no caller path/slug alias exists.
- ProjectSyncStore owns every live connection and outer transaction.
- ProjectSyncStore owns one tested layout-generation/write-permit API before any writer conversion.
- The schema supports all planned aggregate entities without a second database.
- ProjectSyncContext rejects cross-paired authority.
- Atomicity/isolation tests are red on base and green on final.
- WP01 census shrinks and does not gain an exemption.

## Risks and reviewer guidance

Reviewers must look past the filename: physical separation is insufficient if repositories can still connect, commit, or choose a layout privately. Inject a component-local connection and a generation-bypassing writer and confirm the architecture gates fail. Inspect rollback behavior with real SQLite, verify path behavior on platform-specific separators, and reject any fallback to shared journal/queue or store-presence-as-consent logic.

## Activity Log

- 2026-08-09T22:11:30Z – codex – shell_pid=1091 – Planning ownership correction: allocator omitted approved WP01 dependency and the exact canonical connection census entry. Merged lane-a without conflict at 50b6b0742 before red-first work; arbiter authorized a minimal test_project_store_boundary.py baseline/floor correction that preserves all non-vacuity and TODO(#3280) controls.
- 2026-08-09T22:41:11Z – codex – shell_pid=1091 – WP02 implementation complete. Approved WP01 dependency is present through lane merge 1312f2e54; the allocator omitted that dependency and both exact architectural-census ownership sites, corrected formally by plan commit cf3d15090 without weakening TODO(#3280), mutation controls, or the #3030 boundary. Red-first public contract: d307032e5 (4 expected collection errors on absent APIs). Green implementation: 66f8654ab. Final evidence on the green commit: 111 focused/runtime-path/state checks passed; 47 WP01 architectural checks passed with 2 documented strict xfails; Ruff passed all touched files; mypy --strict passed 5 touched source modules; git diff check clean. The store has one canonical UUID path, one live connection/outer transaction owner, durable fail-closed owner/version checks, exact-count census floors, a locked/fsynced one-redirect layout authority, and store-derived immutable context capabilities. No #3108/PR #3135 scope was introduced.
- 2026-08-09T22:47:46Z – codex – shell_pid=1091 – Pre-review gate classification: runtime named tests.sync.test_lifecycle_readiness.test_init_emits_project_init_event_offline as one new shard failure. Exact final-HEAD rerun passed; the leak-guard evidence classifies that node as the existing ACCEPTED #3130 pin, with its remaining spec-kitty-sync-async-loop thread already filed as #3237. This is the explicitly permitted known baseline and not a WP02 regression.
- 2026-08-09T23:36:10Z – codex – shell_pid=1091 – Review cycle 2 closed every material cycle-1 finding within WP02 scope. Red-first acceptance commit 89d89fff8 and implementation commit 22e203738 added exact PRAGMA columns/foreign keys, result-bundle fault coverage, opaque transaction-port denial (including comments, leading no-op semicolons, and BOM), failed-savepoint rollback, persisted/non-forgeable contexts, store-only fail-closed layout authority, real spawned-process serialization, and both deterministic writer orderings. Final lane 10dccf3bf preserves the same source tree after the required planning-artifact cleanup. Final-tree evidence: the recorded 111 focused/runtime-path/state gate is a green 135-test superset; the WP01 architecture/mutation gate is green at 62 passed and 2 documented strict xfails; Ruff check and format-check pass all 11 owned files; strict mypy passes all 5 source modules; and git diff-check is clean. The exact connection/layout census, all TODO(#3280) controls, owner/version/corruption/lock evidence, #3130/#3237 baseline classification, and issue #3262 scope remain preserved.

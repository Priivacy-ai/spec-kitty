---
work_package_id: WP01
title: Green baseline, architecture census, and evidence harness
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-010
- FR-018
- FR-023
- FR-026
- FR-029
- NFR-001
- NFR-004
- NFR-007
- C-001
- C-002
- C-003
- C-005
- C-008
planning_base_branch: feat/per-project-sync-consent
merge_target_branch: feat/per-project-sync-consent
branch_strategy: Planning artifacts for this mission were generated on feat/per-project-sync-consent. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/per-project-sync-consent unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: tests/architectural/test_project_store_boundary.py
create_intent:
- docs/adr/3.x/2026-08-09-1-project-sync-store-boundary.md
- tests/architectural/test_project_store_boundary.py
- tests/architectural/test_sync_writer_census.py
- tests/sync/test_project_consent_incident_baseline.py
execution_mode: code_change
owned_files:
- docs/adr/3.x/2026-08-09-1-project-sync-store-boundary.md
- tests/architectural/test_project_store_boundary.py
- tests/architectural/test_sync_writer_census.py
- tests/architectural/test_egress_consent_boundary.py
- tests/sync/test_project_consent_incident_baseline.py
role: implementer
tags: []
tracker_refs:
- Priivacy-ai/spec-kitty#3262
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile:

```text
/ad-hoc-profile-load architect-alphonso
```

Then read the mission `spec.md`, `plan.md`, `research.md`, both mission contracts, and the current #3030 architectural tests. This WP is a green census/evidence-foundation slice, not permission to implement the replacement store or commit a failing feature test.

## Objective

Freeze the code-truth topology before it changes. Record why #3262 supersedes only #3030's shared-live-store and consent-gated-capture decisions, preserve every remaining #3030 defense, and establish a green reusable harness that can later prove shared SQLite ownership, implicit grant writers, sender bypasses, and layout-writer omissions are live rather than mocked.

## Context and fixed rulings

Current code still contains component-owned connections in journal, ledger, queues, retention, CLI diagnostics/migration, and coalescing. Consent still resolves from project-local, machine-index, environment, repo-default, checkout, and backfill paths. Project-bearing writes span dispatcher HTTP, WebSocket emitter, daemon/background, body/dossier, LocalCommit, history, tracker-hosted, and generic SaaS clients.

The resulting census is a shrink-only baseline, not an allowlist that legitimizes offenders. WP01's own checks remain green by asserting the current census and testing the detector/harness itself. Every later gate built on it needs:

- a concrete floor proving it discovered live offenders on the planning base;
- a positive control proving the intended new authority will be permitted;
- a self-mutation test proving one restored offender makes the gate fail;
- explicit exclusions for test fixtures, strictly read-only migration snapshots, and unrelated SQLite domains;
- a reasoned mapping from each offender to its owning later WP.

Do not add an assertion whose correct result stays red at WP01 review. The behavior-changing packages own their first red acceptance commits.

## Subtask T001 — Record the architectural decision

Create the ADR using the current `docs/adr/3.x/` convention.

Document:

1. Context: shared hosted-sync storage made a filter defect cross-project; project path/slug/login/target/environment are not security identities.
2. Decision: canonical UUID owns one `sync.db`; `ProjectSyncStore.unit_of_work()` owns every live connection and outer transaction; one project-store action owns grants.
3. #3030 supersession: local project capture may happen without hosted consent and shared live stores are retired.
4. Preserved #3030 defenses: consent-bearing batches, SQL UUID predicates, final transmit recheck, terminal refusal parking, and explicit purge.
5. Consequences: copy/verify/cutover migration, no dual-read, cross-platform deterministic identity, and explicit history capability.
6. Scope exclusions: #3108/PR #3135 remains separate; historical 1,322 SaaS events remain Human-in-Charge controlled.

## Subtask T002 — Census live connection and commit owners

Build an AST-backed architecture test over hosted-sync modules. Inventory direct `sqlite3.connect`, connection constructors, `.commit()`, and independently owned transaction contexts. Classify each occurrence as:

- live payload/control path that must migrate;
- strictly read-only legacy snapshot path allowed only behind migration mode;
- test-only or unrelated SQLite domain;
- dead code that should be deleted by its owning WP.

Pin the known live floor by qualified symbol, not line number. Require the final state to allow live `sync.db` opens only through the ProjectSyncStore module and forbid component commits. Keep baseline growth red and shrinkage visible.

## Subtask T003 — Census grant writers and implicit inputs

Enumerate every callable path that can return or persist a grant, including `set_project_consent`, config bulk/index writers, project-local records, checkout-only/repo-default behavior, environment answers, and consent-index backfill. The final architecture test must allow only the explicit project-store decision writer to create `granted`.

Keep refusal migration distinct: importing an explicit legacy refusal may narrow, but a legacy grant never promotes. Include negative cases for login, host, target readiness, machine discovery, remote alias, store presence, and truthy `SPEC_KITTY_ENABLE_SAAS_SYNC`.

## Subtask T004 — Census sender and result paths

Extend `test_egress_consent_boundary.py` with a named sender matrix that covers every surface in `contracts/sender-and-migration-matrix.md`. Record both request start and success/result-write sites. Also inventory every current-version foreground, daemon, journal, delivery, event-outbox, and body/offline insert that must consume WP02's layout-generation write permit in WP04. The census must detect a newly added `httpx`, requests, or WebSocket project write that lacks the canonical attempt/context wrapper and a new current writer that bypasses layout authority.

Do not treat tracker Channel 2 as hosted consent. It can appear only as a narrowing predicate layered after project consent/admission.

## Subtask T005 — Build a green evidence harness

Add reusable A/B fixtures with distinct UUIDs and a common slug, store/open and exact-byte spies, differential counters, deterministic cross-process barriers, and a mutation-runner utility. Add same-path positive controls proving each spy/counter observes an ordinary current write. These harness tests must pass on the planning base and WP01 final commit.

Self-test the mutation detector with isolated synthetic specimens that deliberately:

- restore a shared journal resolver;
- treat the environment kill switch as grant;
- remove a final transport gate;
- cross-pair A's journal with B's target/ledger.

The detector self-tests must fail for each specimen and pass for the clean specimen. Do not yet mutate live production call sites or add the final incident assertion; WP02-WP11 commit their own red-first acceptance tests before the corresponding source change.

## Branch Strategy

Run `spec-kitty agent action implement WP01 --agent <name>` from the repository root checkout. Spec Kitty allocates the lane from `lanes.json`; do not invent a worktree path or branch. The planning base and merge target are both `feat/per-project-sync-consent`. Do not push or open a PR.

## Test strategy

Run the new architectural census and evidence-harness self-tests directly. Also run the existing #3030 architectural and consent-boundary suites. Every WP01 test must be green. Hand dependent WPs the exact census symbols and harness APIs they will use for their own red-on-base/green-on-final evidence. Do not run the full suite in this WP.

## Definition of Done

- ADR explicitly records the narrow supersession and preserved defenses.
- Every live connection/commit/grant/sender occurrence is classified and assigned.
- Architecture gates are non-vacuous, shrink-only, and self-mutation tested.
- Evidence helpers and positive controls are green and proven to observe live current paths.
- No failing feature assertion is left for dependent WPs to inherit.
- No source implementation, production mutation, historical-event access, or external state change occurred.

## Risks and reviewer guidance

The main review risk is a pretty census over dead or mocked call sites. Reviewers must independently trace at least one offender in each category from a public entry point, run the positive controls and synthetic mutation self-tests, and reject broad path allowlists. Reject any intentionally red WP01 test. Confirm the ADR does not weaken retained #3030 controls or absorb #3108.

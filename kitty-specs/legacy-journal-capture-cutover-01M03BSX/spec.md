# Mission Specification: Legacy→Journal Capture Cutover

**Mission Branch**: `fix/legacy-journal-capture-cutover`
**Created**: 2026-08-15
**Status**: Draft
**Input**: Fix P0 #3425 (un-migrated machines silently journal nothing) and fold the same-root cluster (#3476, #3278, #2846), auto-migrating legacy roots. Builds on #3391 (observable emitter failure), which lands first.

## Context & Motivation

Machines that have never run the layout migration default to a **legacy** capture
layout. On such a root, every event-journal / body-queue write is refused deep in
the stack and the refusal is swallowed into a stderr warning — so the command
reports success while capturing **zero** events. The absence of data is visible only
to someone reading stderr. A separate regression introduced with the per-project
consent work refuses genuinely-authenticated hosts at the setup-plan auth gate,
because credential parsing was narrowed and can no longer derive a sync scope from
the supported credential format.

This is not hypothetical: **creating this very mission reproduced the bug live** —
`mission create` emitted `Warning: Explicit-context event capture failed: live
payload writes require the project_only layout; legacy state is migration input
only` five times. This repository is itself an un-migrated legacy root.

The two defects share a root surface (layout resolution + queue selection + journal
capture) with three other open bugs: divergent duplicate events between the two
stores, `sync now` reporting success while events stay stranded in the legacy queue,
and the backfill/cutover write hitting the same guard silently. This mission fixes
them as one coherent change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable capture on an un-migrated machine (Priority: P1)

An operator (or agent) runs `setup-plan` (or any command that emits events) on a
machine that never ran the layout migration. Today the events are silently dropped.
After this mission, capture succeeds: a fresh root with no prior data resolves to a
journaling layout automatically, and a root that holds real legacy data is
auto-migrated so capture resumes without losing or duplicating existing events.

**Why this priority**: This is the P0 (#3425). Silent zero-capture corrupts every
downstream dashboard, sync, and audit trail without any error signal.

**Independent Test**: On a fresh temp root, emit events via the real command entry
point and assert the journal contains them (currently zero). On a root seeded with
legacy data, run the command and assert capture resumes and the pre-existing legacy
events are preserved exactly once.

**Acceptance Scenarios**:

1. **Given** a greenfield root with no `.layout-generation.json` and no legacy data, **When** a command emits an event, **Then** the event is captured to the journal and no capture-failure warning is produced.
2. **Given** an un-migrated root that holds real legacy queue data, **When** a command emits an event, **Then** the root is auto-migrated, capture resumes, and every pre-existing legacy event survives exactly once (no loss, no duplication).
3. **Given** any un-migrated root, **When** a capture attempt cannot succeed, **Then** the failure is observable at the command surface (never a swallowed stderr-only warning).

---

### User Story 2 - Authenticated host is not spuriously refused (Priority: P1)

An operator with valid credentials runs `setup-plan`. Today the auth gate refuses a
genuinely-authenticated host because credential parsing was narrowed. After this
mission, the supported credential format is parsed again and a coherent
authenticated host passes preflight.

**Why this priority**: This is the regression that actually reddens the blocking CI
suite on `main` today; it also blocks real authenticated operators.

**Independent Test**: Write credentials in the supported format, run the real
setup-plan entry point on a coherent host, and assert exit 0 (not a preflight
refusal), with a sync scope correctly derived from the credentials.

**Acceptance Scenarios**:

1. **Given** valid credentials in the supported format, **When** setup-plan runs on a coherent authenticated host, **Then** preflight passes (exit 0) and a sync scope is derived.
2. **Given** a daemon-owner mismatch, **When** setup-plan runs, **Then** the boundary-preflight refusal is the one surfaced (not masked by a spurious auth-unavailable refusal).

---

### User Story 3 - One capture record, no divergent duplicates (Priority: P2)

An operator's captured events can today be duplicated across the legacy and journal
stores. After this mission the one-time cutover copy deduplicates by stable event
identity so each event exists exactly once in the authoritative store.

**Why this priority**: Folds #2846 (divergent duplicates) — same root surface; the
cutover copy must not create duplicates. (Honest `sync now` convergence, #3278, is
**deferred to a separate mission** — see Out of Scope — because it requires cleaning up
migrated legacy rows, which reopens #2750.)

**Independent Test**: Seed a root that would previously diverge; run capture + cutover;
assert exactly one authoritative record per event (dedup by `event_id`/provenance),
including for ownerless legacy rows.

**Acceptance Scenarios**:

1. **Given** a root with events reachable by both stores, **When** cutover copies legacy events, **Then** each event appears exactly once in the authoritative store (no divergent duplicate).

---

### User Story 4 - Cutover/backfill writes fail loud, not silent (Priority: P2)

An operator runs the backfill/cutover path. Today it can hit the same legacy-layout
guard and silently no-op. After this mission, a cutover write that cannot land
surfaces the failure.

**Why this priority**: Folds #3476 — the backfill cutover write is the intended
remediation path for #3425; if it too fails silently, the fix is unobservable.

**Independent Test**: Drive the backfill/cutover path against a legacy layout that
cannot accept the write; assert a surfaced failure rather than a silent success.

**Acceptance Scenarios**:

1. **Given** a cutover write that cannot land on the current layout, **When** the backfill path runs, **Then** the failure is surfaced (non-zero / explicit error), never a silent success.

---

### User Story 5 - Regression reproductions pin the real contract (Priority: P2)

The existing `#3425` red-first reproduction tests currently assert a retired queue
API and mis-attribute the failure. After this mission, the reproductions assert the
current ProjectSyncStore-owned contract and turn green, and the `regression tests
(blocking)` job is green on this branch.

**Why this priority**: Un-reds `main`'s blocking CI signal and prevents the mis-built
test from masking future regressions.

**Independent Test**: Run the (rewritten) `tests/regression/test_issue_3425_*` suite
and assert all pass; run the `regression tests (blocking)` selection and assert green.

**Acceptance Scenarios**:

1. **Given** the rewritten reproductions, **When** the regression suite runs on this branch, **Then** the three previously-failing tests pass and no new reds appear.

---

### Edge Cases

- **Interrupted / partial cutover**: a crash mid-migration must leave a recoverable
  state; re-running completes it without loss or duplication (idempotent).
- **Root with both legacy data and partial project-store state**: cutover must
  reconcile, not double-count.
- **Concurrent writers during cutover**: the "project sync store is locked"
  contention observed during `mission create` must not corrupt or silently drop.
- **Credentials present but no derivable scope**: must produce a clear, actionable
  refusal — not a masked or misattributed one.
- **Greenfield root with zero events emitted yet**: resolving to the journaling
  layout must be a no-op-safe default, not an error.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | No silent-success capture | As an operator, I want any command that cannot capture an event to fail observably, so that success never means zero-capture. | High | Open |
| FR-002 | Fresh roots journal by default | As an operator on a greenfield machine, I want capture to work without a manual migration step, so that events are never silently lost. | High | Open |
| FR-003 | Auto-cutover legacy-with-data roots | As an operator whose machine holds real legacy data, I want the root auto-migrated so capture resumes, preserving every existing event exactly once. | High | Open |
| FR-004 | Restore credential parsing | As an authenticated operator, I want a coherent host to pass the setup-plan auth gate, so that valid credentials are not spuriously refused. | High | Open |
| FR-005 | Single authoritative record | As an operator, I want each event stored exactly once during cutover copy (dedup by stable identity, incl. ownerless legacy rows), so that dashboards are not double-counted. | Medium | Open |
| FR-007 | Loud cutover/backfill failures | As an operator, I want backfill/cutover writes that cannot land to surface the failure rather than silently no-op. | Medium | Open |
| FR-008 | Reproductions assert current contract | As a maintainer, I want the #3425 reproductions to assert the ProjectSyncStore contract and pass, so CI signal is honest. | Medium | Open |
| FR-009 | Preserve ProjectSyncStore selection | As a maintainer, I want the per-project ProjectSyncStore-owned queue selection kept (no revert of the prior consent work). | High | Open |
| FR-010 | Observable emitter capture failure | As an operator, I want a genuinely-unrecoverable capture failure surfaced loud-but-non-fatal at the emitter, so no failure is swallowed to a stderr-only warning (folds #3391). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Observable failure rate | 100% of capture failures are surfaced at the command boundary; 0 swallowed to stderr-only. | Reliability | High | Open |
| NFR-002 | Zero data loss/dup on cutover | Auto-cutover preserves 100% of pre-existing legacy events with 0 duplicates (verified event-count + identity diff before/after). | Data Safety | High | Open |
| NFR-003 | No regression for migrated roots | Existing already-migrated (project_only) roots see 0 behavior change; the pre-existing status/sync/journal test suites stay green. | Compatibility | High | Open |
| NFR-004 | Blocking CI green on-branch | The `regression tests (blocking)` selection returns green on this mission branch with 0 new reds attributable to the diff. | Quality | High | Open |
| NFR-005 | Idempotent cutover | Re-running an interrupted cutover converges to the same state with no additional writes; safe under a held store lock. | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Folds #3391 (emitter) | Issue #3391 (assigned, same emitter swallow shape) is FOLDED IN: this mission makes the emitter capture-failure observable (FR-010). Coordinate with the #3391 assignee (MOES-Media) so the fix closes #3391 rather than colliding. | Coordination | High | Open |
| C-002 | Legacy write path not retired | Retiring the legacy `queue.db` write path (#2750) is OUT of scope; the legacy store remains readable as migration input. | Scope | High | Open |
| C-003 | No consent-work revert | Keep the ProjectSyncStore-owned queue selection from the prior per-project consent work; fixes are additive, not a partial revert. | Governance | High | Open |
| C-004 | Emitter contract owned externally | `emitter.py` observable-failure contract is owned by #3391 (external contributor); coordinate, do not collide. | Coordination | Medium | Open |
| C-005 | Migration safety | Auto-cutover must be idempotent, lock-safe, and recoverable from partial/interrupted runs. | Technical | High | Open |

### Key Entities

- **Layout mode**: the per-root capture layout — legacy (migration-input only) vs project-scoped (live-journaling). Resolved from a durable per-root marker.
- **Layout-generation marker**: the durable per-root record whose absence currently yields the legacy default.
- **Capture stores**: the legacy queue and the event journal — the two destinations that must reconcile to a single authoritative record.
- **Queue/store selector**: the ProjectSyncStore-owned selection that decides where a live write lands (kept, not reverted).
- **Credentials → sync scope**: the operator credential material from which the auth gate derives a sync scope (parsing to be restored).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fresh un-migrated root, 100% of emitted events are captured to the journal (currently 0%).
- **SC-002**: A coherent authenticated host passes setup-plan preflight (exit 0) with 0 spurious refusals across the credential-format test matrix.
- **SC-003**: The three `#3425` regression reproductions pass and the `regression tests (blocking)` selection is green on-branch with 0 new reds.
- **SC-004**: After auto-cutover of a legacy-with-data root, pre-existing event count is preserved exactly (0 loss, 0 duplicates) versus a pre-cutover snapshot.
- **SC-005**: Re-running an interrupted cutover produces no additional or divergent records (idempotent convergence).

## Assumptions

- **#3391 is folded into this mission** (C-001, FR-010). The primary layout/cutover fix makes the common-case write succeed (nothing to swallow); FR-010 adds the loud-but-non-fatal emitter surface as the backstop for genuinely-unrecoverable cases, closing #3391. Coordinate with the assignee (MOES-Media) so the change lands once, not twice.
- The supported credential format whose parsing regressed is the one the existing
  reproductions write; restoring derivation for it is sufficient for FR-004.
- Auto-cutover of legacy-with-data roots (#2688 direction) is desired even though the
  legacy write path is not retired (#2750) — the two are decoupled here: migrate
  forward, keep the old path readable.
- "ProjectSyncStore-owned queue selection" (prior consent work) is the intended
  end-state; the mis-built reproduction (Test A) is rewritten to it rather than the
  code reverted to it.

## Out of Scope

- Retiring the legacy `queue.db` write path (#2750).
- **Honest `sync now` convergence (#3278) — deferred to a separate mission.**
  The code proves it requires cleaning up (deleting) migrated legacy rows, which reopens
  #2750; keeping #2750 out of scope means #3278 cannot be honestly closed here. This
  mission still deduplicates the cutover copy (#2846) so no divergent duplicates are
  created; it just does not change `sync now`'s convergence reporting. (The functional-
  requirement numbering skips one slot between FR-005 and FR-007 to keep IDs stable after
  this deferral; that gap is intentional.)
- Broader sync/tracker or dashboard changes beyond making capture honest.

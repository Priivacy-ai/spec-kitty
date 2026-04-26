# Spec: Spec Kitty Stability & Hygiene Hardening (April 2026)

**Mission slug**: `stability-and-hygiene-hardening-2026-04-01KQ4ARB`
**Mission ID**: `01KQ4ARB0P4SFB0KCDMVZ6BXC8`
**Friendly name**: Spec Kitty Stability & Hygiene Hardening (April 2026)
**Mission type**: software-dev
**Created**: 2026-04-26
**Status**: Draft (specify phase)

## Overview

Operators of Spec Kitty have accumulated a backlog of correctness, safety, and hygiene
issues that span six repositories: `spec-kitty`, `spec-kitty-saas`, `spec-kitty-tracker`,
`spec-kitty-events`, `spec-kitty-runtime`, and `spec-kitty-end-to-end-testing`. The
issues fall into six themes:

1. **Merge, worktree, and lane safety** — silent data loss in lane-based merges, lane
   planning that places dependent work into isolated lanes without dependency files,
   non-recoverable interrupted merges, and post-merge bookkeeping that races with
   untracked artifacts.
2. **Intake security and atomic state hygiene** — provenance comments and brief writes
   that are vulnerable to traversal, symlink escape, prompt injection, OOM on large
   inputs, and partial-write corruption. Inconsistent root selection between scan
   source and write target.
3. **Runtime, status, and orchestration correctness** — `spec-kitty next` defaulting a
   bare call to `success`, valid runs returning a non-actionable `unknown` mission
   state with `[QUERY - no result provided]`, status events written to the wrong
   canonical repo when invoked from a worktree, transition labels that disagree with
   the documented state machine, planning-artifact WPs lacking a workspace, and a
   shipped `plan` mission whose metadata fails its own schema.
4. **Cross-repo package contract hygiene** — drift between `spec-kitty-events`
   contract tests and the resolved package version; lack of a hard
   `tests/contract/` gate during mission review; ambiguity around `spec-kitty-runtime`
   retirement (already resolved on `main` by the shared-package-boundary cutover but
   not yet reflected in mission acceptance gates); release gates that pass on
   package-local CI alone while downstream consumers would fail.
5. **Sync, tracker, SaaS, and hosted flow stability** — offline sync queues silently
   dropping events when full; replay handling that does not deterministically resolve
   tenant/project identity collisions; token refresh failures that flood command
   output; sync, tracker, and websocket clients that do not share a centralized auth
   transport; tracker bidirectional sync without certified failure semantics.
6. **Repo context, governance, and user-facing hygiene** — spec/plan/task ceremony
   silently falling back to another repo when the current repo is uninitialized;
   PR-bound missions starting on `main` without an explicit branch-strategy gate;
   `charter context --mode compact` shedding section-level governance; legacy
   `--feature` aliases visible in help output; local custom mission loader post-merge
   hygiene either incomplete or undocumented.

This mission delivers one coherent hardening pass across all six themes, backed by
unit, contract, integration, and **real cross-repo end-to-end** evidence. The mission
explicitly enumerates every GitHub issue in scope. An issue is closed only when one of
the following is recorded in the mission artifacts: (a) a fix landed with passing
tests; (b) the issue is verified already resolved on current `main` with a regression
test that would have failed against the pre-fix code; or (c) the issue is documented
as obsolete with a precise reason and, if needed, a narrower follow-up issue is
filed.

## User Scenarios

### Scenario 1 — Operator runs a multi-WP mission with a planning lane and lands it cleanly

An operator drives a mission that has three implementation WPs and one
`lane-planning` WP that produces planning artifacts. The implementation WPs depend on
each other in sequence. When the operator runs `spec-kitty merge`, every approved
commit from every lane lands on the target branch. Post-merge cleanup refreshes the
git index without staging phantom deletions, and untracked `.worktrees/` directories
do not block bookkeeping. If the operator's machine is interrupted halfway through
the merge, re-running `spec-kitty merge --resume` finishes the remaining work
idempotently rather than producing a half-merged state.

### Scenario 2 — Operator imports a third-party plan via `spec-kitty intake`

An operator pastes a plan document of unknown provenance into
`spec-kitty intake`. The intake pipeline:

- refuses to follow symlinks that point outside the project root;
- rejects files that exceed the configured size cap before reading them in full;
- escapes provenance comments so that `source_file:` cannot break out of the comment
  and inject prompt content into downstream agent runs;
- distinguishes "file is missing" from "file is unreadable or corrupt";
- writes the brief atomically so an interrupted write never strands the repo with a
  half-written brief.

### Scenario 3 — Agent drives `spec-kitty next` from a lane worktree

An agent invokes `spec-kitty next` while CWD is a lane worktree. The runtime detects
the canonical mission repo, writes status events and config changes to that canonical
repo, and resolves the workspace path the agent receives in the decision. The agent
never sees a stale worktree copy of `status.events.jsonl`. The runtime never advances
on a bare `next` call (no implicit `success`). When the runtime cannot determine what
to do next, it returns a structured error that names the validation failure rather
than `[QUERY - no result provided]` with `unknown` mission state.

### Scenario 4 — Operator marks a WP for review

When a reviewer claims a WP, the runtime emits a `for_review -> in_review` transition
(not `for_review -> in_progress`). `mark-status` accepts WP IDs in the format that
`tasks-finalize` actually emits. Dashboard counters reflect the WP's `in_review`
state during active review and the WP's `done` state after merge.

### Scenario 5 — Maintainer cuts a candidate release of `spec-kitty-events`

A maintainer prepares a candidate release of `spec-kitty-events`. Package-local CI
passes. The candidate is then verified against real downstream consumers
(`spec-kitty`, `spec-kitty-saas`, `spec-kitty-tracker`,
`spec-kitty-end-to-end-testing`) before promotion to stable. If a consumer fails the
candidate, promotion is blocked. Mission review treats `tests/contract/` as a hard
pass/fail gate, not advisory.

### Scenario 6 — Operator works offline and queues sync events

An operator goes offline and accumulates 500 sync events past the local queue cap.
The system surfaces the queue-full state to the operator with a recoverable path
rather than silently dropping events. When the operator comes back online, replay
handles tenant/project identity collisions deterministically: idempotent if safe,
explicit tenant mismatch error if unsafe.

### Scenario 7 — Operator runs the spec ceremony in the wrong repo

An operator runs `/spec-kitty.specify` in a sibling repo that has not been
initialized for Spec Kitty. The command fails loudly with a structured error
(`SPEC_KITTY_REPO_NOT_INITIALIZED`) rather than silently writing artifacts into a
nearby initialized repo. PR-bound missions started on a tracked `main` branch are
gated by an explicit branch-strategy prompt before a worktree can be created.

### Scenario 8 — Cross-repo end-to-end coverage proves the system works

The `spec-kitty-end-to-end-testing` repo contains a scenario that drives a mission
from specify through merge, exercises `SPEC_KITTY_ENABLE_SAAS_SYNC=1` flows, asserts
that package-contract drift is caught before release, and asserts that running the
spec ceremony in an uninitialized repo fails loudly. The scenario is run as a hard
mission-review gate.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The merge subsystem MUST land every approved commit from every lane (including `lane-planning`) onto the target branch with no silent omission. | Required |
| FR-002 | The merge subsystem MUST be re-runnable after interruption: re-running `spec-kitty merge` (or `spec-kitty merge --resume`) MUST complete the remaining work without producing a half-merged state, and MUST be idempotent if no remaining work exists. | Required |
| FR-003 | Post-merge cleanup MUST refresh the git index so that no phantom deletions of files that exist on disk are staged. | Required |
| FR-004 | Post-merge bookkeeping MUST NOT be blocked by untracked `.worktrees/` directories or by other untracked files outside the merge scope. | Required |
| FR-005 | Lane planning MUST schedule a WP that depends on another WP either into the same lane in dependency order, OR into a lane whose base branch already includes the dependency commits. A dependent WP MUST NOT be scheduled into a lane that lacks the dependency files. | Required |
| FR-006 | Parallel SaaS / Django implementation lanes MUST receive lane-specific test database configuration so that two lanes do not collide on a single shared test database. | Required |
| FR-007 | Intake `source_file` provenance MUST be written so that the captured source identifier cannot terminate the comment, inject markdown headings, or inject prompt content into downstream agent runs. | Required |
| FR-008 | Intake plan source scanning MUST NOT escape the configured intake root via path traversal, symlinks pointing outside the root, or canonicalization tricks. | Required |
| FR-009 | Intake MUST reject plan files that exceed the configured size cap before reading them in full into memory. | Required |
| FR-010 | Intake brief and provenance writes MUST be atomic enough that an interrupted write never leaves the repo with a half-written brief on disk. (Atomic-rename semantics on the same filesystem are sufficient.) | Required |
| FR-011 | Intake MUST distinguish "file missing" from "file present but unreadable or corrupt" in its error surface, and MUST NOT swallow the underlying error. | Required |
| FR-012 | Intake root selection MUST be consistent: the directory used for source scanning MUST be the same root used for brief writes. | Required |
| FR-013 | When invoked from a lane worktree, mission status events and config writes MUST target the canonical mission repo (the worktree's main repo), not a stale worktree-local copy. | Required |
| FR-014 | The runtime MUST emit a `planned -> in_progress` status event before any worktree allocation that could fail. If allocation fails, the runtime MUST emit a recoverable failure event rather than leaving the WP in an ambiguous state. | Required |
| FR-015 | Planning-artifact WPs (those whose deliverable is a planning artifact rather than source code in a lane) MUST have either a resolvable implementation workspace or a documented first-class non-worktree execution path. The runtime MUST NOT report such WPs as blocked when they are actually executable. | Required |
| FR-016 | The review claim transition MUST be `for_review -> in_review`, not `for_review -> in_progress`, in both the runtime emit path and the documented transition matrix. | Required |
| FR-017 | `mark-status` MUST accept WP IDs in the exact format emitted by `tasks-finalize`. If `tasks-finalize` emits a different shape, EITHER `mark-status` is extended to accept it OR `tasks-finalize` is changed so its emission matches the parser contract. | Required |
| FR-018 | Dashboard and progress counters MUST reflect approved, in-review, and done states correctly during active implementation, during review, and after merge. | Required |
| FR-019 | A bare `spec-kitty next` call (no `--result`) MUST NOT default to `success`. Completion MUST be explicit (e.g., `--result success`). A bare call MUST return the next decision based on current state, not advance the runtime. | Required |
| FR-020 | A valid mission run MUST NEVER return a decision whose `mission_state` is `unknown` and whose body is `[QUERY - no result provided]` when a concrete validation error or actionable next step is available. | Required |
| FR-021 | The shipped `plan` mission's metadata (e.g. `mission-runtime.yaml`) MUST validate against the runtime schema. | Required |
| FR-022 | The contract test suite under `spec-kitty/tests/contract/` MUST reflect the currently resolved `spec-kitty-events` package version: required envelope fields, type expectations, and version constraints MUST match what `pyproject.toml` and `uv.lock` resolve. | Required |
| FR-023 | `/spec-kitty-mission-review` MUST treat `tests/contract/` as a hard pass/fail gate. A failing contract test MUST block mission acceptance. | Required |
| FR-024 | `spec-kitty-events` and `spec-kitty-tracker` MUST remain independent PyPI contract packages with documented public imports, SemVer expectations, and a downstream-consumer verification step before stable promotion. | Required |
| FR-025 | The status of `spec-kitty-runtime` MUST be resolved deliberately in the mission artifacts: either confirmed retired (no production consumer imports it), or kept under strict release gates with a written reason. The mission MUST verify and document that `spec-kitty next` runs in a fresh venv without the standalone `spec-kitty-runtime` package installed. | Required |
| FR-026 | Candidate releases of any cross-repo package MUST be verified against at least one real downstream consumer before stable promotion. Package-local CI alone MUST NOT be sufficient. | Required |
| FR-027 | When the offline sync queue is at capacity, NEW sync events MUST NOT be silently dropped. The system MUST surface the queue-full state to the operator with a recoverable path (e.g., expand cap, drain to file, force flush). | Required |
| FR-028 | Sync replay MUST handle project/team identity collisions deterministically: replay MUST be idempotent when the incoming event's tenant/project identity matches the local target, and MUST raise an explicit, structured tenant-mismatch error when it does not. | Required |
| FR-029 | Token refresh failures MUST be deduplicated within a single command invocation: a single failure MUST NOT print more than one user-facing line, and MUST NOT flood output after a successful user-facing operation. | Required |
| FR-030 | Sync, tracker, and websocket clients MUST share a centralized auth transport so that auth state, token refresh, and 401 handling are not reimplemented per client. | Required |
| FR-031 | Tracker bidirectional sync MUST have a deterministic retry/failure surface (bounded retries, structured failure event, no silent infinite retry) and MUST be exercised against SaaS in downstream certification. | Required |
| FR-032 | The spec/plan/task ceremony MUST fail loudly with a structured error when invoked in a directory that is not initialized for Spec Kitty. It MUST NOT silently fall back to another repo on disk. | Required |
| FR-033 | A PR-bound mission MUST NOT start on the resolved `merge_target_branch` (typically `main`) without an explicit branch-strategy gate that the operator has acknowledged. | Required |
| FR-034 | `charter context --mode compact` MUST include enough section-level governance content for agents to obey project-specific rules. The compact view MUST NOT shed required directives, tactics, or governance section anchors. | Required |
| FR-035 | Legacy `--feature` aliases on commands that have moved to `--mission` MUST remain accepted (no breaking change), but MUST be hidden from `--help` output. | Required |
| FR-036 | Local custom mission loader post-merge hygiene MUST be either completed in this mission or documented with a precise follow-up issue and a clear scope statement. The mission artifacts MUST capture which path was chosen and why. | Required |
| FR-037 | The mission MUST enumerate every issue listed in `start-here.md` in a traceability matrix, and for each issue MUST record one of: `fixed-in-WPxx`, `verified-already-fixed-in-WPxx`, or `deferred-with-followup-#NNN`. | Required |
| FR-038 | The `spec-kitty-end-to-end-testing` repo MUST contain (or have updated) at least one scenario that proves a dependent-WP plus planning-lane mission merges without data loss. | Required |
| FR-039 | The end-to-end suite MUST contain a scenario that proves the spec ceremony fails loudly in an uninitialized repo. | Required |
| FR-040 | The end-to-end suite MUST contain a scenario that exercises SaaS / tracker / sync flows under `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Required |
| FR-041 | The end-to-end suite MUST contain a scenario that proves package contract drift is caught before release or mission-review signoff. | Required |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage for new and changed code in `spec-kitty` MUST stay at or above the project's minimum (90%+ on changed lines per the charter). | ≥ 90% on changed lines | Required |
| NFR-002 | `mypy --strict` MUST pass on every changed module across all six repos. | 0 type errors | Required |
| NFR-003 | The intake size cap rejection (FR-009) MUST trigger before reading more than the cap into memory. | Reject before reading > 1.5× cap into memory; default cap ≤ 5 MB | Required |
| NFR-004 | Atomic intake writes (FR-010) MUST not produce a half-written brief on disk if the writer is killed mid-write. | 0 partial files in 100 simulated kill-9 runs | Required |
| NFR-005 | `spec-kitty merge --resume` (FR-002) MUST converge on a clean state in bounded time after an interrupted merge. | ≤ 30 s of work for a resumed merge with ≤ 10 lanes on a developer laptop | Required |
| NFR-006 | The cross-repo e2e suite MUST run end-to-end on a developer laptop without external paid services. | Full e2e under 20 min wall-clock; SaaS exercised against the configured dev SaaS endpoint | Required |
| NFR-007 | Token-refresh log dedup (FR-029) MUST cap visible duplicate-failure lines per command invocation. | ≤ 1 user-facing token-refresh failure line per invocation | Required |
| NFR-008 | Status event emission MUST remain append-only and corruption-resistant. | 0 lost or rewritten events under 100 simulated crash points across emit pipeline | Required |
| NFR-009 | The mission MUST not regress existing CLI startup time. | `spec-kitty --version` cold start ≤ 1.5 s on the dev laptop, no worse than current `main` | Required |
| NFR-010 | Documentation pages added or updated by this mission MUST be discoverable from at least one existing index (README, docs index, or migration runbook) without dead links. | 0 dead internal links in changed pages | Required |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Work occurs only inside `/Users/robert/spec-kitty-dev/spec-kitty-20260426-091819-hxH6lN`. No edits to older local checkouts. | Required |
| C-002 | All commands that exercise SaaS, hosted auth, tracker, or sync behavior MUST run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set in the environment on this machine. | Required |
| C-003 | The mission MUST NOT introduce a new shared package boundary that re-introduces `spec-kitty-runtime` as a production dependency. The shared-package-boundary cutover (mission `shared-package-boundary-cutover-01KQ22DS`, 2026-04-25) is the baseline. | Required |
| C-004 | The mission MUST NOT suppress or skip pre-commit hooks (`--no-verify`) or signing flags. | Required |
| C-005 | Issue closure on GitHub MUST be backed by a referenceable artifact in the mission (test name, commit SHA, doc anchor). No issue is closed on vibes. | Required |
| C-006 | The runtime status model MUST remain at Phase 2 (event log is sole authority). The mission MUST NOT reintroduce frontmatter `lane` as an active read or write surface. | Required |
| C-007 | Selectors MUST resolve missions by `mission_id` first, then `mid8`, then `mission_slug`. The mission MUST NOT reintroduce silent fallback semantics on ambiguous selectors. | Required |
| C-008 | Existing public imports of `spec_kitty_events.*` and `spec_kitty_tracker.*` MUST remain stable; any breaking change to a public import path MUST be a SemVer major bump and MUST be reviewed in the mission artifacts. | Required |
| C-009 | The mission MUST NOT bump the version of any cross-repo PyPI package without an explicit instruction from the operator. | Required |
| C-010 | The end-to-end test repo MUST be treated as a hard gate, not an optional check. If a full deployed-dev e2e run cannot be executed locally, the exact blocker, the command to run, and the evidence from the partial local run MUST be recorded in the mission artifacts, and the mission MUST NOT be marked complete without either executed e2e evidence or an explicit operator-approved exception. | Required |

## Issue Scope (Traceability Source)

The mission tracks every GitHub issue listed in `start-here.md` in a traceability
matrix produced during `/spec-kitty.tasks` and reconciled at mission-review. The
themes and issue counts are:

- **Merge / worktree / lane safety**: 7 issues
  - Priivacy-ai/spec-kitty: #785, #416, #784, #772, #675, #715, #770
- **Intake security and state hygiene**: 7 issues
  - Priivacy-ai/spec-kitty: #724, #720, #721, #722, #723, #727, #725
- **Status, runtime, and orchestration correctness**: 16 issues
  - Priivacy-ai/spec-kitty: #539, #538, #541, #542, #551, #622, #783, #775,
    #540, #443, #710, #526, #552, #343, #335, #336
- **Cross-repo package contracts and release gates**: 14 issues
  - Priivacy-ai/spec-kitty: #791, #792, #419, #420, #421
  - Priivacy-ai/spec-kitty-events: #16, #7, #8
  - Priivacy-ai/spec-kitty-tracker: #12, #5, #6
  - Priivacy-ai/spec-kitty-runtime: #16, #7, #8, #11
- **Sync / tracker / SaaS / hosted flow stability**: 5 issues
  - Priivacy-ai/spec-kitty: #306, #352, #717, #564
  - Priivacy-ai/spec-kitty-tracker: #1
- **Repo context, governance, and user-facing hygiene**: 5 issues
  - Priivacy-ai/spec-kitty: #773, #765, #787, #790, #801

## Success Criteria

- SC-001: An operator can run a 4-WP mission (3 implementation WPs with sequential
  dependencies plus 1 planning lane) end-to-end and the merged result on `main`
  contains every approved commit. (Verifies FR-001, FR-005, FR-038.)
- SC-002: An operator who interrupts `spec-kitty merge` mid-flight can re-run the
  command and arrive at a clean state in under 30 seconds for a 10-lane mission.
  (Verifies FR-002, NFR-005.)
- SC-003: An operator who pastes a 50 MB plan file into `spec-kitty intake` receives
  a clean rejection without the process exceeding 1.5 × the configured cap in
  resident memory. (Verifies FR-009, NFR-003.)
- SC-004: An operator running the spec ceremony in an uninitialized sibling repo
  receives a structured error, no files are written outside the current repo, and the
  CLI exits with a non-zero code. (Verifies FR-032, FR-039.)
- SC-005: A reviewer claiming a WP sees a `for_review -> in_review` event in the
  status log; dashboard counters are correct during review and after merge.
  (Verifies FR-016, FR-018.)
- SC-006: A maintainer cutting a candidate release of `spec-kitty-events` cannot
  promote it to stable until at least one real downstream consumer has verified the
  candidate. (Verifies FR-024, FR-026, FR-041.)
- SC-007: An offline operator who exceeds the local sync queue cap is presented with
  a recoverable path; on reconnect, replay is idempotent for matching identities and
  raises a structured tenant-mismatch error otherwise. (Verifies FR-027, FR-028.)
- SC-008: Across a single command invocation that performs many authenticated
  requests, no more than one user-facing token-refresh failure line appears.
  (Verifies FR-029, NFR-007.)
- SC-009: The mission's traceability matrix shows that every issue listed in
  `start-here.md` has a verdict of `fixed`, `verified-already-fixed`, or
  `deferred-with-followup`. No issue has the verdict `unknown`. (Verifies FR-037.)
- SC-010: Mission-review's contract gate fails the mission if any test under
  `spec-kitty/tests/contract/` fails. (Verifies FR-022, FR-023.)
- SC-011: The cross-repo e2e suite (Scenario 8) runs to completion locally and is
  required for mission acceptance. (Verifies FR-038, FR-039, FR-040, FR-041, C-010.)
- SC-012: `spec-kitty next` (bare) on a fresh mission run does not advance state and
  does not return `unknown` mission with `[QUERY - no result provided]`. (Verifies
  FR-019, FR-020.)

## Key Entities

- **Mission**: a Spec Kitty mission tracked by `kitty-specs/<slug>/`, with canonical
  `mission_id` (ULID), human `mission_slug`, and display-only `mission_number` assigned
  at merge time.
- **Work Package (WP)**: a unit of work in a mission with a 9-lane status state
  machine (`planned, claimed, in_progress, for_review, in_review, approved, done,
  blocked, canceled`), append-only event log, and optional lane assignment.
- **Lane**: a parallel execution lane with its own worktree
  (`.worktrees/<human-slug>-<mid8>-lane-<id>`).
- **Status Event**: an immutable JSONL entry in `kitty-specs/<slug>/status.events.jsonl`,
  the sole authority for WP lane state in Phase 2.
- **Mission Brief**: an intake artifact at `.kittify/mission-brief.md` written by
  `spec-kitty intake` with associated provenance metadata.
- **Charter Context**: governance content surfaced at action boundaries via
  `spec-kitty charter context --action <action>`.
- **Cross-repo Package**: an external PyPI package (currently `spec-kitty-events`,
  `spec-kitty-tracker`) consumed by `spec-kitty` via documented public imports and
  governed by SemVer + downstream-consumer verification.
- **Sync Queue**: the offline event queue used when the SaaS endpoint is unreachable.
- **Auth Transport**: the centralized HTTP client / token-refresh layer used by sync,
  tracker, and websocket clients.

## Assumptions

- The shared-package-boundary cutover (mission `shared-package-boundary-cutover-01KQ22DS`,
  2026-04-25) is the baseline. `spec-kitty-runtime` is treated as retired-from-production
  and the standalone PyPI install is no longer a production dependency. The mission
  treats `spec-kitty-runtime` issues as either "verify retirement" or "package-local
  hygiene" rather than as new shared-dependency work.
- The mission-identity model from mission `083` (ULID `mission_id` canonical, numeric
  `mission_number` display-only, `mid8` in branch / worktree names) is the baseline.
  No selector reverts to numeric-prefix identity.
- The status model is at Phase 2 (event log sole authority). Frontmatter `lane` is
  out of scope for new behaviour; only migration code may still touch it.
- Issues that are already fixed on current `main` will be verified with a regression
  test that would fail against the pre-fix code, not a fresh fix.
- The e2e repo (`spec-kitty-end-to-end-testing`) is available locally and can be run
  by an agent.
- The dev SaaS endpoint (`SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev`) is
  available; if it becomes unavailable, e2e SaaS scenarios are recorded as blocked
  with a precise blocker and the mission asks the operator for an exception.

## Out of Scope

- Re-introducing `spec-kitty-runtime` as a shared production dependency.
- Re-introducing frontmatter `lane` as an active status surface (Phase 2 stays).
- Re-introducing `mission_number` as an identity selector.
- Bumping any cross-repo package version (events, tracker) without explicit operator
  instruction (C-009).
- Changing the public import surface of `spec_kitty_events.*` or
  `spec_kitty_tracker.*` (C-008). Bug fixes inside the modules are in scope; rename
  or moves are not.
- Building a new dashboard or new mission type. The mission is hardening only.

## Dependencies

- `spec-kitty` `main` at commit `e056f398` (or later) — baseline checkout.
- `spec-kitty-events` and `spec-kitty-tracker` PyPI packages at the version range
  resolved by the current `pyproject.toml` / `uv.lock`. The mission MUST NOT bump
  either without explicit operator instruction.
- `spec-kitty-saas` at the current `main`; required for SaaS / sync e2e scenarios.
- `spec-kitty-end-to-end-testing` at the current `main`; required for cross-repo e2e
  evidence.
- The dev SaaS endpoint at `https://spec-kitty-dev.fly.dev` for e2e scenarios run with
  `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

## Definition of Done

- Every issue listed in `start-here.md` has a verdict (`fixed`,
  `verified-already-fixed`, or `deferred-with-followup`) recorded in the mission
  traceability matrix.
- All FR / NFR / C items above are met or explicitly deferred with operator
  approval.
- Unit, contract, integration, and **executed** cross-repo e2e evidence is recorded
  in the mission artifacts.
- `tests/contract/` is wired as a hard mission-review gate.
- `spec-kitty next` runs in a fresh venv without `spec-kitty-runtime` installed.
- No GitHub issue is closed without a referenceable artifact (test name, commit SHA,
  or doc anchor).

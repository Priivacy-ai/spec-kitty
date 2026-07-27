# Mission Specification: Runtime-State Birth-Cutover (All Landing Paths)

**Mission Branch**: `fix/runtime-state-birth-cutover-all-paths`
**Created**: 2026-07-27
**Status**: Draft
**Input**: Structural closure of #2917 — the runtime-state birth-cutover seam only fires for one of the two ways a mission can land on `main`, so the dogfood corpus re-drifts red and re-blocks the release tag on every GitHub-side merge wave.

## Context & Background

Every mission records its lifecycle runtime state as an append-only event log
(`status.events.jsonl`). A mission counts as **cut over** to the event-sourced
model only when its committed corpus carries both a stamped
`meta.json status_phase = "1"` **and** the deterministic seed events that make
`verify_backfill` pass (the reduced snapshot equals the legacy reader by count
and value). A release-gating acceptance test
(`tests/specify_cli/migration/test_dogfood_corpus_backfilled.py`) fails on `main`
whenever any eligible mission in the committed corpus is not cut over.

#2920 introduced a **birth-cutover** stamp so missions land already cut over —
but it fires **only inside `spec-kitty merge`** (the local lane-consolidation
path). The maintainer lands missions on `main` through **GitHub-side
squash/rebase merges**, which execute no Spec Kitty code, so those missions
arrive **un-cut-over**. This was proven three independent ways on 2026-07-27
(three `01KW6N*` missions, this programme's predecessor #2963's own mission, and
six recent `01KYE*/01KYF*` missions missing the `status_phase` key). The
mechanical re-green shipped as hotfix #2968; **this mission removes the
structural cause** so the drift cannot recur, plus a fail-closed guard so it can
never again reach `main` silently.

## Domain Language *(canonical terms)*

- **Birth-cutover**: stamping a mission's corpus with `status_phase = "1"` and the
  deterministic seed events, so it passes `verify_backfill`.
- **Cut over**: the state of a mission whose committed corpus passes
  `verify_backfill`.
- **Landing path**: the mechanism by which a mission's corpus reaches `main` —
  `spec-kitty merge` (local lane consolidation) **or** GitHub-side squash/rebase.
  Ambiguous synonym to avoid: bare "merge" (see charter footgun note).
- **Drift**: a mission that reaches `main` not cut over.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A mission is born cut over regardless of how it lands (Priority: P1)

When a mission's work is complete and its corpus is finalized, the cutover stamp
is written **into the mission branch as a committed artifact** before the branch
can land — so whether the maintainer lands it via `spec-kitty merge` or a
GitHub-side squash/rebase, the corpus that arrives on `main` is already cut over.

**Why this priority**: This is the structural root. Without it, every
GitHub-merged mission re-introduces drift and re-blocks the release tag,
requiring a manual re-green each time.

**Independent Test**: Take a mission finalized through the lifecycle, land it via
a GitHub-style squash merge (no `spec-kitty merge`), and assert its corpus on the
target branch is cut over (`verify_backfill` passes) with no manual step.

**Acceptance Scenarios**:

1. **Given** a mission whose runtime work is final, **When** it reaches the
   terminal lifecycle point, **Then** its committed corpus carries
   `status_phase = "1"` and deterministic seed events that pass `verify_backfill`.
2. **Given** a mission whose corpus is already cut over, **When** it lands via a
   GitHub-side squash/rebase merge, **Then** the corpus on the target branch is
   cut over and `test_dogfood_corpus_backfilled` passes.
3. **Given** a mission landed via `spec-kitty merge`, **When** it reaches the
   target branch, **Then** it is cut over exactly as before (no regression to the
   existing path).

### User Story 2 - Un-cut-over missions are blocked before they can reach main (Priority: P1)

A fail-closed pre-merge check rejects any change set that would introduce (or
leave) an un-cut-over mission in the corpus, naming the offending mission(s) and
the exact remedy, so drift can never land silently even if the stamp is bypassed.

**Why this priority**: Defense in depth. The stamp (US1) prevents the common
case; the guard makes the invariant enforceable and makes any future gap loud
instead of silent-until-release.

**Independent Test**: Construct a pull request whose diff contains an
un-cut-over mission corpus and assert the guard check fails the PR with a message
naming the mission and the remedy command; construct one where all touched
missions are cut over and assert it passes.

**Acceptance Scenarios**:

1. **Given** a PR whose changed corpus contains an un-cut-over mission, **When**
   the pre-merge guard runs, **Then** it fails and names the mission(s) plus the
   remedy command.
2. **Given** a PR where every touched mission is cut over, **When** the guard
   runs, **Then** it passes.
3. **Given** the guard encounters a verify error or an ambiguous corpus, **When**
   it evaluates, **Then** it fails closed (blocks), never passes on uncertainty.

### User Story 3 - The corpus stays reconciled and drift is observable (Priority: P2)

After this mission lands, the dogfood corpus acceptance test stays green on
`main` across merge waves with no manual intervention, and an operator can list
un-cut-over missions on demand.

**Why this priority**: Turns the fix into a durable, observable guarantee rather
than a one-time repair.

**Independent Test**: Over consecutive merge waves, `test_dogfood_corpus_backfilled`
stays green on `main` with zero manual re-green; an on-demand audit reports the
cut-over status of every mission.

**Acceptance Scenarios**:

1. **Given** the mission has landed, **When** subsequent missions land via any
   path, **Then** `test_dogfood_corpus_backfilled` remains green on `main` with no
   manual re-green.
2. **Given** an operator wants to audit the corpus, **When** they request cut-over
   status, **Then** they get a deterministic report of any un-cut-over missions.

### Edge Cases

- A mission whose runtime work is **still in progress** must **not** be stamped
  prematurely (a stamp written while `implement` still dual-writes runtime to
  frontmatter/`tasks.md` would pass vacuously and then red `verify_backfill` once
  work advances). The stamp fires only when runtime state is final.
- A mission that is genuinely **excluded** from cutover eligibility (e.g. no
  runtime state to seed) must not be forced to a false stamp and must not be
  flagged by the guard.
- A mission already cut over must be a **no-op** for both the stamp and the guard
  (idempotent; never appends duplicate or divergent seed events).
- The two landing-path stamps must be **one authority**, not two divergent
  writers that can disagree.
- A mission landed with the `status_phase` **key absent** (not merely `null`) must
  be treated as un-cut-over by the guard.
- **Seam-bypass paths**: a corpus can reach `main` without passing the terminal
  lifecycle stamp — directly-authored corpus (e.g. the #2968 hotfix pattern),
  abandoned/cancelled missions, mid-flight merges, or a *later* mission's PR that
  edits an *earlier* mission's corpus. The auto-stamp cannot cover these; the
  **guard is the binding backstop** and must evaluate every mission whose corpus
  appears in the PR diff, not just the "current" mission.
- **Vacuous-green trap**: a natively-born mission has no retired-frontmatter state
  to seed, so `verify_backfill` returns `ok=True, wp_count=0` — vacuously green.
  "Cut over" for such a mission must be established from event-log evidence +
  non-empty snapshot + `status_phase = "1"`, never from `verify_backfill.ok`
  alone (which is necessary-but-not-sufficient and would green-wash the exact
  missions this mission targets, and mask a genuinely broken event log).
- **Write-vs-commit**: the stamp writes `meta.json`/seed events but performs no git
  commit; the seam must commit both partitions (`meta.json` on PRIMARY, seed
  events on COORD) into the branch that lands, with no reliance on a background
  status daemon's auto-commit (which can commit under a stale message).
- **Flipped-but-unverifiable**: two stamps resolving the claim anchor from
  different leg contexts can leave `status_phase = "1"` while `verify_backfill`
  later reds on payload divergence — the worst state. Anchor resolution must be
  pinned to one canonical leg.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Stamp cutover at the terminal lifecycle point | As a maintainer, I want a mission's cutover stamped into its branch when its runtime work is final, so the corpus is already cut over no matter how the branch later lands. | High | Open |
| FR-002 | Fail-closed pre-merge guard | As a maintainer, I want CI to reject any change set that would leave an un-cut-over mission in the corpus, so drift cannot reach `main` silently. | High | Open |
| FR-003 | Actionable guard diagnostics | As a maintainer, I want the guard to name the offending mission(s) and print the exact remedy command, so I can re-green in one step. | High | Open |
| FR-004 | Stamp only when runtime state is final | As a maintainer, I want the stamp withheld while a mission's runtime state is still mutating, so it never produces a vacuously-green stamp that reds later. | High | Open |
| FR-005 | Single cutover authority across landing paths | As a maintainer, I want the `spec-kitty merge` stamp and the new lifecycle stamp to share one implementation, so the two paths cannot diverge. | High | Open |
| FR-006 | Idempotent stamp and guard | As a maintainer, I want stamping/guarding an already-cut-over mission to be a no-op, so re-runs never corrupt the event log. | Medium | Open |
| FR-007 | On-demand cut-over audit | As an operator, I want to list every mission's cut-over status on demand, so I can verify corpus health outside CI. | Medium | Open |
| FR-008 | Guard is wired to fire on corpus-only PRs as a required check | As a maintainer, I want the pre-merge guard to actually trigger when a PR changes only `kitty-specs/**`, and to be a required, non-skippable status check, so a corpus-only mission PR cannot merge without the guard executing. | High | Open |
| FR-009 | Guard evaluates every mission in the diff, keyed on event-log evidence | As a maintainer, I want the guard to check every mission whose corpus appears in the PR diff — using the acceptance test's event-log-evidence eligibility + non-empty-snapshot + `status_phase` check, not bare `verify_backfill` — so natively-born missions (no frontmatter to seed) cannot pass vacuously. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No manual re-green | After this mission lands, `test_dogfood_corpus_backfilled` passes on `main` across at least 3 consecutive merge waves with zero manual re-green interventions. | Reliability | High | Open |
| NFR-002 | Bounded guard cost | The pre-merge guard evaluates only missions touched by the change set (diff-scoped) and completes in under 30s in CI on the current corpus. The full-corpus acceptance lock (NFR-001) is a separate, slower check. | Performance | Medium | Open |
| NFR-003 | Fail-closed by default | On any verify error, missing artifact, ambiguity, or absent `mission_id` at stamp time, the guard/stamp blocks (non-zero exit); it never passes on uncertainty and never falls back to slug-namespaced seed identity. | Safety | High | Open |
| NFR-004 | Deterministic stamp (payload-level) | The stamp produces byte-identical seed events — identity **and** payload (including the resolved claim anchor) — for identical mission input across runs, machines, and landing-path contexts. Anchor resolution is pinned to one canonical leg so the two stamp callers cannot diverge. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Respect the PR workflow | The guard operates pre-merge on pull requests; the stamp commits into the mission branch. No mechanism may push directly to `origin/main`. | Technical | High | Open |
| C-002 | Phase-2 model only | Only `status_phase = "1"` (event-sourced) is written; the retired frontmatter `lane` mirror must not be reintroduced. | Technical | High | Open |
| C-003 | Do not rewrite migrated corpus | The change must not alter the ~319 already-cut-over missions; only un-cut-over missions are affected. | Technical | High | Open |
| C-004 | No spec-kitty execution at GitHub-merge time | The design must not assume any Spec Kitty command runs at GitHub-side merge time; the cutover must already be committed in the branch, enforced by CI. | Technical | High | Open |
| C-005 | Scope boundary | Out of scope: read-side placement (#2922), write-target consolidation (#2966 parts B/C), terminology migration (#2964). The mechanical re-green (#2968) is already shipped and must not be redone. | Business | Medium | Open |

### Key Entities

- **Mission corpus**: the committed `kitty-specs/<mission>/` artifacts — `meta.json`
  (`status_phase`) and `status.events.jsonl` (event log) — that the acceptance
  test evaluates.
- **Cutover stamp**: `status_phase = "1"` plus the deterministic seed events that
  make `verify_backfill` pass.
- **verify_backfill**: the parity check asserting the reduced snapshot equals the
  legacy reader by count and value.
- **Pre-merge guard**: the fail-closed CI check enforcing that every touched
  mission is cut over before merge.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of missions that land on `main` — via either landing path — are
  cut over (0 un-cut-over over at least 3 post-mission merge waves).
- **SC-002**: Every pull request that would introduce an un-cut-over mission is
  blocked by CI before merge (0 false negatives across the guard's test set).
- **SC-003**: 0 manual re-green interventions are required in the release cycle
  following this mission.
- **SC-004**: `test_dogfood_corpus_backfilled` stays green on `main` continuously
  after this mission lands.

## Assumptions

- The confirmed approach is **auto-stamp + fail-closed guard** (operator decision,
  2026-07-27): stamp the cutover into the branch at a terminal lifecycle point and
  enforce with a pre-merge CI guard. The exact terminal seam (e.g. `accept` /
  mission completion) and guard host are plan-phase decisions.
- The stamp reuses the canonical `runtime_state_cutover.cutover_mission` helper
  (single authority) — the same function `merge/executor.py::_run_birth_cutover`
  already calls — rather than a second implementation.
- The pre-merge guard reuses the acceptance test's event-log-evidence eligibility
  and birth-invariant body (`_mission_carries_event_log_runtime` /
  `_assert_birth_invariant_holds`), **not** bare `verify_backfill` (which is
  vacuous for natively-born missions). `verify_backfill` remains part of the
  check but is necessary-not-sufficient.
- The pre-existing corpus backlog was already re-greened whole-corpus by hotfix
  #2968; with the auto-stamp preventing new drift and the diff-scoped guard
  blocking any that slips, the full-corpus acceptance lock stays green on `main`
  without a further one-time backfill.
- The on-demand audit (FR-007) is a `spec-kitty doctor` subcommand backed by
  `cutover_repo(dry_run=True)`, matching the existing per-subcommand-module
  doctor convention.
- Confirmed seam candidate is the terminal `accept` step (runs on the mission
  branch, pre-PR, already commits residual acceptance artifacts); the exact seam
  and guard-host workflow are validated in the plan, including a live scratch-PR
  check that the guard fires on a corpus-only diff (per the #2968 lesson that
  path filters must be verified, not read).

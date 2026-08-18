# Mission Specification: Worktree-Aware Root Resolution & Verdict Parity

**Mission Branch**: `fix/worktree-root-resolution`
**Created**: 2026-08-18 · **Reframed**: 2026-08-18 (post-plan adversarial squad)
**Status**: Draft
**Mission ID**: `01M0B59R1GMN6N33GSGJFVNBP9`
**Base**: `upstream/main` (re-verify tip at implement time; squad ran against `30cffb08b3`) · **Topology**: coord
**Input**: Mission brief `.kittify/mission-brief.md`, operator-ratified scope Tier A+B+C (2026-08-18), **reframed** after a post-plan adversarial squad refuted the brief's clone-re-anchor grounding (see Overview + research.md).

## Overview

A family of commands keys off the **ambient invoking location** — `find_repo_root` / `locate_project_root` / `get_main_repo_root` and their wrappers — and, when invoked from a **linked lane worktree the command does not own**, silently acts on the **primary checkout** instead. This produces two real, decidable harms: **silent cross-checkout writes** (a `--fix`/`intake` write lands in the primary's tracked/untracked state) and **false-green guards** (a cutover/branch check reads a redirected path and reports agreement). The authoritative root-cause investigation for this class is `docs/plans/investigations/write-path-topology-root-cause.md` (spike **#3129**); its accepted remediation is a **fail-closed checkout-identity refusal** (**#3128**) — the command refuses, naming the checkout it would otherwise have acted on — **not** a checkout-local redirect.

This mission fixes the confirmed members of that class and closes the review-verdict CLI-parity gaps that ride the same lifecycle seam.

### What this mission is NOT (grounding corrections — verified against base)

A post-plan adversarial squad (2026-08-18), including an **empirical run of the resolver family**, corrected three load-bearing errors in the original brief:

1. **The "standalone clone re-anchored to a primary" bug does not exist.** A standalone clone's `.git` is a directory, so every resolver already returns the clone as its own primary — the desired outcome. The clone/primary split is also **undecidable** from local git state (a fresh clone ≡ its upstream, byte-for-byte). This mission therefore targets the **linked-worktree / nested-clone invoking-location** distinction, not "clone vs primary".
2. **The worktree→primary re-anchor is often deliberate.** `doctor mission-state --fix`'s primary anchor (`_anchor_repair_root`, per issue **#2320**) and the primary-read anchors (`get_feature_target_branch`, `resolve_merge_target_branch`, `mission_runtime/resolution.py`, per **#3328**) are **intended** and enforced by existing tests. The fix MUST preserve them. The defect is the **absence of checkout-identity awareness** (silent action from a foreign checkout), not the primary anchor itself.
3. **Two already-fixed residuals are out of scope** (verified true in code + ancestry): the `review_result` reducer projection (`407ea376c4`, `status/reducer.py:210-215`) and repair-row preservation (`bec7c25273`, `migration/mission_state.py:1879`). This mission builds on them (C-001/C-002).

### Tracker re-triage flagged by the squad (operator to action, not blocking this spec)

- **#3449 `--owned-checkout`** → recommend **wontfix**: the ownership machinery (`resolve_ownership_claim` → `effective_root` → `create_time_target`) already routes create-time writes to the claimed checkout; the "unreachable" hypothesis is not borne out by the code. Dropped from scope.
- **#3461 writer-half (coordination-key `UNKNOWN_SHAPE`)** → recommend **wontfix**: the post-tasks squad (3 lenses) confirmed it was already fixed by #2696 (`META_COORDINATION_KEYS` ⊆ meta.json known-keys; `mission_metadata.py` does not write those keys). WP12/FR-018 dropped.
- **#3563 full write-side kind-flip** → **partially blocked**: `review/cycle.py:106-158` discloses the global default-flip is not yet safe (moves the physical write into the coord worktree, breaks `test_analysis_report_rehome`). This mission ships only the safe narrow opt-in (FR-017); the full flip needs the physical-write/git-staging separation rework + 3 unrouted sites, tracked separately.
- **#3051 / #2320 contradiction** → reconciled in-mission: keep the primary status-home (#2320), add checkout-identity refusal (#3129). No tracker action required unless the operator disagrees with the reconciliation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fail-closed on a foreign-checkout write (Priority: P1)

An agent runs a state-writing/repair command (`intake`, `doctor tool-surfaces --fix`) from inside a lane worktree it does not own. Today the command silently acts on the primary checkout. After the fix it refuses, naming the checkout it would otherwise have written to (the #3128 fail-closed pattern).

**Why this priority**: Silent cross-checkout writes are the core data-integrity harm and the confirmed root of the class (#3129 §1).

**Independent Test**: From a lane worktree, run each in-scope writing command and assert it refuses with a message naming the target checkout, rather than mutating the primary. Independently testable through the real CLI.

**Acceptance Scenarios**:

1. **Given** a lane worktree with a drifted `.claude/commands/*` surface, **When** `doctor tool-surfaces --fix` runs, **Then** it refuses (naming the primary checkout) rather than silently repairing the primary's manifest. (#2613)
2. **Given** a lane worktree, **When** `intake <plan>` runs and would clobber the primary's shared untracked brief slot, **Then** it refuses / performs an identity check naming the target slot; `--force` does not overwrite a slot owned by a different checkout without that check. (#3540)
3. **Given** any in-scope command that refuses, **When** it emits the refusal, **Then** the message contains the concrete checkout path it would otherwise have acted on. (NFR-003)

---

### User Story 2 - One review-verdict path on both surfaces (Priority: P1)

An orchestrator walks a WP `in_progress → done` (incl. the `in_review` exit) recording a structured verdict. Today only `orchestrator-api transition` accepts a structured `review_result`; `agent status emit` cannot exit `in_review`, its `--help` misroutes the verdict into `--evidence-json`, and the `for_review` commit-gate is one surface's extra check that fails a clone on topology instead of commits.

**Why this priority**: The strongest, cleanly CLI-reproducible red-first slice; the `--help` trap actively misleads operators.

**Independent Test**: Using `agent status emit` alone, walk a WP to `done` with a structured verdict, and assert the `for_review` gate is identical on both surfaces and topology-aware.

**Acceptance Scenarios**:

1. **Given** a WP in `in_review`, **When** `agent status emit --review-result-json '<verdict>'` runs, **Then** the verdict is validated by the same parser both surfaces use, threaded into the transition, and the WP advances toward `approved`/`done`. (#3547, #1734)
2. **Given** either surface, **When** the `for_review` commit-gate evaluates, **Then** it enforces the same invariant, is topology-aware, and evaluates a clone on **commit state** — passing when commits are satisfied and failing when they are not. (#3547)
3. **Given** `agent status emit --help`, **When** an operator reads it, **Then** the misleading `in_review`/`--evidence-json` verdict example is corrected to the working `--review-result-json` path. (#3547)

---

### User Story 3 - No false-green guard (Priority: P1)

An operator relies on a cutover/branch guard. Today `setup-plan` reports `branch_matches_target: true` from the primary's HEAD (not the invoking checkout), and `migrate backfill-runtime-state`'s cutover guard verifies against the same redirected path it wrote — both green regardless of the invoking checkout.

**Why this priority**: A false-green guard launders a redirected read into a success signal; both are confirmed defect-class members (#3129 §1).

**Independent Test**: Run each guard from a lane worktree whose branch/state differs from primary and assert it does not report agreement produced by reading a redirected path.

**Acceptance Scenarios**:

1. **Given** a lane worktree on a lane branch, **When** `setup-plan` evaluates, **Then** `branch_matches_target` reflects the invoking checkout / mission `meta.json`, not the primary's HEAD. (#3124)
2. **Given** `migrate backfill-runtime-state` invoked from a lane worktree, **When** its cutover guard runs, **Then** it does not pass merely by reading the same redirected path it wrote — it is invoking-checkout-aware (or refuses). (#3049)

---

### User Story 4 - Snapshots round-trip and audit clean (Priority: P2)

An operator audits the status event log. Today a review-carrying `status_event_row` emits `UNKNOWN_SHAPE` because `review_result` is unregistered, and no test guarantees a snapshot survives replay by value.

**Independent Test**: Replay an event log carrying a `review_result` and assert (a) the replayed projection equals the persisted snapshot by value, and (b) the row audits with 0 `UNKNOWN_SHAPE`.

**Acceptance Scenarios**:

1. **Given** a `status_event_row` carrying `review_result`, **When** the audit shape registry validates it, **Then** `review_result` is a registered key and no `UNKNOWN_SHAPE` is emitted. (#3543)
2. **Given** a persisted snapshot with a `review_result`, **When** its event log is replayed, **Then** the replayed projection **equals** the snapshot by value (not merely key-presence). (#3543)
3. **Given** a new `status_event_row`-scoped registration test, **When** a persisted event shape is unregistered, **Then** the test fails (a real assertion — the existing `meta.json`-scoped drift test does not cover this artifact). (#3461-registry)

### Edge Cases

- A command invoked from the **primary checkout it owns** must behave exactly as today (no new refusal) — the guard fires only for a foreign-checkout invocation.
- Deliberate primary anchors (#2320 status-home, #3328 primary-reads) must remain green — the fix must not regress the "merge into wrong branch" protections.
- `find_repo_root` crossing a **nested-clone** `.git`-directory boundary that lacks `.kittify` (disagreeing with `resolve_canonical_root`, which stops correctly) — align them. (#2610)
- A WP in a terminal or non-`in_review` lane receiving `--review-result-json` must be rejected consistently on both surfaces.
- The `for_review` gate on a clone with **unsatisfied** commits must fail identically on both surfaces (negative case).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement (testable) | Related Issues | Priority | Status |
|----|------------------------|----------------|----------|--------|
| FR-001 | Introduce one shared **checkout-identity guard** that distinguishes an invocation from a checkout the command owns vs a foreign lane worktree; in-scope commands consult it rather than re-deriving `.git` classification. This is an **identity/ownership** guard, not a clone-vs-primary classifier. | #3129 / #3128 | High | Open |
| FR-002 | `intake` MUST perform a fail-closed checkout-identity check before writing the shared untracked brief slot from a foreign checkout — refusing and naming the target slot; `--force` MUST NOT overwrite a slot owned by a different checkout without the identity check. | #3540 | High | Open |
| FR-003 | `doctor tool-surfaces --fix` MUST fail closed (refuse, naming the primary checkout) when invoked from a lane worktree, rather than silently mutating the primary's per-checkout agent-surface manifest. | #2613 | High | Open |
| FR-004 | `doctor mission-state --audit/--fix` MUST preserve the deliberate primary status-home (#2320) **and** add checkout-identity awareness so a lane invocation does not silently act as an unannounced primary canonicalization; the audit MUST NOT report a false-green from a redirected read. | #3051 | High | Open |
| FR-005 | `migrate backfill-runtime-state`'s cutover guard MUST be invoking-checkout-aware — it MUST NOT report success merely by verifying against the same redirected primary/coord path it wrote from a lane invocation. (The write target to the coord/primary event log is deliberate per C-003; the guard false-green is the defect.) | #3049 | High | Open |
| FR-006 | `setup-plan` MUST compute `branch_matches_target` from the invoking checkout / mission `meta.json`, not the primary's HEAD; it MUST NOT report `branch_matches_target: true` from a redirected read. (Target-branch resolution staying primary-anchored is deliberate and preserved; only the match computation is corrected.) | #3124 | High | Open |
| FR-007 | `find_repo_root` MUST stop at a nested-clone `.git`-directory boundary consistently with `resolve_canonical_root` (which already stops correctly at rule 1 / `.kittify`), eliminating the nested-clone resolver disagreement. | #2610 | Medium | Open |
| FR-008 | A documented **must-not-flip inventory** of deliberate primary-read anchors (`get_feature_target_branch`, `resolve_merge_target_branch`, `mission_runtime/resolution.py` closures, `merge/*`, `coordination/write_seam.py`) MUST be preserved unchanged; the checkout-identity guard MUST carry read/write **intent** so these primary reads do not flip to the invoking checkout (which would regress #3328 "merge into wrong branch"). Characterization tests pin them green. | #3328 (regression guard) | High | Open |
| FR-009 | `doctor mission-state --fix` in-scope repair MUST make the repair manifest enumerate every field it touches, including removed fields (manifest honesty). The verdict destruction is already fixed (C-002) — no destruction fix. | #3541 | Medium | Open |
| FR-010 | `agent status emit` MUST accept `--review-result-json`, validated by the same `_parse_review_result_json` both surfaces use, with `review_result` threaded into the `TransitionRequest`; a WP MUST be walkable `in_progress → done` (incl. the `in_review` exit) through `agent status emit` alone. | #3547, #1734 | High | Open |
| FR-011 | The `for_review` commit-gate MUST be one shared, topology-aware invariant on both `agent status emit` and `orchestrator-api transition`; a clone MUST be evaluated on commit state — passing with satisfied commits and **failing with unsatisfied commits** (both directions asserted). | #3547 | High | Open |
| FR-012 | `agent status emit --help` MUST document only working paths; the misleading `in_review`/`--evidence-json` verdict example MUST be corrected. | #3547 | Medium | Open |
| FR-013 | The `in_review → approved` guard MUST admit a `ReviewResult` path on both surfaces. | #1734 | High | Open |
| FR-014 | `review_result` MUST be registered in the `status_event_row` shape (`audit/shape_registry.py`) so a review-carrying row audits clean (0 `UNKNOWN_SHAPE`). | #3543 | High | Open |
| FR-015 | A round-trip property MUST hold and be tested by **value equality**: replaying a persisted snapshot's event log reproduces the snapshot's projected fields by value (not key-presence); the property generator MUST be guaranteed to emit at least one `review_result`-carrying event (non-vacuous). | #3543 | High | Open |
| FR-016 | A **new `status_event_row`-scoped** registration/drift test MUST fail when a persisted event shape is unregistered. (The existing `test_shape_registry_writer_parity.py` is `meta.json`-scoped and cannot cover this artifact — de-tautologizing it does nothing for `review_result`.) *(The coordination-key registry side is already fixed by #2696 — `META_COORDINATION_KEYS` ⊆ meta.json known-keys — so no registry change is needed there.)* | #3461 (registry half) | Medium | Open |
| FR-017 | `review/cycle.py` MUST opt the safe consumer(s) into `kind=REVIEW_CYCLE` where the physical write location does not move, and MUST verify the already-repointed event-authority reader (`event_sourced_review_result`) is unaffected by the write-side kind, keeping `test_analysis_report_rehome` green. The **global write-side default flip is out of scope** — blocked by the disclosed physical-write/git-staging separation rework (`review/cycle.py:106-158`) + 3 unrouted sites. | #3563 (narrowed) | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement (measurable) | Category | Priority | Status |
|----|-------|--------------------------|----------|----------|--------|
| NFR-001 | Red-first regressions | Each release-blocking slice lands with an issue-pinned `@pytest.mark.regression` test, **authored and shown failing** on base before the fix (not a `-k` glob over non-existent tests), driving the real CLI entry point where one exists. For the fail-closed slices the assertion is **refusal / absence-of-false-green** (per #3128), not "writes into invoking checkout". FR-015/FR-016 are internal-API-level and are marked as such. | Reliability | High | Open |
| NFR-002 | Zero-issue static gates | New/changed code passes `ruff` + `mypy` with zero issues/warnings; complexity ≤15; `tests/architectural/` (terminology + shared-package) green; no new blanket suppressions. | Quality | High | Open |
| NFR-003 | Actionable refusals, single-channelled | 100% of write-refusals route through the one checkout-identity/`WriteTarget` seam whose refusal message names the target checkout path; enforced by an architectural test (no ad-hoc refusal strings), making "100%" an enforced invariant rather than a sampling claim. | Usability | Medium | Open |
| NFR-004 | Preserve already-fixed behavior | The already-fixed reducer projection and repair-row preservation ship a **green sentinel** regression test each (pinning `407ea376c4` / `bec7c25273`); no WP re-implements or regresses them to manufacture a red. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Projection already fixed | Do NOT re-implement the `review_result` reducer projection (`407ea376c4`, `reducer.py:210-215`) — verified true. Scope only registration + round-trip. | Technical | High | Open |
| C-002 | Destruction already fixed | Do NOT re-add a verdict-destruction fix (`bec7c25273`, `mission_state.py:1879`) — verified true. Scope only manifest honesty. | Technical | High | Open |
| C-003 | Remediation is fail-closed refusal, not redirect | Per the #3129 investigation, the canonical remediation for the write-path class is a fail-closed **checkout-identity refusal** (#3128), NOT a checkout-local write redirect. Commands whose canonical write target is deliberately primary/coord keep that target; the fix adds identity awareness/refusal + fixes the guards. | Technical | High | Open |
| C-004 | Preserve deliberate primary anchors | #2320 (primary status-home) and #3328 (primary-read anchors: `get_feature_target_branch`, `resolve_merge_target_branch`, `mission_runtime/resolution.py`) MUST NOT be flipped to the invoking checkout. See FR-008. | Technical | High | Open |
| C-005 | Clone axis is not a behavioral distinction | Do NOT ship a PRIMARY-vs-STANDALONE_CLONE classifier — the distinction is undecidable from local state and behaviorally moot (clones already resolve to self). The decidable axis is linked-worktree/nested-clone invoking-location. | Technical | High | Open |
| C-006 | #3461-writer dropped | The #3461 coordination-key writer migration (was FR-018/WP12) is **dropped** — the post-tasks squad confirmed the coord-key `UNKNOWN_SHAPE` residual was already fixed by #2696 (`META_COORDINATION_KEYS` ⊆ meta.json known-keys; `mission_metadata.py` is not even the writer). Recommend tracker wontfix on the #3461-writer half. | Technical | Medium | Open |
| C-007 | Base & topology | Base `upstream/main` (re-verify tip at implement time), coord topology, lands on `fix/worktree-root-resolution`. | Technical | High | Open |
| C-008 | Out of scope | Keep separate: #3449 (dropped — already correct, recommend wontfix); #3531, #3307/#3451/#3010, #3043/#3065/#3462 (read-seam consolidation — the checkout-identity guard MUST NOT tidy read paths), #2626/#2947/#3536, #2815; #3323 folds only if same resolver; #3548 campsite-fold-only. | Business | Medium | Open |

### Key Entities

- **Checkout-identity guard** (new): given the invoking CWD and the command's intent, decides whether the invocation *owns* the target checkout or is acting from a *foreign* lane worktree; carries read/write intent so deliberate primary reads are not flipped.
- **Invoking-location vs canonical target**: the mission's real distinction — where the command was invoked from vs where its canonical write/read deliberately lives. Replaces the discarded "clone vs primary" framing.
- **`review_result`** (existing): structured verdict on a status transition; projection already correct — this mission adds entry parity + audit registration + value round-trip.
- **`for_review` commit-gate** (existing): one shared, topology-aware invariant across both CLI surfaces (both gate directions asserted).
- **`status_event_row` shape** (existing): must register `review_result`; needs a new artifact-scoped drift test distinct from the `meta.json` one.

## Success Criteria *(mandatory)*

- **SC-001**: For every in-scope writing command, a foreign-checkout invocation refuses (fail-closed, naming the target checkout) or performs an identity check — 0 silent cross-checkout writes (covers FR-002, FR-003; owner-checkout invocations unchanged).
- **SC-002**: 0 false-green guards — no `branch_matches_target: true` or cutover pass produced by reading a redirected path (covers FR-005, FR-006).
- **SC-003**: Deliberate primary anchors stay green — the fix regresses neither #2320 status-home nor #3328 primary-reads; the must-not-flip inventory (FR-008) has passing characterization tests (covers FR-004, FR-008, C-004).
- **SC-004**: A WP walks `in_progress → done` (incl. `in_review`) with a structured verdict via `agent status emit` alone; the `for_review` gate yields identical verdicts on both surfaces across the topology matrix in **both** directions; `--help` has 0 non-functional example paths (covers FR-010…FR-013).
- **SC-005**: A review-carrying `status_event_row` audits clean (0 `UNKNOWN_SHAPE`); the value-equality round-trip holds for 100% of replayed snapshots with a non-vacuous generator (covers FR-014…FR-016).
- **SC-006**: Each release-blocking slice ships an issue-pinned red-first regression authored and shown failing on base; already-fixed behavior ships a green sentinel (covers NFR-001, NFR-004).

## Assumptions

- "Mission type: fix" maps to canonical `software-dev` on the `fix/` branch.
- The #3129 investigation (`docs/plans/investigations/write-path-topology-root-cause.md`) is the authoritative root-cause source; its #3128 fail-closed remediation is the canonical pattern for this class.
- #3051/#2320 reconciliation (keep primary status-home + add identity refusal) is adopted; operator may override.
- #3449 is dropped as already-correct (squad-verified); recommend tracker wontfix.
- Base tip must be re-verified at implement time (squad ran against `30cffb08b3`; both already-fixed residuals still held).

## Lineage / References

- Authoritative root-cause: `docs/plans/investigations/write-path-topology-root-cause.md` (spike **#3129**), remediation **#3128** (fail-closed checkout-identity refusal). Parent epics **#2624** (spine), **#3549** (event-log integrity), **#3044** (review-artifact integrity).
- Already-fixed antecedents (verified): `407ea376c4` (projection), `bec7c25273` (repair preservation). Deliberate anchors: **#2320** (primary status-home), **#3328** (primary-reads).
- Post-plan adversarial squad (2026-08-18): architect + reviewer + debugger converged (incl. empirical resolver run) on the clone-phantom / deliberate-re-anchor findings that drove this reframe.
- Red-first / red-main discipline: ADR `2026-07-17-1`.

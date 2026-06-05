# Merge Preflight Remote-State Boundary Separation

**Mission ID**: 01KTBE5MPD24VTVFHXKCF8MGHN
**Status**: Specifying
**Mission Type**: software-dev
**Related Issue**: https://github.com/Priivacy-ai/spec-kitty/issues/1706

---

## Purpose

`spec-kitty merge` integrates approved mission lane branches into the local target branch. This is a purely local operation: no remote repository is involved, and no internet connection is required. A separate, subsequent step (`--push`) publishes the result to origin.

Currently, the merge command performs a live network check against `origin` before any local branch is touched, and blocks the entire merge if the local target branch is not exactly in sync with origin. This is architecturally inverted. The check enforces a push-safety invariant — whether a future `git push` will succeed cleanly — at the wrong moment and on the wrong operation. The result is that users who accumulate local planning commits, orchestration history, or unsynced origin work cannot run a local merge at all, even though those conditions have no bearing on whether the local merge itself is safe.

This mission separates the two concerns: local-merge safety (determined entirely by the local git graph) and push safety (relevant only when a push is actually requested). It relocates remote-state inspection to the publish layer, corrects the blocking predicate, and adds the necessary persistence field so that resumed merge operations know whether to perform a push check without requiring the user to re-state their intent.

---

## Background

The five-paradigm debugging analysis (Debugger Debbie) and five-lens architecture scout review (Paula Patterns) conducted for issue #1706 converge on the same root cause: a push-safety pre-condition inserted into the local-integration layer. All five architecture lenses (layered, DDD, event-driven, hexagonal, and contract) classify this as a release-blocking boundary violation. The defect was introduced at mission 017 (smarter-feature-merge-with-preflight) and was normalized by a subsequent PR that added a workaround note to `AGENTS.md` rather than correcting the check.

---

## User Scenarios

### Primary — Local merge with diverged local/origin state (issue #1706)

A developer's local `main` has accumulated 10 orchestration and planning commits that origin does not have. Origin has 5 new commits that local does not have. The developer has completed a mission and runs `/spec-kitty.merge`. Under the current behavior, the merge is blocked with "TARGET_BRANCH_NOT_SYNCHRONIZED" and the developer is directed to a PR-based workaround. Under the corrected behavior, the local merge proceeds to completion. The developer syncs with origin on their own schedule — before or after the local merge, as their workflow dictates.

### Secondary — Push-requested merge with diverged state

A developer runs `/spec-kitty.merge --push`. Their local `main` has diverged from origin (local has commits origin lacks and origin has commits local lacks). Because a push was explicitly requested, the push-safety check fires. The developer sees the same diverged guidance as today: rebase, or use the focused-PR-branch escape hatch. No regression from current push-requested behavior.

### Secondary — Push-requested merge with behind state

A developer runs `/spec-kitty.merge --push`. Their local `main` is behind origin (origin has commits local lacks). Because a push was explicitly requested, the push-safety check fires and blocks before local lane integration, target merge, or bookkeeping. This prevents a known non-fast-forward push rejection after local mutation.

### Tertiary — Resumed merge preserves push intent

A merge is interrupted mid-run (network failure, process kill). On resume, the system reads the persisted `push_requested` state and automatically includes or excludes the push step — no need for the user to re-supply `--push` to the resume invocation.

### Exception — Network unavailable during push-requested merge

A developer is offline and runs `/spec-kitty.merge --push`. The remote-state fetch fails. The system reports the fetch failure and blocks before local lane integration, target merge, or bookkeeping. The developer can retry without `--push` for a local-only merge or retry with `--push` when online.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | When merge is invoked without requesting a push, no network fetch against the remote repository shall be performed at any point during the merge operation. | Accepted |
| FR-002 | When merge is invoked without requesting a push, the local merge shall proceed regardless of whether the local target branch is ahead, behind, diverged from, or in sync with its remote tracking branch. | Accepted |
| FR-003 | When merge is invoked with a push requested, the remote-state check shall fire before local lane integration, target merge, or bookkeeping mutation. | Accepted |
| FR-004 | When merge is invoked with a push requested and the local target branch is in a state that would cause a non-fast-forward or destructive push, the push path shall be blocked with remediation guidance before local mutation. | Accepted |
| FR-005 | The sync-state value model shall distinguish between "safe to merge locally" (true for all origin states — the local git graph is the only authority) and "safe to push" (false when the state would require a force push or cause destructive rewrite on origin). | Accepted |
| FR-006 | The component responsible for performing remote-state inspection and network I/O against origin shall reside in the publish layer, not in the local-merge domain layer. The local-merge domain layer shall have no dependency on remote-state inspection. | Accepted |
| FR-007 | The merge resume state shall persist whether the original invocation requested a push. A resumed merge shall respect the persisted push intent without requiring the user to re-supply the push flag. | Accepted |
| FR-008 | Existing merge resume state persisted without a push-intent field shall be readable without error, treating the absence of the field as "push not requested." | Accepted |
| FR-009 | All tests that currently assert "local ahead of origin" blocks the merge shall be updated to assert that condition does not block the merge. | Accepted |
| FR-010 | A regression test covering the exact scenario in issue #1706 (local target N commits ahead and M commits behind origin, merge requested without push) shall be added, asserting that the local merge completes without blocking. | Accepted |
| FR-011 | Documentation advising users to use a PR-based workaround when local is ahead of origin during merge shall be removed and replaced with accurate guidance reflecting that local-ahead state does not block a local merge. | Accepted |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | When a push is requested and the remote-state fetch succeeds immediately, the total additional latency introduced by the relocated push-preflight check (compared to a local-merge-only run) shall not exceed 3 seconds. "Standard network connection" means LAN or broadband with round-trip latency ≤ 100ms to the Git remote. Validated observationally; not covered by automated test suite in this mission. | ≤ 3 seconds | Accepted |
| NFR-002 | Strict type checking must pass with zero new type errors after all changes. | 0 new type errors | Accepted |
| NFR-003 | Test coverage for the modified merge preflight and push-preflight modules must meet or exceed the project baseline of 90%. | ≥ 90% coverage | Accepted |
| NFR-004 | A resumed merge invocation must correctly apply or skip the push step based on the persisted push-intent field, with no loss of intent. | 100% fidelity on resume | Accepted |
| NFR-005 | Backward compatibility: existing stored resume state (without the push-intent field) must not cause any error on read. | Zero read errors on legacy state | Accepted |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The existing push-safety guidance for diverged state (rebase recommendation, focused-PR-branch escape hatch) must be preserved for push-requested invocations. This mission corrects when the check fires; it does not weaken the check itself for cases where it is appropriate. | Accepted |
| C-002 | The WP-level preflight (`run_preflight()`) — which checks that worktrees are clean and that the local target is not behind origin — is out of scope and must not be modified. Only the target-branch sync preflight that guards the entire merge command is in scope. | Accepted |
| C-003 | No changes to lane resolution, worktree management, conflict classification, the forecast module, or the status resolver. | Accepted |
| C-004 | The push-intent field added to resume state must use a backwards-compatible default (absent field = push not requested) so that operators running partial merges across the version boundary are not disrupted. | Accepted |
| C-005 | This mission does not change when or how `git push origin` itself executes — only the preconditions for that step. | Accepted |

---

## Success Criteria

1. A user whose local target branch is ahead of, behind, or diverged from origin can complete a local merge with no error messages related to origin sync state.
2. A user who requests a push as part of merge is blocked before local mutation when the push would fail or be destructive — and sees no blocking behavior when the push would succeed cleanly.
3. A merge resumed after an interruption automatically includes or excludes the push step with 100% fidelity to the original invocation, without user re-intervention.
4. No network I/O occurs during merge invocations that did not request a push, verifiable by monitoring network traffic or by running the merge command in an offline environment.
5. All automated tests pass after the change, including the new #1706 regression test and the updated "ahead-is-not-blocked" assertions.

---

## Key Entities

| Entity | Role |
|--------|------|
| Sync-state value model | Represents the relationship between local and remote target branch. Gains separate local-merge-safety and push-safety predicates. |
| Push preflight module | New module in the publish layer. Owns remote-state fetch and push-safety evaluation. Has no presence in the local-merge domain layer. |
| Merge resume state | Persistent record of an in-progress merge. Gains a push-intent field for correct resume behavior. |
| Local merge domain | The integration layer. After this mission, has no knowledge of or dependency on remote-state inspection. |

---

## Assumptions

1. The "focused-PR-branch escape hatch" in the diverged guidance remains useful for operators who need to handle complex push situations; removing it is out of scope.
2. "Behind" state (origin has commits local lacks) is safe for local merge. For push, it is blocked before mutation because git would reject the final push as non-fast-forward.
3. The project test suite has sufficient integration fixtures to support a realistic #1706 scenario test (local-ahead + local-behind git state) without requiring a live remote.

---

## Dependencies

- Issue #1706 is the direct trigger.
- No dependency on other open missions.
- Architecture ADRs `2026-04-03-1-execution-lanes-own-worktrees-and-mission-branches.md` and `2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md` define adjacent local-graph staleness checks; this mission must not conflict with those boundaries.
- An ADR documenting the push-layer boundary decision must be produced as part of this mission (see FR-006, DIRECTIVE_003).

---

## Domain Language

| Canonical term | Meaning | Synonyms to avoid |
|----------------|---------|-------------------|
| Local merge | The operation of integrating lane branches into the local target branch. No network involved. | "merge and push", "sync merge" |
| Publish / push step | The operation of pushing the integrated local target branch to the remote repository. Follows local merge. | "origin sync", "remote merge" |
| Push-safety check | The remote-state inspection that determines whether a push would succeed non-destructively. Belongs in the publish layer. | "preflight", "sync preflight" (when used ambiguously to mean this check) |
| Local-merge safety | Whether the local git graph supports the integration. Determined entirely by local branch state; origin state is irrelevant. | (no existing term — this mission introduces the distinction) |
| Diverged | Local and remote have both accumulated commits the other lacks. An origin state that is unsafe for a non-destructive push. | "out of sync", "conflicting" |
| Push-preflight module | The Python module (`push_preflight.py`) that implements push-safety checks. Belongs in the publish layer. The domain layer (`preflight.py`) must not import from it. | "push safety module", "push check module" |

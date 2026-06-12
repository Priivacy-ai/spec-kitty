# Phase 0 Research: Coordination and Merge Stabilization

**Date**: 2026-06-12 | **HEAD at research time**: d6363c8ba (planning commits on main; code state equivalent to 956ab0e3e)

All root-cause verification was performed by the Debbie/Paula validation workflow against HEAD with file:line evidence — see [validation/debbie-analysis.md](validation/debbie-analysis.md) (divergence matrix, falsified hypotheses, dormant masks) and [validation/paula-analysis.md](validation/paula-analysis.md) (scout matrix, ship-now vs follow-up split). This document records the remaining *fix-shape decisions* and their rationale. No `[NEEDS CLARIFICATION]` markers remain.

## R1 — Class B fix shape: per-site resync vs shared helper vs transaction self-heal

- **Decision**: Shared minimal helper (`advance_branch_ref(repo_root, ref, new_sha)` or equivalent) used by the three known sites (`lanes/merge.py:440`, `:474`; `cli/commands/merge.py:993-998`), which performs the `update-ref` and then resyncs any worktree that has the advanced branch checked out — refusing loudly if that worktree is dirty. Additionally accept Debbie's belt-and-braces option: a cheap index-behind-HEAD self-heal check in `BookkeepingTransaction._acquire_locked` is **not** included (one mechanism, not two — mirrors C-003's no-double-mechanism principle).
- **Rationale**: Three call sites with identical needs make per-site inline copies a drift hazard (dormant mask 11 in debbie-analysis: any new `update-ref` site re-inherits the bug). A shared helper enables the AC-B3 ratchet ("no raw update-ref outside the helper") which is the cheapest possible recurrence guard. Paula's constraint is honored: blast radius stays inside the merge pipeline (C-002) — the helper is *available* but only the three sites are migrated.
- **Alternatives considered**: (a) Per-site inline resync — rejected: no ratchet anchor, drift-prone. (b) Self-heal in `BookkeepingTransaction` only — rejected: heals the symptom at one consumer; other consumers of the stale worktree (e.g. direct git use) stay broken; harder to assert AC-B2. (c) Both helper and self-heal — rejected: two mechanisms for one invariant violates the mission's own C-003 spirit.

## R2 — Class B dirty-worktree refusal semantics

- **Decision**: Before resync, run `git status --porcelain` in the coordination worktree. If non-empty, raise a structured error naming the worktree path, the advanced ref, and the dirty entries; do NOT reset. Exit the merge with the same resumable-state behavior as other merge failures (merge-state.json preserved).
- **Rationale**: NFR-002 (no silent data discard) and spec Assumption 2: the coord worktree is clean *by design* during bookkeeping; dirt indicates a bug or operator intervention — exactly when an automated `reset --hard` would destroy evidence. The existing `SafeCommitBackstopError` flow proves resumable-failure UX is acceptable here.
- **Alternatives considered**: Auto-stash — rejected: hides the anomaly, complicates recovery, and contradicts the cluster thesis (loud, named failures).

## R3 — Class C guard placement

- **Decision**: Gate the `_ensure_branch_checked_out(...)` call at `cli/commands/agent/mission.py:2462` behind `not validate_only`. No shim deletion.
- **Rationale**: Debbie's Class C analysis confirmed post-WP07 validate-only reads anchor on the primary feature dir (no dependency on being checked out on target); Part 2 of #1861 was falsified (already resolved by `SafeCommitHeadMismatch`, commit 8e79b3f6d). Smallest change that makes the command honest; shim retirement is in the #1666 umbrella (C-001).
- **Alternatives considered**: Replace eager checkout with plumbing reads everywhere — rejected for 3.2.0: that is the shim-retirement architecture work (non-goal).

## R4 — Class D invariant enforcement point(s)

- **Decision**: Enforce "a resolved workspace is a real git worktree" at all three trust boundaries: (a) `ResolvedWorkspace.exists` requires a `.git` entry (file or dir — worktrees use a `.git` *file*); (b) review-claim acquires `ReviewLock` only after the workspace exists, and `git worktree add` failure is a hard error; (c) move-task asserts `git -C <path> rev-parse --show-toplevel` equals the resolved path before any other git call.
- **Rationale**: The husk class has three independent entry points (creation, locking, consumption) — guarding only one leaves the others as dormant masks (debbie-analysis Class D). Checks are O(1) git calls; NFR-003 satisfied by structured errors naming the husk path.
- **Alternatives considered**: Single chokepoint in the resolver only — rejected: move-task receives paths from more than one resolver lineage today; the toplevel assertion is the last-line defense until the #1666 allocator unification lands.

## R5 — Doctor husk check shape (FR-007)

- **Decision**: Add a doctor check that lists `.worktrees/*` entries lacking a `.git` entry and offers `--fix` removal (only when `git worktree list` does not register the path — never remove a registered worktree). Follow the existing doctor check registration pattern (same shape as the registered checks in the doctor module; reuse the quarantine/report conventions from `doctor mission-state`).
- **Rationale**: Spec edge case: pre-existing husks start erroring once Class D guards land; recovery must be one command in the same release.
- **Alternatives considered**: Auto-clean husks on resolution failure — rejected: deletion as a side effect of a read path violates least surprise and NFR-002's spirit.

## R6 — Class A residue cleanup mechanism (#1814)

- **Decision**: `_stage_finalize_artifacts_in_coord_worktree` (`cli/commands/agent/mission.py:99-131`) tracks exactly the primary-side paths it materializes and removes them after successful staging into the coordination worktree (or avoids writing them to the primary checkout at all where the write is incidental). `COORD_OWNED_STATUS_FILES` is NOT widened (C-003).
- **Rationale**: Cleanup-at-source keeps one authority for "what belongs on primary"; widening the exclusion list is the whack-a-field anti-pattern Paula's scout matrix flagged. The test asserts `git status --porcelain` is clean of planning-artifact residue post-finalize (AC-A1).
- **Alternatives considered**: Widen exclusion list — rejected by C-003 (double mechanism, hides the writer bug).

## R7 — Class F exception narrowing scope

- **Decision**: `coordination/status_transition.py:399-400` catches exactly `(ValueError, FileNotFoundError)` with a comment documenting the GENESIS fallback contract; all other exceptions propagate. Lands with/after the Class B resync (C-004).
- **Rationale**: Debbie's dormant-mask list shows the broad except can swallow genesis-corruption signals; the two retained types are the only documented expected failures (absent log, pre-schema log).
- **Alternatives considered**: Catch-log-reraise — rejected: the call site's contract is fallback-to-GENESIS for expected misses, not error logging.

## R8 — Issue hygiene execution (FR-011)

- **Decision**: Close #1770, #1789, #1816, #1771, #1571 citing landed commits (8544012fa / PR #1850, c5a10ce56 / PR #1793, PR #1719); close #1784 as duplicate-of-#1777-fixed and #1735 after folding residuals into this mission; re-scope (retitle + body update) #1814, #1736, #1833, #1861 to residual scope; file ONE follow-up umbrella issue under epic #1666 carrying the C-001 non-goals (resolver strangler completion, ref-advance helper rollout beyond merge pipeline, allocator unification, AC10 lint expansion, shim retirement, #1827 crash-edge).
- **Rationale**: Validation comments with citations were already posted to all 13 issues (2026-06-12); hygiene is now mechanical. One umbrella (not six small issues) per Paula's recommendation to prevent backlog fragmentation.
- **Alternatives considered**: Leaving issues open until the mission merges — rejected: the seven FIXED issues describe behavior retired by *already-landed* PRs, independent of this mission.

## Falsified hypotheses (carried from validation — do not re-litigate)

1. "The safe-commit backstop is buggy" — falsified; it is the detector working as designed (#1826 analysis).
2. "safe-commit --to-branch bounces the checkout" (#1861 Part 2) — falsified; resolved by `SafeCommitHeadMismatch` (8e79b3f6d).
3. "The whole 13-issue cluster shares one root cause" — partially falsified; #1571 (publish-layer policy) and #1789 (background writers) are mechanically distinct classes, both already closed.
4. "#1770/#1816/#1771/#1789 still reproduce at HEAD" — falsified with file:line + regression-test evidence (PR #1850 et al.).

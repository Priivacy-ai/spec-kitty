# Contract: Class B — Ref Advance with Worktree Resync (#1826)

**Surface**: internal merge-pipeline helper (shape per research R1) replacing raw `git update-ref` at `lanes/merge.py:440`, `lanes/merge.py:474`, `cli/commands/merge.py:993-998`.

## Behavior

GIVEN a branch ref advanced by the merge pipeline (lane→mission merge or mission-number baking)
WHEN any git worktree has that branch checked out
THEN after the advance, that worktree's HEAD, index, and working tree match the new branch tip (CONSISTENT state)
AND the subsequent bookkeeping safe-commit succeeds without `SafeCommitBackstopError`.

GIVEN the checked-out worktree holds uncommitted local state at advance time
THEN the operation raises a structured refusal (no `reset --hard` executes) naming: worktree path, ref, old→new SHA, and the dirty entries
AND merge state remains resumable (merge-state.json preserved).

GIVEN no worktree has the branch checked out
THEN behavior is identical to today's raw `update-ref` (no extra work beyond the worktree scan).

## Postconditions & Ratchets

- AC-B1: end-to-end coord-topology merge (≥2 lanes + baking) completes unattended — `tests/specify_cli/cli/commands/test_merge_coord_worktree_resync_1826.py`.
- AC-B2: after each Stage-1 advance, coord worktree index == HEAD (direct assertion).
- AC-B3: architectural ratchet — no raw `git update-ref` subprocess invocation in `src/specify_cli` outside the helper.
- AC-B4: dirty-worktree refusal test (plant a file in the coord worktree; assert refusal + no data loss).
- FR-012 rider: `SafeCommitBackstopError` message names which worktree/ref diverged and the likely cause.

## Non-goals (C-002)

Migration of any ref-advance outside the merge pipeline; changes to `update-ref` semantics elsewhere; `BookkeepingTransaction` self-heal (rejected, research R1).

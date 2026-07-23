# Contract: coord-commit correctness (FR-001/002/003/004, NFR-001/002)

## Behavioral contract

| # | Given | When | Then |
|---|-------|------|------|
| 1 | a coord-routed mission, complete identity triple | a bookkeeping write commits | routes to `_commit_via_coordination_transaction`; commits to the coord worktree; `git show <coord_ref>:<path>` exists; no primary residue |
| 2 | a coord-routed mission, INCOMPLETE identity triple (`_load_coord_branch_meta` returns a `None`) | the commit path runs | it FAILS LOUD (misroute guard) — it must NOT reach the legacy leaf and commit coord paths from `repo_root` |
| 3 | the legacy leaf is legitimately reached (coord-less path) | its porcelain pre-check runs | the pre-check runs against the resolved worktree root (not `repo_root`); no phantom "already committed" for gitignored coord files |
| 4 | a deliberately mis-placed write (`worktree_root` ≠ `destination_ref`) | `safe_commit` runs | raises `SafeCommitHeadMismatch` — the write is unrepresentable at commit (NFR-001 negative case) |
| 5 | a review-cycle (`WORK_PACKAGE_TASK`, PRIMARY) artifact | authored | lands in its PRIMARY home (`tasks/<wp>/`), never the coord husk |
| 6 | `ANALYSIS_REPORT` (re-homed PRIMARY) | authored | lands PRIMARY (target branch); NO coord copy is made |
| 7 | a status event on a COORD-topology mission | emitted | commits to the coord worktree (not primary-uncommitted) |
| 8 | a status event on a coord-LESS topology (`SINGLE_BRANCH`/`LANES`/flat) | emitted | the non-transactional primary write path is PRESERVED (no regression) |

## Invariants (must hold after this mission)

- `assert_partition_invariant` green (disjoint-and-total) after the `ANALYSIS_REPORT` re-home.
- `safe_commit` unchanged: HEAD==`destination_ref` guard + `.worktrees/` path-policy intact (`git/` is read-only here).
- No second, independently-writable copy of any COORD artifact (residue factory removed for coord kinds).
- The modern transaction path is unchanged in behavior — proven by an added regression, not a code edit.

## Test contract (NFR-001/002)

- **Real-repo e2e** (no stubbed `safe_commit`): real `git init` + real `git worktree add` (via production
  `CoordinationWorkspace.resolve`), `CliRunner` on `agent action implement`/`review`; assert placement via
  `git show <ref>:<path>`. Reuse `tests/regression/test_issue_2508.py` + `tests/integration/coord_topology_fixture.py`.
- **Live #2861 causation repro** (runs FIRST): `agent action review WP## --agent tool:model:profile:role`
  with no `--invocation-id`; assert the failure mode (record whether the block is `SafeCommitHeadMismatch`
  = FR-002 seam, or the actor warning = FR-006 seam). The verdict gates the FR-005/006 claim on US2 AC-3.

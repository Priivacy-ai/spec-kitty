# Contract: Class D — Workspace Resolution Fall-Through Is Failure (#1833)

**Surfaces**: `workspace/context.py:148-150` (`ResolvedWorkspace.exists`), `cli/commands/agent/workflow.py:2237/2243/2265` (review claim), `cli/commands/agent/tasks.py:1346` (move-task), doctor husk check (FR-007).

## Behavior

GIVEN a directory under `.worktrees/` that lacks a `.git` entry (a HUSK)
WHEN any command resolves it as a lane workspace
THEN resolution fails with a structured error naming the husk path and the failed check
AND zero git commands execute against the primary repository as a result of that resolution
AND the error is NOT a misattributed verdict ("No implementation commits on lane branch!", primary-repo dirty-tree complaints).

GIVEN `git worktree add` fails during review claim
THEN the claim fails hard (no warning-and-continue), and no `ReviewLock` is held afterward (lock acquired only after the workspace exists).

GIVEN move-task receives a resolved workspace path
THEN it asserts `git -C <path> rev-parse --show-toplevel` == `<path>` before any other git invocation.

GIVEN an operator machine with pre-existing husks
WHEN they run the doctor husk check
THEN every `.worktrees/*` entry lacking `.git` is reported, and `--fix` removes entries not registered in `git worktree list` (registered worktrees are never removed).

## Postconditions & Ratchets

- AC-D1: planted-husk test — `tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py`.
- AC-D2: `ResolvedWorkspace.exists` False for husk; lock-after-create ordering asserted; worktree-add failure is an error.
- AC-D3: doctor check reports and (with `--fix`) removes husks.

## Non-goals (C-001)

Worktree-naming allocator unification; workspace-lifecycle/ReviewLock redesign; "is-a-worktree" as a type invariant across all resolvers (#1666 umbrella).

# Contract: Class C — validate-only Is Read-Only (#1861 Part 1)

**Surface**: `spec-kitty agent mission finalize-tasks --validate-only` (guard at `cli/commands/agent/mission.py:2462`).

## Behavior

GIVEN a repository where the mission target branch differs from the currently checked-out branch
WHEN the operator runs `finalize-tasks --validate-only`
THEN `git symbolic-ref HEAD` is byte-identical before and after
AND `git status --porcelain` output is byte-identical before and after (no staging, no checkout, no writes)
AND validation results are identical to those produced by the commit-phase run's validation step.

GIVEN `finalize-tasks` WITHOUT `--validate-only`
THEN behavior is unchanged from today (existing tests stay green — AC-C2).

## Postconditions & Ratchets

- AC-C1: before/after HEAD + porcelain assertions — `tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py`.
- AC-C2: existing finalize-tasks suite green unmodified.
- AC-C3 (hygiene rider): issue #1861 updated — Part 2 recorded as already resolved by `SafeCommitHeadMismatch` (8e79b3f6d).

## Non-goals (C-001)

Deleting the `_ensure_branch_checked_out` shim; converting commit-phase positioning to plumbing reads (deferred to #1666 umbrella).

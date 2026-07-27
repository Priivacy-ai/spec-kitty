# Contract: `WorkflowMutationPolicy`

**Spec source**: FR-019, FR-020, FR-021, C-012
**Module**: `src/specify_cli/coordination/policy.py`

## Purpose

Single chokepoint for protected-branch refusal. Called by `BookkeepingTransaction.acquire()` *before* any write happens, and called by `safe_commit()` *during* the commit attempt as a defense in depth. The policy input is **always** an explicit `destination_ref` — never inferred from CWD/HEAD.

## Signature

```python
class WorkflowMutationPolicy:
    @staticmethod
    def assert_allowed(change_set: GitChangeSet) -> PolicyVerdict:
        """
        Inspect change_set.destination_ref.
        Return Allowed if the would-be commit is permitted; Refused with a
        stable error_code otherwise.
        """
```

## Behavior

1. Validate inputs. `destination_ref` is required and non-empty. `repo_root` is a git repo.
2. Check whether `destination_ref` exists in the repo. If not → `Refused(error_code="DESTINATION_REF_NOT_FOUND", ...)`.
3. Check whether `destination_ref` is a remote-tracking branch (`refs/remotes/...`). If so → `Refused(error_code="DESTINATION_REF_NOT_LOCAL", ...)`.
4. Look up `destination_ref` against the project's protected-branch list (existing logic in `src/specify_cli/git/commit_helpers.py`).
5. If protected → `Refused(error_code="PROTECTED_BRANCH_REFUSED", next_step=<route to coordination worktree>)`.
6. Otherwise → `Allowed()`.

The policy is **idempotent and side-effect-free**. It never modifies repo state, never writes files, never touches the lock.

## Error code stability (NFR-007)

The error_code field is stable across releases for scripted detection. Adding new codes is allowed; removing or renaming is breaking. Current codes:

| Code                              | Meaning                                                                |
| --------------------------------- | ---------------------------------------------------------------------- |
| `PROTECTED_BRANCH_REFUSED`        | destination_ref is on the protected branch list                        |
| `DESTINATION_REF_NOT_FOUND`       | destination_ref does not resolve to any ref in the repo                |
| `DESTINATION_REF_NOT_LOCAL`       | destination_ref is a remote-tracking branch                            |
| `DESTINATION_REF_INVALID_SHAPE`   | destination_ref does not match expected naming (e.g. starts with `-`)  |

## Operator-facing message format (FR-002)

The `Refused.message` field carries a human-readable description naming:
- The rejected commit's intent (from `change_set.operation`).
- The destination ref the policy rejected.
- The recovery route.

Example:
```
Refusing to record WP01 transitions: destination ref 'main' is on this
project's protected branch list. Bookkeeping commits must target the
coordination branch 'kitty/mission-foo-01ABCDEF'. Re-run the command;
the coordination worktree is auto-resolved.
```

## Integration with existing protected-branch check

The policy **wraps** but does not replace the existing `_is_protected_branch()` helper in `src/specify_cli/git/commit_helpers.py`. The wrapper exists to:
- Provide a single chokepoint for the workflow paths to call (so audits and architectural tests can target one entry point).
- Normalize the error shape into `PolicyVerdict` (the existing helper returns a bool).
- Make the input contract explicit (`GitChangeSet` with required `destination_ref`).

The protected-branch list itself (which branches count as protected) is unchanged by this mission.

## Test surface

- **Unit allowed**: destination_ref is a non-protected branch → `Allowed()`.
- **Unit protected**: destination_ref is on the protected list → `Refused(PROTECTED_BRANCH_REFUSED)`.
- **Unit not found**: destination_ref does not exist → `Refused(DESTINATION_REF_NOT_FOUND)`.
- **Unit remote-tracking**: destination_ref is `refs/remotes/origin/main` → `Refused(DESTINATION_REF_NOT_LOCAL)`.
- **Unit invalid shape**: destination_ref begins with `-` → `Refused(DESTINATION_REF_INVALID_SHAPE)`.
- **Unit side-effect-free**: calling `assert_allowed` does not modify git state, does not touch files, does not acquire locks.
- **Integration**: refusing inside `BookkeepingTransaction.acquire()` results in `BOOKKEEPING_POLICY_REFUSED` with the underlying verdict accessible.

## Composition with `safe_commit()`

`WorkflowMutationPolicy.assert_allowed()` is called twice per write:
1. By `BookkeepingTransaction.acquire()` *before* any write (pre-flight; saves the cost of writing-then-rolling-back when the destination is protected).
2. Indirectly inside `safe_commit()` via the existing protected-branch check (defense in depth, in case a caller bypasses the transaction layer).

The double-call is intentional: the pre-flight catches 99% of refusals cheaply; the helper-level check catches the residual 1% (direct `safe_commit()` callers from outside the transaction layer).

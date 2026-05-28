# Contract: `safe_commit()` signature and HEAD assertion

**Spec source**: FR-031, C-015
**Module**: `src/specify_cli/git/commit_helpers.py`

## Signature

```python
def safe_commit(
    *,
    repo_root: Path,
    worktree_root: Path,
    destination_ref: str,
    message: str,
    paths: tuple[Path, ...],
) -> CommitResult: ...
```

All parameters are **keyword-only**. mypy --strict catches missing `destination_ref` at every typed call site.

## Behavior

1. Validate inputs: `repo_root` is a git repo; `worktree_root` is a worktree of that repo; `paths` is non-empty.
2. Resolve the worktree's HEAD via `git -C <worktree_root> symbolic-ref HEAD` → `actual_head`.
3. **HEAD assertion**: if `actual_head != destination_ref`, raise `SafeCommitHeadMismatch(destination_ref, observed_head=actual_head, worktree_root=worktree_root)`. No commit attempted.
4. Run the existing protected-branch check (`_is_protected_branch(destination_ref)`). If protected and no documented exception applies, raise `ProtectedBranchRefused(destination_ref, message)`.
5. Stage `paths` via `git -C <worktree_root> add -- <paths>`.
6. Run `git -C <worktree_root> commit -m <message>`. Return `CommitResult` with the new commit SHA.

No silent fallback. If `destination_ref` is missing, mypy fails the type check. If HEAD doesn't match, the helper refuses. If the branch is protected, the helper refuses. There is no "infer destination from HEAD" path.

## Error codes (stable for scripted detection; NFR-007)

| Code                              | When raised                                                                     | Recovery suggestion in message                                       |
| --------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `SAFE_COMMIT_HEAD_MISMATCH`       | Worktree HEAD does not match `destination_ref`                                  | "Run `git -C <worktree_root> checkout <destination_ref>` first"      |
| `SAFE_COMMIT_PROTECTED_BRANCH`    | `destination_ref` is on the protected list (no exception)                       | "Use the coordination worktree at .worktrees/<slug>-<mid8>-coord/"   |
| `SAFE_COMMIT_DESTINATION_NOT_FOUND` | `destination_ref` does not exist in the repo                                  | "Did you mean `kitty/mission-<slug>-<mid8>`?"                        |
| `SAFE_COMMIT_EMPTY_CHANGESET`     | `paths` is empty                                                                | Programming error; pass at least one path                            |
| `SAFE_COMMIT_NOT_A_WORKTREE`      | `worktree_root` is not a valid worktree of `repo_root`                          | Programming error; pass the resolved worktree path                   |

Each error carries: `error_code`, `message`, `destination_ref`, `observed_head` (when relevant), `worktree_root`. JSON-serializable.

## CLI surface change

The existing `spec-kitty safe-commit <message> <paths...>` CLI command gains a required `--to-branch <ref>` parameter. Without it, the CLI exits non-zero with `SAFE_COMMIT_HEAD_MISMATCH`. (The CLI does not infer the destination — it requires the operator or wrapping script to declare it.)

For backward compatibility during PR 1's rollout window, the CLI emits a deprecation warning if `--to-branch` is missing AND a `SPEC_KITTY_INFER_DESTINATION_REF=1` env var is set; in that mode it resolves destination via the existing branch-context resolver and proceeds. This env var is removed in the next minor release after PR 1 lands. (Documented in CHANGELOG.)

## Test surface

- **Unit happy path**: worktree on `destination_ref`, non-protected → commit succeeds, returns SHA.
- **Unit HEAD mismatch**: worktree on a different branch → raises `SafeCommitHeadMismatch`.
- **Unit protected branch**: `destination_ref=main` (protected) → raises `ProtectedBranchRefused`.
- **Unit empty paths**: → raises `SAFE_COMMIT_EMPTY_CHANGESET`.
- **Type test**: a missing-arg call site fails `mypy --strict`.
- **CLI test**: `spec-kitty safe-commit` without `--to-branch` exits non-zero.
- **Migration test**: each existing call site in the codebase passes `destination_ref` after PR 1.

## Compatibility

Breaking change for any caller of `safe_commit()` that does not pass `destination_ref`. All such callers live in the spec-kitty tree (audited and migrated in PR 1). External users invoking `spec-kitty safe-commit` get a clear migration message via the CLI deprecation path described above.

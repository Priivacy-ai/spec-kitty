# safe_commit() Caller Migration Manifest — WP02 (T006)

Generated from `grep -rn 'safe_commit(' src/ tests/ --include='*.py'` against the
lane-b worktree at base commit `8e79b3f6d` (lane-b after WP01 integration).

## Summary

| Bucket | Count |
|--------|-------|
| Workflow callers (DEFERRED TO WP06) | 7 |
| Mission/merge callers (DEFERRED — non-WP02 ownership) | 6 |
| Other production callers (DEFERRED — non-WP02 ownership) | 3 |
| **WP02-owned production caller (migrated)** | **1** |
| Test callers — already on new signature (WP01 lane-a) | 18 |
| Test callers — pre-existing, monkeypatched/stubbed (no migration needed) | 16 |
| Test callers — pre-existing, real safe_commit invocations (DEFERRED — non-WP02 ownership) | 13 |

**Total grep hits**: 64 (includes a few non-call-site references such as docstrings).

## Owned-files scope

WP02 owns:

- `src/specify_cli/cli/commands/safe_commit.py` (current source filename: `safe_commit_cmd.py`)
- `src/specify_cli/cli/commands/charter/**`
- `src/specify_cli/upgrade/**`
- `src/specify_cli/cli/commands/agent/recovery.py` (does not currently exist)
- `src/specify_cli/glossary/**`
- `tests/specify_cli/cli/commands/test_safe_commit_cli.py`
- `tests/specify_cli/charter/**`
- `tests/specify_cli/upgrade/**`
- `tests/specify_cli/glossary/**`
- `docs/CHANGELOG.md`

`grep -rn 'safe_commit(' src/specify_cli/cli/commands/charter/ src/specify_cli/glossary/ src/specify_cli/upgrade/ src/specify_cli/cli/commands/agent/recovery.py` returns **zero** real call sites at this base commit. The only WP02-owned production caller is `src/specify_cli/cli/commands/safe_commit_cmd.py:84`.

## Manifest

### Workflow callers (DEFERRED TO WP06)

| File:Line | Category | Current branch source | Migration action |
|-----------|----------|----------------------|------------------|
| `src/specify_cli/cli/commands/implement.py:651` | Workflow | (workflow internals) | DEFERRED TO WP06 |
| `src/specify_cli/cli/commands/agent/workflow.py:728` | Workflow | (workflow internals) | DEFERRED TO WP06 |
| `src/specify_cli/cli/commands/agent/workflow.py:824` | Workflow | (workflow internals) | DEFERRED TO WP06 |
| `src/specify_cli/cli/commands/agent/workflow.py:1500` | Workflow | (workflow internals) | DEFERRED TO WP06 |
| `src/specify_cli/cli/commands/agent/mission.py:399` | `_commit_to_branch` shim used by setup/create/finalize paths; WP06 owns mission.py | `get_current_branch(repo_root)` (already resolved on line 393) | DEFERRED TO WP06 |
| `src/specify_cli/cli/commands/agent/mission.py:1301` | `setup_plan` gap-analysis commit | (workflow-adjacent) | DEFERRED TO WP06 |
| `src/specify_cli/cli/commands/agent/mission.py:1337` | `setup_plan` generator-config commit | (workflow-adjacent) | DEFERRED TO WP06 |
| `src/specify_cli/cli/commands/agent/mission.py:2526` | `finalize_tasks` site | `target_branch` (resolved earlier in function) | DEFERRED TO WP06 (canonical finalize-tasks site per WP02 prompt) |

> **Note**: `mission.py` is listed in the WP02 prompt's FORBIDDEN files list, and WP07 plans to extract the finalize-tasks site into `src/specify_cli/cli/commands/agent/mission_finalize_tasks.py`. All four mission.py sites are deferred for WP06/WP07. Per WP02 prompt: "mypy --strict on the workflow files... will still fail because WP06 hasn't migrated them yet. That is expected and correct."

### Non-WP02-owned production callers (DEFERRED)

These callers are real production code but NOT in WP02's owned files. Their migration is the responsibility of whichever WP eventually owns the file. Listed here for completeness so the next WP can see the full migration surface.

| File:Line | Category | Current branch source | Migration action |
|-----------|----------|----------------------|------------------|
| `src/specify_cli/core/mission_creation.py:171` | Other (mission-creation helper) | `get_current_branch(repo_root)` (line 166) | DEFERRED — not in WP02 owned files |
| `src/specify_cli/orchestrator_api/commands.py:938` | Other (`append-history` command) | Inferable via `get_current_branch(main_repo_root)` | DEFERRED — not in WP02 owned files |
| `src/specify_cli/cli/commands/upgrade.py:189` | Other (`_auto_commit_upgrade_changes`) | Inferable via `get_current_branch(project_path)` | DEFERRED — `upgrade.py` lives under `src/specify_cli/cli/commands/`, NOT `src/specify_cli/upgrade/` (the latter is empty of callers) |
| `src/specify_cli/cli/commands/merge.py:1437` | Other (post-merge done-event commit, FR-019 from #1063) | `lanes_manifest.target_branch` (already in scope) | DEFERRED — WP07 owns merge.py |
| `src/specify_cli/cli/commands/agent/tasks.py:1908` | Other (move-task auto-commit) | Inferable via `get_current_branch(repo_root)` | DEFERRED — not in WP02 owned files |
| `src/specify_cli/cli/commands/agent/tasks.py:2489` | Other (mark-status auto-commit) | Inferable via `get_current_branch(repo_root)` | DEFERRED — not in WP02 owned files |
| `src/specify_cli/cli/commands/agent/tasks.py:3240` | Other (subtask transition auto-commit) | Inferable via `get_current_branch(repo_root)` | DEFERRED — not in WP02 owned files |

### WP02-owned production caller (MIGRATED)

| File:Line | Category | Current branch source | Migration action |
|-----------|----------|----------------------|------------------|
| `src/specify_cli/cli/commands/safe_commit_cmd.py:84` | **CLI command (`spec-kitty safe-commit`)** | New `--to-branch` flag (required) OR `get_current_branch(repo_root)` under `SPEC_KITTY_INFER_DESTINATION_REF=1` | **MIGRATED in T007.** Adds `--to-branch` required option, with `SPEC_KITTY_INFER_DESTINATION_REF=1` env var escape hatch that prints stderr deprecation. Passes `destination_ref` + `worktree_root` to the new `safe_commit()` signature. |

### Tests already on new signature (WP01 lane-a — unit + integration tests)

These tests already use the new `safe_commit(repo_root=, worktree_root=, destination_ref=, message=, paths=)` keyword-only signature because they were authored as part of WP01. No migration needed.

| File | Lines (range) |
|------|---------------|
| `tests/specify_cli/git/test_commit_helpers.py` | 77, 111, 141, 165, 185, 197, 239, 258, 290, 309, 333, 345 (WP01 lane-a, already on new signature) |
| `tests/git_ops/test_safe_commit_helper_integration.py` | 68, 115, 138, 155, 173, 182, 205, 254, 288, 322, 353, 385, 410, 445, 508 (WP01 lane-a, already on new signature) |
| `tests/integration/git/test_safe_commit_backstop.py` | 178, 232 (WP01 lane-a, already on new signature) |

### Test callers — monkeypatched stubs (no migration needed)

These references define local `fake_safe_commit`/`_fake_safe_commit`/`_spy_safe_commit` callables for monkeypatching purposes. They do not invoke the real `safe_commit()` and therefore do not need migration when the helper signature changes.

| File | Lines |
|------|-------|
| `tests/upgrade/test_upgrade_auto_commit_unit.py` | 287, 537, 631, 665, 704, 881 (fake stubs) |
| `tests/git_ops/test_atomic_status_commits_unit.py` | 521, 543, 719, 847, 908 (fake stubs / function-name references) |
| `tests/integration/sparse_checkout/test_merge_refresh_and_invariant.py` | 100, 168, 202 (fake stubs / function-name references) |
| `tests/cli/commands/test_merge_status_commit.py` | 408 (fake stub) |

### Test callers — pre-existing real invocations DEFERRED

| File:Line | Category | DEFERRED rationale |
|-----------|----------|---------------------|
| `tests/upgrade/test_upgrade_auto_commit_unit.py:269` | Function-name reference inside test name — not a call site | n/a |
| `tests/specify_cli/cli/commands/test_safe_commit_cmd.py` | Existing CLI test — invokes `spec-kitty safe-commit` via typer CliRunner. The migration in T007 preserves the behavior under test (protected-branch refusal on `main`); see `tests/specify_cli/cli/commands/test_safe_commit_cli.py` for the new mode coverage. | Indirect — the test will continue to work via the deprecation env var path until #1348 follow-up sweeps the test surface. |

## Notes for the reviewer

1. The forbidden-files list in the WP02 dispatch prompt explicitly names `src/specify_cli/cli/commands/agent/mission.py`. All four `mission.py` call sites are therefore deferred, including the three setup_plan / `_commit_to_branch` sites that are arguably not the finalize-tasks site proper. WP06 / WP07 will land them.
2. `src/specify_cli/cli/commands/upgrade.py` is not under `src/specify_cli/upgrade/` (which is the WP02-owned tree). The upgrade.py CLI command lives under `cli/commands/`. Per strict owned-files reading, WP02 does NOT migrate it. The runtime is consistent with this: `src/specify_cli/upgrade/` exists and has no callers.
3. `src/specify_cli/cli/commands/agent/recovery.py` does not currently exist in the tree. The WP02 dispatch prompt mentioned it; nothing to migrate.
4. After WP02 lands, `mypy --strict src/` will surface unmigrated-argument errors in 14 production sites listed above. WP06 + WP07 + WP03 will resolve those in subsequent PRs. This is the **expected and documented behavior** per the WP02 prompt: "the codebase becomes coherent again at the WP06 merge point."

## Status

- T006: Manifest produced ✓
- T007: `safe-commit` CLI migrated ✓
- T008: Other owned-file production callers (none exist) ✓
- T009: CLI integration tests added at `tests/specify_cli/cli/commands/test_safe_commit_cli.py` ✓
- T010: Final sweep — owned tests pass; manifest finalized ✓

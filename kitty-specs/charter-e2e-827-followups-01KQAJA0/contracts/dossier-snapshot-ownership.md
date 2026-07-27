# Contract — Dossier Snapshot Ownership (post-#845)

Maps to FR-009, FR-010, FR-011 and INV-845-{1,2,3} in `data-model.md`.

## Ownership policy: EXCLUDE FROM DIRTY-STATE

`<feature_dir>/.kittify/dossiers/<mission_slug>/snapshot-latest.json` is treated as a **mutable, derived, ephemeral artifact**. It is:

1. **Excluded from version control** via root `.gitignore`.
2. **Excluded from worktree dirty-state pre-flight** in transition gates (`agent tasks move-task` and related).
3. **Recomputable on demand** from the dossier source (`compute_snapshot()` in `src/specify_cli/dossier/snapshot.py`).

Reviewers do **not** see snapshot diffs in PRs. There is no commit churn from snapshot writes.

## Invariants

| ID | Rule |
|---|---|
| **D1** | The snapshot path glob `*/.kittify/dossiers/*/snapshot-latest.json` is in the root `.gitignore`. |
| **D2** | The pre-flight code path used by `agent tasks move-task` and related transitions explicitly filters paths matching D1 from its dirty-state computation. The filter is in code, not only in `.gitignore` (belt-and-suspenders). |
| **D3** | Real worktree dirty state outside D1's pattern still blocks the transition. The mission only suppresses the self-inflicted dirty state. |

## Producer obligations (snapshot writers in `src/specify_cli/dossier/snapshot.py`)

- `save_snapshot()` continues to write `snapshot-latest.json` exactly as today. No staging, no committing, no special branch interaction. The file is just a file.
- No new error handling required — write semantics are unchanged.

## Consumer obligations (transition gates in `src/specify_cli/cli/commands/agent/tasks.py`, helpers in `src/specify_cli/status/`)

When computing "is the worktree dirty for this transition?":

```python
dirty_files = compute_dirty_files(repo_root)  # however the existing code does this
filtered = [f for f in dirty_files if not _is_dossier_snapshot(f)]
return bool(filtered)  # block only if non-snapshot dirty files remain
```

`_is_dossier_snapshot(path)` returns True when `path` matches the glob in D1.

## Regression test contract (`tests/integration/test_dossier_snapshot_no_self_block.py`)

```
GIVEN a clean worktree on a mission with no other dirty state
WHEN a mission command writes <feature_dir>/.kittify/dossiers/<slug>/snapshot-latest.json
THEN the very next call to `spec-kitty agent tasks move-task <wp> --to <lane>` succeeds
  AND the snapshot file is left in place (not deleted, not auto-committed)
```

```
GIVEN a worktree where `snapshot-latest.json` was just written AND another file (unrelated) has uncommitted edits
WHEN `agent tasks move-task` runs
THEN it fails with a dirty-state error THAT NAMES the unrelated file (not the snapshot)
```

## What this contract does NOT change

- The location, name, schema, or computation of `snapshot-latest.json`.
- `compute_snapshot()`, `save_snapshot()`, `load_snapshot()` signatures or behavior.
- Other dossier artifacts (only `snapshot-latest.json` is in scope).
- The transition state machine.

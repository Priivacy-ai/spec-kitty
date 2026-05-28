# Contract: `CoordinationWorkspace` and lane sparse-checkout policy

**Spec source**: FR-003, FR-018, FR-024, FR-025, FR-029
**Module**: `src/specify_cli/coordination/workspace.py`

## Purpose

Manage the lifecycle of the per-mission coordination worktree at `.worktrees/<slug>-<mid8>-coord/`. Register the sparse-checkout policy that lane worktrees use to exclude status files.

## Coordination worktree lifecycle

### Creation (FR-003, FR-024)

The coordination worktree MUST exist for every active mission whose topology is the new coordination-branch model (not legacy). It is created at one of two points:

1. **`spec-kitty agent mission create`** — creates the coordination branch (`kitty/mission-<slug>-<mid8>`) but does NOT necessarily create the worktree (no implementation work has started yet). The branch is parented off the canonical target branch.
2. **First `implement`/`review` invocation for the mission** — `CoordinationWorkspace.resolve()` is called by `BookkeepingTransaction.acquire()`; if the worktree does not exist, it is created via `git worktree add <path> <branch>`.

Both paths converge on the same end state: `.worktrees/<slug>-<mid8>-coord/` is a git worktree checked out to `kitty/mission-<slug>-<mid8>`.

### Idempotency (FR-018)

`CoordinationWorkspace.resolve()` is idempotent:
- Worktree already exists and points at the correct branch → return path.
- Worktree exists but points at a different branch → raise `COORDINATION_WORKTREE_BRANCH_MISMATCH` (operator must intervene; no auto-recovery).
- Branch exists but worktree does not → create worktree, return path.
- Neither branch nor worktree exists → check whether mission is in the new topology. If new topology: create branch + worktree. If legacy topology: raise `COORDINATION_WORKTREE_NOT_APPLICABLE` (caller falls back to lane worktree).

### Teardown

The coordination worktree is removed at:
- `spec-kitty mission close --discard` — `git worktree remove <path> --force`; also delete the coordination branch.
- `spec-kitty merge` after successful merge of coordination → target — `git worktree remove`; coordination branch deleted (FR-016).

Teardown is idempotent (FR-016): calling on a missing worktree is a no-op.

### Naming

- **Branch**: `kitty/mission-<mission_slug>-<mid8>` (FR-003, FR-015, C-001).
- **Worktree path**: `.worktrees/<mission_slug>-<mid8>-coord/` relative to repo root (FR-024).

`<mission_slug>` and `<mid8>` are taken verbatim from `meta.json`; both are already ASCII-sanitized per DIR-010 / DIR-011.

## Lane worktree sparse-checkout policy (FR-029)

When the lane allocator creates `.worktrees/<slug>-<mid8>-lane-<id>/`, it MUST register a sparse-checkout pattern that excludes `kitty-specs/<mission>/status.events.jsonl` and `kitty-specs/<mission>/status.json` from the lane worktree.

### Implementation steps (executed at lane worktree creation)

**Important**: In a linked worktree, `.git` is a **file** pointing to a per-worktree gitdir, not a directory. Writing literally to `.git/info/sparse-checkout` fails. Resolve the actual path via `git rev-parse --git-path info/sparse-checkout` — this returns the correct location for any worktree topology.

```bash
git worktree add .worktrees/<slug>-<mid8>-lane-<id> <coordination_branch>
cd .worktrees/<slug>-<mid8>-lane-<id>
git sparse-checkout init --no-cone
# Resolve the actual sparse-checkout file path (handles linked worktrees correctly):
SPARSE_FILE=$(git rev-parse --git-path info/sparse-checkout)
# Include everything (default), then exclude the two status files for this mission:
cat > "$SPARSE_FILE" <<EOF
/*
!kitty-specs/<mission_slug>-<mid8>/status.events.jsonl
!kitty-specs/<mission_slug>-<mid8>/status.json
EOF
git read-tree -mu HEAD
```

Python equivalent for the Python helper:

```python
gitdir_info = subprocess.check_output(
    ["git", "-C", str(lane_path), "rev-parse", "--git-path", "info/sparse-checkout"],
    text=True,
).strip()
sparse_file = Path(gitdir_info)
sparse_file.parent.mkdir(parents=True, exist_ok=True)
sparse_file.write_text("\n".join([
    "/*",
    f"!kitty-specs/{mission_slug}-{mid8}/status.events.jsonl",
    f"!kitty-specs/{mission_slug}-{mid8}/status.json",
]) + "\n")
subprocess.run(["git", "-C", str(lane_path), "read-tree", "-mu", "HEAD"], check=True)
```

The `--no-cone` mode is used because the exclusion list is path-specific (not directory-level).

Alternative: `git sparse-checkout set --no-cone <patterns>` handles file location automatically. Either approach is acceptable; the `rev-parse --git-path` form is shown above for clarity about WHY the literal `.git/info/` path is wrong.

### Verification

A `spec-kitty doctor` check (added in PR 2) inspects each lane worktree's `.git/info/sparse-checkout` file. Drift triggers a warning:

```
Lane worktree .worktrees/<slug>-<mid8>-lane-a/ has missing sparse-checkout
exclusion for kitty-specs/<slug>-<mid8>/status.events.jsonl.
Run `spec-kitty agent worktree repair --mission <slug>` to restore.
```

### Why sparse-checkout (vs. alternatives)

See [`research.md`](../research.md) → R-003. Sparse-checkout preserves backward compatibility (files stay under `kitty-specs/<mission>/`), is in-tree (no external config to distribute), and is stock git since 2.25.

## Minimum git version (RR-01)

This contract requires `git >= 2.25` (the version where `git sparse-checkout` graduated from experimental). The doctor command MUST check the git version on startup and emit a one-line error if older.

## Error codes

| Code                                       | Meaning                                                                  |
| ------------------------------------------ | ------------------------------------------------------------------------ |
| `COORDINATION_WORKTREE_BRANCH_MISMATCH`    | Worktree exists but is checked out to a different branch                 |
| `COORDINATION_WORKTREE_NOT_APPLICABLE`     | Mission is on legacy topology; coordination worktree concept does not apply |
| `COORDINATION_WORKTREE_DIRTY`              | Worktree has uncommitted changes that block teardown                     |
| `LANE_SPARSE_CHECKOUT_INIT_FAILED`         | `git sparse-checkout init` returned non-zero                             |
| `LANE_SPARSE_CHECKOUT_DRIFT`               | Doctor check found a lane worktree without the expected exclusion       |

## Test surface

- **Unit `CoordinationWorkspace.resolve()` creates worktree** when missing.
- **Unit resolve idempotent** when worktree exists at the right branch.
- **Unit branch mismatch** raises the structured error.
- **Unit teardown** removes worktree and branch.
- **Integration lane creation**: lane worktree created; `.git/info/sparse-checkout` has the expected exclusions; lane worktree's filesystem does NOT contain the status files; primary checkout still contains them.
- **Integration doctor**: drift detected when sparse-checkout file is manually edited; warning surfaces; `repair` restores.
- **Integration min git version**: on git < 2.25, the CLI exits with a clear error.

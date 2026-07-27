# Phase 1 Data Model — Execution-State Canonical Domain Surface

This mission is a structural refactor; the "data model" is the **type and ownership model** of the canonical surface, not new persisted entities.

## Execution modes (value)

`ExecutionMode` ∈ { `planning`, `direct_to_target`, `worktree` }

| Mode | Authorized write branch | Worktree | Notes |
|------|-------------------------|----------|-------|
| `planning` | coordination branch | no | planning artifacts on the coord branch |
| `direct_to_target` | declared target branch | **no** | worktree is unneeded overhead (operator ruling) |
| `worktree` | lane-worktree branch | yes | isolated lane execution |

**Invariant (C-001):** mainline (main/master) is never the resolved write branch without explicit operator authorization, in any mode.

## ExecutionContext (immutable value object) — owned by `mission_runtime/`

Relocated from `core/execution_context.py` (today `ActionContext`). Fields (Stage C shape, doc 06 §5):

| Field | Meaning |
|-------|---------|
| `mission_slug` / `mission_id` | mission identity (never `mission_number` — C-005) |
| `feature_dir` | resolved mission dir (topology-aware; not raw-constructed) |
| `read_dir` / `write_dir` | coord-aware read/write surfaces |
| `mode` | `ExecutionMode` |
| `target_branch` | mode-correct authorized write branch |
| `workspace_root` | worktree root when `mode == worktree`, else repo root |
| `wp_id` | active work package (optional) |

Construction is **only** via the canonical entry point; callers receive the object, not fragments (FR-004).

## Canonical entry point

`resolve_action_context(repo_root, mission, wp_id=None, *, mode=None) -> ExecutionContext`

- Single sanctioned resolver (FR-003, FR-005); façade delegates to today's resolver internally (Stage C).
- CWD-invariant; raises `ActionContextError` rather than silently degrading.
- Mode resolution: inferred from mission topology + invocation, or supplied; yields the mode-correct `target_branch` (FR-012).

## Ownership / relationships

```
mission_runtime/  (Execution domain)
  ExecutionContext  ── resolved by ──>  resolve_action_context  ──(reads)──>  meta.json topology
        │
        │ consumers (runtime/next, cli/commands/agent, workspace, …) depend ONLY on the public API
        ▼
specify_cli.status  (Mission Management domain)
  MissionStatus  ── owns read+write ──>  status.events.jsonl   (BookkeepingTransaction internal)
        ▲
        │ status consumers route through MissionStatus / the facade (FR-014, FR-017..019)
```

- **Execution → Status**: consumers read status via `MissionStatus`, never deep `status.*` imports (FR-014).
- **`MissionStatus`** is unchanged by this mission except for being made the consistent entry point; `BookkeepingTransaction` internals untouched (NFR-006).
- **`MissionRunSnapshot`** (runtime) carries `mission_id`/`mission_slug` through all reconstruction sites (FR-025).

## Deleted / collapsed surfaces

- 8 duplicate `_resolve_feature_dir` implementations → 1 canonical resolver (FR-010).
- ~125 raw `kitty-specs / mission_slug` path constructions → routed or deleted (FR-009, FR-011).
- ~225 deep `status.*` imports → facade / `MissionStatus` (FR-014).

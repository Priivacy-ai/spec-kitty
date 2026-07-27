# Contract: CLI status mediation

**Spec source**: FR-030
**Affected CLI surface**: `spec-kitty agent tasks status`, `spec-kitty agent context resolve`, any read-side query that consumes `status.events.jsonl` or `status.json`.

## Purpose

Lane worktrees do not contain `status.events.jsonl` or `status.json` (sparse-checkout per FR-029). Any read-side query MUST resolve the coordination worktree path and read from there, regardless of where the operator's process is currently running.

## Mediation rule

Every read-side CLI command that accesses status data:

1. Accepts an optional `--mission <handle>` flag (existing CLI plumbing).
2. Resolves the mission via the existing handle resolver: `mission_id` (ULID) → `mid8` → `mission_slug`. Ambiguous handles produce `MISSION_AMBIGUOUS_SELECTOR` (no silent fallback).
3. Resolves the **read path**: prefer the coordination worktree (`.worktrees/<slug>-<mid8>-coord/kitty-specs/<mission>/`). If the coordination worktree does not exist (legacy topology), fall back to the primary checkout's view of `kitty-specs/<mission>/`.
4. Reads `status.events.jsonl` and `status.json` from the resolved path.
5. Returns the data; the output format is unchanged from current behavior.

The CLI **never** reads from the operator's CWD, the lane worktree, or any other location.

## Affected commands

| Command                                | Read path resolution                                                                  | Behavior change                                                       |
| -------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `spec-kitty agent tasks status`        | Coordination worktree (new topology) / primary checkout (legacy)                      | New: reads from coordination worktree                                 |
| `spec-kitty agent context resolve`     | Coordination worktree                                                                 | New: returns status snapshot from coordination worktree                |
| `spec-kitty agent decision verify`     | Coordination worktree (decisions/index.json lives there too)                           | New: reads from coordination worktree                                  |
| `spec-kitty agent tasks status --json` | Same as above; output is JSON                                                          | No format change                                                       |
| `spec-kitty doctor`                    | Inspects both coordination and lane worktrees                                          | New checks: sparse-checkout drift, missing coordination worktree       |
| `spec-kitty agent mission status`      | Coordination worktree                                                                  | New: reads from coordination worktree                                  |

## Write-side commands (no change to this contract)

Write-side commands (`spec-kitty agent action implement`, `agent action review`, `agent mission finalize-tasks`) go through `BookkeepingTransaction`, which resolves the coordination worktree as the write target. Their behavior is governed by `contracts/bookkeeping_transaction.md`.

## Behavior in lane worktree

An agent process running inside `.worktrees/<slug>-<mid8>-lane-a/` invokes:
```bash
spec-kitty agent tasks status --mission <handle>
```
The CLI resolves the mission, locates the coordination worktree, reads from there, and returns the result. The agent does NOT attempt to read `kitty-specs/<mission>/status.json` directly from its own CWD (sparse-checkout would make that file missing).

## Behavior on legacy missions

Legacy missions have no coordination worktree. The CLI falls back to the primary checkout's view of `kitty-specs/<mission>/`. The mediation contract is unchanged — the read path resolution simply selects a different worktree.

## Error codes

| Code                                | Meaning                                                                |
| ----------------------------------- | ---------------------------------------------------------------------- |
| `STATUS_READ_PATH_NOT_FOUND`        | Neither coordination worktree nor primary checkout has the mission dir |
| `MISSION_AMBIGUOUS_SELECTOR`        | Existing error code from handle resolver                                |

## Performance

The CLI mediation path adds at most one `git worktree list` invocation per command (cached for the process lifetime). Target overhead: < 50ms per command.

## Out-of-scope (future tickets)

- **Read-only mirror in the lane**: caching a stale snapshot in `.spec-kitty/mission-status-snapshot.json` inside the lane for faster repeated reads. Mentioned in R-004 as an optimization for a future ticket; not required by this mission.
- **Watch / subscribe APIs**: real-time status streams via inotify / fsevents are out of scope.

## Test surface

- **Unit handle resolution**: ULID, mid8, slug all resolve to the same mission.
- **Unit ambiguous handle**: returns structured `MISSION_AMBIGUOUS_SELECTOR`.
- **Unit read-from-coordination**: lane worktree CWD; CLI returns same data as primary checkout would.
- **Unit read-from-primary-fallback** (legacy mission): coordination worktree absent; CLI reads from primary checkout view.
- **Unit missing mission**: returns `STATUS_READ_PATH_NOT_FOUND`.
- **Integration**: spawn process inside lane worktree, run `spec-kitty agent tasks status`, verify output matches a process spawned inside the coordination worktree (SC-02).

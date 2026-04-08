# Research: Planning Artifact and Query Consistency

**Mission**: 077-planning-artifact-and-query-consistency
**Date**: 2026-04-08
**Method**: Codebase exploration plus planning decisions confirmed during `/spec-kitty.plan`

## Research Summary

The existing codebase already contains the right building blocks for this mission, but they are split across incompatible call paths.

- `src/specify_cli/core/worktree.py` already treats `planning_artifact` work as repo-root work.
- `src/specify_cli/workspace_context.py` and the implement/workflow/status callers still assume every WP must resolve through `lanes.json`.
- `src/specify_cli/cli/commands/agent/mission.py` already demonstrates the correct compatibility pattern: infer missing metadata once, keep it in memory, and pass normalized objects downstream.
- `src/specify_cli/next/runtime_bridge.py` and `src/specify_cli/cli/commands/next_cmd.py` already expose query mode, but they still encode fresh-run state as `unknown` and make `--agent` mandatory for a read-only call.
- `src/specify_cli/core/worktree_topology.py` and `src/specify_cli/cli/commands/agent/tasks.py` still contain lane-only assumptions that would leave planning-artifact WPs half-supported if not included in scope.

The implementation plan therefore focuses on wiring, normalization, and contract cleanup, not on inventing a new runtime model.

---

## R1: Compatibility Seam For Missing `execution_mode`

### Decision

Normalize missing `execution_mode` once per command/session in memory, then pass only normalized metadata to downstream consumers.

### Rationale

This creates one compatibility seam instead of repeating inference in status, implement, stale detection, and query call sites.

### Validated findings

- `src/specify_cli/cli/commands/agent/mission.py:1468-1629` already keeps `_inmemory_frontmatter` and `_inmemory_bodies` so validate-only flows can rely on normalized metadata without writing disk state.
- `src/specify_cli/ownership/inference.py:62-91` exposes `infer_execution_mode(wp_content, wp_files)` as a deterministic helper.
- `src/specify_cli/status/wp_metadata.py:214-220` provides immutable update semantics through `WPMetadata.update(...)`.
- `src/specify_cli/ownership/models.py:80-93` hard-fails if `OwnershipManifest.from_frontmatter()` sees `execution_mode=None`, which is exactly why repeated ad hoc inference is unsafe.

### Alternatives considered

- Infer at every lookup site -> rejected because it duplicates logic and invites drift.
- Fail immediately when `execution_mode` is missing -> rejected because the mission spec promises zero-migration support for supported historical missions.

---

## R2: Canonical Workspace Resolution

### Decision

Make `src/specify_cli/workspace_context.py` the single authoritative runtime resolver and extend it to return both lane-backed workspaces and repo-root planning work.

### Rationale

The codebase already has one correct repo-root planning router, but it is currently dead for production flows. The fix is to make one resolver authoritative, not to invent placeholder lanes.

### Validated findings

- `src/specify_cli/core/worktree.py:90-160` implements `create_wp_workspace()` and already routes `planning_artifact` WPs to `repo_root`.
- `src/specify_cli/workspace_context.py:270-316` resolves workspaces only through context files and `lanes.json`; it raises `ValueError` when `lane_for_wp()` returns `None`.
- `src/specify_cli/cli/commands/implement.py:439-442` hard-fails if the target WP is not assigned to a lane.
- `src/specify_cli/lanes/implement_support.py:33-134` is explicitly lane-only and creates workspace context files only for lane worktrees.
- `src/specify_cli/cli/commands/agent/workflow.py`, `src/specify_cli/core/execution_context.py`, `src/specify_cli/next/prompt_builder.py`, `src/specify_cli/core/stale_detection.py`, and `src/specify_cli/core/worktree_topology.py` all call `resolve_workspace_for_wp(...)` directly.
- `src/specify_cli/core/worktree_topology.py:112-135` iterates every WP from the dependency graph, calls `lane_for_wp()`, and raises when a planning-artifact WP is outside `lanes.json`.
- `src/specify_cli/cli/commands/agent/workflow.py:737-746` currently swallows topology failures behind `except Exception: pass`, which means topology silently disappears for mixed missions today.

### Alternatives considered

- Make planning-artifact WPs fake lane members -> rejected because it encodes repo-root work as worktree work.
- Add planning-artifact special cases in every caller -> rejected because it recreates the split-brain design this mission is fixing.

---

## R3: Planning-Artifact Lifecycle Completion

### Decision

Keep the existing lifecycle statuses, but interpret them in artifact terms for planning-artifact WPs:

- `for_review` = repository-root planning artifacts are ready for review
- `approved` = review passed and downstream dependents can start
- `done` = artifacts have been accepted as complete, with no lane-merge precondition

### Rationale

This preserves the canonical status-lane model while removing the incorrect assumption that completion must always be tied to branch or worktree merge semantics.

### Validated findings

- `src/specify_cli/cli/commands/agent/tasks.py:2427-2648` already treats lifecycle lanes as mission-wide status reporting, not as execution-lane topology.
- `src/specify_cli/status/models.py` and downstream reducers already distinguish lifecycle lanes from execution lanes.
- The spec now requires planning-artifact WPs to reach completion by accepted repository-root artifacts, not by merge of a lane branch.
- `src/specify_cli/cli/commands/agent/tasks.py:751-792` and `src/specify_cli/cli/commands/agent/tasks.py:1014-1043` still gate `--to done` on branch merge ancestry, which is correct for `code_change` but wrong for planning-artifact WPs under the new lifecycle contract.

### Alternatives considered

- Skip `approved` for planning-artifact WPs -> rejected because it would create a second lifecycle model.
- Wait for mission merge to mark planning-artifact WPs done -> rejected because it would preserve the merge dependency the spec explicitly rejects.

---

## R4: Stale Detection Contract

### Decision

Expose a structured stale object everywhere this mission touches stale reporting. For planning-artifact WPs in repo root, use:

```json
{
  "status": "not_applicable",
  "reason": "planning_artifact_repo_root_shared_workspace"
}
```

### Rationale

Repo-root planning work shares one workspace. Any repo activity can make every planning-artifact WP look fresh, so commit-time freshness is intentionally not a meaningful concept there.

### Validated findings

- `src/specify_cli/core/stale_detection.py:178-318` treats a WP as stale based on commit activity in the resolved workspace path.
- `src/specify_cli/core/stale_detection.py:271-275` currently trusts whatever `resolve_workspace_for_wp(...)` returns and then assumes the path is a worktree.
- `src/specify_cli/cli/commands/agent/tasks.py:2390-2459` serializes stale data as flat booleans and minute counts, which cannot express `not_applicable` safely.
- `src/specify_cli/cli/commands/agent/tasks.py:2406-2408` currently emits `is_stale`, `minutes_since_commit`, and `worktree_exists` directly in JSON output, so the nested `stale` object needs an explicit transition strategy.

### Alternatives considered

- Omit stale fields for planning-artifact WPs -> rejected because omission is ambiguous for machine consumers.
- Report `unknown` -> rejected because `unknown` means the system tried and failed, not that stale detection is intentionally invalid here.
- Use repo-wide git heartbeat -> rejected because unrelated repo activity is not a WP-scoped freshness signal.

---

## R5: Query Mode Contract

### Decision

Make query mode agent-optional, return `mission_state: "not_started"` plus `preview_step` for fresh runs, and raise an actionable validation error when a mission has no issuable first step.

### Rationale

Read-only query mode should not require an actor identity, and fresh-run state should be modeled explicitly rather than hidden inside `unknown`.

### Validated findings

- `src/specify_cli/cli/commands/next_cmd.py:22-34` currently makes `--agent` mandatory even when `--result` is omitted.
- `src/specify_cli/next/runtime_bridge.py:556-624` already has a dedicated `query_current_state()` path, but it returns `snapshot.issued_step_id or "unknown"`.
- `src/specify_cli/next/decision.py:45-92` has no field for `preview_step`, and `Decision.agent` is currently always a required string.
- Human-readable query output in `src/specify_cli/cli/commands/next_cmd.py:192-205` prints `[QUERY - no result provided, state not advanced]` and `Mission: <type> @ <state>`, so the current CLI can already branch on `is_query`.

### Alternatives considered

- Keep `--agent` required in query mode -> rejected because it adds meaningless ceremony.
- Encode the preview inside a compound state string -> rejected because it hides lifecycle state inside a machine-unfriendly string.
- Return success with no preview when the mission has no issuable first step -> rejected because it masks a mission-definition error.

---

## R6: Machine-Facing Compatibility And Docs

### Decision

Treat the query JSON change as an intentional contract change, document it explicitly, and update active docs and command reference examples in the same mission.

### Rationale

Compatibility support for query callers that still pass `--agent` is useful, but callers that parse `mission_state: "unknown"` for fresh runs need an explicit migration note.

### Validated findings

- `docs/index.md` and `docs/reference/cli-commands.md` currently drift from the runtime behavior described in the validated issue report.
- `docs/explanation/runtime-loop.md` and `docs/reference/agent-subcommands.md` also reference `spec-kitty next --agent <agent>` as the canonical entrypoint.
- The spec now makes `not_started` + `preview_step` the canonical fresh-run query shape.

### Alternatives considered

- Treat the change as purely internal -> rejected because machine consumers may parse current JSON.
- Keep `unknown` forever as a compatibility alias -> rejected because it preserves the ambiguous state model.

---

## R7: Agent Context Update Surface

### Decision

Record agent-context mutation as skipped for this mission.

### Rationale

The current CLI no longer exposes an update-context command, and this mission introduces no new toolchain or dependency that requires agent-context file mutation.

### Validated findings

- `src/specify_cli/cli/commands/agent/context.py:117-118` explicitly states that the update-context command was removed.
- `spec-kitty agent context --help` currently exposes only `resolve`.

### Alternatives considered

- Reintroduce an update-context command as part of this mission -> rejected because it is unrelated to the runtime/workflow contract being fixed.
- Mutate agent directories directly -> rejected by repo governance and `.gitignore` policy.

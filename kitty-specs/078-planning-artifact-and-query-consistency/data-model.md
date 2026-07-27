# Data Model: Planning Artifact and Query Consistency

**Mission**: 078-planning-artifact-and-query-consistency
**Date**: 2026-04-08

## State Changes By Domain

### 1. Process-Local Execution-Mode Normalization

No new on-disk schema is required. The compatibility seam is a process-local normalization map loaded once per mission per command/session.

**Existing inputs**

- `src/specify_cli/status/wp_metadata.py` -> `WPMetadata`
- `src/specify_cli/ownership/inference.py` -> `infer_execution_mode()`

**Planned in-memory shape**

```text
NormalizedWPEntry
|- wp_id: str
|- metadata: WPMetadata              # execution_mode guaranteed populated
|- mode_source: str                  # "frontmatter" | "inferred_legacy"
|- diagnostic: str | None            # present only when inference ran
```

**Rules**

- Load every WP once at command/session entry.
- If `execution_mode` is already present, keep it and mark `mode_source = "frontmatter"`.
- If `execution_mode` is missing for a supported historical mission, infer it once from existing WP content and mark `mode_source = "inferred_legacy"`.
- Do not write inferred values back to disk in runtime/status/query flows.
- If classification is impossible, fail once with an actionable compatibility error before downstream routing begins.

This mirrors the `_inmemory_frontmatter` pattern already used in `src/specify_cli/cli/commands/agent/mission.py`.

---

### 2. Resolved Workspace Contract

`src/specify_cli/workspace_context.py` currently models only lane worktrees. This mission expands the returned contract so it can describe both lane-backed and repo-root execution.

**Current shape**

```text
ResolvedWorkspace
|- mission_slug: str
|- wp_id: str
|- workspace_name: str
|- worktree_path: Path
|- branch_name: str
|- lane_id: str
|- lane_wp_ids: list[str]
|- context: WorkspaceContext | None
```

**Planned shape**

```text
ResolvedWorkspace
|- mission_slug: str
|- wp_id: str
|- execution_mode: str               # code_change | planning_artifact
|- mode_source: str                  # frontmatter | inferred_legacy
|- resolution_kind: str              # lane_workspace | repo_root
|- workspace_name: str
|- worktree_path: Path
|- branch_name: str | None
|- lane_id: str | None
|- lane_wp_ids: list[str]
|- context: WorkspaceContext | None
```

**Resolution matrix**

| execution_mode | resolution_kind | worktree_path | branch_name | lane_id | context file |
|----------------|-----------------|---------------|-------------|---------|--------------|
| `code_change` | `lane_workspace` | `.worktrees/<mission>-<lane>` | required | required | may exist |
| `planning_artifact` | `repo_root` | `<repo_root>` | null | null | none |

**Rules**

- `code_change` continues to depend on `lanes.json` membership.
- `planning_artifact` never requires execution-lane membership.
- `WorkspaceContext` files remain lane-only; planning-artifact resolution does not create fake context files.

---

### 2b. Topology Projection For Mixed Missions

`src/specify_cli/core/worktree_topology.py` currently assumes every WP has lane and branch data. That is not true once planning-artifact WPs are first-class runtime citizens.

**Current shape**

```text
WPTopologyEntry
|- wp_id: str
|- lane_id: str
|- lane_wp_ids: list[str]
|- branch_name: str
|- base_branch: str
|- dependencies: list[str]
|- lane: str
|- worktree_exists: bool
|- commits_ahead_of_base: int
```

**Planned shape**

```text
WPTopologyEntry
|- wp_id: str
|- resolution_kind: str              # lane_workspace | repo_root
|- lane_id: str | None
|- lane_wp_ids: list[str]
|- branch_name: str | None
|- base_branch: str | None
|- dependencies: list[str]
|- lane: str
|- workspace_exists: bool
|- commits_ahead_of_base: int | None
```

**Rules**

- Mixed missions must still produce topology output instead of failing closed.
- Planning-artifact entries may not have lane ids or branch names.
- Repo-root topology entries must be rendered explicitly, not dropped silently.
- Informational topology rendering may remain non-critical, but it must not require every WP to be in `lanes.json`.

---

### 3. Planning-Artifact Lifecycle Semantics

No new lifecycle-lane values are introduced. Existing status lanes keep their names but gain explicit planning-artifact meaning.

| Lane | Code-change meaning | Planning-artifact meaning |
|------|---------------------|---------------------------|
| `planned` | work not yet started | work not yet started |
| `in_progress` | agent is working in lane workspace | agent is working on repo-root planning artifacts |
| `for_review` | branch changes ready for review | repository-root artifacts ready for review |
| `approved` | review passed; merge still pending | review passed; downstream dependents may start |
| `done` | merged or otherwise completed | artifacts accepted as complete; no merge prerequisite |

`approved` remains useful because it preserves existing dependency-unblock semantics. `done` no longer depends on lane merge for planning-artifact work.

---

### 4. Structured Stale State

`src/specify_cli/core/stale_detection.py` currently returns a boolean-oriented `StaleCheckResult`. This mission adds a structured stale-state payload that can express `not_applicable` safely.

**Planned stale object**

```json
{
  "status": "fresh | stale | not_applicable",
  "reason": "string or null",
  "minutes_since_commit": "number or null",
  "last_commit_time": "ISO-8601 string or null"
}
```

**Planned wrapper**

```text
StaleCheckResult
|- wp_id: str
|- stale: dict
|- workspace_exists: bool
|- workspace_kind: str              # lane_workspace | repo_root
|- error: str | None
```

**Planning-artifact rule**

```json
{
  "status": "not_applicable",
  "reason": "planning_artifact_repo_root_shared_workspace",
  "minutes_since_commit": null,
  "last_commit_time": null
}
```

This object becomes the canonical JSON contract for:

- `spec-kitty agent tasks status --json`
- stale-detection helpers and any later machine-facing stale surfaces

**Transition compatibility**

During the transition window, `spec-kitty agent tasks status --json` should emit both:

- canonical nested `stale` object
- deprecated flat fields: `is_stale`, `minutes_since_commit`, `worktree_exists`

Legacy field mapping:

| canonical stale status | is_stale | minutes_since_commit | worktree_exists |
|------------------------|----------|----------------------|-----------------|
| `fresh` | false | numeric | true |
| `stale` | true | numeric | true |
| `not_applicable` | false | null | false |

This keeps current machine consumers running while making the nested object the new source of truth.

---

### 5. Query Decision Shape

`src/specify_cli/next/decision.py` currently lacks a field for query preview and assumes `agent` is always present.

**Current query-relevant fields**

```text
Decision
|- kind: str
|- agent: str
|- mission_slug: str
|- mission: str
|- mission_state: str
|- is_query: bool
|- run_id: str | None
|- step_id: str | None
```

**Planned query-relevant fields**

```text
Decision
|- kind: str                        # query
|- agent: str | None               # optional in query mode
|- mission_slug: str
|- mission: str
|- mission_state: str              # not_started or issued step id
|- preview_step: str | None        # required when mission_state == not_started
|- is_query: bool                  # true
|- run_id: str | None
|- step_id: str | None
```

**Fresh-run query contract**

```json
{
  "kind": "query",
  "agent": null,
  "mission_slug": "078-planning-artifact-and-query-consistency",
  "mission": "software-dev",
  "mission_state": "not_started",
  "preview_step": "research",
  "is_query": true,
  "run_id": "<run-id>"
}
```

**Failure rule**

- If the mission runtime definition has no issuable first step, query mode must return an actionable validation error instead of a query payload.

---

### 6. Entity Relationship Summary

```text
WP frontmatter (disk)
  -> loaded once into NormalizedWPEntry map (memory)
  -> consumed by ResolvedWorkspace resolver
      -> lane_workspace result for code_change
      -> repo_root result for planning_artifact

ResolvedWorkspace
  -> consumed by implement/workflow/context/prompt-builder/status/stale detection/topology

StaleCheckResult
  -> serialized into structured stale object for tasks status JSON/human output

Decision (query)
  -> serialized by next_cmd.py
  -> now carries not_started + preview_step for fresh runs
```

---

### 7. No On-Disk Migration Requirement

This mission does not introduce a new persisted mission artifact for compatibility.

- `meta.json` remains unchanged.
- `lanes.json` remains unchanged.
- WP files are not rewritten just because runtime compatibility inference ran.
- Historical supported missions remain operable through in-memory normalization.

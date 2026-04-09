# Quickstart: Planning Artifact and Query Consistency

**Mission**: 078-planning-artifact-and-query-consistency
**Date**: 2026-04-08

## Getting Started

### Prerequisites

```bash
spec-kitty --version
pytest tests/runtime/test_workspace_context_unit.py -q
```

### Recommended Execution Order

```text
1. WP01 - Session normalization and canonical workspace resolution
2. WP04 - Query-mode contract and runtime bridge cleanup
3. WP02 - Implement, workflow, action-context, and topology integration
4. WP03 - Status, stale-state, and planning-artifact done-transition cleanup
5. WP05 - Documentation and compatibility surface updates
```

WP01 should land before any caller-specific fixes. WP04 can run in parallel with WP01 because it has no resolver dependency. WP05 should land last so docs match the final runtime contract.

---

## Per-Stream Quickstart

### WP01: Session Normalization And Canonical Workspace Resolution

**Read first**

1. `src/specify_cli/workspace_context.py:261-316`
2. `src/specify_cli/core/worktree.py:90-160`
3. `src/specify_cli/ownership/inference.py:62-91`
4. `src/specify_cli/status/wp_metadata.py:24-220`

**Change sequence**

1. Add a mission-scoped, process-local normalization cache in `src/specify_cli/workspace_context.py`.
2. Load all WPs once, infer missing `execution_mode` values, and record `mode_source` for diagnostics.
3. Expand `ResolvedWorkspace` so it can describe both lane workspaces and repo-root planning work.
4. Make `resolve_workspace_for_wp(...)` the single shared authority for both execution modes.
5. Fail once with an actionable compatibility error if a supported historical WP still cannot be classified.

### WP02: Implement, Workflow, Context, And Topology Integration

**Read first**

1. `src/specify_cli/cli/commands/implement.py:428-495`
2. `src/specify_cli/lanes/implement_support.py:33-134`
3. `src/specify_cli/cli/commands/agent/workflow.py`
4. `src/specify_cli/core/execution_context.py:186-240`
5. `src/specify_cli/core/worktree_topology.py:95-142`
6. `src/specify_cli/next/prompt_builder.py`

**Change sequence**

1. Replace lane-only validation in `implement.py` with execution-mode-aware validation.
2. Reuse the canonical resolver so planning-artifact WPs start in repo root.
3. Keep workspace-context files lane-only; planning-artifact flows should not create fake lane context files.
4. Update topology materialization so planning-artifact WPs no longer raise on missing lane membership.
5. Update workflow prompt rendering and action-context resolution to show repo-root planning work cleanly.

### WP03: Status, Stale-State, And Done-Transition Cleanup

**Read first**

1. `src/specify_cli/core/stale_detection.py:178-318`
2. `src/specify_cli/cli/commands/agent/tasks.py:751-792`
3. `src/specify_cli/cli/commands/agent/tasks.py:1014-1043`
4. `src/specify_cli/cli/commands/agent/tasks.py:2390-2459`
5. `src/specify_cli/cli/commands/agent/tasks.py:2592-2610`
6. `kitty-specs/078-planning-artifact-and-query-consistency/contracts/stale-status.schema.json`

**Change sequence**

1. Replace boolean stale reporting with a structured stale object.
2. Mark planning-artifact repo-root work as `not_applicable` with the agreed reason code.
3. Keep deprecated flat stale fields in JSON output during the transition window, derived from the nested object.
4. Bypass merge-ancestry gating for planning-artifact `--to done` transitions while keeping the existing ancestry rule for `code_change` WPs.
5. Update human-readable task status output to show `stale: n/a (repo-root planning work)` instead of stale warnings.
6. Add tests for mixed missions containing both code-change and planning-artifact WPs.

### WP04: Query-Mode Contract And Runtime Bridge Cleanup

**Read first**

1. `src/specify_cli/cli/commands/next_cmd.py:20-80`
2. `src/specify_cli/next/runtime_bridge.py:556-624`
3. `src/specify_cli/next/decision.py:34-92`
4. `kitty-specs/078-planning-artifact-and-query-consistency/contracts/next-query-response.schema.json`

**Change sequence**

1. Make `--agent` optional when `--result` is omitted.
2. Extend `Decision` with `preview_step` and a nullable `agent` field for query mode.
3. Teach `query_current_state()` to return `not_started` plus `preview_step` for fresh runs.
4. Add an explicit validation error path when the mission has no issuable first step.
5. Keep advancing mode unchanged: `--agent` and `--result` still required together.

### WP05: Documentation And Compatibility Surface Updates

**Read first**

1. `docs/index.md`
2. `docs/explanation/runtime-loop.md`
3. `docs/reference/cli-commands.md`
4. `docs/reference/agent-subcommands.md`
5. `kitty-specs/078-planning-artifact-and-query-consistency/contracts/workspace-resolution.md`

**Change sequence**

1. Update all active docs so query mode is shown as `spec-kitty next --mission-run <slug>`.
2. Document the intentional fresh-run query contract change from `unknown` to `not_started` + `preview_step`.
3. Document planning-artifact repo-root resolution and stale `not_applicable` semantics.
4. Remove contradictory examples that imply every WP must belong to an execution lane.

---

## Verification Commands

```bash
pytest tests/runtime/test_workspace_context_unit.py -v
pytest tests/agent/test_implement_command.py -v
pytest tests/next/test_next_command_integration.py -v
pytest tests/specify_cli/core/test_worktree_topology.py -v
pytest tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py -v
pytest tests/specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py -v
pytest tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py -v
mypy src/specify_cli/ --strict
```

## Agent Context Update

No agent context file update is required for this mission.

- `spec-kitty agent context --help` exposes only `resolve`.
- The historical update-context command has been removed from the current CLI.
- This mission adds no new dependencies or agent-specific runtime surface that would justify direct agent-directory edits.

# Contract: Workspace Resolution

**Mission**: 078-planning-artifact-and-query-consistency

## Purpose

Define the single runtime contract for determining where a work package runs.

This contract replaces the current split between:

- lane-only runtime lookup in `src/specify_cli/workspace_context.py`
- existing but unwired execution-mode-aware routing in `src/specify_cli/core/worktree.py`

## Resolution Flow

1. Load and normalize WP metadata once per mission per command/session.
2. Ensure every target WP has a non-null `execution_mode` before any caller asks for a workspace.
3. Route by `execution_mode`, not by lane membership alone.
4. Return one `ResolvedWorkspace` object that all callers consume.

## Resolution Matrix

| execution_mode | lane membership required | workspace path | branch name | lane id | context file |
|----------------|--------------------------|----------------|-------------|---------|--------------|
| `code_change` | yes | `.worktrees/<mission>-<lane>` | required | required | allowed |
| `planning_artifact` | no | `<repo_root>` | null | null | none |

## Compatibility Classification

When `execution_mode` is missing for a supported historical mission:

1. Infer it once from existing WP content.
2. Record `mode_source = "inferred_legacy"` for diagnostics.
3. Reuse the inferred value for the rest of the command/session.

If classification is impossible, fail once with an actionable compatibility error before any downstream command path runs.

## Caller Obligations

The following callers must treat this resolver as authoritative and must not re-discover workspace rules themselves:

- `src/specify_cli/cli/commands/implement.py`
- `src/specify_cli/cli/commands/agent/workflow.py`
- `src/specify_cli/cli/commands/agent/tasks.py`
- `src/specify_cli/core/execution_context.py`
- `src/specify_cli/core/stale_detection.py`
- `src/specify_cli/core/worktree_topology.py`
- `src/specify_cli/next/prompt_builder.py`

## Topology Obligation

Informational topology rendering must respect the canonical resolver too.

- A planning-artifact WP must not cause topology materialization to fail solely because it is outside `lanes.json`.
- Topology may represent planning-artifact entries as repo-root entries with nullable lane/branch fields.
- Topology must not silently drop all mixed-mission data because one planning-artifact WP lacks lane membership.

## Non-Goals

- No synthetic lanes for planning-artifact WPs
- No planning-artifact workspace context files
- No mandatory rewrite of historical WP frontmatter on disk

## References

- `../spec.md`
- `../plan.md`
- `../data-model.md`

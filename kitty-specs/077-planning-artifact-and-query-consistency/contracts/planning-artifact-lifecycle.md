# Contract: Planning-Artifact Lifecycle

**Mission**: 077-planning-artifact-and-query-consistency

## Purpose

Define what lifecycle status lanes mean for planning-artifact work packages that execute in repository root instead of a lane worktree.

## Status Meanings

| Lane | Meaning for planning-artifact WPs |
|------|-----------------------------------|
| `planned` | The planning artifact work has not started |
| `in_progress` | The agent is actively editing repository-root planning artifacts |
| `for_review` | The repository-root artifacts are ready for review |
| `approved` | Review passed and downstream dependents may start |
| `done` | The artifacts have been accepted as complete |

## Required Rules

1. Planning-artifact WPs use the same lifecycle status lanes as other valid WPs.
2. `approved` remains meaningful; it is not skipped or renamed.
3. `done` must not depend on lane merge or worktree merge.
4. Review success must not require synthetic branch state for planning-artifact WPs.
5. Human-readable status output must not imply that planning-artifact completion is blocked on lane merge.
6. `spec-kitty agent tasks move-task <wp-id> --to done` must bypass merge-ancestry enforcement for planning-artifact WPs while leaving the ancestry guard intact for `code_change` WPs.

## Explicit Non-Rules

- Planning-artifact WPs do not need execution-lane membership to reach `for_review`, `approved`, or `done`.
- Planning-artifact WPs do not need a workspace context file to participate in lifecycle transitions.

## References

- `../spec.md`
- `../data-model.md`

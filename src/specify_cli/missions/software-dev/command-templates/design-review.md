---
description: Review design direction before task decomposition
---
# /spec-kitty.design-review - Review Design Direction

**Version**: 3.2.0+

## Purpose

Review the planned product, interface, architecture, or workflow design before
the mission is decomposed into work packages. This step is intended for custom
software-dev workflows that insert `design-review` between `plan` and `tasks`.

## Working Directory

Run from the repository root checkout. Do not create or switch to a work-package
worktree during this step.

## User Input

```text
$ARGUMENTS
```

Consider the user input before proceeding when it is not empty.

## Inputs

Read the mission artifacts under `kitty-specs/<mission>/`:

- `spec.md`
- `plan.md`
- `research.md`, `data-model.md`, `contracts/`, and `quickstart.md` when present

## Review Focus

Check the design for:

- clear user workflow and acceptance boundaries
- consistency with the charter and mission scope
- implementation risks that should be split or sequenced before task generation
- missing constraints, edge cases, or migration/rollback considerations
- ambiguous ownership between frontend, backend, runtime, docs, and tests

## Output

Update `plan.md` or add a short design-review note under the mission directory
with any required corrections. If no corrections are needed, record that the
design is ready for task decomposition.

After the review is complete, run `spec-kitty next --agent <name>` to continue
to the next workflow action.

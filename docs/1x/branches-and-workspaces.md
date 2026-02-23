# 1.x Branch and Workspace Model

## Feature-Centric Branching

1. Each feature is tracked as a branch-scoped workspace.
2. Work packages are executed in isolated working directories.
3. Merge operations close the feature workflow by integrating approved work.

## Execution Discipline

1. Work packages should move through lane states in order.
2. Planning artifacts are the contract for implementation and review.
3. Constitution principles are applied before final acceptance.

## Typical 1.x Paths

1. Feature artifacts: `kitty-specs/<feature>/...`
2. Runtime/project state: `.kittify/...`
3. Command templates and mission defaults from packaged mission/template roots (`src/specify_cli/missions/**`, `src/specify_cli/templates/**`) and project overrides.

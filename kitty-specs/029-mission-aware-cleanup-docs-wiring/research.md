# Research Notes: Mission-Aware Cleanup & Docs Wiring

## Decisions

### Decision 1: Remove root-level script duplication
- **Decision**: Treat `src/specify_cli/scripts/` as the sole source of truth and remove root `scripts/` copies by updating tests and references to use the packaged paths.
- **Rationale**: Packaged templates already copy from `src/specify_cli/scripts/`. Root copies are only used by tests and invite drift.
- **Alternatives considered**: Symlinks (rejected per requirements), wrappers (possible interim), keeping duplication (rejected due to drift risk).

### Decision 2: Consolidate task/acceptance helpers
- **Decision**: Extract shared helpers into a non-deprecated module and update both CLI and scripts to import from it.
- **Rationale**: `acceptance.py` depends on `tasks_support.py` which is marked deprecated; duplication causes worktree behavior divergence.
- **Alternatives considered**: Keep deprecated module (blocks cleanup), copy logic (continues drift).

### Decision 3: Wire documentation mission tooling into existing commands
- **Decision**: Use mission-aware branching inside existing CLI flows.
- **Rationale**: No mission-specific command framework exists; existing flows already load mission configs.
- **Alternatives considered**: New public CLI commands (out of scope for 0.13.29).

## Open Questions Resolved

- **Where should doc tooling run?**
  - `specify`: initialize documentation state
  - `plan` and `research`: run gap analysis and update state
  - `validate` and `accept`: enforce presence/recency of gap analysis and state

## Risks

- Mission wiring must not affect software-dev flows.
- Removing root scripts requires updating all tests and any references that still use `scripts/` paths.
- Constitution exception needed for targeting `main` release before 2.x.

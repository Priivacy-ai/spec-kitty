# Constitution as Central Path Resolver — Gap Analysis

**Date**: 2026-03-30
**Origin**: WP09 (058-mission-template-repository-refactor)
**Status**: Vision captured, implementation pending

## Context

WP09 introduced `ProjectMissionPaths` and `MissionType` in
`src/specify_cli/constitution/mission_paths.py` to centralize
`.kittify/missions/` path construction.  This stops filesystem layout
details from leaking into `manifest.py`, `mission.py`, and
`cli/commands/agent/config.py`.

During implementation, the HiC identified a broader principle:

> The constitution serves as the "local doctrine override and project
> configuration" entry point.  Most CLI and runtime calls should route
> through it.

`ProjectMissionPaths` is the first step.  The gaps below capture
what remains.

## Gaps

### 1. Constitution path not routed through `ProjectMissionPaths`

Constitution files (`.kittify/constitution/constitution.md`,
`references.yaml`, `context-state.json`) are resolved ad-hoc in:

- `src/specify_cli/dashboard/constitution_path.py`
- `src/specify_cli/constitution/sync.py`
- `src/specify_cli/constitution/context.py`

**Action**: Extend `ProjectMissionPaths` (or a sibling
`ProjectConstitutionPaths`) to cover constitution path resolution.

### 2. Doctrine defaults location

`src/doctrine/constitution/defaults.yaml` should move to
`src/constitution/defaults.yaml` so the constitution package owns its
own defaults rather than reaching into the doctrine package.

**Action**: Move the file and update all importers.

### 3. Kitty-specs path not centralized

`kitty-specs/<mission-slug>/` paths are constructed inline throughout:

- `src/specify_cli/core/project_resolver.py`
- `src/specify_cli/tasks_support.py`
- Various CLI commands

**Action**: Add `kitty_specs_dir_for(mission_slug)` to the path
resolver.

### 4. Global runtime paths (`~/.kittify/`)

Global paths are resolved in:

- `src/kernel/paths.py` (via `SPEC_KITTY_HOME` env var)
- `src/specify_cli/runtime/bootstrap.py`

These could be unified under a `GlobalPaths` counterpart to
`ProjectMissionPaths`.

### 5. Remaining hardcoded `.kittify/missions/` sites

Beyond the 3 files rerouted in WP09, grep shows additional inline
`.kittify/missions/` path construction in:

- Migration scripts (`src/specify_cli/upgrade/migrations/`)
- Runtime bootstrap (`src/specify_cli/runtime/bootstrap.py`)
- Template resolver (`src/specify_cli/runtime/resolver.py`)

These should be rerouted in a follow-up pass.

### 6. Config-driven path overrides

Currently all paths are convention-based (hardcoded directory names).
A future enhancement could add a `paths:` section to
`.kittify/config.yaml` allowing projects to override default locations:

```yaml
paths:
  missions: .kittify/missions       # default
  constitution: .kittify/constitution  # default
  kitty_specs: kitty-specs           # default
```

This would make `ProjectMissionPaths` read from config rather than
hardcoding the layout.

## Design Principles (from HiC)

1. **Constitution is the configuration entry point** — project-local
   overrides and path resolution should route through it.
2. **No filesystem info leaks** — callers should not construct paths
   from string segments; they should call typed methods.
3. **`MissionType` over raw strings** — predefined constants for
   built-in missions, `with_name()` for custom types.
4. **Singleton for convenience** — `ProjectMissionPaths.get()` lazily
   discovers the repo root; `init()` for explicit setup.

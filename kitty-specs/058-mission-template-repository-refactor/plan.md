# Implementation Plan: Mission Repository Encapsulation

**Branch**: `feature/agent-profile-implementation` | **Date**: 2026-03-27 | **Spec**: `kitty-specs/058-mission-template-repository-refactor/spec.md`
**Input**: Mission specification from `kitty-specs/058-mission-template-repository-refactor/spec.md`

## Summary

Rename `MissionRepository` to `MissionTemplateRepository`, expand it to be the single authoritative API for all mission asset access, and encapsulate filesystem paths behind a content-returning public interface. Two value objects -- `TemplateResult` for markdown templates and `ConfigResult` for YAML configs -- replace raw `Path` returns. Fourteen consumer files are rerouted in two phases with before/after test validation at each step.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `ruamel.yaml` (YAML parsing, already in use), `importlib.resources` (package asset discovery, already in use), `pathlib` (filesystem paths, internal only)
**Storage**: Filesystem (doctrine package assets + project-level overrides in `.kittify/`)
**Testing**: pytest, 90%+ coverage for new code (constitution requirement)
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: Single (Spec Kitty CLI)
**Constraints**: No circular imports between `doctrine` and `specify_cli`; `ruamel.yaml` preferred over `yaml` stdlib (constitution preference)
**Scale/Scope**: 1 class rename, 2 new value objects, 14 consumer reroutes, 1 new test module

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ | PASS | No new language features required |
| pytest + 90%+ coverage | PASS | New test module targets full API coverage |
| mypy --strict | PASS | All new types are fully annotated; value objects use `__slots__` or dict backing |
| Cross-platform | PASS | Only `pathlib` and `importlib.resources` -- no platform-specific code |
| < 2s CLI operations | PASS | No performance change; content reads are single file reads |
| ruamel.yaml | PASS | YAML methods use `YAML(typ="safe")` (matches existing `action_index.py` pattern) |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/058-mission-template-repository-refactor/
  spec.md                                    # Mission specification
  plan.md                                    # This file
  research/
    consumer-analysis.md                   # Phase 0: consumer analysis
  contracts/
    mission-template-repository.md           # API contract for value objects and public methods
  checklists/
    requirements.md                          # Spec quality checklist
```

### Source Code (repository root)

```
src/doctrine/missions/
  repository.py              # RENAMED: MissionRepository -> MissionTemplateRepository
  __init__.py                # MODIFIED: export MissionTemplateRepository + MissionRepository alias
  action_index.py            # MODIFIED: use repository instead of direct path construction

src/constitution/
  context.py                 # MODIFIED: use MissionTemplateRepository for action assets
  catalog.py                 # MODIFIED: use MissionTemplateRepository.list_missions()

src/kernel/
  paths.py                   # EVALUATED: may retain get_package_asset_root() as low-level primitive

src/specify_cli/
  constitution/catalog.py    # MODIFIED: use MissionTemplateRepository.list_missions()
  dossier/manifest.py        # MODIFIED: use MissionTemplateRepository public API
  next/runtime_bridge.py     # MODIFIED: use MissionTemplateRepository
  runtime/
    resolver.py              # MODIFIED: use MissionTemplateRepository._*_path() private methods
    show_origin.py           # MODIFIED: use MissionTemplateRepository
    bootstrap.py             # EVALUATED: may retain direct asset root usage for bulk copy
    migrate.py               # EVALUATED: may retain direct path for migration classification
  template/manager.py        # EVALUATED: may need _path() for file copying

tests/doctrine/
  test_mission_template_repository.py  # NEW: comprehensive tests for renamed + expanded class
```

## Phase 0: Research

See `kitty-specs/058-mission-template-repository-refactor/research/consumer-analysis.md` for the full consumer analysis.

Key findings:
- Only 2 production files actually instantiate `MissionRepository` (`dossier/manifest.py`, `next/runtime_bridge.py`)
- 5 of 7 query methods have zero callers through the repository -- all bypassed via direct path construction
- The resolver already has `ResolutionResult(path, tier, mission)` and `ResolutionTier` enum -- `TemplateResult` wraps this and adds content
- `action_index.py` uses `ruamel.yaml` with `YAML(typ="safe")` -- this is the pattern for all YAML parsing
- `load_action_index()` in `action_index.py` is a standalone function that duplicates `MissionRepository.get_action_index_path()` + parsing

## Phase 1: Design

### Value Objects

Defined in contract: `contracts/mission-template-repository.md`

**TemplateResult**: Dict-backed value object for markdown template content.
- `content` property: raw template text (`str`)
- `origin` property: human-readable origin label (`str`, e.g., `"doctrine/software-dev/implement.md"` or `"override/software-dev/implement.md"`)
- `tier` property: `ResolutionTier` enum value (for programmatic tier checking)

**ConfigResult**: Dict-backed value object for YAML config content.
- `content` property: raw YAML text (`str`)
- `origin` property: human-readable origin label (`str`)
- `parsed` property: pre-parsed YAML data (`dict`)

Both objects are constructed internally by `MissionTemplateRepository` -- consumers never build them directly.

### Public API Surface

All methods are instance methods on `MissionTemplateRepository` (renamed from `MissionRepository`). The class is instantiated with a `missions_root: Path` and has a `default()` classmethod for the doctrine-bundled root.

**Template methods** (return `TemplateResult | None`):
- `get_command_template(mission, name)` -- doctrine-level lookup
- `get_content_template(mission, name)` -- doctrine-level lookup

**Note**: `resolve_command_template()` and `resolve_content_template()` (5-tier project-aware resolution) live on `ConstitutionTemplateResolver` in `src/constitution/`, NOT on `MissionTemplateRepository`. Doctrine has zero dependencies on `specify_cli` or `constitution` (2.x landscape invariant). The constitution module is the concretization of doctrine into local context-aware legislation — the override chain is its responsibility.

**Enumeration methods** (return `list[str]`):
- `list_command_templates(mission)` -- sorted names without .md
- `list_content_templates(mission)` -- sorted filenames
- `list_missions()` -- sorted mission names

**Config methods** (return `ConfigResult | None`):
- `get_action_index(mission, action)` -- parsed action index YAML
- `get_action_guidelines(mission, action)` -- action guidelines markdown as `TemplateResult | None`
- `get_mission_config(mission)` -- parsed mission.yaml
- `get_expected_artifacts(mission)` -- parsed expected-artifacts.yaml

**Private path methods** (return `Path | None`, for internal callers only):
- `_command_template_path(mission, name)`
- `_content_template_path(mission, name)`
- `_action_index_path(mission, action)`
- `_action_guidelines_path(mission, action)`
- `_mission_config_path(mission)`
- `_expected_artifacts_path(mission)`
- `_missions_root` property

### Backward Compatibility

- `MissionRepository` is a module-level alias for `MissionTemplateRepository` in `doctrine/missions/__init__.py`
- The alias keeps shipped migrations and any external consumers functional
- Old path-returning methods are renamed to private `_*_path()` -- the alias means `MissionRepository(root)._command_template_path()` still works if anyone needs it

### Interaction with Existing Resolver

`ConstitutionTemplateResolver` (new class in `src/constitution/template_resolver.py`) composes `MissionTemplateRepository` (for tier-5 doctrine-level lookups) with the 5-tier resolver in `specify_cli.runtime.resolver`. The resolver's `ResolutionResult` (which contains `path` and `tier`) is wrapped into a `TemplateResult` by reading the file content and mapping the tier.

The resolver module itself (`resolver.py`) is rerouted to use `MissionTemplateRepository._*_path()` for its tier-5 (PACKAGE_DEFAULT) lookups instead of calling `get_package_asset_root()` directly.

**Package boundary enforcement**: `MissionTemplateRepository` (in `doctrine`) has zero imports from `specify_cli` or `constitution`. `ConstitutionTemplateResolver` (in `constitution`) may import from `specify_cli.runtime` per the 2.x landscape dependency direction. This preserves doctrine as a standalone distributable package.

## Implementation Phases

### Phase 1: Rename + New Public API + Alias

**Goal**: `MissionTemplateRepository` exists with the full public API. `MissionRepository` alias keeps everything working. No consumer changes yet.

1. Rename class in `repository.py`: `MissionRepository` -> `MissionTemplateRepository`
2. Add `TemplateResult` and `ConfigResult` value objects to `repository.py`
3. Convert existing path-returning methods to private `_*_path()` names
4. Add new public content-returning methods that wrap the private path methods
5. Add `resolve_command_template()` and `resolve_content_template()` with lazy resolver import
6. Add `get_action_index()`, `get_action_guidelines()`, `get_mission_config()`, `get_expected_artifacts()` public methods
7. Update `__init__.py`: export `MissionTemplateRepository`, add `MissionRepository = MissionTemplateRepository` alias
8. Add `list_command_templates()`, `list_content_templates()` methods

**Test strategy**: Run `pytest tests/doctrine/missions/ tests/doctrine/test_central_templates.py -v` before and after. All existing tests must pass unchanged via the alias.

### Phase 2: Reroute 14 Consumers

**Goal**: All production code uses `MissionTemplateRepository` public API. No direct path construction outside the repository.

Consumers rerouted in dependency order:

1. `doctrine/missions/action_index.py` -- use `MissionTemplateRepository._action_index_path()` or accept `Path` parameter
2. `constitution/context.py` -- use `get_action_index()` and `get_action_guidelines()`
3. `constitution/catalog.py` -- use `list_missions()` and `get_mission_config()`
4. `specify_cli/constitution/catalog.py` -- same pattern as above
5. `specify_cli/dossier/manifest.py` -- use `get_expected_artifacts()`
6. `specify_cli/next/runtime_bridge.py` -- use `_missions_root` or `list_missions()`
7. `specify_cli/runtime/resolver.py` -- use `_*_path()` for tier-5 lookups
8. `specify_cli/runtime/show_origin.py` -- use `list_command_templates()` and `list_content_templates()`
9. `specify_cli/runtime/bootstrap.py` -- evaluate: may keep direct root access for bulk copy
10. `specify_cli/runtime/migrate.py` -- evaluate: may keep direct path for migration classification
11. `kernel/paths.py` -- evaluate: `get_package_asset_root()` is a low-level primitive used by the repository itself

**Test strategy**: For each consumer file, identify and run the tests that exercise it before making changes. After changes, run the same tests. Full suite at end.

**Shipped migrations**: NOT touched (C-001). The `MissionRepository` alias ensures they keep working.

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Circular imports (`doctrine` importing `specify_cli`) | `resolve_*` methods use lazy imports inside method body |
| Breaking shipped migrations | `MissionRepository` alias in `__init__.py` |
| Test regressions from rename | Alias makes old import path work; before/after test runs on each change |
| `ruamel.yaml` vs `yaml.safe_load` inconsistency | Standardize on `YAML(typ="safe")` from ruamel.yaml (matches existing `action_index.py`) |
| `bootstrap.py` and `migrate.py` need bulk directory access | These may retain `_missions_root` usage -- evaluate during Phase 2 |

## HiC Decisions (from /analyze review, 2026-03-27)

| ID | Finding | Decision | Rationale |
|----|---------|----------|-----------|
| F1 | Return type mismatch: spec said `str`/`dict`, plan uses `TemplateResult`/`ConfigResult` | **Update spec to match plan** | Value objects are the correct design; spec now reflects `TemplateResult`/`ConfigResult` return types |
| F4 | FR-005 missing error behavior | **Aligned with FR-004** | `resolve_content_template` now specifies `raises FileNotFoundError` (same as `resolve_command_template`) |
| F2 | NFR-002 sequencing: tests break between WP01-WP03 | **Reword NFR-002** | Accept temporary breakage as normal for incremental refactor. NFR-002 now scopes to "after WP04" not "without modification" |
| F3 | NFR-004 names stdlib `yaml.safe_load` instead of `ruamel.yaml` | **Update NFR-004** | Aligned with constitution and plan: `ruamel.yaml YAML(typ="safe")` is the correct library |
| F5 | Consumer count: spec says "14", actual reroutes differ | **Split FR-017 + add FR-019** | `kernel/paths.py` stays excluded (circular). `manifest.py`, `mission.py`, `config.py` rerouted through constitution-module indirection (`ProjectMissionPaths`) to prepare for future constitution-aware resolution. FR-017 scoped to doctrine-asset consumers (11). FR-019 added for project-local reroutes (3 files). |
| F6 | WP02/WP03 parallel vs sequential contradiction | **Keep sequential** | WP03 depends on WP02 for established patterns. Removed "can potentially run in parallel" claim from dependency summary. |
| F7 | FR-008 `list_missions()` has no explicit verification subtask | **Add to WP04/T017** | T017 now includes verifying `list_missions()` signature and return type match FR-008 |
| F8 | Constitution terminology: "Feature" in spec artifacts | **Rename to "Mission Specification" + glossary update** | "Feature Specification" → "Mission Specification" in all artifacts. "Feature Branch" is an accepted VCS concept and stays. Glossary updated with distinction (T043 in WP08). |
| AR-1 | `resolve_*` methods on `MissionTemplateRepository` violate doctrine → specify_cli dependency ban | **Move to `ConstitutionTemplateResolver` in `src/constitution/`** | Constitution is the concretization of doctrine into local context-aware legislation. The 5-tier override chain is "how project context modifies doctrine defaults" — that's constitution by definition. Doctrine depends only on kernel (the true zero-dependency root). |

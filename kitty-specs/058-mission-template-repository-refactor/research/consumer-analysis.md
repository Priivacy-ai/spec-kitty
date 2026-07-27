# Consumer Analysis: Mission Asset Path Construction

**Mission**: 058 - Mission Repository Encapsulation
**Date**: 2026-03-27
**Purpose**: Catalog all production files that construct mission asset paths directly, bypassing the `MissionRepository` API, and classify them by remediation priority.

## Current MissionRepository API

The existing `MissionRepository` class (`src/doctrine/missions/repository.py`, 143 lines) exposes 7 query methods and 1 classmethod:

| Method | Path Pattern | Returns |
|--------|-------------|---------|
| `default_missions_root()` | `importlib.resources.files("doctrine") / "missions"` | `Path` |
| `list_missions()` | `_root / * / mission.yaml` | `list[str]` |
| `get_command_template(mission, cmd)` | `_root / mission / "command-templates" / f"{cmd}.md"` | `Path \| None` |
| `get_template(mission, tpl)` | `_root / mission / "templates" / tpl` | `Path \| None` |
| `get_action_index_path(mission, action)` | `_root / mission / "actions" / action / "index.yaml"` | `Path \| None` |
| `get_action_guidelines_path(mission, action)` | `_root / mission / "actions" / action / "guidelines.md"` | `Path \| None` |
| `get_mission_config_path(mission)` | `_root / mission / "mission.yaml"` | `Path \| None` |
| `get_expected_artifacts(mission)` | `_root / mission / "expected-artifacts.yaml"` | `Path \| None` |

**Key finding**: Only 2 of 14 consumer files actually import and use this API. The other 12 bypass it entirely with direct path construction.

## File-by-File Analysis

### HIGH Priority -- Must Reroute

---

#### 1. `src/constitution/context.py`

**Imports MissionRepository**: No
**Function**: `_append_action_doctrine_lines()` (lines 220-262)

| Line | Pattern | Should Use |
|------|---------|-----------|
| 225 | `missions_root = resolve_doctrine_root() / "missions"` | `MissionTemplateRepository.default()` |
| 229 | `action_index = load_action_index(missions_root, mission, action)` | `repo.get_action_index(mission, action)` |
| 249 | `guidelines_path = missions_root / mission / "actions" / action / "guidelines.md"` | `repo.get_action_guidelines(mission, action)` |

**Notes**: Constructs `missions_root` by appending `"missions"` to `resolve_doctrine_root()`, then builds paths for action indexes and guidelines manually. Imports `load_action_index` from `doctrine.missions.action_index` -- a standalone function that duplicates repository logic.

---

#### 2. `src/constitution/catalog.py`

**Imports MissionRepository**: No
**Uses `get_package_asset_root`**: Yes (line 13)
**Function**: `_load_template_sets_with_presence()` (lines 245-270)

| Line | Pattern | Should Use |
|------|---------|-----------|
| 256 | `missions_root = doctrine_root / "missions"` | `MissionTemplateRepository.default()` |
| 259 | `missions_root = _get_package_asset_root()` | `MissionTemplateRepository.default()` |
| 261 | `missions_root = doctrine_root / "missions"` | Same as 256 |
| 267 | `mission_dir / "mission.yaml"` (iteration check) | `repo.list_missions()` + `repo.get_mission_config()` |

**Notes**: Has multiple fallback strategies for finding `missions_root`, then reimplements `list_missions()` logic by iterating directories and checking for `mission.yaml`. The function `resolve_doctrine_root()` (lines 115-145) is the doctrine-root resolver and is a separate concern.

---

#### 3. `src/specify_cli/constitution/catalog.py`

**Imports MissionRepository**: No
**Uses `get_package_asset_root`**: Yes (line 12)
**Function**: `_load_template_sets()` (lines 100-119)

| Line | Pattern | Should Use |
|------|---------|-----------|
| 107 | `missions_root = doctrine_root / "missions"` | `MissionTemplateRepository.default()` |
| 110 | `missions_root = get_package_asset_root()` | `MissionTemplateRepository.default()` |
| 112 | `missions_root = doctrine_root / "missions"` | Same as 107 |
| 116 | `mission_dir / "mission.yaml"` (iteration check) | `repo.list_missions()` |

**Notes**: Legacy copy of `constitution/catalog.py`. Identical pattern -- constructs `missions_root` manually and reimplements `list_missions()`.

---

#### 4. `src/specify_cli/runtime/show_origin.py`

**Imports MissionRepository**: No
**Uses `get_package_asset_root`**: Yes (line 17)

| Line | Function | Pattern | Should Use |
|------|----------|---------|-----------|
| 68-69 | `_discover_mission_names()` | `pkg_root / * / mission.yaml` iteration | `repo.list_missions()` |
| 85-86 | `_discover_command_names()` | `pkg_root / mission / "command-templates"` dir listing | `repo.list_command_templates(mission)` (new method) |
| 103-104 | `_discover_template_names()` | `pkg_root / mission / "templates"` dir listing | `repo.list_content_templates(mission)` (new method) |

**Notes**: Three discovery functions all construct mission paths directly. Two of them (`list_command_templates`, `list_content_templates`) need methods that don't exist yet on the repository -- these are part of the new API surface.

---

### MEDIUM Priority -- Should Reroute

---

#### 5. `src/specify_cli/runtime/resolver.py`

**Imports MissionRepository**: No
**Uses `get_package_asset_root`**: Yes (line 24)

| Line | Pattern | Should Use |
|------|---------|-----------|
| 174-175 | `pkg_missions = get_package_asset_root()` / `pkg_path = pkg_missions / mission / subdir / name` | `repo._command_template_path()` or `repo._content_template_path()` for tier 5 |
| 302-303 | `pkg_missions = get_package_asset_root()` / `pkg_path = pkg_missions / name / filename` | `repo._mission_config_path(name)` for tier 5 |

**Notes**: The 5-tier resolver. Tiers 1-4 are project/user overrides and legitimately construct their own paths. Only tier 5 (PACKAGE_DEFAULT) duplicates MissionRepository logic. These tier-5 lookups should delegate to private `_*_path()` methods.

---

#### 6. `src/specify_cli/runtime/bootstrap.py`

**Imports MissionRepository**: No
**Uses `get_package_asset_root`**: Yes (line 24)
**Function**: `populate_from_package()` (lines 67-93)

| Line | Pattern | Should Use |
|------|---------|-----------|
| 74 | `asset_root = get_package_asset_root()` | `MissionTemplateRepository.default()._missions_root` |
| 78-81 | `shutil.copytree(asset_root, target / "missions")` | Same source, bulk copy |
| 84 | `scripts_src = asset_root.parent / "scripts"` | N/A -- parent traversal for non-mission assets |
| 89 | `agents_src = asset_root.parent / "AGENTS.md"` | N/A -- non-mission asset |

**Notes**: Bulk copy operation. The source path at line 74 could use the repository's `_missions_root`, but lines 84 and 89 traverse to the parent for sibling directories (`scripts/`, `AGENTS.md`) which is a different concern. Evaluate whether `_missions_root` suffices or if a separate `doctrine_root` accessor is needed.

---

#### 7. `src/specify_cli/runtime/migrate.py`

**Imports MissionRepository**: No
**Uses `get_package_asset_root`**: Yes (line 19)
**Function**: `_find_package_counterpart()` (lines 50-66)

| Line | Pattern | Should Use |
|------|---------|-----------|
| 57 | `pkg_path = package_root / mission / str(rel)` | Generic asset comparison -- could use repository for specific asset types |
| 177 | `package_root = get_package_asset_root()` | `MissionTemplateRepository.default()._missions_root` |

**Notes**: Migration module compares project-local files against package defaults. Uses `get_package_asset_root()` to get missions root, then constructs arbitrary sub-paths for file comparison. The path construction at line 57 is generic (handles any relative path within a mission directory), so a specific repository method may not fit cleanly. The root resolution at line 177 should use the repository.

---

#### 8. `src/specify_cli/template/manager.py`

**Imports MissionRepository**: No
**Uses `importlib.resources.files` directly**: Yes

| Line | Pattern | Should Use |
|------|---------|-----------|
| 165-170 | `repo_root / "src" / "doctrine" / "missions"` copytree | Dev-mode source -- `MissionTemplateRepository.default()._missions_root` |
| 242-243 | `files("doctrine").joinpath("missions")` | `MissionTemplateRepository.default()._missions_root` |
| 247-249 | Legacy fallback paths for missions | Evaluate: may still need fallbacks |

**Notes**: Init-time template copy system. Has extensive path construction for both dev-layout and package-resource scenarios. The `get_local_repo_root()` function (lines 65-106) probes for `src/doctrine/templates/command-templates` to detect dev mode -- these are existence checks, not asset lookups.

---

### LOW Priority -- Evaluate

---

#### 9. `src/doctrine/missions/action_index.py`

**Imports MissionRepository**: No

| Line | Pattern | Should Use |
|------|---------|-----------|
| 36 | `index_path = missions_root / mission / "actions" / action / "index.yaml"` | This is the low-level implementation that `MissionRepository.get_action_index_path()` wraps |

**Notes**: The `load_action_index()` standalone function accepts `missions_root: Path` as parameter. It is called by `constitution/context.py` (line 229). After the refactor, callers should use `MissionTemplateRepository.get_action_index()` instead of calling `load_action_index()` directly. The function itself may remain as an internal implementation detail of the repository.

---

### NO CHANGE Needed

---

#### 10. `src/kernel/paths.py`

| Line | Pattern | Reason |
|------|---------|--------|
| 74 | `doctrine_missions = Path(str(importlib.resources.files("doctrine") / "missions"))` | Foundational path resolution. Cannot import from `doctrine.missions.repository` (circular dependency). This IS the canonical source that `MissionRepository.default_missions_root()` wraps. |

---

#### 11. `src/specify_cli/dossier/manifest.py`

**Already correct**: Imports `MissionRepository` (line 178), instantiates it, and calls `get_expected_artifacts()`. This is the model of correct usage. No changes needed.

---

#### 12. `src/specify_cli/next/runtime_bridge.py`

**Already correct**: Imports `MissionRepository` (line 205) and uses `default_missions_root()`. The other path constructions in this file are part of the 7-tier runtime template discovery system (a separate concern from mission asset lookup).

---

### Additional Files Discovered

These files were not in the original 14-file list but also construct mission paths:

| File | Lines | Pattern | Priority |
|------|-------|---------|----------|
| `src/constitution/compiler.py` | 601 | `doctrine_root / "missions" / mission / "mission.yaml"` | MEDIUM |
| `src/specify_cli/constitution/compiler.py` | 333 | `doctrine_root / "missions" / mission / "mission.yaml"` | MEDIUM |
| `src/specify_cli/cli/commands/agent/config.py` | 145, 365 | `.kittify / "missions" / mission / "command-templates"` | MEDIUM (project-local paths) |
| `src/specify_cli/cli/commands/agent/feature.py` | 1716 | `Path(__file__).parents[3] / "specify_cli" / "missions" / mission / "mission.yaml"` | HIGH (stale legacy path!) |
| `src/specify_cli/manifest.py` | 22, 43, 48, 72 | `kittify_dir / "missions" / mission_key`, `self.mission_dir / "command-templates"` | MEDIUM (project-local) |
| `src/specify_cli/mission.py` | 276, 457, 467, 470, 493, 500, 522, 714, 722 | Multiple `kittify_dir / "missions" / ...` patterns | MEDIUM (project-local) |
| Migration files in `src/specify_cli/upgrade/migrations/` | Many | Various mission path patterns | NONE (frozen historical) |

**Note on project-local paths**: Files like `manifest.py`, `mission.py`, and `config.py` construct paths under `.kittify/missions/` (project-local copies). These are NOT doctrine-package asset lookups -- they're accessing the user's customized copies. The 5-tier resolver handles the precedence between these locations and doctrine defaults. These files may not need `MissionTemplateRepository` at all, but should be evaluated during Phase 2 implementation.

**Note on `feature.py` line 1716**: This constructs `Path(__file__).parents[3] / "specify_cli" / "missions"` -- a stale pre-migration path that references the old `specify_cli/missions/` directory (which was migrated to `doctrine/missions/`). This is a bug and should be fixed regardless of this feature.

## Summary Statistics

| Category | Count | Files |
|----------|-------|-------|
| HIGH priority (must reroute) | 4 | context.py, catalog.py (x2), show_origin.py |
| MEDIUM priority (should reroute) | 4 | resolver.py, bootstrap.py, migrate.py, manager.py |
| LOW priority (evaluate) | 1 | action_index.py |
| No change needed | 3 | kernel/paths.py, manifest.py, runtime_bridge.py |
| Newly discovered | 6 | compiler.py (x2), config.py, feature.py, manifest.py, mission.py |
| Migration files (frozen) | ~5 | Various under upgrade/migrations/ |

**Total direct path constructions to remediate**: ~30 patterns across 14+ files (excluding migrations and project-local paths).

## Missing Repository Methods

The current `MissionRepository` lacks methods needed by consumers:

| Needed Method | Needed By | Pattern |
|---------------|-----------|---------|
| `list_command_templates(mission)` | `show_origin.py` | Dir listing of `command-templates/` |
| `list_content_templates(mission)` | `show_origin.py` | Dir listing of `templates/` |
| Content-returning variants of all path methods | All rerouted consumers | Read file + return `str` |
| `get_action_index()` (parsed YAML) | `context.py` | Read + parse YAML |
| `get_action_guidelines()` (content) | `context.py` | Read + return `str` |
| `get_mission_config()` (parsed YAML) | `catalog.py` (x2) | Read + parse YAML |

These are all specified in the plan's Phase 1 design.

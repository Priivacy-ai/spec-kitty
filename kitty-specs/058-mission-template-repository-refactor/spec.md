# Mission Specification: Mission Repository Encapsulation

**Feature Branch**: `feature/agent-profile-implementation`
**Created**: 2026-03-27
**Status**: Specifying
**Mission**: software-dev
**Target**: Spec Kitty 2.x (`2.x` line only)

## Problem Statement

Mission asset access in Spec Kitty is fragmented across 14 production files using at least 4 different patterns:

1. **MissionRepository instance methods** -- only 2 files actually call these (`dossier/manifest.py`, `next/runtime_bridge.py`), and 5 of 7 query methods have zero callers
2. **5-tier resolver** -- reimplements `get_command_template` and `get_template` logic via direct path construction in `runtime/resolver.py`
3. **Direct path construction** -- 10+ files build mission asset paths manually (`missions_root / mission / "actions" / ...`, `missions_root / mission / "command-templates" / ...`)
4. **Multiple `default_missions_root()` implementations** -- `MissionRepository.default_missions_root()`, `kernel.paths.get_package_asset_root()`, and `importlib.resources.files("doctrine") / "missions"` all do the same thing

This fragmentation leads to:
- Path knowledge leaking into every consumer
- No single authority for how mission assets are accessed
- Consumers building filesystem paths directly, making it impossible to swap the storage strategy
- The 5-tier override chain only accessible through a low-level resolver module, not through the domain API

## Goal

Rename `MissionRepository` to `MissionTemplateRepository`, expand it to be the single authoritative API for all mission asset access, and encapsulate filesystem paths behind a content-returning public interface. Consumers call public methods that return content (`str`) or structured data. Private `_path()` variants exist only for the few internal callers that genuinely need filesystem access (init template copying, packaging, bootstrap).

## User Scenarios & Testing

### User Story 1 - Read a Command Template by Content (Priority: P1)

A prompt builder or CLI command needs the text content of a mission command template (e.g., the "implement" prompt for the software-dev mission). It calls `MissionTemplateRepository.get_command_template("software-dev", "implement")` and receives the template content as a string, without knowing or caring where the file lives on disk.

**Why this priority**: This is the most common access pattern. The prompt builder, runtime bridge, and show-origin all need template content.

**Acceptance Scenarios**:

1. **Given** the software-dev mission with a bundled implement template, **When** calling `get_command_template("software-dev", "implement")`, **Then** it returns a non-empty `str` containing the template content.
2. **Given** a nonexistent mission, **When** calling `get_command_template("nonexistent", "implement")`, **Then** it returns `None`.
3. **Given** a valid mission but nonexistent template name, **When** calling `get_command_template("software-dev", "nonexistent")`, **Then** it returns `None`.
4. **Given** multiple callers reading the same template, **When** each calls `get_command_template()`, **Then** all receive identical content.

---

### User Story 2 - Read a Content Template by Content (Priority: P1)

A planning or task-generation tool needs the text content of a mission content template (e.g., `spec-template.md`, `plan-template.md`). It calls `get_content_template("software-dev", "spec-template.md")` and receives the string content.

**Acceptance Scenarios**:

1. **Given** a valid mission and template name, **When** calling `get_content_template("software-dev", "spec-template.md")`, **Then** it returns a non-empty `str`.
2. **Given** a nonexistent template, **When** calling `get_content_template("software-dev", "nonexistent.md")`, **Then** it returns `None`.

---

### User Story 3 - Resolve a Template Through the Override Chain (Priority: P1)

A runtime CLI command needs a template that respects user/project overrides. It calls `resolve_command_template("software-dev", "implement", project_dir=some_dir)` and receives the content from the highest-priority tier that has the template (OVERRIDE > LEGACY > GLOBAL_MISSION > GLOBAL > PACKAGE_DEFAULT).

**Acceptance Scenarios**:

1. **Given** a project with no overrides, **When** calling `resolve_command_template(...)`, **Then** it returns the doctrine default content (tier 5).
2. **Given** a project with an override file at `.kittify/override/software-dev/command-templates/implement.md`, **When** calling `resolve_command_template(...)`, **Then** it returns the override file's content (tier 1).
3. **Given** no `project_dir` argument, **When** calling `resolve_command_template("software-dev", "implement")`, **Then** it falls back to doctrine defaults.
4. **Given** a template not found at any tier, **When** calling `resolve_command_template(...)`, **Then** it raises `FileNotFoundError`.

---

### User Story 4 - Enumerate Available Templates (Priority: P2)

A CLI tool or validator needs to list all command or content templates for a given mission to display options or validate inputs.

**Acceptance Scenarios**:

1. **Given** the software-dev mission, **When** calling `list_command_templates("software-dev")`, **Then** it returns a sorted list including at least `["implement", "plan", "specify", "tasks"]`.
2. **Given** the software-dev mission, **When** calling `list_content_templates("software-dev")`, **Then** it returns a sorted list including at least `["plan-template.md", "spec-template.md", "task-prompt-template.md"]`.
3. **Given** a nonexistent mission, **When** calling `list_command_templates("nonexistent")`, **Then** it returns an empty list.

---

### User Story 5 - Read Action Assets (Priority: P2)

The constitution context builder needs action index data and guidelines text for a mission action. It calls `get_action_index("software-dev", "implement")` and receives parsed YAML data, or `get_action_guidelines("software-dev", "implement")` and receives markdown content as a string.

**Acceptance Scenarios**:

1. **Given** a valid mission and action with an `index.yaml`, **When** calling `get_action_index("software-dev", "implement")`, **Then** it returns a `dict` with the parsed YAML content.
2. **Given** a valid mission and action with a `guidelines.md`, **When** calling `get_action_guidelines("software-dev", "implement")`, **Then** it returns a non-empty `str`.
3. **Given** a nonexistent action, **When** calling either method, **Then** it returns `None`.

---

### User Story 6 - Read Mission Configuration (Priority: P2)

A mission loader needs the configuration for a specific mission. It calls `get_mission_config("software-dev")` and receives parsed YAML data.

**Acceptance Scenarios**:

1. **Given** the software-dev mission, **When** calling `get_mission_config("software-dev")`, **Then** it returns a `dict` with the parsed `mission.yaml` content.
2. **Given** a nonexistent mission, **When** calling `get_mission_config("nonexistent")`, **Then** it returns `None`.

---

### User Story 7 - Read Expected Artifacts Manifest (Priority: P2)

The dossier `ManifestRegistry` needs the expected-artifacts manifest for a mission type. It calls `get_expected_artifacts("software-dev")` and receives parsed YAML data.

**Acceptance Scenarios**:

1. **Given** the software-dev mission, **When** calling `get_expected_artifacts("software-dev")`, **Then** it returns a `dict` (or `list`) with the parsed manifest content.
2. **Given** a mission without an expected-artifacts file, **When** calling `get_expected_artifacts("plan")`, **Then** it returns `None`.

---

### User Story 8 - Backward Compatibility During Transition (Priority: P1)

Existing code that imports `MissionRepository` must continue to work without immediate changes. A compatibility alias ensures the old import path resolves to the renamed class.

**Acceptance Scenarios**:

1. **Given** existing code with `from doctrine.missions import MissionRepository`, **When** importing after the rename, **Then** the import succeeds (alias to `MissionTemplateRepository`).
2. **Given** existing code calling `MissionRepository(root).get_command_template(m, c)`, **When** the rename is applied, **Then** the call still returns the same `Path` as before (old path-returning methods remain accessible but private/deprecated).
3. **Given** shipped migrations referencing `MissionRepository`, **When** the rename is applied, **Then** those migrations are untouched and the alias keeps them functional.

---

### User Story 9 - Eliminate Direct Path Construction in Consumers (Priority: P1)

After the refactor, no production code outside `MissionTemplateRepository` itself constructs mission asset paths directly. The 10+ files currently building paths like `missions_root / mission / "command-templates" / name` are rerouted to use the repository API.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** searching production code for direct mission path construction, **Then** no matches are found outside the repository class, shipped migrations, and `test_package_bundling.py`.
2. **Given** `constitution/context.py` which currently builds `missions_root / mission / "actions" / action / "guidelines.md"`, **When** the refactor is applied, **Then** it calls `MissionTemplateRepository.get_action_guidelines()` instead.
3. **Given** `runtime/resolver.py` which currently builds `pkg_missions / mission / subdir / name`, **When** the refactor is applied, **Then** it uses `MissionTemplateRepository._command_template_path()` or equivalent private method.

## Functional Requirements

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| FR-001 | Rename `MissionRepository` to `MissionTemplateRepository` in `src/doctrine/missions/repository.py` | P1 | Proposed |
| FR-002 | Public `get_command_template(mission, name)` returns `TemplateResult` (content + origin + tier) or `None` | P1 | Proposed |
| FR-003 | Public `get_content_template(mission, name)` returns `TemplateResult` or `None` | P1 | Proposed |
| FR-004 | `resolve_command_template(mission, name, project_dir?)` on `ConstitutionTemplateResolver` (in `src/constitution/`) returns `TemplateResult` through 5-tier chain, raises `FileNotFoundError` if not found. Composes `MissionTemplateRepository` (tier 5) + resolver. | P1 | Proposed |
| FR-005 | `resolve_content_template(mission, name, project_dir?)` on `ConstitutionTemplateResolver` returns `TemplateResult` through 5-tier chain, raises `FileNotFoundError` if not found | P1 | Proposed |
| FR-006 | Public `list_command_templates(mission)` returns sorted `list[str]` of template names (without .md extension) | P2 | Proposed |
| FR-007 | Public `list_content_templates(mission)` returns sorted `list[str]` of template filenames | P2 | Proposed |
| FR-008 | Public `list_missions()` returns sorted `list[str]` of mission names | P2 | Proposed |
| FR-009 | Public `get_action_index(mission, action)` returns `ConfigResult` (content + origin + parsed dict) or `None` | P2 | Proposed |
| FR-010 | Public `get_action_guidelines(mission, action)` returns `TemplateResult` or `None` | P2 | Proposed |
| FR-011 | Public `get_mission_config(mission)` returns `ConfigResult` or `None` | P2 | Proposed |
| FR-012 | Public `get_expected_artifacts(mission)` returns `ConfigResult` or `None` | P2 | Proposed |
| FR-013 | Private `_command_template_path(mission, name)` returns `Path` or `None` for internal callers | P1 | Proposed |
| FR-014 | Private `_content_template_path(mission, name)` returns `Path` or `None` for internal callers | P1 | Proposed |
| FR-015 | Private `_missions_root()` returns `Path` for internal callers needing directory access | P1 | Proposed |
| FR-016 | Backward-compatible `MissionRepository` alias exported from `doctrine.missions` | P1 | Proposed |
| FR-017 | Reroute doctrine-asset consumers (11 files: context.py, both catalog.py copies, show_origin.py, resolver.py, bootstrap.py, migrate.py, manager.py, both compiler.py copies, feature.py stale path) to use `MissionTemplateRepository` public API | P1 | Proposed |
| FR-018 | `ConstitutionTemplateResolver` in `src/constitution/` composes `MissionTemplateRepository` (doctrine) with the 5-tier resolver. `MissionTemplateRepository` in `doctrine` depends only on `kernel` (the true zero-dependency root) — no imports from `specify_cli` or `constitution`. `constitution` depends only on `doctrine` and `kernel` — no imports from `specify_cli`. | P1 | Proposed |
| FR-019 | Reroute project-local mission path construction in `manifest.py`, `mission.py`, `config.py` through a constitution-module indirection (`ProjectMissionPaths`) to prepare for future constitution-aware resolution | P2 | Proposed |
| FR-020 | Add `IN_REVIEW` lane to the status model (`Lane` enum) with transitions: `for_review → in_review`, `in_review → approved`, `in_review → done`, `in_review → planned`, `in_review → in_progress`, `in_review → blocked`, `in_review → canceled` | P1 | Proposed |
| FR-021 | Record reviewer `role` (e.g. `architect`, `implementer`) in WP frontmatter when review starts | P1 | Proposed |
| FR-022 | Populate `approved_by` frontmatter field with the approver's agent-profile when a WP moves to `approved` | P1 | Proposed |
| FR-023 | `agent` metadata field stores the LLM tool identifier (e.g. `claude-opus-4-6`), semantically distinct from `agent_profile` / `role` | P1 | Proposed |
| FR-024 | Workflow review command (`spec-kitty agent workflow review`) moves WP to `in_review` lane (not `in_progress`) and populates `role`, `agent_profile`, and `agent` in frontmatter | P1 | Proposed |
| FR-025 | Dashboard renders `in_review` lane column, `role` badge on kanban cards, and `approved_by` in WP detail pane. WPs without these fields render gracefully. | P2 | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|------------|-----------|--------|
| NFR-001 | No circular imports between `doctrine` and `specify_cli` at module load time | Zero `ImportError` on `import doctrine.missions` | Proposed |
| NFR-002 | Existing test suite passes after Phase 1 complete (WP04). Temporary breakage between WP01-WP03 is expected during incremental refactor. | 0 regressions after WP04 | Proposed |
| NFR-003 | Content-returning methods must not cache file reads (templates may change during runtime via overrides) | Each call reads fresh from disk | Proposed |
| NFR-004 | YAML-returning methods must parse using `ruamel.yaml` with `YAML(typ="safe")` only (no unsafe deserialization, no stdlib `yaml.load`) | Zero use of unsafe YAML loading | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Shipped migrations must NOT be modified (frozen historical snapshots) | Active |
| C-002 | `test_package_bundling.py` may retain repo-root paths (needs them for `python -m build`) | Active |
| C-003 | The 5-tier resolver's internal logic must not change (only its callers are rerouted) | Active |
| C-004 | `CentralTemplateRepository` (non-mission-scoped templates) is out of scope | Active |
| C-005 | No constitution intermediary added to the resolver chain | Active |

## Key Entities

- **MissionTemplateRepository**: The renamed + expanded class. Single authority for all mission asset access.
- **5-tier resolver**: Internal implementation engine for project-aware resolution. Called by `resolve_*` methods via lazy import.
- **Mission asset types**: command-templates (.md), content-templates (.md), action indexes (index.yaml), action guidelines (guidelines.md), mission configs (mission.yaml), expected-artifacts manifests (expected-artifacts.yaml).

## Assumptions

1. The `MissionRepository` name is not referenced by external consumers outside this repository (it is an internal doctrine API).
2. All YAML files in mission assets are safe-loadable (no custom tags or Python objects).
3. Template content is always UTF-8 encoded text.

## Dependencies

- Depends on the completed doctrine migration (committed in PR #305 as `770bc0ed`).
- The 5-tier resolver in `src/specify_cli/runtime/resolver.py` must remain functional.

## Out of Scope

- Adding a constitution intermediary to the resolver chain
- Changing the 5-tier resolver's internal resolution logic
- Modifying shipped migrations
- Changing `CentralTemplateRepository` (non-mission-scoped templates)
- Adding caching or memoization to content reads

## Success Criteria

1. `MissionTemplateRepository` is the sole public API for mission asset access, exported from `doctrine.missions`
2. Public methods return content (`str`) or parsed data (`dict`), never filesystem `Path` objects
3. All 14 consumer files are rerouted to use the public API (no direct path construction outside the repository). Exempt: shipped migrations (C-001, frozen snapshots), `test_package_bundling.py` (C-002, needs repo-root paths for `python -m build`), and `kernel/paths.py` (low-level primitive used by the repository itself).
4. `MissionRepository` alias exists for backward compatibility
5. Full test suite passes with zero regressions
6. New test module covers all public API methods with at least doctrine-level and project-aware scenarios

# Work Packages: Agent Profile Domain Model

**Inputs**: Design documents from `kitty-specs/047-agent-profile-domain-model/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Tests**: Test-first development per constitution. ATDD + TDD for all production code.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Package Scaffolding and Import Boundary (Priority: P0)

**Goal**: Create the `src/doctrine/` package skeleton with `__init__.py`, `py.typed`, empty subpackages, and a CI-ready import boundary test. Update `pyproject.toml` to include the new package.
**Independent Test**: `import doctrine` succeeds. The boundary test passes (no `specify_cli` imports in `src/doctrine/`). `pip install -e .` includes both packages.
**Prompt**: `tasks/WP01-package-scaffolding.md`

### Included Subtasks

- [ ] T001 Create `src/doctrine/` package directory with `__init__.py` and `py.typed`
- [ ] T002 Create empty subpackage directories: `model/`, `repository/`, `schema/`, `agents/`
- [ ] T003 Update `pyproject.toml` to include `src/doctrine` in wheel packages
- [ ] T004 Create import boundary test `tests/test_doctrine_import_boundary.py`
- [ ] T005 Create `tests/doctrine/conftest.py` with shared fixtures

### Implementation Notes

- The `__init__.py` files should export nothing yet — just make the packages importable.
- `py.typed` is an empty marker file for PEP 561 typed package support.
- The boundary test walks all `.py` files in `src/doctrine/` and asserts none import from `specify_cli`.
- `pyproject.toml` change: add `"src/doctrine"` to `[tool.hatch.build.targets.wheel] packages`.

### Parallel Opportunities

- T004 and T005 (tests) can be written in parallel with T001-T003 (package structure).

### Dependencies

- None (starting package).

### Risks & Mitigations

- Package resolution: Ensure `hatchling` correctly discovers both packages. Verify with `pip install -e .` and `python -c "import doctrine"`.

---

## Work Package WP02: AgentProfile Domain Model (Priority: P0) 🎯 MVP

**Goal**: Implement the `AgentProfile` frozen dataclass entity and all supporting value objects (`Specialization`, `CollaborationContract`, `ContextSources`, `ModeDefault`, `DirectiveRef`, `SpecializationContext`) in `src/doctrine/model/profile.py`. Implement `Role` enum and `RoleCapabilities` in `src/doctrine/model/capabilities.py`.
**Independent Test**: Create an `AgentProfile` programmatically, serialize to dict, deserialize back, verify round-trip fidelity. Validate required field enforcement.
**Prompt**: `tasks/WP02-domain-model.md`

### Included Subtasks

- [ ] T006 [P] Implement `Role` StrEnum and `RoleCapabilities` in `src/doctrine/model/capabilities.py`
- [ ] T007 Implement value objects in `src/doctrine/model/profile.py`: `Specialization`, `CollaborationContract`, `ContextSources`, `ModeDefault`, `DirectiveRef`, `SpecializationContext`
- [ ] T008 Implement `AgentProfile` frozen dataclass with all 6 sections in `src/doctrine/model/profile.py`
- [ ] T009 Implement `to_dict()` and `from_dict()` on all dataclasses
- [ ] T010 Implement `validate()` method on `AgentProfile` (required fields, range checks)
- [ ] T011 Write unit tests for all value objects and `AgentProfile` in `tests/doctrine/model/test_profile.py`
- [ ] T012 [P] Write unit tests for `RoleCapabilities` in `tests/doctrine/model/test_capabilities.py`

### Implementation Notes

- Follow the frozen dataclass + manual `to_dict()`/`from_dict()` pattern from `src/specify_cli/status/models.py`.
- `Role` uses `StrEnum`. Custom roles accepted as plain strings via `Role | str` typing.
- `validate()` returns a `list[str]` of error messages (empty = valid).
- Required fields: `profile_id`, `name`, `purpose` (str, non-empty), `specialization.primary_focus`.
- `routing_priority` range: 0-100, default 50. `max_concurrent_tasks` range: >0, default 5.

### Parallel Opportunities

- T006 (capabilities.py) and T007-T010 (profile.py) work on different files and can proceed in parallel.
- T011 and T012 (tests) are on different files.

### Dependencies

- Depends on WP01 (package exists and is importable).

### Risks & Mitigations

- Complex nested dataclass serialization: Test round-trip thoroughly with all field combinations.
- `StrEnum` + custom string union: Ensure `from_dict` correctly handles both known roles and arbitrary strings.

---

## Work Package WP03: Specialization Hierarchy and Context Matching (Priority: P0) 🎯 MVP

**Goal**: Implement `SpecializationHierarchy`, `HierarchyNode`, and `TaskContext` in `src/doctrine/model/hierarchy.py` with tree building, cycle detection, weighted context matching (DDR-011 algorithm), workload penalties, and complexity adjustments.
**Independent Test**: Build a 3-level hierarchy (root → generalist → specialist). Query with a Python/FastAPI context. Verify specialist wins. Overload specialist. Verify fallback to generalist.
**Prompt**: `tasks/WP03-hierarchy-and-matching.md`

### Included Subtasks

- [ ] T013 Implement `TaskContext` frozen dataclass (input to matching)
- [ ] T014 Implement `HierarchyNode` frozen dataclass (profile + parent + children + depth)
- [ ] T015 Implement `SpecializationHierarchy.build()` class method (tree construction from profile list)
- [ ] T016 Implement cycle detection and validation in hierarchy builder
- [ ] T017 Implement `find_best_match(task_context)` with DDR-011 weighted scoring algorithm
- [ ] T018 Implement workload penalty and complexity adjustment functions
- [ ] T019 Implement `as_tree()` for Rich Tree rendering
- [ ] T020 Write comprehensive tests in `tests/doctrine/model/test_hierarchy.py`

### Implementation Notes

- Weighted scoring: language 40%, framework 20%, file_patterns 20%, keywords 10%, exact_id 10%.
- Workload penalties: 0-2 tasks=1.0, 3-4=0.85, 5+=0.70.
- Complexity adjustments: low→specialist+10%, medium→neutral, high→parent+10%/specialist-10%.
- Cycle detection: Track visited nodes during tree construction. If a node is visited twice, raise validation error.
- `as_tree()` returns a nested dict suitable for `rich.tree.Tree` rendering.
- Handle edge cases: missing parent (treat as root with warning), duplicate profile_id (last wins with warning).

### Parallel Opportunities

- T013-T014 (dataclasses) can be written before T015-T018 (algorithms).

### Dependencies

- Depends on WP02 (needs `AgentProfile`, `SpecializationContext`, `Role`).

### Risks & Mitigations

- Scoring algorithm correctness: Use the DDR-011 reference test cases (20 scenarios from SC-002).
- Performance with large hierarchies: 50 profiles is the target; keep O(n*m) matching where n=profiles, m=context fields.

---

## Work Package WP04: AgentProfileRepository with Two-Source Loading (Priority: P1)

**Goal**: Implement `AgentProfileRepository` in `src/doctrine/repository/profile_repository.py` with shipped profile loading (via `importlib.resources`), project-level profile loading, field-level merge semantics, and all query methods.
**Independent Test**: Create shipped + custom profiles in tmp directories. Load via repository. Verify merge semantics, queries by role, queries by specialization context.
**Prompt**: `tasks/WP04-repository.md`

### Included Subtasks

- [ ] T021 Implement YAML loading helpers using `ruamel.yaml` in `src/doctrine/repository/profile_repository.py`
- [ ] T022 Implement shipped profile loading via `importlib.resources`
- [ ] T023 Implement project-level profile loading from filesystem path
- [ ] T024 Implement field-level merge semantics (project overrides shipped, per-field)
- [ ] T025 Implement query methods: `list_all()`, `get()`, `find_by_role()`, `find_by_specialization()`, `get_hierarchy()`
- [ ] T026 Implement `save()` and `delete()` for project-level profile management
- [ ] T027 Write comprehensive tests in `tests/doctrine/repository/test_profile_repository.py`

### Implementation Notes

- Use `importlib.resources.files("doctrine") / "agents"` for shipped profiles.
- `ruamel.yaml` for YAML I/O (matches codebase convention). `yaml.preserve_quotes = True`.
- Invalid YAML → log warning, skip profile (FR-1.6).
- Deterministic loading: sort files alphabetically, apply overrides in order (FR-013).
- Field-level merge: For nested value objects, recurse into fields. Lists are replaced wholesale, not merged.
- The `save()` method writes to `project_dir` only. `delete()` removes from `project_dir` only (cannot delete shipped).

### Parallel Opportunities

- T021-T024 (loading) must be sequential. T025-T026 (queries/mutations) can follow once loading works.

### Dependencies

- Depends on WP02 (needs AgentProfile and value objects for parsing).

### Risks & Mitigations

- `importlib.resources` path handling: Differs between editable install and wheel. Test both modes.
- Merge semantics edge cases: Empty list in project profile — should it override shipped list or keep shipped? Decision: empty list = explicit override (project chose to clear it). Only missing/None fields retain shipped values.

---

## Work Package WP05: JSON Schema and Validation (Priority: P1)

**Goal**: Create the JSON Schema file for `.agent.yaml` validation and implement schema validation helpers in `src/doctrine/_validation.py`.
**Independent Test**: Validate a correct profile YAML against the schema (passes). Validate a profile missing required fields (fails with meaningful error). Validate a profile with out-of-range routing_priority (fails).
**Prompt**: `tasks/WP05-schema-validation.md`

### Included Subtasks

- [ ] T028 Author `src/doctrine/schema/agent_profile.schema.json` covering all entity fields
- [ ] T029 Implement `validate_profile_yaml(data: dict) → list[str]` in `src/doctrine/_validation.py`
- [ ] T030 Integrate schema validation into repository loader (optional validation on load)
- [ ] T031 Write tests in `tests/doctrine/test_schema_validation.py`

### Implementation Notes

- JSON Schema uses `jsonschema` library (already a dependency).
- Schema loaded via `importlib.resources.files("doctrine") / "schema" / "agent_profile.schema.json"`.
- `validate_profile_yaml()` returns a list of validation error messages (empty = valid).
- Schema should validate: required properties, type constraints, enum values for `role`, range for `routing_priority` (0-100), positive `max_concurrent_tasks`, `schema_version` pattern.
- Repository integration: Add an optional `validate=True` parameter to loading. Default `True` for project profiles, `False` for shipped (trusted).

### Parallel Opportunities

- T028 (schema authoring) and T029 (validation code) can proceed in parallel.

### Dependencies

- Depends on WP02 (schema must match AgentProfile dataclass fields exactly).

### Risks & Mitigations

- Schema drift from dataclass: Keep schema and dataclass in sync. The test suite validates that all shipped profiles pass the schema.

---

## Work Package WP06: Shipped Reference Profile Catalog (Priority: P1)

**Goal**: Create the reference profile YAML files in `src/doctrine/agents/` for the 6 core roles (architect, implementer, reviewer, planner, researcher, curator), adapted from the doctrine reference repository.
**Independent Test**: Load all shipped profiles via repository. Verify each passes schema validation. Build hierarchy — verify valid tree with no orphans or cycles.
**Prompt**: `tasks/WP06-reference-profiles.md`

### Included Subtasks

- [ ] T032 [P] Create `architect.agent.yaml` adapted from `doctrine_ref/agents/architect.agent.md`
- [ ] T033 [P] Create `implementer.agent.yaml` (generalist implementer role)
- [ ] T034 [P] Create `reviewer.agent.yaml` adapted from doctrine reference
- [ ] T035 [P] Create `planner.agent.yaml` adapted from doctrine reference
- [ ] T036 [P] Create `researcher.agent.yaml` adapted from doctrine reference
- [ ] T037 [P] Create `curator.agent.yaml` adapted from doctrine reference
- [ ] T038 Write integration test: load all profiles, validate schema, build hierarchy

### Implementation Notes

- Each profile is a full `.agent.yaml` with all 6 sections populated (see data-model.md for format).
- Adapt Markdown sections to YAML keys: frontmatter → top-level fields, sections → nested objects.
- Core 6 are root profiles (no `specializes_from`). They form the foundation that users extend with specialists.
- Directive references adapted to code/name/rationale tuples (see architect example in data-model.md).
- All profiles get `schema_version: "1.0"`, `routing_priority: 50`, reasonable `max_concurrent_tasks` defaults.
- Canonical verbs per role (from Directive 009): architect=audit/synthesize/plan, implementer=generate/refine, reviewer=audit/refine, planner=plan/synthesize, researcher=audit/synthesize, curator=audit/translate.

### Parallel Opportunities

- All 6 profiles (T032-T037) can be written in parallel — they're independent files.

### Dependencies

- Depends on WP04 (repository must be working to load/validate profiles) and WP05 (schema validation).

### Risks & Mitigations

- Content quality: Profiles are adapted from proven doctrine reference, not invented. Review against original `.agent.md` files.
- Hierarchy coherence: Integration test (T038) validates the full profile set.

---

## Work Package WP07: ToolConfig Rename and Backward Compatibility (Priority: P1)

**Goal**: Rename `AgentConfig` to `ToolConfig` using alias-first strategy. Create `tool_config.py`, replace `agent_config.py` with deprecation alias, update all 7 importing files, update `config.yaml` reader to support `tools:` key with `agents:` fallback.
**Independent Test**: Load project with `agents:` key in `config.yaml` — works with deprecation warning. Load project with `tools:` key — works cleanly. Import from `tool_config` — works. Import from `agent_config` — works with deprecation warning.
**Prompt**: `tasks/WP07-toolconfig-rename.md`

### Included Subtasks

- [ ] T039 Create `src/specify_cli/orchestrator/tool_config.py` with renamed classes and functions
- [ ] T040 Replace `agent_config.py` with deprecation alias module
- [ ] T041 Update `config.yaml` reader to check `tools:` first, fall back to `agents:`
- [ ] T042 Update import in `src/specify_cli/agent_utils/directories.py`
- [ ] T043 Update imports in `src/specify_cli/orchestrator/scheduler.py` (2 sites)
- [ ] T044 [P] Update import in `src/specify_cli/upgrade/migrations/m_0_14_0_centralized_feature_detection.py`
- [ ] T045 [P] Update imports in `src/specify_cli/cli/commands/init.py` and `agent/config.py`
- [ ] T046 [P] Update re-exports in `src/specify_cli/orchestrator/__init__.py` and `config.py` and `monitor.py`
- [ ] T047 Write tests in `tests/specify_cli/orchestrator/test_tool_config.py`

### Implementation Notes

- Step 1: Copy `agent_config.py` → `tool_config.py`, rename all classes/functions inside.
- Step 2: Replace `agent_config.py` content with deprecation alias imports.
- Step 3: Update each importing file one by one, running tests after each change.
- Step 4: Add dual-key logic to `load_tool_config()`: read `tools:` first, fall back to `agents:` with `logger.warning("Deprecation: ...")`.
- Keep existing test files passing throughout — the alias ensures backward compat.

### Parallel Opportunities

- T044, T045, T046 (import updates in different files) can proceed in parallel after T039-T041 are done.

### Dependencies

- Depends on WP01 only (no dependency on doctrine model — this is a specify_cli-only change).

### Risks & Mitigations

- Missed import: Run `grep -r "agent_config" src/` after all changes to verify no leftover direct imports.
- Test breakage: Run full test suite after each file change. The alias module prevents breakage during transition.

---

## Work Package WP08: CLI Profile Commands (Priority: P2)

**Goal**: Implement `spec-kitty agent profile` subcommand group with `list`, `show`, `create`, `edit`, and `hierarchy` subcommands in `src/specify_cli/cli/commands/agent/profile.py`. Register in `agent/__init__.py`.
**Independent Test**: Run `spec-kitty agent profile list` — shows shipped profiles in Rich table. Run `spec-kitty agent profile show architect` — displays full profile. Run `spec-kitty agent profile hierarchy` — shows tree visualization.
**Prompt**: `tasks/WP08-cli-profile-commands.md`

### Included Subtasks

- [ ] T048 Create `src/specify_cli/cli/commands/agent/profile.py` with typer app
- [ ] T049 Implement `list` subcommand with Rich table output
- [ ] T050 Implement `show <profile_id>` subcommand with formatted profile display
- [ ] T051 Implement `create --from-template <profile_id>` subcommand
- [ ] T052 Implement `edit <profile_id>` subcommand (open YAML file or interactive fields)
- [ ] T053 Implement `hierarchy` subcommand with Rich Tree visualization
- [ ] T054 Register profile subcommand in `src/specify_cli/cli/commands/agent/__init__.py`
- [ ] T055 Write CLI integration tests in `tests/specify_cli/cli/commands/agent/test_profile_cli.py`

### Implementation Notes

- Follow existing CLI patterns: `app = typer.Typer(name="profile", ...)`, `@app.command()` decorators.
- `list` table columns: ID, Name, Role, Parent, Priority, Source (shipped/custom/override).
- `show` uses Rich Panel/Markdown for formatted display of all 6 sections.
- `create --from-template` reads the specified shipped profile and writes a copy to `.kittify/constitution/agents/`.
- `create --interactive` prompts for: profile_id, name, role, purpose, primary_focus (minimum viable profile).
- `edit` opens the file path in `$EDITOR` or prints the path if no editor configured.
- `hierarchy` uses `rich.tree.Tree` for visualization (profile_id [role] priority=N).
- The profile commands import from `doctrine.repository` (the specify_cli → doctrine direction is allowed).

### Parallel Opportunities

- T049-T053 (individual subcommands) can be implemented in parallel once T048 (skeleton) exists.

### Dependencies

- Depends on WP04 (needs AgentProfileRepository for loading/querying profiles).

### Risks & Mitigations

- Rich formatting: Test with `from rich.console import Console; console = Console(record=True)` for snapshot testing.
- Interactive mode: Use `readchar` or `typer.prompt()` for field-by-field input (both are dependencies).

---

## Dependency & Execution Summary

```
Phase 0 (Foundation):
  WP01 (scaffolding) ─── no dependencies

Phase 1 (Domain Model — parallelizable after WP01):
  WP02 (domain model) ─── depends on WP01
  WP07 (ToolConfig)   ─── depends on WP01 (independent of WP02)

Phase 2 (Services — parallelizable after WP02):
  WP03 (hierarchy)     ─── depends on WP02
  WP04 (repository)    ─── depends on WP02
  WP05 (schema)        ─── depends on WP02

Phase 3 (Integration — after Phase 2):
  WP06 (ref profiles)  ─── depends on WP04, WP05
  WP08 (CLI commands)  ─── depends on WP04
```

**Parallelization highlights**:

- WP02 + WP07 can run in parallel after WP01 (different packages)
- WP03 + WP04 + WP05 can run in parallel after WP02 (different modules)
- WP06 + WP08 can run in parallel after WP04 (different packages)

**MVP Scope**: WP01 + WP02 + WP03 (package + domain model + hierarchy). This provides the core entity and matching algorithm consumable by features 044 and 046.

**Critical path**: WP01 → WP02 → WP04 → WP06 (longest dependency chain).

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create `src/doctrine/` package with `__init__.py` and `py.typed` | WP01 | P0 | No |
| T002 | Create empty subpackage directories | WP01 | P0 | No |
| T003 | Update `pyproject.toml` packages list | WP01 | P0 | No |
| T004 | Create import boundary test | WP01 | P0 | Yes |
| T005 | Create test conftest.py with fixtures | WP01 | P0 | Yes |
| T006 | Implement `Role` StrEnum and `RoleCapabilities` | WP02 | P0 | Yes |
| T007 | Implement value objects (Specialization, CollaborationContract, etc.) | WP02 | P0 | No |
| T008 | Implement `AgentProfile` frozen dataclass | WP02 | P0 | No |
| T009 | Implement `to_dict()` and `from_dict()` on all dataclasses | WP02 | P0 | No |
| T010 | Implement `validate()` method | WP02 | P0 | No |
| T011 | Write profile model unit tests | WP02 | P0 | No |
| T012 | Write capabilities unit tests | WP02 | P0 | Yes |
| T013 | Implement `TaskContext` dataclass | WP03 | P0 | No |
| T014 | Implement `HierarchyNode` dataclass | WP03 | P0 | No |
| T015 | Implement `SpecializationHierarchy.build()` | WP03 | P0 | No |
| T016 | Implement cycle detection and validation | WP03 | P0 | No |
| T017 | Implement `find_best_match()` weighted scoring | WP03 | P0 | No |
| T018 | Implement workload penalty and complexity adjustment | WP03 | P0 | No |
| T019 | Implement `as_tree()` for Rich rendering | WP03 | P0 | No |
| T020 | Write hierarchy tests | WP03 | P0 | No |
| T021 | Implement YAML loading helpers | WP04 | P1 | No |
| T022 | Implement shipped profile loading via `importlib.resources` | WP04 | P1 | No |
| T023 | Implement project-level profile loading | WP04 | P1 | No |
| T024 | Implement field-level merge semantics | WP04 | P1 | No |
| T025 | Implement query methods | WP04 | P1 | No |
| T026 | Implement `save()` and `delete()` | WP04 | P1 | No |
| T027 | Write repository tests | WP04 | P1 | No |
| T028 | Author JSON Schema file | WP05 | P1 | Yes |
| T029 | Implement `validate_profile_yaml()` | WP05 | P1 | Yes |
| T030 | Integrate schema validation into repository | WP05 | P1 | No |
| T031 | Write schema validation tests | WP05 | P1 | No |
| T032 | Create `architect.agent.yaml` | WP06 | P1 | Yes |
| T033 | Create `implementer.agent.yaml` | WP06 | P1 | Yes |
| T034 | Create `reviewer.agent.yaml` | WP06 | P1 | Yes |
| T035 | Create `planner.agent.yaml` | WP06 | P1 | Yes |
| T036 | Create `researcher.agent.yaml` | WP06 | P1 | Yes |
| T037 | Create `curator.agent.yaml` | WP06 | P1 | Yes |
| T038 | Write profile catalog integration test | WP06 | P1 | No |
| T039 | Create `tool_config.py` with renamed classes | WP07 | P1 | No |
| T040 | Replace `agent_config.py` with alias module | WP07 | P1 | No |
| T041 | Update config.yaml reader for `tools:` key | WP07 | P1 | No |
| T042 | Update import in directories.py | WP07 | P1 | No |
| T043 | Update imports in scheduler.py | WP07 | P1 | No |
| T044 | Update import in migration file | WP07 | P1 | Yes |
| T045 | Update imports in init.py and agent/config.py | WP07 | P1 | Yes |
| T046 | Update re-exports in orchestrator **init**.py, config.py, monitor.py | WP07 | P1 | Yes |
| T047 | Write ToolConfig tests | WP07 | P1 | No |
| T048 | Create profile.py CLI skeleton with typer app | WP08 | P2 | No |
| T049 | Implement `list` subcommand | WP08 | P2 | Yes |
| T050 | Implement `show` subcommand | WP08 | P2 | Yes |
| T051 | Implement `create` subcommand | WP08 | P2 | Yes |
| T052 | Implement `edit` subcommand | WP08 | P2 | Yes |
| T053 | Implement `hierarchy` subcommand | WP08 | P2 | Yes |
| T054 | Register profile subcommand in agent/**init**.py | WP08 | P2 | No |
| T055 | Write CLI profile integration tests | WP08 | P2 | No |

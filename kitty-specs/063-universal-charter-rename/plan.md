# Implementation Plan: Universal Charter Rename

**Branch**: `main` | **Date**: 2026-04-04 (revised) | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/063-universal-charter-rename/spec.md`

## Summary

Rename every occurrence of "constitution" to "charter" across the spec-kitty codebase. Convert the 5 existing constitution-related migrations to no-op stubs and consolidate all backward-compatibility logic into a single comprehensive charter-rename migration that handles all 3 known legacy layouts, rewrites generated content, updates agent prompts, and normalizes metadata IDs. Add metadata normalization so old migration IDs are rewritten at load time. Update all Python packages, CLI commands, skills, doctrine mission artifacts, worktree code, documentation, tests, and configuration.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (YAML parsing), pathlib (filesystem), shutil (directory operations)
**Storage**: Filesystem only (YAML, JSON, Markdown files in `.kittify/`)
**Testing**: pytest with 90%+ coverage for new migration code
**Target Platform**: Cross-platform (macOS, Linux, Windows)
**Project Type**: Single Python package (`spec-kitty-cli`)
**Constraints**: mypy --strict must pass; no backward-compatibility CLI aliases

## Charter Check

**Source**: `.kittify/constitution/constitution.md` (will become `.kittify/charter/charter.md`)

- **typer** for CLI: Confirmed — CLI command group renamed via typer
- **rich** for console output: Confirmed — migration progress messages use rich
- **ruamel.yaml** for YAML parsing: Confirmed — metadata normalization reads/writes YAML
- **pytest with 90%+ coverage**: Confirmed — comprehensive migration tests required
- **mypy --strict**: Confirmed — all renamed modules + new migration pass strict type checking
- **Integration tests for CLI commands**: Confirmed — CLI tests renamed and updated

**DIRECTIVE_010 (Specification Fidelity)**: The rename inventory covers 12 surface categories. Implementation must cover every listed surface plus the newly identified surfaces (doctrine mission artifacts, worktree code, extended documentation).

**DIRECTIVE_003 (Decision Documentation)**: Design decisions DD-1 through DD-7 are documented below with rationale and alternatives considered.

No violations. All gates pass.

## Project Structure

### Documentation (this feature)

```
kitty-specs/063-universal-charter-rename/
├── spec.md              # Feature specification (revised)
├── plan.md              # This file (revised)
├── research.md          # Phase 0: migration registry + surface research
├── data-model.md        # Phase 1: path layout, migration state, symbol renames
├── quickstart.md        # Phase 1: implementation quickstart
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```
# Renamed packages
src/charter/                          # Was: src/constitution/ (14 modules)
src/specify_cli/charter/              # Was: src/specify_cli/constitution/ (11 modules)
src/specify_cli/cli/commands/charter.py  # Was: constitution.py
src/specify_cli/dashboard/charter_path.py  # Was: constitution_path.py
src/doctrine/charter/defaults.yaml    # Was: src/doctrine/constitution/

# Renamed skills
src/doctrine/skills/spec-kitty-charter-doctrine/  # Was: spec-kitty-constitution-doctrine/

# Renamed command template
src/specify_cli/missions/software-dev/command-templates/charter.md  # Was: constitution.md

# Migration files
src/specify_cli/upgrade/migrations/
  ├── m_0_10_12_charter_cleanup.py         # STUB (was: constitution_cleanup)
  ├── m_0_13_0_update_charter_templates.py # STUB (was: constitution_templates, already disabled)
  ├── m_2_0_0_charter_directory.py         # STUB (was: constitution_directory)
  ├── m_2_0_2_charter_context_bootstrap.py # STUB (was: constitution_context_bootstrap)
  ├── m_2_1_2_fix_charter_doctrine_skill.py # STUB (was: constitution_doctrine_skill)
  └── m_3_1_1_charter_rename.py            # NEW: comprehensive migration
src/specify_cli/upgrade/metadata.py        # MODIFIED: legacy ID normalization map

# Renamed tests
tests/charter/                        # Was: tests/constitution/ (16 files)
tests/init/test_charter_runtime_integration.py
tests/test_dashboard/test_api_charter.py
tests/upgrade/migrations/test_charter_migration.py
tests/upgrade/test_charter_template_migration.py
tests/upgrade/test_migration_charter_cleanup_unit.py
tests/merge/test_profile_charter_e2e.py
tests/agent/cli/commands/test_charter_cli.py
tests/agent/test_workflow_charter_context.py
```

**Structure Decision**: This is a rename operation. The directory structure mirrors the existing layout with "constitution" replaced by "charter" at every level. Old migrations become stubs; a single comprehensive migration replaces them.

## Design Decisions

### DD-1: Stub Old Migrations + Comprehensive Charter-Rename

**Decision**: Convert all 5 existing constitution-related migrations to no-op stubs. Create a single charter-rename migration that handles ALL known legacy layouts (A, B, C), content rewriting, agent prompt updates, and metadata normalization.

**Rationale**: Old migrations contain "constitution" in path-detection logic that cannot be changed without breaking upgrades. Converting them to stubs (detect → False) removes ALL "constitution" strings from those files. The charter-rename migration is the ONE file that must reference old paths, creating a precisely bounded exception.

**Alternatives rejected**:
- Keep old migrations functional: Leaves "constitution" path literals in 5 files — rejected (larger exception surface)
- Delete old migrations: Breaks migration_id tracking — rejected

### DD-2: Metadata ID Normalization at Load Time

**Decision**: Add `_LEGACY_MIGRATION_ID_MAP` in `metadata.py`. On `ProjectMetadata.load()`, rewrite old migration IDs to charter-era IDs before the runner loop.

**Rationale**: Allows changing migration_id class attributes in stub files to charter names. The normalization runs before has_migration() checks, so the runner correctly recognizes previously-applied migrations. The map contains 5 old ID strings — this is the second precisely bounded exception.

**Alternatives rejected**:
- Keep old migration_ids unchanged: Leaves "constitution" in 5 class attributes AND in all user metadata forever — rejected
- Pre-migration hook: Extra complexity for same result — rejected
- Hash-based detection: Fragile and overengineered — rejected

### DD-3: Clean Break (No CLI Alias)

**Decision**: No backward-compatibility alias from `spec-kitty constitution` to `spec-kitty charter`.

**Rationale**: Per constraint C-005. Users must use `spec-kitty charter` after upgrading.

### DD-4: Content Rewriting in Migration

**Decision**: The charter-rename migration performs case-insensitive find-and-replace of "constitution" → "charter" in all text files under `.kittify/charter/` and in deployed agent prompt files.

**Rationale**: Generated files (references.yaml, governance.yaml, charter.md) embed "constitution" in path strings (`source_path=".kittify/constitution/..."`) and command strings (`spec-kitty constitution context`). A path-only move leaves stale references. Content rewriting ensures migrated user state is fully charter-only.

### DD-5: Dev Repo Direct Rename

**Decision**: The spec-kitty development repo's own `.kittify/constitution/` is renamed directly via git, not via the migration.

**Rationale**: The migration targets user projects during `spec-kitty upgrade`. The dev repo's `.kittify/` state is managed directly by contributors.

### DD-6: Agent Artifact Regeneration

**Decision**: Rename agent command files and skill directories in all configured agent directories. Also rename within the charter-rename migration for user projects.

**Rationale**: Agent artifacts are generated copies. Renaming the source templates ensures future deployments produce correct names. The migration handles existing projects. Global skill sync (`ensure_global_agent_skills()`) automatically removes stale `spec-kitty-constitution-*` skills and deploys `spec-kitty-charter-*` skills.

### DD-7: Worktree Code Update (Not Migration)

**Decision**: Update worktree setup code (`setup_feature_directory()`, `copy_charter_templates()`) to use charter paths. Do NOT retroactively fix existing worktrees.

**Rationale**: Worktrees are ephemeral execution workspaces. Existing worktrees will be recreated or abandoned. New worktrees pick up the charter paths automatically.

## Work Packages

### WP01: Core Package Renames (depends: none)

Rename the two Python packages and all module-level content:

- `git mv src/constitution/ src/charter/` — rename the 14-module top-level package
- `git mv src/specify_cli/constitution/ src/specify_cli/charter/` — rename the 11-module CLI namespace package
- Inside every `.py` file in both renamed packages: replace "constitution" with "charter" in class names, function names, docstrings, comments, string literals
- Update `src/charter/__init__.py` exports: `CompiledConstitution` → `CompiledCharter`, `ConstitutionParser` → `CharterParser`, etc. (see data-model.md Symbol Renames)
- Update `src/specify_cli/charter/__init__.py` to mirror

### WP02: CLI, Dashboard, Worktree & Runtime Renames (depends: none)

- `git mv src/specify_cli/cli/commands/constitution.py src/specify_cli/cli/commands/charter.py`
- Update typer app: `name="charter"`, `help="Charter management commands"`
- Update all subcommand help text, docstrings, imports
- `git mv src/specify_cli/dashboard/constitution_path.py src/specify_cli/dashboard/charter_path.py`
- Rename `resolve_project_constitution_path()` → `resolve_project_charter_path()`
- Update CLI registration in `src/specify_cli/cli/commands/__init__.py`: change module import + `name="constitution"` → `name="charter"`
- Update `src/specify_cli/state_contract.py`: `.kittify/constitution/context-state.json` → `.kittify/charter/context-state.json`
- Update `src/specify_cli/core/worktree.py` `setup_feature_directory()`: comment + symlink logic referencing constitution → charter
- Update `src/specify_cli/template/manager.py`: rename `copy_constitution_templates()` → `copy_charter_templates()`, update all internal references
- Update `src/specify_cli/cli/commands/init.py`: constitution setup → charter setup

### WP03: Import, Build & Cross-Reference Updates (depends: WP01, WP02)

- Update ALL import statements across the entire codebase: `from constitution.X import Y` → `from charter.X import Y`, `from specify_cli.constitution.X` → `from specify_cli.charter.X`
- Update `pyproject.toml`: package list (`src/constitution` → `src/charter`), data includes, all "constitution" references
- Update `src/specify_cli/cli/commands/__init__.py` module import path
- Update any `importlib.import_module` calls referencing "constitution"
- Verify: `python -c "from charter import compile_charter"` succeeds
- Verify: `mypy --strict src/charter/ src/specify_cli/charter/` passes

### WP04: Doctrine, Skills, Templates & Mission Artifacts (depends: none)

- `git mv src/doctrine/constitution/ src/doctrine/charter/`
- Update `src/doctrine/charter/defaults.yaml` content
- `git mv src/doctrine/skills/spec-kitty-constitution-doctrine/ src/doctrine/skills/spec-kitty-charter-doctrine/`
- Rename `references/constitution-command-map.md` → `references/charter-command-map.md`
- Update SKILL.md: name, triggers, description, all content
- `git mv src/specify_cli/missions/software-dev/command-templates/constitution.md ...charter.md`
- Update command template content
- `git mv src/doctrine/procedures/shipped/migrate-project-guidance-to-spec-kitty-constitution.procedure.yaml ...charter.procedure.yaml`
- **Doctrine mission artifacts** (9 files):
  - `src/doctrine/missions/software-dev/mission.yaml` (1 match)
  - `src/doctrine/missions/software-dev/templates/plan-template.md` (2 matches: "Constitution Check" → "Charter Check")
  - `src/doctrine/missions/software-dev/templates/task-prompt-template.md` (1 match: path reference)
  - `src/doctrine/missions/software-dev/actions/specify/guidelines.md` (1 match)
  - `src/doctrine/missions/software-dev/actions/plan/guidelines.md` (5 matches: "Constitution Compliance" → "Charter Compliance")
  - `src/doctrine/missions/software-dev/actions/implement/guidelines.md` (1 match)
  - `src/doctrine/missions/software-dev/actions/review/guidelines.md` (1 match)
  - `src/doctrine/missions/documentation/templates/plan-template.md` (1 match)
  - `src/doctrine/missions/research/templates/task-prompt-template.md` (1 match)

### WP05: Agent Artifacts & Configuration (depends: WP04)

- For each of the 12 agent directories: rename command files (`spec-kitty.constitution.md` → `spec-kitty.charter.md`)
- For each agent with skill directories: rename skill directory (`spec-kitty-constitution-doctrine/` → `spec-kitty-charter-doctrine/`)
- Update `.kittify/skills-manifest.json` entries
- Update `.kittify/AGENTS.md` (3 matches) and `.kittify/overrides/AGENTS.md` (3 matches)
- Update `.gitignore`: `.kittify/constitution/` → `.kittify/charter/`
- Rename `.kittify/constitution/` → `.kittify/charter/` in the dev repo itself
- Rename `.kittify/charter/constitution.md` → `.kittify/charter/charter.md`
- Update CLAUDE.md: constitution context commands, Constitution Check sections → Charter Check
- Update `.kittify/memory/058-architectural-review.md` (7 matches)

### WP06: Migration Overhaul (depends: WP01)

**Part A: Convert 5 old migrations to stubs**

For each of the 5 migration files:
1. `git mv` to charter name (e.g., `m_0_10_12_constitution_cleanup.py` → `m_0_10_12_charter_cleanup.py`)
2. Replace class with stub:
   ```python
   @MigrationRegistry.register
   class CharterCleanupMigration(BaseMigration):
       migration_id = "0.10.12_charter_cleanup"  # NEW charter-era ID
       description = "Superseded by 3.1.1_charter_rename"
       target_version = "0.10.12"

       def detect(self, project_path: Path) -> bool:
           return False

       def can_apply(self, project_path: Path) -> tuple[bool, str]:
           return False, "Superseded by charter-rename migration"

       def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
           return MigrationResult(success=True, warnings=["Superseded by charter-rename"])
   ```
3. Zero "constitution" strings remain in any stub file

**Part B: Add metadata normalization to metadata.py**

- Add `_LEGACY_MIGRATION_ID_MAP` dict (5 entries mapping old → new IDs)
- In `ProjectMetadata.load()`: after reading YAML, iterate `applied_migrations`, rewrite any ID found in map, persist if changed
- The 5 dict keys are the ONLY "constitution" strings in this file

**Part C: Create comprehensive m_3_1_1_charter_rename.py**

- `migration_id = "3.1.1_charter_rename"`
- `target_version = "3.1.1"`
- `detect()`: returns True if ANY constitution-era path exists:
  - `.kittify/constitution/` (Layout A)
  - `.kittify/memory/constitution.md` (Layout B)
  - `.kittify/missions/*/constitution/` (Layout C)
- `apply()` performs 4 phases:
  1. **Layout normalization**: Remove Layout C dirs, move Layout B file, rename Layout A directory, handle partial state
  2. **Content rewriting**: Case-insensitive find-replace "constitution" → "charter" in all text files under `.kittify/charter/`; replace `spec-kitty constitution context` → `spec-kitty charter context` in deployed agent prompt files
  3. **Agent artifact rename**: Rename command and skill files in all configured agent directories
  4. **Metadata normalization**: Rewrite old migration IDs in `.kittify/metadata.yaml`
- Path literals like `.kittify/constitution/`, `.kittify/memory/constitution.md`, `.kittify/missions/` are the ONLY "constitution" strings in this file — they exist to detect old state

### WP07: Test Overhaul (depends: WP01, WP02, WP03, WP06)

- `git mv tests/constitution/ tests/charter/` — rename directory with all 16 files
- Rename 8 additional test files (see spec Surface 7)
- Update ALL test content: imports, string literals, path references, fixture names, assertion messages
- Update `tests/git_ops/test_worktree.py`: `constitution.md` → `charter.md` references (3 matches)
- Update `conftest.py` fixtures that reference constitution paths
- **New tests for charter-rename migration**:
  - Test Layout A migration (`.kittify/constitution/` → `.kittify/charter/`)
  - Test Layout B migration (`.kittify/memory/constitution.md` → `.kittify/charter/charter.md`)
  - Test Layout C migration (`.kittify/missions/*/constitution/` removal)
  - Test content rewriting (embedded path strings updated)
  - Test agent prompt command string replacement
  - Test metadata ID normalization
  - Test idempotency (run twice, same result)
  - Test partial state recovery (both source and target exist)
  - Test no-op when already migrated
- **New tests for metadata normalization**:
  - Test old IDs rewritten to new IDs on load
  - Test persistence after rewrite
  - Test no-op when IDs already charter-era
- Verify: `python -m pytest tests/ -x -q`

### WP08: Documentation & Acceptance (depends: WP01-WP07)

**Documentation renames** (4 files with "constitution" in filename):
- `docs/2x/doctrine-and-constitution.md` → `doctrine-and-charter.md`
- `docs/development/constitution-path-resolution-gaps.md` → `charter-path-resolution-gaps.md`
- `examples/constitution-driven-quality.md` → `charter-driven-quality.md`
- `architecture/2.x/user_journey/005-governance-mission-constitution-operations.md` → `...charter-operations.md`

**Documentation content updates** (30+ files, 100+ matches):
- `README.md` (9 matches)
- `docs/reference/cli-commands.md` (27 matches)
- `docs/reference/slash-commands.md` (18 matches)
- `docs/reference/file-structure.md` (3 matches)
- `docs/reference/supported-agents.md` (1 match)
- `docs/reference/configuration.md` (8 matches)
- `glossary/README.md` (1 match)
- `glossary/contexts/governance.md` (16 matches)
- `glossary/contexts/configuration-project-structure.md` (6 matches)
- `glossary/contexts/doctrine.md` (13 matches)
- `src/kernel/README.md` (5 matches)
- `src/kernel/paths.py` (1 match)
- `docs/development/test-execution-report-pr305.md`
- `docs/development/doctrine-inclusion-assessment.md`
- `docs/development/pr305-review-resolution-plan.md`
- `docs/development/code-review-2026-03-25.md`
- `docs/development/test-plan-pr305.md`
- `docs/how-to/non-interactive-init.md`
- `docs/how-to/setup-governance.md`
- `examples/claude-cursor-collaboration.md`
- `examples/solo-developer-workflow.md`
- `examples/worktree-parallel-features.md`
- `architecture/2.x/04_implementation_mapping/README.md`
- `architecture/audience/internal/maintainer.md`
- `architecture/audience/internal/spec-kitty-cli-runtime.md`
- `architecture/audience/internal/lead-developer.md`

**Acceptance verification**:
```bash
# Primary gate: zero matches outside bounded exceptions
rg -n -i constitution . \
  --glob '!CHANGELOG.md' \
  --glob '!kitty-specs/' \
  --glob '!src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py' \
  --glob '!src/specify_cli/upgrade/metadata.py'
# Must return 0 matches

# Filename gate: no filenames contain "constitution"
find . -name '*constitution*' -not -path './kitty-specs/*' -not -path './.git/*'
# Must return 0 results

# Test gate
python -m pytest tests/ -x -q

# Type gate
mypy --strict src/charter/ src/specify_cli/charter/
```

## Dependency Graph

```
WP01 ──┐
       ├──→ WP03 ──┐
WP02 ──┘            │
                    ├──→ WP07 ──┐
WP04 ──→ WP05      │           ├──→ WP08
                    │           │
WP06 ───────────────┘───────────┘
```

- WP01 + WP02 + WP04: parallel (no interdependencies)
- WP03: imports + build (after WP01, WP02)
- WP05: agent artifacts + config (after WP04)
- WP06: migration overhaul (after WP01 — imports charter package in new migration)
- WP07: tests (after WP01, WP02, WP03, WP06)
- WP08: docs + acceptance (after all)

## Complexity Tracking

No charter check violations. No complexity justifications needed.

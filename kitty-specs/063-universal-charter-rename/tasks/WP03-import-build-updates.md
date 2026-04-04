---
work_package_id: WP03
title: Import, Build & Cross-Reference Updates
dependencies: []
requirement_refs:
- FR-010
- FR-011
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T013, T014, T015, T016, T017]
history:
- date: '2026-04-04'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files: [pyproject.toml, src/specify_cli/__init__.py, src/specify_cli/runtime/**, src/specify_cli/skills/**]
---

# WP03: Import, Build & Cross-Reference Updates

## Objective

Update every import statement across the codebase that references `constitution` or `specify_cli.constitution` modules. Update `pyproject.toml` package configuration. Verify the codebase compiles and passes type checking.

## Context

WP01 renamed the packages. WP02 renamed CLI and runtime modules. This WP makes the rest of the codebase aware of those renames by updating all cross-references. This is the integration glue that makes everything compile again.

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

## Subtask T013: Update all import statements across codebase

**Purpose**: Every file outside WP01/WP02 scope that imports from `constitution` or `specify_cli.constitution` must be updated.

**Steps**:
1. Search for all imports: `rg "from constitution" src/` and `rg "from specify_cli.constitution" src/` and `rg "import constitution" src/`
2. For each match NOT in `src/charter/` or `src/specify_cli/charter/` (those are WP01's scope):
   - Replace `from constitution.X import Y` → `from charter.X import Y`
   - Replace `from specify_cli.constitution.X import Y` → `from specify_cli.charter.X import Y`
   - Replace `import constitution` → `import charter`
3. Key files likely to have imports:
   - `src/specify_cli/runtime/` modules (agent_skills.py, etc.)
   - `src/specify_cli/skills/` modules (registry.py, manifest.py, etc.)
   - `src/specify_cli/__init__.py` (main package init)
   - `src/specify_cli/merge/` modules
   - `src/specify_cli/core/config.py`
   - Any file that calls `compile_constitution()`, `build_constitution_context()`, `sync_constitution()`, etc.
4. Also update function CALL sites where renamed functions are called:
   - `compile_constitution()` → `compile_charter()`
   - `build_constitution_context()` → `build_charter_context()`
   - `sync_constitution()` → `sync_charter()`
   - `write_compiled_constitution()` → `write_compiled_charter()`
   - `resolve_project_constitution_path()` → `resolve_project_charter_path()`
   - `copy_constitution_templates()` → `copy_charter_templates()`

**Validation**: `rg "from constitution" src/ --glob '!src/charter/**'` returns zero matches. `rg "constitution" src/specify_cli/ --glob '!src/specify_cli/charter/**' --glob '!src/specify_cli/upgrade/**'` returns zero matches (upgrade/ is WP06 scope).

## Subtask T014: Update pyproject.toml package configuration

**Purpose**: Update the build configuration to reference the charter package.

**Steps**:
1. In `pyproject.toml`:
   - Update `packages = ["src/kernel", "src/specify_cli", "src/doctrine", "src/constitution"]` → replace `"src/constitution"` with `"src/charter"`
   - Update any `py.typed` entries referencing constitution
   - Update data includes: `"src/constitution/"` → `"src/charter/"`
   - Update `"src/specify_cli/constitution/"` → `"src/specify_cli/charter/"`
   - Search for ALL occurrences of "constitution" in the file and replace

**Validation**: `rg -i constitution pyproject.toml` returns zero matches.

## Subtask T015: Update importlib.import_module references

**Purpose**: Update any dynamic import references.

**Steps**:
1. Search: `rg "importlib.*constitution" src/` and `rg "import_module.*constitution" src/`
2. Replace any string arguments to `importlib.import_module()` that reference constitution packages
3. Check for any `__import__` or `pkgutil` references to constitution

**Validation**: No dynamic references to constitution remain.

## Subtask T016: Verify mypy --strict passes

**Purpose**: Ensure type checking passes on all renamed modules.

**Steps**:
1. Run: `mypy --strict src/charter/ src/specify_cli/charter/`
2. Fix any type errors introduced by the renames
3. Common issues: Type aliases using old names, TypeVar references, Protocol implementations

**Validation**: mypy returns 0 errors on charter modules.

## Subtask T017: Smoke test imports

**Purpose**: Verify the renamed packages can be imported.

**Steps**:
1. Run: `python -c "from charter import CompiledCharter, CharterParser, compile_charter, build_charter_context"`
2. Run: `python -c "from specify_cli.charter import CompiledCharter"`
3. Run: `python -c "from specify_cli.cli.commands.charter import app"`
4. Run: `python -c "from specify_cli.dashboard.charter_path import resolve_project_charter_path"`

**Validation**: All imports succeed without ImportError.

## Definition of Done

- [ ] No import statements reference `constitution` or `specify_cli.constitution` (outside upgrade/ which is WP06)
- [ ] `pyproject.toml` references `src/charter` not `src/constitution`
- [ ] `mypy --strict` passes on charter modules
- [ ] All smoke test imports succeed
- [ ] `rg "from constitution" src/ --glob '!src/specify_cli/upgrade/**'` returns zero matches

## Risks

- **Hidden imports**: Some files may use conditional imports or lazy imports. Search thoroughly with multiple patterns.
- **Call sites**: Renaming functions means updating every call site, not just import statements.

## Reviewer Guidance

- Pay special attention to `__init__.py` files which may have complex re-export chains
- Verify pyproject.toml changes don't break `pip install -e .`
- Check that no constitution references leak through string interpolation (f-strings mentioning old module paths)

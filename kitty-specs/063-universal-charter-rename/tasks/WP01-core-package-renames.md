---
work_package_id: WP01
title: Core Package Renames
dependencies: []
requirement_refs:
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: c254e92603a20bad62b5a8cc80bedfec36caae9b
created_at: '2026-04-04T19:48:38.211373+00:00'
subtasks: [T001, T002, T003, T004, T005]
shell_pid: "18377"
agent: "codex"
history:
- date: '2026-04-04'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/charter/
execution_mode: code_change
owned_files: [src/charter/**, src/specify_cli/charter/**]
---

# WP01: Core Package Renames

## Objective

Rename the two Python packages `src/constitution/` and `src/specify_cli/constitution/` to `src/charter/` and `src/specify_cli/charter/` respectively. Update all class names, function names, docstrings, comments, and string literals within these packages so that no occurrence of "constitution" remains.

## Context

These two packages are the core of the governance system:
- `src/constitution/` (14 modules): Top-level package exporting 41+ symbols including `CompiledConstitution`, `ConstitutionParser`, `compile_constitution()`, etc.
- `src/specify_cli/constitution/` (11 modules): CLI-namespace mirror package re-exporting most symbols.

The symbol rename table is in `kitty-specs/063-universal-charter-rename/data-model.md` under "Symbol Renames".

## Implementation Command

```bash
spec-kitty implement WP01
```

## Subtask T001: Rename src/constitution/ directory

**Purpose**: Move the 14-module top-level package to its new name.

**Steps**:
1. Run `git mv src/constitution/ src/charter/`
2. Verify all 14 .py files are present in `src/charter/`:
   - `__init__.py`, `catalog.py`, `compiler.py`, `context.py`, `extractor.py`, `generator.py`, `hasher.py`, `interview.py`, `parser.py`, `reference_resolver.py`, `resolver.py`, `schemas.py`, `sync.py`, `template_resolver.py`

**Validation**: `ls src/charter/` shows all 14 files.

## Subtask T002: Update class/function names in src/charter/ modules

**Purpose**: Replace all "constitution" references in class names, function names, variable names, docstrings, comments, and string literals.

**Steps**:
For each .py file in `src/charter/`, perform case-preserving replacements:
- `constitution` → `charter`
- `Constitution` → `Charter`
- `CONSTITUTION` → `CHARTER`

**Key renames** (see data-model.md for full list):
- `compiler.py`: `CompiledConstitution` → `CompiledCharter`, `compile_constitution()` → `compile_charter()`, `write_compiled_constitution()` → `write_compiled_charter()`
- `parser.py`: `ConstitutionParser` → `CharterParser`, `ConstitutionSection` → `CharterSection`
- `interview.py`: `ConstitutionInterview` → `CharterInterview`
- `context.py`: `build_constitution_context()` → `build_charter_context()`
- `generator.py`: `build_constitution_draft()` → `build_charter_draft()`
- `sync.py`: References to "constitution" in sync logic
- `template_resolver.py`: `ConstitutionTemplateResolver` → `CharterTemplateResolver`
- `schemas.py`: Any schema class names or field references
- `catalog.py`, `extractor.py`, `hasher.py`, `reference_resolver.py`, `resolver.py`: All internal references

**Do NOT update**: Import paths like `from constitution.X` — those are handled in WP03.

**Validation**: `rg -i constitution src/charter/` returns zero matches.

## Subtask T003: Rename src/specify_cli/constitution/ directory

**Purpose**: Move the 11-module CLI namespace package.

**Steps**:
1. Run `git mv src/specify_cli/constitution/ src/specify_cli/charter/`
2. Verify all 11 .py files are present.

## Subtask T004: Update class/function names in src/specify_cli/charter/ modules

**Purpose**: Same as T002 but for the CLI namespace mirror package.

**Steps**: Same case-preserving replacement as T002 across all 11 modules. This package mirrors src/charter/ so the same renames apply.

**Validation**: `rg -i constitution src/specify_cli/charter/` returns zero matches.

## Subtask T005: Update __init__.py exports in both packages

**Purpose**: Ensure the public API of both packages uses charter names.

**Steps**:
1. In `src/charter/__init__.py`:
   - Update all `__all__` entries from constitution to charter names
   - Update all import-and-reexport statements
   - Update module docstring
2. In `src/specify_cli/charter/__init__.py`:
   - Mirror the changes from src/charter/__init__.py
   - Ensure it re-exports the same set of symbols under charter names

**Validation**:
- `python -c "from charter import CompiledCharter, CharterParser, compile_charter"` (will fail until WP03 fixes pyproject.toml, but verify the names exist in the file)
- `rg -i constitution src/charter/__init__.py src/specify_cli/charter/__init__.py` returns zero matches.

## Definition of Done

- [ ] `src/charter/` exists with all 14 modules
- [ ] `src/specify_cli/charter/` exists with all 11 modules
- [ ] `src/constitution/` does not exist
- [ ] `src/specify_cli/constitution/` does not exist
- [ ] `rg -i constitution src/charter/ src/specify_cli/charter/` returns zero matches
- [ ] All class/function renames from data-model.md Symbol Renames table are applied

## Risks

- **Downstream import breakage**: Expected. WP03 handles all import updates. This WP focuses solely on the packages themselves.
- **Missed renames in string literals**: Check generated output strings (e.g., error messages mentioning "constitution") carefully.

## Reviewer Guidance

- Verify every class name in data-model.md Symbol Renames is present in the renamed files
- Check docstrings and comments — these are easy to miss
- Verify __init__.py exports match the new names exactly

## Activity Log

- 2026-04-04T19:48:38Z – claude – shell_pid=15690 – Started implementation via action command
- 2026-04-04T19:53:48Z – claude – shell_pid=15690 – Core packages renamed to charter: src/constitution/ -> src/charter/ (14 modules), src/specify_cli/constitution/ -> src/specify_cli/charter/ (12 modules). All class/function/docstring/string renames applied.
- 2026-04-04T19:54:23Z – codex – shell_pid=16345 – Started review via action command
- 2026-04-04T19:59:08Z – codex – shell_pid=16345 – Moved to planned
- 2026-04-04T19:59:28Z – claude – shell_pid=17519 – Started implementation via action command
- 2026-04-04T20:01:37Z – claude – shell_pid=17519 – Fixed: all 19 intra-package imports updated from constitution to charter, zero constitution references remain, import verified
- 2026-04-04T20:01:53Z – codex – shell_pid=18377 – Started review via action command

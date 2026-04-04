---
work_package_id: WP02
title: CLI, Dashboard, Worktree & Runtime Renames
dependencies: []
requirement_refs:
- FR-001
- FR-013
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 666905f1d5d393a3b9f7318fa10c643bee90e78b
created_at: '2026-04-04T19:48:40.413256+00:00'
subtasks: [T006, T007, T008, T009, T010, T011, T012]
shell_pid: "15743"
agent: "claude"
history:
- date: '2026-04-04'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/
execution_mode: code_change
owned_files: [src/specify_cli/cli/commands/charter.py, src/specify_cli/cli/commands/__init__.py, src/specify_cli/dashboard/charter_path.py, src/specify_cli/state_contract.py, src/specify_cli/core/worktree.py, src/specify_cli/template/manager.py, src/specify_cli/cli/commands/init.py]
---

# WP02: CLI, Dashboard, Worktree & Runtime Renames

## Objective

Rename the CLI command module, dashboard path resolver, and runtime code that references "constitution". Update worktree setup, template manager, and project initialization to use charter paths.

## Context

The CLI exposes `spec-kitty constitution` as a typer subcommand group. The dashboard resolves constitution paths. The worktree system shares constitution state via symlinks. The template manager copies constitution templates. All must switch to "charter".

## Implementation Command

```bash
spec-kitty implement WP02
```

## Subtask T006: Rename CLI command file + update typer app

**Purpose**: Rename the CLI module and update its internal command group.

**Steps**:
1. `git mv src/specify_cli/cli/commands/constitution.py src/specify_cli/cli/commands/charter.py`
2. In `charter.py`:
   - Change `app = typer.Typer(name="constitution", help="Constitution management commands", ...)` → `app = typer.Typer(name="charter", help="Charter management commands", ...)`
   - Update all subcommand help text and docstrings: "constitution" → "charter"
   - Update all import statements: `from constitution.X import Y` → `from charter.X import Y`
   - Update all path references: `.kittify/constitution/` → `.kittify/charter/`
   - Update suggested commands in output messages: `spec-kitty constitution sync` → `spec-kitty charter sync`

**Validation**: `rg -i constitution src/specify_cli/cli/commands/charter.py` returns zero matches.

## Subtask T007: Update CLI registration in commands/__init__.py

**Purpose**: Mount the renamed command group on the CLI.

**Steps**:
1. In `src/specify_cli/cli/commands/__init__.py`:
   - Change the import: `from . import constitution as constitution_module` → `from . import charter as charter_module` (or however the import is structured)
   - Change the registration: `app.add_typer(constitution_module.app, name="constitution")` ��� `app.add_typer(charter_module.app, name="charter")`
   - Update any other references to the constitution module

**Validation**: `rg -i constitution src/specify_cli/cli/commands/__init__.py` returns zero matches.

## Subtask T008: Rename dashboard module + update function names

**Purpose**: Rename the path resolution module.

**Steps**:
1. `git mv src/specify_cli/dashboard/constitution_path.py src/specify_cli/dashboard/charter_path.py`
2. In `charter_path.py`:
   - Rename `resolve_project_constitution_path()` → `resolve_project_charter_path()`
   - Update all internal path references: `.kittify/constitution/` → `.kittify/charter/`, `.kittify/memory/constitution.md` → `.kittify/charter/charter.md`
   - Update docstrings and comments

**Validation**: `rg -i constitution src/specify_cli/dashboard/charter_path.py` returns zero matches.

## Subtask T009: Update state_contract.py

**Purpose**: Update the state tracking module's path references.

**Steps**:
1. In `src/specify_cli/state_contract.py`:
   - Replace `.kittify/constitution/context-state.json` → `.kittify/charter/context-state.json`
   - Replace any other "constitution" references in path strings, comments, or variable names

**Validation**: `rg -i constitution src/specify_cli/state_contract.py` returns zero matches.

## Subtask T010: Update worktree.py setup_feature_directory()

**Purpose**: Update worktree constitution sharing to use charter paths.

**Steps**:
1. In `src/specify_cli/core/worktree.py`:
   - Find `setup_feature_directory()` (around line 440)
   - Update the comment "Setup shared constitution and AGENTS.md via symlink" → "Setup shared charter and AGENTS.md via symlink"
   - Update any symlink paths that reference constitution
   - If the function creates symlinks to `.kittify/memory` (which contained constitution.md), update to include `.kittify/charter` if needed
   - Replace all "constitution" references in comments, variable names, and string literals

**Validation**: `rg -i constitution src/specify_cli/core/worktree.py` returns zero matches.

## Subtask T011: Rename copy_constitution_templates() in template/manager.py

**Purpose**: Rename the template copy function and update internal references.

**Steps**:
1. In `src/specify_cli/template/manager.py`:
   - Rename function `copy_constitution_templates()` → `copy_charter_templates()`
   - Update all internal references and comments
   - Update callers within the same file: `copy_specify_base_from_local()` and `copy_specify_base_from_package()` both call this function
   - Update path references if any point to constitution directories

**Validation**: `rg -i constitution src/specify_cli/template/manager.py` returns zero matches.

## Subtask T012: Update init.py constitution setup references

**Purpose**: Update project initialization to scaffold charter paths.

**Steps**:
1. In `src/specify_cli/cli/commands/init.py`:
   - Replace any references to `constitution` in path construction, variable names, comments
   - Ensure `spec-kitty init` scaffolds `.kittify/charter/` not `.kittify/constitution/`
   - Update any help text or output messages

**Validation**: `rg -i constitution src/specify_cli/cli/commands/init.py` returns zero matches.

## Definition of Done

- [ ] `src/specify_cli/cli/commands/charter.py` exists (old `constitution.py` removed)
- [ ] `src/specify_cli/dashboard/charter_path.py` exists (old `constitution_path.py` removed)
- [ ] CLI registers `spec-kitty charter` command group
- [ ] Worktree setup uses charter paths
- [ ] Template manager function renamed to `copy_charter_templates()`
- [ ] `rg -i constitution` across all 7 owned files returns zero matches

## Risks

- **CLI subcommand loss**: After renaming, verify all 5 subcommands (interview, generate, context, sync, status) are accessible under `spec-kitty charter`.
- **Broken callers**: Functions like `copy_charter_templates()` are called from other files — WP03 handles updating those callers.

## Reviewer Guidance

- Check that the typer app `name=` parameter is "charter" (not "constitution")
- Verify all output messages to the user say "charter" not "constitution"
- Check worktree.py symlink logic carefully — constitution sharing is critical for multi-agent workflows

## Activity Log

- 2026-04-04T19:48:40Z – claude – shell_pid=15743 – Started implementation via action command

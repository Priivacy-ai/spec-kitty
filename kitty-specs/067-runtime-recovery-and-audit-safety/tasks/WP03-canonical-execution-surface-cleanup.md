---
work_package_id: WP03
title: Canonical Execution Surface Cleanup
dependencies: []
requirement_refs:
- C-003
- FR-006
- FR-007
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T012, T013, T014, T015, T016, T017]
history:
- timestamp: '2026-04-06T18:43:32+00:00'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/shims/
execution_mode: code_change
owned_files:
- src/specify_cli/shims/generator.py
- src/specify_cli/shims/entrypoints.py
- src/specify_cli/shims/models.py
- src/specify_cli/shims/__init__.py
- src/specify_cli/cli/commands/shim.py
- src/specify_cli/cli/commands/agent/__init__.py
- src/specify_cli/core/execution_context.py
- src/specify_cli/migration/rewrite_shims.py
- tests/specify_cli/shims/**
- tests/specify_cli/core/test_execution_context*
---

# WP03: Canonical Execution Surface Cleanup

## Objective

Remove the generic `agent shim` runtime and replace generated command files with direct canonical CLI calls. Also register `accept` in the action resolver to fix the inconsistency where shim support exists but the canonical resolver rejects it.

**Issues**: [#412](https://github.com/Priivacy-ai/spec-kitty/issues/412), [#414](https://github.com/Priivacy-ai/spec-kitty/issues/414)

## Context

Two parallel dispatch systems coexist:

1. **ActionName resolver** (`src/specify_cli/core/execution_context.py:21-28`): Only knows 6 actions: `tasks`, `tasks_outline`, `tasks_packages`, `tasks_finalize`, `implement`, `review`. **`accept` is missing**.

2. **Shim registry** (`src/specify_cli/shims/registry.py:24-43`): Classifies 16 consumer skills as prompt-driven (9) or CLI-driven (7). For CLI-driven commands, `generate_shim_content()` emits markdown files containing `spec-kitty agent shim <cmd>` dispatch calls.

The shim pipeline: Generated command files → `spec-kitty agent shim <cmd>` → `shim_dispatch()` → `resolve_or_load()` → returns context. The shim runtime does context resolution then returns — it never actually dispatches the canonical command. This is pure overhead.

`accept` is feature-level (takes `--mission`, not `--wp-id`). Adding it to `ActionName` (WP-scoped) is backward-compat convenience. The primary fix is making all generated files call canonical commands directly.

### Key files

| File | Line(s) | What |
|------|---------|------|
| `src/specify_cli/core/execution_context.py` | 21-28 | ActionName Literal — missing "accept" |
| `src/specify_cli/shims/registry.py` | 24-43, 58-85 | 16 consumer skills, prompt vs CLI classification |
| `src/specify_cli/shims/generator.py` | 53-77 | `generate_shim_content()` — emits `spec-kitty agent shim <cmd>` |
| `src/specify_cli/shims/entrypoints.py` | 86-149 | `shim_dispatch()` — context resolution (TO DELETE) |
| `src/specify_cli/shims/models.py` | all | AgentShimConfig, ShimTemplate (only used via __init__.py re-export, TO DELETE) |
| `src/specify_cli/cli/commands/shim.py` | all | CLI shim command with 9 subcommands (TO DELETE) |
| `src/specify_cli/cli/commands/agent/__init__.py` | 24 | Shim CLI registration (TO REMOVE) |
| `src/specify_cli/migration/rewrite_shims.py` | 149-252 | `rewrite_agent_shims()` — regenerates all agent files |

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

## Subtasks

### T012: Rewrite `generate_shim_content()` for Direct Commands

**Purpose**: Make generated CLI-driven command files call canonical CLI commands directly instead of routing through the shim runtime.

**Steps**:

1. In `src/specify_cli/shims/generator.py`, rewrite `generate_shim_content()`:
   - Keep the same signature: `(command: str, agent_name: str, arg_placeholder: str) -> str`
   - Replace the single `spec-kitty agent shim <cmd>` dispatch with command-specific canonical calls

2. The mapping for CLI-driven commands:
   ```
   implement    → spec-kitty agent action implement {ARGS} --agent {AGENT}
   review       → spec-kitty agent action review {ARGS} --agent {AGENT}
   accept       → spec-kitty agent mission accept {ARGS}
   merge        → spec-kitty merge {ARGS}
   status       → spec-kitty agent tasks status {ARGS}
   dashboard    → spec-kitty dashboard {ARGS}
   tasks-finalize → spec-kitty agent mission finalize-tasks {ARGS}
   ```

3. Keep the existing markdown format:
   ```markdown
   <!-- spec-kitty-command-version: X.Y.Z -->
   Run this exact command and treat its output as authoritative.
   Do not rediscover context from branches, files, or prompt contents.
   In repos with multiple missions, pass --mission <slug> in your arguments.

   `<canonical-command>`
   ```

4. The `{ARGS}` and `{AGENT}` placeholders are replaced by the `arg_placeholder` and `agent_name` parameters.

**Validation**:
- [ ] `generate_shim_content("implement", "claude", "$ARGUMENTS")` produces `spec-kitty agent action implement $ARGUMENTS --agent claude`
- [ ] `generate_shim_content("accept", "claude", "$ARGUMENTS")` produces `spec-kitty agent mission accept $ARGUMENTS`
- [ ] All 7 CLI-driven commands produce correct canonical calls

### T013: Add `"accept"` to ActionName Literal

**Purpose**: Register `accept` in the canonical action resolver for backward compatibility with any code path that uses `ActionName`.

**Steps**:

1. In `src/specify_cli/core/execution_context.py:21-28`, update:
   ```python
   ActionName = Literal[
       "tasks",
       "tasks_outline",
       "tasks_packages",
       "tasks_finalize",
       "implement",
       "review",
       "accept",  # NEW
   ]
   ```

2. Verify that `resolve_action_context()` at line 166 handles `accept` appropriately:
   - `accept` is feature-level (no WP context). The resolver may need a code path that returns mission-level context without WP resolution.
   - If `resolve_action_context()` assumes WP-level scope, add a guard: for `accept`, return a partial context without `wp_id` / `wp_file` / `lane`.

3. Update `ACTION_NAMES` tuple (line 29) — this is auto-derived from `get_args(ActionName)`, so no manual change needed.

**Validation**:
- [ ] `"accept"` is in `ACTION_NAMES`
- [ ] `resolve_action_context()` with action="accept" does not crash
- [ ] Backward compatibility: existing action resolution for implement/review still works

### T014: Delete Shim Runtime Files

**Purpose**: Remove the shim dispatch infrastructure that is no longer needed.

**Steps**:

1. Delete these files:
   - `src/specify_cli/shims/entrypoints.py` (shim_dispatch, resolve_or_load)
   - `src/specify_cli/shims/models.py` (AgentShimConfig, ShimTemplate — only re-exported in `__init__.py`, no other consumers)
   - `src/specify_cli/cli/commands/shim.py` (CLI shim command with 9 subcommands)

2. Update `src/specify_cli/shims/__init__.py`:
   - Remove imports of `AgentShimConfig`, `ShimTemplate` from models
   - Remove imports of `shim_dispatch`, `resolve_or_load` from entrypoints
   - Keep imports from `generator.py` and `registry.py` (still used)

3. Remove shim CLI registration in `src/specify_cli/cli/commands/agent/__init__.py:24`:
   ```python
   # DELETE: app.add_typer(shim_module.app, name="shim")
   ```
   Also remove the import of `shim_module`.

4. Search for any remaining imports of deleted symbols and update:
   ```bash
   grep -r "from specify_cli.shims.entrypoints" src/
   grep -r "from specify_cli.shims.models" src/
   grep -r "from specify_cli.cli.commands.shim" src/
   grep -r "agent shim" src/ tests/
   ```

**Validation**:
- [ ] `entrypoints.py`, `models.py`, `shim.py` are deleted
- [ ] `__init__.py` exports are updated (no import errors)
- [ ] `agent shim` CLI subcommand no longer registered
- [ ] No dangling imports reference deleted modules

### T015: Update `rewrite_agent_shims()` for New Generator

**Purpose**: Ensure the migration rewrite function produces direct-command files when regenerating agent surfaces.

**Steps**:

1. In `src/specify_cli/migration/rewrite_shims.py`:
   - `rewrite_agent_shims()` at lines 149-252 already calls `generate_all_shims(repo_root)` which calls `generate_shim_content()`
   - Since T012 rewrites `generate_shim_content()`, this function automatically produces correct output
   - Verify the flow: `rewrite_agent_shims()` → `generate_all_shims()` → `generate_shim_content()` (rewritten)

2. Check if `rewrite_agent_shims()` references any deleted code paths:
   - Look for imports of `entrypoints`, `models`, `ShimTemplate`, `AgentShimConfig`
   - Remove any references to deleted symbols

3. Verify the function still handles all 12 agent directories correctly via `get_agent_dirs_for_project()`.

**Validation**:
- [ ] `rewrite_agent_shims()` produces direct-command files (not `agent shim` calls)
- [ ] No references to deleted modules
- [ ] All configured agents are processed

### T016: Write Migration to Regenerate Agent Files

**Purpose**: Existing projects have shim-based command files. A migration must rewrite them to use direct commands.

**Steps**:

1. Create a new migration in `src/specify_cli/upgrade/migrations/`:
   - Name: `m_X_Y_Z_direct_canonical_commands.py` (use appropriate version)
   - Pattern: follows existing migration conventions

2. The migration's `apply()` method:
   - Call `rewrite_agent_shims(repo_root)` to regenerate all agent command files
   - Log which files were updated and which agents were processed
   - Return `RewriteResult` stats

3. Register the migration in the migrations registry so `spec-kitty upgrade` picks it up.

4. Handle edge cases:
   - Projects with no agent directories (skip gracefully)
   - Projects with only prompt-driven commands (no CLI shim files to rewrite)
   - Projects with custom/manual command files (preserve files not matching `spec-kitty.*` pattern)

**Validation**:
- [ ] Migration rewrites existing shim files to direct commands
- [ ] Migration runs idempotently (can be applied multiple times)
- [ ] Unconfigured agents are skipped

### T017: Write Tests for Direct Command Surfaces

**Purpose**: Verify that generated command files contain direct canonical commands across the 3 required agent surfaces (C-003).

**Test scenarios**:

1. **test_generate_shim_content_direct_implement**: Verify implement command maps to `spec-kitty agent action implement`
2. **test_generate_shim_content_direct_accept**: Verify accept command maps to `spec-kitty agent mission accept`
3. **test_generate_shim_content_all_cli_driven**: Verify all 7 CLI-driven commands produce correct canonical calls
4. **test_accept_in_action_names**: Verify `"accept"` is in `ACTION_NAMES`
5. **test_shim_cli_removed**: Verify `spec-kitty agent shim` command is no longer registered
6. **test_rewrite_produces_direct_commands**: Run `rewrite_agent_shims()` on test project, verify output files contain direct commands
7. **test_claude_commands_have_direct_calls**: Check `.claude/commands/spec-kitty.implement.md` contains `spec-kitty agent action implement`
8. **test_codex_prompts_have_direct_calls**: Check `.codex/prompts/spec-kitty.implement.md` contains `spec-kitty agent action implement`
9. **test_opencode_commands_have_direct_calls**: Check `.opencode/command/spec-kitty.implement.md` contains `spec-kitty agent action implement`
10. **test_migration_idempotent**: Run migration twice, verify same output

**Files**: `tests/specify_cli/shims/test_direct_commands.py` (new file)

## Definition of Done

- Generated command files call canonical CLI commands directly (no `agent shim` dispatch)
- `accept` is registered in ActionName and resolves without error
- Shim runtime (entrypoints.py, models.py, shim.py) is deleted
- Migration rewrites existing agent command files
- Tests verify `.claude/`, `.codex/`, `.opencode/` surfaces (C-003)
- 90%+ test coverage on new code

## Risks

- Breaking existing projects with old shim files (mitigate: migration handles upgrade path)
- Some agent may have custom command files that don't match the `spec-kitty.*` pattern (mitigate: rewrite only touches `spec-kitty.*` files)

## Reviewer Guidance

- Verify all 7 CLI-driven command mappings are correct (T012 mapping table)
- Check that `accept` resolution doesn't require WP context (it's feature-level)
- Confirm all deleted files have no remaining importers (grep check in T014)
- Test migration against a project with existing shim-based files

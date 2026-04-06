---
work_package_id: WP05
title: Command Ergonomics for External Agents
dependencies: []
requirement_refs:
- FR-011
- FR-012
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T026, T027, T028, T029, T030, T031, T032, T033]
history:
- at: '2026-04-06T13:45:48+00:00'
  actor: claude
  action: Created WP05 prompt during /spec-kitty.tasks
authoritative_surface: src/specify_cli/context/
execution_mode: code_change
owned_files:
- src/specify_cli/context/middleware.py
- src/specify_cli/context/store.py
- src/specify_cli/shims/generator.py
- src/specify_cli/core/paths.py
- src/specify_cli/cli/commands/validate_tasks.py
- src/specify_cli/cli/commands/validate_encoding.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/cli/commands/research.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/missions/software-dev/command-templates/tasks.md
- tests/context/test_middleware.py
- tests/context/test_store.py
- tests/shims/test_generator.py
- tests/core/test_paths.py
---

# WP05 — Command Ergonomics for External Agents

## Objective

Fix all generated command guidance so that `--mission <slug>` is present wherever required. Fix inconsistent flag naming (`--feature` vs `--mission`) in error messages. Improve error messages with complete, copy-pasteable examples. Audit all task-related command templates for missing mission context.

This WP addresses issue #434 (agents fail on first try due to missing --feature/--mission guidance).

## Context

### Current State

Three sources of confusion cause first-try agent failures:

1. **Error messages use wrong flag name**: `context/middleware.py:100` and `context/store.py:65` say `--feature <feature>` but the CLI parameter is `--mission <slug>`

2. **Shim templates lack guidance**: `shims/generator.py:53-76` generates a bare `$ARGUMENTS` placeholder with no hint about required flags. Agents receive no guidance on what arguments to include.

3. **Template examples omit --mission**: The tasks command template at `tasks.md:52-58` shows `context resolve` without `--mission`. Agents copy-paste the example and immediately fail.

The `require_explicit_feature()` function at `core/paths.py:273-339` does generate a helpful error message listing available features, but the error only appears AFTER the agent has already failed.

### Target State

- All error messages use `--mission` (matching the CLI parameter)
- Shim templates include guidance about `--mission <slug>`
- All command examples in task-related templates include `--mission <slug>`
- Error messages include a complete, copy-pasteable example command
- Agents succeed on the first try when following generated guidance

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`
- To start implementation: `spec-kitty implement WP05`

---

## Subtask T026: Fix --feature to --mission in middleware.py

**Purpose**: Error message in context middleware uses the wrong flag name (FR-012).

**Steps**:

1. In `src/specify_cli/context/middleware.py` at line 100, change:
   ```python
   "Run `spec-kitty agent context resolve --wp <WP> --feature <feature>` first, "
   ```
   to:
   ```python
   "Run `spec-kitty agent context resolve --wp <WP> --mission <slug>` first, "
   ```

2. Verify no other occurrences of `--feature` in this file.

**Files**: `src/specify_cli/context/middleware.py`

**Validation**: Error message contains `--mission`, not `--feature`.

---

## Subtask T027: Fix --feature to --mission in store.py

**Purpose**: Error message in context store uses the wrong flag name (FR-012).

**Steps**:

1. In `src/specify_cli/context/store.py` at line 65, change:
   ```python
   "Run `spec-kitty agent context resolve --wp <WP> --feature <feature>` "
   ```
   to:
   ```python
   "Run `spec-kitty agent context resolve --wp <WP> --mission <slug>` "
   ```

2. Verify no other occurrences of `--feature` in this file.

**Files**: `src/specify_cli/context/store.py`

**Validation**: Error message contains `--mission`, not `--feature`.

---

## Subtask T028: Add --mission Hint to Shim Template

**Purpose**: Generated shim files should tell agents that `--mission <slug>` is required for mission-scoped commands (FR-011).

**Steps**:

1. In `src/specify_cli/shims/generator.py`, modify the `generate_shim_content` function (lines 53-76).

   **Current**:
   ```python
   return (
       f"<!-- spec-kitty-command-version: {version} -->\n"
       "Run this exact command and treat its output as authoritative.\n"
       "Do not rediscover context from branches, files, or prompt contents.\n"
       "\n"
       f'`spec-kitty agent shim {command} --agent {agent_name} --raw-args "{arg_placeholder}"`\n'
   )
   ```

   **Updated**:
   ```python
   return (
       f"<!-- spec-kitty-command-version: {version} -->\n"
       "Run this exact command and treat its output as authoritative.\n"
       "Do not rediscover context from branches, files, or prompt contents.\n"
       "In repos with multiple missions, pass --mission <slug> in your arguments.\n"
       "\n"
       f'`spec-kitty agent shim {command} --agent {agent_name} --raw-args "{arg_placeholder}"`\n'
   )
   ```

2. This change will take effect for newly generated shims. Existing shims will be updated on next `spec-kitty upgrade` via the standard migration path.

**Files**: `src/specify_cli/shims/generator.py`

**Validation**: `generate_shim_content("tasks", "claude", "$ARGUMENTS")` includes "--mission" guidance.

---

## Subtask T029: Fix Tasks Template Context Resolve Example

**Purpose**: The tasks command template must show `--mission <slug>` in its context resolve example (FR-011).

**Steps**:

1. In `src/specify_cli/missions/software-dev/command-templates/tasks.md`, find the context resolution section (around lines 52-58).

   **Current** (approximately):
   ```markdown
   ```bash
   spec-kitty agent context resolve --action tasks --json
   ```
   ```

   **Updated**:
   ```markdown
   ```bash
   spec-kitty agent context resolve --action tasks --mission <mission-slug> --json
   ```
   ```

2. Ensure all other command examples in this template also include `--mission`. This is covered by T030 (audit), but the context resolve example is the most critical fix.

**Files**: `src/specify_cli/missions/software-dev/command-templates/tasks.md`

**Validation**: The context resolve example in the template includes `--mission <mission-slug>`.

---

## Subtask T030: Audit All Template Command Examples

**Purpose**: Every `spec-kitty agent` command example that requires mission context must include `--mission <slug>` (FR-011).

**Steps**:

1. Search all command template files for `spec-kitty agent` invocations:
   ```bash
   grep -rn "spec-kitty agent" src/specify_cli/missions/*/command-templates/
   ```

2. For each match, check whether the command requires `--mission` (it does if it calls any function that uses `require_explicit_feature()`).

3. Commands that need `--mission`:
   - `spec-kitty agent context resolve --action <X>`
   - `spec-kitty agent mission check-prerequisites`
   - `spec-kitty agent mission finalize-tasks`
   - `spec-kitty agent mission setup-plan`
   - `spec-kitty agent tasks mark-status`
   - `spec-kitty agent tasks finalize-tasks`
   - `spec-kitty agent tasks map-requirements`

4. For each matching example that's missing `--mission`, add it. Use the pattern `--mission <mission-slug>` as a placeholder.

5. Also check other template directories:
   - `src/specify_cli/missions/software-dev/command-templates/implement.md`
   - `src/specify_cli/missions/software-dev/command-templates/review.md`
   - `src/specify_cli/missions/software-dev/command-templates/plan.md`
   - `src/specify_cli/missions/software-dev/command-templates/specify.md`

**Files**: Multiple template files under `src/specify_cli/missions/`

**Validation**: `grep -c "spec-kitty agent.*--json" <template>` shows no examples without `--mission` for commands that need it.

---

## Subtask T031: Improve require_explicit_feature Error Message

**Purpose**: Error message should include a complete, copy-pasteable command example (FR-013).

**Steps**:

1. In `src/specify_cli/core/paths.py` lines 333-339, improve the example command:

   **Current**:
   ```python
   msg = (
       f"Mission slug is required. Provide it explicitly: {flag}\n"
       "No auto-detection is performed (branch scanning / env vars removed).\n"
       f"{available}"
       f"Example: spec-kitty ... {flag.split()[0]} {example_slug}"
   )
   ```

   **Updated**:
   ```python
   flag_name = flag.split()[0]  # e.g., "--mission"
   msg = (
       f"Mission slug is required. Provide it explicitly: {flag}\n"
       "No auto-detection is performed (branch scanning / env vars removed).\n"
       f"{available}"
       f"Example:\n"
       f"  spec-kitty agent context resolve --action tasks {flag_name} {example_slug} --json\n"
       f"  spec-kitty agent mission finalize-tasks {flag_name} {example_slug} --json"
   )
   ```

2. The example should use a real command agents frequently need, not just `spec-kitty ...`.

**Files**: `src/specify_cli/core/paths.py`

**Validation**: Error message includes two complete, copy-pasteable commands.

---

## Subtask T032: Write Regression Tests

**Purpose**: Cover all WP05 changes with targeted tests.

**Tests to add/modify**:

1. **`tests/context/test_middleware.py`** (new or modify):
   - `test_missing_context_error_uses_mission_flag`: error message contains `--mission`, not `--feature`

2. **`tests/context/test_store.py`** (new or modify):
   - `test_missing_token_error_uses_mission_flag`: error message contains `--mission`, not `--feature`

3. **`tests/shims/test_generator.py`** (new or modify):
   - `test_shim_content_mentions_mission`: output includes `--mission` guidance
   - `test_shim_content_version_marker`: existing test still passes

4. **`tests/core/test_paths.py`** (new or modify):
   - `test_require_explicit_feature_error_has_complete_example`: error includes full command
   - `test_require_explicit_feature_uses_real_slug`: error example uses first available slug

5. **Template content test** (can be a simple file-read assertion):
   - `test_tasks_template_context_resolve_has_mission`: tasks.md template example includes `--mission`
   - `test_all_template_agent_commands_have_mission`: scan all templates, assert `--mission` present on commands that need it

**Files**: `tests/context/test_middleware.py`, `tests/context/test_store.py`, `tests/shims/test_generator.py`, `tests/core/test_paths.py`

---

## Subtask T033: Fix --feature command_hint in require_explicit_feature Callers

**Purpose**: Five callers pass `command_hint="--feature <slug>"` to `require_explicit_feature()`, overriding the correct default. This causes error messages to say `--feature` even though the CLI parameter is `--mission` (FR-012).

**Steps**:

1. Update all five callers to use `--mission <slug>`:

   - `src/specify_cli/cli/commands/validate_tasks.py:106`:
     ```python
     mission_slug = require_explicit_feature(feature, command_hint="--mission <slug>")
     ```
   - `src/specify_cli/cli/commands/validate_encoding.py:78`: same change
   - `src/specify_cli/cli/commands/next_cmd.py:59`: same change
   - `src/specify_cli/cli/commands/research.py:58`: same change
   - `src/specify_cli/cli/commands/implement.py:102`: same change

2. Verify no other callers pass `--feature` by grepping:
   ```bash
   grep -rn 'command_hint.*--feature' src/
   ```
   Should return zero results after the fix.

**Files**: `src/specify_cli/cli/commands/validate_tasks.py`, `src/specify_cli/cli/commands/validate_encoding.py`, `src/specify_cli/cli/commands/next_cmd.py`, `src/specify_cli/cli/commands/research.py`, `src/specify_cli/cli/commands/implement.py`

**Validation**: `grep -c 'command_hint.*--feature' src/` returns 0.

---

## Definition of Done

- [ ] All `require_explicit_feature()` callers use `command_hint="--mission <slug>"`, not `--feature`
- [ ] Error messages in middleware.py and store.py use `--mission`, not `--feature`
- [ ] Shim template includes `--mission` guidance
- [ ] Tasks template context resolve example includes `--mission <mission-slug>`
- [ ] All `spec-kitty agent` command examples in templates include `--mission` where required
- [ ] Error message from `require_explicit_feature()` includes complete, copy-pasteable commands
- [ ] All tests pass, mypy --strict clean on changed files

## Reviewer Guidance

- Grep for `--feature` in the codebase to verify no stale references remain in error messages or guidance (legitimate CLI parameter aliases for backward compatibility are OK — only error message text and template examples need fixing)
- Verify the shim template change is a single additional line that doesn't break existing shim detection/migration logic
- Test by running `spec-kitty agent context resolve --action tasks --json` WITHOUT `--mission` — verify the error message now includes complete, correct commands

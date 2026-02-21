# Data Model

## AgentCommand

- **Responsibility**: Represents a Python CLI command in the `spec-kitty agent` namespace, designed for AI agents to call programmatically.
- **Key Fields**:
  - `name` — command name (string, e.g., "create-feature", "workflow", "update-context")
  - `module_path` — Python module location (e.g., "specify_cli.cli.commands.agent.feature")
  - `json_output_supported` — boolean indicating `--json` flag support
  - `help_text` — description for `spec-kitty agent --help`
  - `execution_location` — enum `{main_repo, worktree, either}` indicating where command can run
- **Validations**:
  - `name` MUST follow kebab-case convention
  - `json_output_supported` MUST be `true` for all agent commands
  - `help_text` MUST indicate "for AI agents" to distinguish from user commands
- **State Transitions**:
  - None (commands are stateless)
- **Relationships**:
  - Registered in `AgentCommandRegistry` under `spec-kitty agent` namespace
  - Invoked by `SlashCommandTemplate` via command name
  - Uses `PathResolver` for location-aware path resolution

## PathResolver

- **Responsibility**: Detects execution location (main repository vs worktree) and resolves file paths correctly regardless of where command is executed.
- **Key Fields**:
  - `repo_root` — repository root path (Path object)
  - `execution_context` — enum `{main_repo, worktree, unknown}`
  - `feature_slug` — if in worktree, the feature identifier (e.g., "008-unified-python-cli")
  - `worktree_path` — if in worktree, absolute path to worktree root
  - `kittify_marker_found` — boolean indicating `.kittify/` directory exists
- **Validations**:
  - `repo_root` MUST be a valid directory
  - If `execution_context` is `worktree`, `worktree_path` MUST be under `.worktrees/`
  - MUST handle broken symlinks gracefully
- **State Transitions**:
  - `unknown → main_repo` when `.kittify/` found at current level
  - `unknown → worktree` when `.worktrees/` detected in path hierarchy
- **Relationships**:
  - Used by all `AgentCommand` instances
  - References `RepositoryConfig` for validation rules

## SlashCommandTemplate

- **Responsibility**: Markdown file in `.claude/commands/` that defines an agent workflow by referencing `AgentCommand` instances.
- **Key Fields**:
  - `command_name` — slash command identifier (string, e.g., "spec-kitty.implement")
  - `template_path` — file path to .md template (e.g., ".claude/commands/spec-kitty.implement.md")
  - `agent_commands_referenced` — list of `AgentCommand` names invoked in template
  - `migration_status` — enum `{bash_based, python_based, mixed}` indicating migration state
- **Validations**:
  - `template_path` MUST exist
  - All `agent_commands_referenced` MUST exist in `AgentCommandRegistry`
  - After migration, `migration_status` MUST equal `python_based`
- **State Transitions**:
  - `bash_based → python_based` during `UpgradeMigration` execution
  - `mixed → python_based` after manual migration (for custom modifications)
- **Relationships**:
  - References multiple `AgentCommand` instances
  - Updated by `UpgradeMigration` during project upgrade
  - Executed by AI agents as part of feature workflow

## UpgradeMigration

- **Responsibility**: Migration script that transforms existing spec-kitty projects from bash-based to Python CLI-based architecture.
- **Key Fields**:
  - `migration_version` — semantic version (e.g., "0.10.0")
  - `bash_scripts_detected` — list of bash script paths found in `.kittify/scripts/bash/`
  - `templates_updated` — list of `SlashCommandTemplate` instances modified
  - `custom_modifications_found` — list of bash scripts with custom changes (cannot auto-migrate)
  - `idempotent_execution_count` — number of times migration has run (for safety)
- **Validations**:
  - `migration_version` MUST be tracked in migration registry
  - `bash_scripts_detected` MUST all be removed after migration
  - `custom_modifications_found` MUST generate warnings for user
  - Safe to run multiple times (idempotent)
- **State Transitions**:
  - `not_run → in_progress` when migration starts
  - `in_progress → completed` when all templates updated and bash scripts removed
  - `completed → completed` on subsequent runs (idempotent)
- **Relationships**:
  - Updates all `SlashCommandTemplate` instances in project
  - Removes `BashScript` instances from project
  - References `ProjectConfig` for project-specific paths

## BashScript

- **Responsibility**: Legacy bash script file that will be eliminated during migration.
- **Key Fields**:
  - `script_path` — file path (e.g., ".kittify/scripts/bash/create-new-feature.sh")
  - `script_type` — enum `{wrapper, utility, ci_workflow}` based on functionality
  - `python_equivalent` — corresponding `AgentCommand` name after migration
  - `custom_modified` — boolean indicating user customization (blocks auto-migration)
  - `line_count` — number of lines (for elimination metrics)
- **Validations**:
  - `script_path` MUST exist before migration
  - `script_path` MUST NOT exist after migration
  - If `custom_modified` is `true`, migration MUST warn user
- **State Transitions**:
  - `active → deprecated` during migration announcement
  - `deprecated → removed` after migration completes
- **Relationships**:
  - Replaced by `AgentCommand` during migration
  - Removed by `UpgradeMigration` process
  - May be referenced by `SlashCommandTemplate` (requires template update)

## WorktreeContext

- **Responsibility**: Represents git worktree location where agents may execute commands, requiring automatic path resolution.
- **Key Fields**:
  - `worktree_path` — absolute path to worktree (e.g., ".worktrees/008-unified-python-cli")
  - `feature_slug` — feature identifier extracted from worktree path
  - `feature_dir` — path to feature spec directory within worktree
  - `symlinks_present` — boolean indicating if symlinks exist (vs file copies)
  - `bash_scripts_copied` — list of bash scripts copied to worktree (legacy, removed after migration)
- **Validations**:
  - `worktree_path` MUST be under `.worktrees/`
  - `feature_dir` MUST follow pattern `kitty-specs/<feature-slug>/`
  - After migration, `bash_scripts_copied` MUST be empty list
- **State Transitions**:
  - `not_initialized → initialized` when worktree created
  - `initialized → cleaned` after migration removes bash script copies
- **Relationships**:
  - Detected by `PathResolver` to determine execution context
  - Contains `FeatureSpec` directory
  - Used by `AgentCommand` instances to resolve feature-specific paths

## AgentCommandRegistry

- **Responsibility**: Central registry of all `spec-kitty agent` commands, used for validation and help text generation.
- **Key Fields**:
  - `commands` — dict mapping command name to `AgentCommand` instance
  - `namespaces` — list of command groups (e.g., "feature", "tasks", "context", "release")
  - `cli_version` — spec-kitty version that registered these commands
- **Validations**:
  - All command names MUST be unique
  - Each command MUST have `json_output_supported = true`
  - Help text MUST generate correctly for `spec-kitty agent --help`
- **State Transitions**:
  - None (registry is static after CLI initialization)
- **Relationships**:
  - Contains all `AgentCommand` instances
  - Referenced by Typer CLI for command dispatch
  - Used by `UpgradeMigration` to validate template updates

## RepositoryConfig

- **Responsibility**: Configuration and metadata for spec-kitty project repository.
- **Key Fields**:
  - `repo_root` — repository root directory
  - `kittify_dir` — path to `.kittify/` directory
  - `worktrees_dir` — path to `.worktrees/` directory
  - `migration_version` — current migration version applied to project
  - `platform` — enum `{windows, macos, linux}` for platform-specific behavior
- **Validations**:
  - `repo_root` MUST contain `.kittify/` directory
  - `migration_version` MUST be tracked in migration history
  - On Windows, symlink support MUST fall back to file copy
- **State Transitions**:
  - `pre_migration → post_migration` when `UpgradeMigration` completes
- **Relationships**:
  - Referenced by `PathResolver` for path resolution rules
  - Updated by `UpgradeMigration` to track migration version
  - Contains `WorktreeContext` instances for each feature worktree

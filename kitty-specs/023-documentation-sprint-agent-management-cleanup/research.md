# Research Findings: Documentation Sprint

**Feature**: 023-documentation-sprint-agent-management-cleanup
**Date**: 2026-01-23

## Research Summary

This documentation feature requires minimal research as all information exists in the current codebase. Research focused on validating source files and confirming architectural context.

## R1: Agent Config Command Signatures

**Source**: `src/specify_cli/cli/commands/agent/config.py` (382 lines)

### Command Structure

```
spec-kitty agent config [OPTIONS] COMMAND [ARGS]...
├── list     - List configured agents and their status
├── add      - Add agents to the project
├── remove   - Remove agents from the project
├── status   - Show which agents are configured vs present on filesystem
└── sync     - Sync filesystem with config.yaml
```

### Command Details

**`list` (lines 39-76)**:
- No arguments
- Output: Configured agents with ✓/⚠ status, available unconfigured agents
- Implementation: Reads `AgentConfig`, checks filesystem, displays with Rich Console

**`add <agents>` (lines 78-157)**:
- Arguments: Space-separated agent keys (e.g., `claude codex`)
- Validation: Checks against `AGENT_DIR_TO_KEY.values()`
- Side effects:
  - Creates agent directories with `mkdir(parents=True)`
  - Copies mission templates from `.kittify/missions/software-dev/command-templates/`
  - Updates `config.yaml` via `save_agent_config()`
- Error handling: Invalid keys show list of valid agents, raises `typer.Exit(1)`

**`remove <agents>` (lines 159-228)**:
- Arguments: Space-separated agent keys
- Options: `--keep-config` (keep in config but delete directory)
- Side effects:
  - Deletes entire agent root directory (e.g., `.claude/`)
  - Removes from `config.yaml` unless `--keep-config`
- Error handling: Already removed shows dim message, continues

**`status` (lines 230-295)**:
- No arguments
- Output: Rich Table with columns (Agent Key, Directory, Configured, Exists, Status)
- Status values: "OK" (green), "Missing" (yellow), "Orphaned" (red), "Not used" (dim)
- Orphaned detection: Present on filesystem but not in `config.available`
- Actionable message if orphaned found: `spec-kitty agent config sync --remove-orphaned`

**`sync` (lines 297-380)**:
- Options:
  - `--create-missing` (default: False) - Create dirs for configured agents
  - `--remove-orphaned` / `--keep-orphaned` (default: remove) - Handle orphaned dirs
- Default behavior: Remove orphaned only
- Side effects:
  - Deletes orphaned directories with `shutil.rmtree()`
  - Creates missing directories with mission templates (if `--create-missing`)

### Output Formatting

- Uses `rich.console.Console` for colored output
- Uses `rich.table.Table` for status display
- Status indicators: ✓ (green checkmark), ⚠ (yellow warning), ✗ (red x), • (dim bullet)
- Color scheme: cyan (info), green (success), yellow (warning), red (error), dim (inactive)

**Decision**: Document exact syntax, flags, defaults, and output format in CLI reference.

## R2: AgentConfig Schema

**Source**: `src/specify_cli/orchestrator/agent_config.py` (lines 46-108)

### DataClass Definitions

```python
@dataclass
class AgentSelectionConfig:
    strategy: SelectionStrategy = SelectionStrategy.PREFERRED
    implementer_agent: str | None = None
    reviewer_agent: str | None = None

@dataclass
class AgentConfig:
    available: list[str] = field(default_factory=list)
    selection: AgentSelectionConfig = field(default_factory=AgentSelectionConfig)
```

### YAML Structure

```yaml
agents:
  available:
    - claude
    - codex
    - opencode
  selection:
    strategy: preferred  # or "random"
    implementer_agent: claude
    reviewer_agent: codex
```

### Configuration Behavior

- **Empty `available` list**: Falls back to all 12 agents (legacy behavior)
- **Missing config.yaml**: Falls back to all 12 agents with warning
- **Corrupt YAML**: Falls back to all 12 agents with error message
- **Selection strategy**: Used by orchestrator for multi-agent workflows (not in scope for this doc feature)

**Decision**: Document config.yaml structure in how-to guide and configuration reference. Note fallback behavior for troubleshooting.

## R3: Agent Directory Mappings

**Source**: `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`

### Complete Agent List (12 agents)

| Agent Key | Agent Root Directory | Subdirectory | Full Path | Notes |
|-----------|---------------------|--------------|-----------|-------|
| `claude` | `.claude` | `commands` | `.claude/commands/` | Standard |
| `codex` | `.codex` | `prompts` | `.codex/prompts/` | Standard |
| `gemini` | `.gemini` | `commands` | `.gemini/commands/` | Standard |
| `cursor` | `.cursor` | `commands` | `.cursor/commands/` | Standard |
| `qwen` | `.qwen` | `commands` | `.qwen/commands/` | Standard |
| `opencode` | `.opencode` | `command` | `.opencode/command/` | Singular "command" |
| `windsurf` | `.windsurf` | `workflows` | `.windsurf/workflows/` | Workflows not commands |
| `kilocode` | `.kilocode` | `workflows` | `.kilocode/workflows/` | Workflows not commands |
| `roo` | `.roo` | `commands` | `.roo/commands/` | Standard |
| `copilot` | `.github` | `prompts` | `.github/prompts/` | **Special: GitHub directory** |
| `auggie` | `.augment` | `commands` | `.augment/commands/` | **Special: Key ≠ directory** |
| `q` | `.amazonq` | `prompts` | `.amazonq/prompts/` | **Special: Short key, full directory** |

### Special Cases Explained

- **copilot → .github**: GitHub Copilot uses the standard `.github/prompts/` directory
- **auggie → .augment**: Shorter config key for Augment Code agent
- **q → .amazonq**: Minimal key for Amazon Q agent (full branding in directory)

### AGENT_DIR_TO_KEY Mapping

```python
AGENT_DIR_TO_KEY = {
    ".claude": "claude",
    ".codex": "codex",
    ".gemini": "gemini",
    ".cursor": "cursor",
    ".qwen": "qwen",
    ".opencode": "opencode",
    ".windsurf": "windsurf",
    ".kilocode": "kilocode",
    ".roo": "roo",
    ".github": "copilot",      # Special mapping
    ".augment": "auggie",      # Special mapping
    ".amazonq": "q",           # Special mapping
}
```

**Decision**: Create comprehensive mapping table in how-to guide, clearly marking special cases.

## R4: Jujutsu Reference Audit

**Method**:
```bash
grep -r "jujutsu\|jj\s\|\.jj" docs/ | grep -v ".jj/" | grep -v "jjust"
```

**Findings**: (To be validated during implementation)

Expected result: Zero matches, as commit 99b0d84 removed all jujutsu documentation:
- `docs/explanation/auto-rebase-and-conflicts.md` (deleted)
- `docs/explanation/jujutsu-for-multi-agent.md` (deleted)
- `docs/how-to/handle-conflicts-jj.md` (deleted)
- `docs/how-to/use-operation-history.md` (deleted)
- `docs/tutorials/jujutsu-workflow.md` (deleted)

**Potential lingering references** (to check):
- VCS detection order in `docs/reference/cli-commands.md` (init command documentation)
- Cross-references in other how-to guides
- Explanation articles mentioning VCS options
- Tutorial examples showing jj commands

**Decision**: If any jj references found, list them in tasks for removal. Update VCS detection docs to reflect git-only behavior.

## R5: ADR #6 Migration Context

**Source**: `architecture/adrs/2026-01-23-6-config-driven-agent-management.md`

### Key Points for Migration Guide

**Problem** (Pre-0.12.0):
- Migrations hardcoded all 12 agents in `AGENT_DIRS` list
- Ignored `.kittify/config.yaml` agent selection
- Recreated deleted agent directories on every upgrade
- User workflow broken: Delete directories → Run upgrade → Directories recreated

**Solution** (0.12.0+):
- `.kittify/config.yaml` is single source of truth for agent configuration
- Migrations use `get_agent_dirs_for_project()` helper (respects config)
- If directory doesn't exist, migrations skip it (respect deletions)
- New CLI commands: `spec-kitty agent config {list|add|remove|status|sync}`

**Migration Workflow**:
1. Use `spec-kitty agent config remove` to delete unwanted agents
2. Config is updated atomically (directory + config.yaml)
3. Future upgrades respect config (no recreation)

**Architectural Changes**:
- Centralized `AGENT_DIRS` in `m_0_9_1_complete_lane_migration.py`
- Config-aware migration pattern (all 8 migrations updated)
- Fallback for legacy projects: Empty config → all 12 agents

**Testing**:
- Unit tests: 20 tests in `tests/specify_cli/cli/commands/test_agent_config.py`
- Integration tests: 11 tests in `tests/specify_cli/test_agent_config_migration.py`

**Decision**: Summarize problem/solution in migration guide. Link to ADR #6 for full architectural context. Focus on user workflow (remove command) not implementation details.

## Findings Consolidation

### No NEEDS CLARIFICATION Items

All information required for documentation is available in:
- Source code (command implementations, dataclasses)
- ADR #6 (architectural context)
- Git history (jujutsu removal confirmation)
- Existing project structure (config.yaml examples)

### Documentation Strategy Confirmed

**Code-First Validation**:
- Read source files directly to extract signatures
- Compare documented syntax against `--help` output
- Verify config schema matches dataclass definitions
- Grep for jujutsu references to confirm cleanup

**No Automation Tooling**:
- Manual inspection sufficient for documentation feature
- Source files are readable and well-commented
- CLI help text is authoritative source

### Ready for Phase 1

All research complete. Implementing agent can proceed with:
1. Creating how-to guide using research findings
2. Updating CLI reference with exact command syntax
3. Writing migration guide with ADR #6 context
4. Auditing and fixing jujutsu references
5. Cross-referencing agent config from related docs

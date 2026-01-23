# WP01 Research Findings: Agent Config Command Signatures and Data Structures

**Purpose**: Complete extraction of command signatures, config schema, and agent mappings from source code for use in documentation work (WP02-WP08).

**Date**: 2026-01-23
**Source Commit**: b74536b (or current workspace state)

---

## Table of Contents

1. [Command Signatures (T001)](#t001-command-signatures)
2. [Config Schema (T002)](#t002-config-schema)
3. [Agent Mappings (T003)](#t003-agent-mappings)

---

## T001: Command Signatures

**Source**: `src/specify_cli/cli/commands/agent/config.py` (382 lines)

### Parent Command

```bash
spec-kitty agent config [OPTIONS] COMMAND [ARGS]...
```

**Help text**: "Manage project AI agent configuration (add, remove, list agents)"

**Defined at**: Lines 24-28

**Subcommands**: 5 total (list, add, remove, status, sync)

---

### Subcommand: `list`

**Function**: `list_agents()` (lines 39-76)

**Signature**:
```bash
spec-kitty agent config list
```

**Arguments**: None

**Options**: None

**Output Format**:
```
Configured agents:
  ✓ opencode (.opencode/command/)
  ✓ claude (.claude/commands/)
  ⚠ codex (.codex/prompts/) <-- missing from filesystem

Available but not configured:
  - gemini
  - cursor
  ...
```

**Status Indicators**:
- `✓` (green checkmark) - Agent configured AND directory exists
- `⚠` (yellow warning) - Agent configured but directory missing
- `✗` (red x) - Unknown agent (not in AGENT_DIR_TO_KEY mapping)

**Implementation Notes**:
- Loads `AgentConfig` via `load_agent_config(repo_root)` (line 49)
- Checks filesystem with `agent_path.exists()` (line 63)
- Displays with `rich.console.Console` (line 29, 57-66)
- Shows "No agents configured" if `config.available` is empty (lines 51-54)
- Lists unconfigured agents from `AGENT_DIR_TO_KEY.values()` (lines 69-75)

**Error Handling**:
- Repository not found: Displays `"[red]Error:[/red] {e}"` and exits with code 1 (lines 44-46)

---

### Subcommand: `add`

**Function**: `add_agents(agents: List[str])` (lines 78-157)

**Signature**:
```bash
spec-kitty agent config add <agent_key>... [OPTIONS]
```

**Arguments**:
- `agents` (required, variadic): Space-separated agent keys (e.g., `claude codex gemini`)
- Help text: "Agent keys to add (e.g., claude codex)" (line 80)

**Options**: None

**Example**:
```bash
spec-kitty agent config add claude codex
```

**Side Effects**:
1. Creates agent directory structure: `agent_dir.mkdir(parents=True, exist_ok=True)` (line 126)
2. Copies templates from `.kittify/missions/software-dev/command-templates/*.md` to `{agent_dir}/spec-kitty.{template_name}` (lines 130-135)
3. Updates `config.yaml` via `save_agent_config(repo_root, config)` (line 146)

**Output Messages**:
- Success: `"[green]✓[/green] Added {agent_root}/{subdir}/"` (line 139)
- Already configured: `"\n[dim]Already configured:[/dim] {', '.join(already_configured)}"` (lines 149-150)
- Updated config: `"\n[cyan]Updated config.yaml:[/cyan] added {', '.join(added)}"` (line 147)

**Error Handling**:
- **Invalid agent keys**: Validates against `AGENT_DIR_TO_KEY.values()` (line 99)
  - Message: `"[red]Error:[/red] Invalid agent keys: {', '.join(invalid)}"` (line 101)
  - Shows valid agents: `"\nValid agents: {', '.join(sorted(AGENT_DIR_TO_KEY.values()))}"` (line 102)
  - Exits with code 1 (line 103)
- **OSError during mkdir/copy**: Appends to errors list, displays at end (lines 141-142, 152-156)
- **Already configured**: Skips agent, shows in summary (lines 111-113, 149-150)

**Implementation Notes**:
- Builds list of added, already_configured, and errors (lines 105-107)
- Only saves config if at least one agent added (line 145)
- Template copy is conditional on missions_dir existence (line 132)

---

### Subcommand: `remove`

**Function**: `remove_agents(agents: List[str], keep_config: bool)` (lines 159-228)

**Signature**:
```bash
spec-kitty agent config remove <agent_key>... [OPTIONS]
```

**Arguments**:
- `agents` (required, variadic): Space-separated agent keys to remove

**Options**:
- `--keep-config` (default: `False`) - Keep agent in config.yaml but delete directory
  - Type: `bool`
  - Lines: 162-166
  - Help text: "Keep in config.yaml but delete directory"

**Example**:
```bash
spec-kitty agent config remove codex gemini
spec-kitty agent config remove codex --keep-config
```

**Side Effects**:
1. Deletes entire agent root directory: `shutil.rmtree(agent_path)` (line 207)
2. Removes from `config.yaml` unless `--keep-config` (lines 216-217)
3. Saves updated config via `save_agent_config()` (line 221)

**Output Messages**:
- Success: `"[green]✓[/green] Removed {agent_root}/"` (line 209)
- Already removed: `"[dim]• {agent_root}/ already removed[/dim]"` (line 213)
- Updated config: `"\n[cyan]Updated config.yaml:[/cyan] removed {', '.join(removed)}"` (line 222)

**Error Handling**:
- **Invalid agent keys**: Same validation as `add` (lines 185-189)
- **OSError during rmtree**: Appends to errors list, displays as warnings (lines 210-211, 224-227)
- **Already removed**: Shows dim message, doesn't error (line 213)

**Implementation Notes**:
- Deletes entire agent root (e.g., `.claude/`), not just subdir (line 204, 207)
- Config update conditional on `not keep_config` (line 220)
- Errors displayed as `[yellow]Warnings:[/yellow]` not errors (line 225)

---

### Subcommand: `status`

**Function**: `agent_status()` (lines 230-295)

**Signature**:
```bash
spec-kitty agent config status
```

**Arguments**: None

**Options**: None

**Output Format**: Rich Table with 5 columns

**Table Structure** (lines 249-254):
```
┌─────────────────────────────────────────────────────────────────────┐
│                          Agent Status                               │
├─────────────┬──────────────┬────────────┬────────┬──────────────────┤
│ Agent Key   │ Directory    │ Configured │ Exists │ Status           │
│ (cyan)      │ (dim)        │ (center)   │(center)│                  │
├─────────────┼──────────────┼────────────┼────────┼──────────────────┤
│ claude      │.claude/cmds/ │     ✓      │   ✓    │ OK (green)       │
│ codex       │.codex/prompts│     ✓      │   ✗    │ Missing (yellow) │
│ gemini      │.gemini/cmds/ │     ✗      │   ✓    │ Orphaned (red)   │
│ cursor      │.cursor/cmds/ │     ✗      │   ✗    │ Not used (dim)   │
└─────────────┴──────────────┴────────────┴────────┴──────────────────┘

⚠ 1 orphaned directories found (present but not configured)
Run 'spec-kitty agent config sync --remove-orphaned' to clean up
```

**Status Values** (lines 269-276):
- `[green]OK[/green]` - Configured AND exists (line 270)
- `[yellow]Missing[/yellow]` - Configured but NOT exists (line 272)
- `[red]Orphaned[/red]` - NOT configured but exists (line 274)
- `[dim]Not used[/dim]` - NOT configured AND NOT exists (line 276)

**Orphaned Detection** (lines 283-286):
```python
orphaned = [
    key
    for key in all_agent_keys
    if key not in config.available and (repo_root / KEY_TO_AGENT_DIR[key][0]).exists()
]
```

**Actionable Message** (lines 289-294):
- Shown if any orphaned directories found
- Message: `"[yellow]⚠ {len(orphaned)} orphaned directories found[/yellow] (present but not configured)"`
- Suggestion: `"Run 'spec-kitty agent config sync --remove-orphaned' to clean up"`

**Implementation Notes**:
- Iterates over ALL agents in `AGENT_DIR_TO_KEY.values()` (sorted) (line 256)
- Uses Rich Table for formatted output (lines 249-280)
- Check exists uses subdir path: `repo_root / agent_root / subdir` (line 264)

---

### Subcommand: `sync`

**Function**: `sync_agents(create_missing: bool, remove_orphaned: bool)` (lines 297-380)

**Signature**:
```bash
spec-kitty agent config sync [OPTIONS]
```

**Arguments**: None

**Options**:
- `--create-missing` (default: `False`) - Create directories for configured agents that are missing
  - Type: `bool`
  - Lines: 299-302
  - Help text: "Create directories for configured agents that are missing"
- `--remove-orphaned` / `--keep-orphaned` (default: `True` / remove)
  - Type: `bool`
  - Lines: 304-307
  - Help text: "Remove directories for agents not in config"

**Default Behavior**: Removes orphaned directories only (line 305: `True`)

**Example**:
```bash
spec-kitty agent config sync                    # Remove orphaned only
spec-kitty agent config sync --create-missing    # Remove orphaned + create missing
spec-kitty agent config sync --keep-orphaned     # Do nothing (both disabled)
```

**Side Effects**:
1. **Remove orphaned** (if enabled):
   - Deletes orphaned agent root directories: `shutil.rmtree(agent_path)` (line 341)
   - Message: `"  [green]✓[/green] Removed orphaned {agent_root}/"` (line 342)
2. **Create missing** (if enabled):
   - Creates missing agent directories with templates (lines 362-369)
   - Same template copy logic as `add` command
   - Message: `"  [green]✓[/green] Created {agent_root}/{subdir}/"` (line 371)

**Output Messages**:
- Phase headers:
  - `"[cyan]Checking for orphaned directories...[/cyan]"` (line 328)
  - `"\n[cyan]Checking for missing directories...[/cyan]"` (line 349)
- Success: `"\n[green]✓ Sync complete[/green]"` (line 379)
- No changes: `"[dim]No changes needed - filesystem matches config[/dim]"` (line 377)

**Error Handling**:
- **OSError during rmtree**: Displays `"  [red]✗[/red] Failed to remove {agent_root}/: {e}"` (line 345)
- **OSError during mkdir/copy**: Displays `"  [red]✗[/red] Failed to create {agent_root}/{subdir}/: {e}"` (line 374)
- **Unknown agent**: Shows `"  [yellow]⚠[/yellow] Unknown agent: {agent_key}"` (line 355)

**Implementation Notes**:
- Orphaned detection same as `status` command (lines 330-334)
- Template source: `.kittify/missions/software-dev/command-templates/` (line 350)
- Only saves config if changes made (implicit - no config update in sync)
- Changes tracked with `changes_made` flag (line 324)

---

### Common Error Handling Patterns

**Repository Root Not Found**:
- Used in: ALL commands
- Pattern:
  ```python
  try:
      repo_root = find_repo_root()
  except Exception as e:
      console.print(f"[red]Error:[/red] {e}")
      raise typer.Exit(1)
  ```

**Invalid Agent Keys**:
- Used in: `add`, `remove`
- Validation: `invalid = [a for a in agents if a not in AGENT_DIR_TO_KEY.values()]`
- Message: `"[red]Error:[/red] Invalid agent keys: {', '.join(invalid)}"`
- Shows valid agents: `"\nValid agents: {', '.join(sorted(AGENT_DIR_TO_KEY.values()))}"`
- Exits with code 1

---

### Output Formatting Details

**Library**: `rich.console.Console` (imported line 10)

**Colors/Styles**:
- `[cyan]` - Informational messages, headers, file paths
- `[green]` - Success messages, OK status
- `[yellow]` - Warnings, Missing status
- `[red]` - Errors, Orphaned status
- `[dim]` - Informational text, Not used status

**Status Indicators**:
- `✓` - Success, present, configured
- `⚠` - Warning, missing
- `✗` - Error, not present, not configured
- `•` - Informational bullet

**Table Formatting** (status command only):
- Library: `rich.table.Table` (imported line 11)
- Title: "Agent Status"
- Column alignment: center for Configured/Exists, left for others
- Column styles: cyan for Agent Key, dim for Directory

---

## T002: Config Schema

**Source**: `src/specify_cli/orchestrator/agent_config.py` (225 lines)

### Dataclass: `SelectionStrategy`

**Type**: `Enum` (inherits from `str, Enum`)

**Defined at**: Lines 24-28

**Values**:
- `PREFERRED = "preferred"` - Use user-specified preferred agents (line 27)
- `RANDOM = "random"` - Randomly select from available agents (line 28)

**Default**: `PREFERRED`

---

### Dataclass: `AgentSelectionConfig`

**Defined at**: Lines 31-43

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strategy` | `SelectionStrategy` | `SelectionStrategy.PREFERRED` | How to select agents (preferred or random) |
| `preferred_implementer` | `str \| None` | `None` | Agent ID for implementation (if strategy=preferred) |
| `preferred_reviewer` | `str \| None` | `None` | Agent ID for review (if strategy=preferred) |

**Docstring** (lines 33-39):
> Configuration for agent selection.
>
> Attributes:
>     strategy: How to select agents (preferred or random)
>     preferred_implementer: Agent ID for implementation (if strategy=preferred)
>     preferred_reviewer: Agent ID for review (if strategy=preferred)

---

### Dataclass: `AgentConfig`

**Defined at**: Lines 46-56

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `available` | `list[str]` | `field(default_factory=list)` | List of agent IDs that are available for use |
| `selection` | `AgentSelectionConfig` | `field(default_factory=AgentSelectionConfig)` | Configuration for how to select agents |

**Docstring** (lines 48-53):
> Full agent configuration.
>
> Attributes:
>     available: List of agent IDs that are available for use
>     selection: Configuration for how to select agents

**Methods**:
- `select_implementer(exclude: str | None = None) -> str | None` (lines 58-77)
  - Selects agent for implementation
  - Excludes specified agent if provided
  - Returns preferred_implementer if in candidates (PREFERRED strategy)
  - Returns random choice (RANDOM strategy)
  - Falls back to first available if preferred not in candidates
- `select_reviewer(implementer: str | None = None) -> str | None` (lines 79-106)
  - Selects agent for review
  - Prefers different agent than implementer for cross-review
  - Returns preferred_reviewer if in candidates (PREFERRED strategy)
  - Returns random choice (RANDOM strategy)
  - Falls back to same agent if no other available

**Note**: Selection methods are used by orchestrator (not documented in this sprint, per spec.md scope)

---

### YAML Structure

**File Location**: `.kittify/config.yaml`

**Structure**:
```yaml
agents:
  available:
    - claude
    - codex
    - opencode
  selection:
    strategy: preferred  # or "random"
    preferred_implementer: claude
    preferred_reviewer: codex
```

**Minimal Example** (only available agents):
```yaml
agents:
  available:
    - opencode
```

**Full Example** (with selection config):
```yaml
agents:
  available:
    - claude
    - codex
    - gemini
  selection:
    strategy: preferred
    preferred_implementer: claude
    preferred_reviewer: codex
```

---

### Helper Functions

#### `load_agent_config(repo_root: Path) -> AgentConfig`

**Defined at**: Lines 109-159

**Purpose**: Load agent configuration from `.kittify/config.yaml`

**Returns**: `AgentConfig` instance (defaults if not configured)

**Fallback Behavior**:
1. **File not found** (lines 120-122):
   - Logs warning: `"Config file not found: {config_file}"`
   - Returns: `AgentConfig()` (empty available list, default selection)
2. **YAML parse error** (lines 127-132):
   - Logs error: `"Failed to load config: {e}"`
   - Returns: `AgentConfig()` (empty available list, default selection)
3. **No agents section** (lines 134-137):
   - Logs info: `"No agents section in config.yaml"`
   - Returns: `AgentConfig()` (empty available list, default selection)
4. **Invalid strategy** (lines 147-151):
   - Logs warning: `"Invalid strategy '{strategy_str}', defaulting to 'preferred'"`
   - Uses: `SelectionStrategy.PREFERRED`

**Edge Cases**:
- Single agent string converted to list (lines 141-142): `if isinstance(available, str): available = [available]`
- Empty config file: Returns `AgentConfig()` (line 129: `yaml.load(f) or {}`)

**YAML Library**: `ruamel.yaml` with `preserve_quotes = True` (lines 124-125)

---

#### `save_agent_config(repo_root: Path, config: AgentConfig) -> None`

**Defined at**: Lines 162-199

**Purpose**: Save agent configuration to `.kittify/config.yaml`

**Side Effects**:
1. Creates `.kittify/` directory if missing (line 183: `config_dir.mkdir(parents=True, exist_ok=True)`)
2. Merges with existing config (preserves other sections like `vcs`) (lines 178-182)
3. Writes YAML with preserved quotes (line 197)

**Merge Behavior**:
- Loads existing config.yaml if present (lines 178-180)
- Updates only `agents` section (lines 186-193)
- Preserves other top-level keys (e.g., `vcs`, `project`, etc.)

**YAML Output Structure** (lines 186-193):
```yaml
agents:
  available:
    - agent1
    - agent2
  selection:
    strategy: preferred  # value from enum
    preferred_implementer: agent1
    preferred_reviewer: agent2
```

**YAML Library**: `ruamel.yaml` with `preserve_quotes = True` (lines 174-175)

---

#### `get_configured_agents(repo_root: Path) -> list[str]`

**Defined at**: Lines 202-214

**Purpose**: Get DEFINITIVE list of configured agents

**Returns**: List of agent IDs (empty if not configured)

**Implementation**: Calls `load_agent_config(repo_root).available` (line 213)

**Docstring Note** (line 205): "This is the DEFINITIVE list of available agents, set during init."

---

### Fallback Behavior Summary

**Empty `available` list**: Commands like `list` show "No agents configured" (see T001)

**Missing config.yaml**:
- `load_agent_config()` returns `AgentConfig()` (empty available)
- Migrations fall back to ALL 12 agents (see `get_agent_dirs_for_project()` in T003)

**Corrupt YAML**:
- `load_agent_config()` returns `AgentConfig()` (empty available)
- Logs error to logger

**Invalid strategy**:
- Defaults to `SelectionStrategy.PREFERRED`
- Logs warning

---

## T003: Agent Mappings

**Source**: `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`

### Constant: `AGENT_DIRS`

**Defined at**: Lines 53-66 (in `CompleteLaneMigration` class)

**Type**: `list[tuple[str, str]]` - List of (agent_root, subdir) tuples

**Count**: 12 agents total (as of v0.12.0)

**Structure**:
```python
AGENT_DIRS = [
    (".claude", "commands"),
    (".github", "prompts"),       # GitHub Copilot
    (".gemini", "commands"),
    (".cursor", "commands"),
    (".qwen", "commands"),
    (".opencode", "command"),     # NOTE: Singular "command"
    (".windsurf", "workflows"),
    (".codex", "prompts"),
    (".kilocode", "workflows"),
    (".augment", "commands"),
    (".roo", "commands"),
    (".amazonq", "prompts"),
]
```

---

### Constant: `AGENT_DIR_TO_KEY`

**Defined at**: Lines following AGENT_DIRS (extracted via grep)

**Type**: `dict[str, str]` - Mapping from agent root directory to agent key

**Count**: 12 mappings

**Structure**:
```python
AGENT_DIR_TO_KEY = {
    ".claude": "claude",
    ".github": "copilot",    # SPECIAL: Key ≠ directory
    ".gemini": "gemini",
    ".cursor": "cursor",
    ".qwen": "qwen",
    ".opencode": "opencode",
    ".windsurf": "windsurf",
    ".codex": "codex",
    ".kilocode": "kilocode",
    ".augment": "auggie",     # SPECIAL: Key ≠ directory
    ".roo": "roo",
    ".amazonq": "q",          # SPECIAL: Short key, full directory
}
```

---

### Complete Agent Mapping Table

| Agent Key | Agent Root Directory | Subdirectory | Full Path | Notes |
|-----------|---------------------|--------------|-----------|-------|
| `claude` | `.claude` | `commands` | `.claude/commands/` | Standard pattern |
| `copilot` | `.github` | `prompts` | `.github/prompts/` | **SPECIAL: GitHub Copilot uses `.github/` (not `.copilot/`)** |
| `gemini` | `.gemini` | `commands` | `.gemini/commands/` | Standard pattern |
| `cursor` | `.cursor` | `commands` | `.cursor/commands/` | Standard pattern |
| `qwen` | `.qwen` | `commands` | `.qwen/commands/` | Standard pattern |
| `opencode` | `.opencode` | `command` | `.opencode/command/` | **NOTE: Singular "command" (not "commands")** |
| `windsurf` | `.windsurf` | `workflows` | `.windsurf/workflows/` | Uses "workflows" not "commands" |
| `codex` | `.codex` | `prompts` | `.codex/prompts/` | Uses "prompts" not "commands" |
| `kilocode` | `.kilocode` | `workflows` | `.kilocode/workflows/` | Uses "workflows" not "commands" |
| `auggie` | `.augment` | `commands` | `.augment/commands/` | **SPECIAL: Key "auggie" ≠ directory ".augment"** |
| `roo` | `.roo` | `commands` | `.roo/commands/` | Standard pattern |
| `q` | `.amazonq` | `prompts` | `.amazonq/prompts/` | **SPECIAL: Short key "q" maps to ".amazonq" directory** |

---

### Special Cases (Highlighted)

#### 1. GitHub Copilot: `copilot` → `.github/prompts/`

**Why**: GitHub Copilot uses the standard `.github/` directory for GitHub-specific configurations.

**Config key**: `copilot`

**Directory**: `.github/prompts/` (NOT `.copilot/`)

**Impact**: When documenting `spec-kitty agent config add copilot`, users see `.github/` directory created.

---

#### 2. Augment Code: `auggie` → `.augment/commands/`

**Why**: Shorter, friendlier config key for Augment Code agent.

**Config key**: `auggie`

**Directory**: `.augment/commands/` (full branding in directory)

**Impact**: Config uses `auggie`, but filesystem shows `.augment/`.

---

#### 3. Amazon Q: `q` → `.amazonq/prompts/`

**Why**: Minimal key for Amazon Q agent.

**Config key**: `q`

**Directory**: `.amazonq/prompts/` (full branding in directory)

**Impact**: Config uses `q`, but filesystem shows `.amazonq/`.

---

### Subdirectory Patterns

**`commands/` (plural)**: 7 agents
- claude, gemini, cursor, qwen, augment, roo

**`command/` (singular)**: 1 agent
- opencode (NOTE: Deliberate singular form)

**`prompts/`**: 3 agents
- copilot (.github), codex, q (.amazonq)

**`workflows/`**: 2 agents
- windsurf, kilocode

---

### Usage in Migrations

**Helper Function**: `get_agent_dirs_for_project(project_path: Path) -> list[tuple[str, str]]`

**Purpose**: Get agent directories to process based on project config.

**Behavior**:
1. Reads `config.yaml` to determine which agents are enabled (via `get_configured_agents()`)
2. Filters `AGENT_DIRS` to only return configured agents
3. **Fallback**: Returns ALL agents for legacy projects without config.yaml

**Why**: Respects user configuration - migrations only process configured agents (post-0.12.0 ADR #6 behavior).

**Example**:
```python
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project

def apply(self, project_path: Path, dry_run: bool = False):
    # Get only configured agents
    agent_dirs = get_agent_dirs_for_project(project_path)

    for agent_root, subdir in agent_dirs:
        agent_dir = project_path / agent_root / subdir

        # Skip if directory doesn't exist (respect deletions)
        if not agent_dir.exists():
            continue  # DON'T recreate!

        # Process agent...
```

---

### Canonical Reference

**Source of Truth**: `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`

**Constants Used**:
- `CompleteLaneMigration.AGENT_DIRS` - List of (agent_root, subdir) tuples
- `AGENT_DIR_TO_KEY` - Mapping from agent_root to agent key

**Exported**: `__all__ = ["CompleteLaneMigration", "AGENT_DIR_TO_KEY", "get_agent_dirs_for_project"]`

**Note**: When documenting agent commands, ALWAYS reference this file for accurate mappings.

---

## Validation

### Cross-Reference Checks

**CLI Help Output**:
```bash
spec-kitty agent config --help
spec-kitty agent config list --help
spec-kitty agent config add --help
spec-kitty agent config remove --help
spec-kitty agent config status --help
spec-kitty agent config sync --help
```

**Verify Agent Mappings**:
```bash
# In a test project:
spec-kitty agent config add claude
ls -la .claude/commands/
# Should see spec-kitty.*.md files
```

**Verify Config Schema**:
```bash
cat .kittify/config.yaml
# Should match YAML structure documented in T002
```

---

## Summary

### T001 Completeness Checklist

- [x] All 5 subcommands documented (list, add, remove, status, sync)
- [x] All arguments and flags with defaults
- [x] Error handling behavior captured
- [x] Output formatting details (Rich Console, colors, status indicators)
- [x] Side effects documented (mkdir, rmtree, config updates)
- [x] Success and error messages (exact strings)

### T002 Completeness Checklist

- [x] AgentConfig and AgentSelectionConfig fields documented
- [x] YAML structure with example values
- [x] Fallback behavior for empty/missing/corrupt config
- [x] Field types and defaults recorded
- [x] Helper functions (load, save, get_configured_agents)

### T003 Completeness Checklist

- [x] All 12 agent mappings documented
- [x] Special cases highlighted (copilot, auggie, q)
- [x] Subdirectory patterns identified
- [x] Canonical source referenced
- [x] Usage in migrations documented

---

## Next Steps (WP02-WP08)

**WP02**: Use this document to write `list` command documentation without re-reading source.

**WP03**: Use this document to write `add` and `remove` command documentation without re-reading source.

**WP04**: Use this document to write `status` and `sync` command documentation without re-reading source.

**WP05**: Use T002 findings to document config.yaml schema.

**WP07**: Use T003 findings to create agent mapping reference table.

**Validation**: If any WP needs to re-read source files, this research is incomplete.

---

**Research Complete**: 2026-01-23

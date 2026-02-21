---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
title: "Agent Config Command Research"
phase: "Phase 0 - Research & Validation"
lane: "done"
assignee: ""
agent: "Claude"
shell_pid: "18985"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies: []
history:
  - timestamp: "2026-01-23T10:23:45Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Agent Config Command Research

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

**Goal**: Extract command signatures, config schema, and agent mappings from source code to establish validation baseline for documentation work.

**Success Criteria**:

- [ ] All 5 agent config subcommand signatures documented (command name, arguments, flags, defaults)
- [ ] AgentConfig and AgentSelectionConfig dataclass schemas extracted with field names and types
- [ ] All 12 agent keys and directory mappings documented (including 3 special cases)
- [ ] Error handling behavior identified for each command
- [ ] Output formatting details captured (Rich Console, status indicators, table format)

**Independent Test**: Research findings are comprehensive enough that WP02-WP06 can document commands without re-reading source files.

## Context & Constraints

**Purpose**: This is a research work package - gathering information from source code to validate documentation accuracy. No documentation files are written in this WP; findings feed into WP02-WP08.

**Source Files** (read-only inspection):

- `src/specify_cli/cli/commands/agent/config.py` (382 lines) - Command implementations
- `src/specify_cli/orchestrator/agent_config.py` (lines 46-108) - Config dataclasses
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` - Agent mappings

**Reference Documents**:

- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/research.md` (R1-R3 sections provide expected findings)
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/plan.md` (validation strategy)
- `architecture/adrs/2026-01-23-6-config-driven-agent-management.md` (ADR #6 - architectural context)

**Validation Strategy**: Code-first - manually inspect source files and extract exact syntax. No automation scripts created.

**Constraints**:

- Read-only source inspection (no code modifications)
- Document findings in working notes (not formal documentation yet)
- Extract EXACT syntax (don't paraphrase or summarize)

## Subtasks & Detailed Guidance

### Subtask T001 – Extract Command Signatures from agent/config.py

**Purpose**: Document exact command syntax, arguments, flags, defaults, and error handling for all 5 subcommands.

**Steps**:

1. **Open source file**:

   ```bash
   code src/specify_cli/cli/commands/agent/config.py
   ```

   Or use `cat -n` to view with line numbers

2. **Extract command structure** (lines 24-28):
   - Parent command: `spec-kitty agent config [OPTIONS] COMMAND [ARGS]...`
   - Help text: "Manage project AI agent configuration (add, remove, list agents)"
   - 5 subcommands defined via `@app.command(name="...")`

3. **Document `list` subcommand** (lines 39-76):
   - Function: `list_agents()`
   - Arguments: None
   - Options: None
   - Output format:
     - Configured agents with status (✓ = present, ⚠ = missing)
     - Available but not configured agents
   - Implementation: Loads `AgentConfig`, checks filesystem with `agent_path.exists()`, displays with `rich.console.Console`
   - Example output (approximate):

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

4. **Document `add` subcommand** (lines 78-157):
   - Function: `add_agents(agents: List[str])`
   - Arguments: `agents` (space-separated agent keys, e.g., `claude codex gemini`)
   - Options: None
   - Side effects:
     - Creates `agent_dir.mkdir(parents=True, exist_ok=True)` (line 126)
     - Copies templates from `.kittify/missions/software-dev/command-templates/*.md` (lines 133-135)
     - Updates `config.yaml` via `save_agent_config()` (line 146)
   - Error handling:
     - Invalid agent keys: Validates against `AGENT_DIR_TO_KEY.values()` (line 99)
     - Shows error with list of valid agents (lines 101-103)
     - Raises `typer.Exit(1)`
   - Already configured: Skips with message "Already configured: ..." (lines 149-150)
   - Success message: `"✓ Added {agent_root}/{subdir}/"` (line 139)

5. **Document `remove` subcommand** (lines 159-228):
   - Function: `remove_agents(agents: List[str], keep_config: bool)`
   - Arguments: `agents` (space-separated agent keys)
   - Options:
     - `--keep-config` (default: False) - Keep in config.yaml but delete directory (lines 162-166)
   - Side effects:
     - Deletes entire agent root directory with `shutil.rmtree(agent_path)` (line 207)
     - Removes from `config.yaml` unless `--keep-config` (lines 216-217)
   - Error handling:
     - Invalid keys: Same validation as `add` (lines 185-189)
     - Already removed: Shows dim message "• {agent_root}/ already removed" (line 213)
   - Success message: `"✓ Removed {agent_root}/"` (line 209)

6. **Document `status` subcommand** (lines 230-295):
   - Function: `agent_status()`
   - Arguments: None
   - Options: None
   - Output format: Rich Table with columns (lines 249-254):
     - Agent Key (cyan)
     - Directory (dim)
     - Configured (center aligned, ✓/✗)
     - Exists (center aligned, ✓/✗)
     - Status (colored)
   - Status values (lines 269-276):
     - `[green]OK[/green]` - Configured and present
     - `[yellow]Missing[/yellow]` - Configured but not present
     - `[red]Orphaned[/red]` - Not configured but present
     - `[dim]Not used[/dim]` - Neither configured nor present
   - Orphaned detection: `agent_key not in config.available and agent_path.exists()` (lines 283-286)
   - Actionable message if orphaned: `"Run 'spec-kitty agent config sync --remove-orphaned' to clean up"` (line 294)

7. **Document `sync` subcommand** (lines 297-380):
   - Function: `sync_agents(create_missing: bool, remove_orphaned: bool)`
   - Arguments: None
   - Options:
     - `--create-missing` (default: False) - Create directories for configured agents (lines 299-303)
     - `--remove-orphaned` / `--keep-orphaned` (default: True / remove) - Handle orphaned dirs (lines 304-308)
   - Default behavior: Remove orphaned only (line 305)
   - Side effects:
     - Deletes orphaned with `shutil.rmtree()` (line 341)
     - Creates missing with templates (lines 362-369)
   - Success messages:
     - `"✓ Removed orphaned {agent_root}/"` (line 342)
     - `"✓ Created {agent_root}/{subdir}/"` (line 371)
   - No changes: `"No changes needed - filesystem matches config"` (line 377)

8. **Document output formatting**:
   - Library: `rich.console.Console` for colored output
   - Library: `rich.table.Table` for tabular data (status command)
   - Status indicators: ✓ (green checkmark), ⚠ (yellow warning), ✗ (red x), • (dim bullet)
   - Color scheme:
     - `[cyan]` - Informational messages
     - `[green]` - Success
     - `[yellow]` - Warnings
     - `[red]` - Errors
     - `[dim]` - Inactive/informational

**Files**: None (read-only source inspection)

**Parallel**: Yes (independent from T002 and T003)

**Notes**:

- Extract EXACT strings from source (e.g., help text, success messages)
- Note line numbers for future reference
- Pay attention to default values for flags
- Document error handling behavior (what user sees when invalid input)

**Validation**:

- [ ] All 5 subcommands documented with complete syntax
- [ ] All flags documented with defaults
- [ ] Error handling behavior captured
- [ ] Output format details recorded

---

### Subtask T002 – Extract Config Schema from agent_config.py

**Purpose**: Document config.yaml structure for agent configuration based on AgentConfig and AgentSelectionConfig dataclasses.

**Steps**:

1. **Open source file**:

   ```bash
   code src/specify_cli/orchestrator/agent_config.py
   ```

2. **Extract AgentSelectionConfig dataclass** (lines 30-42):

   ```python
   @dataclass
   class AgentSelectionConfig:
       strategy: SelectionStrategy = SelectionStrategy.PREFERRED
       preferred_implementer: str | None = None
       preferred_reviewer: str | None = None
   ```

   **Document fields**:
   - `strategy`: Enum `SelectionStrategy` with values `PREFERRED` or `RANDOM` (default: `PREFERRED`)
   - `preferred_implementer`: Optional string (agent ID for implementation)
   - `preferred_reviewer`: Optional string (agent ID for review)

3. **Extract AgentConfig dataclass** (lines 45-55):

   ```python
   @dataclass
   class AgentConfig:
       available: list[str] = field(default_factory=list)
       selection: AgentSelectionConfig = field(default_factory=AgentSelectionConfig)
   ```

   **Document fields**:
   - `available`: List of agent keys (e.g., `["claude", "codex", "opencode"]`)
   - `selection`: Nested `AgentSelectionConfig` object

4. **Document YAML structure**:

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

5. **Document fallback behavior** (from docstring and load_agent_config function):
   - Empty `available` list: Falls back to all 12 agents (legacy behavior)
   - Missing config.yaml: Falls back to all 12 agents with warning
   - Corrupt YAML: Falls back to all 12 agents with error message

6. **Document selection behavior** (lines 57-108):
   - `select_implementer()`: Returns agent from `available` list
     - If `strategy == PREFERRED`: Returns `preferred_implementer` if in available, else first agent
     - If `strategy == RANDOM`: Returns random choice from available
   - `select_reviewer()`: Prefers different agent than implementer for cross-review
   - **Note**: Selection strategy is used by orchestrator (not in scope for this doc feature, but good to know)

**Files**: None (read-only source inspection)

**Parallel**: Yes (independent from T001 and T003)

**Notes**:

- Config schema is simple (just 2 dataclasses)
- Focus on YAML structure users will see in `.kittify/config.yaml`
- Fallback behavior is important for migration guide
- Selection strategy details are out of scope (orchestrator feature, not documented in this sprint)

**Validation**:

- [ ] AgentConfig and AgentSelectionConfig fields documented
- [ ] YAML structure with example values
- [ ] Fallback behavior for empty/missing/corrupt config
- [ ] Field types and defaults recorded

---

### Subtask T003 – Extract Agent Mappings from m_0_9_1_complete_lane_migration.py

**Purpose**: Document all 12 agent keys and their directory mappings, highlighting 3 special cases.

**Steps**:

1. **Open source file**:

   ```bash
   code src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py
   ```

2. **Extract AGENT_DIRS constant** (lines ~50-65):

   ```python
   AGENT_DIRS = [
       (".claude", "commands"),
       (".codex", "prompts"),
       (".gemini", "commands"),
       (".cursor", "commands"),
       (".qwen", "commands"),
       (".opencode", "command"),     # Note: singular "command"
       (".windsurf", "workflows"),
       (".kilocode", "workflows"),
       (".roo", "commands"),
       (".github", "prompts"),       # GitHub Copilot
       (".augment", "commands"),
       (".amazonq", "prompts"),
   ]
   ```

3. **Extract AGENT_DIR_TO_KEY mapping** (lines ~70-85):

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
       ".github": "copilot",    # SPECIAL: Key ≠ directory
       ".augment": "auggie",     # SPECIAL: Key ≠ directory
       ".amazonq": "q",          # SPECIAL: Key ≠ directory
   }
   ```

4. **Create comprehensive mapping table**:

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
   | `copilot` | `.github` | `prompts` | `.github/prompts/` | **SPECIAL: GitHub directory** |
   | `auggie` | `.augment` | `commands` | `.augment/commands/` | **SPECIAL: Key ≠ directory** |
   | `q` | `.amazonq` | `prompts` | `.amazonq/prompts/` | **SPECIAL: Short key, full directory** |

5. **Document special cases** (for emphasis in documentation):
   - **copilot → .github**: GitHub Copilot uses the standard `.github/prompts/` directory (not `.copilot/`)
   - **auggie → .augment**: Shorter config key `auggie` maps to `.augment` directory (Augment Code agent)
   - **q → .amazonq**: Minimal key `q` maps to `.amazonq/prompts/` directory (Amazon Q agent, full branding in directory)

6. **Note for documentation**: These mappings are canonical and should be referenced when documenting agent commands.

**Files**: None (read-only source inspection)

**Parallel**: Yes (independent from T001 and T002)

**Notes**:

- 12 agents total (as of 0.12.0)
- 3 special cases where agent key ≠ directory name
- Standard pattern: agent key matches directory (e.g., `claude` → `.claude`)
- Subdirectory varies: `commands`, `command`, `prompts`, `workflows`
- This mapping is used by `agent config add/remove/status/sync` commands

**Validation**:

- [ ] All 12 agents listed with keys, directories, and subdirectories
- [ ] Special cases clearly identified (copilot, auggie, q)
- [ ] Mapping table formatted for easy documentation reference

---

## Test Strategy

**Not applicable** - This is a research work package. Validation is confirmation that findings are comprehensive and accurate.

**Validation approach**:

- Cross-reference extracted information against actual CLI help output: `spec-kitty agent config --help`
- Verify agent mappings match directory structure in an initialized project
- Confirm config schema matches `.kittify/config.yaml` in an example project

## Risks & Mitigations

**Risk**: Source code changes between research and documentation writing

- **Mitigation**: Use git commit hash (b74536b) as reference point; if code updated, re-run research
- **Detection**: Documentation validation will catch mismatches

**Risk**: Incomplete extraction (missing flags, options, edge cases)

- **Mitigation**: Review research.md R1-R3 sections for expected findings checklist
- **Validation**: WP02-WP06 should not require re-reading source files

**Risk**: Misinterpreting source code behavior

- **Mitigation**: Test commands manually if behavior unclear (e.g., `spec-kitty agent config list`)
- **Cross-reference**: ADR #6 provides architectural context

## Review Guidance

**Acceptance Checkpoints**:

- [ ] All 5 agent config subcommands fully documented (command, args, flags, defaults, output)
- [ ] AgentConfig and AgentSelectionConfig schemas extracted with YAML structure
- [ ] All 12 agent mappings documented in table format with special cases highlighted
- [ ] Error handling and fallback behavior captured
- [ ] Output formatting details (Rich Console, colors, status indicators) recorded
- [ ] Findings organized for easy reference in WP02-WP08

**Review Focus**:

- Completeness: Are findings comprehensive enough for doc writing?
- Accuracy: Do extracted details match source code?
- Clarity: Can WP02-WP08 implementers use these findings without re-reading source?

**Success Indicator**: WP02 implementer can document all 5 commands without opening source files again.

## Activity Log

**Initial entry**:

- 2026-01-23T10:23:45Z – system – lane=planned – Prompt generated.

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

---

- 2026-01-23T10:30:42Z – claude – shell_pid=97630 – lane=doing – Started implementation via workflow command
- 2026-01-23T10:34:10Z – claude – shell_pid=97630 – lane=for_review – Ready for review: Complete command signatures, config schema, and agent mappings extracted from source code. All 5 subcommands documented with exact syntax, error handling, and output formatting. 12 agent mappings documented with 3 special cases highlighted. 802-line research document ready for WP02-WP08 documentation writers.
- 2026-01-23T10:59:28Z – Claude – shell_pid=18985 – lane=doing – Started review via workflow command
- 2026-01-23T10:59:38Z – Claude – shell_pid=18985 – lane=done – Review passed: Complete command signatures, config schema, and agent mappings extracted from source code. 802-line research document ready for WP02-WP08 documentation writers.

## Implementation Command

**No dependencies** - This is the starting work package.

```bash
spec-kitty implement WP01
```

After completing this WP, multiple WPs can start in parallel: WP02, WP04, WP05, WP07, WP08.

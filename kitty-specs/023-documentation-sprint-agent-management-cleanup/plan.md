# Implementation Plan: Documentation Sprint: Agent Management and Cleanup

**Branch**: `023-documentation-sprint-agent-management-cleanup` | **Date**: 2026-01-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/023-documentation-sprint-agent-management-cleanup/spec.md`

## Summary

Update spec-kitty user documentation to reflect recent architectural changes in agent management (ADR #6, config-driven model) and clean up outdated jujutsu/jj references (removed in commit 99b0d84). This documentation sprint addresses three priorities:

1. **Agent Management (P1)**: Create comprehensive documentation for `spec-kitty agent config` commands (list/add/remove/status/sync), explaining the config-driven model where `.kittify/config.yaml` is the single source of truth
2. **Migration Guide (P1)**: Provide 0.11.x → 0.12.0 upgrade guidance for users transitioning to config-driven agent management
3. **Cleanup (P2-P3)**: Remove jujutsu references, fix broken links, and opportunistically correct documentation-code mismatches

**Validation approach**: Code-first - implementing agent manually inspects source files (`src/specify_cli/cli/commands/agent/config.py`, `src/specify_cli/orchestrator/agent_config.py`, ADR #6) to extract command signatures, dataclass schemas, and behavioral details. No automation scripts created.

## Technical Context

**Language/Version**: Markdown (documentation only)
**Primary Dependencies**: None (pure documentation)
**Storage**: N/A (files only)
**Testing**: Manual validation against source code
**Target Platform**: Documentation website (DocFX-rendered)
**Project Type**: Documentation update
**Performance Goals**: N/A
**Constraints**: Must not introduce implementation details; documentation stays at user/business level
**Scale/Scope**:
- 1 new how-to guide (`manage-agents.md`)
- 1 new migration guide section (may be separate file or section in existing guide)
- Updates to 14+ existing docs (CLI reference, configuration, init docs, etc.)
- Removal of 5+ jujutsu file references

**Source Files for Validation** (read-only, no modifications):
- `src/specify_cli/cli/commands/agent/config.py` - Command implementations, help text, error messages
- `src/specify_cli/orchestrator/agent_config.py` - `AgentConfig` and `AgentSelectionConfig` dataclasses
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` - `AGENT_DIRS` and `AGENT_DIR_TO_KEY` mappings
- `architecture/adrs/2026-01-23-6-config-driven-agent-management.md` - Architectural decision context

**Validation Strategy**:
- Agent reads source files directly
- Extracts command signatures from CLI help strings and function definitions
- Extracts config schema from dataclass type hints
- Extracts agent mappings from `AGENT_DIR_TO_KEY` constant
- Cross-references all documented commands/options against implementation
- Uses grep to verify zero jujutsu references remain
- Manually checks all internal links resolve

## Constitution Check

**Status**: SKIPPED - No constitution file exists at `.kittify/memory/constitution.md`

This feature is a documentation-only update with no code changes, so constitutional constraints on code complexity, architecture, or technology choices do not apply.

## Project Structure

### Documentation (this feature)

```
kitty-specs/023-documentation-sprint-agent-management-cleanup/
├── spec.md                    # Feature specification (complete)
├── plan.md                    # This file
├── research.md                # Phase 0 output (minimal for docs)
├── data-model.md              # N/A (no data entities for documentation)
├── quickstart.md              # Phase 1 output
└── tasks.md                   # Phase 2 output (created by /spec-kitty.tasks)
```

### Documentation Files (repository root)

```
docs/
├── how-to/
│   ├── manage-agents.md              # NEW: Agent management guide (FR-001)
│   ├── install-spec-kitty.md         # UPDATE: Cross-reference agent config
│   ├── upgrade-to-0-11-0.md          # UPDATE: Add 0.12.0 migration section (FR-004, FR-005)
│   └── [other guides]                # AUDIT: Fix opportunistic issues
│
├── reference/
│   ├── cli-commands.md               # UPDATE: Add agent config section (FR-006, FR-007)
│   ├── agent-subcommands.md          # UPDATE: Add agent config to index (FR-009)
│   ├── configuration.md              # UPDATE: Document config-driven model (FR-003)
│   └── supported-agents.md           # UPDATE: Cross-reference agent config
│
├── tutorials/
│   ├── getting-started.md            # AUDIT: Check for jj references, update init examples
│   └── [other tutorials]             # AUDIT: Fix opportunistic issues
│
└── explanation/
    └── [articles]                    # AUDIT: Remove jj references (FR-010, FR-011, FR-012)
```

**Files to Create**:
- `docs/how-to/manage-agents.md` (new)
- Optional: `docs/how-to/upgrade-to-0-12-0.md` (if migration guide warrants separate file)

**Files to Update** (audit and fix):
- `docs/reference/cli-commands.md` (add agent config commands)
- `docs/reference/agent-subcommands.md` (add to command index)
- `docs/reference/configuration.md` (explain config-driven model)
- `docs/how-to/install-spec-kitty.md` (cross-reference agent management)
- `docs/how-to/upgrade-to-0-11-0.md` (add 0.12.0 section or link to new guide)
- All docs mentioning `spec-kitty init --ai` (cross-reference post-init agent management)
- All docs with broken jj links or jj workflow references

**Jujutsu Files Removed** (validate no lingering references):
- `docs/explanation/auto-rebase-and-conflicts.md` (deleted)
- `docs/explanation/jujutsu-for-multi-agent.md` (deleted)
- `docs/how-to/handle-conflicts-jj.md` (deleted)
- `docs/how-to/use-operation-history.md` (deleted)
- `docs/tutorials/jujutsu-workflow.md` (deleted)

## Complexity Tracking

N/A - No constitution violations (no constitution exists, and this is documentation-only)

## Phase 0: Research

**Status**: Minimal research required - most information available in source code and ADR #6

### Research Tasks

#### R1: Validate Agent Config Command Signatures

**Goal**: Extract exact command signatures, flags, defaults, and error messages from implementation

**Sources**:
- `src/specify_cli/cli/commands/agent/config.py` (lines 1-382)
- Run `spec-kitty agent config --help` and subcommand help

**Expected Findings**:
- Command structure: `spec-kitty agent config {list|add|remove|status|sync}`
- Flag details: `--keep-config`, `--create-missing`, `--remove-orphaned`, defaults
- Error handling: Invalid agent keys show list of valid agents
- Output formatting: Rich Console tables, colored status indicators

**Decision**: Document exact syntax as implemented

#### R2: Extract AgentConfig Schema

**Goal**: Document config.yaml structure for agent configuration

**Sources**:
- `src/specify_cli/orchestrator/agent_config.py` (AgentConfig dataclass, lines 46-108)
- Example: `.kittify/config.yaml` from initialized project

**Expected Findings**:
```yaml
agents:
  available:
    - claude
    - codex
  selection:
    strategy: preferred  # or random
    preferred_implementer: claude
    preferred_reviewer: codex
```

**Decision**: Document structure with examples

#### R3: Confirm Agent Directory Mappings

**Goal**: Document all 12 agent keys and their directory mappings

**Sources**:
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` (`AGENT_DIR_TO_KEY` constant)

**Expected Findings**:
- Standard: `claude` → `.claude/commands`, `gemini` → `.gemini/commands`
- Special cases: `copilot` → `.github/prompts`, `auggie` → `.augment/commands`, `q` → `.amazonq/prompts`

**Decision**: Create mapping table in how-to guide

#### R4: Audit Jujutsu References

**Goal**: Identify all remaining jujutsu/jj references in documentation

**Method**:
```bash
grep -r "jujutsu\|jj\s\|\.jj" docs/ | grep -v ".jj/" | grep -v "jjust"
```

**Expected Findings**: Zero matches (cleanup was in commit 99b0d84)

**Decision**: If any found, list for removal in tasks

#### R5: Review ADR #6 for Migration Guide Content

**Goal**: Extract key points for 0.11.x → 0.12.0 migration guide

**Sources**:
- `architecture/adrs/2026-01-23-6-config-driven-agent-management.md`

**Expected Findings**:
- Problem: Migrations recreated deleted agent directories
- Solution: config.yaml as single source of truth
- User workflow: Use `spec-kitty agent config remove` instead of manual deletion
- Fallback: Legacy projects without config get all 12 agents

**Decision**: Summarize in migration guide with ADR link for details

### Research Consolidation

**Findings Summary**:
- All agent config commands validated against source
- Config schema extracted from dataclasses
- Agent mappings confirmed (12 agents, 3 special cases)
- Jujutsu cleanup confirmed complete
- ADR #6 provides migration context

**No NEEDS CLARIFICATION items** - all information available in codebase

**Output**: `research.md` with findings from R1-R5

## Phase 1: Design & Contracts

### Data Model

**Status**: N/A - Documentation feature has no data entities

Documentation describes existing data structures (AgentConfig, agent mappings) but does not introduce new entities.

### API Contracts

**Status**: N/A - No API changes

This feature documents existing CLI commands without modifying their interfaces.

### Agent Context Update

**Deferred**: Agent context files (`.claude/commands/`, etc.) are not updated by this feature. Agent management documentation explains how users update these via `spec-kitty agent config` commands.

### Documentation Outline (Key Artifact)

#### New: `docs/how-to/manage-agents.md`

```markdown
# Managing AI Agents

Overview of agent configuration system

## Prerequisites
- Initialized spec-kitty project
- At least one agent configured

## Agent Configuration Model
- Explain config.yaml as single source of truth
- Diagram: config.yaml → migrations respect → agent directories

## Commands

### Listing Agents
`spec-kitty agent config list`
- Shows configured agents with status
- Shows available but unconfigured agents
- Example output

### Adding Agents
`spec-kitty agent config add <agents>`
- Creates directories
- Updates config.yaml
- Copies mission templates
- Example: Adding claude and codex
- Error handling: Invalid agent keys

### Removing Agents
`spec-kitty agent config remove <agents>`
- Deletes directories
- Updates config.yaml
- `--keep-config` flag explanation
- Example: Removing gemini

### Checking Status
`spec-kitty agent config status`
- Table format explanation
- Status indicators: OK, Missing, Orphaned, Not used
- What "orphaned" means
- When to use this

### Syncing Filesystem
`spec-kitty agent config sync`
- Default behavior: Remove orphaned
- `--remove-orphaned` / `--keep-orphaned` flags
- `--create-missing` flag
- Example: Cleaning up after manual deletion

## Agent Directory Mappings
- Table of 12 agents with directory paths
- Special cases: copilot (.github), auggie (.augment), q (.amazonq)

## Troubleshooting
- Orphaned directories
- Missing directories
- Corrupt config.yaml

## See Also
- ADR #6 (config-driven architecture)
- CLI commands reference
- Supported agents reference
```

#### Update: `docs/how-to/upgrade-to-0-11-0.md`

Add new section:

```markdown
## Upgrading to 0.12.0: Config-Driven Agent Management

### What Changed
- Migrations now respect `.kittify/config.yaml`
- Agent directories no longer recreated on upgrade
- New `spec-kitty agent config` commands

### Migration Steps

1. Check current agents:
   ```bash
   spec-kitty agent config status
   ```

2. Remove unwanted agents (if any):
   ```bash
   spec-kitty agent config remove gemini cursor
   ```

3. Verify configuration:
   ```bash
   cat .kittify/config.yaml
   ```

4. Run upgrade:
   ```bash
   spec-kitty upgrade
   ```

5. Confirm agents not recreated:
   ```bash
   spec-kitty agent config status
   ```

### Why This Change
- Previous behavior: Manually deleted directories recreated on upgrade
- New behavior: config.yaml tracks user intent, migrations respect it
- See ADR #6 for architectural details

### Troubleshooting
- "Orphaned directories found": Run `spec-kitty agent config sync`
- "Agent directory missing": Run `spec-kitty agent config sync --create-missing`
```

#### Update: `docs/reference/cli-commands.md`

Insert section after existing commands:

```markdown
## spec-kitty agent config

**Synopsis**: `spec-kitty agent config [OPTIONS] COMMAND [ARGS]...`

**Description**: Manage project AI agent configuration (add, remove, list agents)

**Commands**:
- `list` - List configured agents and their status
- `add` - Add agents to the project
- `remove` - Remove agents from the project
- `status` - Show which agents are configured vs present on filesystem
- `sync` - Sync filesystem with config.yaml

---

### spec-kitty agent config list

**Synopsis**: `spec-kitty agent config list`

**Description**: List configured agents and their status.

**Output**:
- Configured agents with status indicators (✓ = present, ⚠ = missing)
- Available but not configured agents

**Examples**:
```bash
spec-kitty agent config list
```

---

[Continue with add, remove, status, sync subcommands following same format]
```

### Quickstart Guide

**Purpose**: Provide implementing agent with fast-start checklist

**Output**: `quickstart.md`

```markdown
# Documentation Sprint: Quick Implementation Guide

## Pre-Implementation Checklist

- [ ] Read spec.md (understand 5 user stories, 19 functional requirements)
- [ ] Read research.md (command signatures, config schema, agent mappings)
- [ ] Read ADR #6 (`architecture/adrs/2026-01-23-6-config-driven-agent-management.md`)
- [ ] Open source files for reference:
  - [ ] `src/specify_cli/cli/commands/agent/config.py`
  - [ ] `src/specify_cli/orchestrator/agent_config.py`
  - [ ] `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`

## Implementation Order (by Priority)

### Phase 1: P1 - Core Agent Management (FR-001 to FR-005)

1. **Create `docs/how-to/manage-agents.md`**
   - Extract command signatures from `src/specify_cli/cli/commands/agent/config.py`
   - Document all 5 subcommands (list/add/remove/status/sync)
   - Include agent directory mapping table
   - Add troubleshooting section

2. **Update Migration Guide**
   - Edit `docs/how-to/upgrade-to-0-11-0.md` (add 0.12.0 section)
   - OR create `docs/how-to/upgrade-to-0-12-0.md` (if content warrants separate file)
   - Reference ADR #6
   - Provide step-by-step migration workflow

### Phase 2: P2 - CLI Reference (FR-006 to FR-009)

3. **Update `docs/reference/cli-commands.md`**
   - Add `spec-kitty agent config` section
   - Document all subcommands with synopsis, options, examples
   - Follow existing format/style

4. **Update `docs/reference/agent-subcommands.md`**
   - Add `config` to command index

5. **Cross-Reference Updates**
   - `docs/reference/configuration.md` - Explain config-driven model
   - `docs/how-to/install-spec-kitty.md` - Link to manage-agents.md
   - `docs/reference/supported-agents.md` - Link to manage-agents.md

### Phase 3: P3 - Cleanup (FR-010 to FR-015)

6. **Jujutsu Audit**
   - Search: `grep -r "jujutsu\|jj\s" docs/ | grep -v ".jj/"`
   - Remove any remaining references
   - Fix broken links to deleted files

7. **Opportunistic Fixes**
   - Validate command syntax against source code
   - Fix broken internal links
   - Correct outdated configuration examples

## Validation Checklist

- [ ] All 5 agent config subcommands documented with correct syntax
- [ ] Agent directory mappings accurate (12 agents, special cases noted)
- [ ] Config schema matches `AgentConfig` dataclass
- [ ] Migration guide references ADR #6
- [ ] Zero jujutsu references remain (`grep -r "jujutsu\|jj\s" docs/`)
- [ ] All internal links resolve (no 404s)
- [ ] Cross-references present in at least 3 related docs

## Success Criteria Verification

- **SC-001**: How-to guide is clear and self-contained (no external consultation needed)
- **SC-002**: Migration guide explains config-driven model in < 500 words
- **SC-003**: Zero broken links (`grep -r "\[.*\](.*\.md)" docs/ | check paths exist`)
- **SC-004**: Command syntax matches `spec-kitty agent config --help` output
- **SC-005**: Zero jujutsu references (`grep -r "jujutsu\|jj" docs/ --exclude-dir=.jj`)
- **SC-006**: Agent config commands cross-referenced in 3+ docs

## Estimated Effort

- Phase 1 (P1): 60% of effort (new guide + migration guide)
- Phase 2 (P2): 30% of effort (reference updates + cross-refs)
- Phase 3 (P3): 10% of effort (cleanup audit)

Total: ~4-6 hours for thorough implementation + validation
```

## Phase 2: Task Generation

**Status**: NOT STARTED - Requires explicit `/spec-kitty.tasks` command

Phase 2 artifacts (tasks.md, tasks/*.md) are generated by the `/spec-kitty.tasks` command, which the user must run separately.

## Deliverables Summary

**Generated Artifacts** (in `kitty-specs/023-documentation-sprint-agent-management-cleanup/`):
- ✅ `plan.md` - This file
- ✅ `research.md` - Research findings (R1-R5)
- ⏭️ `data-model.md` - N/A (no data entities)
- ⏭️ `contracts/` - N/A (no API contracts)
- ✅ `quickstart.md` - Fast-start implementation guide

**Documentation Files to Create** (in `docs/`):
- `docs/how-to/manage-agents.md` (new)
- Optional: `docs/how-to/upgrade-to-0-12-0.md` (if migration content warrants separate file)

**Documentation Files to Update** (in `docs/`):
- `docs/reference/cli-commands.md` (add agent config section)
- `docs/reference/agent-subcommands.md` (add to index)
- `docs/reference/configuration.md` (config-driven model)
- `docs/how-to/install-spec-kitty.md` (cross-reference)
- `docs/how-to/upgrade-to-0-11-0.md` (add 0.12.0 section)
- `docs/reference/supported-agents.md` (cross-reference)
- All docs with jj references or broken links (audit and fix)

**Next Command**: `/spec-kitty.tasks` (user must invoke explicitly)

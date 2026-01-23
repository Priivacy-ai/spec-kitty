# Documentation Sprint: Quick Implementation Guide

**Feature**: 023-documentation-sprint-agent-management-cleanup
**Mission**: software-dev
**Estimated Effort**: 4-6 hours

## Pre-Implementation Checklist

- [ ] Read `spec.md` - Understand 5 user stories (P1-P3), 19 functional requirements (FR-001 to FR-019)
- [ ] Read `research.md` - Command signatures, config schema, agent mappings (R1-R5)
- [ ] Read `plan.md` - Implementation phases, documentation outline, validation strategy
- [ ] Read ADR #6: `architecture/adrs/2026-01-23-6-config-driven-agent-management.md`
- [ ] Open source files for reference (read-only):
  - [ ] `src/specify_cli/cli/commands/agent/config.py` - Command implementations
  - [ ] `src/specify_cli/orchestrator/agent_config.py` - AgentConfig dataclass
  - [ ] `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` - Agent mappings

## Implementation Order (by Priority)

### Phase 1: P1 - Core Agent Management (FR-001 to FR-005)

**Estimated Effort**: 60% of total (2.5-3.5 hours)

#### 1. Create `docs/how-to/manage-agents.md` (NEW FILE)

**Requirements**: FR-001, FR-002, FR-003

**Content Structure** (from plan.md Phase 1):
```markdown
# Managing AI Agents

## Overview
- Explain agent configuration system
- Config-driven model (.kittify/config.yaml as single source of truth)

## Prerequisites
- Initialized spec-kitty project
- At least one agent configured

## Agent Configuration Model
- Diagram or explanation: config.yaml → migrations respect → agent directories
- Single source of truth concept
- Fallback behavior (empty config → all 12 agents)

## Commands

### Listing Agents (spec-kitty agent config list)
- Syntax, arguments, output format
- Example output with status indicators (✓ ⚠)
- When to use: Check current configuration

### Adding Agents (spec-kitty agent config add <agents>)
- Syntax: `spec-kitty agent config add claude codex gemini`
- What it does: Creates directories, updates config.yaml, copies templates
- Example: Adding claude and codex
- Error handling: Invalid agent keys (shows valid list)

### Removing Agents (spec-kitty agent config remove <agents>)
- Syntax: `spec-kitty agent config remove gemini cursor`
- What it does: Deletes directories, updates config.yaml
- `--keep-config` flag: Keep in config but delete directory
- Example: Removing gemini

### Checking Status (spec-kitty agent config status)
- Table output format (Agent Key, Directory, Configured, Exists, Status)
- Status indicators: OK (green), Missing (yellow), Orphaned (red), Not used (dim)
- What "orphaned" means: Present but not configured
- When to use: Audit sync issues

### Syncing Filesystem (spec-kitty agent config sync)
- Default behavior: Remove orphaned directories
- `--remove-orphaned` / `--keep-orphaned` flags (default: remove)
- `--create-missing` flag: Create dirs for configured agents
- Example: Cleaning up after manual deletion

## Agent Directory Mappings
- Table of 12 agents (from research.md R3)
- Columns: Agent Key, Directory Path
- Highlight special cases: copilot (.github), auggie (.augment), q (.amazonq)

## Troubleshooting
- Orphaned directories: Run `sync --remove-orphaned`
- Missing directories: Run `sync --create-missing`
- Corrupt config.yaml: Fallback to all 12 agents, repair with `add/remove`

## See Also
- [ADR #6: Config-Driven Agent Management](../../architecture/adrs/2026-01-23-6-config-driven-agent-management.md)
- [CLI Commands Reference](../reference/cli-commands.md#spec-kitty-agent-config)
- [Supported Agents](../reference/supported-agents.md)
```

**Validation**:
- Extract command syntax from `src/specify_cli/cli/commands/agent/config.py`
- Verify agent mappings against `AGENT_DIR_TO_KEY` constant
- Test all examples match actual CLI behavior

#### 2. Update Migration Guide (FR-004, FR-005)

**Option A**: Add section to `docs/how-to/upgrade-to-0-11-0.md`
**Option B**: Create new `docs/how-to/upgrade-to-0-12-0.md` (if content > 500 words)

**Content** (from plan.md Phase 1):
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

**Validation**:
- Review ADR #6 for accuracy
- Confirm migration workflow matches implementation
- Keep under 500 words (SC-002 requirement)

---

### Phase 2: P2 - CLI Reference (FR-006 to FR-009)

**Estimated Effort**: 30% of total (1.5-2 hours)

#### 3. Update `docs/reference/cli-commands.md` (FR-006, FR-007)

**Insert After**: Existing `spec-kitty agent` section

**Content Template**:
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

**Options**: None

**Output**:
- Configured agents with status indicators (✓ = present, ⚠ = missing)
- Available but not configured agents

**Examples**:
```bash
spec-kitty agent config list
```

---

### spec-kitty agent config add

**Synopsis**: `spec-kitty agent config add <agents>`

**Description**: Add agents to the project. Creates agent directories and updates config.yaml.

**Arguments**:
- `<agents>`: Space-separated agent keys (e.g., `claude codex`)

**Options**: None

**Examples**:
```bash
spec-kitty agent config add claude codex
spec-kitty agent config add gemini
```

---

[Continue with remove, status, sync following same format]
```

**Validation**:
- Extract exact syntax from `spec-kitty agent config <subcommand> --help`
- Match format/style of existing CLI reference entries
- Include all options with defaults

#### 4. Update `docs/reference/agent-subcommands.md` (FR-009)

**Add Entry**:
```markdown
| Command | Description |
|---------|-------------|
| `config` | Manage project AI agent configuration (add, remove, list agents) |
```

**Link**: Point to `cli-commands.md#spec-kitty-agent-config`

#### 5. Cross-Reference Updates (FR-008)

**Files to Update**:

**`docs/reference/configuration.md`**:
- Add section explaining config-driven agent model
- Link to ADR #6
- Link to manage-agents.md

**`docs/how-to/install-spec-kitty.md`**:
- Add note after init examples: "To manage agents after initialization, see [Managing AI Agents](manage-agents.md)"

**`docs/reference/supported-agents.md`**:
- Add intro paragraph: "Use `spec-kitty agent config` commands to manage which agents are active. See [Managing AI Agents](../how-to/manage-agents.md) for details."

---

### Phase 3: P3 - Cleanup (FR-010 to FR-015)

**Estimated Effort**: 10% of total (0.5-1 hour)

#### 6. Jujutsu Audit (FR-010, FR-011, FR-012)

**Search Command**:
```bash
grep -r "jujutsu\|jj\s\|\.jj" docs/ | grep -v ".jj/" | grep -v "jjust"
```

**Expected Deletions** (from commit 99b0d84):
- `docs/explanation/auto-rebase-and-conflicts.md` (already deleted)
- `docs/explanation/jujutsu-for-multi-agent.md` (already deleted)
- `docs/how-to/handle-conflicts-jj.md` (already deleted)
- `docs/how-to/use-operation-history.md` (already deleted)
- `docs/tutorials/jujutsu-workflow.md` (already deleted)

**Remaining References to Fix**:
- VCS detection order in `docs/reference/cli-commands.md` (init section)
  - Remove mentions of "jj preferred if available"
  - Update to "git-only" workflow
- Any cross-references to deleted jj files (fix or remove)

**Validation**: `grep` confirms zero jujutsu references (SC-005)

#### 7. Opportunistic Fixes (FR-013, FR-014, FR-015)

**Command Syntax Validation** (FR-013):
- Cross-reference documented commands against `--help` output
- Fix any outdated flag names or options
- Common issues: Renamed flags, deprecated commands

**Config Schema Validation** (FR-014):
- Check config.yaml examples match `AgentConfig` dataclass
- Verify field names, types, defaults

**Broken Link Check** (FR-015):
- Manual scan for `[text](path.md)` links
- Verify all referenced files exist
- Common issues: Renamed files, moved directories

---

## Validation Checklist

**Before committing, verify**:

- [ ] All 5 agent config subcommands documented with correct syntax (FR-002, FR-006)
- [ ] Agent directory mappings accurate (12 agents, 3 special cases noted) (FR-017)
- [ ] Config schema matches `AgentConfig` dataclass (FR-018)
- [ ] Migration guide references ADR #6 (FR-019)
- [ ] Zero jujutsu references remain: `grep -r "jujutsu\|jj\s" docs/` (FR-010, SC-005)
- [ ] All internal links resolve (no 404s) (FR-015, SC-003)
- [ ] Cross-references present in at least 3 related docs (SC-006):
  - [ ] `configuration.md`
  - [ ] `install-spec-kitty.md`
  - [ ] `supported-agents.md`

**Code-First Validation**:
- [ ] Command syntax matches `spec-kitty agent config --help` output (SC-004)
- [ ] Config schema matches `src/specify_cli/orchestrator/agent_config.py` dataclass
- [ ] Agent mappings match `m_0_9_1_complete_lane_migration.py` `AGENT_DIR_TO_KEY`

---

## Success Criteria Verification

**SC-001**: New users can successfully add/remove agents without consulting support
- ✅ How-to guide is clear and self-contained
- ✅ Examples cover common use cases
- ✅ Troubleshooting section addresses common issues

**SC-002**: Existing 0.11.x users understand config-driven behavior within 5 minutes
- ✅ Migration guide explains problem/solution concisely (< 500 words)
- ✅ Step-by-step workflow provided
- ✅ ADR #6 link for deeper understanding

**SC-003**: Zero broken links in documentation
- ✅ All `[text](path.md)` links verified
- ✅ No references to deleted jj files

**SC-004**: 100% of agent config command syntax matches actual CLI implementation
- ✅ All syntax extracted from source code or `--help` output
- ✅ Flags and defaults accurate

**SC-005**: Zero references to jujutsu/jj remain
- ✅ `grep -r "jujutsu\|jj" docs/ --exclude-dir=.jj` returns zero matches

**SC-006**: Agent config commands discoverable via CLI help and referenced from 3+ pages
- ✅ CLI reference updated (`cli-commands.md`)
- ✅ Cross-references added (`configuration.md`, `install-spec-kitty.md`, `supported-agents.md`)

---

## Estimated Effort Breakdown

| Phase | Tasks | Effort | Notes |
|-------|-------|--------|-------|
| Phase 1 (P1) | Create manage-agents.md, migration guide | 60% | 2.5-3.5 hours (most content creation) |
| Phase 2 (P2) | Update CLI reference, cross-refs | 30% | 1.5-2 hours (systematic updates) |
| Phase 3 (P3) | Jujutsu audit, opportunistic fixes | 10% | 0.5-1 hour (cleanup) |
| **Total** | All phases | **100%** | **4-6 hours** |

**Assumptions**:
- Implementing agent familiar with spec-kitty documentation structure
- Source files are readable and well-documented
- No major documentation framework changes needed

**Risks**:
- Opportunistic fixes scope creep (mitigate: limit to obvious issues only)
- Jujutsu references more widespread than expected (mitigate: strict grep criteria)

---

## Tips for Implementation

**Documentation Style**:
- Follow existing doc patterns (reference other how-to guides)
- Use concrete examples with actual commands
- Keep user-focused (avoid implementation details)
- Use Divio framework: How-to guides are task-oriented

**Code-First Validation**:
- Open source files in editor while writing docs
- Copy exact strings from source (don't paraphrase)
- Run `--help` commands to verify syntax
- Use `cat -n` to reference line numbers

**Time Management**:
- Do P1 (core docs) first - highest user value
- P2 (references) second - important for discoverability
- P3 (cleanup) last - nice-to-have, can be partial if time-constrained

**Quality Over Speed**:
- Better to have complete, accurate P1 docs than rushed P1+P2+P3
- Validation checklist is mandatory, not optional
- Cross-reference accuracy critical for user trust

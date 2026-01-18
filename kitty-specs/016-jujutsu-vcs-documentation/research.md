# Research: Jujutsu VCS Documentation

**Feature**: 016-jujutsu-vcs-documentation
**Created**: 2026-01-17
**Purpose**: Consolidate research findings for jj documentation

## Research Sources

1. **CLI Help Output** - Live output from spec-kitty commands
2. **Feature 015 Design Docs** - spec.md, plan.md, data-model.md, contracts/vcs-protocol.py
3. **Current Docs Structure** - toc.yml, existing Divio 4-type structure from feature 014

---

## CLI Command Documentation

### New Command: `spec-kitty sync`

**Purpose**: Synchronize workspace with upstream changes

**Usage**: `spec-kitty sync [OPTIONS]`

**Options**:
| Flag | Short | Description |
|------|-------|-------------|
| `--repair` | `-r` | Attempt workspace recovery (may lose uncommitted work) |
| `--verbose` | `-v` | Show detailed sync output |

**Backend Differences** (critical for documentation):
- **git**: Sync may FAIL on conflicts (must resolve before continuing)
- **jj**: Sync always SUCCEEDS (conflicts stored, resolve later)

**Examples from CLI**:
```bash
# Sync current workspace
spec-kitty sync

# Sync with verbose output
spec-kitty sync --verbose

# Attempt recovery from broken state
spec-kitty sync --repair
```

---

### New Command: `spec-kitty ops`

**Purpose**: Operation history and undo

**Subcommands**:
| Subcommand | Description |
|------------|-------------|
| `log` | Show operation history |
| `undo` | Undo last operation (jj only) |
| `restore` | Restore to a specific operation (jj only) |

---

### Subcommand: `spec-kitty ops log`

**Purpose**: Show operation history

**Usage**: `spec-kitty ops log [OPTIONS]`

**Options**:
| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--limit` | `-n` | Number of operations to show | 20 |
| `--verbose` | `-v` | Show full operation IDs and details | - |

**Backend Differences**:
- **jj**: Shows operation log with undo information
- **git**: Shows reflog (read-only history)

---

### Subcommand: `spec-kitty ops undo`

**Purpose**: Undo last operation (jj only)

**Usage**: `spec-kitty ops undo [OPTIONS] [OPERATION_ID]`

**Arguments**:
| Argument | Description |
|----------|-------------|
| `operation_id` | Operation ID to undo (defaults to last operation) |

**Backend Support**:
- **jj**: Full support - reverts repository to state before last operation
- **git**: NOT SUPPORTED - git does not have reversible operation history

---

### Subcommand: `spec-kitty ops restore`

**Purpose**: Restore to a specific operation (jj only)

**Usage**: `spec-kitty ops restore OPERATION_ID`

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `operation_id` | Yes | Operation ID to restore to |

**Backend Support**:
- **jj**: Full support - more powerful than undo, can jump to any point in history
- **git**: NOT SUPPORTED

---

### Updated Command: `spec-kitty init`

**New Option**:
| Flag | Description |
|------|-------------|
| `--vcs` | VCS to use: 'git' or 'jj'. Defaults to jj if available. |

**Documentation Note**: When jj is available and user runs `spec-kitty init`, the tool will:
1. Auto-detect jj availability
2. Prefer jj over git when both available
3. Display recommendation message if jj is not installed

---

## Feature 015 Design Reference

### VCS Backend Enum

```python
class VCSBackend(str, Enum):
    GIT = "git"
    JUJUTSU = "jj"
```

### VCS Capabilities Comparison

| Capability | jj | git |
|------------|-----|-----|
| Auto-rebase | Yes | No |
| Conflict storage (non-blocking) | Yes | No (conflicts block) |
| Operation log | Yes (full) | Partial (reflog) |
| Change IDs (stable identity) | Yes | No |
| Workspaces | Yes (native) | Yes (worktrees) |
| Colocated mode | Yes | N/A |

### Key Data Structures for Documentation

**SyncResult** - What users see after `spec-kitty sync`:
- `status`: UP_TO_DATE, SYNCED, CONFLICTS, FAILED
- `conflicts`: List of conflicted files with details
- `files_updated/added/deleted`: Statistics
- `changes_integrated`: What commits were pulled in
- `message`: Human-readable summary

**ConflictInfo** - What users see in conflict reports:
- `file_path`: Which file has conflicts
- `conflict_type`: CONTENT, MODIFY_DELETE, ADD_ADD, etc.
- `line_ranges`: Where conflicts are located
- `is_resolved`: Whether conflict markers have been removed

**OperationInfo** - What users see in `spec-kitty ops log`:
- `operation_id`: ID for undo/restore
- `timestamp`: When operation occurred
- `description`: What the operation did
- `is_undoable`: Whether this can be undone

### VCS Detection Order (for init documentation)

1. If `--vcs` specified, use that
2. If path is in a feature, read meta.json for locked VCS
3. If jj available and prefer_jj=True (default), use jj
4. If git available, use git
5. Raise error if neither available

### Per-Feature VCS Lock

Once a feature is created, its VCS choice is **locked in meta.json**:
```json
{
  "vcs": "jj",
  "vcs_locked_at": "2026-01-17T11:15:00Z"
}
```
Cannot be changed after feature creation.

---

## Current Documentation Structure

### Existing Files to Update (from feature 014)

**Tutorials** (`docs/tutorials/`):
- `getting-started.md` - Add jj mention, installation recommendation
- `your-first-feature.md` - Mention VCS abstraction
- `multi-agent-workflow.md` - Highlight jj benefits for parallel work

**How-To Guides** (`docs/how-to/`):
- `install-spec-kitty.md` - Add jj installation section
- `implement-work-package.md` - Mention jj workspace vs git worktree
- `parallel-development.md` - Emphasize jj auto-rebase benefits
- `handle-dependencies.md` - Mention sync command for dependent WPs

**Reference** (`docs/reference/`):
- `cli-commands.md` - Add sync, ops commands
- `file-structure.md` - Document .jj/ alongside .git/
- `configuration.md` - Document vcs section in config.yaml

**Explanations** (`docs/explanation/`):
- `workspace-per-wp.md` - Already exists, may need jj additions
- `git-worktrees.md` - Already exists, compare with jj workspaces

### New Files to Create

**Tutorials**:
- `jujutsu-workflow.md` - Complete jj workflow tutorial

**How-To Guides**:
- `sync-workspaces.md` - How to use spec-kitty sync
- `handle-conflicts-jj.md` - Non-blocking conflict handling with jj
- `use-operation-history.md` - How to use spec-kitty ops

**Reference**:
- Add to `cli-commands.md`: sync, ops log, ops undo, ops restore

**Explanations**:
- `jujutsu-for-multi-agent.md` - Why jj is preferred for multi-agent development
- `auto-rebase-and-conflicts.md` - How jj auto-rebase and non-blocking conflicts work

---

## Key Documentation Decisions

### Decision 1: Integration vs. Dedicated Content

**Choice**: Both - integrate throughout AND create dedicated jj content

**Rationale**:
- Users following any tutorial/how-to should learn jj is an option
- Users specifically interested in jj need dedicated deep-dives

### Decision 2: Backend Difference Documentation

**Choice**: Use comparison tables and clear callouts

**Rationale**:
- Users need to quickly understand what's different between git and jj
- Tables work well for capability comparisons
- Callout boxes for critical behavioral differences (conflicts blocking vs. stored)

### Decision 3: Command Reference Format

**Choice**: Add to existing cli-commands.md with full detail

**Rationale**:
- Maintains consistency with feature 014 structure
- Users expect all commands in one reference file
- Cross-reference to jj explanation for deeper understanding

---

## Documentation Accuracy Verification

### Commands Verified Against CLI

| Command | Verified | Notes |
|---------|----------|-------|
| `spec-kitty sync` | ✅ | Help matches implementation |
| `spec-kitty ops` | ✅ | Help matches implementation |
| `spec-kitty ops log` | ✅ | Help matches implementation |
| `spec-kitty ops undo` | ✅ | Help matches implementation |
| `spec-kitty ops restore` | ✅ | Help matches implementation |
| `spec-kitty init --vcs` | ✅ | New flag documented |

### Feature 015 Design Docs Verified

| Document | Status | Notes |
|----------|--------|-------|
| spec.md | ✅ | 9 user stories, 24 FRs |
| plan.md | ✅ | Architecture decisions documented |
| data-model.md | ✅ | All types defined |
| contracts/vcs-protocol.py | ✅ | Full API contract |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| CLI output changes in future versions | Document minimum version (0.12.0+) |
| jj behavior differs from documentation | Verified against live CLI |
| Users confused by jj vs git differences | Use comparison tables, clear callouts |
| Search doesn't find "jujutsu" | Use both "jj" and "jujutsu" terms throughout |

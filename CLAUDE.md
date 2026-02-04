# Spec Kitty Development Guidelines

## ⚠️ CRITICAL: Template Source Location (READ THIS FIRST!)

**When fixing bugs or updating templates, edit the SOURCE files, NOT the agent copies!**

| What | Location | Action |
|------|----------|--------|
| **SOURCE templates** | `src/specify_cli/missions/*/command-templates/` | ✅ EDIT THESE |
| **Agent copies** | `.claude/`, `.amazonq/`, `.augment/`, etc. | ❌ DO NOT EDIT |

The directories like `.claude/commands/`, `.amazonq/prompts/`, etc. are **GENERATED COPIES** that get deployed to projects that USE spec-kitty. They are NOT source code.

**To fix a template bug:**
```bash
# ✅ CORRECT: Edit the source template
vim src/specify_cli/missions/software-dev/command-templates/implement.md

# ❌ WRONG: Editing agent copies (these are generated, not source!)
vim .claude/commands/spec-kitty.implement.md  # NO!
vim .amazonq/prompts/spec-kitty.implement.md  # NO!
```

**How templates flow:**
```
src/specify_cli/missions/*/command-templates/*.md  (SOURCE - edit here!)
    ↓ (copied by migrations during `spec-kitty upgrade`)
.claude/commands/spec-kitty.*.md  (GENERATED COPY - don't edit!)
.amazonq/prompts/spec-kitty.*.md  (GENERATED COPY - don't edit!)
... (12 agent directories total)
```

---

## Supported AI Agents

Spec Kitty supports **12 AI agents** with slash commands. When adding features that affect slash commands, migrations, or templates, ensure ALL agents are updated:

| Agent | Directory | Subdirectory | Slash Commands |
|-------|-----------|--------------|----------------|
| Claude Code | `.claude/` | `commands/` | `/spec-kitty.*` |
| GitHub Copilot | `.github/` | `prompts/` | `/spec-kitty.*` |
| Google Gemini | `.gemini/` | `commands/` | `/spec-kitty.*` |
| Cursor | `.cursor/` | `commands/` | `/spec-kitty.*` |
| Qwen Code | `.qwen/` | `commands/` | `/spec-kitty.*` |
| OpenCode | `.opencode/` | `command/` | `/spec-kitty.*` |
| Windsurf | `.windsurf/` | `workflows/` | `/spec-kitty.*` |
| GitHub Codex | `.codex/` | `prompts/` | `/spec-kitty.*` |
| Kilocode | `.kilocode/` | `workflows/` | `/spec-kitty.*` |
| Augment Code | `.augment/` | `commands/` | `/spec-kitty.*` |
| Roo Cline | `.roo/` | `commands/` | `/spec-kitty.*` |
| Amazon Q | `.amazonq/` | `prompts/` | `/spec-kitty.*` |

**Canonical source**: `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` → `AGENT_DIRS`

**When modifying**:
- Migrations that update slash commands: Use `get_agent_dirs_for_project()` helper (config-aware)
- Template changes: Will propagate to all agents via migration
- Testing: Verify at least .claude, .codex, .opencode (most common)

## Agent Management Best Practices

**CRITICAL: config.yaml is the single source of truth for agent configuration.**

### For Users

**Adding/Removing Agents:**
```bash
# List configured agents
spec-kitty agent config list

# Add agents
spec-kitty agent config add claude codex

# Remove agents
spec-kitty agent config remove codex gemini

# Check status (configured vs orphaned)
spec-kitty agent config status

# Sync filesystem with config
spec-kitty agent config sync
```

**DO:**
- ✅ Use `spec-kitty agent config add/remove` commands
- ✅ Let migrations respect your agent configuration
- ✅ Keep agents you actually use configured

**DON'T:**
- ❌ Manually delete agent directories without updating config
- ❌ Expect manually deleted agents to stay deleted (pre-0.12.0 bug)
- ❌ Modify `.kittify/config.yaml` directly (use CLI commands)

### For Developers

**Writing Migrations:**
```python
# ALWAYS use config-aware helper:
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

**DO:**
- ✅ Import `get_agent_dirs_for_project()` from `m_0_9_1_complete_lane_migration`
- ✅ Use `continue` if directory doesn't exist (respect deletions)
- ✅ Test with both configured and unconfigured agents
- ✅ Test legacy projects without config.yaml (should fallback to all)

**DON'T:**
- ❌ Hardcode `AGENT_DIRS` in new migrations (import from `m_0_9_1`)
- ❌ Create missing directories (`mkdir`) - respect user deletions
- ❌ Assume all 12 agents are always present
- ❌ Process agents not in config.yaml

**Testing Migrations:**
```python
# Test config-aware behavior
def test_migration_respects_config(tmp_path):
    # Setup: config with only opencode
    config = AgentConfig(available=["opencode"])
    save_agent_config(tmp_path, config)

    # Create opencode directory (configured)
    (tmp_path / ".opencode" / "command").mkdir(parents=True)

    # Create claude directory (NOT configured - orphaned)
    (tmp_path / ".claude" / "commands").mkdir(parents=True)

    # Run migration
    migration.apply(tmp_path)

    # Verify: opencode processed, claude skipped
    assert migration_updated_opencode
    assert not migration_updated_claude
```

**Agent Key Mappings:**
- `copilot` → `.github/prompts` (not `.copilot`)
- `auggie` → `.augment/commands` (not `.auggie`)
- `q` → `.amazonq/prompts` (not `.q`)

Use `AGENT_DIR_TO_KEY` mapping for conversions.

### Architecture

**Single Source of Truth:** `.kittify/config.yaml`
```yaml
agents:
  available:
    - opencode
    - claude
```

**Derived State:** Agent directories on filesystem
- Only configured agents have directories
- Migrations only process configured agents
- Deletions are respected across upgrades

**Key Functions:**
- `get_agent_dirs_for_project(project_path)` - Returns list of (dir, subdir) tuples for configured agents
- `load_agent_config(repo_root)` - Loads AgentConfig from config.yaml
- `save_agent_config(repo_root, config)` - Saves AgentConfig to config.yaml

**See Also:**
- ADR #6: Config-Driven Agent Management
- `tests/specify_cli/test_agent_config_migration.py` - Integration tests
- `tests/specify_cli/cli/commands/test_agent_config.py` - CLI command tests

---

# Feature Development History

*Auto-generated from all feature plans. Last updated: 2025-11-10*

## Active Technologies
- Python 3.11+ (existing spec-kitty codebase) + pathlib, Rich (for console output), subprocess (for git operations) (003-auto-protect-agent)
- Python 3.11+ (existing spec-kitty codebase) + yper, rich, httpx, pyyaml, readchar (004-modular-code-refactoring)
- File system (no database) (004-modular-code-refactoring)
- Python 3.11+ (existing spec-kitty codebase requirement) (005-refactor-mission-system)
- Filesystem only (YAML configs, CSV files, markdown templates) (005-refactor-mission-system)
- Python 3.11+ (existing spec-kitty codebase) + pathlib, Rich (console output), ruamel.yaml (frontmatter parsing), typer (CLI) (007-frontmatter-only-lane)
- Filesystem only (YAML frontmatter in markdown files) (007-frontmatter-only-lane)
- Python 3.11+ (existing spec-kitty requirement) (008-unified-python-cli)
- Filesystem only (no database) (008-unified-python-cli)
- Python 3.11+ + pathlib, Rich, ruamel.yaml, typer, subprocess (git worktree), pytest (010-workspace-per-work-package-for-parallel-development)
- Filesystem only (YAML frontmatter, git worktrees) (010-workspace-per-work-package-for-parallel-development)
- Python 3.11+ (existing spec-kitty codebase) + psutil (cross-platform process management) (011-constitution-packaging-safety-and-redesign)
- Filesystem only (templates in src/specify_cli/, user projects in .kittify/) (011-constitution-packaging-safety-and-redesign)
- Python 3.11+ (existing spec-kitty codebase) + subprocess (for JSDoc, Sphinx, rustdoc invocation), ruamel.yaml (YAML parsing) (012-documentation-mission)
- Filesystem only (mission configs in YAML, Divio templates in Markdown, iteration state in JSON) (012-documentation-mission)
- Python 3.11+ (existing spec-kitty codebase) + subprocess (for jj/git CLI invocation), typing (Protocol), dataclasses (015-first-class-jujutsu-vcs-integration)
- Filesystem only (meta.json, YAML frontmatter, git/jj repositories) (015-first-class-jujutsu-vcs-integration)

- Python 3.11+ + typer, rich, ruamel.yaml, pydantic (029-mission-aware-cleanup-docs-wiring)
- N/A (file-based CLI artifacts) (029-mission-aware-cleanup-docs-wiring)
## Project Structure
```
architecture/           # Architectural design decisions and technical specifications
  ├── README.md        # Overview of architecture documentation
  ├── GIT_REPO_MANAGEMENT_IMPLEMENTATION.md  # Complete git repo management design
  ├── PHASE1_IMPLEMENTATION.md               # Base branch tracking spec
  └── PHASE2_IMPLEMENTATION.md               # Multi-parent merge spec
src/                   # Source code
tests/                 # Test suite
kitty-specs/          # Feature specifications (dogfooding spec-kitty)
docs/                 # User documentation
```

**When adding new architectural designs**:
- Store in `architecture/` directory
- Follow the template in `architecture/README.md`
- Update the architecture README index
- Reference from code comments for major components

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Testing

**Run tests in headless mode** (prevents browser windows from opening):
```bash
PWHEADLESS=1 pytest tests/
```

Or use pytest flags:
```bash
pytest tests/ --browser-channel=chromium --headed=false
```

## Code Style
Python 3.11+ (existing spec-kitty codebase): Follow standard conventions

## Recent Changes
- 029-mission-aware-cleanup-docs-wiring: Added Python 3.11+ + typer, rich, ruamel.yaml, pydantic
- 015-first-class-jujutsu-vcs-integration: Adding VCS abstraction layer (Protocol-based), jj as first-class citizen alongside git, new vcs/ subpackage
- 011-constitution-packaging-safety-and-redesign: Added psutil for cross-platform process management, relocated templates from .kittify/ to src/specify_cli/
<!-- MANUAL ADDITIONS START -->

## PyPI Release (Quick Reference)

**CRITICAL: NEVER create releases without explicit user instruction!**
**CRITICAL: NEVER manually create releases! You MUST use the Github release process.**

Only cut a release when the user explicitly says:
- "cut a release"
- "release v0.X.Y"
- "push to PyPI"
- Similar clear instructions

**DO NOT**:
- Automatically release after fixing bugs
- Release without verification
- Assume a fix should be released immediately

```bash
# 1. Ensure version is bumped in pyproject.toml
# 2. Ensure CHANGELOG.md has entry for version
# 3. Create and push annotated tag:
git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"
git push origin vX.Y.Z

# 4. Monitor workflow:
gh run list --workflow=release.yml --limit=1
gh run watch <run_id>

# 5. Verify:
gh release view vX.Y.Z
pip install --upgrade spec-kitty-cli && spec-kitty --version
```

Full docs: [CONTRIBUTING.md](CONTRIBUTING.md#release-process)

## Workspace-per-Work-Package Development (0.11.0+)

**Breaking change in 0.11.0**: Workspace model changed from workspace-per-feature to workspace-per-work-package.

### Planning Workflow

**All planning happens in main repository:**
- `/spec-kitty.specify` → Creates `kitty-specs/###-feature/` in main, commits to main
- `/spec-kitty.plan` → Creates `plan.md` in main, commits to main
- `/spec-kitty.tasks` → LLM creates `tasks.md` and `tasks/*.md` in main
- `spec-kitty agent feature finalize-tasks` → Parses dependencies, validates, commits to main
- All artifacts committed to main **before** implementation starts

**NO worktrees created during planning.**

### Implementation Workflow

**Worktrees created on-demand:**
- `spec-kitty implement WP01` → Creates `.worktrees/###-feature-WP01/`
- One worktree per work package (not per feature)
- Each WP has isolated workspace with dedicated branch

**Example implementation sequence:**
```bash
# After planning completes in main:
spec-kitty implement WP01              # Creates first workspace
spec-kitty implement WP02 --base WP01  # Creates second workspace from WP01
spec-kitty implement WP03              # Independent WP, parallel with WP02
```

### Dependency Handling

**Declare in WP frontmatter:**
```yaml
---
work_package_id: "WP02"
title: "Build API"
dependencies: ["WP01"]  # This WP depends on WP01
---
```

**Generated during `/spec-kitty.tasks` and `finalize-tasks`:**
- LLM creates tasks.md with dependency descriptions (phase grouping, explicit mentions)
- `finalize-tasks` parses dependencies from tasks.md
- Writes `dependencies: []` field to each WP's frontmatter
- Validates no cycles, no self-dependencies, no invalid references

**Use --base flag during implementation:**
```bash
spec-kitty implement WP02 --base WP01  # Branches from WP01's branch
```

**Multiple dependencies:**
- Git limitation: Can only branch from ONE base
- If WP04 depends on WP02 and WP03, use `--base WP03`, then manually merge WP02:
  ```bash
  spec-kitty implement WP04 --base WP03
  cd .worktrees/###-feature-WP04/
  git merge ###-feature-WP02
  ```

### Testing Requirements

**For workspace-per-WP features:**
- Write migration tests for template updates (parametrized across all 12 agents)
- Write integration tests for full workflow (specify → implement → merge)
- Write dependency graph tests (cycle detection, validation, inverse graph)

**Example test structure:**
```python
# tests/specify_cli/test_workspace_per_wp_migration.py
@pytest.mark.parametrize("agent_key", [
    "claude", "codex", "gemini", "cursor", "qwen", "opencode",
    "windsurf", "kilocode", "auggie", "roo", "copilot", "q"
])
def test_implement_template_updated(tmp_path, agent_key):
    """Verify implement.md template exists for all agents"""
    # Test implementation...
```

### Agent Template Updates

**When modifying workflow commands, update ALL 12 agents:**

Use `AGENT_DIRS` constant from migrations:
```python
from specify_cli.upgrade.migrations.m_0_9_1_complete_lane_migration import AGENT_DIRS

for agent_key, (agent_dir, _) in AGENT_DIRS.items():
    # Update template for this agent
```

**Test with migration test:**
```bash
pytest tests/specify_cli/test_workspace_per_wp_migration.py -v
```

**Template files to update (per agent):**
- `specify.md` - Remove worktree creation, document main repo workflow
- `plan.md` - Remove worktree references
- `tasks.md` - Document dependency generation, validation
- `implement.md` - NEW file for workspace-per-WP workflow with `--base` flag

### Review Warnings

**When WP enters review, check for dependents:**
```python
from specify_cli.core.dependency_graph import DependencyGraph

graph = DependencyGraph.build_graph(feature_dir)
dependents = graph.get_dependents("WP01")

if dependents:
    print(f"⚠️ {', '.join(dependents)} depend on WP01")
    print("If changes requested, they'll need rebase")
```

**Display during `/spec-kitty.review` if WP has downstream dependencies.**

### Status Tracking Behavior (Important for Agents)

**NOTE: Don't be confused by stale status in `/spec-kitty.status` output!**

WP status is tracked in the **main branch** via kitty-specs files. When you run `spec-kitty agent tasks move-task WP## --to for_review`, the status is committed to main. However:

1. **Your worktree may show stale status** - The kanban board reads from main, but your worktree's sparse checkout may not reflect the latest main commits immediately.

2. **Other agents may move your WP** - If a reviewer agent moves your WP back to "doing" (e.g., changes requested), the board will show "doing" even though you just moved it to "for_review".

3. **This is normal parallel workflow behavior** - Multiple agents work simultaneously. Status changes from other agents are expected. Focus only on YOUR assigned WP.

**Don't panic if:**
- You moved WP to "for_review" but the board shows "doing" → A reviewer may have started or requested changes
- You see commits from other WPs → Other agents are working in parallel, ignore them
- Status seems out of sync → The source of truth is the WP file in main branch

### Dogfooding: How This Feature Was Built

This workspace-per-WP feature (010) used the NEW model:

**Planning phase:**
- Ran `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks` in main
- NO worktrees created
- All artifacts committed to main (3 commits)

**Implementation phase:**
- WP01 (dependency graph) → Independent, branched from main
- WP02, WP03, WP06 → Parallel wave (3 agents simultaneously)
- WP04 → Depended on WP02 and WP03 (manual merge required)
- WP08, WP09 → Parallel wave (2 agents simultaneously)
- WP10 → Documentation (depended on everything)

**Timeline:**
- Legacy model (0.10.x): ~10 time units (sequential)
- Workspace-per-WP (0.11.0): ~6 time units (40% faster due to parallelization)

**Lessons learned:**
- Parallelization significantly reduces time-to-completion
- Dependency tracking in frontmatter works well
- Manual merges for multi-parent dependencies are annoying but manageable
- Review warnings prevent downstream rebase confusion
- Planning in main provides better visibility

### Common Patterns

**Linear chain:**
```
WP01 → WP02 → WP03
```
```bash
spec-kitty implement WP01
spec-kitty implement WP02 --base WP01
spec-kitty implement WP03 --base WP02
```

**Fan-out (parallel):**
```
        WP01
       /  |  \
    WP02 WP03 WP04
```
```bash
spec-kitty implement WP01
# After WP01 completes, run in parallel:
spec-kitty implement WP02 --base WP01 &
spec-kitty implement WP03 --base WP01 &
spec-kitty implement WP04 --base WP01 &
```

**Diamond (complex):**
```
        WP01
       /    \
    WP02    WP03
       \    /
        WP04
```
```bash
spec-kitty implement WP01
spec-kitty implement WP02 --base WP01 &  # Parallel
spec-kitty implement WP03 --base WP01 &  # Parallel
# After both complete:
spec-kitty implement WP04 --base WP03
cd .worktrees/###-feature-WP04/
git merge ###-feature-WP02  # Manual merge second dependency
```

### Migration to 0.11.0

**Before migrating:**
- Complete or delete all in-progress features (legacy worktrees)
- Use `spec-kitty list-legacy-features` to check
- Upgrade blocked if legacy worktrees exist

**Migration script (`m_0_11_0_workspace_per_wp.py`):**
- Detects legacy worktrees, blocks with actionable error
- Regenerates all agent templates with new workflow
- Updates mission templates (specify, plan, tasks, implement)

**Post-migration:**
- All new features use workspace-per-WP model
- Planning in main, worktrees on-demand
- Dependency tracking in frontmatter

### Troubleshooting

**"Base workspace does not exist":**
- Implement dependency first: `spec-kitty implement WP01`
- Then implement dependent: `spec-kitty implement WP02 --base WP01`

**"Circular dependency detected":**
- Fix tasks.md to remove cycle
- Ensure dependencies form a DAG (directed acyclic graph)

**"Legacy worktrees detected" during upgrade:**
- Complete or delete features before upgrading
- Use `spec-kitty list-legacy-features` to identify
- Follow [upgrading-to-0-11-0.md](docs/upgrading-to-0-11-0.md)

### Documentation

**For users:**
- [docs/workspace-per-wp.md](docs/workspace-per-wp.md) - Workflow guide with examples
- [docs/upgrading-to-0-11-0.md](docs/upgrading-to-0-11-0.md) - Migration instructions
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/quickstart.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/quickstart.md) - Quick reference

**For contributors:**
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/spec.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/spec.md) - Full specification
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/plan.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/plan.md) - Technical design
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/data-model.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/data-model.md) - Entities and relationships



## Merge & Preflight Patterns (0.11.0+)

When merging workspace-per-WP features, spec-kitty uses a preflight validation system and persistent merge state for resumable operations.

### Merge State Persistence

Merge progress is saved in `.kittify/merge-state.json` to enable resuming interrupted merges:

```json
{
  "feature_slug": "017-feature-name",
  "target_branch": "main",
  "wp_order": ["WP01", "WP02", "WP03"],
  "completed_wps": ["WP01"],
  "current_wp": "WP02",
  "has_pending_conflicts": false,
  "strategy": "merge",
  "started_at": "2026-01-18T10:00:00+00:00",
  "updated_at": "2026-01-18T10:30:00+00:00"
}
```

**MergeState dataclass fields** (`src/specify_cli/merge/state.py`):

| Field | Type | Description |
|-------|------|-------------|
| `feature_slug` | `str` | Feature identifier (e.g., "017-feature-name") |
| `target_branch` | `str` | Branch being merged into (e.g., "main") |
| `wp_order` | `list[str]` | Ordered list of WP IDs to merge |
| `completed_wps` | `list[str]` | WPs that have been successfully merged |
| `current_wp` | `str \| None` | WP currently being merged (if interrupted) |
| `has_pending_conflicts` | `bool` | True if git merge conflicts exist |
| `strategy` | `str` | "merge", "squash", or "rebase" |
| `started_at` | `str` | ISO timestamp when merge began |
| `updated_at` | `str` | ISO timestamp of last state update |

**Helper properties:**
- `remaining_wps` → List of WPs not yet merged
- `progress_percent` → Completion percentage (0-100)

**State functions (import from `specify_cli.merge`):**
```python
from specify_cli.merge import (
    MergeState,
    save_state,      # Persist state to JSON file
    load_state,      # Load state from JSON file (returns None if missing/invalid)
    clear_state,     # Remove state file
    has_active_merge,  # Check if state exists with remaining WPs
)
```

### Pre-flight Validation

Before any merge operation, `run_preflight()` validates all WP workspaces:

```python
from pathlib import Path
from specify_cli.merge import run_preflight, PreflightResult, WPStatus

result = run_preflight(
    feature_slug="017-feature",
    target_branch="main",
    repo_root=Path("."),
    wp_workspaces=[(Path(".worktrees/017-feature-WP01"), "WP01", "017-feature-WP01")],
)

if not result.passed:
    for error in result.errors:
        print(f"Error: {error}")
```

**PreflightResult dataclass fields:**

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | True if all checks passed |
| `wp_statuses` | `list[WPStatus]` | Status for each WP worktree |
| `target_diverged` | `bool` | True if target branch behind origin |
| `target_divergence_msg` | `str \| None` | Instructions for fixing divergence |
| `errors` | `list[str]` | List of error messages |
| `warnings` | `list[str]` | List of warning messages |

**WPStatus dataclass fields:**

| Field | Type | Description |
|-------|------|-------------|
| `wp_id` | `str` | Work package ID (e.g., "WP01") |
| `worktree_path` | `Path` | Path to worktree directory |
| `branch_name` | `str` | Git branch name |
| `is_clean` | `bool` | True if no uncommitted changes |
| `error` | `str \| None` | Error message if check failed |

**Checks performed:**
1. All expected WPs have worktrees (based on tasks in kitty-specs)
2. All worktrees are clean (no uncommitted changes)
3. Target branch is not behind origin

### Programmatic Access

**Check for active merge:**
```python
from pathlib import Path
from specify_cli.merge import load_state, has_active_merge

repo_root = Path(".")

if has_active_merge(repo_root):
    state = load_state(repo_root)
    print(f"Merge in progress: {state.feature_slug}")
    print(f"Progress: {len(state.completed_wps)}/{len(state.wp_order)}")
    print(f"Remaining: {', '.join(state.remaining_wps)}")
```

**Run preflight validation:**
```python
from pathlib import Path
from specify_cli.merge import run_preflight

wp_workspaces = [
    (Path(".worktrees/017-feature-WP01"), "WP01", "017-feature-WP01"),
    (Path(".worktrees/017-feature-WP02"), "WP02", "017-feature-WP02"),
]

result = run_preflight(
    feature_slug="017-feature",
    target_branch="main",
    repo_root=Path("."),
    wp_workspaces=wp_workspaces,
)

for status in result.wp_statuses:
    icon = "✓" if status.is_clean else "✗"
    print(f"{icon} {status.wp_id}: {status.error or 'clean'}")
```

**Conflict forecasting (dry-run):**
```python
from pathlib import Path
from specify_cli.merge import predict_conflicts

wp_workspaces = [
    (Path(".worktrees/017-feature-WP01"), "WP01", "017-feature-WP01"),
    (Path(".worktrees/017-feature-WP02"), "WP02", "017-feature-WP02"),
]

predictions = predict_conflicts(wp_workspaces, "main", Path("."))

for pred in predictions:
    auto = "auto" if pred.auto_resolvable else "manual"
    print(f"{pred.file_path}: {', '.join(pred.conflicting_wps)} ({auto})")
```

### Common Patterns

**Resume interrupted merge:**
```bash
spec-kitty merge --resume
```

**Abort and start fresh:**
```bash
spec-kitty merge --abort
```

**Preview merge with conflict forecast:**
```bash
spec-kitty merge --dry-run
```

**Merge from main branch:**
```bash
spec-kitty merge --feature 017-my-feature
```

### Implementation Files

- `src/specify_cli/merge/state.py` - MergeState dataclass, persistence functions
- `src/specify_cli/merge/preflight.py` - PreflightResult, WPStatus, validation checks
- `src/specify_cli/merge/executor.py` - Merge execution with state tracking
- `src/specify_cli/merge/forecast.py` - Conflict prediction for dry-run
- `src/specify_cli/merge/status_resolver.py` - Auto-resolution for status file conflicts
- `src/specify_cli/cli/commands/merge.py` - CLI command with --resume/--abort flags


## Agent Utilities for Work Package Status

**Quick Status Check (Recommended for Agents)**

Use the CLI command to check work package status:

```bash
spec-kitty agent tasks status
spec-kitty agent tasks status --feature 012-documentation-mission
```

**What You Get:**
- Kanban board (planned/doing/for_review/done lanes)
- Progress bar (█████░░░) with percentage
- Summary metrics panel

**When to Use:**
- Before starting work (check what's ready)
- During implementation (track progress)
- After completing a WP (see what's next)
- When planning parallelization (identify opportunities)

**Alternative (Python API):**

For programmatic access in Jupyter notebooks or scripts:

```python
from specify_cli.agent_utils.status import show_kanban_status

# Auto-detect feature or specify explicitly
result = show_kanban_status("012-documentation-mission")
```

Returns structured data:
```python
{
    'progress_percentage': 80.0,
    'done_count': 8,
    'total_wps': 10,
    'parallelization': {
        'ready_wps': [...],  # WPs that can start now
        'can_parallelize': True/False,  # Multiple WPs ready?
        'parallel_groups': [...]  # Grouping strategy
    }
}
```

## Documentation Mission Patterns (0.11.0+)

**When to Use Documentation Mission**:
- Creating comprehensive docs for a new project (initial mode)
- Filling gaps in existing documentation (gap-filling mode)
- Documenting a specific feature or component (feature-specific mode)

### Key Concepts

**Divio 4-Type System**:
- **Tutorial**: Learning-oriented, teaches beginners step-by-step
- **How-To**: Task-oriented, solves specific problems
- **Reference**: Information-oriented, describes APIs (often auto-generated)
- **Explanation**: Understanding-oriented, explains architecture and "why"

**Iteration Modes**:
- **initial**: Create docs from scratch (no gap analysis)
- **gap_filling**: Audit existing docs, prioritize gaps, fill high-priority missing content
- **feature_specific**: Document a specific feature/module only

**Generators**:
- **JSDoc**: JavaScript/TypeScript API reference (requires `npx`)
- **Sphinx**: Python API reference (requires `sphinx-build`)
- **rustdoc**: Rust API reference (requires `cargo`)

### Workflow

**Planning Phase**:
```bash
/spec-kitty.specify Create documentation [describe what you need]
# Prompts: iteration_mode, divio_types, target_audience, generators
/spec-kitty.plan [describe documentation structure and generators]
/spec-kitty.tasks
```

**Implementation Phase**:
```bash
/spec-kitty.implement
# Creates Divio templates, configures generators, generates API docs
/spec-kitty.review
/spec-kitty.accept
```

### Gap Analysis

**Gap-filling mode automatically**:
1. Detects documentation framework (Sphinx, MkDocs, Docusaurus, etc.)
2. Classifies existing docs by Divio type (frontmatter or content heuristics)
3. Builds coverage matrix (area × Divio type)
4. Identifies missing cells
5. Prioritizes gaps:
   - **HIGH**: Missing tutorials/reference for core features (blocks users)
   - **MEDIUM**: Missing how-tos, tutorials for advanced features
   - **LOW**: Missing explanations (nice-to-have)

**Output**: `gap-analysis.md` with coverage matrix, prioritized gaps, recommendations

### Generator Configuration

**Sphinx (Python)**:
```python
# docs/conf.py
extensions = [
    'sphinx.ext.autodoc',    # Generate from docstrings
    'sphinx.ext.napoleon',   # Google/NumPy style
    'sphinx.ext.viewcode',   # Link to source
]
```

**JSDoc (JavaScript/TypeScript)**:
```json
// jsdoc.json
{
  "source": {"include": ["src/"]},
  "opts": {"destination": "docs/api/javascript"}
}
```

**rustdoc (Rust)**:
```toml
# Cargo.toml
[package.metadata.docs.rs]
all-features = true
```

### State Management

Documentation state persisted in `meta.json`:
```json
{
  "documentation_state": {
    "iteration_mode": "gap_filling",
    "divio_types_selected": ["tutorial", "how-to", "reference"],
    "generators_configured": [
      {
        "name": "sphinx",
        "language": "python",
        "config_path": "docs/conf.py"
      }
    ],
    "target_audience": "developers",
    "last_audit_date": "2026-01-13T15:00:00Z",
    "coverage_percentage": 0.67
  }
}
```

### Common Patterns

**Initial project documentation**:
- Include all 4 Divio types
- Configure generator for primary language
- Create comprehensive suite (tutorial → reference → explanations)

**Gap-filling existing docs**:
- Run audit first (detects framework, classifies docs)
- Focus on HIGH priority gaps (tutorials, core reference)
- Iteratively improve coverage

**Feature-specific docs**:
- Select only relevant Divio types (e.g., how-to + reference for new API)
- Integrate with existing structure
- Update coverage metadata

### Troubleshooting

**Generator not found**:
```bash
# Install required tools
pip install sphinx sphinx-rtd-theme  # Python
npm install --save-dev jsdoc docdash  # JavaScript
curl --proto '=https' -sSf https://sh.rustup.rs | sh  # Rust
```

**Low confidence classification**:
Add frontmatter to existing docs:
```markdown
---
type: tutorial  # or how-to, reference, explanation
---
```

**Templates not populated**:
Replace all `[TODO: ...]` placeholders with actual content during validation phase.

### Documentation

**User Guide**: [docs/documentation-mission.md](docs/documentation-mission.md)
- Complete workflow with examples
- Generator setup instructions
- Divio type explanations
- Troubleshooting guide

**Implementation**:
- Mission config: `src/specify_cli/missions/documentation/mission.yaml`
- Generators: `src/specify_cli/doc_generators.py`
- Gap analysis: `src/specify_cli/gap_analysis.py`
- State management: `src/specify_cli/doc_state.py`

## Other Notes

Never claim something in the frontend works without Playwright proof.

- API responses don't guarantee UI works
- Frontend can break silently (404 caught, shows fallback)
- Always test the actual user experience, not just backend

## GitHub CLI Authentication for Organization Repos

When `gh` commands fail with "Missing required token scopes" error on organization repos:

**Problem**: GITHUB_TOKEN environment variable may have limited scopes (e.g., 'copilot' only)
**Solution**: Unset GITHUB_TOKEN to use keyring authentication which typically has broader scopes

```bash
# Check current auth status
gh auth status

# If GITHUB_TOKEN has limited scopes, unset it
unset GITHUB_TOKEN && gh issue comment <issue> --body "..."
unset GITHUB_TOKEN && gh issue close <issue>
```

**Background**:
- `gh` checks GITHUB_TOKEN env var first, then falls back to keyring
- GITHUB_TOKEN (ghp_*) may have limited scopes for security
- Keyring token (gho_*) often has full 'repo' scope
- For organization repos, you need 'repo' and 'read:org' scopes

**Verify fix worked**:
```bash
unset GITHUB_TOKEN && gh auth status
# Should show keyring token with 'repo' scope as active
```

<!-- MANUAL ADDITIONS END -->

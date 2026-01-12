# Spec Kitty Development Guidelines

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
- Migrations that update slash commands: Use `AGENT_DIRS` list
- Template changes: Will propagate to all agents via migration
- Testing: Verify at least .claude, .codex, .opencode (most common)

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

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11+ (existing spec-kitty codebase): Follow standard conventions

## Recent Changes
- 011-constitution-packaging-safety-and-redesign: Added psutil for cross-platform process management, relocated templates from .kittify/ to src/specify_cli/
- 010-workspace-per-work-package-for-parallel-development: Added workspace-per-WP model, dependency graph utilities, breaking change to 0.11.0
- 008-unified-python-cli: Added Python 3.11+ (existing spec-kitty requirement)
- 007-frontmatter-only-lane: Added Python 3.11+ (existing spec-kitty codebase) + pathlib, Rich (console output), ruamel.yaml (frontmatter parsing), typer (CLI)
- 005-refactor-mission-system: Added Python 3.11+ (existing spec-kitty codebase requirement)

<!-- MANUAL ADDITIONS START -->

## PyPI Release (Quick Reference)

**CRITICAL: NEVER create releases without explicit user instruction!**

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

### Future: jj Integration

Workspace-per-WP enables future jujutsu VCS integration:
- Automatic rebasing of dependent workspaces when parent changes
- No manual rebase needed for review feedback
- Multi-parent merges handled automatically

This foundation makes jj integration possible in future version.

### Documentation

**For users:**
- [docs/workspace-per-wp.md](docs/workspace-per-wp.md) - Workflow guide with examples
- [docs/upgrading-to-0-11-0.md](docs/upgrading-to-0-11-0.md) - Migration instructions
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/quickstart.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/quickstart.md) - Quick reference

**For contributors:**
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/spec.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/spec.md) - Full specification
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/plan.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/plan.md) - Technical design
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/data-model.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/data-model.md) - Entities and relationships

## Other Notes

Never claim something in the frontend works without Playwright proof.

- API responses don't guarantee UI works
- Frontend can break silently (404 caught, shows fallback)
- Always test the actual user experience, not just backend

<!-- MANUAL ADDITIONS END -->

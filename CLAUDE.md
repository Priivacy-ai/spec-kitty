# Spec Kitty Development Guidelines

## ⚠️ CRITICAL: Template Source Location (READ THIS FIRST!)

**When fixing bugs or updating templates, edit the SOURCE files, NOT the agent copies!**

| What | Location | Action |
|------|----------|--------|
| **SOURCE templates** | `src/doctrine/missions/mission-steps/` | ✅ EDIT THESE |
| **Agent copies** | `.claude/`, `.amazonq/`, `.augment/`, etc. | ❌ DO NOT EDIT |

The directories like `.claude/commands/`, `.amazonq/prompts/`, etc. are **GENERATED COPIES** that get deployed to projects that USE spec-kitty. They are NOT source code.

**To fix a template bug:**
```bash
# ✅ CORRECT: Edit the source template
vim src/doctrine/missions/mission-steps/software-dev/implement/prompt.md

# ❌ WRONG: Editing agent copies (these are generated, not source!)
vim .claude/commands/spec-kitty.implement.md  # NO!
vim .amazonq/prompts/spec-kitty.implement.md  # NO!
```

**How templates flow:**
```
src/doctrine/missions/mission-steps/{mission_type}/{step_id}/prompt.md  (SOURCE - edit here!)
    ↓ (deployed by migrations during `spec-kitty upgrade`)
.claude/commands/spec-kitty.*.md  (GENERATED COPY - don't edit!)
.amazonq/prompts/spec-kitty.*.md  (GENERATED COPY - don't edit!)
... (12 agent directories total)
.agents/skills/spec-kitty.*/SKILL.md  (Agent Skills - GENERATED COPY - don't edit!)
```

---

## Supported AI Agents

Spec Kitty supports **19 AI agents** total: 13 use the slash-command pipeline (Amazon Q/`q` retained as legacy alongside its rebrand Kiro) and 6 use the Agent Skills pipeline. When adding features that affect slash commands, migrations, or templates, ensure all command-layer agents are updated.

### Slash-Command Agents (13)

| Agent | Directory | Subdirectory | Slash Commands |
|-------|-----------|--------------|----------------|
| Claude Code | `.claude/` | `commands/` | `/spec-kitty.*` |
| GitHub Copilot | `.github/` | `prompts/` | `/spec-kitty.*` |
| Google Gemini | `.gemini/` | `commands/` | `/spec-kitty.*` |
| Cursor | `.cursor/` | `commands/` | `/spec-kitty.*` |
| Qwen Code | `.qwen/` | `commands/` | `/spec-kitty.*` |
| OpenCode | `.opencode/` | `command/` | `/spec-kitty.*` |
| Windsurf | `.windsurf/` | `workflows/` | `/spec-kitty.*` |
| Kilocode | `.kilocode/` | `workflows/` | `/spec-kitty.*` |
| Augment Code | `.augment/` | `commands/` | `/spec-kitty.*` |
| Roo Cline | `.roo/` | `commands/` | `/spec-kitty.*` |
| Amazon Q | `.amazonq/` | `prompts/` | `/spec-kitty.*` |
| Kiro | `.kiro/` | `prompts/` | `/spec-kitty.*` |
| Google Antigravity | `.agent/` | `workflows/` | `/spec-kitty.*` |

### Agent Skills Agents (6)

| Agent | Skills Root | Command Surface | Key |
|-------|-------------|-----------------|-----|
| Codex CLI | `.agents/skills/` | `$spec-kitty.<command>` | `codex` |
| Mistral Vibe | `.agents/skills/` via `.vibe/config.toml` `skill_paths` | `/spec-kitty.<command>` | `vibe` |
| Pi | `.agents/skills/` | `/skill:spec-kitty.<command>` | `pi` |
| Letta Code | `.agents/skills/` | Agent Skills | `letta` |

Codex, Vibe, Pi, and Letta share a single installation under `.agents/skills/spec-kitty.<command>/SKILL.md`. Codex, Pi, and Letta read that tree directly; Vibe is configured to read it via `.vibe/config.toml`. The manifest at `.kittify/command-skills-manifest.json` tracks which agents reference each skill package.

**New modules (mission 083):**
- `src/specify_cli/skills/command_renderer.py` — renders source templates into Agent Skills format
- `src/specify_cli/skills/command_installer.py` — installs/removes skill packages and updates the manifest
- `src/specify_cli/skills/manifest_store.py` — reads and writes `.kittify/command-skills-manifest.json`

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
- Python 3.11+ (existing spec-kitty codebase) + psutil (cross-platform process management) (011-charter-packaging-safety-and-redesign)
- Filesystem only (templates in src/specify_cli/, user projects in .kittify/) (011-charter-packaging-safety-and-redesign)
- Python 3.11+ (existing spec-kitty codebase) + subprocess (for JSDoc, Sphinx, rustdoc invocation), ruamel.yaml (YAML parsing) (012-documentation-mission)
- Filesystem only (mission configs in YAML, Divio templates in Markdown, iteration state in JSON) (012-documentation-mission)
- Markdown (documentation only) + None (pure documentation) (023-documentation-sprint-agent-management-cleanup)
- N/A (files only) (023-documentation-sprint-agent-management-cleanup)
- Python 3.11+ + typer, rich, ruamel.yaml, requests, pytest, mypy (047-namespace-aware-artifact-body-sync)
- SQLite (existing `OfflineQueue` DB file, new sibling table) (047-namespace-aware-artifact-body-sync)
- Python 3.11+ + stdlib `ast` (no new dependency), existing `safe_commit` from `specify_cli.git`, existing `scan_recovery_state` from `specify_cli.lanes.recovery` (068-post-merge-reliability-and-release-hardening)
- Filesystem only — `.kittify/config.yaml` gains a `merge.strategy` key; `kitty-specs/<mission>/status.events.jsonl` becomes the canonical surface for the FR-019 safe_commit fix (068-post-merge-reliability-and-release-hardening)

## Project Structure

```
architecture/           # Architectural design decisions and technical specifications
  ├── README.md        # Overview of architecture documentation
  ├── GIT_REPO_MANAGEMENT_IMPLEMENTATION.md  # Complete git repo management design
  ├── PHASE1_IMPLEMENTATION.md               # Base branch tracking spec
  └── PHASE2_IMPLEMENTATION.md               # Multi-parent merge spec
src/                   # Source code
  └── specify_cli/
      ├── glossary/      # Glossary semantic integrity pipeline + CLI surfaces (implemented)
      └── next/          # Canonical mission-next command loop integration (implemented)
      # Planned in future core/runtime work:
      # - core/events/   # Event ABCs, Pydantic models, factory (Feature 040 target)
      # - telemetry/     # JSONL event writer (Feature 040 target)
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

- 068-post-merge-reliability-and-release-hardening: Added new `src/specify_cli/post_merge/` package (stdlib `ast`-based stale-assertion analyzer), new `agent tests` CLI subgroup, populated `agent/release.py` stub with `prep` subcommand, FR-019 status-events safe_commit fix in `_run_lane_based_merge`, FR-021 `scan_recovery_state` extension + `implement --base` flag
- 047-namespace-aware-artifact-body-sync: Added Python 3.11+ + typer, rich, ruamel.yaml, requests, pytest, mypy
- 023-documentation-sprint-agent-management-cleanup: Added Markdown (documentation only) + None (pure documentation)
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
pipx install --force spec-kitty-cli==X.Y.Z && spec-kitty --version
```

Full docs: [CONTRIBUTING.md](CONTRIBUTING.md#release-process)

## Execution Workspace Strategy (2.x)

Current 2.x behavior is:

- Planning happens in the main repository checkout.
- `spec-kitty implement WP##` creates or reuses the **execution workspace** for that work package.
- If `lanes.json` exists, the execution workspace is lane-based: `.worktrees/<feature>-lane-<id>`.
- If `lanes.json` does not exist, the legacy fallback is one worktree per WP: `.worktrees/<feature>-WP##`.

### Planning Workflow

All planning artifacts are created and committed before implementation starts:

- `/spec-kitty.specify` creates `kitty-specs/<feature>/` artifacts in the main checkout
- `/spec-kitty.plan` writes planning artifacts in the main checkout
- `/spec-kitty.tasks` writes `tasks.md` and `tasks/*.md` in the main checkout
- `spec-kitty agent mission finalize-tasks` validates dependencies, writes any lane metadata, and commits the finalized task set

No worktrees are created during planning.

### Implementation Workflow

`spec-kitty implement WP##` is the only supported way to prepare a coding workspace.

- Lane-based feature: creates or reuses `.worktrees/<feature>-lane-a`, `.worktrees/<feature>-lane-b`, and so on
- Agent-facing workflow commands must print and consume the resolved workspace path instead of reconstructing it

Example:

```bash
# After planning completes in main:
spec-kitty implement WP01               # resolves the actual workspace for WP01
spec-kitty implement WP02               # reuses the lane workspace when WP02 is in the same lane
spec-kitty implement WP03               # independent WP, may land in another lane
```

If multiple dependent WPs land in one lane, that lane workspace is the only coding workspace for the sequence.

### Contributor Rules

When modifying workflow or orchestration behavior:

1. Update the runtime-owned resolver logic first.
2. Update all agent-facing wrappers to use the resolver instead of guessing workspace paths.
3. Update mission templates, skills, and docs together so they describe the same lane-only contract.

### Testing Expectations

Any execution-workspace change should include:

- unit coverage for workspace resolution
- integration coverage for `agent workflow implement/review`
- doc/template updates for affected command surfaces

Prefer tests that exercise both:

- lane-based features with shared worktrees

### Status Tracking Notes

Work package status remains tracked in the feature artifacts on the main branch. Execution workspaces may lag the latest status commit until they rebase or refresh. That is normal in parallel work:

- reviewers can move a WP back out of `for_review`
- other agents can advance other WPs concurrently
- the source of truth is the feature metadata on the main branch, not the currently opened worktree view

### References

- [docs/explanation/execution-lanes.md](docs/explanation/execution-lanes.md) - lane computation and worktree ownership
- [docs/explanation/git-worktrees.md](docs/explanation/git-worktrees.md) - git worktree mechanics
- [kitty-specs/010-workspace-per-work-package-for-parallel-development/spec.md](kitty-specs/010-workspace-per-work-package-for-parallel-development/spec.md) - original design history

## Merge & Preflight Patterns (0.11.0+)

When merging execution-workspace features, spec-kitty uses a preflight validation system and persistent merge state for resumable operations.

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

Before any merge operation, `run_preflight()` validates all resolved execution workspaces:

```python
from pathlib import Path
from specify_cli.merge import run_preflight, PreflightResult, WPStatus

result = run_preflight(
    feature_slug="017-feature",
    target_branch="main",
    repo_root=Path("."),
    wp_workspaces=[(Path(".worktrees/017-feature-lane-a"), "WP01", "kitty/mission-017-feature-lane-a")],
)

if not result.passed:
    for error in result.errors:
        print(f"Error: {error}")
```

**PreflightResult dataclass fields:**

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | True if all checks passed |
| `wp_statuses` | `list[WPStatus]` | Status for each resolved execution worktree |
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
    (Path(".worktrees/017-feature-lane-a"), "WP01", "kitty/mission-017-feature-lane-a"),
    (Path(".worktrees/017-feature-lane-b"), "WP02", "kitty/mission-017-feature-lane-b"),
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
    (Path(".worktrees/017-feature-lane-a"), "WP01", "kitty/mission-017-feature-lane-a"),
    (Path(".worktrees/017-feature-lane-b"), "WP02", "kitty/mission-017-feature-lane-b"),
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

## Status Model Patterns (034+, 060 cleanup)

The canonical status model uses an append-only event log per feature as the **sole authority** for WP lane state. Every lane transition is an immutable `StatusEvent` in `status.events.jsonl`. As of 3.0 (feature 060), frontmatter `lane` is no longer part of the active model -- it is retained only in migration code paths for backward compatibility with pre-3.0 features.

### Canonical Event Log Format

Each line in `status.events.jsonl` is a JSON object with sorted keys:

```json
{"actor":"claude","at":"2026-02-08T12:00:00+00:00","event_id":"01HXYZ...","evidence":null,"execution_mode":"worktree","feature_slug":"034-feature","force":false,"from_lane":"planned","reason":null,"review_ref":null,"to_lane":"claimed","wp_id":"WP01"}
```

### Key Functions

| Function | Module | Purpose |
|----------|--------|---------|
| `emit_status_transition()` | `status.emit` | Single entry point for all state changes (validate -> persist -> materialize -> views -> SaaS) |
| `reduce()` | `status.reducer` | Deterministic reducer: same events always produce same snapshot |
| `append_event()` / `read_events()` | `status.store` | JSONL I/O with corruption detection |
| `validate_transition()` | `status.transitions` | Check (from, to) against transition matrix + guard conditions |
| `resolve_phase()` | `status.phase` | Phase resolution: meta.json > config.yaml > default(1) |
| `resolve_lane_alias()` | `status.transitions` | Resolve `doing` -> `in_progress` at input boundaries |

### 9-Lane State Machine

```
planned -> claimed -> in_progress -> for_review -> in_review -> approved -> done
```

Plus: `blocked` (reachable from planned/claimed/in_progress/for_review/in_review/approved), `canceled` (reachable from all non-terminal lanes).

Alias: `doing` -> `in_progress` (resolved at input boundaries, never persisted in events).

Terminal lanes: `done`, `canceled` (force required to leave).

### Dependency Gating (WP claim readiness)

A work package whose `dependencies` frontmatter is non-empty cannot be claimed or
implemented until **every** declared dependency is in the `approved` **or** `done`
lane. This is "dependency readiness," computed by
`dependency_readiness_for_wp()` in `src/specify_cli/core/dependency_graph.py` and
enforced by the **dependency gate** at every claim path: `next` claim discovery
(`preview_claimable_wp`), `agent action implement`, the low-level `implement`
command (before any worktree is created), and orchestrator-api
`start-implementation` / `list-ready`.

`approved` satisfies the gate on purpose. `done` is emitted **only** by the
whole-mission `spec-kitty merge` (`_mark_wp_merged_done`), which itself refuses to
complete until every WP has reached `done`. Gating strictly on `done` would
therefore deadlock every same-mission dependency chain. This matches the merge
dependency gate (`policy/merge_gates.py`), which already treats `{approved, done}`
as satisfied. The read-only surfaces (`preview_claimable_wp`, `list-ready`) only
surface `planned` candidates, so a blocked WP is simply withheld. The imperative
verbs (`agent action implement`, `implement`, `start-implementation`) additionally
apply a resume guard: they enforce readiness only on the not-yet-started
(`planned`/`claimed`) claim transition, so re-invoking implement on an already
`in_progress` WP is a no-op resume, never re-gated. A blocked claim surfaces the
stable `dependencies_not_satisfied` reason/error. Independent WPs (no declared
dependencies) continue to fan out in parallel.

### Phase Behavior (3.0: Phase 2 is active)

Phase 2 (event-log authority) is the only active model as of 3.0. Phases 0 and 1 are historical.

| Phase | Write behavior | Read authority | Status |
|-------|---------------|----------------|--------|
| 0 (hardening) | No event log | Frontmatter only | **Historical** |
| 1 (dual-write) | Events + frontmatter | Frontmatter (events accumulate) | **Historical** |
| 2 (read-cutover) | Events are sole authority | `status.json` is derived snapshot | **Active (3.0)** |

Frontmatter `lane` is no longer written or read by active runtime commands. `finalize-tasks` bootstraps WP definitions; all subsequent status is tracked in `status.events.jsonl`.

### Package Architecture

```
src/specify_cli/status/
  __init__.py          # Public API exports
  models.py            # Lane enum, StatusEvent, DoneEvidence, StatusSnapshot
  transitions.py       # ALLOWED_TRANSITIONS, guards, alias resolution
  reducer.py           # reduce(), materialize() -- deterministic event -> snapshot
  store.py             # append_event(), read_events() -- JSONL I/O
  phase.py             # resolve_phase() -- 3-tier config precedence
  emit.py              # emit_status_transition() -- orchestration pipeline
  lane_reader.py       # get_wp_lane() -- canonical lane read (event log only)
  bootstrap.py         # bootstrap_feature_status() -- create initial events from finalize-tasks
  legacy_bridge.py     # update_frontmatter_views() -- compatibility views (historical)
  validate.py          # Schema, legality, drift validation
  doctor.py            # Health checks (stale claims, orphans, drift)
  reconcile.py         # Cross-repo drift detection and event generation
  migrate.py           # MIGRATION-ONLY: bootstrap event log from frontmatter state
  history_parser.py    # MIGRATION-ONLY: reconstruct transitions from legacy frontmatter
```

### Common Operations

```python
# Emit a transition (the standard way)
from specify_cli.status.emit import emit_status_transition
event = emit_status_transition(
    feature_dir=feature_dir, feature_slug="034-feature",
    wp_id="WP01", to_lane="claimed", actor="claude",
)

# Materialize snapshot from event log
from specify_cli.status.reducer import materialize
snapshot = materialize(feature_dir)

# Read events
from specify_cli.status.store import read_events
events = read_events(feature_dir)

# Validate transitions
from specify_cli.status.transitions import validate_transition
ok, error = validate_transition("planned", "claimed", actor="claude")

# Resolve phase
from specify_cli.status.phase import resolve_phase
phase, source = resolve_phase(repo_root, "034-feature")
```

### Documentation

- Operator docs: [docs/status-model.md](docs/status-model.md)
- Data model: [kitty-specs/034-feature-status-state-model-remediation/data-model.md](kitty-specs/034-feature-status-state-model-remediation/data-model.md)
- Quickstart: [kitty-specs/034-feature-status-state-model-remediation/quickstart.md](kitty-specs/034-feature-status-state-model-remediation/quickstart.md)

## Mission Identity Model (083+)

As of mission `083-mission-id-canonical-identity-migration`, every mission carries a ULID-based canonical identity in `meta.json`. The three-digit numeric prefix is display-only and is not assigned until merge time. This fixes the collision problem where two missions could share the same `NNN-` prefix and confuse selectors, branches, and dashboards.

**ADR:** [2026-04-09-1](architecture/adrs/2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md) - **Issue:** [Priivacy-ai/spec-kitty#557](https://github.com/Priivacy-ai/spec-kitty/issues/557)

### Identity Fields

| Field | Type | Role | When assigned |
|-------|------|------|---------------|
| `mission_id` | ULID (26 chars) | **Canonical machine identity**, immutable | At `mission create` |
| `mid8` | First 8 chars of `mission_id` | Short disambiguator used in branch / worktree names | Derived |
| `mission_slug` | Human-readable kebab slug (e.g. `my-feature`) | Human handle | At `mission create` |
| `mission_number` | `int \| None` | **Display-only** metadata, `null` pre-merge | At merge time, via `max(existing)+1` inside the merge-state lock |
| `friendly_name` | Title string | Human display | At `mission create` |

`mission_id` is the only field the runtime treats as identity. `mission_number` is never used for lookup, locking, or event routing.

### Branch and Worktree Naming

- **Branch:** `kitty/mission-<human-slug>-<mid8>-lane-<id>` (e.g. `kitty/mission-my-feature-01J6XW9K-lane-a`)
- **Worktree:** `.worktrees/<human-slug>-<mid8>-lane-<id>` (e.g. `.worktrees/my-feature-01J6XW9K-lane-a`)

The `<mid8>` segment guarantees two missions with the same human slug never collide on disk or in git refs.

### Selector Disambiguation

`spec-kitty agent context resolve --mission <handle>` resolves handles against `mission_id` first, then against `mid8`, then against `mission_slug`. Ambiguous handles produce a **structured error** listing the candidates; there is **no silent fallback** to the first match. WP07 removed fallback semantics on purpose — any code path that reintroduces them is a regression.

The dashboard scanner (WP09) is keyed by `mission_id` and surfaces distinct rows for every duplicate prefix, so operators can tell collisions apart at a glance.

### Migration

Pre-083 projects have `mission_number` as identity and no `mission_id`. Operators upgrade via:

```bash
spec-kitty doctor identity --json          # audit current state
spec-kitty migrate backfill-identity       # mint mission_id for legacy missions
spec-kitty doctor identity --json          # confirm zero legacy state
```

Backfill is additive-only: existing `mission_number` values are preserved, a `mission_id` is minted, and branch/worktree names rename on the next `implement` cycle.

Full runbook: [docs/migration/mission-id-canonical-identity.md](docs/migration/mission-id-canonical-identity.md).

## Agent Utilities for Work Package Status

**Quick Status Check (Recommended for Agents)**

Use the CLI command to check work package status:

```bash
spec-kitty agent tasks status
spec-kitty agent tasks status --feature 012-documentation-mission
```

**What You Get:**
- Kanban board (planned/claimed/in_progress/for_review/in_review/approved/done/blocked/canceled lanes)
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

## Shared Package Boundary (post-cutover)

As of mission `shared-package-boundary-cutover-01KQ22DS` (2026-04-25):

- **Runtime**: CLI-internal under `src/specify_cli/next/_internal_runtime/`. The standalone `spec-kitty-runtime` PyPI package is retired; the CLI does not depend on it.
- **Events**: external PyPI dependency. Consumed only via `spec_kitty_events.*` public imports. The vendored copy under `src/specify_cli/spec_kitty_events/` was removed.
- **Tracker**: external PyPI dependency. Consumed only via `spec_kitty_tracker.*` public imports.
- **Compatibility ranges** live in `pyproject.toml`; **exact pins** live in `uv.lock`.
- **Editable / path overrides** for events / tracker are dev-only; never committed in `pyproject.toml`'s `[tool.uv.sources]`. Consult [`docs/development/local-overrides.md`](docs/development/local-overrides.md) for the dev workflow.

Architectural enforcement of these invariants lives in `tests/architectural/test_shared_package_boundary.py` and `tests/architectural/test_pyproject_shape.py`. The clean-install verification job in `.github/workflows/ci-quality.yml` (`clean-install-verification`) proves `spec-kitty next` works in a fresh venv without `spec-kitty-runtime`.

ADR: [`architecture/3.x/adr/2026-04-25-1-shared-package-boundary.md`](architecture/3.x/adr/2026-04-25-1-shared-package-boundary.md). Migration runbook: [`docs/migration/shared-package-boundary-cutover.md`](docs/migration/shared-package-boundary-cutover.md).

## Charter Activation and Doctrine Integrity Model (org-doctrine-profile-integrity-activation-closure-01KT1TV1)

This section documents the charter activation/cascade subsystem, the canonical kind vocabulary, and the DRG profile-lineage relation introduced by the org-doctrine-profile-integrity mission. Governing ADR: [`architecture/3.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md`](architecture/3.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md).

### Charter Activation Engine (`charter.activation_engine`)

The plan/commit seam separates validation from mutation. `plan_activation()` validates the artifact ID and kind against the live doctrine catalog; `commit_activation()` writes to config only after the plan succeeds. This guarantees the activation/deactivation commands cannot corrupt configuration on unknown-ID failure.

```python
# Plan step: validates ID, returns an ActivationPlan (non-mutating)
plan = plan_activation(kind="directive", artifact_id="010-...", pack_context=ctx)

# Commit step: writes to .kittify/config.yaml
commit_activation(plan, project_root=Path("."))
```

**`CharterPackConfigError`** (`charter.pack_context`): raised on malformed `.kittify/config.yaml` charter-pack shape. Activation and context entry points catch it and present its `CHARTER_PACK_CONFIG_INVALID` code + remediation as a fail-closed error; no activation state is mutated. The symbol has live external callers (CLI entry points) and is no longer in the dead-symbol allowlist.

**Key rules:**
- `charter activate` / `charter deactivate` do NOT mutate config on validation failure (NFR-003).
- Projects with no explicit activation restrictions continue to behave as pre-#1535 (FR-021 backward compatibility).

### Charter Cascade (`charter.cascade`)

Cascade activation / deactivation follows DRG `requires` and `suggests` reference edges rather than hardcoded per-kind special cases. Scope is explicit:

```bash
# Activate with cascade — all referenced kinds
charter activate mission-type research --cascade all

# Activate with cascade — selected referenced kinds only
charter activate mission-type research --cascade agent-profile,tactic

# Deactivate with cascade (shared-reference safety: skips artifacts still referenced elsewhere)
charter deactivate mission-type research --cascade all
```

Without `--cascade`, the command completes the direct activation and warns about referenced artifacts that were not cascaded, naming the skipped kinds and a suggested recovery command (FR-013).

**Shared-reference safety (C-005):** cascade deactivation never removes an artifact still referenced by another active artifact; skipped entries include the active artifact that still references them.

### Canonical Kind Vocabulary (`doctrine.artifact_kinds` + `charter.kind_vocabulary`)

A single canonical mapping (`charter.kind_vocabulary.from_operator_token`) normalises all operator-facing kind tokens across `charter context --include`, `charter activate`, `charter deactivate`, and `charter list`. Hyphenated forms are normalised to canonical doctrine kinds at input boundaries:

| Operator token | Canonical kind |
|----------------|----------------|
| `agent-profile` | `agent_profile` |
| `mission-step-contract` | `mission_step_contract` |
| `directive` | `directive` |
| `tactic` | `tactic` |
| `styleguide` | `styleguide` |
| `toolguide` | `toolguide` |
| `paradigm` | `paradigm` |
| `template` | `template` |
| `mission-type` (special) | raises `MissionTypeNotAnArtifactKind` — mission types are addressed separately |

`charter list --all` includes all artifact kinds (including `template`) across built-in, org-pack, and project layers, each annotated with its source layer.

### `specializes_from` DRG Lineage Relation

Profile lineage is represented as a DRG edge — not a field on the profile model — per the C-009 binding constraint (DRG is canonical source of truth for doctrine relationships).

```yaml
# Org-pack DRG fragment: declare a profile as a specialization of a built-in
nodes:
  - urn: "urn:profile:my-analyst"
    kind: agent_profile
    id: my-analyst
edges:
  - source: "urn:profile:my-analyst"
    target: "urn:profile:researcher-ryan"   # built-in
    relation: specializes_from
```

**Key rules:**
- `specializes_from` is DISTINCT from `delegates_to` (runtime work handoff). Delegation consumers do not receive lineage edges; lineage consumers do not receive delegation edges.
- Profile hierarchy resolution (`AgentProfileRepository.resolve_profile`) follows `specializes_from` edges via DRG traversal, not the retired per-profile `specializes_from` field.
- The retired field form is rejected at load time (`test_relationship_fields_rejected.py` full negative matrix).
- Augmentation relations (`enhances`, `overrides`) are also DRG edges; the `specializes_from` relation is intentionally excluded from the intent-advisory logic.

**Field-merge semantics for topology-bearing kinds** (mission step contracts and mission types): `enhances` field-merges preserving action-sequence ordering and step I/O contracts; `overrides` is full replacement. Silently dropping steps or stripping step I/O is rejected. Governing ADR: `architecture/3.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md`.

### Profile Load Diagnostics

`AgentProfileRepository.skipped_profiles` exposes structured diagnostics for profiles that failed to load, without requiring callers to rescan the filesystem. `DoctrineService.agent_profiles` preserves diagnostics across all configured layers. `spec-kitty doctor doctrine --json` includes the diagnostics as a stable machine-readable field.

A pack with invalid agent profiles is NOT reported as fully healthy by `doctor doctrine`, even if its DRG node/edge counts are otherwise valid (FR-010).

### Deferred Items (DIRECTIVE_013 Trackers)

Filed DIRECTIVE_013 trackers (deferred, non-blocking):

- **Upstream `coordination.status_service` dead-symbol debt** (5 symbols, pre-existing on `upstream/main` via #1614): [Priivacy-ai/spec-kitty#1622](https://github.com/Priivacy-ai/spec-kitty/issues/1622). (The related `status.lifecycle_events` pair was resolved in WP04, not deferred.)
- **FR-012 (`doctor.py` god-module split, I-10)**: [Priivacy-ai/spec-kitty#1623](https://github.com/Priivacy-ai/spec-kitty/issues/1623).
- **FR-013 (`_tag_source` provenance sidecar typing, I-11)**: [Priivacy-ai/spec-kitty#1624](https://github.com/Priivacy-ai/spec-kitty/issues/1624). The generic `TypeVar` fix (the I-3 mypy class) was landed in WP04; only the `Provenanced[T]` sidecar refactor is deferred.

Absorbed in this close-out (not tracked — fixed directly): the pre-existing pytest-marker gate failures (`git_repo`/convention markers on 6 non-mission test files) were greened as an operator-approved boyscout scope increase rather than tracker-only.

<!-- MANUAL ADDITIONS END -->

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore

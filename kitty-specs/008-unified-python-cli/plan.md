# Implementation Plan: Unified Python CLI for Agents

**Branch**: `008-unified-python-cli` | **Date**: 2025-12-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/008-unified-python-cli/spec.md`

## Summary

Migrate all bash scripts (~2,600 lines) to unified Python CLI under `spec-kitty agent` namespace, eliminating worktree script copying and providing AI agents with reliable, location-aware command interface. Research phase validated approach is feasible with high confidence. Implementation structured for maximum parallelization after foundation phase.

**Core Problem Solved**: AI agents struggle with bash script locations, path confusion, and script copying to worktrees. New approach: agents call `spec-kitty agent <command>` from anywhere, CLI handles path resolution automatically.

**Key Deliverables**:
1. `spec-kitty agent` CLI namespace with 20+ commands
2. Automatic path resolution (worktree-aware)
3. `spec-kitty upgrade` migration for existing projects
4. Complete bash script elimination
5. 90%+ test coverage for agent commands

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement)

**Primary Dependencies**:
- Typer (CLI framework, already in use)
- Rich (console output, already in use)
- pathlib (path manipulation, stdlib)
- subprocess (git operations, stdlib)
- pytest (testing framework, already in use)

**Storage**: Filesystem only (no database)
- YAML metadata (`.kittify/metadata.yaml`)
- Markdown files (spec.md, plan.md, task prompts)
- Git repository state

**Testing**: pytest with unit + integration tests
- Target: 90%+ coverage for `src/specify_cli/cli/commands/agent/` namespace
- Integration tests verify commands work from main repo and worktrees
- Cross-platform CI (Windows, macOS, Linux)

**Target Platform**: Cross-platform CLI
- macOS (primary development)
- Linux (CI/CD and production)
- Windows (fallback with file copy instead of symlinks)

**Project Type**: Single Python package (spec-kitty CLI extension)

**Performance Goals**:
- Command execution <100ms for simple operations (path resolution, validation)
- Command execution <5s for complex operations (worktree creation, migration)
- Negligible overhead vs current bash implementation

**Constraints**:
- Must maintain existing `spec-kitty` CLI user experience (no breaking changes for user commands)
- Must preserve upgrade migration infrastructure patterns
- Must work identically in main repo and worktrees
- Must support idempotent upgrade migration (safe to re-run)
- Must handle broken symlinks and Windows gracefully

**Scale/Scope**:
- ~2,600 lines of bash code to eliminate
- 24 bash scripts to migrate
- 20+ agent commands to implement
- 10+ slash command templates to update
- All existing spec-kitty projects must be upgradeable

## Constitution Check

*GATE: Must pass before implementation.*

**Note**: Project constitution file is not yet populated. For this infrastructure migration, applying standard spec-kitty development principles:

### Principles Applied

✅ **Single Responsibility**: Each agent command module (`feature.py`, `tasks.py`, `context.py`, `release.py`) handles one domain
✅ **DRY (Don't Repeat Yourself)**: Consolidate bash path resolution (5 implementations) → single Python path resolver
✅ **Testability**: All agent commands unit + integration testable (90%+ coverage requirement)
✅ **Cross-Platform**: Python + pathlib ensures Windows/macOS/Linux compatibility
✅ **Simplicity**: Eliminate 2,600 lines of bash, unified command interface for agents
✅ **Backward Compatibility for Users**: User commands (`spec-kitty init`, `spec-kitty merge`) unchanged
⚠️ **Breaking Changes for Agents**: Slash commands must be updated (automated via `spec-kitty upgrade`)

### Gates

**Gate 1: No unnecessary complexity**
- ✅ PASS - Eliminates bash complexity, doesn't add new patterns
- Justification: Consolidating to single language (Python) reduces overall system complexity

**Gate 2: Existing patterns reused**
- ✅ PASS - Reuses Typer sub-app pattern, existing path resolution logic, proven migration infrastructure
- Evidence: `m_0_9_0_frontmatter_only.py` migration precedent

**Gate 3: Breaking changes justified**
- ✅ PASS - Clean cut migration justified by eliminating unmaintainable bash, improving agent reliability
- Mitigation: Automated upgrade via `spec-kitty upgrade`, clear migration guide

**Gate 4: Test coverage mandatory**
- ✅ PASS - 90%+ coverage requirement for agent namespace (FR-026, FR-027)

**Constitution Check Result**: ✅ **PASS** - Proceed with implementation

## Project Structure

### Documentation (this feature)

```
kitty-specs/008-unified-python-cli/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (in progress)
├── research.md          # Phase 0 research findings (complete)
├── data-model.md        # Key entities and relationships (complete)
├── quickstart.md        # Developer quick-start guide (pending)
├── checklists/
│   └── requirements.md  # Spec quality validation (complete)
├── research/
│   ├── evidence-log.csv        # Research evidence (complete)
│   └── source-register.csv     # Source citations (complete)
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/
│   ├── commands/
│   │   ├── init.py              # User command (existing, unchanged)
│   │   ├── merge.py             # User command (existing, unchanged)
│   │   ├── upgrade.py           # User command (existing, will extend)
│   │   └── agent/               # NEW: Agent command namespace
│   │       ├── __init__.py      # Agent CLI registration (Phase 1)
│   │       ├── feature.py       # Feature lifecycle commands (Phase 2)
│   │       ├── context.py       # Agent context management (Phase 4)
│   │       ├── tasks.py         # Task workflow commands (Phase 3)
│   │       └── release.py       # Release packaging commands (Phase 5)
│   └── __init__.py              # Main CLI (update in Phase 1)
├── core/
│   ├── paths.py                 # Path resolution (enhance in Phase 1)
│   ├── git_ops.py               # Git operations (existing, may enhance)
│   ├── worktree.py              # NEW: Worktree management (Phase 2)
│   └── agent_context.py         # NEW: CLAUDE.md processing (Phase 4)
├── upgrade/
│   └── migrations/
│       └── m_0_10_0_python_only.py  # NEW: Bash elimination migration (Phase 6)
└── tasks_support.py             # Existing task logic (refactor in Phase 3)

tests/
├── unit/
│   └── agent/                   # NEW: Agent command unit tests (Phases 2-5)
│       ├── test_feature.py
│       ├── test_tasks.py
│       ├── test_context.py
│       └── test_release.py
└── integration/
    └── test_agent_workflows.py  # NEW: End-to-end agent tests (Phase 7)

.kittify/scripts/bash/           # DELETE in Phase 6
.github/workflows/scripts/       # DELETE in Phase 6

.claude/commands/                # UPDATE in Phase 6
├── spec-kitty.specify.md        # Update to call spec-kitty agent
├── spec-kitty.plan.md
├── spec-kitty.tasks.md
├── spec-kitty.implement.md
├── spec-kitty.review.md
├── spec-kitty.accept.md
└── spec-kitty.merge.md
```

**Structure Decision**: Single project extension (Option 1). This is an enhancement to existing spec-kitty CLI, not a new standalone project. New code integrates into existing `src/specify_cli/` structure under `cli/commands/agent/` namespace and `core/` utilities.

## Parallel Work Analysis

### Dependency Graph

```
Phase 1: Foundation (Sequential - Days 1-2)
├── Core infrastructure must complete before parallel work
└── Sets up: agent namespace, enhanced path resolution, base utilities

↓

Wave 1: Command Implementation (Parallel - Days 3-6)
├── Stream A: Feature Commands (Phase 2, Days 3-4)
│   └── Implements: create-feature, check-prerequisites, setup-plan
├── Stream B: Task Commands (Phase 3, Days 5-6)
│   └── Implements: move-task, mark-status, validate-workflow
└── Stream C: Context Commands (Phase 4, Day 7)
    └── Implements: update-context

↓ (Context can overlap with release)

Wave 2: Advanced Features (Parallel - Day 8)
└── Stream D: Release Commands (Phase 5, Day 8)
    └── Implements: build-release (CI/CD integration)

↓

Phase 6: Cleanup & Migration (Sequential - Days 9-10)
├── Requires: All command streams complete
└── Implements: Bash deletion, template updates, upgrade migration

↓

Phase 7: Validation (Sequential - Day 11)
├── Requires: All implementation complete
└── Verifies: End-to-end workflows, cross-platform, upgrade process
```

### Work Distribution

**Sequential Work (Phase 1 - Foundation)**:
- Create `src/specify_cli/cli/commands/agent/__init__.py` with Typer sub-app registration
- Create stub modules: `feature.py`, `context.py`, `tasks.py`, `release.py`
- Enhance `src/specify_cli/core/paths.py` with worktree detection
- Register agent sub-app in main CLI
- Test: `spec-kitty agent --help` shows subcommands

**Parallel Streams (Phases 2-5)**:

**Stream A: Feature Commands** (can start after Phase 1)
- Owner: Agent Alpha
- Files: `src/specify_cli/cli/commands/agent/feature.py`, `src/specify_cli/core/worktree.py`
- Commands: `create-feature`, `check-prerequisites`, `setup-plan`
- Dependencies: Phase 1 complete
- No conflicts with: Streams B, C, D (different modules)

**Stream B: Task Commands** (can start after Phase 1)
- Owner: Agent Beta
- Files: `src/specify_cli/cli/commands/agent/tasks.py`
- Commands: `move-task`, `mark-status`, `list-tasks`, `add-history`, `rollback-task`, `validate-workflow`
- Dependencies: Phase 1 complete, migrate `tasks_cli.py` → Typer
- No conflicts with: Streams A, C, D (different modules)

**Stream C: Context Commands** (can start after Phase 1, overlaps with Stream D)
- Owner: Agent Gamma
- Files: `src/specify_cli/cli/commands/agent/context.py`, `src/specify_cli/core/agent_context.py`
- Commands: `update-context`
- Dependencies: Phase 1 complete
- No conflicts with: Streams A, B, D (different modules)

**Stream D: Release Commands** (can start after Phase 1, overlaps with Stream C)
- Owner: Agent Delta
- Files: `src/specify_cli/cli/commands/agent/release.py`, `src/specify_cli/core/release.py`
- Commands: `build-release`
- Dependencies: Phase 1 complete
- No conflicts with: Streams A, B, C (different modules)

**Sequential Work (Phase 6 - Cleanup)**: Requires ALL streams complete
- Delete bash scripts
- Update slash command templates
- Create upgrade migration
- Update documentation

**Sequential Work (Phase 7 - Validation)**: Requires Phase 6 complete
- End-to-end workflow testing
- Cross-platform validation
- Upgrade migration testing

### Coordination Points

**Sync 1: After Phase 1 (Day 2)**
- Foundation complete, all parallel streams can begin
- Verify: `spec-kitty agent --help` works, path resolution tested
- Handoff: Each stream gets foundation utilities

**Sync 2: After Streams A+B Complete (Day 6)**
- Feature and Task commands functional
- Verify: Basic agent workflows work (create feature, move tasks)
- Continue: Streams C+D can still run in parallel

**Sync 3: After All Streams Complete (Day 8)**
- All agent commands implemented
- Verify: `spec-kitty agent --help` shows all commands, JSON modes work
- Proceed: Begin Phase 6 cleanup

**Sync 4: After Phase 6 (Day 10)**
- Bash scripts deleted, templates updated, migration created
- Verify: Upgrade migration works on test project
- Proceed: Begin Phase 7 validation

**Integration Tests Schedule**:
- Daily: Each stream runs its own unit tests
- Sync 1-4: Integration tests verify cross-stream compatibility
- Phase 7: Full end-to-end workflow validation

## Phase 1: Core Infrastructure (Sequential - Days 1-2)

**Goal**: Establish foundation for all parallel work streams

**Prerequisites**: Research complete ✅

**Work Items**:

1. Create agent command structure:
   - `src/specify_cli/cli/commands/agent/__init__.py` - Typer sub-app registration
   - `src/specify_cli/cli/commands/agent/feature.py` - Empty module with stub
   - `src/specify_cli/cli/commands/agent/context.py` - Empty module with stub
   - `src/specify_cli/cli/commands/agent/tasks.py` - Empty module with stub
   - `src/specify_cli/cli/commands/agent/release.py` - Empty module with stub

2. Register agent namespace in main CLI:
   - Update `src/specify_cli/cli/commands/__init__.py` to import and register agent sub-app
   - Update `src/specify_cli/__init__.py` if needed for CLI entry point

3. Enhance path resolution utilities:
   - Review `src/specify_cli/core/paths.py` (existing)
   - Add/enhance worktree detection logic
   - Add environment variable support (`SPECIFY_REPO_ROOT`)
   - Ensure broken symlink handling (is_symlink() before exists())

4. Testing infrastructure:
   - Create `tests/unit/agent/` directory
   - Create `tests/integration/` directory
   - Set up pytest fixtures for worktree testing

**Acceptance Criteria**:
- ✅ `spec-kitty agent --help` displays help text
- ✅ All stub modules import without errors
- ✅ Path resolution works from main repo and worktree
- ✅ Test infrastructure runs `pytest` successfully

**Estimated Effort**: 2 days

**Blockers**: None

**Output**: Foundation ready for parallel command implementation

## Phase 2: Feature Management Commands (Stream A - Days 3-4)

**Goal**: Migrate feature lifecycle bash scripts to Python

**Prerequisites**: Phase 1 complete ✅

**Dependencies**: None (can run in parallel with Phases 3-5)

**Work Items**:

1. Create `src/specify_cli/core/worktree.py`:
   - `create_feature_worktree(repo_root, feature_slug)` - migrates `create-new-feature.sh` logic
   - `get_next_feature_number(repo_root)` - determines next feature number
   - `setup_feature_directory(feature_dir)` - creates directory structure, symlinks/copies
   - `validate_feature_structure(feature_dir)` - migrates `check-prerequisites.sh` logic

2. Implement `src/specify_cli/cli/commands/agent/feature.py`:
   - `create-feature` command with `--json` flag
   - `check-prerequisites` command with `--json`, `--paths-only`, `--include-tasks` flags
   - `setup-plan` command with `--json` flag
   - All commands support dual output (JSON for agents, Rich for humans)

3. Update slash command templates:
   - `.claude/commands/spec-kitty.specify.md` - call `spec-kitty agent create-feature`
   - `.claude/commands/spec-kitty.plan.md` - call `spec-kitty agent setup-plan`

4. Testing:
   - Unit tests for worktree utilities
   - Unit tests for feature commands
   - Integration test: Create feature from main repo and worktree

**Acceptance Criteria**:
- ✅ `spec-kitty agent create-feature "test-feature" --json` creates worktree and returns JSON
- ✅ `spec-kitty agent check-prerequisites` validates feature structure
- ✅ Commands work identically from main repo and worktree
- ✅ 90%+ test coverage for feature.py and worktree.py

**Estimated Effort**: 2 days

**Blockers**: Requires Phase 1 foundation

**Output**: Feature lifecycle commands functional, ready for agent use

## Phase 3: Task Workflow Commands (Stream B - Days 5-6)

**Goal**: Migrate task management bash scripts to Python

**Prerequisites**: Phase 1 complete ✅

**Dependencies**: None (can run in parallel with Phases 2, 4, 5)

**Work Items**:

1. Migrate `tasks_cli.py` (argparse) to Typer:
   - Convert 850 lines of argparse-based CLI to Typer decorators
   - Preserve all existing functionality (move, mark-status, list, history, rollback)
   - Move to `src/specify_cli/cli/commands/agent/tasks.py`

2. Implement agent task commands:
   - `move-task` - Move work package between lanes with `--json` flag
   - `mark-status` - Update task checkbox status with `--json` flag
   - `list-tasks` - List tasks by lane with `--json` flag
   - `add-history` - Add history entry to task with `--json` flag
   - `rollback-task` - Rollback lane move with `--json` flag
   - `validate-workflow` - Validate task metadata with `--json` flag

3. Update slash command templates:
   - `.claude/commands/spec-kitty.implement.md` - call `spec-kitty agent move-task`
   - `.claude/commands/spec-kitty.review.md` - call `spec-kitty agent validate-workflow`

4. Testing:
   - Unit tests for all task commands
   - Integration test: Full task workflow (planned → doing → for_review → done)

**Acceptance Criteria**:
- ✅ `spec-kitty agent move-task WP01 --to doing --json` moves task and returns JSON
- ✅ All 6 task commands functional with JSON output
- ✅ Commands work from main repo and worktree
- ✅ 90%+ test coverage for tasks.py

**Estimated Effort**: 2 days

**Blockers**: Requires Phase 1 foundation

**Output**: Task workflow commands functional, `tasks_cli.py` eliminated

## Phase 4: Agent Context Management (Stream C - Day 7)

**Goal**: Migrate agent context update bash script to Python

**Prerequisites**: Phase 1 complete ✅

**Dependencies**: None (can run in parallel with Phases 2, 3, 5)

**Work Items**:

1. Create `src/specify_cli/core/agent_context.py`:
   - `parse_plan_for_tech_stack(plan_path)` - Extract tech stack from plan.md
   - `update_agent_context(agent_type, tech_stack, feature_dir)` - Update CLAUDE.md, GEMINI.md, etc.
   - `preserve_manual_additions(content, markers)` - Preserve content between `<!-- MANUAL ADDITIONS -->` markers
   - Support 12 agent types (Claude, Gemini, Copilot, Cursor, Windsurf, etc.)

2. Implement `src/specify_cli/cli/commands/agent/context.py`:
   - `update-context` command with `--json`, `--agent-type` flags
   - Template processing for agent-specific context files
   - Preserve manual additions

3. Update slash command templates:
   - `.claude/commands/spec-kitty.plan.md` - call `spec-kitty agent update-context`

4. Testing:
   - Unit tests for context parsing and preservation
   - Integration test: Update context for multiple agent types

**Acceptance Criteria**:
- ✅ `spec-kitty agent update-context --json` updates CLAUDE.md with tech stack from plan
- ✅ Manual additions between markers are preserved
- ✅ Works for all 12 agent types
- ✅ 90%+ test coverage for context.py and agent_context.py

**Estimated Effort**: 1 day

**Blockers**: Requires Phase 1 foundation

**Output**: Agent context management functional, `update-agent-context.sh` eliminated

## Phase 5: Release Packaging (Stream D - Day 8)

**Goal**: Migrate GitHub Actions CI scripts to Python

**Prerequisites**: Phase 1 complete ✅

**Dependencies**: None (can run in parallel with Phases 2, 3, 4)

**Work Items**:

1. Create `src/specify_cli/core/release.py`:
   - `get_next_version(repo_root)` - Migrates `get-next-version.sh`
   - `update_version(repo_root, version)` - Migrates `update-version.sh`
   - `generate_release_notes(repo_root, version)` - Migrates `generate-release-notes.sh`
   - `create_release_packages(repo_root, version)` - Migrates `create-release-packages.sh`
   - `create_github_release(version, notes)` - Migrates `create-github-release.sh`

2. Implement `src/specify_cli/cli/commands/agent/release.py`:
   - `build-release` command with `--json`, `--version`, `--dry-run` flags
   - Orchestrates full release workflow
   - Validates version alignment (tag, pyproject.toml, CHANGELOG.md)

3. Update GitHub Actions workflow:
   - `.github/workflows/release.yml` - Replace bash script calls with `spec-kitty agent build-release`

4. Testing:
   - Unit tests for release utilities
   - Integration test: Full release workflow (dry-run mode)

**Acceptance Criteria**:
- ✅ `spec-kitty agent build-release --dry-run --json` executes release workflow without publishing
- ✅ All 6 GitHub Actions bash scripts eliminated
- ✅ Works in CI/CD environment
- ✅ 90%+ test coverage for release.py

**Estimated Effort**: 1 day

**Blockers**: Requires Phase 1 foundation

**Output**: Release packaging functional, CI bash scripts eliminated

## Phase 6: Cleanup & Migration (Sequential - Days 9-10)

**Goal**: Remove bash scripts, update templates, create upgrade migration

**Prerequisites**: Phases 1-5 complete ✅

**Dependencies**: ALL command streams must complete before cleanup

**Work Items**:

1. Create upgrade migration:
   - `src/specify_cli/upgrade/migrations/m_0_10_0_python_only.py`
   - Detect bash scripts in `.kittify/scripts/bash/`
   - Update slash command templates in `.claude/commands/*.md`
   - Clean up worktree bash script copies
   - Detect and warn on custom bash modifications
   - Implement idempotent execution (version tracking)

2. Delete bash scripts:
   - Remove entire `scripts/bash/` directory
   - Remove entire `.github/workflows/scripts/` directory
   - Update `.gitignore` if needed

3. Update all slash command templates:
   - Scan `.claude/commands/*.md` for bash script references
   - Replace with `spec-kitty agent` command equivalents
   - Update mission templates in `templates/missions/*/command-templates/`

4. Update documentation:
   - `CONTRIBUTING.md` - Remove bash sections, add agent commands
   - `README.md` - Document new `spec-kitty agent` namespace
   - Create migration guide for custom bash scripts

5. Testing:
   - Test upgrade migration on example project
   - Verify all bash scripts removed
   - Verify all slash commands updated

**Acceptance Criteria**:
- ✅ Upgrade migration successfully updates test project
- ✅ All bash scripts deleted from main repository
- ✅ All slash command templates reference `spec-kitty agent` commands
- ✅ Migration is idempotent (safe to re-run)
- ✅ Custom modifications detected and warned

**Estimated Effort**: 2 days

**Blockers**: Requires all command implementations complete (Phases 2-5)

**Output**: Bash scripts eliminated, projects can upgrade

## Phase 7: Testing & Validation (Sequential - Day 11)

**Goal**: Validate all workflows work end-to-end

**Prerequisites**: Phase 6 complete ✅

**Dependencies**: ALL previous phases complete

**Work Items**:

1. Test full feature workflow:
   - `/spec-kitty.specify` → creates feature
   - `/spec-kitty.plan` → creates plan, updates context
   - `/spec-kitty.tasks` → generates tasks
   - `/spec-kitty.implement` → moves tasks through lanes
   - `/spec-kitty.review` → validates and marks done
   - `/spec-kitty.accept` → acceptance workflow
   - `/spec-kitty.merge` → merges and cleans up

2. Test release workflow:
   - `spec-kitty agent build-release --dry-run`
   - Verify all packages created
   - Test in GitHub Actions CI environment

3. Test upgrade migration:
   - Create test project with old bash structure
   - Run `spec-kitty upgrade`
   - Verify migration succeeded
   - Test workflows in upgraded project

4. Cross-platform validation:
   - Run CI tests on macOS
   - Run CI tests on Linux
   - Run CI tests on Windows (verify file copy fallback)

5. Performance validation:
   - Measure command execution time vs bash baseline
   - Verify <100ms for simple commands, <5s for complex commands

**Acceptance Criteria**:
- ✅ All spec-kitty workflows complete without errors
- ✅ Upgrade migration works on test projects
- ✅ CI passes on all platforms (Windows, macOS, Linux)
- ✅ Performance meets targets (<100ms simple, <5s complex)
- ✅ Zero path-related errors in agent execution

**Estimated Effort**: 1 day

**Blockers**: Requires everything complete

**Output**: Validated, production-ready feature

## Implementation Timeline (Parallelized)

**Total Duration**: 11 days with parallelization (vs 11 days sequential)

| Day | Phase | Work Streams | Coordination |
|-----|-------|--------------|--------------|
| 1-2 | Phase 1 | Foundation (sequential) | Sync 1: Foundation complete |
| 3-4 | Phase 2 | Stream A: Feature Commands | Independent |
| 5-6 | Phase 3 | Stream B: Task Commands | Independent |
| 7 | Phase 4 | Stream C: Context Commands | Independent |
| 8 | Phase 5 | Stream D: Release Commands | Independent |
|  | | | Sync 3: All streams complete |
| 9-10 | Phase 6 | Cleanup & Migration (sequential) | Sync 4: Migration ready |
| 11 | Phase 7 | Validation (sequential) | Final validation |

**Parallelization Benefit**: Phases 2-5 (6 days of work) execute concurrently across 4 agents, reducing to ~4 days of calendar time with proper coordination.

**Critical Path**: Phase 1 (2d) → Longest parallel stream (2d) → Phase 6 (2d) → Phase 7 (1d) = ~7 days minimum with perfect parallelization

## Risk Management

### Risk 1: Parallel Stream Conflicts
- **Description**: Multiple agents editing related code could create merge conflicts
- **Mitigation**: Strict module separation (each stream owns different `.py` files), daily integration tests
- **Severity**: Low (clean module boundaries)

### Risk 2: Foundation Phase Delays
- **Description**: Phase 1 delays block all parallel work
- **Mitigation**: Prioritize Phase 1 completion, minimal scope (stubs only)
- **Severity**: Medium (critical path dependency)

### Risk 3: Cross-Platform Testing Gaps
- **Description**: Development on macOS may miss Windows-specific issues
- **Mitigation**: CI runs on all platforms, early testing in Phase 1
- **Severity**: Low (existing patterns for Windows compatibility)

### Risk 4: Upgrade Migration Edge Cases
- **Description**: Custom bash modifications may break automated migration
- **Mitigation**: Migration detects modifications, provides warnings and manual guide
- **Severity**: Medium (affects subset of users)

### Risk 5: Integration Test Failures
- **Description**: Parallel streams may integrate incorrectly despite unit tests passing
- **Mitigation**: Daily integration tests at coordination points, final validation in Phase 7
- **Severity**: Low (integration points are well-defined)

## Success Metrics

**Code Quality**:
- 90%+ test coverage for `src/specify_cli/cli/commands/agent/`
- All tests pass on Windows, macOS, Linux
- Ruff linter passes with zero violations

**Agent Reliability**:
- 0% path-related error rate in agent execution
- 95%+ reduction in agent retry behavior
- All spec-kitty workflows complete without errors

**Migration Success**:
- 100% of bash scripts eliminated (~2,600 lines)
- 100% of test projects upgrade successfully
- Migration is idempotent (safe to re-run)

**Performance**:
- Simple commands <100ms execution time
- Complex commands <5s execution time
- No measurable overhead vs bash baseline

## Open Questions

None - all planning questions answered, research validated approach.

## Next Steps

After this plan is approved:

1. **Run `/spec-kitty.tasks`** to generate work packages from this plan
2. **Assign work packages** to parallel streams (Agents Alpha, Beta, Gamma, Delta)
3. **Execute Phase 1** sequentially (foundation)
4. **Launch parallel streams** (Phases 2-5) after Sync 1
5. **Converge for cleanup** (Phase 6) after Sync 3
6. **Final validation** (Phase 7) before merge

**Coordination**: Use daily sync points to verify integration, resolve blockers, and track progress across parallel streams.

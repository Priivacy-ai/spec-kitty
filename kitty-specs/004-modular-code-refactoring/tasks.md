# Tasks: Modular Code Refactoring
*Path: kitty-specs/004-modular-code-refactoring/tasks.md*

**Feature ID**: 004-modular-code-refactoring
**Feature Name**: Modular Code Refactoring
**Created**: 2025-11-11
**Status**: Ready for Implementation
**Developer Count**: 6 (parallel execution enabled)

## Summary

This task breakdown refactors two monolithic Python files (5,730 total lines) into a modular architecture with ~21 modules, each under 200 lines. The plan enables up to 6 agents to work in parallel using a hybrid layer-module approach with clear ownership boundaries.

## Work Packages

### Setup Phase

#### WP01: Foundation Layer [Priority: P1] ✅
**Goal**: Create core infrastructure modules that all other packages depend on
**Prompt**: `tasks/done/WP01-foundation-layer.md`
**Owner**: codex (shell_pid: 18347)
**Reviewer**: claude
**Duration**: Day 1
**Status**: ✅ APPROVED

**Summary**: Extract fundamental utilities, configuration, and UI components that form the base layer for all other modules.

**Subtasks**:
- [X] T001: Create package directory structure (src/specify_cli/core/, cli/, template/, dashboard/)
- [X] T002: Extract all constants and configuration to core/config.py (92 lines)
- [X] T003: Extract shared utility functions to core/utils.py (43 lines)
- [X] T004: Extract StepTracker class to cli/step_tracker.py (91 lines)
- [X] T005: Extract menu selection functions to cli/ui.py (192 lines)
- [X] T006: Create __init__.py files with proper exports for each package
- [X] T007: Write unit tests for core/config.py
- [X] T008: Write unit tests for core/utils.py
- [X] T009: Write unit tests for cli/ui.py

**Dependencies**: None (foundation layer)
**Risks**: All other work depends on this; must be completed first
**Verification**: ✅ Unit tests pass, all imports working, modules integrated successfully

---

### Foundational Phase

#### WP02: Dashboard Infrastructure [Priority: P2] [P]
**Goal**: Extract dashboard static assets and core scanning/diagnostic functions
**Prompt**: `tasks/planned/WP02-dashboard-infrastructure.md`
**Owner**: Agent A
**Duration**: Days 2-3

**Summary**: Extract embedded HTML/CSS/JS strings to files and create dashboard utility modules.

**Subtasks**:
- [ ] T010: Extract embedded HTML from dashboard.py to dashboard/templates/index.html (~500 lines) [P]
- [ ] T011: Extract embedded CSS to dashboard/static/dashboard.css (~1000 lines) [P]
- [ ] T012: Extract embedded JavaScript to dashboard/static/dashboard.js (~300 lines) [P]
- [ ] T013: Extract scan_all_features() to dashboard/scanner.py (~60 lines)
- [ ] T014: Extract scan_feature_kanban() to dashboard/scanner.py (~55 lines)
- [ ] T015: Extract get_feature_artifacts() and get_workflow_status() to dashboard/scanner.py (~50 lines)
- [ ] T016: Extract run_diagnostics() to dashboard/diagnostics.py (~150 lines)
- [ ] T017: Create dashboard package __init__.py with public API exports
- [ ] T018: Write integration tests for scanner.py
- [ ] T019: Write integration tests for diagnostics.py

**Dependencies**: WP01 (core/config.py, core/utils.py)
**Risks**: Large HTML/CSS/JS extraction may have formatting issues
**Verification**: Dashboard loads correctly, scanner finds features, diagnostics run

#### WP03: Template System [Priority: P2] [P]
**Goal**: Create template management and rendering infrastructure
**Prompt**: `tasks/planned/WP03-template-system.md`
**Owner**: Agent B
**Duration**: Days 2-3

**Summary**: Extract template discovery, copying, rendering, and asset generation functions.

**Subtasks**:
- [ ] T020: Extract get_local_repo_root() to template/manager.py (~15 lines)
- [ ] T021: Extract copy_specify_base_from_local() to template/manager.py (~55 lines)
- [ ] T022: Extract copy_specify_base_from_package() to template/manager.py (~50 lines)
- [ ] T023: Extract copy_package_tree() to template/manager.py (~15 lines)
- [ ] T024: Extract parse_frontmatter() to template/renderer.py (~25 lines)
- [ ] T025: Extract render_template() and rewrite_paths() to template/renderer.py (~110 lines)
- [ ] T026: Extract generate_agent_assets() to template/asset_generator.py (~30 lines)
- [ ] T027: Extract render_command_template() to template/asset_generator.py (~100 lines)
- [ ] T028: Create template package __init__.py with exports
- [ ] T029: Write unit tests for template operations

**Dependencies**: WP01 (core/config.py)
**Risks**: Template path resolution complexity
**Verification**: Templates render correctly, assets generate properly

#### WP04: Core Services [Priority: P2] [P]
**Goal**: Extract git operations, project resolution, and tool checking
**Prompt**: `tasks/planned/WP04-core-services.md`
**Owner**: Agent C
**Duration**: Days 2-3

**Summary**: Create service modules for git operations, path resolution, and tool verification.

**Subtasks**:
- [ ] T030: Extract is_git_repo() to core/git_ops.py (~20 lines)
- [ ] T031: Extract init_git_repo() to core/git_ops.py (~25 lines)
- [ ] T032: Extract run_command() to core/git_ops.py (~20 lines)
- [ ] T033: Extract get_current_branch() helper to core/git_ops.py (~15 lines)
- [ ] T034: Extract locate_project_root() to core/project_resolver.py (~10 lines)
- [ ] T035: Extract resolve_template_path() to core/project_resolver.py (~20 lines)
- [ ] T036: Extract resolve_worktree_aware_feature_dir() to core/project_resolver.py (~45 lines)
- [ ] T037: Extract get_active_mission_key() to core/project_resolver.py (~35 lines)
- [ ] T038: Extract check_tool() and check_all_tools() to core/tool_checker.py (~40 lines)
- [ ] T039: Write unit tests for each service module

**Dependencies**: WP01 (core/utils.py)
**Risks**: Git operations must maintain exact behavior
**Verification**: All git commands work, paths resolve correctly

---

### Story-Based Development Phase

#### WP05: Dashboard Handlers [Priority: P3] [P]
**Goal**: Refactor HTTP request handling into modular handler classes
**Prompt**: `tasks/planned/WP05-dashboard-handlers.md`
**Owner**: Agent D
**Duration**: Days 4-5

**Summary**: Split monolithic DashboardHandler into specialized endpoint handlers.

**Subtasks**:
- [ ] T040: Create dashboard/handlers/base.py with BaseHandler class (~100 lines)
- [ ] T041: Extract health and shutdown endpoints to dashboard/handlers/api.py (~80 lines)
- [ ] T042: Extract feature-related endpoints to dashboard/handlers/features.py (~150 lines)
- [ ] T043: Extract static file serving to dashboard/handlers/static.py (~50 lines)
- [ ] T044: Extract start_dashboard() to dashboard/server.py (~70 lines)
- [ ] T045: Extract find_free_port() to dashboard/server.py (~35 lines)
- [ ] T046: Extract dashboard lifecycle functions to dashboard/lifecycle.py (~198 lines)
- [ ] T047: Update dashboard/__init__.py with ensure_dashboard_running() and stop_dashboard()
- [ ] T048: Write HTTP endpoint tests
- [ ] T049: Write subprocess import tests

**Dependencies**: WP02 (dashboard infrastructure)
**Risks**: HTTP routing must remain compatible
**Verification**: All dashboard endpoints respond correctly

#### WP06: CLI Commands Extraction [Priority: P3] [P]
**Goal**: Extract CLI commands (except init) into separate modules
**Prompt**: `tasks/planned/WP06-cli-commands.md`
**Owner**: Agent E
**Duration**: Days 4-5

**Summary**: Move each CLI command to its own module for better organization and testing.

**Subtasks**:
- [ ] T050: Extract check command to cli/commands/check.py (~60 lines)
- [ ] T051: Extract research command to cli/commands/research.py (~150 lines)
- [ ] T052: Extract accept command to cli/commands/accept.py (~130 lines)
- [ ] T053: Extract merge command to cli/commands/merge.py (~240 lines)
- [ ] T054: Extract verify_setup command to cli/commands/verify.py (~65 lines)
- [ ] T055: Extract dashboard command to cli/commands/dashboard.py (~95 lines)
- [ ] T056: Create cli/commands/__init__.py with command registration
- [ ] T057: Extract BannerGroup and helpers to cli/helpers.py (~80 lines)
- [ ] T058: Write integration tests for each command
- [ ] T059: Verify command registration in main app

**Dependencies**: WP01 (cli/ui.py), WP04 (core services)
**Risks**: Command registration must preserve CLI interface
**Verification**: All commands work identically to before

#### WP07: GitHub Client and Init Command [Priority: P3] [P]
**Goal**: Extract GitHub operations and refactor the complex init command
**Prompt**: `tasks/planned/WP07-github-init.md`
**Owner**: Agent F
**Duration**: Days 4-5

**Summary**: Create GitHub client module and break down the massive init command.

**Subtasks**:
- [ ] T060: Extract download_template_from_github() to template/github_client.py (~120 lines)
- [ ] T061: Extract download_and_extract_template() to template/github_client.py (~200 lines)
- [ ] T062: Extract GitHub auth helpers to template/github_client.py (~10 lines)
- [ ] T063: Extract parse_repo_slug() to template/github_client.py (~5 lines)
- [ ] T064: Begin extracting init command to cli/commands/init.py (setup, ~50 lines)
- [ ] T065: Extract init interactive prompts logic (~100 lines)
- [ ] T066: Extract init template mode detection (~30 lines)
- [ ] T067: Extract init main orchestration loop (~120 lines)
- [ ] T068: Mock GitHub API for testing
- [ ] T069: Test init command with all flags

**Dependencies**: WP03 (template system)
**Risks**: Init is the most complex command with many edge cases
**Verification**: Init works for all modes (local/package/remote)

---

### Polish Phase

#### WP08: Integration and Cleanup [Priority: P4]
**Goal**: Update main __init__.py, fix imports, and ensure everything works together
**Prompt**: `tasks/planned/WP08-integration-cleanup.md`
**Owner**: 1-2 developers
**Duration**: Day 6

**Summary**: Final integration to ensure all modules work together correctly.

**Subtasks**:
- [ ] T070: Update main __init__.py to import from new modules (~150 lines final)
- [ ] T071: Remove old monolithic code from __init__.py
- [ ] T072: Fix any circular imports discovered during integration
- [ ] T073: Update all import statements to use new module paths
- [ ] T074: Ensure subprocess imports work (try/except patterns)
- [ ] T075: Run full regression test suite
- [ ] T076: Test pip installation with new structure
- [ ] T077: Test development mode imports
- [ ] T078: Update documentation for new structure
- [ ] T079: Performance verification (startup time, command response)

**Dependencies**: WP01-WP07 (all previous work)
**Risks**: Integration issues, import resolution problems
**Verification**: All tests pass, pip install works, performance unchanged

---

## Parallelization Strategy

### Execution Timeline
```
Day 1: WP01 (Sequential - Foundation)
Days 2-3: WP02, WP03, WP04 (Parallel - Wave 1)
Days 4-5: WP05, WP06, WP07 (Parallel - Wave 2)
Day 6: WP08 (Sequential - Integration)
```

### Agent Assignments
- **Foundation**: Single agent creates base modules
- **Agent A**: WP02 - Dashboard Infrastructure
- **Agent B**: WP03 - Template System
- **Agent C**: WP04 - Core Services
- **Agent D**: WP05 - Dashboard Handlers
- **Agent E**: WP06 - CLI Commands
- **Agent F**: WP07 - GitHub & Init
- **Integration**: 1-2 agents for final assembly

### Coordination Points
- End of Day 1: Foundation complete, all agents pull latest
- End of Day 3: Wave 1 complete, merge and sync
- End of Day 5: Wave 2 complete, ready for integration
- Day 6: Final integration and testing

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import resolution failures | High | High | Try/except pattern, test all contexts |
| Behavioral changes | Medium | High | Comprehensive tests before refactor |
| Merge conflicts | Low | Medium | Exclusive file ownership |
| Performance regression | Low | Medium | Benchmark before/after |
| Missing functionality | Low | High | Keep old files as reference |

## Definition of Done

- [ ] All modules under 200 lines (excluding comments/docstrings)
- [ ] No circular imports
- [ ] All existing tests pass
- [ ] New unit tests for each module
- [ ] Import compatibility verified (local/pip/subprocess)
- [ ] CLI commands work identically to before
- [ ] Dashboard functionality unchanged
- [ ] Performance metrics maintained
- [ ] Documentation updated
- [ ] Code formatted with black/ruff

## MVP Scope

**Minimum Viable Refactor**: WP01 (Foundation Layer)

The foundation layer alone provides value by:
- Centralizing configuration
- Extracting reusable UI components
- Creating the package structure
- Enabling incremental refactoring

This allows the team to validate the approach before committing to the full refactoring.

## Notes

- Subtasks marked with [P] can be done in parallel (different files)
- Each work package has a corresponding prompt file in tasks/planned/
- Agents must sync at end of each day to avoid drift
- Keep original files as reference until WP08 cleanup
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

#### WP02: Dashboard Infrastructure [Priority: P2] ✅
**Goal**: Extract dashboard static assets and core scanning/diagnostic functions
**Prompt**: `tasks/done/WP02-dashboard-infrastructure.md`
**Owner**: codex (shell_pid: 57706)
**Reviewer**: sonnet-4.5
**Duration**: Days 2-3
**Status**: ✅ APPROVED

**Summary**: Extract embedded HTML/CSS/JS strings to files and create dashboard utility modules.

**Subtasks**:
- [X] T010: Extract embedded HTML from dashboard.py to dashboard/templates/index.html (~500 lines)
- [X] T011: Extract embedded CSS to dashboard/static/dashboard.css (~1000 lines)
- [X] T012: Extract embedded JavaScript to dashboard/static/dashboard.js (~300 lines)
- [X] T013: Extract scan_all_features() to dashboard/scanner.py (~60 lines)
- [X] T014: Extract scan_feature_kanban() to dashboard/scanner.py (~55 lines)
- [X] T015: Extract get_feature_artifacts() and get_workflow_status() to dashboard/scanner.py (~50 lines)
- [X] T016: Extract run_diagnostics() to dashboard/diagnostics.py (~150 lines)
- [X] T017: Create dashboard handlers directory structure
- [X] T018: Extract base DashboardHandler class to handlers/base.py
- [X] T019: Extract server initialization to dashboard/server.py
- [X] T020: Extract lifecycle management to dashboard/lifecycle.py
- [X] T021: Extract static assets
- [X] T022: Update dashboard __init__.py with proper exports
- [X] T023: Test static file extraction
- [X] T024: Test infrastructure modules (including diagnostics)
- [X] T025: Test import resolution

**Dependencies**: WP01 (core/config.py, core/utils.py)
**Risks**: Large HTML/CSS/JS extraction may have formatting issues
**Verification**: ✅ Dashboard loads correctly, 13/13 tests passing, all modules compliant

#### WP03: Template System [Priority: P2] ✅
**Goal**: Create template management and rendering infrastructure
**Prompt**: `tasks/done/WP03-template-system.md`
**Owner**: codex (shell_pid: 32837)
**Reviewer**: sonnet-4.5
**Duration**: Days 2-3
**Status**: ✅ APPROVED

**Summary**: Extract template discovery, copying, rendering, and asset generation functions.

**Subtasks**:
- [X] T020: Extract get_local_repo_root() to template/manager.py (~15 lines)
- [X] T021: Extract copy_specify_base_from_local() to template/manager.py (~55 lines)
- [X] T022: Extract copy_specify_base_from_package() to template/manager.py (~50 lines)
- [X] T023: Extract copy_package_tree() to template/manager.py (~15 lines)
- [X] T024: Extract parse_frontmatter() to template/renderer.py (~25 lines)
- [X] T025: Extract render_template() and rewrite_paths() to template/renderer.py (~110 lines)
- [X] T026: Extract generate_agent_assets() to template/asset_generator.py (~30 lines)
- [X] T027: Extract render_command_template() to template/asset_generator.py (~100 lines)
- [X] T028: Create template package __init__.py with exports
- [X] T029: Write unit tests for template operations

**Dependencies**: WP01 (core/config.py)
**Risks**: Template path resolution complexity
**Verification**: ✅ Templates render correctly, assets generate properly, all 9 tests passing

#### WP04: Core Services [Priority: P2] ✅
**Goal**: Extract git operations, project resolution, and tool checking
**Prompt**: `tasks/done/WP04-core-services.md`
**Owner**: codex (shell_pid: 33775)
**Reviewer**: sonnet-4.5
**Duration**: Days 2-3
**Status**: ✅ APPROVED

**Summary**: Create service modules for git operations, path resolution, and tool verification.

**Subtasks**:
- [X] T030: Extract is_git_repo() to core/git_ops.py (~20 lines)
- [X] T031: Extract init_git_repo() to core/git_ops.py (~25 lines)
- [X] T032: Extract run_command() to core/git_ops.py (~20 lines)
- [X] T033: Extract get_current_branch() helper to core/git_ops.py (~15 lines)
- [X] T034: Extract locate_project_root() to core/project_resolver.py (~10 lines)
- [X] T035: Extract resolve_template_path() to core/project_resolver.py (~20 lines)
- [X] T036: Extract resolve_worktree_aware_feature_dir() to core/project_resolver.py (~45 lines)
- [X] T037: Extract get_active_mission_key() to core/project_resolver.py (~35 lines)
- [X] T038: Extract check_tool() and check_all_tools() to core/tool_checker.py (~40 lines)
- [X] T039: Write unit tests for each service module

**Dependencies**: WP01 (core/utils.py)
**Risks**: Git operations must maintain exact behavior
**Verification**: ✅ All git commands work, paths resolve correctly, 19/19 tests passing

---

### Story-Based Development Phase

#### WP05: Dashboard Handlers [Priority: P3] ✅
**Goal**: Refactor HTTP request handling into modular handler classes
**Prompt**: `tasks/done/WP05-dashboard-handlers.md`
**Owner**: agent-d
**Reviewer**: sonnet-4.5
**Duration**: Days 4-5
**Status**: ✅ APPROVED

**Summary**: Split monolithic DashboardHandler into specialized endpoint handlers.

**Subtasks**:
- [X] T040: Implement APIHandler in dashboard/handlers/api.py (71 lines)
- [X] T041: Implement FeatureHandler in dashboard/handlers/features.py (231 lines)
- [X] T042: Implement StaticHandler in dashboard/handlers/static.py (50 lines)
- [X] T043: Implement DashboardRouter in dashboard/handlers/router.py (69 lines)
- [X] T044: HTTP endpoint functionality verified through tests
- [X] T045: Subprocess import tests passing

**Dependencies**: WP02 (dashboard infrastructure)
**Risks**: HTTP routing must remain compatible
**Verification**: ✅ All dashboard endpoints respond correctly, 13/13 tests passing

#### WP06: CLI Commands Extraction [Priority: P3] [P] ✅
**Goal**: Extract CLI commands (except init) into separate modules
**Prompt**: `tasks/done/WP06-cli-commands.md`
**Owner**: codex (shell_pid: multiple)
**Reviewer**: sonnet-4.5
**Duration**: Days 4-5
**Status**: ✅ APPROVED

**Summary**: Move each CLI command to its own module for better organization and testing.

**Subtasks**:
- [X] T050: Extract check command to cli/commands/check.py (~60 lines)
- [X] T051: Extract research command to cli/commands/research.py (~150 lines)
- [X] T052: Extract accept command to cli/commands/accept.py (~130 lines)
- [X] T053: Extract merge command to cli/commands/merge.py (~240 lines)
- [X] T054: Extract verify_setup command to cli/commands/verify.py (~65 lines)
- [X] T055: Extract dashboard command to cli/commands/dashboard.py (~95 lines)
- [X] T056: Create cli/commands/__init__.py with command registration
- [X] T057: Extract BannerGroup and helpers to cli/helpers.py (~80 lines)
- [X] T058: Write integration tests for each command
- [X] T059: Verify command registration in main app

**Dependencies**: WP01 (cli/ui.py), WP04 (core services)
**Risks**: Command registration must preserve CLI interface
**Verification**: ✅ All commands work identically to before, tests passing

#### WP07: GitHub Client and Init Command [Priority: P3] [P] ✅
**Goal**: Extract GitHub operations and refactor the complex init command
**Prompt**: `tasks/done/WP07-github-init.md`
**Owner**: codex (shell_pid: multiple)
**Reviewer**: sonnet-4.5
**Duration**: Days 4-5
**Status**: ✅ APPROVED

**Summary**: Create GitHub client module and break down the massive init command.

**Subtasks**:
- [X] T060: Extract download_template_from_github() to template/github_client.py (~120 lines)
- [X] T061: Extract download_and_extract_template() to template/github_client.py (~200 lines)
- [X] T062: Extract GitHub auth helpers to template/github_client.py (~10 lines)
- [X] T063: Extract parse_repo_slug() to template/github_client.py (~5 lines)
- [X] T064: Begin extracting init command to cli/commands/init.py (setup, ~50 lines)
- [X] T065: Extract init interactive prompts logic (~100 lines)
- [X] T066: Extract init template mode detection (~30 lines)
- [X] T067: Extract init main orchestration loop (~120 lines)
- [X] T068: Mock GitHub API for testing
- [X] T069: Test init command with all flags

**Dependencies**: WP03 (template system)
**Risks**: Init is the most complex command with many edge cases
**Verification**: ✅ Init works for all modes (local/package/remote), tests passing

---

### Polish Phase

#### WP08: Integration and Cleanup [Priority: P4] ✅
**Goal**: Update main __init__.py, fix imports, and ensure everything works together
**Prompt**: `tasks/done/WP08-integration-cleanup.md`
**Owner**: sonnet-4.5 (shell_pid: 50329)
**Reviewer**: sonnet-4.5
**Duration**: Day 6
**Status**: ✅ APPROVED

**Summary**: Final integration to ensure all modules work together correctly.

**Subtasks**:
- [X] T070: Update main __init__.py to import from new modules (~150 lines final)
- [X] T071: Remove old monolithic code from __init__.py
- [X] T072: Fix any circular imports discovered during integration
- [X] T073: Update all import statements to use new module paths
- [X] T074: Ensure subprocess imports work (try/except patterns)
- [X] T075: Run full regression test suite
- [X] T076: Test pip installation with new structure
- [X] T077: Test development mode imports
- [X] T078: Update documentation for new structure
- [X] T079: Performance verification (startup time, command response)

**Dependencies**: WP01-WP07 (all previous work)
**Risks**: Integration issues, import resolution problems
**Verification**: ✅ All tests pass (32/32 refactoring tests), pip install works, CLI functional

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

- [X] All modules under 200 lines (excluding comments/docstrings)
- [X] No circular imports
- [X] All existing tests pass
- [X] New unit tests for each module
- [X] Import compatibility verified (local/pip/subprocess)
- [X] CLI commands work identically to before
- [X] Dashboard functionality unchanged
- [X] Performance metrics maintained
- [X] Documentation updated
- [X] Code formatted with black/ruff

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
# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to the Spec Kitty CLI and templates are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.15.2] - 2026-02-13

### 🐛 Fixed

- **Unborn branch misdetected as detached HEAD**: `get_current_branch()` now uses `git branch --show-current` (Git 2.22+) with fallback to `git rev-parse --abbrev-ref HEAD` for older Git. Correctly returns the branch name on fresh repos with no commits, fixing false "Not in a git repository" errors during `spec-kitty init`.
- **Windows subprocess decode crash**: Added `encoding="utf-8", errors="replace"` to all 113 `subprocess.run(text=True)` calls across 31 files. Prevents `UnicodeDecodeError` on Windows systems with non-UTF-8 locale settings.
- **Pre-commit hook blocks commits when Python unavailable**: Expanded interpreter detection to try `python3`, `python`, and `py` (Windows launcher) with a smoke test. Removed `set -e` so non-encoding Python failures (e.g. filenames with special characters) warn-and-skip instead of blocking commits. Distinguishes Python execution failure from actual encoding errors via distinct exit codes.
- **Init reports "project ready" even when git init failed**: `init` now raises `RuntimeError` after `tracker.error()` when `init_git_repo()` returns False, triggering the failure panel and non-zero exit instead of falsely reporting success.
- **PowerShell equivalents in implement templates**: Added PowerShell syntax examples (in collapsible `<details>` blocks) after bash code blocks in implement templates for all 3 missions (software-dev, research, documentation).

### 🔧 Changed

- Removed 7 duplicate inline `subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"])` calls in `feature.py`, `tasks.py`, and `workflow.py`, replacing them with the centralized `get_current_branch()` helper.
- Updated all callers that checked `== "HEAD"` to check `is None` instead, since `git branch --show-current` never returns the literal string `"HEAD"`.

## [0.15.1] - 2026-02-12

### 🐛 Fixed

- **Dynamic primary branch detection**: Replaced 26 hardcoded `"main"` branch references across 13 files with dynamic detection via `resolve_primary_branch()`. Repos using `master`, `develop`, or custom primary branches now work correctly for merge operations, branch resolution, manifest status checks, and CLI defaults.
- **Deduplicated branch resolution**: Consolidated 4 duplicate copies of `_resolve_primary_branch()` scattered across CLI commands into a single centralized implementation in `core/git_ops.py` with lightweight delegating wrappers.
- **Multi-parent merge target**: `create_multi_parent_base()` now accepts explicit `target_branch` parameter instead of hardcoding `"main"` for merge-base calculations.

### ✅ Added

- 20 integration tests covering master/develop/custom branch scenarios for primary branch detection, target branch resolution, manifest status, multi-parent merge, and conflict prediction.

## [0.15.0] - 2026-02-11

### 🐛 Fixed

- **#95 - Kebab-case validation**: Feature slugs now validated before creation - prevents creation of invalid feature directories with uppercase/underscores/spaces. Enforces kebab-case format (lowercase, hyphens only) at the point of feature creation, with clear error messages guiding users to valid names.
- **#120 - Gitignore isolation**: Worktree-specific ignores now use `.git/info/exclude` instead of `.gitignore` - prevents cross-contamination when multiple worktrees share the same main repository. Each worktree can have isolated ignore rules without affecting other workspaces.
- **#117 - Dashboard false-failure**: Accurate process detection with robust PID validation - fixes false "no agent process found" errors. New `is_process_alive()` helper uses `psutil` for cross-platform reliability and handles stale PIDs gracefully.
- **#124 - Branch routing unification**: Unified branch resolution with no implicit `master` fallback - all branch routing now uses a single `resolve_target_branch()` function. Prevents silent fallback to `master` when target branch is not found, failing fast with actionable errors instead.
- **#119 - Assignee relaxation**: Optional assignee for done work packages - removes the requirement for `assignee` field in WP frontmatter when WP is in `done` lane. Completed work no longer needs to track who did it.
- **#122 - Safe commit helper**: Preserve staging area during automated commits - new `safe_commit()` helper stages only the files it needs without clearing pre-existing staged changes. Prevents accidental loss of user's staging state during spec-kitty operations.
- **#123 - Atomic state transitions**: Lane transitions happen before status file writes - ensures WP frontmatter updates are atomic and consistent. When lane changes fail (e.g., validation errors), the status board is never touched, preventing partial state.

### ✅ Added

- 54+ comprehensive tests for all bug fixes
- Safe commit helper (`git/commit_helpers.py`)
- Unified branch resolution (`git/branch_utils.py`)
- Enhanced process detection utilities (`dashboard/process_utils.py`)
- Robust validation for feature slug format

## [0.14.2] - 2026-02-07

### 🐛 Fixed

- **False "behind main" errors for stacked worktree branches**: `move-task --to for_review` now checks against the WP's actual base branch (from workspace context) instead of always checking against the target branch. Stacked WPs (e.g., WP03 based on WP01) no longer produce false "behind main by N commits" errors.

### ✨ Added

- **Worktree topology context for stacked branches**: New `worktree_topology` module auto-detects when WPs are stacked (branched from other WPs) and injects structured JSON topology into implement and review prompts. Agents now understand where their branch fits in the dependency stack. Only activates when stacking is detected — flat features get no extra noise.

## [0.14.1] - 2026-02-04

### 🐛 Fixed

- **Broken import in 0.14.0 migration**: Fixed `ModuleNotFoundError` in `m_0_14_0_centralized_feature_detection` - corrected import paths for `load_agent_config` and `AGENT_DIR_TO_KEY`.
- **Integration test fixture**: Fixed `clean_project` fixture failing to copy source missions when `.kittify/missions/` already existed with stale leftovers.
- **Stale mission directory**: Removed orphaned `.kittify/missions/research/` that was left behind when missions were untracked from git.

## [0.14.0] - 2026-02-04

### ✨ Added

**Mission-aware cleanup, docs wiring, and module consolidation** (Feature 029):

- **Documentation mission state initialization**: `spec-kitty agent create-feature --mission documentation` now initializes `documentation_state` in `meta.json` with spec-compliant defaults. New `init-doc-state` command for existing features.
- **Gap analysis wiring**: Automatically runs gap analysis during `/spec-kitty.plan` and `/spec-kitty.research` for documentation missions in `gap_filling` or `feature_specific` mode. Writes `gap-analysis.md` and updates audit metadata.
- **Generator auto-detection**: Detects JSDoc, Sphinx, and Rustdoc generators during plan setup for documentation missions. Persists configuration to `documentation_state.generators_configured`.
- **Documentation validation checks**: New `validators/documentation.py` with 3 checks (`documentation_state_exists`, `gap_analysis_exists`, `audit_recency`). Integrated into acceptance flow - doc validation errors block acceptance.
- **Shared task helpers module**: `task_helpers_shared.py` consolidates duplicated logic from `tasks_support.py` and `scripts/tasks/task_helpers.py` into a single source of truth (~900 lines of duplication removed).
- **Shared acceptance core module**: `core/acceptance_core.py` extracts shared acceptance workflow logic from `acceptance.py` and `scripts/tasks/acceptance_support.py`, enabling both to delegate to a single implementation.
- **Base plan template alignment**: Added feature detection guidance (steps 2a-2d) to the base plan template, matching the software-dev mission template.

### 🧹 Removed

- **Root script duplicates**: Removed `scripts/validate_encoding.py`, `scripts/debug-dashboard-scan.py`, and `scripts/tasks/` which duplicated files already in `src/specify_cli/scripts/`.

### 🐛 Fixed

- **Merge command worktree detection**: Fixed `merge_command` to use the current working directory for branch detection instead of the resolved main repo root, preventing false "Already on target branch" errors when merging from worktrees.

## [0.13.28] - 2026-02-04

### 🐛 Fixed

**Workflow implement now tolerates non-git test repos**:
- If a workflow prompt is generated in a minimal test repo without `.git`, the command skips workspace creation and still completes
- Prevents workflow tests from failing on repo scaffolds that only include `.kittify`

## [0.13.27] - 2026-02-04

### 🧹 Removed

**Sync module and WebSocket sync tooling**:
- Removed `specify_cli.sync` package from mainline 0.13.x
- Dropped WebSocket sync status command and related dependencies
- Updated workspace sync docs to use `spec-kitty sync workspace`

## [0.13.26] - 2026-02-04

### 🛠️ Refactored

**Consolidated workflow implement workspace creation**:
- `spec-kitty agent workflow implement` now delegates workspace creation to `spec-kitty implement` when needed
- Removes duplicated worktree/sparse-checkout setup in the agent command
- Prevents agents from creating worktrees from inside another worktree

### 🐛 Fixed

**Clearer recovery guidance for multi-parent merge failures**:
- When auto-merge fails, instructions now show concrete recovery steps
- Explicitly warns there is no `spec-kitty agent workflow merge` command
- Points agents to the correct `spec-kitty agent feature merge` command

## [0.13.25] - 2026-02-04

### 🐛 Fixed

**`spec-kitty upgrade` not bumping version when no migrations needed**:
- When `spec-kitty upgrade` found no applicable migrations, it returned early without updating the version in `.kittify/metadata.yaml`
- This left the project stuck at its old version (e.g., 0.13.21) even though the CLI was newer (0.13.24)
- The dashboard then blocked with a version mismatch error
- Fixed both `upgrade.py` (CLI command path) and `runner.py` (programmatic path) to stamp the version even when no migrations are needed

## [0.13.24] - 2026-02-04

### 🔧 Improved

**Review workflow shows git context for reviewers**:
- `spec-kitty agent workflow review` now displays the WP's branch name, base branch, and commit count
- Reviewers see exactly which commits belong to the WP vs inherited history
- Provides ready-to-use `git log <base>..HEAD` and `git diff <base>..HEAD` commands
- Base branch auto-detected from WP dependencies (tries dependency branches first, then main/2.x)
- Prevents reviewers from accidentally diffing against the wrong base (e.g., `main` instead of `2.x`)

## [0.13.23] - 2026-02-04

### 🐛 Fixed

**"Done" Lane Semantics — Branch from WP Branch, Not Target (ADR-21)**:
- Fixed critical bug where `implement --base WP01` branched from the target branch when WP01 was "done", missing all of WP01's implementation code
- Root cause: Three locations in `implement.py` incorrectly treated "done" lane as "merged to target branch". In reality, "done" means review-complete — WP branches persist and are NOT merged to target until `spec-kitty merge` runs at the feature level
- Fix 1 (validation): When base WP is "done", verify its branch exists instead of skipping validation
- Fix 2 (create workspace): When base WP is "done", branch from `{feature}-{WP}` branch instead of target
- Fix 3 (multi-parent): When all dependencies are "done", create merge base from their WP branches instead of short-circuiting to target
- Fix 4 (CI): Fall back to `resolve_primary_branch()` when default "main" target doesn't exist (repos using "master")
- Updated `dependency_resolver.py` messaging to stop claiming "done = merged"
- Updated integration tests to match corrected semantics

### 📝 Architecture

- **ADR-21**: "Done" Means Review-Complete, Not Merged — establishes authoritative lane lifecycle
- **Supersedes ADR-15 and ADR-18** which incorrectly conflated "done" with "merged to target"
- Updated ADR-4 with cross-reference to ADR-21
- Updated architecture README index with ADRs 17-21

## [0.13.22] - 2026-02-03

### 🐛 Fixed

**Target Branch Routing Test Failures (36 fixes)**:
- Fixed missing `_ensure_target_branch_checked_out()` call in `review()` command — caused 5 test failures from undefined `main_repo_root` and `target_branch` variables
- Removed duplicate `_ensure_target_branch_checked_out()` call in `implement()` — prevented double git operations at runtime
- Fixed `sync` → `sync_workspace` rename in `test_sync.py` — function was renamed but test imports were not updated (1 collection error)
- Fixed `_commit_to_main` → `_commit_to_branch` mock rename in `test_agent_feature.py` — 5 test failures from patching non-existent function
- Updated branch policy tests to reflect new any-branch feature creation behavior — tests expected rejection on non-main branches but code now intentionally allows any branch
- Added `_ensure_target_branch_checked_out` mocks to 27 unit tests across 5 test files that run against tmp directories without git repos
- Fixed integration test `test_race_condition_prevented` — merge planning files to target branch before status routing
- Fixed integration test `test_creates_feature_from_existing_worktree` — assert worktree rejection instead of branch rejection
- Fixed missing branch restoration in `implement` command after committing lane change to target branch — caused subsequent implement calls to fail with "Planning artifacts must be committed" error

## [0.13.21] - 2026-02-02

### 🐛 Fixed

**Duplicate Migration Registration Warning**:
- Fixed warning on startup: "Failed to import migration module m_0_9_1_complete_lane_migration: Duplicate migration ID"
- Root cause: Migration module served dual purposes (migration + utilities), causing reload during auto-discovery
- Solution: Extracted agent directory utilities to `agent_utils/directories.py` module
- Changes:
  - Created `agent_utils/directories.py` with `AGENT_DIRS`, `AGENT_DIR_TO_KEY`, `get_agent_dirs_for_project()`
  - Updated `m_0_9_1_complete_lane_migration.py` to import from `agent_utils` (backward compatible)
  - Fixed `auto_discover_migrations()` to skip reload if migration already registered
- Impact: Clean startup without warnings, proper separation of concerns
- Applies to both 1.x (main) and 2.x branches

## [0.13.20] - 2026-01-30

### 🐛 Fixed

**Merged Single-Parent Dependency Workflow Gap** (ADR-18):
- Fixed `spec-kitty implement` failing when single-parent dependency has been merged to target branch
- Issue: WP01 merged to 2.x → WP02 can't implement (looks for non-existent WP01 workspace branch)
- Root cause: Implement command didn't distinguish between in-progress vs merged dependencies
- Solution: Auto-detect when dependency lane is "done" and branch from target branch instead
- Behavior:
  - If `base_wp.lane == "done"`: Branch from target branch (e.g., 2.x) - merged work already there
  - If `base_wp.lane != "done"`: Branch from workspace branch (e.g., 025-feature-WP01) - work in progress
- Eliminates need for manual frontmatter editing (remove dependencies, update base_branch)
- Complements ADR-15 (multi-parent all-done suggestion) for single-parent case
- **Impact**: Critical fix for normal workspace-per-WP workflow where dependencies complete before dependents start
- **Technical Story**: Feature 025-cli-event-log-integration WP02/WP08 blocked on merged WP01

## [0.13.9] - 2026-01-30

### 🐛 Fixed

**Two-Branch Strategy Support (Critical)**:
- Fixed hardcoded `main` branch in move-task validation (now uses `target_branch` from meta.json)
- Fixed misleading console messages showing "committed to main" for all features
- Enables proper separation between 1.x (main) and 2.x (SaaS) development per ADR-12
- Features targeting 2.x now validate against 2.x branch, not main
- Rebase instructions now show correct target branch
- **Impact**: Unblocks Feature 025 (CLI Event Log Integration) on 2.x branch

**Multi-Parent Dependency Support (Critical)**:
- Fixed missing `force` parameter in implement command (line 561 used undefined variable)
- Users can now bypass merge-first recommendation with `--force` flag
- **Impact**: Unblocks all multi-parent workflows where dependencies are complete
- **Error fixed**: `NameError: name 'force' is not defined`

**Single Dependency Auto-Detection (UX)**:
- Auto-detect `--base` from single dependency in frontmatter
- No longer requires manual `--base WP01` when WP has single dependency
- Reduces command friction: `spec-kitty implement WP02` just works
- **Impact**: Simpler UX for 90% of work packages (most have single parent)

### 📝 Changed

**Console Output**:
- move-task validation messages now show target branch name (e.g., "behind 2.x by 3 commits")
- implement command shows accurate branch in status messages (e.g., "committed to 2.x")

### ✅ Tests

**New Integration Tests**:
- Added `tests/integration/test_two_branch_strategy.py`
- Verifies target_branch detection from meta.json
- Verifies default to "main" for legacy features
- Ensures two-branch strategy (ADR-12) works correctly

## [0.13.8] - 2026-01-29

### 🎯 Added

**Dual-Branch Status Routing** (Main Feature):
- Status commits now route to `target_branch` from feature metadata (not hard-coded to main)
- Enables parallel development on main (1.x) and 2.x (SaaS) branches
- Meta.json field: `"target_branch": "main"` or `"target_branch": "2.x"`
- Migration automatically adds target_branch to existing features
- Feature 025 (CLI Event Log Integration) can now develop on 2.x without race conditions
- **ADR-13**: Target Branch Routing for Status Commits

**Explicit Metadata Fields**:
- meta.json now always includes `target_branch` and `vcs` fields (no implicit defaults)
- Follows SDD principle: configuration should be explicit and visible
- Updated specify template for all 12 agent directories
- Improves debugging: `cat meta.json` shows complete configuration
- **ADR-14**: Explicit Metadata Fields Over Implicit Defaults

**Smart Dependency Detection**:
- Auto-detects when multi-parent dependencies are complete
- Suggests merge-first workflow before attempting auto-merge (prevents .gitignore conflicts)
- Provides clear guidance: "Run spec-kitty merge first, then implement WP04"
- New module: `src/specify_cli/core/dependency_resolver.py`
- **ADR-15**: Merge-First Suggestion for Completed Dependencies

**Auto-Create Target Branch**:
- Automatically creates target branch during first implement if missing
- Solves bootstrap paradox (WP01 creating the branch it should work on)
- Just-in-time creation: `git branch 3.x main` when first WP implemented
- Console message: "Creating target branch: 3.x"
- **ADR-17**: Auto-Create Target Branch on First Implement

**Centralized Feature Detection**:
- Unified feature detection across all commands
- Priority: --feature flag > SPECIFY_FEATURE env > git branch > cwd > single auto-detect
- Clear error messages with actionable guidance
- New module: Refactored in feature_detection.py

**Priority 6 Fallback to Latest Incomplete Feature**:
- Auto-selects highest numbered incomplete feature when running from repo root with no context
- Resolves ambiguity: instead of erroring with "Multiple features found", auto-selects the feature you're most likely working on
- Smart detection: features with all WPs `lane: done` are considered complete
- Informational message: "Auto-selected latest incomplete: 022-dashboard"
- Benefits all commands (plan/tasks/implement/review) automatically
- Safe defaults: parse errors treat features as incomplete

### 🐛 Fixed

**Agent JSON Output Confusion**:
- `spec-kitty agent feature finalize-tasks --json` now includes:
  - `commit_created`: boolean (did commit happen?)
  - `commit_hash`: string (SHA for verification)
  - `files_committed`: array (what was committed)
- Prevents agents from committing twice when unrelated files are dirty
- **ADR-16**: Rich JSON Outputs for Agent Commands

**Tasks Template Guidance**:
- Added warning: "DO NOT commit after finalize-tasks (commits automatically)"
- Clarifies that finalize-tasks handles git commit internally
- Prevents redundant git commit attempts

### 📚 Documentation

- **5 New ADRs**: ADR-13 through ADR-17 documenting architectural decisions
- **architecture/README.md**: Updated with new ADRs, organized by topic
- **README.md**: Branch strategy badges (main → 1.x, 2.x → active)

### 🧪 Testing

- **66 new tests** across 6 test files (1 known issue in auto-create routing)
- **test_dual_branch_status_routing.py**: 12 tests for routing behavior
- **test_feature_025_workflow.py**: 3 end-to-end tests
- **test_specify_metadata_explicit.py**: 13 tests for explicit fields
- **test_finalize_tasks_json_output.py**: 6 tests for JSON enhancements
- **test_auto_merge_dependencies.py**: 7 tests for smart detection
- **test_auto_create_target_branch.py**: 6 tests (5 passing, 1 known issue)
- **test_feature_detection.py**: 12 tests for Priority 6 fallback (is_feature_complete, find_latest_incomplete)
- **test_feature_detection.py**: 7 tests for target branch detection (get_feature_target_branch)
- **conftest.py**: dual_branch_repo fixture for multi-branch testing

### ⚠️ Known Issues

- Auto-created target branches don't receive status commits immediately (fallback to main works)
- Worktree cleanup after merge not yet implemented (ADR-9)

### 🔧 Migration

- **m_0_13_8_target_branch**: Adds target_branch field to all existing features
  - Auto-detects Feature 025 as targeting 2.x (from spec.md content)
  - Defaults to "main" for all other features
  - Safe, non-breaking migration

- **m_0_14_0_centralized_feature_detection**: Updates to unified detection module
  - No user-visible changes
  - Infrastructure improvement

## [0.13.7] - 2026-01-27

### 🐛 Fixed

**Activity Log Parser Failing on Hyphenated Agent Names** ([#111](https://github.com/Priivacy-ai/spec-kitty/pull/111)):
- Fixed `activity_entries()` regex in `tasks_support.py` to handle hyphenated agent names
- Parser was using `[^–-]+?` pattern which treated hyphens as field separators
- Agent names like `cursor-agent`, `claude-reviewer`, `cursor-reviewer` now parse correctly
- Acceptance validation no longer fails with "Activity Log missing entry for lane=done" for hyphenated agents
- Changed pattern to `\S+(?:\s+\S+)*?` (matches non-whitespace), aligning with `task_helpers.py`
- Added comprehensive test suite with 11 test cases covering hyphenated names, backward compatibility, and edge cases
- **Contributors**: Rodrigo D. L. (bruj0)

**Workflow Completion Instructions Missing Git Commit Step** ([#104](https://github.com/Priivacy-ai/spec-kitty/pull/104)):
- Fixed agents not committing implementation files before marking tasks done
- Issue caused cascading failures where dependent work packages started from empty branches
  - WP02 worktree had HTML + CSS ✅
  - WP03 worktree had HTML only (missing WP02's CSS) ❌
  - WP04 worktree had HTML only (missing CSS and JS from WP02 and WP03) ❌
- Root cause: "WHEN YOU'RE DONE" instructions in `workflow implement` command didn't include git commit step
- Fix: Added explicit git commit instruction as step 1 in completion checklist
- Updated both in-prompt instructions (shown twice) and terminal output summary
- Added warning: "The move-task command will FAIL if you have uncommitted changes! Commit all implementation files BEFORE moving to for_review. Dependent work packages need your committed changes."
- **Impact**: Critical fix for multi-agent parallel development workflows using workspace-per-WP model (v0.11.0+)
- **Contributors**: Jerome Lacube

**Dashboard Command Template Generating Python Code Instead of Running CLI** ([#94](https://github.com/Priivacy-ai/spec-kitty/issues/94), [#99](https://github.com/Priivacy-ai/spec-kitty/pull/99)):
- Fixed `/spec-kitty.dashboard` command template to use `spec-kitty dashboard` CLI command
- Removed outdated Python code that manually checked dashboard status and opened browsers
- Dashboard now properly:
  - Starts automatically if not running
  - Opens in default browser
  - Handles worktree detection automatically
- Updated all three dashboard template files:
  - `.kittify/missions/software-dev/command-templates/dashboard.md`
  - `src/specify_cli/missions/software-dev/command-templates/dashboard.md`
  - `src/specify_cli/templates/command-templates/dashboard.md`
- Reduced template code from ~264 lines to ~47 lines
- **Contributors**: Jerome Lacube

## [0.13.6] - 2026-01-27

### 🐛 Fixed

**Critical JSON Mode Corruption Fix** (Release Blocker):
- Fixed JSON output corruption in `spec-kitty implement --json` mode (GitHub Issue #72 follow-up)
  - **Bug**: Warning messages from empty branch detection were written to stdout, corrupting JSON output
  - **Impact**: Automated workflows using `--json` flag would fail with JSON parse errors
  - **Fix**: Changed warning messages to use `file=sys.stderr` to separate warnings from JSON output
  - **File**: `src/specify_cli/core/multi_parent_merge.py:142-144`
  - **Tests**: Updated 5 tests in `test_multi_parent_merge_empty_branches.py` to check stderr instead of stdout

**Missing Migration Fix** (Existing Users Affected):
- Fixed missing migration for commit workflow section (GitHub Issue #72 follow-up)
  - **Bug**: New projects got commit workflow section in implement.md, but existing projects didn't after upgrade
  - **Impact**: Existing users remained vulnerable to agents forgetting to commit work
  - **Fix**: Created migration `m_0_13_5_add_commit_workflow_to_templates.py` to update all agent templates
  - **Coverage**: Updates both software-dev and documentation mission templates for all 12 agents
  - **Migration**: Automatically runs on `spec-kitty upgrade` for projects missing commit workflow

**Subprocess Error Handling** (Defensive Programming):
- Added timeout and error handling to multi-parent merge git commands
  - **Bug**: Git commands in empty branch detection lacked timeout parameters and try/except blocks
  - **Impact**: Function could hang forever or crash on git errors (corrupted repo, permission issues)
  - **Fix**: Added 10-second timeouts and exception handling to all git subprocess calls
  - **File**: `src/specify_cli/core/multi_parent_merge.py:117-144`
  - **Errors handled**: TimeoutExpired (>10s git commands), general exceptions with warning

### Added
- Git commit validation for "done" status transitions - prevents completing WPs with uncommitted changes
- Empty branch detection in merge-base creation - warns when dependencies have no commits
- Git commit workflow section in documentation mission template (consistency with software-dev/research)
- Comprehensive troubleshooting guide for empty branch recovery in workspace-per-wp documentation
- Migration to add commit workflow section to existing projects (`m_0_13_5_add_commit_workflow_to_templates.py`)

### Changed
- `move-task --to done` now validates git status (same checks as "for_review")
- Use `--force` flag to bypass validation (not recommended)
- Warning messages in multi-parent merge now output to stderr instead of stdout (preserves JSON output integrity)

### Fixed (Non-Critical)
- WP agents can no longer mark tasks as "done" without committing implementation files
- Multi-parent merge-bases no longer silently accept empty dependency branches
- Documentation mission now instructs agents to commit work before review
- Stale WP detection now correctly detects default branch name (main/master/develop) instead of hardcoding "main"
  - **Bug**: Fresh worktrees incorrectly flagged as stale when repository used non-standard default branch
  - **Root Cause**: Code hardcoded "main" as default branch; when `git merge-base HEAD main` failed, it fell through to using parent branch's old commit timestamp
  - **Fix**: Added `get_default_branch()` helper to dynamically detect default branch via origin HEAD or local branch existence
  - **Impact**: Prevents false staleness warnings for fresh worktrees in repos using "master", "develop", or other default branches

## [0.13.5] - 2026-01-26

### 🐛 Fixed

**Fixed /spec-kitty.clarify Command Template**:
- Fixed broken placeholder in clarify template that prevented agents from running clarification workflow
  - **Bug**: Template contained `(Missing script command for sh)` placeholder instead of actual command
  - **Impact**: Agents couldn't get feature context, invented non-existent commands like `spec-kitty agent feature get-active --json`
  - **Fix**: Replaced manual detection logic with `spec-kitty agent feature check-prerequisites --json --paths-only`
  - **Consistency**: Now matches pattern used in specify.md, plan.md, and tasks.md templates
  - Migration `m_0_13_5_fix_clarify_template.py` automatically updates all 12 agent directories on upgrade
  - Source template: `src/specify_cli/missions/software-dev/command-templates/clarify.md`

**Testing**:
- Added comprehensive test suite with 34 tests covering all scenarios
  - Parametrized tests for all 12 agents (claude, copilot, gemini, cursor, qwen, opencode, windsurf, codex, kilocode, auggie, roo, q)
  - Tests for detection, application, agent config respect, idempotency, dry-run
  - Template content validation (ensures no broken placeholders, matches tasks.md pattern)
  - End-to-end integration test verifying migration actually runs and fixes templates

## [0.13.4] - 2026-01-26

### 🐛 Fixed

**Critical Dependency Validation Fix**:
- Fixed `spec-kitty agent workflow implement` not validating WP dependencies before creating workspaces
  - **Bug**: WP with single dependency could create workspace without `--base` flag
  - **Impact**: Workspace branched from main instead of dependency branch (silent correctness bug)
  - **Fix**: Added shared validation utility that errors when single dependency but no `--base` provided
  - **Example**: `WP06` depends on `WP04` → command now errors and suggests `--base WP04`
  - Created `src/specify_cli/core/implement_validation.py` with `validate_and_resolve_base()`
  - Agent commands now delegate to top-level commands (no more legacy script calls)

**Fixed Broken Agent Commands**:
- Fixed `spec-kitty agent feature accept` calling non-existent `scripts/tasks/tasks_cli.py`
  - Now delegates to top-level `accept()` command
- Fixed `spec-kitty agent feature merge` calling non-existent `scripts/tasks/tasks_cli.py`
  - Now delegates to top-level `merge()` command
  - Parameter mapping: `keep_branch` → `delete_branch` (inverted logic)

**Critical Merge Workflow Fix**:
- Fixed merge failing when main branch lacks upstream tracking (Issue reported post-0.13.2 release)
  - 0.13.2 only checked if remote EXISTS, but not if branch TRACKS it
  - Added `has_tracking_branch()` function to check upstream tracking
  - Merge now skips pull if: (1) no remote OR (2) no upstream tracking
  - Affects users with local-only repos or repos where main doesn't track origin/main

**Testing & Prevention**:
- Added 22 new tests for dependency validation and agent command wrappers
  - Unit tests: `test_implement_validation.py` (11 tests)
  - Integration tests: `test_agent_command_wrappers.py` (11 tests)
- Added `TestMigrationRegistryCompleteness` test (prevents 0.13.2-style release blocker)
  - Verifies all m_*.py migration files are imported in __init__.py
  - Prevents silent bugs where migrations exist but never run
- Added integration tests for merge with untracked branches
- Added unit tests for `has_tracking_branch()` function

**Documentation**:
- Added `src/specify_cli/cli/commands/agent/README.md` (wrapper pattern documentation)
  - Dependency validation best practices
  - Parameter mapping guidelines
  - Common pitfalls and examples
- Updated RELEASE_CHECKLIST.md with mandatory migration registry verification

## [0.13.2] - 2026-01-26

### 🐛 Fixed

**Critical Windows Compatibility Issues**:
- Fixed UTF-8 encoding errors causing Windows crashes (Issue #101)
  - Added `encoding='utf-8'` to all `write_text()` and `read_text()` calls
  - Affected files: feature.py, worktree.py, agent_context.py, doc_generators.py, gap_analysis.py
  - Completes PR #100 which missed several locations
- Fixed hardcoded `python3` breaking Windows installations (Issue #105)
  - Replaced with `sys.executable` in Python code (feature.py)
  - Added dynamic Python detection in git hooks (tries python3, falls back to python)
  - Windows users no longer need to create python3 hardlinks/aliases

**Workflow Improvements**:
- Added `--base` parameter to `spec-kitty agent workflow implement` (Issue #96)
  - Enables agents to create dependent WP worktrees via workflow command
  - Provides feature parity with top-level `spec-kitty implement` command
  - Example: `spec-kitty agent workflow implement WP02 --base WP01 --agent claude`

**Template and Documentation Fixes**:
- Fixed broken `/spec-kitty.clarify` skill (Issue #106)
  - Removed unresolved `{SCRIPT}` and `{ARGS}` placeholders
  - Replaced with auto-detection instructions for feature paths
- Fixed outdated template path references (Issue #102)
  - Updated 6 references from `.kittify/templates/` to `src/specify_cli/missions/`
  - Templates now reference correct bundled locations
- Fixed upgrade version detection for modern projects (Issue #108)
  - Added detection for versions 0.7.0-0.13.0
  - Prevents unnecessary migrations on modern projects
- Regenerated all 12 agent constitution templates (Issue #97)
  - All agents now correctly suggest `/spec-kitty.specify` as next step (not `/spec-kitty.plan`)

### 📚 Documentation

- Added GitHub CLI authentication troubleshooting to CLAUDE.md
  - Documents `unset GITHUB_TOKEN` technique for organization repos

**Issues Closed**: #96, #97, #101, #102, #105, #106, #108, #103 (not a bug), #107 (not a bug)

## [0.13.1] - 2026-01-25

### ✨ Added

**Adversarial Test Suite for 0.13.0 Release**:
- **Distribution tests**: Validate PyPI user experience without SPEC_KITTY_TEMPLATE_ROOT bypass (prevents 0.10.8-style packaging failures)
- **Path validation security tests**: Test directory traversal, symlink attacks, case-sensitivity bypasses, and path injection prevention
- **CSV schema attack tests**: Validate handling of formula injection, encoding errors, duplicate columns, and empty files
- **Git state detection tests**: Verify accuracy of uncommitted work, merge state, and branch divergence detection
- **Migration robustness tests**: Test UTF-8 encoding, idempotency, and partial/corrupted file handling
- **Multi-parent merge tests**: Validate dependency-order merging and conflict resolution
- **Context & config tests**: Test non-interactive modes, agent configuration, and workspace validation

**Test Infrastructure**:
- New `tests/adversarial/` directory with shared fixtures and attack vectors
- `@pytest.mark.distribution` and `@pytest.mark.slow` markers for CI optimization
- Session-scoped `wheel_install` fixture for efficient testing
- Platform-specific skip conditions for cross-platform compatibility

### 📚 Documentation

**Testing**:
- Comprehensive adversarial test documentation in feature 024 spec
- Attack vector catalog with prevention strategies
- CI integration guidance for slow/distribution tests

## [0.13.0] - 2026-01-25

### ✨ Added

**Deterministic CSV Schema Enforcement for Research Missions**:
- **Canonical schema documentation**: Research CSV schemas now documented in all 12 agent implement.md templates
- **Two schemas enforced**:
  - `evidence-log.csv`: `timestamp,source_type,citation,key_finding,confidence,notes`
  - `source-register.csv`: `source_id,citation,url,accessed_date,relevance,status`
- **Schema visibility**: Agents see schemas before editing (in "Research CSV Schemas" section with examples)
- **Detection migration**: `m_0_13_0_research_csv_schema_check.py` scans existing features for schema mismatches (informational only, no auto-fix)
- **Template propagation**: `m_0_13_0_update_research_implement_templates.py` updates all agent templates with schema documentation
- **Reusable validator**: `src/specify_cli/validators/csv_schema.py` provides `CSVSchemaValidation` dataclass for exact schema matching
- **Exported constants**: `EVIDENCE_REQUIRED_COLUMNS` and `SOURCE_REGISTER_REQUIRED_COLUMNS` now importable from `research.py`
- **ADR #8**: Documents architecture decision for documentation-based enforcement vs runtime enforcement/auto-migration

**Problem Solved**: Agents were modifying CSV schemas during implementation, creating different schemas in parallel WPs, causing merge conflicts and validation failures at review time.

**Solution Approach**: Document schemas where agents can see them (prevention) rather than runtime enforcement or auto-migration (data loss risk).

**Fully Non-Interactive Init Support**:
- Added `--non-interactive` / `--yes` and `SPEC_KITTY_NON_INTERACTIVE` to disable prompts
- Added `--agent-strategy`, `--preferred-implementer`, and `--preferred-reviewer` to expose all selection options via CLI
- Non-interactive mode now avoids arrow-key menus and requires `--force` for non-empty `--here` directories
- Updated documentation for automation and CI usage

### 🐛 Fixed

**Windows UTF-8 Encoding Crashes**:
- Fixed all `write_text()` calls to include `encoding='utf-8'` parameter
- Affects feature creation, worktree setup, gap analysis, doc generators, agent context, and test fixtures
- Windows users can now create features without charmap encoding errors
- Fixes #101, incorporates PR #100

**Constitution Template Workflow**:
- Fixed incorrect next-step suggestion after creating constitution
- Now correctly suggests `/spec-kitty.specify` instead of `/spec-kitty.plan`
- Propagated fix to all 12 agent directories via migration
- Fixes #97 (inspired by PR #98)

**Research Mission Detection**:
- Fixed `spec-kitty mission current` to show feature-level missions
- Now auto-detects feature from current directory (kitty-specs or worktree)
- Added `--feature` flag for explicit feature specification
- No longer always defaults to software-dev for research features
- Fixes #93

### 🎉 Closed

**Agent Configuration Feature**:
- Closed #51 as completed (already implemented in v0.12.0)
- Feature: `spec-kitty agent config add/remove/list`

### 📚 Documentation

**Release Management**:
- Added `RELEASE_CHECKLIST.md` - Comprehensive release preparation checklist with version-specific sections for research missions, agent management, and workspace-per-WP changes

### Migration Notes

**For users with existing research features**:
1. Run `spec-kitty upgrade` to trigger detection migration
2. See informational report with schema diffs and migration tips
3. Use LLM agent to help migrate data:
   - Read canonical schema in `.claude/commands/spec-kitty.implement.md`
   - Create new CSV with correct headers
   - Map old columns → new columns
   - Replace old file and commit to main

**For new research features (0.13.0+)**:
- Templates already have correct schemas
- Agents see schema documentation before editing
- Follow append-only pattern to avoid overwrites
- Validation passes at review

## [0.12.1] - 2026-01-24

### 🐛 Fixed

**kitty-specs/ in .gitignore Blocking Feature Creation**:
- Fixed issue where users with `kitty-specs/` in their `.gitignore` couldn't create features
- Error manifested as: "Issue Detected: The spec-kitty agent feature create-feature command failed to commit because .gitignore contains kitty-specs/"
- New migration `m_0_12_1_remove_kitty_specs_from_gitignore` automatically removes blocking entries
- Only removes patterns that block the entire `kitty-specs/` directory
- Preserves worktree-specific patterns like `kitty-specs/**/tasks/*.md` (used to prevent merge conflicts)

### Migration Notes

**For users experiencing this bug:**
1. Run `spec-kitty upgrade` to apply the fix automatically
2. Or manually remove `kitty-specs/` from your `.gitignore`

The migration will detect and remove entries like:
- `kitty-specs`
- `kitty-specs/`
- `/kitty-specs`
- `/kitty-specs/`

It will NOT remove specific subpath patterns that are intentionally used in worktrees.

## [0.12.0] - 2026-01-23

### ✨ Added

**Config-Driven Agent Management** (Feature 022):
- **Single source of truth**: `.kittify/config.yaml` now controls which agents are configured
- **New CLI commands**: `spec-kitty agent config list|add|remove|status|sync`
  - `list`: Show configured agents
  - `add <agents...>`: Add agents to configuration
  - `remove <agents...>`: Remove agents from configuration
  - `status`: Show configured vs orphaned agents
  - `sync`: Synchronize filesystem with configuration
- **Migrations respect config**: `get_agent_dirs_for_project()` helper only processes configured agents
- **Orphan detection**: Identifies agent directories not in config (from manual deletions)
- **ADR #6**: Documents architectural decision for config-driven approach

**Smarter Feature Merge with Pre-flight** (Feature 017):
- **Pre-flight validation**: Checks all WP worktrees for uncommitted changes, missing worktrees, and target branch divergence before any merge starts
- **Conflict forecasting**: `--dry-run` predicts which files will conflict and classifies them as auto-resolvable (status files) or manual
- **Smart merge order**: WPs merged in dependency order based on frontmatter `dependencies` field
- **Status file auto-resolution**: Conflicts in WP prompt files (`kitty-specs/*/tasks/*.md`) automatically resolved by taking advanced lane status
- **Merge state persistence**: Progress saved to `.kittify/merge-state.json` for recovery
- **Resume/abort flags**: `--resume` continues interrupted merges, `--abort` clears state and starts fresh
- **Auto-cleanup**: Worktrees and branches removed after successful merge (configurable with `--keep-worktree`, `--keep-branch`)

### 📚 Documentation

**Merge Preflight Documentation** (Feature 018):
- Added `docs/how-to/merge-feature.md` - Complete merge workflow guide with pre-flight, dry-run, strategies, and cleanup options
- Added `docs/how-to/troubleshoot-merge.md` - Comprehensive troubleshooting guide with error reference table
- Updated CLAUDE.md with Merge & Preflight Patterns section documenting MergeState dataclass and public API

**Agent Management Documentation Sprint** (Feature 023):
- Added `docs/how-to/manage-agents.md` - Complete guide to adding, removing, and managing AI agent integrations
- Added `docs/how-to/upgrade-to-0-12-0.md` - Migration guide for config-driven agent management
- Updated `docs/reference/cli-commands.md` with comprehensive `agent config` subcommand documentation
- Updated `docs/reference/agent-subcommands.md`, `docs/reference/configuration.md`, `docs/reference/supported-agents.md` with accurate cross-references
- Cleaned up outdated Jujutsu (jj) references throughout documentation (git-only VCS for now)
- Updated `docs/how-to/install-spec-kitty.md` with agent configuration guidance

### 🐛 Fixed

**Merge Resume Bug**:
- Fixed `merge_workspace_per_wp()` missing `resume_state` parameter causing `TypeError` when using `--resume`

**Agent Workflow Output Truncation** (GitHub Codex compatibility):
- Fixed workflow commands (`implement`, `review`) outputting 300+ lines which got truncated by agents like GitHub Codex
- Prompts now written to temp file with concise 15-line summary to stdout
- Added directive language (`▶▶▶ NEXT STEP: Read the full prompt file now:`) so agents automatically read the file
- Agents no longer miss work package requirements due to output truncation

**False Staleness for Newly-Created Worktrees**:
- Fixed stale detection flagging new worktrees as stale immediately
- Previously, `git log -1` returned parent branch's commit time (could be hours old)
- Now checks if branch has commits since diverging from main
- Worktrees with no new commits are NOT flagged as stale (agent just started)

## [0.11.1] - 2026-01-16

### 🐛 Fixed

**Merge Template Improvements**:
- Added explicit preflight validation code using `python3 -c` with `validate_worktree_location()`
- Added clear visual "⛔ Location Pre-flight Check (CRITICAL)" section to prevent agents running merge from wrong location
- Fixed contradictory instructions in software-dev mission merge template (was incorrectly saying "run from main")
- Fixed empty Python code block in research mission merge template that confused agents
- Added workspace-per-WP model (0.11.0+) documentation vs legacy pattern in worktree strategy section

**Documentation Accuracy** (Feature 014):
- Rewrote `multi-agent-orchestration.md` for 0.11.0+ workspace-per-WP model:
  - Planning happens in main repo (not worktrees)
  - Each WP gets its own worktree (not shared)
  - Removed references to non-existent scripts
  - Updated lane tracking to frontmatter (not directories)
  - Added parallelization patterns and status monitoring
- Fixed `workspace-per-wp.md` merge command syntax (runs from worktree without feature argument)
- Fixed `documentation-mission.md` broken source links
- Fixed `reference/README.md` - replaced outdated "Planned Content" with actual content links
- Fixed `kanban-workflow.md` - clarified `/spec-kitty.accept` works on features, not individual WPs

### 📚 Added

**Comprehensive End-User Documentation** (Feature 014):
- Complete Divio 4-type documentation suite:
  - **Tutorials**: Getting Started, Your First Feature, Claude Code Integration, Claude Code Workflow, Multi-Agent Workflow, Missions Overview
  - **How-To Guides**: 14 task-oriented guides covering installation, specifications, planning, implementation, review, dependencies, parallel development, dashboard usage, and migration
  - **Reference**: CLI Commands, Slash Commands, Agent Subcommands, Configuration, Environment Variables, File Structure, Missions, Supported Agents
  - **Explanations**: Spec-Driven Development, Divio Documentation, Workspace-per-WP, Git Worktrees, Mission System, Kanban Workflow, AI Agent Architecture, Documentation Mission, Multi-Agent Orchestration
- Cross-references between all documentation types
- DocFX-compatible structure with `toc.yml` navigation

## [0.11.0] - 2026-01-12

### 🚨 BREAKING CHANGES - Workspace Model Changed (Feature 010)

**Old (0.10.x)**: One worktree per feature
- `/spec-kitty.specify` created `.worktrees/###-feature/`
- All WPs worked in same worktree
- Sequential development (one agent at a time)

**New (0.11.0)**: One worktree per work package
- Planning commands (specify, plan, tasks) work in main repository (NO worktree created)
- `spec-kitty implement WP##` creates `.worktrees/###-feature-WP##/`
- Each WP has isolated worktree with dedicated branch
- Enables parallel multi-agent development

### ⚠️ Migration Required

**You MUST complete or delete all in-progress features before upgrading to 0.11.0.**

Check for legacy worktrees:
```bash
spec-kitty list-legacy-features
```

See [docs/upgrading-to-0-11-0.md](docs/upgrading-to-0-11-0.md) for complete migration guide.

### 🔒 Security (IMPORTANT) - Feature 011

- **Comprehensive adversarial review framework**
  - Expanded review template from 3 bullets (109 lines) to 12 scrutiny categories (505 lines)
  - **Security scrutiny now mandatory**: 10 detailed security subsections
  - **Mandatory verification**: 7 security grep commands must be run on EVERY review
  - **Automatic rejection** if any security check fails
  - **Impact**: All future features will have security-first reviews

### ✨ Added

**Workspace-per-WP Features (010)**:
- **New command**: `spec-kitty implement WP## [--base WPXX]` - Create workspace for work package
  - `--base` flag branches from another WP's branch (for dependencies)
  - Automatically moves WP from `planned` → `doing` lane
- **New command**: `spec-kitty agent feature finalize-tasks` - Finalize WP generation
  - Parses dependencies from tasks.md
  - Generates `dependencies: []` field in WP frontmatter
  - Validates dependency graph (cycle detection, invalid references)
- **Dependency tracking**: WP frontmatter includes `dependencies: []` field
- **Dependency graph utilities**: `src/specify_cli/core/dependency_graph.py`
- **Review warnings**: Alert when dependent WPs need rebase

**Constitution Features (011)**:
- **Interactive constitution command** (Phase-based discovery)
  - 4-phase discovery workflow (Technical, Quality, Tribal Knowledge, Governance)
  - Two paths: Minimal (Phase 1 only) or Comprehensive (all phases)
  - Skip options for each phase
  - Truly optional - all commands work without constitution

### ♻️ Refactored - Feature 011

- **Template source relocation** (Safe dogfooding - Critical)
  - Moved ALL template sources from `.kittify/` to `src/specify_cli/`
  - Updated template manager to load from package resources
  - Removed `.kittify/*` force-includes from `pyproject.toml`
  - **Impact**: Developers can now safely dogfood without packaging risk

- **Mission-specific constitutions removed**
  - Single project-level constitution model (`.kittify/memory/constitution.md`)
  - Migration removes mission constitutions from user projects

### 🐛 Fixed - Feature 011

- **Windows dashboard ERR_EMPTY_RESPONSE** (#71)
  - Replaced POSIX-only signal handling with cross-platform psutil
  - Added `psutil>=5.9.0` dependency
  - Dashboard now works on Windows 10/11

- **Upgrade migration failures** (#70)
  - Fixed multiple migrations to handle missing files gracefully
  - All migrations now idempotent
  - Upgrade path from 0.6.4 → 0.10.12 completes without intervention

### 🐛 Fixed - Feature 012

- **`/spec-kitty.status` template instructed agents to run Python code**
  - AI agents cannot execute arbitrary Python - they use CLI tools
  - Updated template to use CLI command as primary method
  - Python API now documented as alternative for Jupyter/scripts

### 📖 Documentation - Feature 010

- **New docs**: `docs/workspace-per-wp.md` - Workflow guide with examples
- **New docs**: `docs/upgrading-to-0-11-0.md` - Migration instructions

### 🎯 Why These Changes?

**Feature 010 (Workspace-per-WP)**:
- Enables parallel multi-agent development
- Better isolation per work package
- Explicit dependencies with validation
- Scalability for large features (10+ WPs)
- Foundation for future jujutsu VCS integration

**Feature 011 (Constitution & Packaging Safety)**:
- Safe dogfooding (no packaging contamination)
- Cross-platform dashboard support
- Optional, interactive constitution setup
- Smooth upgrade migrations

## [0.10.13] - 2026-01-12

### 🐛 Fixed

- **CRITICAL: Missing migration in PyPI v0.10.12 package**
  - Migration `m_0_10_12_constitution_cleanup.py` was missing from PyPI package uploaded on 2026-01-07
  - File existed in source repository but was not included in distributed wheel
  - Caused constitution cleanup to not run during upgrades from v0.10.11
  - v0.10.13 includes the missing migration file
  - Users who installed v0.10.12 should run `spec-kitty upgrade` again after upgrading to v0.10.13
  - **Root cause**: PyPI package was built before migration file was committed to repository
  - **Prevention**: Added migration file count verification to release workflow

### ♻️ Improved

- **Release workflow hardening**
  - Added verification step to count migration files in built wheel
  - Release now fails if migration count doesn't match source repository
  - Prevents future packaging bugs where files are missing from distribution

### 📋 Migration for v0.10.12 Users

If you installed v0.10.12 from PyPI and upgraded from v0.10.11:
```bash
pip install --upgrade spec-kitty-cli
spec-kitty upgrade  # Run again to apply missing migration 0.10.12
```

The migration will remove mission-specific constitution directories:
- `.kittify/missions/software-dev/constitution/` → removed
- `.kittify/missions/research/constitution/` → removed
- Single project-level constitution: `.kittify/memory/constitution.md` (kept)

## [0.10.12] - 2026-01-12

### 🔒 Security (IMPORTANT)

- **Comprehensive adversarial review framework**
  - Expanded review template from 3 bullets (109 lines) to 12 scrutiny categories (505 lines)
  - **Security scrutiny now mandatory**: 10 detailed security subsections
  - **Mandatory verification**: 7 security grep commands must be run on EVERY review
  - **Automatic rejection** if any security check fails
  - **Impact**: All future features will have security-first reviews
  - **Rationale**: Prevents systematic quality issues (TODOs in prod, mocked implementations, security vulnerabilities)
  - See spec footnote and commit `61d7d01` for complete rationale

### 🐛 Fixed

- **Windows dashboard ERR_EMPTY_RESPONSE** (#71)
  - Replaced POSIX-only signal handling with cross-platform psutil library
  - `signal.SIGKILL` and `signal.SIGTERM` don't exist on Windows
  - Added `psutil>=5.9.0` dependency for cross-platform process management
  - Refactored `src/specify_cli/dashboard/lifecycle.py`:
    * `os.kill(pid, 0)` → `psutil.Process(pid).is_running()`
    * `signal.SIGKILL` → `psutil.Process(pid).kill()` (6 locations)
    * `signal.SIGTERM` → `psutil.Process(pid).terminate()` with timeout
  - Added proper exception handling (NoSuchProcess, AccessDenied, TimeoutExpired)
  - Dashboard now starts, serves HTML, and stops cleanly on Windows 10/11
  - All 41 dashboard tests passing

- **Upgrade migration failures** (#70)
  - Fixed `m_0_7_3_update_scripts.py` to handle missing bash scripts gracefully
  - Fixed `m_0_10_6_workflow_simplification.py` to copy templates before validation
  - Fixed `m_0_10_2_update_slash_commands.py` to explicitly remove legacy .toml files
  - Fixed `m_0_10_0_python_only.py` to explicitly remove `.kittify/scripts/tasks/`
  - Created `m_0_10_12_constitution_cleanup.py` to remove mission constitutions
  - All migrations now idempotent (safe to run multiple times)
  - Upgrade path from 0.6.4 → 0.10.12 now completes without manual intervention

- **Upgrade migration parameter mismatch** (#68 follow-up)
  - Fixed `m_0_10_9_repair_templates.py` migration calling `generate_agent_assets()` with wrong parameter name
  - Changed `ai=ai_config` to `agent_key=ai_config` to match function signature

### ♻️ Refactored

- **Template source relocation** (Safe dogfooding - Critical)
  - Moved ALL template sources from `.kittify/` to `src/specify_cli/`
  - Templates: `.kittify/templates/` → `src/specify_cli/templates/`
  - Missions: `.kittify/missions/` → `src/specify_cli/missions/`
  - Scripts: `.kittify/scripts/` → `src/specify_cli/scripts/`
  - Updated `src/specify_cli/template/manager.py` to load from `src/` not `.kittify/`
  - Removed ALL `.kittify/*` force-includes from `pyproject.toml`
  - **Impact**: Spec-kitty developers can now safely dogfood spec-kitty without risk of packaging their filled-in constitutions
  - **Verification**: Building wheel produces ZERO `.kittify/` or `memory/constitution.md` entries
  - Package now only contains `src/specify_cli/` (proper Python packaging)

- **Mission-specific constitutions removed**
  - Removed `mission.constitution_dir` property from `src/specify_cli/mission.py`
  - Removed constitution scanning from `src/specify_cli/manifest.py`
  - Deleted all `missions/*/constitution/` directories
  - **Impact**: Single project-level constitution model (`.kittify/memory/constitution.md`)
  - **Migration**: `m_0_10_12_constitution_cleanup.py` removes mission constitutions from user projects
  - Eliminates confusion about which constitution applies

## [0.10.11] - 2026-01-07

### 🐛 Fixed

- **Upgrade migration parameter mismatch** (#68 follow-up)
  - Fixed `m_0_10_9_repair_templates.py` migration calling `generate_agent_assets()` with wrong parameter name
  - Changed `ai=ai_config` to `agent_key=ai_config` to match function signature
  - Corrected parameter order to match function definition
  - **Root cause**: Migration was using deprecated parameter name, blocking users from upgrading to 0.10.11
  - **Impact**: Users unable to run `spec-kitty upgrade` to get template fixes from 0.10.11

## [0.10.11] - 2026-01-07

### 🐛 Fixed

- **Deprecated script references in mission templates** (#68)
  - Fixed `.kittify/missions/software-dev/templates/task-prompt-template.md` to use workflow commands instead of deprecated `python3 .kittify/scripts/tasks/tasks_cli.py`
  - Fixed `.kittify/templates/task-prompt-template.md` with same update
  - Fixed `.kittify/missions/software-dev/command-templates/tasks.md` to reference workflow commands
  - Updated `.kittify/templates/POWERSHELL_SYNTAX.md` to document spec-kitty CLI instead of obsolete PowerShell scripts
  - **Root cause**: Migration 0.10.9 fixed agent command templates but missed mission-specific templates
  - **Impact**: Agents were executing users' local `cli.py` files instead of spec-kitty CLI on Windows

### ✨ Added

- **Template compliance tests** - Prevent deprecated script references
  - `test_no_deprecated_script_references()` - Detects old `.kittify/scripts/` paths in templates
  - `test_templates_use_spec_kitty_cli()` - Ensures templates reference spec-kitty CLI commands
  - Tests run on all mission templates and global templates
  - Prevents regression of issue #68

## [0.10.10] - 2026-01-06

### 🐛 Fixed

- **Windows UTF-8 encoding error in agent commands** (#66)
  - Fixed `'charmap' codec can't encode characters` error on Windows
  - `spec-kitty agent feature create-feature` now works correctly on Windows
  - Added UTF-8 stdout/stderr reconfiguration in main() entry point
  - Handles Unicode characters in git output and error messages
  - Gracefully falls back for Python < 3.7

## [0.10.9] - 2026-01-06

### 🐛 Fixed

- **CRITICAL: Wrong templates bundled in PyPI packages** (#62, #63, #64)
  - Fixed pyproject.toml to bundle .kittify/templates/ instead of outdated /templates/
  - Removed outdated /templates/ directory entirely to prevent confusion
  - All PyPI installations now receive correct Python CLI templates
  - No more bash script references in command templates
  - Migration 0.10.0 now handles missing templates gracefully
  - Added package bundling validation tests to prevent regression

- **Template divergence eliminated**
  - 10 of 13 command templates were outdated in /templates/
  - implement.md was 199 lines longer in old location (277 vs 78 lines)
  - Git hooks were missing (1 vs 3)
  - claudeignore-template was missing

- **All 12 AI agent integrations fixed**
  - Claude Code, GitHub Copilot, Cursor, Gemini, Qwen Code, OpenCode, Windsurf,
    GitHub Codex, Kilocode, Augment Code, Roo Cline, Amazon Q
  - All agents now receive correct Python CLI slash commands

### ✨ Added

- **`spec-kitty repair` command** - Standalone command to repair broken templates
  - Detects bash/PowerShell script references in slash commands
  - Automatically regenerates templates from correct source
  - Provides detailed feedback about repairs performed
  - Can be run with `--dry-run` to preview changes

- **Repair migration (0.10.9_repair_templates)** - Automatically fixes broken installations
  - Detects projects with broken template references
  - Regenerates all agent slash commands from correct templates
  - Runs automatically during `spec-kitty upgrade`
  - Verifies repair was successful

- **Package bundling validation tests** - Prevents future regressions
  - Validates correct templates are bundled in sdist and wheel
  - Checks for bash script references before release
  - Tests importlib.resources accessibility

### 📚 Migration & Upgrade Path

**For users with broken installations (issues #62, #63, #64):**

1. **Upgrade spec-kitty package:**
   ```bash
   pip install --upgrade spec-kitty-cli
   spec-kitty --version  # Should show 0.10.9
   ```

2. **Run upgrade to apply repair migration:**
   ```bash
   cd /path/to/your/project
   spec-kitty upgrade
   ```
   This will automatically detect and fix broken templates.

3. **Alternative: Use dedicated repair command:**
   ```bash
   spec-kitty repair
   ```
   Provides detailed feedback about what's being fixed.

4. **Verify repair:**
   ```bash
   # Check for bash script references (should return nothing)
   grep -r "scripts/bash" .claude/commands/
   ```

**For new projects:**
- Automatically get correct templates from package
- No action needed

**For existing healthy projects:**
- Run `spec-kitty upgrade` to stay current
- No breaking changes

### 🔒 Breaking Changes

None - Fully backwards compatible. Existing projects will upgrade smoothly.

## [0.10.8] - 2025-12-30

### 🐛 Fixed

- **Critical: Constitution not copied to worktrees** (#46)
  - Moved `memory/` directory from root to `.kittify/memory/` where code expects it
  - Removed broken circular symlinks (`.kittify/memory` → `../../../.kittify/memory`)
  - Fixed `.kittify/AGENTS.md` to be real file instead of broken symlink
  - Fixed worktree.py symlink handling (check for symlink before trying rmtree)
  - Added migration to automatically fix existing projects
  - Worktrees now correctly access constitution from main repo

- **Migration system** (v0.10.8_fix_memory_structure)
  - Automatically moves `memory/` to `.kittify/memory/` in existing projects
  - Removes broken symlinks and creates proper structure
  - Updates worktrees to use correct paths
  - Handles both Unix symlinks and Windows file copies

### 🔧 Changed

- **Directory structure standardization**
  - `memory/` → `.kittify/memory/` (matches `.kittify/scripts/`, `.kittify/templates/`)
  - `.kittify/AGENTS.md` is now a real file (not symlink)
  - All `.kittify/` resources now follow consistent pattern

## [0.10.7] - 2025-12-30

### 🐛 Fixed

- **Critical: Copilot initialization bug** (#53, fixes #61, #50)
  - Fixed NameError when running `spec-kitty init --ai copilot`
  - Changed `commands_dir` to `command_templates_dir` in asset_generator.py
  - Unblocks all users trying to initialize projects with Copilot

- **Critical: Dashboard contracts and checklists missing** (#59, fixes #52)
  - Restored contracts and checklists handlers that were lost in Nov 11 dashboard refactoring
  - Added generic `_handle_artifact_directory()` helper method
  - Both contracts and checklists now display correctly in dashboard
  - Fixed frontend to use full filepath instead of filename only

- **Critical: Windows UTF-8 encoding errors** (#56)
  - Added explicit `encoding='utf-8'` to read_text() calls
  - Fixes dashboard diagnostics showing "undefined" on Windows
  - Affects manifest.py and migration files
  - Windows defaults to cp1252, causing UnicodeDecodeError with UTF-8 content

- **Plan.md location validation** (#60)
  - Improved validation messaging in plan.md template
  - Added prominent ⚠️ STOP header for AI agents
  - Clearer examples of correct vs wrong worktree locations
  - Template-only change (no code modifications)

### 🔄 Closed

- PR #58 - Obsolete (PowerShell scripts deleted in v0.10.0)
- PR #57 - Obsolete (PowerShell scripts deleted in v0.10.0)
- PR #49 - Superseded by #59 (better architecture)
- PR #43 - Obsolete (PowerShell scripts deleted in v0.10.0)

## [0.10.6] - 2025-12-18

### ✨ Added

- **Workflow commands for simplified agent experience**
  - New `spec-kitty agent workflow implement [WP_ID]` command
  - New `spec-kitty agent workflow review [WP_ID]` command
  - Commands display full WP prompt directly to agents (no file navigation)
  - Auto-detect first planned/for_review WP when no ID provided
  - Auto-move WP to "doing" lane before displaying prompt
  - Show "WHEN YOU'RE DONE" instructions at top of output
  - Display source file path for easy re-reading
  - Prevents race conditions (two agents picking same WP)

### 🔧 Changed

- **Slash command template simplification**
  - implement.md: 78 lines → 11 lines (calls workflow command)
  - review.md: 72 lines → 11 lines (calls workflow command)
  - Templates now just run workflow commands instead of complex instructions
  - Agents see prompts immediately without navigation confusion

- **Consistent lane management**
  - Both implement and review workflows move WP to "doing" at start
  - Prevents ambiguity about which lane means "actively working"
  - Review workflow now supports auto-detect (no argument needed)

### 🐛 Fixed

- **Worktree path resolution**
  - Fixed `_find_first_planned_wp()` to work correctly in worktrees
  - Fixed `_find_first_for_review_wp()` to work correctly in worktrees
  - Auto-detect now finds WPs in worktree's kitty-specs/, not main repo

- **Legacy subdirectory cleanup**
  - Migrated features 007 and 010 from old subdirectory structure to flat structure
  - Moved 15 WP files from `tasks/done/phase-*/` to flat `tasks/`
  - All features now use proper flat structure with frontmatter-only lanes

## [0.9.4] - 2025-12-17

### 📚 Documentation & Validation

- **Prevent agent-created subdirectories in tasks/**
  - Added explicit warnings to tasks/README.md
  - Updated AGENTS.md with flat structure requirements
  - Updated /spec-kitty.tasks template to forbid subdirectories
  - Added runtime validation in check-prerequisites.sh
  - Blocks execution if phase-*, component-*, or any subdirectories found
  - Clear error messages with examples of correct vs wrong paths

This prevents Claude agents from creating organizational subdirectories like `tasks/phase-1/`, `tasks/backend/`, etc.

## [0.9.3] - 2025-12-17

### 🐛 Fixed

- **Critical symlink detection fix**
  - Now checks `is_symlink()` BEFORE `exists()` (exists() returns False for broken symlinks!)
  - Properly removes both working and broken symlinks from worktrees
  - Fixes remaining test failures in worktree cleanup migration
  - Handles all symlink scenarios correctly

This completes the fix for symlink removal in worktree cleanup.

## [0.9.2] - 2025-12-17

### 🐛 Fixed

- **Symlink handling in worktree cleanup**
  - Migration now properly detects and removes symlinks to command directories
  - Uses `unlink()` for symlinks instead of `shutil.rmtree()`
  - Fixes "Cannot call rmtree on a symbolic link" error during upgrade
  - Handles both symlinks and regular directories correctly

This fixes the upgrade failure when worktrees have symlinked agent command directories.

## [0.9.1] - 2025-12-17

### 🔧 Bug Fixes & Improvements

This release fixes critical issues found in v0.9.0 and adds version checking to prevent compatibility problems.

### 🆕 Added

- **Version compatibility checking**
  - CLI now checks for version mismatches between installed spec-kitty-cli and project version
  - Hard error with explicit instructions when versions don't match
  - Special critical warning for v0.9.0+ upgrade explaining breaking changes
  - Shows detailed before/after directory structure comparison
  - Version checks in all CLI commands and bash scripts
  - Graceful handling of legacy projects without metadata

- **Programmatic frontmatter management**
  - New `specify_cli.frontmatter` module for consistent YAML operations
  - Uses ruamel.yaml for absolute formatting consistency
  - No more manual YAML editing by LLMs or scripts
  - Prevents quoted vs unquoted value inconsistencies

### 🐛 Fixed

- **Migration improvements**
  - v0.9.0 migration now finds ALL markdown files (not just WP*.md)
  - Detects and removes empty lane subdirectories
  - Uses shutil.rmtree() for robust directory removal
  - Better detection of legacy format

- **Complete lane migration (v0.9.1)**
  - Migrates files missed by v0.9.0 (phase-*.md, task-*.md, etc.)
  - Removes ALL agent command directories from worktrees (.codex/prompts/, .gemini/commands/, etc.)
  - Removes .kittify/scripts/ from worktrees (inherit from main repo)
  - Normalizes all frontmatter to consistent YAML format
  - Fixes issue where worktrees had old command templates referencing deprecated scripts

- **Flat structure in new features**
  - Fixed create-new-feature.sh to create flat tasks/ directory (not subdirectories)
  - Updated README.md documentation to reflect v0.9.0+ structure
  - New features now work correctly with frontmatter-only lanes from day one

- **Lane validation**
  - tasks_cli.py update command now validates lane values
  - Rejects invalid lanes before processing
  - Clear error messages for invalid input

### 🔧 Changed

- Added `ruamel.yaml>=0.18.0` dependency for consistent YAML handling
- Updated success messages to reflect flat structure

### 🚀 Migration

If you upgraded to v0.9.0 and still have issues, run `spec-kitty upgrade` again to apply v0.9.1 fixes:
- Completes any remaining lane migrations
- Cleans up worktree command directories
- Normalizes all frontmatter for consistency

## [0.9.0] - 2025-12-17

### 🎯 Major Release: Frontmatter-Only Lane Management

This release fundamentally changes how Spec Kitty manages work package lanes, eliminating directory-based lane tracking in favor of a simpler, conflict-free frontmatter-only system.

### ⚠️ Breaking Changes

- **Lane system completely redesigned**
  - Work packages now live in a flat `kitty-specs/<feature>/tasks/` directory
  - Lane status determined **solely by `lane:` frontmatter field** (no more subdirectories)
  - Old system: `tasks/planned/WP01.md`, `tasks/doing/WP02.md` ❌
  - New system: `tasks/WP01.md` with `lane: "planned"` ✅

- **Command renamed: `move` → `update`**
  - Legacy `tasks_cli.py move` command removed
  - Use `tasks_cli.py update <feature> <WP> <lane>` instead
  - Semantic clarity: command updates metadata, doesn't move files
  - Legacy format detection: `update` command refuses to work on old directory-based structure

- **Direct frontmatter editing now supported**
  - You can now directly edit the `lane:` field in WP frontmatter
  - Previous "DO NOT EDIT" warnings removed from all templates
  - System recognizes manual lane changes immediately
  - No file movement required for lane transitions

### 🆕 Added

- **Migration command: `spec-kitty upgrade`**
  - Automatically migrates features from directory-based to frontmatter-only format
  - Preserves all lane assignments during migration
  - Idempotent: safe to run multiple times
  - Cleans up empty lane subdirectories after migration
  - Migrates both main repo and worktree features

- **Legacy format detection**
  - `is_legacy_format()` function detects old directory-based structure
  - CLI commands display helpful warnings when legacy format detected
  - Dashboard shows migration prompt for legacy features
  - Non-blocking: legacy features remain functional until migrated

- **Enhanced status command**
  - Better formatted output with lane grouping
  - Auto-detects feature from branch/worktree when not specified
  - Shows work packages organized by current lane
  - Works with both legacy and new formats

### 🔧 Changed

- **Work package location logic**
  - `locate_work_package()` now searches flat `tasks/` directory first
  - Falls back to legacy subdirectory search for backwards compatibility
  - Exact WP ID matching (WP04 won't match WP04b)

- **Lane extraction utilities**
  - New `get_lane_from_frontmatter()` function extracts lane from YAML
  - Defaults to "planned" when `lane:` field missing
  - Validates lane values against allowed set
  - Available in both `task_helpers.py` and `tasks_support.py`

- **Dashboard scanner updates**
  - Reads lane from frontmatter instead of directory location
  - Displays legacy format warnings
  - Works seamlessly with both formats during transition

- **Activity log behavior**
  - Lane transitions still append activity log entries
  - Captures agent, shell PID, and timestamp
  - No file movement logged (because no movement occurs)

### 📚 Documentation

- **Updated all templates**
  - `.kittify/templates/task-prompt-template.md` - Removed "DO NOT EDIT" warnings
  - `.kittify/templates/tasks-template.md` - Updated for flat structure
  - `.kittify/templates/AGENTS.md` - New lane management instructions
  - `tasks/README.md` - Rewritten for flat directory layout

- **Updated mission templates**
  - All mission-specific templates updated (software-dev, research)
  - Command templates updated (`implement.md`, `review.md`, `merge.md`)
  - Examples updated to show new workflow

- **Updated main documentation**
  - `README.md` - Updated quick start examples
  - `docs/quickstart.md` - New lane management workflow
  - `docs/multi-agent-orchestration.md` - Updated collaboration examples
  - All `examples/` updated with new commands

### 🧪 Testing

- 286 tests passing (0 failures)
- New tests for frontmatter-only lane system
- Legacy format detection tests
- Migration command tests
- Dual-format compatibility tests

### 🚀 Migration Guide

**For existing projects:**

1. **Back up your work** (commit changes, push to remote)
2. **Run migration**: `spec-kitty upgrade`
3. **Verify**: `spec-kitty status --feature <your-feature>`
4. **Update workflows**: Replace `move` with `update` in scripts/docs

**Key benefits of upgrading:**

- ✅ No file conflicts during lane changes (especially in worktrees)
- ✅ Direct editing of `lane:` field supported
- ✅ Better multi-agent compatibility
- ✅ Simpler mental model (one directory, not four)
- ✅ Fewer git operations per lane change

**Legacy format still works** - You can continue using old directory structure until ready to migrate. All commands detect format automatically.

### 🐛 Fixed

- File conflicts during simultaneous lane changes by multiple agents
- Git staging issues with lane transitions
- Race conditions in worktree-based parallel development
- Lane mismatch validation errors (no longer possible with frontmatter-only)

### 🔗 Related

- Feature implementation: `007-frontmatter-only-lane`
- All 6 work packages completed and reviewed
- Comprehensive test coverage added

---

## [0.8.2] - 2025-12-17

### Added

- **Task lane management documentation** - Added clear instructions to AGENTS.md and task templates warning agents never to manually edit the `lane:` YAML field
  - Lane is determined by directory location, not YAML field
  - Editing `lane:` without moving the file creates a mismatch that breaks the system
  - All templates now include YAML comment: `# DO NOT EDIT - use: workflow commands` (legacy note)
  - Added "Task Lane Management Rule" section to project AGENTS.md

## [0.8.1] - 2025-12-17

### Fixed

- **Work package move race conditions** - Multiple agents can now work on different WPs simultaneously without blocking each other
  - Conflict detection now only blocks on changes to the same WP, not unrelated WP files
  - Agents working on WP05 no longer block moves of WP04

- **Exact WP ID matching** - `WP04` no longer incorrectly matches `WP04b`
  - Changed from prefix matching to exact boundary matching
  - Pattern now requires WP ID to be followed by `-`, `_`, `.`, or end of filename

- **Cleanup no longer leaves staged deletions** - Stale copy cleanup uses filesystem delete instead of `git rm`
  - Prevents orphaned staged deletions from blocking subsequent operations
  - Automatically unstages any previously staged changes to cleaned files

## [0.8.0] - 2025-12-15

### Breaking Changes

- **Mission system refactored to per-feature model**
  - Missions are now selected during `/spec-kitty.specify` instead of `spec-kitty init`
  - Each feature stores its mission in `meta.json` (field: `"mission": "software-dev"`)
  - `.kittify/active-mission` symlink/file is no longer used
  - Run `spec-kitty upgrade` to clean up existing projects

- **Removed commands**
  - `spec-kitty mission switch` - Missions are now per-feature, not per-project
  - Running this command now shows a helpful error message explaining the new workflow

- **Removed flags**
  - `--mission` flag from `spec-kitty init` - Use `/spec-kitty.specify` instead
  - Flag is hidden but shows deprecation warning if used

### Added

- **Mission inference during `/spec-kitty.specify`** - LLM analyzes feature description and suggests appropriate mission:
  - "Build a REST API" → suggests `software-dev`
  - "Research best practices" → suggests `research`
  - User confirms or overrides the suggestion
  - Explicit `--mission` flag bypasses inference

- **Per-feature mission storage** - Selected mission stored in feature's `meta.json`:
  - All downstream commands read mission from feature context
  - Legacy features without mission field default to `software-dev`

- **Mission discovery** - New `discover_missions()` function returns all available missions with source indicators

- **Updated `spec-kitty mission list`** - Shows source column (project/built-in) for each mission

- **Migration for v0.8.0** - `spec-kitty upgrade` removes obsolete `.kittify/active-mission` file

- **AGENTS.md worktree fix** - New worktrees get AGENTS.md symlink, and `spec-kitty upgrade` fixes existing worktrees

### Changed

- All downstream commands (`/spec-kitty.plan`, `/spec-kitty.tasks`, `/spec-kitty.implement`, `/spec-kitty.review`, `/spec-kitty.accept`) now read mission from feature's `meta.json`
- `create-new-feature.sh` accepts `--mission <key>` parameter to set mission in meta.json
- Common bash/PowerShell scripts updated to resolve mission from feature directory
- `spec-kitty mission current` shows current default mission (for informational purposes)
- Dashboard template now includes dynamic AGENTS.md path discovery instructions

### Deprecated

- `set_active_mission()` function - Shows deprecation warning, will be removed in future version

### Migration Guide

1. Run `spec-kitty upgrade` to remove `.kittify/active-mission`
2. Existing features without `mission` field will use `software-dev` by default
3. New features will have mission set during `/spec-kitty.specify`

## [0.7.4] - 2025-12-14

### Added

- **Script Update Migration** – `spec-kitty upgrade` now updates project scripts:
  - Copies latest `create-new-feature.sh` from package to project
  - Fixes worktree feature numbering bug in existing projects
  - Previously, projects kept old scripts from when they were initialized

## [0.7.3] - 2025-12-14

### Fixed

- **Duplicate Feature Numbers with Worktrees** – Script now scans both `kitty-specs/` AND `.worktrees/` for existing feature numbers:
  - Previously only scanned `kitty-specs/` which was empty when using worktrees
  - This caused new features to get `001` even when `001-*` worktree already existed
  - Now correctly finds highest number across both locations

## [0.7.2] - 2025-12-14

### Fixed

- **Duplicate Slash Commands in Worktrees (Corrected)** – Fixed the fix from v0.7.1:
  - v0.7.1 incorrectly removed commands from main repo (broke `/` commands there)
  - v0.7.2 removes commands from **worktrees** instead (they inherit from main repo)
  - Claude Code traverses UP, so worktrees find main repo's `.claude/commands/`
  - Main repo keeps commands, worktrees don't need their own copy

## [0.7.1] - 2025-12-14 [YANKED]

### Fixed

- ~~Duplicate Slash Commands in Worktrees~~ – **Incorrect fix, replaced by v0.7.2**

## [0.7.0] - 2025-12-14

### Added

- **`spec-kitty upgrade` Command** – Automatically migrate existing projects to current version:
  - Detects project version via metadata or directory structure heuristics
  - Applies all necessary migrations in order (0.2.0 → 0.6.7)
  - Auto-upgrades worktrees alongside main project
  - Supports `--dry-run`, `--verbose`, `--json`, `--target`, `--no-worktrees` options
  - Tracks applied migrations in `.kittify/metadata.yaml`
  - Idempotent - safe to run multiple times

- **Migration System** – Five automatic migrations for project structure updates:
  - `0.2.0`: `.specify/` → `.kittify/` directory rename
  - `0.4.8`: Add all 12 agent directories to `.gitignore`
  - `0.5.0`: Install encoding validation git hooks
  - `0.6.5`: `commands/` → `command-templates/` rename
  - `0.6.7`: Ensure software-dev and research missions are present

- **Broken Mission Detection** – `VersionDetector.detect_broken_mission_system()` identifies corrupted mission.yaml files

- **Migration Registry Validation** – Duplicate migration IDs and missing required fields now raise `ValueError`

### Fixed

- **Test Timeout in Dashboard CLI Tests** – Reduced port cleanup from 763 ports to 8 specific test ports
- **Playwright Window Handling** – Tests now open new windows (not tabs) and close properly on exit

## [0.6.7] - 2025-12-13

### Fixed

- **Missing software-dev Mission in PyPI Package** – Fixed build configuration to include all missions:
  - Added explicit sdist include patterns to pyproject.toml
  - The `software-dev` mission was missing from v0.6.5 and v0.6.6 wheel builds
  - Root cause: `force-include` only applied to wheel target, not sdist (wheel was built from sdist)
  - Now both `software-dev` and `research` missions are correctly packaged

## [0.6.6] - 2025-12-13

### Fixed

- **Test Suite Updated for 12 Agent Directories** – All tests now expect 12 agents (added `.github/copilot/`):
  - Updated `test_init_flow.py`, `test_gitignore_management.py`, `test_gitignore_manager_simple.py`
  - Updated `tests/unit/test_gitignore_manager.py` to expect 12 agents
  - Fixed template manager tests to use new `.kittify/` source paths

### Changed

- **Template Source Paths** – Tests now use correct `.kittify/templates/command-templates/` paths

## [0.6.5] - 2025-12-13

### Added

- **Pre-commit Git Hooks** – Automatic protection against committing agent directories:
  - Blocks commits containing `.claude/`, `.codex/`, `.gemini/`, etc.
  - Warns about `.github/copilot/` (nested in `.github/` which is usually committed)
  - Installed automatically during `spec-kitty init`

- **GitHub Copilot Directory Protection** – Added `.github/copilot/` as 12th protected agent directory

- **.claudeignore Generation** – Optimizes Claude Code token usage by excluding templates

### Fixed

- **Worktree Constitution Symlinks** – Feature worktrees now share constitution via symlink
- **Git Hooks Installation Timing** – Hooks now install after `.git/` is created

## [0.6.4] - 2025-11-26

### Fixed

- **Agent Commands Missing in Worktrees** – Slash commands now work in all feature worktrees for all AI agents:
  - `create-new-feature.sh` now symlinks agent command directories from main repo to worktrees
  - Supports all 12 agent types: Claude, Gemini, Copilot, Cursor, Qwen, OpenCode, Windsurf, Codex, KiloCode, Auggie, Roo, Amazon Q
  - Fixes `/spec-kitty.research`, `/spec-kitty.plan`, and all other slash commands in worktrees
  - Existing worktrees get symlinks added when reused (backward compatible)
  - Root cause: worktrees are separate working directories that don't share `.claude/commands/` etc.

## [0.6.3] - 2025-11-25

### Fixed

- **Mission Directory Not Copied During Init** – Projects initialized with `spec-kitty init` now correctly receive mission templates:
  - Fixed `copy_specify_base_from_package()` to look at correct path `specify_cli/missions` (matching pyproject.toml)
  - Previously looked at wrong paths: `.kittify/missions` and `template_data/missions`
  - `software-dev` mission was missing from initialized projects, breaking `/spec-kitty.plan` and other commands
  - Root cause: pyproject.toml packages missions to `specify_cli/missions` but code looked elsewhere

## [0.6.2] - 2025-11-18

### Fixed

- **PowerShell Wrapper Parameter Handling** – Windows lane transitions now work correctly:
  - Fixed legacy `tasks-move-to-lane.ps1` to properly parse named PowerShell parameters
  - Translates Spec Kitty's named params (`-FeatureName`, `-TaskId`, `-TargetLane`) to `tasks_cli.py` positional args
  - Resolves `unrecognized arguments` error that broke `/spec-kitty.review` on Windows
  - Maintains backward compatibility with positional argument usage
  - Fixes #34

## [0.6.1] - 2025-11-18

### Fixed

- **Untracked Task File Moves** – Task move workflow now handles untracked files:
  - Added `is_file_tracked()` helper to detect if file is in git index
  - Move command automatically stages untracked source files before moving
  - Fixes `/spec-kitty.implement` failures when `/spec-kitty.tasks` doesn't commit
  - Provides clear feedback: `[spec-kitty] Added untracked file: ...`
  - Defensive fix works with both existing untracked files and future workflows

## [0.6.0] - 2025-11-16

### Fixed

- **Dashboard Constitution Tracking** – Feature-level constitution.md files now tracked and displayed:
  - Added constitution to scanner artifact list
  - Constitution appears in overview with ⚖️ icon
  - Frontend properly detects constitution.exists property

- **Dashboard Modification Detection** – Dashboard now detects file modifications, not just existence:
  - Scanner returns {exists, mtime, size} for each artifact instead of boolean
  - Frontend updated to use .exists property with optional chaining
  - Overview auto-reloads when artifacts change during polling
  - No manual refresh required to see new/modified files

- **Dashboard Project Constitution Endpoint** – Project constitution now loads in dashboard:
  - Added /api/constitution endpoint to serve .kittify/memory/constitution.md
  - Sidebar Constitution link now displays file content instead of "not found"
  - Separate from feature-level constitution tracking

- **Work Package Conflict Detection Too Strict** – Moving WP no longer blocked by unrelated WP changes:
  - Conflict detection now scoped to same work package ID only
  - Moving WP04 no longer fails if WP06/WP08 have uncommitted changes
  - Reduces false positives from ~90% to ~5%
  - Agents don't need --force for unrelated work packages
  - Still catches real conflicts (same WP in multiple lanes)

- **Accept Command Over-Questioning** – Acceptance workflow now auto-detects instead of asking:
  - Feature slug auto-detected from git branch
  - Mode defaults to 'local' (most common)
  - Validation commands searched in git log
  - Only asks user if auto-detection fails
  - Reduces user questions from 3-4 to 0 in typical case

- **Init Command Blocking on Optional Tools** – Project init no longer fails on missing agent tools:
  - Changed from red error + exit(1) to yellow warning + continue
  - Gemini CLI and other tools are optional
  - Users can install tools later without re-init
  - --ignore-agent-tools flag still available but rarely needed

- **Encoding Normalization Incomplete** – Unicode smart quotes now properly normalized to ASCII:
  - Added character mapping for 12 common Unicode characters
  - Smart quotes (U+2018/U+2019) → ASCII apostrophe
  - Em/en dashes → hyphens
  - Ellipsis, bullets, nbsp → ASCII equivalents
  - --normalize-encoding now produces true ASCII output

### Changed

- **Mission Display Simplified** – Reduced verbose mission card to single line:
  - Removed domain label, version number, path display
  - Removed redundant refresh button (auto-updates every second)
  - Changed from card layout to inline text: "Mission: {name}"
  - Cleaner, less cluttered header

### Added

- **Mission System Architecture** – Complete mission-based workflow system (feature 005):
  - Guards module for pre-flight validation
  - Pydantic mission schema validation
  - Mission CLI commands (list, current, switch, info)
  - Research mission templates and citation validators
  - Path convention validation
  - Dashboard mission display
  - Comprehensive integration tests

## [0.5.3] - 2025-11-15

### Fixed

- **Dashboard Orphaned Process Cleanup** – Fixed dashboard startup failures caused by orphaned test processes:
  - Dashboard now detects and cleans up orphaned processes when health check fails due to project path mismatch
  - Added retry logic after successful orphan cleanup
  - Orphan cleanup triggers on health check failure (not just port exhaustion)
  - Eliminates false "Unable to start dashboard" errors when orphaned test dashboards occupy ports

- **Dashboard Subprocess Import Failure** – Fixed ModuleNotFoundError in complex Python environments:
  - Dashboard subprocess now always inserts spec-kitty path at sys.path[0]
  - Fixes import failures when user's PYTHONPATH or .pth files contain spec-kitty path at lower priority
  - Ensures correct spec-kitty installation takes precedence over environment paths
  - Resolves "ModuleNotFoundError: No module named 'specify_cli.dashboard'" in subprocesses

### Changed

- **Test Suite Cleanup Improvements** – Enhanced dashboard test cleanup to prevent orphaned processes:
  - Module-level cleanup fixture kills all orphaned dashboards before and after test runs
  - Expanded cleanup port range from 9992-9999 to 9237-10000 (covers default and test ranges)
  - Added `kill_all_spec_kitty_dashboards()` helper using pgrep/pkill
  - Two-tier cleanup strategy: module-level (all processes) + function-level (specific ports)

### Added

- **Testing Guidelines for Agents** (`docs/testing-guidelines.md`) – Comprehensive testing best practices:
  - Required cleanup patterns for dashboard tests (pytest fixtures, autouse fixtures)
  - Anti-patterns to avoid (cleanup in test body, shared directories, no exception handling)
  - Impact analysis of orphaned processes on local development and CI/CD
  - Examples of proper test isolation and resource management

### Changed

- **Command Consolidation** – Merged `spec-kitty check` and `spec-kitty diagnostics` into `spec-kitty verify-setup`:
  - Removed redundant `spec-kitty check` and `spec-kitty diagnostics` commands
  - Tool checking now integrated into `verify-setup` with `--check-tools` flag (default: enabled)
  - Diagnostics mode with dashboard health available via `--diagnostics` flag
  - Removed ASCII banner from verify-setup for cleaner output
  - Simplifies CLI interface - single command for all environment verification
  - JSON output includes tool availability when `--check-tools` is enabled

### Removed

- **`spec-kitty check` command** – Functionality moved to `verify-setup --check-tools`
  - Migration: Use `spec-kitty verify-setup` instead of `spec-kitty check`
  - Tool checking enabled by default, disable with `--check-tools=false`
- **`spec-kitty diagnostics` command** – Functionality moved to `verify-setup --diagnostics`
  - Migration: Use `spec-kitty verify-setup --diagnostics` instead of `spec-kitty diagnostics`
  - Shows Rich panel-based output with dashboard health, observations, and issues

## [0.5.2] - 2025-11-14

### Fixed

- **Dashboard Startup Race Condition** – Fixed root cause of dashboard health check timing out prematurely:
  - Increased health check timeout from 10 to 20 seconds with exponential backoff
  - Retry pattern: 10×100ms, 40×250ms, 20×500ms for adaptive performance
  - Removed workaround fallback check that was masking the real issue
  - Eliminated false "Unable to start dashboard" errors on slower systems

### Changed

- **Dashboard Health Check Strategy** – Improved reliability with exponential backoff:
  - Quick initial checks (100ms) for fast systems
  - Gradual slowdown (250ms then 500ms) for slower systems
  - Total timeout increased to ~20 seconds for adequate startup time
  - Cleaner error handling without port-scanning fallback

### Added

- **Symlinked kitty-specs Test Coverage** – New test validates dashboard works with worktree structure:
  - Tests scenario from bug report (symlinked `kitty-specs/` to `.worktrees/`)
  - Ensures dashboard starts correctly with symlinked directories
  - Prevents regression of false error reporting

## [0.5.1] - 2025-11-14

### Added

- **Task Metadata Validation Guardrail** – Prevents workflow failures when file locations don't match frontmatter:
  - Auto-detects lane mismatches (file in `for_review/` but `lane: "planned"`)
  - CLI command: `spec-kitty validate-tasks --fix`
  - Integrated into `/spec-kitty.review` workflow (auto-runs before review)
  - Adds activity log entries documenting all repairs
  - Validates required fields (work_package_id, lane) and formats
- **Task Metadata Validation Module** (`src/specify_cli/task_metadata_validation.py`) – Core validation:
  - `detect_lane_mismatch()` - Finds directory/frontmatter inconsistencies
  - `repair_lane_mismatch()` - Auto-fixes with audit trail
  - `validate_task_metadata()` - Comprehensive field validation
  - `scan_all_tasks_for_mismatches()` - Feature-wide scanning

### Changed

- **Version Reading** – Now reads dynamically from package metadata instead of hardcoded value:
  - Uses `importlib.metadata.version()` to get actual installed version
  - `spec-kitty --version` always shows correct version
  - No manual updates needed in `__init__.py`
- **Review Workflow** – Added automatic task metadata validation before review:
  - Runs `spec-kitty validate-tasks --fix` automatically
  - Prevents agents getting stuck on lane mismatches
  - Documented in `.claude/commands/spec-kitty.review.md`

### Fixed

- **Dashboard CLI False Error** – CLI no longer reports "Unable to start dashboard" when dashboard actually started successfully. Added fallback verification to check if dashboard is accessible before reporting failure. Handles race condition where health check times out but server is functional.
- **Review Workflow Blocking** – Review command no longer fails when file locations don't match frontmatter metadata. Auto-validation repairs inconsistencies before review.
- **Hardcoded Version** – `spec-kitty --version` now reads from package metadata, always shows correct installed version.

### Documentation

- **task-metadata-validation.md** (350 lines) – Auto-repair workflow:
  - Lane mismatch detection and repair
  - CLI usage examples
  - Python API reference
  - Integration with review workflow

### Testing

- Added version detection tests to prevent future hardcoded version bugs
- Task metadata validation tested with real frontmatter/directory mismatches
- All tests passing (13/13)

## [0.5.0] - 2025-11-13

### Added

- **Encoding Validation Guardrail** – Comprehensive 5-layer defense system to prevent Windows-1252 characters from crashing the dashboard:
  - **Layer 1**: Dashboard auto-fixes encoding errors on read (server-side resilience)
  - **Layer 2**: Character sanitization module with 15+ problematic character mappings
  - **Layer 3**: CLI command `spec-kitty validate-encoding` with `--fix` flag
  - **Layer 4**: Pre-commit hook that blocks commits with encoding errors
  - **Layer 5**: Enhanced AGENTS.md with real crash examples and character blacklist
- **Plan Validation Guardrail** – Prevents agents from skipping the planning phase:
  - Detects 11 template markers in plan.md (threshold: 5+ markers = unfilled)
  - Blocks `/spec-kitty.research` command when plan is unfilled
  - Blocks `/spec-kitty.tasks` via check-prerequisites.sh
  - Clear error messages with remediation steps
- **Character Sanitization Module** (`src/specify_cli/text_sanitization.py`) – Core module for encoding fixes:
  - Maps smart quotes (`' ' " "`) → ASCII (`' "`)
  - Maps plus-minus (`±`) → `+/-`, multiplication (`×`) → `x`, degree (`°`) → `degrees`
  - Supports dry-run mode and automatic backup creation
  - Directory-wide sanitization with glob patterns
- **Plan Validation Module** (`src/specify_cli/plan_validation.py`) – Template detection:
  - Configurable threshold (default: 5 markers)
  - Line-precise error reporting
  - Strict and lenient validation modes

### Changed

- **Version Reading** – Now reads dynamically from package metadata instead of hardcoded value:
  - Uses `importlib.metadata.version()` to get actual installed version
  - `spec-kitty --version` always shows correct version
  - No manual updates needed in `__init__.py`
- **Review Workflow** – Added automatic task metadata validation before review:
  - Runs `spec-kitty validate-tasks --fix` automatically
  - Prevents agents getting stuck on lane mismatches
  - Documented in `.claude/commands/spec-kitty.review.md`
- **Dashboard Scanner** – Now resilient to encoding errors:
  - Auto-fixes files on read with backup creation
  - Creates error cards instead of crashing on bad files
  - Logs encoding issues with clear error messages
- **Research Command** – Added plan validation gate before allowing research artifact creation
- **Prerequisites Check Script** – Added bash-based plan validation (35 lines)
- **AGENTS.md Template** – Enhanced with encoding warnings:
  - Real crash examples from production
  - Explicit character blacklist with Unicode codepoints
  - Auto-fix workflow documentation

### Fixed

- **Dashboard Blank Page Issue** – Dashboard no longer crashes when markdown files contain Windows-1252 smart quotes, ±, ×, ° symbols. Auto-fix sanitizes files on first read.
- **Agents Skipping Planning** – Research and tasks commands now blocked until plan.md is properly filled out (not just template).
- **Review Workflow Blocking** – Review command no longer fails when file locations don't match frontmatter metadata. Auto-validation repairs inconsistencies before review.
- **Hardcoded Version** – `spec-kitty --version` now reads from package metadata, always shows correct installed version.

### Documentation

- **encoding-validation.md** (554 lines) – Complete guide covering:
  - Problem description with real examples
  - 5-layer architecture explanation
  - Testing procedures and troubleshooting
  - Migration guide for existing projects
  - API reference and performance considerations
- **plan-validation-guardrail.md** (202 lines) – Implementation details:
  - Problem and solution overview
  - Configuration instructions
  - Testing procedures
  - Benefits and future enhancements
- **task-metadata-validation.md** (350 lines) – Auto-repair workflow:
  - Lane mismatch detection and repair
  - CLI usage examples
  - Python API reference
  - Integration with review workflow
- **TESTING_REQUIREMENTS_ENCODING_AND_PLAN_VALIDATION.md** (1056 lines) – Functional test specifications:
  - 35+ test cases across 6 test suites
  - Coverage targets (85-95%)
  - Performance requirements
  - Edge case testing requirements

### Testing

- Added 7 unit tests for plan validation (all passing)
- Verified on real project (battleship): fixed 9 files with encoding issues
- Dashboard now loads successfully after encoding fixes
- Character mapping tests: smart quotes, ±, ×, ° all converted correctly

## [0.4.13] - 2025-11-13

### Fixed

- **CRITICAL: verify-setup ImportError (Issue #28)** – Fixed ImportError in `verify-setup` command caused by incorrect import statement in `verify_enhanced.py`. Changed `from . import detect_feature_slug, AcceptanceError` to `from .acceptance import detect_feature_slug, AcceptanceError`. This was a blocking bug that prevented users from running the diagnostic command.

## [0.4.12] - 2025-11-13

### Added

- **Version Flag** – Added `--version` and `-v` flags to display installed spec-kitty-cli version.
- **Dashboard Health Diagnostics** – Enhanced `spec-kitty diagnostics` to detect dashboard startup failures, test if dashboard can start, and report specific errors. Now catches issues like corrupted files, health check timeouts, and background process failures.

### Changed

- **Diagnostics Output** – Added Dashboard Health panel showing startup test results, PID tracking status, and specific failure reasons.

## [0.4.11] - 2025-11-13

### Fixed

- **PowerShell Python Quoting Bug (Issue #26)** – Fixed SyntaxError in PowerShell scripts caused by double-quote conflicts in embedded Python code. Changed all Python strings in `common.ps1` to use single quotes to avoid PowerShell string parsing conflicts.

### Added

- **PowerShell Syntax Guide** – Created comprehensive `templates/POWERSHELL_SYNTAX.md` with bash vs PowerShell syntax comparison table, common mistakes, and debugging tips for AI agents.
- **Conditional PowerShell Reference** – Enhanced `agent-file-template.md` to conditionally include PowerShell syntax reminders only for PowerShell projects, keeping bash contexts clean.

### Changed

- **AI Agent Context** – PowerShell-specific guidance now provided via separate reference document instead of cluttering bash-focused templates.

Fixes #26
Addresses #27

## [0.4.10] - 2025-11-13

### Fixed

- **CRITICAL: Missing missions directory in PyPI package** – Added `.kittify/missions/` to `pyproject.toml` force-include list. Previous release (0.4.9) was missing this directory, causing "Active mission directory not found" errors for all fresh installations.

## [0.4.9] - 2025-11-13

### Added

- **Diagnostics CLI Command** – New `spec-kitty diagnostics` command with human-readable and JSON output for comprehensive project health checks.
- **Dashboard Process Tracking** – Dashboard now stores process PID in `.dashboard` metadata file for reliable cleanup and monitoring.
- **Feature Collision Detection** – Added explicit warnings when creating features with duplicate names that would overwrite existing work.
- **LLM Context Documentation** – Enhanced all 13 command templates with location pre-flight checks, file discovery sections, and workflow context to prevent agents from getting lost.

### Changed

- **Dashboard Lifecycle** – Enhanced `ensure_dashboard_running()` to automatically clean up orphaned dashboard processes on initialization, preventing port exhaustion.
- **Feature Creation Warnings** – `create-new-feature.sh` now warns when git is disabled or features already exist, with clear JSON indicators for LLM agents.
- **Import Safety** – Fixed `detect_feature_slug` import path in diagnostics module to use correct module location.
- **Worktree Documentation** – Updated WORKTREE_MODEL.md to accurately describe `.kittify/` as a complete copy (not symlink) with disk space implications documented.

### Fixed

- **CRITICAL: Dashboard Process Orphan Leak** – Fixed critical bug where background dashboard processes were orphaned and accumulated until all ports were exhausted. Complete fix includes:
  - PIDs are captured and stored in `.dashboard` file (commit b8c7394)
  - Orphaned processes with .dashboard files are automatically cleaned up on next init
  - HTTP shutdown failures fall back to SIGTERM/SIGKILL with PID tracking
  - Port range cleanup scans for orphaned dashboards without .dashboard files (commit 11340a4)
  - Safe fingerprinting via health check API prevents killing unrelated services
  - Automatic retry with cleanup when port exhaustion detected
  - Failed startup processes are cleaned up (no orphans from Ctrl+C during health check)
  - Multi-project scenarios remain fully isolated (per-project PIDs, safe port sweeps)
  - Handles all orphan types: with metadata, without metadata, deleted temp projects
  - Prevents "Could not find free port" errors after repeated uses

- **Import Path Bug** – Fixed `detect_feature_slug` import in `src/specify_cli/dashboard/diagnostics.py` to import from `specify_cli.acceptance` instead of package root.

- **Worktree Documentation Accuracy** – Corrected WORKTREE_MODEL.md which incorrectly stated `.kittify/` was symlinked; it's actually a complete copy due to git worktree behavior.

### LLM Context Improvements

All command templates enhanced with consistent context patterns:
- **Location Pre-flight Checks**: pwd/git branch verification with expected outputs and correction steps
- **File Discovery**: Lists what files {SCRIPT} provides, output locations, and available context
- **Workflow Context**: Documents before/after commands and feature lifecycle integration

Templates updated:
- merge.md: CRITICAL safety check preventing merges from wrong location
- clarify.md, research.md, analyze.md: HIGH priority core workflow commands
- specify.md, checklist.md: Entry point and utility commands
- constitution.md, dashboard.md: Project-level and monitoring commands

### Testing

- ✅ Dashboard comprehensive test suite (34 tests, 100% coverage)
- ✅ All CLI commands validated
- ✅ Import paths verified
- ✅ Worktree behavior confirmed across test scenarios
- ✅ LLM context patterns applied consistently

### Security

- Dashboard process cleanup prevents resource exhaustion attacks
- Explicit warnings when creating duplicate features prevent silent data overwrite
- Git disabled warnings ensure users know when version control is unavailable

### Backward Compatibility

All changes are fully backward compatible:
- PID storage is optional (old `.dashboard` files still work)
- Feature collision detection is advisory (doesn't block creation)
- LLM context additions don't change command behavior
- Dashboard cleanup is automatic (users don't need to do anything)

## [0.4.12] - 2025-11-11

### Added

- **Core Service Modules** – Introduced `specify_cli.core.git_ops`, `project_resolver`, and `tool_checker` packages to host git utilities, project discovery, and tool validation logic with clean public APIs.
- **Test Coverage** – Added dedicated suites (`tests/specify_cli/test_core/test_git_ops.py`, `test_project_resolver.py`, `test_tool_checker.py`) covering subprocess helpers, path resolution, and tool validation flows.

### Changed

- **CLI Import Surface** – `src/specify_cli/__init__.py` now imports git, resolver, and tool helpers from the new core modules, slimming the monolith and sharing the implementations across commands.
- **Versioning Compliance** – `pyproject.toml` bumped to v0.4.12 to capture the core-service extraction and accompanying behavior changes.

## [0.4.11] - 2025-11-11

### Added

- **Template Test Suite** – New `tests/test_template/` coverage exercises template manager, renderer, and agent asset generator flows to guard the init experience.

### Changed

- **Template System Extraction** – Moved template discovery, rendering, and asset generation logic out of `src/specify_cli/__init__.py` into dedicated `specify_cli.template` modules with shared frontmatter parsing.
- **Dashboard Reuse** – Updated the dashboard scanner to consume the shared frontmatter parser so Kanban metadata stays in sync with CLI-generated commands.

## [0.4.10] - 2025-11-11

### Added

- **Core Modules** – Introduced `specify_cli.core.config` and `specify_cli.core.utils` to centralize constants, shared helpers, and exports for downstream packages.
- **CLI UI Package** – Moved `StepTracker`, arrow-key selection, and related utilities into `specify_cli.cli.ui`, enabling reuse across commands.
- **Test Coverage** – Added dedicated unit suites for the new core modules and CLI UI interactions (12 new tests).

### Changed

- **Package Structure** – Created foundational package directories for `core/`, `cli/`, `template/`, and `dashboard/`, including structured `__init__.py` exports.
- **Init Command Dependencies** – Updated `src/specify_cli/__init__.py` to consume the extracted modules, reducing monolith size and improving readability.
- **File Utilities** – Replaced ad-hoc directory creation/removal with safe helper functions to prevent duplication across commands.

## [0.4.8] - 2025-11-10

### Added

- **GitignoreManager Module** – New centralized system for managing .gitignore entries for AI agent directories, replacing fragmented approach.
- **Comprehensive Agent Protection** – Auto-protect ALL 12 AI agent directories (.claude/, .codex/, .opencode/, etc.) in .gitignore during init, not just selected ones.
- **Duplicate Detection** – Smart duplicate detection prevents .gitignore pollution when running init multiple times.
- **Cross-Platform Support** – Line ending preservation ensures .gitignore works correctly on Windows, macOS, and Linux.

### Changed

- **init Command Behavior** – Now automatically protects all AI agent directories instead of just selected ones, ensuring no sensitive data is accidentally committed.
- **Error Messages** – Improved error messages for permission issues with clear remediation steps (e.g., "Run: chmod u+w .gitignore").

### Fixed

- **Dashboard Markdown Rendering** – Fixed issue where .md files in Research and Contracts tabs were not rendered, now properly displays formatted markdown content.
- **Dashboard CSV Display** – Fixed CSV files not rendering in dashboard, now displays as formatted tables with proper styling and hover effects.

### Security

- **Agent Directory Protection** – All 12 known AI agent directories are now automatically added to .gitignore during init, preventing accidental commit of API keys, auth tokens, and other sensitive data.
- **Special .github/ Handling** – Added warning for .github/ directory which is used both by GitHub Copilot and GitHub Actions, reminding users to review before committing.

### Removed

- **Legacy Functions** – Removed `handle_codex_security()` and `ensure_gitignore_entries()` functions, replaced by comprehensive GitignoreManager class.

## [0.4.7] - 2025-11-07

### Added

- **Dashboard Diagnostics Page** – New diagnostics page showing real-time environment analysis, artifact location mismatches, and actionable recommendations.
- **CLI verify-setup Command** – New `spec-kitty verify-setup` command for comprehensive environment diagnostics in the terminal.
- **Worktree-Aware Resolution** – Added `resolve_worktree_aware_feature_dir()` function that intelligently detects and prefers worktree locations.
- **Agent Location Checks** – Standardized "CRITICAL: Location Requirement" sections in command templates with bash verification scripts.
- **Test Coverage** – Added comprehensive test suite for gitignore management and Codex security features with 9 test cases covering all edge cases.

### Changed

- **Command Templates** – Enhanced plan.md and tasks.md with explicit worktree location requirements and verification scripts.
- **Error Messages** – Improved bash script errors with visual indicators (❌ ERROR, 🔧 TO FIX, 💡 TIP) and exact fix commands.
- **Research Command** – Updated to use worktree-aware feature directory resolution.
- **Refactored Codex Security** – Extracted Codex credential protection logic into a dedicated `handle_codex_security()` function for better maintainability and testability.

### Fixed

- **Artifact Location Mismatch** – Fixed issue where agents create artifacts in wrong location, preventing them from appearing in dashboard.

## [0.4.5] - 2025-11-06

### Added

- **Agent Guidance** – Bundled a shared `AGENTS.md` ruleset that is copied into `.kittify/` so every generated command has a canonical place to point agents for path/encoding/git expectations.
- **Encoding Toolkit** – Introduced `scripts/validate_encoding.py` and new documentation to scan/fix Windows-1252 artifacts, plus a non-interactive init guide in `docs/non-interactive-init.md`.
- **Dashboard Assets** – Split the inline dashboard UI into static CSS/JS files and committed them with the release.

### Changed

- **CLI Help & Docs** – Expanded `spec-kitty init`, `research`, `check`, `accept`, and `merge` help text and refreshed README/index links to render correctly on PyPI.
- **Dashboard Runtime** – Hardened the dashboard server/CLI handshake with health checks, token-gated shutdown, and more resilient worktree detection.
- **Mission Handling** – Improved mission activation to fall back gracefully when symlinks are unavailable (e.g., Windows w/out dev mode) and aligned shell helpers with the new logic.

### Security

- **Codex Guardrails** – Automatically append `.codex/` to `.gitignore`, warn if `auth.json` is tracked, and reiterate the `CODEX_HOME` workflow to keep API credentials out of source control.

## [0.4.6] - 2025-11-06

### Fixed

- **PyYAML Dependency** – Added `pyyaml` to the core dependency list so mission loading works in clean environments (CI no longer fails installing the package).
- **PyPI README Links** – Restored absolute documentation links to keep images and references working on PyPI.

## [0.4.4] - 2025-11-06

### Security

- **Credential Cleanup** – Removed the committed `.codex` directory (OpenAI credentials) from the entire Git history and regenerated sanitized release assets.
- **Token Rotation** – Documented that all compromised keys were revoked and environments refreshed before reissuing packages.

### Changed

- **Release Artifacts** – Rebuilt GitHub release bundles and PyPI distributions from the cleaned history to ensure no secrets are present in published archives.

## [0.3.2] - 2025-11-03

### Added

- **Automated PyPI Release Pipeline** – Tag-triggered GitHub Actions workflow automatically builds, validates, and publishes releases to PyPI using `PYPI_API_TOKEN` secret, eliminating manual publish steps.
- **Release Validation Tooling** – `scripts/release/validate_release.py` CLI enforces semantic version progression, changelog completeness, and version/tag alignment in both branch and tag modes with actionable error messages.
- **Release Readiness Guardrails** – Pull request workflow validates version bumps, changelog entries, and test passage before merge; nightly scheduled checks monitor drift.
- **Comprehensive Release Documentation** – Complete maintainer guides covering secret management, branch protection, troubleshooting, and step-by-step release workflows.
- **Changelog Extraction** – `scripts/release/extract_changelog.py` automatically extracts version-specific release notes for GitHub Releases.
- **Release Test Suite** – 4 pytest tests validate branch mode, tag mode, changelog parsing, and version regression detection.

### Changed

- **GitHub Actions Workflows** – Updated `release.yml` with pinned dependency versions, proper workflow ordering (PyPI publish before GitHub Release), and checksums stored in `dist/SHA256SUMS.txt`.
- **Workflow Reliability** – Fixed heredoc syntax error in `protect-main.yml` that was causing exit code 127 failures.

### Security

- **Secret Hygiene** – PyPI credentials exclusively stored in GitHub Actions secrets with rotation guidance; no tokens in repository or logs; workflows sanitize outputs.
- **Workflow Permissions** – Explicit least-privilege permissions in all workflows (contents:write, id-token:write for releases; contents:read for guards).

## [0.3.1] - 2025-11-03

### Changed

- **Worktree-Aware Merge Flow** – `/spec-kitty merge` now detects when it is invoked from a Git worktree, runs the actual merge steps from the primary repository checkout, and surfaces clearer guidance when the target checkout is dirty.

### Documentation

- **Merge Workflow Guidance** – Updated templates and Claude workflow docs to describe the primary-repo hand-off during merges and reinforce the feature-worktree best practice.

## [0.3.0] - 2025-11-02

### Added

- **pip Installation Instructions** – All documentation now includes pip installation commands alongside uv, making Spec Kitty accessible to users who prefer traditional Python package management.
- **Multiple Installation Methods** – Documented three installation paths: PyPI (stable), GitHub (development), and one-time usage (pipx/uvx).

### Changed

- **Documentation Consistency** – Updated README.md, docs/index.md, docs/installation.md, and docs/quickstart.md to provide both pip and uv commands throughout.
- **Installation Recommendations** – PyPI installation now marked as recommended for stable releases, with GitHub source for development versions.

### Fixed

- **Packaging Issues** – Removed duplicate `.kittify` force-include that caused "Duplicate filename in local headers" errors on PyPI.
- **Test Dependencies** – Added `pip install -e .[test]` to workflows to ensure all project dependencies available for tests.

## [0.2.20] - 2025-11-02

### Added

- **Automated PyPI Release Pipeline** – Tag-triggered GitHub Actions workflow automatically builds, validates, and publishes releases to PyPI using `PYPI_API_TOKEN` secret, eliminating manual publish steps.
- **Release Validation Tooling** – `scripts/release/validate_release.py` CLI enforces semantic version progression, changelog completeness, and version/tag alignment in both branch and tag modes with actionable error messages.
- **Release Readiness Guardrails** – Pull request workflow validates version bumps, changelog entries, and test passage before merge; protect-main workflow blocks direct pushes to main branch.
- **Comprehensive Release Documentation** – Complete maintainer guides covering secret management, branch protection, troubleshooting, and step-by-step release workflows in README, docs, and inline help.
- **Enhanced PyPI Metadata** – Added project URLs (repository, issues, docs, changelog), keywords, classifiers, and license information to improve PyPI discoverability and presentation.
- **Changelog Extraction** – `scripts/release/extract_changelog.py` automatically extracts version-specific release notes for GitHub Releases.
- **Release Test Suite** – 4 pytest tests validate branch mode, tag mode, changelog parsing, and version regression detection.

### Changed

- **GitHub Actions Workflows** – Replaced legacy release workflow with modern PyPI automation supporting validation, building, checksums, GitHub Releases, and secure publishing.
- **Documentation Structure** – Added dedicated releases section to docs with readiness checklist, workflow references, and troubleshooting guides; updated table of contents.

### Security

- **Secret Hygiene** – PyPI credentials exclusively stored in GitHub Actions secrets with rotation guidance; no tokens in repository or logs; workflows sanitize outputs.
- **Workflow Permissions** – Explicit least-privilege permissions in all workflows (contents:write, id-token:write for releases; contents:read for guards).

## [0.2.3] - 2025-10-29

### Added

- **Mission system assets** – Bundled Software Dev Kitty and Deep Research Kitty mission definitions (commands, templates, constitutions) directly in the CLI package so `spec-kitty init` can hydrate missions without a network call.

### Changed

- Synced mission templates between the repository and packaged wheel to keep `/spec-kitty.*` commands consistent across `--ai` choices.

## [0.2.2] - 2025-10-29

### Added

- **Phase 0 Research command** – `spec-kitty research` (and `/spec-kitty.research`) scaffolds `research.md`, `data-model.md`, and CSV evidence logs using mission-aware templates so Deep Research Kitty teams can execute discovery workflows without leaving the guided process.
- **Mission templates for research** – Deep Research Kitty now ships reusable templates for research decisions, data models, and evidence capture packaged inside the Python wheel.

### Changed

- Updated `spec-kitty init` guidance, plan command instructions, and README workflow to include the new research phase between planning and task generation.

## [0.2.1] - 2025-10-29

### Added

- **Mission picker in init** - `spec-kitty init` now prompts for a mission (or accepts `--mission`) so projects start with Software Dev Kitty, Deep Research Kitty, or another bundled mission and record the choice in `.kittify/active-mission`.

### Changed

- Highlight the active mission in the post-init guidance while keeping the Codex export step as the final instruction.

## [0.2.0] - 2025-10-28

### Added

- **New `/spec-kitty.merge` command** - Completes the workflow by merging features into main branch and cleaning up worktrees automatically. Supports multiple merge strategies (merge, squash, rebase), optional push to origin, and configurable cleanup of worktrees and branches.
- **Worktree Strategy documentation** - Added comprehensive guide to the opinionated worktree approach for parallel feature development.
- **Dashboard screenshots** - Added dashboard-kanban.png and dashboard-overview.png showcasing the real-time kanban board.
- **Real-Time Dashboard section** - Added prominent dashboard documentation "above the fold" in README with screenshots and feature highlights.
- **Mission management CLI** - `spec-kitty mission list|current|switch|info` for inspecting and activating domain-specific missions inside a project.
- **Deep Research Kitty mission** - Research-focused templates (spec, plan, tasks, findings, prompts) and command guardrails for evidence-driven work.
- **Mission packaging** - Missions are now bundled in release archives and Python wheels so project initialization copies `.kittify/missions` automatically.

### Changed

- Updated command list in init output to show workflow order and include merge command.
- Updated `/spec-kitty.accept` description to clarify it verifies (not merges) features.
- Reordered slash commands documentation to reflect actual execution workflow.
- Updated maintainers to reflect fork ownership (Robert Douglass).
- Updated all repository references from `spec-kitty/spec-kitty` to `Priivacy-ai/spec-kitty`.
- Updated installation instructions to use GitHub repository URL instead of local directory.

### Fixed

- Removed invalid `multiple=True` parameter from `typer.Option()` in accept command that caused TypeError on CLI startup.
- Fixed "nine articles" claim in spec-driven.md to "core articles" (only 6 are documented).

### Removed

- Removed SECURITY.md (GitHub-specific security policies).
- Removed CODE_OF_CONDUCT.md (GitHub-specific contact information).
- Removed video overview section from README (outdated content).
- Removed plant emoji (🌱) branding from all documentation and code.
- Replaced logo_small.webp and logo_large.webp with actual spec-kitty cat logo.

## [0.1.3] - 2025-10-28

### Fixed

- Removed invalid `multiple=True` parameter from `typer.Option()` in accept command that caused TypeError on CLI startup.

## [0.1.2] - 2025-10-28

### Changed

- Rebranded the CLI command prefix from `speckitty` to `spec-kitty`, including package metadata and documentation references.
- Migrated template directories from `.specify` to `.kittify` and feature storage from `/specs` to `/kitty-specs` to avoid namespace conflicts with Spec Kit.
- Updated environment variables, helper scripts, and dashboards to align with the new `.kittify` and `kitty-specs` conventions.

## [0.1.1] - 2025-10-07

### Added

- New `/spec-kitty.accept` command (and `spec-kitty accept`) for feature-level acceptance: validates kanban state, frontmatter metadata, and artifacts; records acceptance metadata in `meta.json`; prints merge/cleanup instructions; and supports PR or local workflows across every agent.
- Acceptance helper scripts (`accept-feature.sh` / `.ps1`) and expanded `tasks_cli` utilities (`status`, `verify`, `accept`) for automation and integration with AI agents.
- Worktree-aware bootstrap workflow now defaults to creating per-feature worktrees, enabling parallel feature development with isolated sandboxes.
- Implementation prompts now require operating inside the feature’s worktree and rely on the lane helper scripts for moves/metadata, eliminating `git mv` conflicts; the dashboard also surfaces active/expected worktree paths.

### Changed

- `/spec-kitty.specify`, `/spec-kitty.plan`, and `/spec-kitty.clarify` now run fully conversational interviews—asking one question at a time, tracking internal coverage without rendering markdown tables, and only proceeding once summaries are confirmed—while continuing to resolve helper scripts via the `.kittify/scripts/...` paths.
- Added proportionality guidance so discovery, planning, and clarification depth scales with feature complexity (e.g., lightweight tic-tac-toe flows vs. an operating system build).
- `/spec-kitty.tasks` now produces both `tasks.md` and the kanban prompt files in one pass; the separate `/spec-kitty.task-prompts` command has been removed.
- Tasks are grouped into at most ten work packages with bundled prompts, reducing file churn and making prompt generation LLM-friendly.
- Both shell and PowerShell feature bootstrap scripts now stop with guidance to return `WAITING_FOR_DISCOVERY_INPUT` when invoked without a confirmed feature description, aligning with the new discovery workflow.

## [0.1.0] - 2025-10-07

### Changed

- `/spec-kitty.specify` and `/spec-kitty.plan` now enforce mandatory discovery interviews, pausing until you answer their question sets before any files are written.
- `/spec-kitty.implement` now enforces the kanban workflow (planned → doing → for_review) with blocking validation, new helper scripts, and a task workflow quick reference.
- Removed the legacy `specify` entrypoint; the CLI is now invoked exclusively via `spec-kitty`.
- Updated installation instructions and scripts to use the new `spec-kitty-cli` package name and command.
- Simplified local template overrides to use the `SPEC_KITTY_TEMPLATE_ROOT` environment variable only.

## [0.0.20] - 2025-10-07

### Changed

- Renamed the primary CLI entrypoint to `spec-kitty` and temporarily exposed a legacy `specify` alias for backwards compatibility.
- Refreshed documentation, scripts, and examples to use the `spec-kitty` command by default.

## [0.0.19] - 2025-10-07

### Changed

- Rebranded the project as Spec Kitty, updating CLI defaults, docs, and scripts while acknowledging the original GitHub Spec Kit lineage.
- Renamed all slash-command prefixes and generated artifact names from `/speckit.*` to `/spec-kitty.*` to match the new branding.

### Added

- Refreshed CLI banner text and tagline to reflect spec-kitty branding.

## [0.0.18] - 2025-10-06

### Added

- Support for using `.` as a shorthand for current directory in `spec-kitty init .` command, equivalent to `--here` flag but more intuitive for users.
- Use the `/spec-kitty.` command prefix to easily discover Spec Kitty-related commands.
- Refactor the prompts and templates to simplify their capabilities and how they are tracked. No more polluting things with tests when they are not needed.
- Ensure that tasks are created per user story (simplifies testing and validation).
- Add support for Visual Studio Code prompt shortcuts and automatic script execution.
- Allow `spec-kitty init` to bootstrap multiple AI assistants in one run (interactive multi-select or comma-separated `--ai` value).
- When running from a local checkout, `spec-kitty init` now copies templates directly instead of downloading release archives, so new commands are immediately available.

### Changed

- All command files now prefixed with `spec-kitty.` (e.g., `spec-kitty.specify.md`, `spec-kitty.plan.md`) for better discoverability and differentiation in IDE/CLI command palettes and file explorers

# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to the Spec Kitty CLI and templates are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to the Spec Kitty CLI and templates are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

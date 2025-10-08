# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to the Spec Kitty CLI and templates are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-10-07

### Changed

- `/speckitty.specify`, `/speckitty.plan`, and `/speckitty.clarify` now run fully conversational interviews—asking one question at a time, tracking internal coverage without rendering markdown tables, and only proceeding once summaries are confirmed—while continuing to resolve helper scripts via the `.specify/scripts/...` paths.
- Added proportionality guidance so discovery, planning, and clarification depth scales with feature complexity (e.g., lightweight tic-tac-toe flows vs. an operating system build).
- `/speckitty.tasks` now produces both `tasks.md` and the kanban prompt files in one pass; the separate `/speckitty.task-prompts` command has been removed.
- Tasks are grouped into at most ten work packages with bundled prompts, reducing file churn and making prompt generation LLM-friendly.
- Both shell and PowerShell feature bootstrap scripts now stop with guidance to return `WAITING_FOR_DISCOVERY_INPUT` when invoked without a confirmed feature description, aligning with the new discovery workflow.

## [0.1.0] - 2025-10-07

### Changed

- `/speckitty.specify` and `/speckitty.plan` now enforce mandatory discovery interviews, pausing until you answer their question sets before any files are written.
- `/speckitty.implement` now enforces the kanban workflow (planned → doing → for_review) with blocking validation, new helper scripts, and a task workflow quick reference.
- Removed the legacy `specify` entrypoint; the CLI is now invoked exclusively via `speckitty`.
- Updated installation instructions and scripts to use the new `speckitty-cli` package name and command.
- Simplified local template overrides to use the `SPECKITTY_TEMPLATE_ROOT` environment variable only.

## [0.0.20] - 2025-10-07

### Changed

- Renamed the primary CLI entrypoint to `speckitty` and temporarily exposed a legacy `specify` alias for backwards compatibility.
- Refreshed documentation, scripts, and examples to use the `speckitty` command by default.

## [0.0.19] - 2025-10-07

### Changed

- Rebranded the project as Spec Kitty, updating CLI defaults, docs, and scripts while acknowledging the original GitHub Spec Kit lineage.
- Renamed all slash-command prefixes and generated artifact names from `/speckit.*` to `/speckitty.*` to match the new branding.

### Added

- Refreshed CLI banner text and tagline to reflect spec-kitty branding.

## [0.0.18] - 2025-10-06

### Added

- Support for using `.` as a shorthand for current directory in `speckitty init .` command, equivalent to `--here` flag but more intuitive for users.
- Use the `/speckitty.` command prefix to easily discover Spec Kitty-related commands.
- Refactor the prompts and templates to simplify their capabilities and how they are tracked. No more polluting things with tests when they are not needed.
- Ensure that tasks are created per user story (simplifies testing and validation).
- Add support for Visual Studio Code prompt shortcuts and automatic script execution.
- Allow `speckitty init` to bootstrap multiple AI assistants in one run (interactive multi-select or comma-separated `--ai` value).
- When running from a local checkout, `speckitty init` now copies templates directly instead of downloading release archives, so new commands are immediately available.

### Changed

- All command files now prefixed with `speckitty.` (e.g., `speckitty.specify.md`, `speckitty.plan.md`) for better discoverability and differentiation in IDE/CLI command palettes and file explorers

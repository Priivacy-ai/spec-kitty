# Implementation Plan: Agent Profile Projection and Plugin Production Pipeline

**Branch**: `feat/agent-profile-projection-plugin-production` | **Date**: 2026-06-14 | **Spec**: [spec.md](spec.md)
**Mission ID**: 01KV3NGSDCJ272573TF6T6NWDW | **Mission slug**: agent-profile-projection-plugin-production-01KV3NGS

## Summary

rc44 added the ToolSurfaceContract registry and staging plugin bundles but stopped short of wiring the repair service into `init`/`upgrade`, shipping production plugin artifacts, and implementing Codex native profile projection. This plan closes all gaps across eight implementation concerns: surface repair wiring, Codex profile renderer, harness capability matrix completion, Claude Code plugin build pipeline, Codex plugin bundle projector, command-skill manifest self-heal, Roo Code deprecation, and certification tests with an rc44-era migration acceptance fixture.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (YAML/frontmatter), tomli/tomllib (TOML write for Codex profiles), pytest (testing), mypy (strict type checking), ruff (linting)
**Storage**: Files — JSONL event log, YAML config (`.kittify/config.yaml`), Markdown agent profiles (`.claude/agents/`, `.github/agents/`, `.augment/agents/`), TOML agent profiles (`.codex/agents/`), JSON agent config (`~/.aws/amazonq/cli-agents/`), JSON plugin manifests (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`), JSON command-skill manifests (`.kittify/command-skills-manifest.json`), JSON managed-doctrine skill manifests (`.kittify/skills-manifest.json`)
**Testing**: pytest with ≥90% branch coverage on new code; `mypy --strict` on changed modules; `ruff check`; integration tests for CLI commands; migration acceptance fixture for rc44-era upgrade scenario
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform CLI tool)
**Project Type**: Single Python package (`src/specify_cli/`)
**Performance Goals**: `spec-kitty upgrade` completes in ≤30 s on a typical project; `spec-kitty plugin build` completes in ≤60 s; `doctor tool-surfaces` completes in ≤5 s
**Constraints**: Python 3.11+; McCabe complexity ≤15 on new/changed functions; no new top-level dependencies not already in `pyproject.toml` unless strictly required; drift policy applies uniformly across all surface kinds; `--yes` alone must never overwrite drifted files
**Scale/Scope**: 19 supported harnesses; ≤15 canonical command skills; ≤20 built-in agent profiles; single project checkout at a time

## Charter Check

- **typer** CLI framework: ✓ All new CLI commands (`plugin build`) use typer
- **rich** console output: ✓ Upgrade/init summary uses rich panels/tables
- **ruamel.yaml** for YAML: ✓ Used for agent profile frontmatter
- **mypy --strict**: ✓ Applied to all new and changed modules
- **90%+ test coverage**: ✓ New code paths have focused unit + integration tests
- **No direct push to origin/main**: ✓ All changes go through PR from `feat/agent-profile-projection-plugin-production`
- **Migrations use `get_agent_dirs_for_project()`**: ✓ Hardcoded `AGENT_DIRS` is forbidden
- **No `feature*` terminology**: ✓ All new code and docs use `mission`
- **Complexity ceiling ≤15**: ✓ Functions near the limit will be extracted

Gates pass. No charter violations.

## Project Structure

### Documentation (this mission)

```
kitty-specs/agent-profile-projection-plugin-production-01KV3NGS/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── drift-policy.md
│   ├── plugin-manifest-claude.md
│   └── plugin-manifest-codex.md
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (affected surfaces)

```
src/specify_cli/
├── core/
│   └── config.py                        # Remove roo from AI_CHOICES (IC-07)
├── cli/
│   └── commands/
│       ├── init.py                      # Wire repair service (IC-01)
│       ├── upgrade.py                   # Wire repair service (IC-01)
│       ├── doctor.py                    # Verify agent_profile coverage (IC-03)
│       └── plugin.py                    # NEW: plugin build command (IC-04, IC-05)
├── tool_surface/
│   ├── profiles/
│   │   ├── renderers.py                 # Add CodexProfileRenderer, AmazonQ, Augment (IC-02, IC-03)
│   │   ├── projection.py                # Wire new renderers (IC-02, IC-03)
│   │   └── __init__.py                  # Export new renderers (IC-02, IC-03)
│   ├── providers/
│   │   └── agent_profiles.py            # Update not_applicable matrix (IC-03)
│   ├── bundles/
│   │   ├── claude.py                    # Productionize: real version, bin/ script (IC-04)
│   │   ├── codex.py                     # NEW: CodexBundleProjector (IC-05)
│   │   └── __init__.py                  # Export CodexBundleProjector (IC-05)
│   ├── repair.py                        # Ensure drift policy handles interactive/non-interactive (IC-01)
│   └── service.py                       # Export repair-only entry point for init/upgrade (IC-01)
├── skills/
│   ├── manifest_store.py                # Stale manifest detection and self-heal (IC-06)
│   └── command_installer.py             # Unsafe symlink detection and removal (IC-06)
├── upgrade/
│   └── migrations/
│       └── m_0_XX_roo_deprecation.py    # Remove roo from AGENT_DIRS, detect .roo/ (IC-07)
└── agent_utils/
    └── directories.py                   # Remove roo key mappings (IC-07)

tests/specify_cli/
├── tool_surface/
│   └── profiles/
│       ├── test_renderers.py            # Add Codex/AmazonQ/Augment renderer tests (IC-08)
│       └── test_projection.py           # Add not_applicable matrix tests (IC-08)
├── integration/
│   ├── test_init_surface_repair.py      # NEW: init wiring integration test (IC-08)
│   ├── test_upgrade_surface_repair.py   # NEW: upgrade wiring integration test (IC-08)
│   └── test_rc44_migration_fixture.py   # NEW: rc44-era acceptance fixture (IC-08)
└── cli/
    └── commands/
        └── test_plugin_build.py         # NEW: plugin build command tests (IC-08)

dist/spec-kitty-plugins/                 # Build output (git-ignored)
├── claude-code/                         # Claude Code plugin bundle (IC-04)
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── skills/
│   ├── agents/
│   ├── bin/
│   │   └── spec-kitty-wrapper
│   └── marketplace.json
└── codex/                               # Codex plugin bundle (IC-05)
    ├── .codex-plugin/
    │   └── plugin.json
    ├── skills/
    └── marketplace.json
```

**Structure Decision**: Single Python package (`src/specify_cli/`). All new code stays within the existing module hierarchy. One new CLI command sub-group (`plugin`) is added under `src/specify_cli/cli/commands/plugin.py`. Build artifacts go to `dist/spec-kitty-plugins/` (already the staging target from rc44).

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Init/Upgrade Surface Repair Wiring

- **Purpose**: Call `SurfaceRepairService` from `spec-kitty init` and `spec-kitty upgrade` so missing/stale surfaces are auto-healed and drifted surfaces are drift-protected without silent overwrite.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-006, NFR-007
- **Affected surfaces**: `src/specify_cli/cli/commands/init.py`, `src/specify_cli/upgrade/run.py`, `src/specify_cli/tool_surface/repair.py`, `src/specify_cli/tool_surface/service.py`
- **Sequencing/depends-on**: IC-02 and IC-03 must exist so renderers are registered before repair runs
- **Risks**: `SurfaceRepairService` currently assumes an interactive context; must thread `is_interactive: bool` through the repair call. The `--yes` flag (typer) must not be mistaken for "allow drift overwrite." Needs a new `--repair-drift=overwrite` flag added to both commands. Idempotency test must verify second-run produces zero diff.

### IC-02 — Codex Native Profile Renderer

- **Purpose**: Implement `CodexProfileRenderer` projecting built-in Spec Kitty profiles to `.codex/agents/<profile_id>.toml` with the three required fields (`name`, `description`, `developer_instructions`) so Codex CLI recognizes them as custom agents.
- **Relevant requirements**: FR-011, FR-016, FR-038, FR-039
- **Affected surfaces**: `src/specify_cli/tool_surface/profiles/renderers.py`, `src/specify_cli/tool_surface/profiles/__init__.py`, `src/specify_cli/tool_surface/providers/agent_profiles.py`
- **Sequencing/depends-on**: none
- **Risks**: Python's standard library `tomllib` (3.11+) is read-only; `tomli-w` or `tomllib`-compatible write needed. Profile `developer_instructions` field must be synthesized from the Spec Kitty profile's `delegations` + `instructions` body — the mapping must be designed carefully. TOML output must survive round-trip through Codex CLI without errors.

### IC-03 — Harness Capability Matrix Completion

- **Purpose**: Encode the `not_applicable`/`research_gap`/renderer decision for all remaining harnesses (Amazon Q CLI, Augment Code, Windsurf, Cursor, Kiro, etc.) so `doctor tool-surfaces --kind agent-profile` reports accurate per-harness status with no silent gaps.
- **Relevant requirements**: FR-012, FR-013, FR-014, FR-015, FR-016
- **Affected surfaces**: `src/specify_cli/tool_surface/profiles/renderers.py`, `src/specify_cli/tool_surface/providers/agent_profiles.py`, `src/specify_cli/tool_surface/enums.py` (if new status values needed)
- **Sequencing/depends-on**: IC-02 (Codex must be implemented so it leaves `research_gap` status)
- **Risks**: Amazon Q CLI targets `~/.aws/amazonq/cli-agents/` (user-global, outside project root); the repair service and manifest tracking must handle paths outside the project tree without breaking the staging-safety guard. Augment Code format confirmed CLI-GA but IDE-beta — needs explicit documented ruling. Windsurf/Cursor/Kiro must each get an explicit `not_applicable` with a recorded reason, not just silence.

### IC-04 — Claude Code Plugin Build Pipeline

- **Purpose**: Implement `spec-kitty plugin build --target claude-code` as a real build command producing a production-ready Claude Code plugin bundle — replacing the `version: 0.0.0` placeholder, adding a `bin/` wrapper script with CLI-check + uvx fallback, and maintaining a `marketplace.json` for git-based distribution.
- **Relevant requirements**: FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, NFR-004
- **Affected surfaces**: `src/specify_cli/cli/commands/plugin.py` (new), `src/specify_cli/tool_surface/bundles/claude.py`, `src/specify_cli/tool_surface/providers/plugin_bundle.py`, `dist/spec-kitty-plugins/claude-code/`
- **Sequencing/depends-on**: IC-06 (skill set must be current before bundling)
- **Risks**: Plugin version must be read from `pyproject.toml` at build time (not hardcoded). The `bin/` wrapper script must be shell-portable (bash/zsh/sh on macOS/Linux; a `.cmd` equivalent or PowerShell script for Windows). `claude plugin validate --strict` must be available in CI — plan must document how to install Claude CLI in CI. The `marketplace.json` source type is `git-subdir` or `local` depending on repo layout.

### IC-05 — Codex Plugin Bundle Projector

- **Purpose**: Implement `CodexBundleProjector` generating `.codex-plugin/plugin.json` with all required interface fields, bundling the current canonical skill set and MCP config, and producing a companion `marketplace.json` for repo-local Codex plugin install.
- **Relevant requirements**: FR-025, FR-026, FR-027, FR-028, FR-029
- **Affected surfaces**: `src/specify_cli/tool_surface/bundles/codex.py` (new), `src/specify_cli/tool_surface/bundles/__init__.py`, `src/specify_cli/tool_surface/providers/plugin_bundle.py`
- **Sequencing/depends-on**: IC-06 (skills must be current before bundling); IC-02 (not for bundling agents, but for ensuring the skill set is fully wired)
- **Risks**: The `hooks` key is NOT valid in `plugin.json` for Codex (rejected by validator); hooks are discovered by filesystem presence. Must guard against accidentally adding `agents/` to the plugin bundle. `interface.displayName` and `interface.shortDescription` are required and must be non-empty strings.

### IC-06 — Command-Skill Manifest Self-Heal

- **Purpose**: Make stale command-skill manifests (e.g., 11-entry rc44-era) self-heal during `spec-kitty upgrade` without prompting, detect and remove unsafe symlink artifacts (e.g., `.agents/skills/spec-kitty.advise`), and ensure drifted SKILL.md files follow the same drift policy as agent profiles.
- **Relevant requirements**: FR-030, FR-031, FR-032
- **Affected surfaces**: `src/specify_cli/skills/manifest_store.py`, `src/specify_cli/skills/command_installer.py`, `src/specify_cli/upgrade/migrations/`
- **Sequencing/depends-on**: none (independent)
- **Risks**: Symlink removal must be Windows-compatible (`os.path.islink` behavior). Must not remove user-created symlinks that coincidentally share a name with a canonical skill. The "stale vs. drifted" distinction for SKILL.md files requires the manifest to store a content hash or last-known-good checksum — verify existing `manifest_store.py` tracks this.

### IC-07 — Roo Code Deprecation and Removal

- **Purpose**: Remove Roo Code from the supported agents list, add an upgrade migration that detects existing `.roo/` directories and emits a deprecation notice, remove `roo` from `config.yaml` when present, and update documentation.
- **Relevant requirements**: FR-033, FR-034, FR-035, FR-036
- **Affected surfaces**: `src/specify_cli/core/config.py` (not `__init__.py` — `AI_CHOICES` lives in `config.py`), `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` (or new migration), `src/specify_cli/agent_utils/directories.py`, `src/specify_cli/cli/commands/init.py`, `README.md`
- **Sequencing/depends-on**: none; can be implemented first
- **Risks**: Existing test fixtures that reference `roo` or `.roo/` must be updated. The deprecation notice must not error if `.roo/` does not exist. The migration must not delete `.roo/` content — only warn and update config.

### IC-08 — Certification Tests and Migration Fixture

- **Purpose**: Add focused automated tests for every new renderer and wiring point, and the rc44-era migration acceptance fixture that validates the complete upgrade path from a known-bad state to zero-error doctor output.
- **Relevant requirements**: FR-037, FR-038, FR-039, FR-040, FR-041, FR-042, NFR-001, NFR-002, NFR-005
- **Affected surfaces**: `tests/specify_cli/tool_surface/profiles/`, `tests/specify_cli/integration/`, `tests/specify_cli/cli/commands/`
- **Sequencing/depends-on**: all other ICs; must be implemented alongside or immediately after each IC (not deferred to end)
- **Risks**: The rc44-era fixture must represent a reproducible project state without network calls. The doctor JSON stability test in `test_migration_compat.py` must be updated to include new surface kinds without breaking the frozen baseline contract (additive only). Tests that call `claude plugin validate` require the Claude CLI to be present — mock or skip with a clear marker in CI environments without it.
